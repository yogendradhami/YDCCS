from io import BytesIO

import cloudinary
import requests
from cloudinary.utils import cloudinary_url
from django.db.models import Q, Case, Count, When, Value, IntegerField
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.core.paginator import Paginator
from django.db.models import (
    Q,
    Case,
    When,
    Value,
    IntegerField,
)
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from urllib.parse import urlencode

from .forms import CompanyDocumentForm
from .models import (
    CompanyDocument,
    CompanyDocumentAudit,
    BulkImportBatch,
    BulkImportItem,
)

from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from datetime import datetime, date, timedelta
from django.db import transaction
from django.core.paginator import Paginator
from .services.bulk_import import (
    create_batch,
    analyse_batch,
    refresh_batch_statistics,
    import_approved_batch,
    delete_staged_raw_document,
)

from company_documents.services.compliance_requirements import (
    build_overall_report,
)

from company_documents.services.employee_compliance import (
    build_employee_compliance_profile,
)
from company_documents.services.compliance_resolution import (
    resolve_document_compliance,
)

from .services.compliance_notifications import (
    get_compliance_document_alerts,
    get_compliance_notification_summary,
)


@login_required
def compliance_notifications(request):
    """
    Live compliance notification centre.

    Alerts are calculated from the current CompanyDocument
    records and are not persisted as duplicate notifications.
    """

    if not can_manage_documents(request.user):
        raise Http404

    alerts = get_compliance_document_alerts()

    severity = request.GET.get("severity", "").strip().lower()
    alert_type = request.GET.get("type", "").strip().lower()
    search = request.GET.get("q", "").strip()

    if severity in {"critical", "warning", "notice"}:
        alerts = [
            alert
            for alert in alerts
            if alert["severity"] == severity
        ]

    if alert_type:
        alerts = [
            alert
            for alert in alerts
            if alert["type"] == alert_type
        ]

    if search:
        search_lower = search.lower()

        alerts = [
            alert
            for alert in alerts
            if (
                search_lower in alert["title"].lower()
                or search_lower in alert["message"].lower()
                or search_lower in alert["related_name"].lower()
                or search_lower in alert["document"].name.lower()
            )
        ]

    context = {
        "alerts": alerts,
        "summary": get_compliance_notification_summary(
            get_compliance_document_alerts()
        ),
        "active_severity": severity,
        "active_type": alert_type,
        "search_query": search,
    }

    return render(
        request,
        "dashboard/company_documents/compliance_notifications.html",
        context,
    )

# ==========================================================
# ACCESS CONTROL
# ==========================================================

def can_manage_documents(user):
    """
    Company document management is restricted to staff/superusers.
    """

    return bool(
        user.is_authenticated
        and (user.is_superuser or user.is_staff)
    )


def can_access_document(user, document):
    """
    Determine whether the current user can access a document.

    Sensitive documents require either:
    - superuser access
    - explicit download_sensitive_companydocument permission
    """

    if not can_manage_documents(user):
        return False

    if document.is_sensitive:
        return bool(
            user.is_superuser
            or user.has_perm(
                "company_documents.download_sensitive_companydocument"
            )
        )

    return True


# ==========================================================
# AUDIT LOGGING
# ==========================================================

def create_audit(document, user, action, metadata=None):
    """
    Create a company document audit record.

    Kept intentionally compatible with the current
    CompanyDocumentAudit model.
    """

    return CompanyDocumentAudit.objects.create(
        document=document,
        user=user,
        action=action,
        metadata=metadata or {},
    )


# ==========================================================
# CLOUDINARY RAW DOCUMENT HELPERS
# ==========================================================

def upload_raw_document(uploaded_file):
    """
    Upload a document directly to Cloudinary as a RAW resource.

    This intentionally bypasses the FileField storage backend
    because company documents can contain formats such as:

    PDF
    DOC
    DOCX
    XLS
    XLSX
    PPT
    PPTX
    CSV
    TXT
    ZIP
    JPG
    PNG
    WEBP
    etc.
    """

    folder = timezone.now().strftime(
        "company_documents/%Y/%m"
    )

    result = cloudinary.uploader.upload(
        uploaded_file,
        resource_type="raw",
        folder=folder,
        use_filename=True,
        unique_filename=True,
        overwrite=False,
    )

    public_id = result.get("public_id")

    if not public_id:
        raise ValueError(
            "Cloudinary did not return a document public ID."
        )

    return public_id


def delete_raw_document(file_name):
    """
    Delete a RAW document from Cloudinary.

    Fail silently so that deleting a database record is not
    blocked by a Cloudinary cleanup failure.
    """

    if not file_name:
        return

    try:
        cloudinary.uploader.destroy(
            file_name,
            resource_type="raw",
            type="upload",
            invalidate=True,
        )
    except Exception:
        pass


def get_raw_document_url(file_name):
    """
    Generate a secure RAW Cloudinary URL.
    """

    if not file_name:
        raise ValueError("Document does not have a stored file.")

    raw_url, _ = cloudinary_url(
        file_name,
        resource_type="raw",
        type="upload",
        secure=True,
    )

    return raw_url


def download_raw_document(file_name):
    """
    Download RAW document bytes from Cloudinary.
    """

    raw_url = get_raw_document_url(file_name)

    response = requests.get(
        raw_url,
        timeout=60,
    )

    response.raise_for_status()

    return response.content


# ==========================================================
# DOCUMENT LIST
# ==========================================================

@login_required
def document_list(request):
    """
    Company Document Centre.

    Provides:

    - Full-text document search
    - Category filtering
    - Status filtering
    - Expiry filtering
    - Document health filtering
    - Relationship filtering
    - Sensitive-document filtering
    - Health KPIs
    - Pagination
    - Dynamic document folders

    Folder behaviour:

    - Uses the existing CompanyDocument category choices.
    - Automatically discovers categories currently used by documents.
    - Automatically creates a folder card when a category contains
      at least one document.
    - Supports future/new categories without requiring a database
      folder model or migration.
    """

    # ==========================================================
    # PERMISSION
    # ==========================================================

    if not can_manage_documents(request.user):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    # ==========================================================
    # DATE INTELLIGENCE
    # ==========================================================

    today = timezone.localdate()

    thirty_days = today + timezone.timedelta(
        days=30
    )

    sixty_days = today + timezone.timedelta(
        days=60
    )

    ninety_days = today + timezone.timedelta(
        days=90
    )

    # ==========================================================
    # CATEGORY DISPLAY METADATA
    # ==========================================================

    category_meta = {
        "company": {
            "title": "Company & Business",
            "description": (
                "Core company records, policies and business documents."
            ),
            "short": "Company records",
            "icon": "CO",
        },

        "insurance": {
            "title": "Insurance",
            "description": (
                "Insurance policies, certificates and renewal records."
            ),
            "short": "Insurance records",
            "icon": "IN",
        },

        "employee": {
            "title": "Employees",
            "description": (
                "Employee, HR, employment and personnel documents."
            ),
            "short": "Employee records",
            "icon": "EM",
        },

        "whs": {
            "title": "WHS & Safety",
            "description": (
                "Work health, safety, risk, incident and compliance records."
            ),
            "short": "Safety records",
            "icon": "WS",
        },

        "operations": {
            "title": "Operations",
            "description": (
                "Cleaning procedures, checklists, schedules and operational records."
            ),
            "short": "Operations records",
            "icon": "OP",
        },

        "customer": {
            "title": "Customers",
            "description": (
                "Customer, client and service-related documents."
            ),
            "short": "Customer records",
            "icon": "CU",
        },

        "contract": {
            "title": "Contracts",
            "description": (
                "Contracts, agreements, terms and related legal records."
            ),
            "short": "Contracts",
            "icon": "CT",
        },

        "supplier": {
            "title": "Suppliers",
            "description": (
                "Supplier, vendor and procurement documents."
            ),
            "short": "Supplier records",
            "icon": "SU",
        },

        "finance": {
            "title": "Finance",
            "description": (
                "Financial, accounting, tax, invoice and payment records."
            ),
            "short": "Financial records",
            "icon": "FI",
        },

        "training": {
            "title": "Training",
            "description": (
                "Training, competency, qualification and induction records."
            ),
            "short": "Training records",
            "icon": "TR",
        },

        "marketing": {
            "title": "Marketing",
            "description": (
                "Marketing, advertising, brand and promotional documents."
            ),
            "short": "Marketing records",
            "icon": "MK",
        },

        "business_continuity": {
            "title": "Business Continuity",
            "description": (
                "Business continuity, disaster recovery and resilience records."
            ),
            "short": "Continuity records",
            "icon": "BC",
        },

        "quality": {
            "title": "Quality",
            "description": (
                "Quality assurance, audits, inspections and improvement records."
            ),
            "short": "Quality records",
            "icon": "QU",
        },

        "privacy": {
            "title": "Privacy",
            "description": (
                "Privacy, data protection and information management records."
            ),
            "short": "Privacy records",
            "icon": "PR",
        },

        "vehicle": {
            "title": "Vehicles & Fleet",
            "description": (
                "Vehicle, fleet, inspection and registration documents."
            ),
            "short": "Fleet records",
            "icon": "VE",
        },

        "licence": {
            "title": "Licences & Registrations",
            "description": (
                "Licences, registrations, permits and authorisations."
            ),
            "short": "Licensing records",
            "icon": "LI",
        },

        "property": {
            "title": "Property & Premises",
            "description": (
                "Property, premises, site and facility documents."
            ),
            "short": "Property records",
            "icon": "PR",
        },

        "other": {
            "title": "Other / Needs Review",
            "description": (
                "Documents that require review or do not fit another category."
            ),
            "short": "Needs review",
            "icon": "OR",
        },
    }

    # ==========================================================
    # BASE QUERYSET
    # ==========================================================

    documents = (
        CompanyDocument.objects
        .select_related(
            "employee",
            "customer",
            "vehicle",
            "supplier",
            "contract",
            "uploaded_by",
        )
        .all()
    )

    # ==========================================================
    # SEARCH
    # ==========================================================

    query = request.GET.get(
        "q",
        "",
    ).strip()

    if query:
        documents = documents.filter(
            Q(name__icontains=query)
            | Q(document_type__icontains=query)
            | Q(document_reference__icontains=query)
            | Q(description__icontains=query)
            | Q(original_filename__icontains=query)
        )

    # ==========================================================
    # CATEGORY FILTER
    # ==========================================================

    category = request.GET.get(
        "category",
        "",
    ).strip()

    if category:
        documents = documents.filter(
            category=category
        )

    # ==========================================================
    # STATUS FILTER
    # ==========================================================

    status = request.GET.get(
        "status",
        "",
    ).strip()

    if status:
        valid_statuses = {
            value
            for value, label in CompanyDocument.Status.choices
        }

        if status in valid_statuses:
            documents = documents.filter(
                status=status
            )
        else:
            status = ""

    # ==========================================================
    # RELATIONSHIP FILTER
    # ==========================================================

    relationship = request.GET.get(
        "relationship",
        "",
    ).strip().lower()

    valid_relationships = {
        value
        for value, label in CompanyDocument.RelatedType.choices
    }

    if relationship in valid_relationships:
        documents = documents.filter(
            related_type=relationship
        )
    else:
        relationship = ""

    # ==========================================================
    # SENSITIVE FILTER
    # ==========================================================

    sensitive = request.GET.get(
        "sensitive",
        "",
    ).strip().lower()

    if sensitive == "yes":
        documents = documents.filter(
            is_sensitive=True
        )

    elif sensitive == "no":
        documents = documents.filter(
            is_sensitive=False
        )

    else:
        sensitive = ""

    # ==========================================================
    # EXPIRY FILTER
    # ==========================================================

    expiry = request.GET.get(
        "expiry",
        "",
    ).strip()

    if expiry == "expired":

        documents = documents.filter(
            expiry_date__lt=today
        )

    elif expiry == "30":

        documents = documents.filter(
            expiry_date__gte=today,
            expiry_date__lte=thirty_days,
        )

    elif expiry == "60":

        documents = documents.filter(
            expiry_date__gte=today,
            expiry_date__lte=sixty_days,
        )

    elif expiry == "90":

        documents = documents.filter(
            expiry_date__gte=today,
            expiry_date__lte=ninety_days,
        )

    elif expiry == "none":

        documents = documents.filter(
            expiry_date__isnull=True
        )

    # ==========================================================
    # HEALTH FILTER
    # ==========================================================

    health = request.GET.get(
        "health",
        "",
    ).strip().lower()

    if health == "expired":

        documents = documents.filter(
            expiry_date__lt=today,
            status=CompanyDocument.Status.ACTIVE,
        )

    elif health == "expiring":

        documents = documents.filter(
            expiry_date__gte=today,
            expiry_date__lte=thirty_days,
            status=CompanyDocument.Status.ACTIVE,
        )

    elif health == "review":

        documents = documents.filter(
            review_date__lte=today,
            status=CompanyDocument.Status.ACTIVE,
        )

    elif health == "no_expiry":

        documents = documents.filter(
            expiry_date__isnull=True,
            status=CompanyDocument.Status.ACTIVE,
        )

    elif health == "healthy":

        documents = documents.filter(
            status=CompanyDocument.Status.ACTIVE,
        ).filter(
            Q(expiry_date__isnull=True)
            | Q(expiry_date__gt=thirty_days)
        ).filter(
            Q(review_date__isnull=True)
            | Q(review_date__gt=today)
        )

    elif health not in {
        "",
        "expired",
        "expiring",
        "review",
        "no_expiry",
        "healthy",
    }:

        health = ""

    # ==========================================================
    # ORDERING
    # ==========================================================

    documents = documents.order_by(
        "-uploaded_at"
    )

    # ==========================================================
    # PAGINATION
    # ==========================================================

    paginator = Paginator(
        documents,
        15,
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    # ==========================================================
    # GLOBAL KPI DATA
    # ==========================================================

    all_documents = (
        CompanyDocument.objects.all()
    )

    active_documents = all_documents.filter(
        status=CompanyDocument.Status.ACTIVE
    )

    total_documents = all_documents.count()

    active_count = active_documents.count()

    archived_documents = all_documents.filter(
        status=CompanyDocument.Status.ARCHIVED
    ).count()

    # ==========================================================
    # DOCUMENT HEALTH
    # ==========================================================

    expired_documents = active_documents.filter(
        expiry_date__lt=today
    ).count()

    expiring_30_days = active_documents.filter(
        expiry_date__gte=today,
        expiry_date__lte=thirty_days,
    ).count()

    expiring_60_days = active_documents.filter(
        expiry_date__gte=today,
        expiry_date__lte=sixty_days,
    ).count()

    expiring_90_days = active_documents.filter(
        expiry_date__gte=today,
        expiry_date__lte=ninety_days,
    ).count()

    review_due_documents = active_documents.filter(
        review_date__lte=today
    ).count()

    sensitive_documents = active_documents.filter(
        is_sensitive=True
    ).count()

    no_expiry_documents = active_documents.filter(
        expiry_date__isnull=True
    ).count()

    healthy_documents = active_documents.filter(
        expiry_date__gt=thirty_days,
    ).filter(
        Q(review_date__isnull=True)
        | Q(review_date__gt=today)
    ).count()

    # ==========================================================
    # CATEGORY / STATUS / RELATIONSHIP OPTIONS
    # ==========================================================

    categories = CompanyDocument.Category.choices

    statuses = CompanyDocument.Status.choices

    relationships = CompanyDocument.RelatedType.choices

    # ==========================================================
    # DYNAMIC CATEGORY / FOLDER CENTRE
    # ==========================================================

    # Start with categories defined by the model.
    known_categories = list(
        CompanyDocument.Category.choices
    )

    known_category_values = {
        value
        for value, label in known_categories
    }

    # Discover categories actually stored in the database.
    #
    # This means that if the classifier/import system later
    # introduces a new category, the document centre can
    # automatically display it without requiring a folder
    # model or manual folder creation.
    database_categories = (
        CompanyDocument.objects
        .exclude(
            category__isnull=True
        )
        .exclude(
            category=""
        )
        .values_list(
            "category",
            flat=True,
        )
        .distinct()
    )

    # Preserve the model's normal category order and append
    # any categories found in the database that are not
    # currently defined in the model choices.
    category_values = list(
        dict.fromkeys(
            [
                value
                for value, label in known_categories
            ]
            + list(database_categories)
        )
    )

    # ----------------------------------------------------------
    # CATEGORY COUNTS
    # ----------------------------------------------------------

    category_counts = {
        row["category"]: row["total"]
        for row in (
            CompanyDocument.objects
            .values("category")
            .annotate(
                total=Count("id")
            )
        )
    }

    # ----------------------------------------------------------
    # EXPIRED CATEGORY COUNTS
    # ----------------------------------------------------------

    category_expired_counts = {
        row["category"]: row["total"]
        for row in (
            CompanyDocument.objects
            .filter(
                status=CompanyDocument.Status.ACTIVE,
                expiry_date__lt=today,
            )
            .values("category")
            .annotate(
                total=Count("id")
            )
        )
    }

    # ----------------------------------------------------------
    # EXPIRING CATEGORY COUNTS
    # ----------------------------------------------------------

    category_expiring_counts = {
        row["category"]: row["total"]
        for row in (
            CompanyDocument.objects
            .filter(
                status=CompanyDocument.Status.ACTIVE,
                expiry_date__gte=today,
                expiry_date__lte=thirty_days,
            )
            .values("category")
            .annotate(
                total=Count("id")
            )
        )
    }

    # ==========================================================
    # AUTOMATIC CATEGORY DISPLAY HELPERS
    # ==========================================================

    known_labels = dict(
        known_categories
    )

    def category_display_name(value):
        """
        Convert an internal category value into a friendly
        folder name.

        Known categories use their model label.

        Unknown categories are automatically converted from
        values such as:

            risk_management

        into:

            Risk Management
        """

        if value in category_meta:
            return category_meta[value]["title"]

        if value in known_labels:
            return known_labels[value]

        return (
            value
            .replace("_", " ")
            .replace("-", " ")
            .strip()
            .title()
        )

    def category_icon(value):
        """
        Return a compact folder icon code for known
        categories and a safe default for new categories.
        """

        icon_map = {
            "company": "CO",
            "insurance": "IN",
            "employee": "EM",
            "whs": "WS",
            "operations": "OP",
            "customer": "CU",
            "contract": "CT",
            "supplier": "SU",
            "finance": "FI",
            "training": "TR",
            "marketing": "MK",
            "business_continuity": "BC",
            "quality": "QU",
            "privacy": "PR",
            "vehicle": "VE",
            "licence": "LI",
            "property": "PP",
            "other": "OR",
        }

        return icon_map.get(
            value,
            "DO",
        )

    # ==========================================================
    # BUILD FOLDER CARDS
    # ==========================================================

    category_cards = []

    for value in category_values:

        label = category_display_name(
            value
        )

        meta = category_meta.get(
            value,
            {
                "title": label,
                "description": (
                    f"Documents filed under {label}."
                ),
                "short": "Document records",
                "icon": category_icon(
                    value
                ),
            },
        )

        count = category_counts.get(
            value,
            0,
        )

        # Do not display empty folders.
        #
        # The folder automatically appears when the first
        # document is assigned to this category.
        if count <= 0:
            continue

        category_cards.append(
            {
                "value": value,

                "label": meta["title"],

                "description": meta[
                    "description"
                ],

                "short": meta[
                    "short"
                ],

                "icon": meta[
                    "icon"
                ],

                "count": count,

                "expired": category_expired_counts.get(
                    value,
                    0,
                ),

                "expiring": category_expiring_counts.get(
                    value,
                    0,
                ),
            }
        )

    # ==========================================================
    # SORTING
    # ==========================================================

    # Keep the model/category order rather than sorting
    # alphabetically. This creates a predictable document
    # centre layout.
    category_order = {
        value: index
        for index, value in enumerate(
            category_values
        )
    }

    category_cards.sort(
        key=lambda card: category_order.get(
            card["value"],
            9999,
        )
    )

    # ==========================================================
    # CONTEXT
    # ==========================================================

    context = {
        # ------------------------------------------------------
        # Documents
        # ------------------------------------------------------

        "documents": page_obj,

        "page_obj": page_obj,

        "paginator": paginator,

        # ------------------------------------------------------
        # Selected filters
        # ------------------------------------------------------

        "query": query,

        "selected_category": category,

        "selected_status": status,

        "selected_expiry": expiry,

        "selected_health": health,

        "selected_relationship": relationship,

        "selected_sensitive": sensitive,

        # ------------------------------------------------------
        # Filter options
        # ------------------------------------------------------

        "categories": categories,

        "statuses": statuses,

        "relationships": relationships,

        # ------------------------------------------------------
        # Dynamic folder centre
        # ------------------------------------------------------

        "category_cards": category_cards,

        # ------------------------------------------------------
        # Core KPIs
        # ------------------------------------------------------

        "total_documents": total_documents,

        "active_documents": active_count,

        "archived_documents": archived_documents,

        # ------------------------------------------------------
        # Health KPIs
        # ------------------------------------------------------

        "expired_documents": expired_documents,

        "expiring_30_days": expiring_30_days,

        "expiring_60_days": expiring_60_days,

        "expiring_90_days": expiring_90_days,

        "review_due_documents": review_due_documents,

        "sensitive_documents": sensitive_documents,

        "no_expiry_documents": no_expiry_documents,

        "healthy_documents": healthy_documents,

        # ------------------------------------------------------
        # Dates
        # ------------------------------------------------------

        "today": today,

        "thirty_days": thirty_days,

        "sixty_days": sixty_days,

        "ninety_days": ninety_days,
    }

    return render(
        request,
        "dashboard/company_documents/list.html",
        context,
    )



@login_required
def compliance_renewals(request):
    """
    Central renewal queue for company documents.

    Shows active documents that are expired, review-due,
    or expiring within the next 30 days.
    """

    from django.core.paginator import Paginator
    from django.db.models import Case, IntegerField, Q, Value, When

    today = timezone.localdate()
    thirty_days = today + timezone.timedelta(days=30)

    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    category_filter = request.GET.get(
        "category",
        "",
    ).strip()

    documents = (
        CompanyDocument.objects
        .filter(
            status=CompanyDocument.Status.ACTIVE,
        )
        .select_related(
            "employee",
            "customer",
            "vehicle",
            "supplier",
            "contract",
        )
        .filter(
            Q(expiry_date__lt=today)
            | Q(review_date__lte=today)
            | Q(
                expiry_date__gte=today,
                expiry_date__lte=thirty_days,
            )
        )
        .annotate(
            renewal_priority=Case(
                When(
                    expiry_date__lt=today,
                    then=Value(1),
                ),
                When(
                    review_date__lte=today,
                    then=Value(2),
                ),
                When(
                    expiry_date__gte=today,
                    expiry_date__lte=thirty_days,
                    then=Value(3),
                ),
                default=Value(99),
                output_field=IntegerField(),
            )
        )
        .order_by(
            "renewal_priority",
            "expiry_date",
            "review_date",
            "-updated_at",
        )
    )

    if search_query:
        documents = documents.filter(
            Q(name__icontains=search_query)
            | Q(document_type__icontains=search_query)
            | Q(original_filename__icontains=search_query)
            | Q(employee__full_name__icontains=search_query)
            | Q(customer__full_name__icontains=search_query)
            | Q(vehicle__vehicle_name__icontains=search_query)
            | Q(supplier__name__icontains=search_query)
        )

    if category_filter:
        documents = documents.filter(
            category=category_filter,
        )

    total_attention = documents.count()

    expired_count = documents.filter(
        expiry_date__lt=today,
    ).count()

    review_due_count = documents.filter(
        review_date__lte=today,
    ).count()

    expiring_count = documents.filter(
        expiry_date__gte=today,
        expiry_date__lte=thirty_days,
    ).count()

    paginator = Paginator(
        documents,
        25,
    )

    page_number = request.GET.get(
        "page",
        1,
    )

    page_obj = paginator.get_page(
        page_number,
    )

    category_choices = CompanyDocument.Category.choices

    context = {
        "page_obj": page_obj,
        "documents": page_obj.object_list,
        "total_attention": total_attention,
        "expired_count": expired_count,
        "review_due_count": review_due_count,
        "expiring_count": expiring_count,
        "search_query": search_query,
        "category_filter": category_filter,
        "category_choices": category_choices,
        "today": today,
    }

    return render(
        request,
        "dashboard/company_documents/compliance-renewals.html",
        context,
    )



@login_required
def compliance_attention(request):
    """
    Compliance Attention Command Centre.

    Priority order:

        1. Expired
        2. Review due
        3. Expiring within 30 days

    A document can satisfy more than one condition. The highest-priority
    condition is used as the primary compliance issue.

    Documents with no expiry date are not treated as compliance failures.
    They are displayed only as an informational count.
    """

    today = timezone.localdate()
    thirty_days = today + timezone.timedelta(days=30)

    active_documents = (
        CompanyDocument.objects
        .filter(
            status=CompanyDocument.Status.ACTIVE,
        )
        .select_related(
            "employee",
            "customer",
            "vehicle",
            "supplier",
            "contract",
        )
    )

    # --------------------------------------------------------------
    # PRIMARY COMPLIANCE QUEUE
    # --------------------------------------------------------------
    #
    # Priority:
    #   1 = Expired
    #   2 = Review due
    #   3 = Expiring soon
    #
    # A document that is both review-due and expiring soon will therefore
    # be shown primarily as "Review due".
    #
    # A document that is expired and review-due will be shown as "Expired".
    #
    attention_queryset = (
        active_documents
        .filter(
            Q(expiry_date__lt=today)
            | Q(review_date__lte=today)
            | Q(
                expiry_date__gte=today,
                expiry_date__lte=thirty_days,
            )
        )
        .annotate(
            compliance_priority=Case(
                When(
                    expiry_date__lt=today,
                    then=Value(1),
                ),
                When(
                    review_date__lte=today,
                    then=Value(2),
                ),
                When(
                    expiry_date__gte=today,
                    expiry_date__lte=thirty_days,
                    then=Value(3),
                ),
                default=Value(99),
                output_field=IntegerField(),
            )
        )
        .order_by(
            "compliance_priority",
            "expiry_date",
            "review_date",
            "-updated_at",
        )
    )

    # --------------------------------------------------------------
    # KPI COUNTS
    # --------------------------------------------------------------

    expired_documents = active_documents.filter(
        expiry_date__lt=today,
    ).count()

    review_due_documents = active_documents.filter(
        review_date__lte=today,
    ).count()

    expiring_30_days = active_documents.filter(
        expiry_date__gte=today,
        expiry_date__lte=thirty_days,
    ).count()

    no_expiry_documents = active_documents.filter(
        expiry_date__isnull=True,
    ).count()

    active_document_count = active_documents.count()

    attention_documents = attention_queryset.count()

    # --------------------------------------------------------------
    # PRIORITY SUMMARY
    # --------------------------------------------------------------

    if expired_documents:
        attention_level = "critical"
        attention_label = "Immediate action required"
        attention_message = (
            "One or more active documents have expired. "
            "Resolve expired documents before they create operational "
            "or compliance risk."
        )

    elif review_due_documents:
        attention_level = "warning"
        attention_label = "Review required"
        attention_message = (
            "Active documents require compliance review. "
            "Review these records before they become operational issues."
        )

    elif expiring_30_days:
        attention_level = "notice"
        attention_label = "Expiry approaching"
        attention_message = (
            "One or more active documents will expire within the next "
            "30 days. Consider renewing them early."
        )

    else:
        attention_level = "healthy"
        attention_label = "All clear"
        attention_message = (
            "No active documents currently require compliance attention."
        )

    # --------------------------------------------------------------
    # PAGINATION
    # --------------------------------------------------------------

    paginator = Paginator(
        attention_queryset,
        15,
    )

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(
        page_number,
    )

    # --------------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------------

    context = {
        "today": today,
        "thirty_days": thirty_days,

        "documents": page_obj.object_list,

        "paginator": paginator,
        "page_obj": page_obj,

        "attention_documents": attention_documents,

        "expired_documents": expired_documents,
        "review_due_documents": review_due_documents,
        "expiring_30_days": expiring_30_days,
        "no_expiry_documents": no_expiry_documents,

        "active_document_count": active_document_count,

        "attention_level": attention_level,
        "attention_label": attention_label,
        "attention_message": attention_message,
    }

    return render(
        request,
        "dashboard/company_documents/compliance.html",
        context,
    )


@login_required
@require_http_methods(["GET", "POST"])
def bulk_import_upload(request):
    """
    Upload multiple company documents into a staging batch.

    Files are NOT imported into CompanyDocument here.
    They remain staged until reviewed and approved.
    """

    if not can_manage_documents(request.user):
        raise PermissionDenied

    if request.method == "POST":

        files = request.FILES.getlist("files")

        if not files:
            messages.error(
                request,
                "Please select at least one document to upload.",
            )

            return redirect(
                "company_documents:bulk_import_upload"
            )

        try:
            batch = create_batch(
                user=request.user,
                files=files,
            )

            messages.success(
                request,
                f"{len(files)} document(s) uploaded successfully.",
            )

            return redirect(
                "company_documents:bulk_import_review",
                pk=batch.pk,
            )

        except Exception as exc:

            messages.error(
                request,
                f"Bulk upload failed: {exc}",
            )

    return render(
        request,
        "dashboard/company_documents/bulk_import/upload.html",
    )

@login_required
@require_http_methods(["GET"])
def bulk_import_review(request, pk):
    """
    Review a staged bulk-import batch before permanent import.
    """

    if not can_manage_documents(request.user):
        raise PermissionDenied

    batch = get_object_or_404(
        BulkImportBatch.objects
        .select_related("uploaded_by"),
        pk=pk,
    )

    items = (
        batch.items
        .select_related(
            "duplicate_document",
            "imported_document",
            "reviewer",
        )
        .order_by("id")
    )

    paginator = Paginator(items, 15)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    refresh_batch_statistics(batch)

    batch.refresh_from_db()

    context = {
        "batch": batch,
        "page_obj": page_obj,
        "items": page_obj.object_list,

        "ready_count": batch.items.filter(
            status=BulkImportItem.Status.READY
        ).count(),

        "review_count": batch.items.filter(
            status=BulkImportItem.Status.REVIEW
        ).count(),

        "duplicate_count": batch.items.filter(
            status=BulkImportItem.Status.DUPLICATE
        ).count(),

        "approved_count": batch.items.filter(
            status=BulkImportItem.Status.APPROVED
        ).count(),
    }

    return render(
        request,
        "dashboard/company_documents/bulk_import/review.html",
        context,
    )

@login_required
@require_http_methods(["POST"])
def bulk_import_analyse(request, pk):
    """
    Analyse every staged item in a batch.
    """

    if not can_manage_documents(request.user):
        raise PermissionDenied

    batch = get_object_or_404(
        BulkImportBatch,
        pk=pk,
    )

    try:

        analyse_batch(batch)

        refresh_batch_statistics(batch)

        messages.success(
            request,
            "Document analysis completed.",
        )

    except Exception as exc:

        messages.error(
            request,
            f"Document analysis failed: {exc}",
        )

    return redirect(
        "company_documents:bulk_import_review",
        pk=batch.pk,
    )


@login_required
@require_http_methods(["POST"])
def bulk_import_approve(request, pk):
    """
    Approve one staged document for permanent import.
    """

    if not can_manage_documents(request.user):
        raise PermissionDenied

    item = get_object_or_404(
        BulkImportItem.objects.select_related("batch"),
        pk=pk,
    )

    if item.status in {
        BulkImportItem.Status.IMPORTED,
        BulkImportItem.Status.SKIPPED,
        BulkImportItem.Status.DUPLICATE,
    }:
        messages.warning(
            request,
            "This document cannot be approved in its current state.",
        )

        return redirect(
            "company_documents:bulk_import_review",
            pk=item.batch_id,
        )

    item.status = BulkImportItem.Status.APPROVED
    item.reviewer = request.user
    item.reviewed_at = timezone.now()

    item.save(
        update_fields=[
            "status",
            "reviewer",
            "reviewed_at",
        ]
    )

    messages.success(
        request,
        f"{item.original_filename} has been approved.",
    )

    return redirect(
        "company_documents:bulk_import_review",
        pk=item.batch_id,
    )


@login_required
@require_http_methods(["GET", "POST"])
def bulk_import_item_edit(request, pk):
    if not can_manage_documents(request.user):
        raise PermissionDenied

    item = get_object_or_404(
        BulkImportItem.objects.select_related("batch"),
        pk=pk,
    )

    if item.status in {
        BulkImportItem.Status.IMPORTED,
        BulkImportItem.Status.SKIPPED,
    }:
        messages.warning(
            request,
            "This document can no longer be edited.",
        )
        return redirect(
            "company_documents:bulk_import_review",
            pk=item.batch_id,
        )

    if request.method == "POST":

        item.suggested_name = request.POST.get(
            "suggested_name",
            "",
        ).strip()

        item.suggested_category = request.POST.get(
            "suggested_category",
            "",
        ).strip()

        item.suggested_document_type = request.POST.get(
            "suggested_document_type",
            "",
        ).strip()

        item.suggested_description = request.POST.get(
            "suggested_description",
            "",
        ).strip()

        item.suggested_reference = request.POST.get(
            "suggested_reference",
            "",
        ).strip()

        item.suggested_related_type = request.POST.get(
            "suggested_related_type",
            "",
        ).strip()

        item.suggested_issue_date = (
            request.POST.get("suggested_issue_date")
            or None
        )

        item.suggested_expiry_date = (
            request.POST.get("suggested_expiry_date")
            or None
        )

        item.suggested_review_date = (
            request.POST.get("suggested_review_date")
            or None
        )

        item.suggested_sensitive = (
            request.POST.get("suggested_sensitive") == "on"
        )

        item.reviewer = request.user
        item.reviewed_at = timezone.now()

        # A manually reviewed document is ready for approval.
        if item.status not in {
            BulkImportItem.Status.IMPORTED,
            BulkImportItem.Status.DUPLICATE,
        }:
            item.status = BulkImportItem.Status.REVIEW
            item.reviewer = request.user
            item.reviewed_at = timezone.now()
            item.error_message = ""

        item.save(
            update_fields=[
                "suggested_name",
                "suggested_category",
                "suggested_document_type",
                "suggested_description",
                "suggested_reference",
                "suggested_related_type",
                "suggested_issue_date",
                "suggested_expiry_date",
                "suggested_review_date",
                "suggested_sensitive",
                "status",
                "reviewer",
                "reviewed_at",
                "error_message",
            ]
        )

        messages.success(
            request,
            f"{item.original_filename} has been updated.",
        )

        return redirect(
            "company_documents:bulk_import_review",
            pk=item.batch_id,
        )

    return render(
        request,
        "dashboard/company_documents/bulk_import/item_edit.html",
        {
            "item": item,
        },
    )

@login_required
@require_http_methods(["POST"])
def bulk_import_import(request, pk):
    """
    Permanently import approved documents into the
    Company Document Centre.
    """

    if not can_manage_documents(request.user):
        raise PermissionDenied

    batch = get_object_or_404(
        BulkImportBatch,
        pk=pk,
    )

    approved_count = (
        batch.items.filter(
            status=BulkImportItem.Status.APPROVED
        ).count()
    )

    if approved_count == 0:

        messages.warning(
            request,
            "There are no approved documents ready for import.",
        )

        return redirect(
            "company_documents:bulk_import_review",
            pk=batch.pk,
        )

    try:

        result = import_approved_batch(
            batch=batch,
            user=request.user,
        )

        imported_count = result["imported"]
        duplicate_count = result["duplicates"]
        failed_count = result["failed"]

        if imported_count:

            messages.success(
                request,
                (
                    f"{imported_count} document"
                    f"{'s' if imported_count != 1 else ''} "
                    "imported successfully into the "
                    "Company Document Centre."
                ),
            )

        if duplicate_count:

            messages.warning(
                request,
                (
                    f"{duplicate_count} document"
                    f"{'s' if duplicate_count != 1 else ''} "
                    "were blocked as duplicates."
                ),
            )

        if failed_count:

            messages.error(
                request,
                (
                    f"{failed_count} document"
                    f"{'s' if failed_count != 1 else ''} "
                    "failed during import. "
                    "Review the affected items."
                ),
            )

    except Exception as exc:

        messages.error(
            request,
            f"Bulk import failed: {exc}",
        )

    return redirect(
        "company_documents:bulk_import_review",
        pk=batch.pk,
    )



@login_required
@require_http_methods(["GET"])
def bulk_import_list(request):
    """
    Bulk Document Intelligence dashboard.

    Shows previous import batches with pagination.
    """

    if not can_manage_documents(request.user):
        raise PermissionDenied

    query = request.GET.get("q", "").strip()
    requested_status = request.GET.get("status", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    valid_statuses = {
        value
        for value, _label in BulkImportBatch.Status.choices
    }
    status = (
        requested_status
        if requested_status in valid_statuses
        else ""
    )

    parsed_date_from = None
    if date_from:
        try:
            parsed_date_from = date.fromisoformat(date_from)
        except ValueError:
            pass

    parsed_date_to = None
    if date_to:
        try:
            parsed_date_to = date.fromisoformat(date_to)
        except ValueError:
            pass

    batches = (
        BulkImportBatch.objects
        .select_related("uploaded_by")
        .prefetch_related("items")
    )

    if query:
        batches = batches.filter(
            Q(batch_reference__icontains=query)
            | Q(uploaded_by__username__icontains=query)
            | Q(uploaded_by__first_name__icontains=query)
            | Q(uploaded_by__last_name__icontains=query)
        )

    if status:
        batches = batches.filter(status=status)

    if parsed_date_from:
        batches = batches.filter(
            created_at__date__gte=parsed_date_from
        )

    if parsed_date_to:
        batches = batches.filter(
            created_at__date__lte=parsed_date_to
        )

    batches = batches.order_by("-created_at")
    paginator = Paginator(batches, 15)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    pagination_filters = {}
    if query:
        pagination_filters["q"] = query
    if status:
        pagination_filters["status"] = status
    if parsed_date_from:
        pagination_filters["date_from"] = parsed_date_from.isoformat()
    if parsed_date_to:
        pagination_filters["date_to"] = parsed_date_to.isoformat()

    context = {
        "page_obj": page_obj,
        "batches": page_obj.object_list,
        "search_query": query,
        "selected_status": status,
        "selected_status_label": dict(
            BulkImportBatch.Status.choices
        ).get(status, ""),
        "date_from": date_from,
        "date_to": date_to,
        "parsed_date_from": parsed_date_from,
        "parsed_date_to": parsed_date_to,
        "statuses": BulkImportBatch.Status.choices,
        "pagination_query": urlencode(pagination_filters),
    }

    return render(
        request,
        "dashboard/company_documents/bulk_import/list.html",
        context,
    )


@login_required
@require_http_methods(["POST"])
def bulk_import_delete(request, pk):
    if not can_manage_documents(request.user):
        raise PermissionDenied

    batch = get_object_or_404(BulkImportBatch, pk=pk)

    if batch.status in {
        BulkImportBatch.Status.ANALYSING,
        BulkImportBatch.Status.IMPORTING,
    }:
        messages.warning(
            request,
            "This import batch cannot be deleted while it is being processed.",
        )
        return redirect("company_documents:bulk_import_list")

    items = list(batch.items.all())
    for item in items:
        delete_staged_raw_document(item)

    batch_reference = batch.batch_reference
    batch.delete()
    messages.success(
        request,
        f'Import batch "{batch_reference}" was deleted.',
    )
    return redirect("company_documents:bulk_import_list")

# ==========================================================
# UPLOAD
# ==========================================================

@login_required
@require_http_methods(["GET", "POST"])
def document_upload(request):
    """
    Upload a new company document.
    """
    prefill_related_type = request.GET.get(
        "related_type",
        "",
    ).strip()

    prefill_employee_id = request.GET.get(
        "employee",
        "",
    ).strip()

    prefill_document_type = request.GET.get(
        "document_type",
        "",
    ).strip()

    if (
        prefill_related_type == "employee"
        and prefill_employee_id
    ):
        try:
            from employees.models import Employee

            Employee.objects.get(
                pk=prefill_employee_id,
            )
        except (
            Employee.DoesNotExist,
            ValueError,
            TypeError,
        ):
            prefill_employee_id = ""

    if not can_manage_documents(request.user):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    if request.method == "POST":

        form = CompanyDocumentForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            uploaded_file = form.cleaned_data.get(
                "file"
            )

            if not uploaded_file:
                form.add_error(
                    "file",
                    "Please select a document to upload.",
                )
            else:

                max_size = getattr(
                    settings,
                    "COMPANY_DOCUMENT_MAX_SIZE",
                    50 * 1024 * 1024,
                )

                if uploaded_file.size > max_size:
                    form.add_error(
                        "file",
                        "The selected file is larger than "
                        "the maximum allowed size of 50 MB.",
                    )

                else:

                    cloudinary_public_id = None

                    try:
                        # Upload directly to Cloudinary RAW.
                        cloudinary_public_id = (
                            upload_raw_document(
                                uploaded_file
                            )
                        )

                        document = form.save(
                            commit=False
                        )

                        document.file.name = (
                            cloudinary_public_id
                        )

                        document.file._committed = True

                        document.uploaded_by = (
                            request.user
                        )

                        document.original_filename = (
                            uploaded_file.name
                        )

                        document.file_size = (
                            uploaded_file.size
                        )

                        document.mime_type = (
                            uploaded_file.content_type
                            or "application/octet-stream"
                        )

                        document.version = (
                            document.version or 1
                        )

                        document.save()

                        create_audit(
                            document=document,
                            user=request.user,
                            action="uploaded",
                        )

                        messages.success(
                            request,
                            f'"{document.name}" was uploaded successfully.',
                        )

                        return redirect(
                            "company_documents:detail",
                            pk=document.pk,
                        )

                    except Exception as exc:

                        if cloudinary_public_id:
                            delete_raw_document(
                                cloudinary_public_id
                            )

                        form.add_error(
                            "file",
                            (
                                "The document could not be uploaded. "
                                f"Cloudinary returned: {exc}"
                            ),
                        )

    else:

        form = CompanyDocumentForm(
            initial={
                "related_type": prefill_related_type,
                "employee": prefill_employee_id or None,
                "document_type": prefill_document_type,

            }
        )

    context = {
        "form": form,
        "page_title": "Upload document",
        "page_subtitle": (
            "Securely add a document to the company document centre."
        ),
        "is_edit": False,
        "document": None,
    }

    return render(
        request,
        "dashboard/company_documents/form.html",
        context,
    )


# ==========================================================
# EDIT / REPLACE DOCUMENT
# ==========================================================


@login_required
@require_http_methods(["GET", "POST"])
def document_edit(request, pk):
    """
    Edit an existing company document.

    Important:
    - Editing metadata does NOT require a new file.
    - Cloudinary is only contacted when an actual replacement
      file has been uploaded.
    - The existing Cloudinary file is preserved when no file
      is selected.
    """

    if not can_manage_documents(request.user):
        raise Http404

    document = get_object_or_404(
        CompanyDocument,
        pk=pk,
    )

    if request.method == "POST":

        # ---------------------------------------------------------
        # IMPORTANT
        #
        # Check the actual FILES dictionary instead of relying
        # only on form.cleaned_data.
        #
        # If the user did not select a replacement file,
        # this will be None.
        # ---------------------------------------------------------

        replacement_file = request.FILES.get("file")

        form = CompanyDocumentForm(
            request.POST,
            request.FILES,
            instance=document,
        )

        if form.is_valid():

            try:
                # =================================================
                # CASE 1
                # No replacement file
                #
                # Only update database metadata.
                # DO NOT contact Cloudinary.
                # =================================================

                if replacement_file is None:
                    updated_document = form.save(
                        commit=False
                    )

                    # Preserve the existing Cloudinary file.
                    updated_document.file = document.file

                    # Preserve original file metadata.
                    updated_document.original_filename = (
                        document.original_filename
                    )

                    updated_document.file_size = (
                        document.file_size
                    )

                    updated_document.mime_type = (
                        document.mime_type
                    )

                    updated_document.version = (
                        document.version
                    )

                    updated_document.uploaded_by = (
                        document.uploaded_by
                    )

                    updated_document.uploaded_at = (
                        document.uploaded_at
                    )

                    updated_document.save()

                    create_audit(
                        document=updated_document,
                        user=request.user,
                        action="updated",
                    )

                    resolve_document_compliance(
                        updated_document,
                    )

                    messages.success(
                        request,
                        "Document updated successfully.",
                    )

                    return redirect(
                        "company_documents:detail",
                        pk=updated_document.pk,
                    )

                # =================================================
                # CASE 2
                # Replacement file was actually uploaded
                # =================================================

                uploaded_size = getattr(
                    replacement_file,
                    "size",
                    None,
                )

                # Safety check.
                if uploaded_size is None:
                    messages.error(
                        request,
                        "The replacement file could not be "
                        "read. Please select the file again.",
                    )

                    return render(
                        request,
                        "dashboard/company_documents/form.html",
                        {
                            "form": form,
                            "document": document,
                            "is_edit": True,
                        },
                    )

                # -------------------------------------------------
                # Maximum file size
                # -------------------------------------------------

                max_size = getattr(
                    settings,
                    "COMPANY_DOCUMENT_MAX_SIZE",
                    50 * 1024 * 1024,
                )

                if uploaded_size > max_size:
                    messages.error(
                        request,
                        "The selected file is larger than "
                        "the maximum allowed size of 50 MB.",
                    )

                    return render(
                        request,
                        "dashboard/company_documents/form.html",
                        {
                            "form": form,
                            "document": document,
                            "is_edit": True,
                        },
                    )

                # =================================================
                # Upload replacement to Cloudinary
                # =================================================

                new_public_id = upload_raw_document(
                    replacement_file
                )

                if not new_public_id:
                    raise ValueError(
                        "Cloudinary did not return a public ID "
                        "for the replacement file."
                    )

                current_document = CompanyDocument.objects.get(
                    pk=pk,
                )

                previous_document = CompanyDocument.objects.create(
                    name=current_document.name,
                    category=current_document.category,
                    document_type=current_document.document_type,
                    description=current_document.description,
                    document_reference=current_document.document_reference,
                    file=current_document.file.name,
                    original_filename=current_document.original_filename,
                    file_size=current_document.file_size,
                    mime_type=current_document.mime_type,
                    file_hash=current_document.file_hash,
                    issue_date=current_document.issue_date,
                    expiry_date=current_document.expiry_date,
                    review_date=current_document.review_date,
                    is_sensitive=current_document.is_sensitive,
                    status=CompanyDocument.Status.ARCHIVED,
                    related_type=current_document.related_type,
                    employee=current_document.employee,
                    customer=current_document.customer,
                    vehicle=current_document.vehicle,
                    supplier=current_document.supplier,
                    contract=current_document.contract,
                    version=current_document.version or 1,
                    previous_version=current_document.previous_version,
                    uploaded_by=current_document.uploaded_by,
                    archived_at=timezone.now(),
                )

                # -------------------------------------------------
                # Update database object
                # -------------------------------------------------

                updated_document = form.save(
                    commit=False
                )

                updated_document.file.name = new_public_id
                updated_document.file._committed = True

                updated_document.original_filename = (
                    replacement_file.name
                )

                updated_document.file_size = (
                    uploaded_size
                )

                updated_document.mime_type = (
                    getattr(
                        replacement_file,
                        "content_type",
                        None,
                    )
                    or "application/octet-stream"
                )

                updated_document.version = (
                    (current_document.version or 1) + 1
                )

                updated_document.previous_version = (
                    previous_document
                )

                updated_document.save()

                resolve_document_compliance(
                    updated_document,
                )

                # =================================================
                # Audit
                # =================================================

                create_audit(
                    document=updated_document,
                    user=request.user,
                    action="version_replaced",
                )

                messages.success(
                    request,
                    "Document updated successfully and the "
                    "file was replaced.",
                )

                return redirect(
                    "company_documents:detail",
                    pk=updated_document.pk,
                )

            except Exception as exc:
                messages.error(
                    request,
                    f"The document could not be updated. "
                    f"Cloudinary returned: {exc}",
                )

        # ---------------------------------------------------------
        # Form validation failed
        # ---------------------------------------------------------

        return render(
            request,
            "dashboard/company_documents/form.html",
            {
                "form": form,
                "document": document,
                "is_edit": True,
            },
        )

    # =============================================================
    # GET
    # =============================================================

    form = CompanyDocumentForm(
        instance=document
    )

    return render(
        request,
        "dashboard/company_documents/form.html",
        {
            "form": form,
            "document": document,
            "is_edit": True,
        },
    )

# ==========================================================
# DETAIL
# ==========================================================

@login_required
def document_detail(request, pk):
    """
    Display document details and audit history.
    """

    if not can_manage_documents(request.user):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    document = get_object_or_404(
        CompanyDocument.objects.select_related(
            "employee",
            "customer",
            "vehicle",
            "supplier",
            "contract",
            "uploaded_by",
        ),
        pk=pk,
    )

    if not can_access_document(
        request.user,
        document,
    ):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    create_audit(
        document=document,
        user=request.user,
        action="viewed",
    )

    audit_events = (
        document.audit_events
        .select_related("user")
        .order_by("-created_at")[:50]
    )

    compliance_resolution = resolve_document_compliance(
        document,
    )

    context = {
        "document": document,
        "audit_events": audit_events,
        "audits": audit_events,
        "compliance_resolution": compliance_resolution,
        "compliance_results": compliance_resolution["results"],
    }

    return render(
        request,
        "dashboard/company_documents/detail.html",
        context,
    )


# ==========================================================
# DOWNLOAD
# ==========================================================

@login_required
def document_download(request, pk):
    """
    Securely download a company document from Cloudinary RAW.
    """

    if not can_manage_documents(request.user):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    document = get_object_or_404(
        CompanyDocument,
        pk=pk,
    )

    if not can_access_document(
        request.user,
        document,
    ):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    if not document.file:
        raise Http404(
            "This document does not have a stored file."
        )

    try:

        file_content = download_raw_document(
            document.file.name
        )

    except requests.RequestException as exc:

        raise Http404(
            f"Unable to retrieve the document: {exc}"
        )

    except Exception as exc:

        raise Http404(
            f"Unable to retrieve the document: {exc}"
        )

    create_audit(
        document=document,
        user=request.user,
        action="downloaded",
    )

    filename = (
        document.original_filename
        or document.name
        or "document"
    )

    response = FileResponse(
        BytesIO(file_content),
        as_attachment=True,
        filename=filename,
    )

    if document.mime_type:
        response["Content-Type"] = document.mime_type

    response["Content-Length"] = str(
        len(file_content)
    )

    return response


# ==========================================================
# EMAIL DOCUMENT
# ==========================================================

@login_required
@require_http_methods(["GET", "POST"])
def document_email(request, pk):
    """
    Email a company document as an attachment.
    """

    if not can_manage_documents(request.user):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    document = get_object_or_404(
        CompanyDocument,
        pk=pk,
    )

    if not can_access_document(
        request.user,
        document,
    ):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    if request.method == "POST":

        recipient = (
            request.POST.get(
                "recipient",
                "",
            )
            .strip()
        )

        subject = (
            request.POST.get(
                "subject",
                "",
            )
            .strip()
        )

        message = (
            request.POST.get(
                "message",
                "",
            )
            .strip()
        )

        if not recipient:

            messages.error(
                request,
                "Please enter a recipient email address.",
            )

        elif not subject:

            messages.error(
                request,
                "Please enter an email subject.",
            )

        else:

            try:

                # --------------------------------------------------
                # RETRIEVE RAW FILE FROM CLOUDINARY
                # --------------------------------------------------

                file_content = download_raw_document(
                    document.file.name
                )

                attachment_name = (
                    document.original_filename
                    or document.name
                    or "document"
                )

                mime_type = (
                    document.mime_type
                    or "application/octet-stream"
                )

                email = EmailMessage(
                    subject=subject,
                    body=message,
                    from_email=getattr(
                        settings,
                        "DEFAULT_FROM_EMAIL",
                        None,
                    ),
                    to=[recipient],
                )

                email.attach(
                    attachment_name,
                    file_content,
                    mime_type,
                )

                email.send(
                    fail_silently=False
                )

                create_audit(
                    document=document,
                    user=request.user,
                    action="emailed",
                )

                messages.success(
                    request,
                    f'"{document.name}" was emailed successfully to {recipient}.',
                )

                return redirect(
                    "company_documents:detail",
                    pk=document.pk,
                )

            except requests.RequestException as exc:

                messages.error(
                    request,
                    (
                        "Unable to retrieve the document for email: "
                        f"{exc}"
                    ),
                )

            except Exception as exc:

                messages.error(
                    request,
                    (
                        "Unable to send the document email: "
                        f"{exc}"
                    ),
                )

    context = {
        "document": document,
    }

    return render(
        request,
        "dashboard/company_documents/email.html",
        context,
    )


# ==========================================================
# ARCHIVE
# ==========================================================

@login_required
@require_http_methods(["POST"])
def document_archive(request, pk):
    """
    Archive a company document.
    """

    if not can_manage_documents(request.user):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    document = get_object_or_404(
        CompanyDocument,
        pk=pk,
    )

    if not can_access_document(
        request.user,
        document,
    ):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    document.status = (
        CompanyDocument.Status.ARCHIVED
    )

    document.archived_at = timezone.now()

    document.save(
        update_fields=[
            "status",
            "archived_at",
            "updated_at",
        ]
        if hasattr(
            CompanyDocument,
            "updated_at",
        )
        else [
            "status",
            "archived_at",
        ]
    )

    create_audit(
        document=document,
        user=request.user,
        action="archived",
    )

    messages.success(
        request,
        f'"{document.name}" has been archived.',
    )

    return redirect(
        "company_documents:detail",
        pk=document.pk,
    )


# ==========================================================
# DELETE
# ==========================================================

@login_required
@require_http_methods(["POST"])
def document_delete(request, pk):
    """
    Permanently delete a document and attempt to remove
    its Cloudinary RAW file.
    """

    if not can_manage_documents(request.user):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    document = get_object_or_404(
        CompanyDocument,
        pk=pk,
    )

    if not can_access_document(
        request.user,
        document,
    ):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    document_name = document.name

    file_name = (
        document.file.name
        if document.file
        else None
    )

    # Delete the Cloudinary RAW file first.
    delete_raw_document(
        file_name
    )

    # Delete database record.
    document.delete()

    messages.success(
        request,
        f'"{document_name}" was permanently deleted.',
    )

    return redirect(
        "company_documents:list"
    )


@login_required
def compliance_overview(request):
    """
    Compliance Requirements Overview.

    Evaluates configured requirements against existing
    CompanyDocument records and existing business entities.
    """

    report = build_overall_report()

    summary = report["summary"]
    scopes = report["scopes"]

    scope_cards = []

    scope_labels = {
        "company": "Company",
        "employee": "Employees",
        "vehicle": "Vehicles",
        "customer": "Customers",
        "supplier": "Suppliers",
        "contract": "Contracts",
    }

    for scope, label in scope_labels.items():

        scope_report = scopes.get(
            scope,
            [],
        )

        total = 0
        satisfied = 0
        missing = 0
        expired = 0
        review_due = 0
        expiring = 0

        for item in scope_report:

            item_summary = item["summary"]

            total += item_summary["total"]
            satisfied += item_summary["satisfied"]
            missing += item_summary["missing"]
            expired += item_summary["expired"]
            review_due += item_summary["review_due"]
            expiring += item_summary["expiring"]

        percentage = (
            round(
                (
                    satisfied
                    / total
                )
                * 100
            )
            if total
            else None
        )

        scope_cards.append(
            {
                "scope": scope,
                "label": label,
                "total": total,
                "satisfied": satisfied,
                "missing": missing,
                "expired": expired,
                "review_due": review_due,
                "expiring": expiring,
                "percentage": percentage,
                "has_applicable_requirements": bool(total),
            }
        )

    context = {
        "summary": summary,
        "scope_cards": scope_cards,
        "scope_reports": scopes,
    }

    return render(
        request,
        "dashboard/company_documents/compliance_overview.html",
        context,
    )

@login_required
def employee_compliance_profile(request, employee_id):
    """
    Employee-specific compliance command centre.
    """

    from employees.models import Employee

    employee = get_object_or_404(
        Employee,
        pk=employee_id,
    )

    profile = build_employee_compliance_profile(
        employee,
    )

    context = {
        "employee": employee,
        "profile": profile,
        "summary": profile["summary"],
        "results": profile["results"],
        "documents": profile["documents"],
    }

    return render(
        request,
        "dashboard/company_documents/employee_compliance.html",
        context,
    )


@login_required
def employee_compliance_matrix(request):
    """
    Employee compliance matrix.

    Provides a searchable, filterable and paginated overview
    of employee compliance.
    """

    from company_documents.services.employee_compliance_matrix import (
        build_employee_compliance_matrix,
        filter_employee_compliance_matrix,
        summarize_employee_compliance_matrix,
    )

    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    status_filter = request.GET.get(
        "status",
        "",
    ).strip()

    rows = build_employee_compliance_matrix()

    overall_summary = summarize_employee_compliance_matrix(
        rows
    )

    filtered_rows = filter_employee_compliance_matrix(
        rows,
        search_query=search_query,
        status_filter=status_filter,
    )

    paginator = Paginator(
        filtered_rows,
        25,
    )

    page_number = request.GET.get(
        "page",
        1,
    )

    page_obj = paginator.get_page(
        page_number
    )

    context = {
        "page_obj": page_obj,
        "employees": page_obj.object_list,
        "matrix_summary": overall_summary,
        "search_query": search_query,
        "status_filter": status_filter,
    }

    return render(
        request,
        "dashboard/company_documents/employee-compliance-matrix.html",
        context,
    )
