# ==========================================================
# Create Activity Log Entry
# ==========================================================


def create_activity_log(user, action_type, title, description=""):
    ActivityLog.objects.create(
        user=user, action_type=action_type, title=title, description=description
    )

from datetime import timedelta
import csv
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST
from .decorators import admin_required
import logging

from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, transaction
from django.core.mail import EmailMessage,EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import format_html
import requests
from django.http import StreamingHttpResponse
import mimetypes
from urllib.parse import quote as urlquote, urlencode
from django.db.models import Avg, Count, DecimalField, ExpressionWrapper, F, Max, Q, Sum
from django.core.paginator import Paginator
from django.db.models.functions import TruncDate, TruncMonth
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from attendance.models import AttendanceLog
from bookings.forms import BookingForm, BookingWorkOrderFormSet
from bookings.models import Booking
from bookings.services import create_booking, replace_booking_work_orders
from contracts.models import CleaningContract
from customers.forms import CustomerForm, MarketingSignupForm
from customers.models import Customer, MarketingSubscriber
from dashboard.models import CampaignLog, CleaningSupply, Equipment, Vehicle, CareerApplication
from employees.forms import (
    EmployeeCreateForm,
    EmployeeForm,
    PropertyDamageReportReplyForm,
)
from employees.models import Employee, PropertyDamageReport
from employees.damage_report_chat import (
    conversation_response,
    update_report_presence,
)
from employees.services import create_employee_from_form
from expenses.models import Expense
from gallery.forms import GalleryItemForm
from gallery.models import GalleryItem, GalleryImage
from gallery.upload_services import (
    GALLERY_UPLOAD_SESSION_KEY,
    save_gallery_uploads,
    save_verified_gallery_uploads,
)
from google_reviews.calendar_utils import (
    create_or_update_booking_event,
    delete_booking_event,
    delete_roster_event,
)
from invoices.models import Invoice
from invoices.services import get_or_create_invoice_for_booking
from invoices.pdf_utils import generate_invoice_pdf
from leave_management.models import LeaveRequest
from notifications.models import Notification
from notifications.utils import notify_user
from payroll.models import PayrollRecord
from quotes.models import QuoteRequest
from quotes.services import convert_quote_to_booking as convert_quote_service
from reviews.forms import ReviewForm
from reviews.models import Review
from rosters.models import Roster
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from core.models import FAQQuestion
from core.forms import FAQSubmissionForm
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from google_reviews.calendar_utils import create_or_update_booking_event
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.utils import timezone

logger = logging.getLogger(__name__)


def _lock_booking_mutations(failure_route):
    def decorate(view):
        @wraps(view)
        def wrapped(request, booking_id, *args, **kwargs):
            from rosters.services import (
                RosterSyncLockError,
                booking_roster_sync_lock,
            )

            try:
                get_object_or_404(Booking, pk=booking_id)
                with booking_roster_sync_lock(booking_id):
                    get_object_or_404(
                        Booking.objects.select_for_update(),
                        pk=booking_id,
                    )
                    return view(request, booking_id, *args, **kwargs)
            except (DatabaseError, RosterSyncLockError):
                logger.exception(
                    "Could not safely serialize booking mutation for booking %s.",
                    booking_id,
                )
                messages.error(
                    request,
                    "The booking could not be safely updated right now. Please retry.",
                )
                return redirect(failure_route)

        return wrapped

    return decorate


# Company settings form
from .forms import (
    CampaignLogForm,
    CompanySettingsForm,
    MarketingSubscriberForm,
)

from .models import (
    ActivityLog,
    CompanySettings,
    EmailLog,
    PurchaseOrder,
    ReviewRequestLog,
)

from analytics.models import (
    ActivityEvent,
    SearchEvent,
    Visitor,
    VisitorSession,
)


@login_required
def dashboard_home(request):
    today = timezone.now().date()
    week_start = today - timedelta(days=7)
    overdue_date = today - timedelta(days=2)
    month_start = today.replace(day=1)
    next_month_start = (
        month_start.replace(year=month_start.year + 1, month=1)
        if month_start.month == 12
        else month_start.replace(month=month_start.month + 1)
    )

    vehicle_metrics = Vehicle.objects.aggregate(
        active=Count("pk", filter=Q(status="active")),
        insurance_alerts=Count("pk", filter=Q(insurance_expiry__lt=today)),
        registration_alerts=Count("pk", filter=Q(registration_expiry__lt=today)),
        service_alerts=Count("pk", filter=Q(service_due_date__lt=today)),
        insurance_expiring=Count(
            "pk",
            filter=Q(insurance_expiry__gte=today, insurance_expiry__lte=today + timedelta(days=30)),
        ),
        service_due=Count(
            "pk",
            filter=Q(service_due_date__gte=today, service_due_date__lte=today + timedelta(days=30)),
        ),
    )
    active_vehicles = vehicle_metrics["active"]
    vehicle_alerts = sum(
        vehicle_metrics[key]
        for key in ("insurance_alerts", "registration_alerts", "service_alerts")
    )
    insurance_expiring = vehicle_metrics["insurance_expiring"]
    service_due = vehicle_metrics["service_due"]

    equipment_metrics = Equipment.objects.aggregate(
        overdue=Count("pk", filter=Q(next_service_date__lt=today)),
        due_today=Count("pk", filter=Q(next_service_date=today)),
        active=Count("pk", filter=~Q(condition="retired")),
        total_value=Sum("purchase_cost"),
    )
    overdue_equipment = equipment_metrics["overdue"]
    due_today_equipment = equipment_metrics["due_today"]
    active_equipment = equipment_metrics["active"]
    total_equipment_value = equipment_metrics["total_value"] or 0

    supply_metrics = CleaningSupply.objects.aggregate(
        low_stock=Count("pk", filter=Q(current_stock__lte=F("minimum_stock"))),
        total=Count("pk"),
        total_value=Sum(
            ExpressionWrapper(
                F("current_stock") * F("unit_cost"),
                output_field=DecimalField(max_digits=20, decimal_places=2),
            )
        ),
    )
    low_stock_supplies = supply_metrics["low_stock"]
    total_supplies = supply_metrics["total"]
    total_supplies_value = supply_metrics["total_value"] or 0

    quote_metrics = QuoteRequest.objects.aggregate(
        total=Count("pk"),
        today=Count("pk", filter=Q(created_at__date=today)),
        week=Count("pk", filter=Q(created_at__date__gte=week_start)),
        month=Count("pk", filter=Q(created_at__date__gte=month_start)),
        new=Count("pk", filter=Q(status="new")),
        contacted=Count("pk", filter=Q(status="contacted")),
        quoted=Count("pk", filter=Q(status="quoted")),
        booked=Count("pk", filter=Q(status="booked")),
        completed=Count("pk", filter=Q(status="completed")),
        lost=Count("pk", filter=Q(status="lost")),
    )
    total_quotes = quote_metrics["total"]
    today_quotes = quote_metrics["today"]
    week_quotes = quote_metrics["week"]
    month_quotes = quote_metrics["month"]
    new_quotes = quote_metrics["new"]
    contacted_quotes = quote_metrics["contacted"]
    quoted_quotes = quote_metrics["quoted"]
    booked_quotes = quote_metrics["booked"]
    completed_quotes = quote_metrics["completed"]
    lost_quotes = quote_metrics["lost"]

    booking_metrics = Booking.objects.aggregate(
        total=Count("pk"),
        today=Count("pk", filter=Q(booking_date=today)),
        upcoming=Count("pk", filter=Q(booking_date__gte=today) & ~Q(status="cancelled")),
        pending=Count("pk", filter=Q(status="pending")),
        confirmed=Count("pk", filter=Q(status="confirmed")),
        assigned=Count("pk", filter=Q(status="assigned")),
        in_progress=Count("pk", filter=Q(status="in_progress")),
        completed=Count("pk", filter=Q(status="completed")),
        cancelled=Count("pk", filter=Q(status="cancelled")),
        revenue=Sum("quoted_price", filter=Q(status="completed")),
    )
    total_bookings = booking_metrics["total"]
    today_bookings = booking_metrics["today"]
    upcoming_bookings = booking_metrics["upcoming"]
    pending_bookings = booking_metrics["pending"]
    confirmed_bookings = booking_metrics["confirmed"]
    assigned_bookings = booking_metrics["assigned"]
    in_progress_bookings = booking_metrics["in_progress"]
    completed_bookings = booking_metrics["completed"]
    cancelled_bookings = booking_metrics["cancelled"]
    booking_revenue = booking_metrics["revenue"] or 0

    employee_metrics = Employee.objects.aggregate(
        total=Count("pk"),
        active_total=Count("pk", filter=Q(active=True)),
        available_total=Count("pk", filter=Q(active=True, availability="available")),
    )

    unassigned_jobs = (
        Booking.objects.filter(assigned_employee__isnull=True, booking_date__gte=today)
        .exclude(status="cancelled")
        .order_by("booking_date", "booking_time")[:10]
    )

    urgent_jobs_today = (
        Booking.objects.filter(booking_date=today)
        .exclude(status="cancelled")
        .order_by("booking_time")[:10]
    )

    overdue_leads = QuoteRequest.objects.filter(
        status__in=["new", "contacted", "quoted"], created_at__date__lte=overdue_date
    ).order_by("created_at")[:10]

    upcoming_jobs = (
        Booking.objects.filter(booking_date__gte=today)
        .exclude(status="cancelled")
        .order_by("booking_date", "booking_time")[:10]
    )

    employee_workload = (
        Booking.objects.filter(assigned_employee__isnull=False, booking_date__gte=today)
        .exclude(status="cancelled")
        .values("assigned_employee__full_name")
        .annotate(total=Count("id"))
        .order_by("-total")[:8]
    )

    property_type_data = (
        QuoteRequest.objects.values("property_type")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    quote_trend_data = (
        QuoteRequest.objects.filter(created_at__date__gte=week_start)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Count("id"))
        .order_by("day")
    )

    booking_trend_data = (
        Booking.objects.filter(created_at__date__gte=week_start)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Count("id"))
        .order_by("day")
    )

    revenue_trend_data = (
        Booking.objects.filter(status="completed", booking_date__gte=week_start)
        .values("booking_date")
        .annotate(total=Sum("quoted_price"))
        .order_by("booking_date")
    )

    action_alert_count = (
        len(unassigned_jobs)
        + len(urgent_jobs_today)
        + len(overdue_leads)
        + pending_bookings
    )
    recent_activity = ActivityLog.objects.select_related("user").all()[:10]
    context = {
        "recent_activity": recent_activity,
        "total_quotes": total_quotes,
        "today_quotes": today_quotes,
        "week_quotes": week_quotes,
        "month_quotes": month_quotes,
        "new_quotes": new_quotes,
        "contacted_quotes": contacted_quotes,
        "quoted_quotes": quoted_quotes,
        "booked_quotes": booked_quotes,
        "completed_quotes": completed_quotes,
        "lost_quotes": lost_quotes,
        "gallery_count": GalleryItem.objects.count(),
        "reviews_count": Review.objects.count(),
        "customer_count": Customer.objects.count(),
        "employee_count": employee_metrics["total"],
        "available_employees": employee_metrics["available_total"],
        "active_employees": employee_metrics["active_total"],
        "total_bookings": total_bookings,
        "today_bookings": today_bookings,
        "upcoming_bookings": upcoming_bookings,
        "completed_bookings": completed_bookings,
        "booking_revenue": booking_revenue,
        "pending_bookings": pending_bookings,
        "confirmed_bookings": confirmed_bookings,
        "assigned_bookings": assigned_bookings,
        "in_progress_bookings": in_progress_bookings,
        "cancelled_bookings": cancelled_bookings,
        "overdue_equipment": overdue_equipment,
        "due_today_equipment": due_today_equipment,
        "active_equipment": active_equipment,
        "total_equipment_value": total_equipment_value,
        "low_stock_supplies": low_stock_supplies,
        "total_supplies": total_supplies,
        "total_supplies_value": total_supplies_value,
        "recent_quotes": QuoteRequest.objects.order_by("-created_at")[:15],
        "recent_customers": Customer.objects.order_by("-created_at")[:5],
        "recent_employees": Employee.objects.order_by("-created_at")[:5],
        "upcoming_jobs": upcoming_jobs,
        "urgent_jobs_today": urgent_jobs_today,
        "unassigned_jobs": unassigned_jobs,
        "overdue_leads": overdue_leads,
        "employee_workload": employee_workload,
        "action_alert_count": action_alert_count,
        "active_vehicles": active_vehicles,
        "vehicle_alerts": vehicle_alerts,
        "insurance_expiring": insurance_expiring,
        "service_due": service_due,
        "property_type_labels": [item["property_type"] for item in property_type_data],
        "property_type_counts": [item["total"] for item in property_type_data],
        "quote_trend_labels": [
            item["day"].strftime("%d %b") for item in quote_trend_data
        ],
        "quote_trend_counts": [item["total"] for item in quote_trend_data],
        "booking_trend_labels": [
            item["day"].strftime("%d %b") for item in booking_trend_data
        ],
        "booking_trend_counts": [item["total"] for item in booking_trend_data],
        "revenue_trend_labels": [
            item["booking_date"].strftime("%d %b") for item in revenue_trend_data
        ],
        "revenue_trend_counts": [
            float(item["total"] or 0) for item in revenue_trend_data
        ],
    }

    return render(request, "dashboard.html", context)


@admin_required
def careers_list(request):
    """Dashboard view listing career applications."""
    applications = CareerApplication.objects.all().order_by("-created_at")

    # Filtering
    status = request.GET.get("status")
    position = request.GET.get("position")
    q = request.GET.get("q")

    if status:
        applications = applications.filter(status=status)
    if position:
        applications = applications.filter(position=position)

    if q:
        applications = applications.filter(
            Q(full_name__icontains=q)
            | Q(email__icontains=q)
            | Q(phone__icontains=q)
            | Q(suburb__icontains=q)
        )

    context = {"applications": applications, "filter_status": status, "filter_position": position, "q": q}
    return render(request, "dashboard/careers_list.html", context)

@admin_required
def career_detail(request, application_id):
    application = get_object_or_404(CareerApplication, id=application_id)

    if request.method == "POST":
        # allow updating status/admin notes from dashboard
        status = request.POST.get("status")
        admin_notes = request.POST.get("admin_notes", "")
        if not request.user.is_staff and not request.user.is_superuser:
            messages.error(request, "Permission denied.")
            return redirect("career_detail", application_id=application.id)

        old_status = application.status

        if status and status in dict(CareerApplication.STATUS_CHOICES):
            application.status = status
        application.admin_notes = admin_notes
        application.save()

        # Send status update email to applicant and record it in EmailLog
        logger = logging.getLogger(__name__)
        try:
            subject = f"YD Commercial Cleaning — Application Update: {application.get_position_display()}"
            context = {"application": application, "admin_notes": admin_notes}
            text = render_to_string("emails/application_update.txt", context)
            html = render_to_string("emails/application_update.html", context)

            # send email (raise on failure) and log it
            send_mail(
                subject,
                text,
                settings.DEFAULT_FROM_EMAIL,
                [application.email],
                fail_silently=False,
                html_message=html,
            )

            try:
                EmailLog.objects.create(
                    sent_by=request.user,
                    email_type="system",
                    recipient_name=application.full_name or application.email,
                    recipient_email=application.email,
                    subject=subject,
                    related_object=f"CareerApplication #{application.id}",
                )
            except Exception:
                logger.exception("Failed to create EmailLog for application update")

            messages.success(request, "✅ Application updated and applicant notified.")

        except Exception:
            logger.exception("Failed to send application update email to %s", application.email)
            messages.warning(request, "⚠️ Application updated but failed to notify applicant by email.")
        return redirect("career_detail", application_id=application.id)

    return render(request, "dashboard/career_detail.html", {"application": application})


@admin_required
def download_resume(request, application_id):
    """Proxy download for resume to ensure proper headers and filename.

    Streams the file from the storage URL and returns a download response
    with a sensible filename so Cloudinary URL quirks don't break downloads.
    """
    application = get_object_or_404(CareerApplication, id=application_id)
    if not application.resume:
        return redirect("career_detail", application_id=application.id)

    file_url = application.resume.url

    # Derive filename from stored name if possible
    filename = getattr(application.resume, 'name', None) or f"resume-{application.id}"
    # Ensure we have a filename only, not a full path
    filename = filename.split('/')[-1]
    # If filename has no extension, try to infer from content-type later
    try:
        r = requests.get(file_url, stream=True, timeout=10)
        r.raise_for_status()
    except Exception:
        # If proxying fails, fall back to redirecting the browser to the
        # direct storage URL (Cloudinary). This avoids silently returning
        # the detail page and lets the browser attempt the download/preview.
        return redirect(file_url)

    content_type = r.headers.get('Content-Type') or mimetypes.guess_type(filename)[0] or 'application/octet-stream'

    # If filename missing extension, try to append based on content type
    if '.' not in filename:
        ext = mimetypes.guess_extension(content_type) or ''
        if ext:
            filename = filename + ext

    response = StreamingHttpResponse(r.iter_content(chunk_size=8192), content_type=content_type)
    response['Content-Length'] = r.headers.get('Content-Length', '')
    response['Content-Disposition'] = f'attachment; filename="{urlquote(filename)}"'
    return response


@admin_required
def preview_resume(request, application_id):
    """Stream the resume for inline preview (PDFs/images) when possible.

    If proxying fails, redirect to the storage URL so the browser can attempt
    to render the file directly.
    """
    application = get_object_or_404(CareerApplication, id=application_id)
    if not application.resume:
        return redirect("career_detail", application_id=application.id)

    file_url = application.resume.url
    filename = getattr(application.resume, 'name', None) or f"resume-{application.id}"
    filename = filename.split('/')[-1]

    try:
        r = requests.get(file_url, stream=True, timeout=10)
        r.raise_for_status()
    except Exception:
        return redirect(file_url)

    content_type = r.headers.get('Content-Type') or mimetypes.guess_type(filename)[0] or 'application/octet-stream'

    # For preview, prefer inline disposition so browsers render PDFs/images
    disposition = 'inline'

    # If content-type is not previewable, fall back to attachment
    previewable = content_type.startswith('application/pdf') or content_type.startswith('image/')
    if not previewable:
        disposition = 'attachment'

    response = StreamingHttpResponse(r.iter_content(chunk_size=8192), content_type=content_type)
    response['Content-Length'] = r.headers.get('Content-Length', '')
    response['Content-Disposition'] = f'{disposition}; filename="{urlquote(filename)}"'
    return response


@login_required
def lead_list(request):
    all_quotes = QuoteRequest.objects.all()
    status = request.GET.get("status", "").strip()
    property_type = request.GET.get("property_type", "").strip()
    lead_source = request.GET.get("lead_source", "").strip()
    search = request.GET.get("q", "").strip()[:100]
    date_from_raw = request.GET.get("date_from", "").strip()
    date_to_raw = request.GET.get("date_to", "").strip()
    date_from = parse_date(date_from_raw) if date_from_raw else None
    date_to = parse_date(date_to_raw) if date_to_raw else None
    sort = request.GET.get("sort", "newest").strip()
    page_size = request.GET.get("page_size", "25").strip()

    filter_form = {
        "status": status if status in dict(QuoteRequest.STATUS_CHOICES) else "",
        "property_type": (
            property_type
            if property_type in dict(QuoteRequest.PROPERTY_TYPES)
            else ""
        ),
        "lead_source": (
            lead_source
            if lead_source in dict(QuoteRequest.LEAD_SOURCE_CHOICES)
            else ""
        ),
        "q": search,
        "date_from": date_from.isoformat() if date_from else "",
        "date_to": date_to.isoformat() if date_to else "",
        "sort": sort
        if sort in {"newest", "oldest", "preferred_date", "estimate_high", "estimate_low"}
        else "newest",
        "page_size": page_size if page_size in {"10", "25", "50"} else "25",
    }

    quotes = all_quotes
    if filter_form["status"]:
        quotes = quotes.filter(status=filter_form["status"])
    if filter_form["property_type"]:
        quotes = quotes.filter(property_type=filter_form["property_type"])
    if filter_form["lead_source"]:
        quotes = quotes.filter(lead_source=filter_form["lead_source"])
    if search:
        quotes = quotes.filter(
            Q(name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
            | Q(suburb_postcode__icontains=search)
            | Q(message__icontains=search)
        )
    if date_from:
        quotes = quotes.filter(created_at__date__gte=date_from)
    if date_to:
        quotes = quotes.filter(created_at__date__lte=date_to)

    ordering = {
        "newest": ("-created_at", "-pk"),
        "oldest": ("created_at", "pk"),
        "preferred_date": ("preferred_date", "-created_at"),
        "estimate_high": ("-estimated_price", "-created_at"),
        "estimate_low": ("estimated_price", "-created_at"),
    }
    quotes = quotes.prefetch_related("images").order_by(
        *ordering[filter_form["sort"]]
    )
    paginator = Paginator(quotes, int(filter_form["page_size"]))
    page_obj = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)
    pagination_query = urlencode(query_params, doseq=True)

    return render(
        request,
        "dashboard/leads/lead_list.html",
        {
            "quotes": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "filter_form": filter_form,
            "pagination_query": pagination_query,
            "filtered_count": paginator.count,
            "total_count": all_quotes.count(),
            "new_count": all_quotes.filter(status="new").count(),
            "booked_count": all_quotes.filter(status="booked").count(),
            "lost_count": all_quotes.filter(status="lost").count(),
            "status_choices": QuoteRequest.STATUS_CHOICES,
            "property_type_choices": [
                choice
                for choice in QuoteRequest.PROPERTY_TYPES
                if choice[0]
            ],
            "lead_source_choices": QuoteRequest.LEAD_SOURCE_CHOICES,
        },
    )


@login_required
@require_POST
@permission_required("quotes.delete_quoterequest", raise_exception=True)
def delete_quote_request(request, quote_id):
    quote = get_object_or_404(QuoteRequest, pk=quote_id)
    quote_name = quote.name
    quote.delete()

    messages.success(request, f'Quote request for "{quote_name}" was deleted.')
    return redirect("lead_list")


@login_required
@require_POST
@permission_required(
    ("quotes.change_quoterequest", "bookings.add_booking"),
    raise_exception=True,
)
def update_quote_status(request, quote_id):
    quote = get_object_or_404(QuoteRequest, id=quote_id)

    if request.method != "POST":
        return redirect("lead_list")

    new_status = request.POST.get("status")
    admin_notes = request.POST.get("admin_notes", "")

    if new_status not in dict(QuoteRequest.STATUS_CHOICES):
        messages.error(request, "Invalid quote status.")
        return redirect("lead_list")

    if new_status == "completed":
        linked_booking = Booking.objects.filter(
            idempotency_key=f"quote:{quote.pk}"
        ).first()
        if not linked_booking or linked_booking.status != "completed":
            messages.error(
                request,
                "A quote can only be marked completed after its linked job is completed.",
            )
            return redirect("lead_list")

    # ------------------------------------------------------
    # QUOTE → BOOKING
    # ------------------------------------------------------
    # Do NOT save the quote as "booked" before conversion.
    # The conversion service creates/reuses the Booking first
    # and then marks the quote as booked.
    # ------------------------------------------------------
    if new_status == "booked":

        try:
            booking, created = convert_quote_service(
                quote_id=quote.id,
                booking_date=quote.preferred_date or timezone.localdate(),
                booking_time=time(9, 0),
            )

            # Save admin notes after successful conversion.
            if quote.admin_notes != admin_notes:
                quote.admin_notes = admin_notes
                quote.save(update_fields=["admin_notes"])

            # --------------------------------------------------
            # GOOGLE CALENDAR
            # --------------------------------------------------
            try:
                create_or_update_booking_event(booking)

            except Exception:
                logger.exception(
                    "Google Calendar sync failed after quote conversion for booking %s.",
                    booking.pk,
                )
                messages.warning(
                    request,
                    (
                        f"Booking #{booking.id} created successfully, "
                        "but Google Calendar could not be synced automatically."
                    ),
                )

            # --------------------------------------------------
            # SUCCESS MESSAGE
            # --------------------------------------------------
            if created:
                messages.success(
                    request,
                    (
                        f"Quote booked successfully. "
                        f"Booking #{booking.id} created."
                    ),
                )
            else:
                messages.success(
                    request,
                    (
                        f"Quote is already linked to "
                        f"Booking #{booking.id}."
                    ),
                )

            return redirect("booking_list")

        except Exception:
            logger.exception("Quote-to-booking status update failed for quote %s.", quote.id)
            messages.error(
                request,
                "The quote could not be converted to a booking. Please check its details or contact an administrator.",
            )

            return redirect("lead_list")

    # ------------------------------------------------------
    # OTHER QUOTE STATUS CHANGES
    # ------------------------------------------------------
    quote.status = new_status
    quote.admin_notes = admin_notes
    quote.save()

    messages.success(
        request,
        f"Quote status updated to {quote.get_status_display()}."
    )

    return redirect("lead_list")

@login_required
def customer_list(request):
    customers = Customer.objects.select_related("user").all().order_by("-created_at")
    customer_totals = customers.aggregate(
        total_revenue=Sum("total_revenue"),
        jobs_completed=Sum("jobs_completed"),
    )
    return render(
        request,
        "customers/customer_list.html",
        {
            "customers": customers,
            "customer_count": customers.count(),
            "linked_customer_count": customers.filter(user__isnull=False).count(),
            "unlinked_customer_count": customers.filter(user__isnull=True).count(),
            "customer_revenue_total": customer_totals["total_revenue"] or 0,
            "customer_jobs_total": customer_totals["jobs_completed"] or 0,
        },
    )


@login_required
def faq_question_list(request):
    q = request.GET.get("q", "").strip()
    questions_qs = FAQQuestion.objects.order_by("-created_at")
    if q:
        questions_qs = questions_qs.filter(
            Q(question__icontains=q) | Q(name__icontains=q) | Q(email__icontains=q)
        )

    paginator = Paginator(questions_qs, 20)
    page = request.GET.get("page")
    page_obj = paginator.get_page(page)

    context = {"questions": page_obj.object_list, "page_obj": page_obj, "q": q}
    return render(request, "dashboard/faq_questions.html", context)


@login_required
def faq_question_reply(request, question_id):
    q = get_object_or_404(FAQQuestion, id=question_id)
    if request.method == "POST":
        answer = request.POST.get("answer", "").strip()
        publish = request.POST.get("publish") == "1"
        notify = request.POST.get("notify") == "1"

        if publish and not answer:
            messages.error(request, "❌ Please enter an answer before publishing.")
            return render(request, "dashboard/faq_reply.html", {"question": q})

        q.answer = answer
        q.answered_by = request.user
        q.answered_at = timezone.now()
        q.is_published = publish and bool(answer)
        q.save()

        if notify and q.email:
            logger = logging.getLogger(__name__)
            try:
                subject = f"Answer to your question on {settings.SITE_URL}"
                message = (
                    f"Hi {q.name or ''},\n\nYour question:\n{q.question}\n\nOur answer:\n{q.answer}\n\nThanks,\nYD Commercial Cleaning Team"
                )
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [q.email], fail_silently=False)
                messages.success(request, "✅ Reply saved and applicant notified by email.")
            except Exception:
                logger.exception("Failed to send FAQ reply email to %s", q.email)
                messages.warning(request, "⚠️ Reply saved but failed to send notification email.")
        else:
            if publish:
                messages.success(request, "✅ Reply saved and published.")
            else:
                messages.success(request, "✅ Reply saved as draft.")
        return redirect("faq_question_list")

    return render(request, "dashboard/faq_reply.html", {"question": q})


@admin_required
def add_customer(request):
    if request.method == "POST":
        form = CustomerForm(request.POST)

        if form.is_valid():
            customer = form.save()

            # Save activity log when a customer is created.
            create_activity_log(
                request.user,
                "customer",
                "Customer Added",
                f"{customer.full_name} was added to the CRM.",
            )

            messages.success(request, "✅ Customer added successfully.")
            return redirect("customer_list")

        messages.error(request, "❌ Please check the customer form.")
    else:
        form = CustomerForm()

    return render(
        request,
        "customers/customer_form.html",
        {
            "form": form,
            "page_title": "Add Customer",
            "button_text": "Save Customer",
        },
    )


@admin_required
def edit_customer(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)

    if request.method == "POST":
        form = CustomerForm(request.POST, instance=customer)

        if form.is_valid():
            updated_customer = form.save()

            # Save activity log when customer details are updated.
            create_activity_log(
                request.user,
                "customer",
                "Customer Updated",
                f"{updated_customer.full_name}'s details were updated.",
            )

            messages.success(request, "✅ Customer updated successfully.")
            return redirect("customer_list")

        messages.error(request, "❌ Please check the customer form.")
    else:
        form = CustomerForm(instance=customer)

    return render(
        request,
        "customers/customer_form.html",
        {
            "form": form,
            "page_title": "Edit Customer",
            "button_text": "Update Customer",
        },
    )


@require_POST
@admin_required
def delete_customer(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)

    customer_name = customer.full_name

    if request.method == "POST":
        customer.delete()

        # Save activity log when a customer is deleted.
        create_activity_log(
            request.user,
            "customer",
            "Customer Deleted",
            f"{customer_name} was removed from the CRM.",
        )

        messages.success(request, "✅ Customer deleted successfully.")
        return redirect("customer_list")

    return render(
        request,
        "shared/confirm_delete.html",
        {
            "object_name": customer.full_name,
            "cancel_url": "/dashboard/customers/",
        },
    )


@login_required
def booking_list(request):
    from rosters.models import Roster

    bookings = (
        Booking.objects
        .select_related("customer", "assigned_employee")
        .prefetch_related("rosters", "work_orders")
        .all()
        .order_by("-booking_date", "-booking_time")
    )

    return render(
        request,
        "bookings/booking_list.html",
        {
            "bookings": bookings,
        },
    )

@admin_required
def add_booking(request):
    work_order_prefix = "work_orders"
    if request.method == "POST":
        form = BookingForm(request.POST)
        if f"{work_order_prefix}-TOTAL_FORMS" in request.POST:
            work_order_formset = BookingWorkOrderFormSet(
                request.POST,
                prefix=work_order_prefix,
            )
        else:
            work_order_formset = BookingWorkOrderFormSet(
                prefix=work_order_prefix
            )

        if form.is_valid():
            if work_order_formset is None:
                work_orders = [
                    {
                        "service_type": form.cleaned_data["service_type"],
                        "price": form.cleaned_data["quoted_price"],
                    }
                ]
            elif work_order_formset.is_valid():
                work_orders = [
                    {
                        "service_type": item["service_type"],
                        "price": item["price"],
                    }
                    for item in work_order_formset.cleaned_data
                    if item
                    and item.get("service_type")
                    and not item.get("DELETE")
                ]
            else:
                work_orders = []

            if work_orders:
                booking, _ = create_booking(
                    customer=form.cleaned_data.get("customer"),
                    service_type=work_orders[0]["service_type"],
                    booking_date=form.cleaned_data["booking_date"],
                    booking_time=form.cleaned_data["booking_time"],
                    address=form.cleaned_data["address"],
                    suburb_postcode=form.cleaned_data["suburb_postcode"],
                    quoted_price=sum(
                        (item["price"] for item in work_orders),
                        Decimal("0.00"),
                    ),
                    assigned_employee=form.cleaned_data.get("assigned_employee"),
                    notes=form.cleaned_data.get("notes", ""),
                    trusted_assignment=True,
                    work_orders=work_orders,
                )
            else:
                booking = None

            if booking:
                return _finish_new_booking(request, booking)

    else:
        form = BookingForm()
        work_order_formset = BookingWorkOrderFormSet(prefix=work_order_prefix)

    return render(
        request,
        "bookings/booking_form.html",
        {
            "form": form,
            "work_order_formset": work_order_formset,
            "page_title": "Add New Booking",
            "button_text": "Save Booking",
        },
    )


def _finish_new_booking(request, booking):
    roster_sync_succeeded = True
    try:
        from rosters.services import (
            RosterSyncNotConfigured,
            RosterSyncPending,
            sync_booking_roster,
        )

        roster_sync = sync_booking_roster(booking)
        if isinstance(roster_sync, RosterSyncPending):
            raise roster_sync.error
        if isinstance(roster_sync, RosterSyncNotConfigured):
            messages.info(
                request,
                "Booking saved, but this employee has not connected Google "
                "Calendar or needs to reconnect it. Connect it from the "
                "employee portal to sync the schedule.",
            )
    except Exception:
        roster_sync_succeeded = False
        logger.exception("Roster sync failed for new booking %s.", booking.pk)
        messages.warning(
            request,
            "Booking saved, but the employee schedule could not be synced. "
            "Check the employee's Google Calendar connection and application logs.",
        )

    try:
        create_or_update_booking_event(booking)
    except Exception:
        logger.exception("Google Calendar sync failed for new booking %s.", booking.pk)
        messages.warning(
            request,
            "Booking saved, but Google Calendar could not be synced automatically.",
        )

    if send_booking_confirmation_email(request, booking):
        messages.success(
            request,
            f"Booking confirmation emailed to {booking.customer.email}.",
        )
    else:
        messages.warning(
            request,
            "Booking was created, but the customer confirmation email could not "
            "be sent. Check the customer email address and email provider logs.",
        )

    if send_company_booking_created_email(request, booking):
        messages.success(request, "Booking details emailed to the company.")
    else:
        messages.warning(
            request,
            "Booking was created, but the company notification email could not "
            "be sent. Check ADMIN_EMAIL and the email provider logs.",
        )

    if (
        roster_sync_succeeded
        and booking.assigned_employee
        and booking.assigned_employee.user
    ):
        Notification.objects.create(
            user=booking.assigned_employee.user,
            title="New Job Assigned",
            message=(
                f"You have been assigned "
                f"{booking.service_type} on "
                f"{booking.booking_date} at "
                f"{booking.booking_time}."
            ),
            notification_type="booking",
            link="/employee/jobs/",
        )

    create_activity_log(
        request.user,
        "booking",
        "Booking Created",
        f"{booking.customer.full_name if booking.customer else 'No customer'} "
        f"- {booking.service_type} on {booking.booking_date}",
    )
    messages.success(request, "✅ Booking created successfully.")
    return redirect("booking_list")


def send_booking_confirmation_email(request, booking, old_status=None):
    """
    Send the customer an email describing the booking's new status.
    Uses the shared branded booking-status email templates.
    """

    customer = booking.customer

    logger.info(
        "Booking status email function called: booking=%s status=%s",
        booking.id,
        booking.status,
    )

    # --------------------------------------------------
    # Validate customer email
    # --------------------------------------------------
    if not customer:
        logger.warning(
            "Booking %s has no customer. Status email not sent.",
            booking.id,
        )
        return False

    if not customer.email:
        logger.warning(
            "Customer %s has no email address. Booking %s status email not sent.",
            customer.full_name,
            booking.id,
        )
        return False

    status_display = booking.get_status_display()

    if booking.status == "pending" and old_status is None:
        subject = f"Booking request received — YD-B-{booking.id:05d}"
    elif booking.status == "confirmed":
        subject = f"Booking confirmed — YD-B-{booking.id:05d}"
    else:
        subject = (
            f"Booking status updated to {status_display} "
            f"— YD-B-{booking.id:05d}"
        )

    try:
        # --------------------------------------------------
        # Portal URL
        # --------------------------------------------------
        portal_url = f"{settings.SITE_URL.rstrip('/')}/portal/"

        # --------------------------------------------------
        # Status-specific customer messaging
        # --------------------------------------------------
        status_content = {
            "pending": {
                "heading": "Booking request received",
                "message": (
                    "We have received your cleaning booking request. "
                    "Our team will review your booking details and "
                    "provide an update shortly."
                ),
            },
            "confirmed": {
                "heading": "Your booking is confirmed",
                "message": (
                    "Great news — your cleaning booking with "
                    "YD Commercial Cleaning Services has been confirmed."
                ),
            },
            "assigned": {
                "heading": "Your cleaning team has been assigned",
                "message": (
                    "Your booking has been assigned to our cleaning team "
                    "and is now being prepared for service."
                ),
            },
            "in_progress": {
                "heading": "Your cleaning service is underway",
                "message": (
                    "Your scheduled cleaning service is currently "
                    "in progress."
                ),
            },
            "completed": {
                "heading": "Your cleaning service is complete",
                "message": (
                    "Your scheduled cleaning service has been marked "
                    "as completed. Thank you for choosing "
                    "YD Commercial Cleaning Services."
                ),
            },
            "cancelled": {
                "heading": "Your booking has been cancelled",
                "message": (
                    "Your cleaning booking has been cancelled. "
                    "If you believe this was unexpected or need "
                    "assistance, please contact our team."
                ),
            },
        }

        status_info = status_content.get(
            booking.status,
            {
                "heading": "Your booking has been updated",
                "message": (
                    "Your cleaning booking status has been updated."
                ),
            },
        )

        # --------------------------------------------------
        # Previous status
        # --------------------------------------------------
        previous_status = dict(Booking.STATUS_CHOICES).get(
            old_status,
            old_status,
        )

        if previous_status:
            change_description = (
                f"Your booking status has changed from "
                f"{previous_status} to {status_display}."
            )
        else:
            change_description = (
                f"Your booking status is now {status_display}."
            )

        # --------------------------------------------------
        # Email context
        # --------------------------------------------------
        email_context = {
            "customer": customer,
            "booking": booking,
            "portal_url": portal_url,
            "status_heading": status_info["heading"],
            "status_message": status_info["message"],
            "change_description": change_description,
        }

        # --------------------------------------------------
        # Render branded templates
        # --------------------------------------------------
        text_body = render_to_string(
            "emails/bookings/status.txt",
            email_context,
        )

        html_body = render_to_string(
            "emails/bookings/status.html",
            email_context,
        )

        # --------------------------------------------------
        # Send email
        # --------------------------------------------------
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[customer.email],
        )

        email.attach_alternative(
            html_body,
            "text/html",
        )

        logger.info(
            "Sending booking status email: "
            "booking=%s status=%s recipient=%s",
            booking.id,
            booking.status,
            customer.email,
        )

        sent_count = email.send(fail_silently=False)

        if not sent_count:
            logger.error(
                "Booking status email send returned no successful sends: "
                "booking=%s status=%s recipient=%s",
                booking.id,
                booking.status,
                customer.email,
            )
            return False

        logger.info(
            "Booking status email send succeeded: "
            "booking=%s status=%s recipient=%s",
            booking.id,
            booking.status,
            customer.email,
        )

    except Exception:
        logger.exception(
            "BOOKING STATUS EMAIL FAILED - "
            "booking=%s status=%s customer=%s email=%s",
            booking.id,
            booking.status,
            customer.full_name,
            customer.email,
        )
        return False

    # --------------------------------------------------
    # Email was successfully handed to the backend.
    #
    # Logging failures must NOT make us report the email
    # as failed because the email has already been sent.
    # --------------------------------------------------

    try:
        EmailLog.objects.create(
            sent_by=request.user,
            email_type="system",
            recipient_name=customer.full_name,
            recipient_email=customer.email,
            subject=subject,
            related_object=f"Booking #{booking.id}",
        )
    except Exception:
        logger.exception(
            "Booking status email was sent, but EmailLog creation "
            "failed for booking %s.",
            booking.id,
        )

    try:
        activity_title = (
            "Booking Confirmation Email Sent"
            if booking.status == "confirmed"
            else "Booking Status Email Sent"
        )

        create_activity_log(
            request.user,
            "booking",
            activity_title,
            (
                f"Booking YD-B-{booking.id:05d} status update "
                f"({status_display}) emailed to {customer.full_name}."
            ),
        )
    except Exception:
        logger.exception(
            "Booking status email was sent, but activity logging "
            "failed for booking %s.",
            booking.id,
        )

    return True


def send_company_booking_created_email(request, booking):
    """Email the configured company inbox when a dashboard booking is created."""
    company_email = getattr(settings, "ADMIN_EMAIL", "").strip()
    if not company_email:
        logger.warning(
            "Company booking notification not sent: ADMIN_EMAIL is not configured. "
            "Booking=%s",
            booking.pk,
        )
        return False

    customer = booking.customer
    work_orders = list(booking.work_orders.all())
    services = (
        "\n".join(
            f"{position}. {work_order.service_type} — ${work_order.price:.2f}"
            for position, work_order in enumerate(work_orders, start=1)
        )
        if work_orders
        else f"1. {booking.service_type} — ${booking.quoted_price:.2f}"
    )
    subject = f"New booking created — YD-B-{booking.pk:05d}"
    body = (
        "A new booking was created in the YD Commercial Cleaning dashboard.\n\n"
        f"Booking: YD-B-{booking.pk:05d}\n"
        f"Customer: {customer.full_name if customer else 'No customer'}\n"
        f"Customer email: {customer.email if customer and customer.email else 'Not provided'}\n"
        f"Customer phone: {customer.phone if customer else 'Not provided'}\n"
        f"Date: {booking.booking_date}\n"
        f"Time: {booking.booking_time}\n"
        f"Address: {booking.address}, {booking.suburb_postcode}\n"
        f"Assigned employee: {booking.assigned_employee or 'Unassigned'}\n\n"
        f"Work orders:\n{services}\n"
        f"Total before GST: ${booking.quoted_price:.2f}\n"
    )

    try:
        sent_count = send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [company_email],
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            "Company booking notification email failed for booking %s.",
            booking.pk,
        )
        return False

    if not sent_count:
        logger.error(
            "Company booking notification returned no successful sends. Booking=%s",
            booking.pk,
        )
        return False

    try:
        EmailLog.objects.create(
            sent_by=request.user,
            email_type="system",
            recipient_name="YD Commercial Cleaning Services",
            recipient_email=company_email,
            subject=subject,
            related_object=f"Booking #{booking.pk}",
        )
    except Exception:
        logger.exception(
            "Company booking notification was sent, but EmailLog creation failed "
            "for booking %s.",
            booking.pk,
        )

    return True


def _booking_work_order_initial(booking):
    work_orders = list(booking.work_orders.all())
    if work_orders:
        return [
            {"service_type": order.service_type, "price": order.price}
            for order in work_orders
        ]
    return [{"service_type": booking.service_type, "price": booking.quoted_price}]


def _save_and_sync_booking_edit(request, booking, form, work_order_formset=None):
    from google_reviews.calendar_utils import (
        CalendarNotConfigured,
        create_or_update_roster_event,
    )
    from notifications.utils import temporary_instance_flags
    from rosters.services import (
        RosterSyncNotConfigured,
        RosterSyncLockError,
        RosterSyncPending,
        booking_roster_sync_lock,
        sync_booking_roster,
    )

    old_roster_event_deleted = False
    roster = None
    original_employee_id = booking.assigned_employee_id
    reassignment_requested = False
    reassignment_failed = False
    old_status = booking.status

    def restore_roster_event(roster_to_restore):
        with booking_roster_sync_lock(
            booking.pk,
            using=booking._state.db or "default",
        ):
            current_booking = (
                Booking.objects.select_for_update()
                .get(pk=booking.pk)
            )
            current_roster = (
                Roster.objects.select_for_update()
                .get(pk=roster_to_restore.pk)
            )
            if (
                current_booking.assigned_employee_id
                != current_roster.employee_id
            ):
                raise RuntimeError(
                    "The roster assignment changed before its Calendar event could be restored."
                )
            event = create_or_update_roster_event(current_roster)
            if event is None:
                raise CalendarNotConfigured(
                    "The old employee's Calendar is not configured."
                )

    try:
        with booking_roster_sync_lock(
            booking.pk,
            using=booking._state.db or "default",
        ):
            booking = Booking.objects.select_for_update().get(pk=booking.pk)
            old_status = booking.status
            original_employee = booking.assigned_employee
            original_employee_id = booking.assigned_employee_id
            form = BookingForm(request.POST, instance=booking)
            if not form.is_valid():
                return {
                    "form": form,
                    "work_order_formset": work_order_formset,
                    "saved": False,
                    "invalid": True,
                }
            if "work_orders-TOTAL_FORMS" in request.POST:
                work_order_formset = BookingWorkOrderFormSet(
                    request.POST,
                    prefix="work_orders",
                )
                if not work_order_formset.is_valid():
                    return {
                        "form": form,
                        "work_order_formset": work_order_formset,
                        "saved": False,
                        "invalid": True,
                    }
                work_orders = [
                    {
                        "service_type": item["service_type"],
                        "price": item["price"],
                    }
                    for item in work_order_formset.cleaned_data
                    if item
                    and item.get("service_type")
                    and not item.get("DELETE")
                ]
            else:
                work_orders = [
                    {
                        "service_type": form.cleaned_data["service_type"],
                        "price": form.cleaned_data["quoted_price"],
                    }
                ]
            if not work_orders:
                form.add_error(None, "Add at least one service or work order.")
                return {
                    "form": form,
                    "work_order_formset": work_order_formset,
                    "saved": False,
                    "invalid": True,
                }
            form.instance.service_type = work_orders[0]["service_type"]
            form.instance.quoted_price = sum(
                (item["price"] for item in work_orders),
                Decimal("0.00"),
            )

            requested_employee = form.cleaned_data.get("assigned_employee")
            requested_employee_id = (
                requested_employee.pk if requested_employee else None
            )
            reassignment_requested = requested_employee_id != original_employee_id


            if reassignment_requested:
                roster = booking.rosters.order_by("id").first()
                if roster and roster.google_calendar_event_id:
                    try:
                        reassignment_failed = not delete_roster_event(roster)
                        old_roster_event_deleted = not reassignment_failed
                    except Exception:
                        logger.exception(
                            "Could not remove the existing roster calendar event "
                            "before reassigning booking %s.",
                            booking.pk,
                        )
                        reassignment_failed = True

                    if reassignment_failed:
                        roster.refresh_from_db(
                            fields=["google_calendar_event_id"]
                        )
                        form.instance.assigned_employee = original_employee
                        messages.warning(
                            request,
                            "Booking details were saved, but the employee "
                            "reassignment failed because the existing roster "
                            "Calendar event could not be removed. The employee "
                            "schedule could not be synced.",
                        )

            suppression_flags = (
                {
                    "_suppress_employee_assignment_notification": True,
                    "_suppress_customer_status_notification": True,
                }
                if reassignment_requested
                else {}
            )
            try:
                with temporary_instance_flags(form.instance, **suppression_flags):
                    with transaction.atomic():
                        updated_booking = form.save()
                        replace_booking_work_orders(updated_booking, work_orders)
            except Exception:
                logger.exception(
                    "Booking save failed after editing booking %s.",
                    booking.pk,
                )
                if old_roster_event_deleted and roster:
                    try:
                        restore_roster_event(roster)
                    except Exception:
                        logger.exception(
                            "Could not restore the old roster Calendar event "
                            "after booking %s failed to save.",
                            booking.pk,
                        )
                        messages.error(
                            request,
                            "The booking could not be saved. The old roster "
                            "Calendar event could not be restored yet; retrying "
                            "the edit will retry synchronization.",
                        )
                    else:
                        messages.error(
                            request,
                            "The booking could not be saved. The old employee's "
                            "roster Calendar event was restored.",
                        )
                else:
                    messages.error(request, "The booking could not be saved.")
                return {
                    "form": form,
                    "work_order_formset": work_order_formset,
                    "saved": False,
                    "invalid": False,
                }

            new_status = updated_booking.status
            if not reassignment_failed:
                try:
                    sync_result = sync_booking_roster(updated_booking)
                    if isinstance(sync_result, RosterSyncPending):
                        raise sync_result.error
                    if isinstance(sync_result, RosterSyncNotConfigured):
                        if reassignment_requested:
                            reassignment_failed = True
                            messages.warning(
                                request,
                                "Booking details and employee assignment were "
                                "saved, but the new employee has not connected "
                                "Google Calendar or needs to reconnect it. "
                                "Completion "
                                "notifications and invoice creation were skipped.",
                            )
                        else:
                            messages.info(
                                request,
                                "Booking changes were saved, but this employee "
                                "has not connected Google Calendar or needs to "
                                "reconnect it from the employee portal.",
                            )
                except Exception:
                    logger.exception(
                        "Roster sync failed after editing booking %s.",
                        updated_booking.pk,
                    )
                    if reassignment_requested:
                        current_roster = (
                            Roster.objects.filter(booking_id=updated_booking.pk)
                            .order_by("id")
                            .first()
                        )
                        updated_booking.refresh_from_db(
                            fields=["assigned_employee"]
                        )
                        if (
                            current_roster is None
                            or current_roster.employee_id
                            != updated_booking.assigned_employee_id
                        ):
                            recovery_employee_id = (
                                current_roster.employee_id
                                if current_roster
                                else original_employee_id
                            )
                            Booking.objects.filter(pk=updated_booking.pk).update(
                                assigned_employee_id=recovery_employee_id
                            )
                            updated_booking.assigned_employee_id = (
                                recovery_employee_id
                            )
                        reassignment_failed = True
                        if (
                            current_roster
                            and current_roster.employee_id == original_employee_id
                            and old_roster_event_deleted
                        ):
                            try:
                                restore_roster_event(current_roster)
                            except Exception:
                                logger.exception(
                                    "Could not restore the old roster Calendar "
                                    "event after reassignment of booking %s failed.",
                                    updated_booking.pk,
                                )
                                messages.error(
                                    request,
                                    "The reassignment failed and was rolled back "
                                    "to the original employee. Restoring that "
                                    "employee's Calendar event is still pending; "
                                    "retry the edit to complete synchronization.",
                                )
                            else:
                                messages.warning(
                                    request,
                                    "The reassignment failed and was rolled back "
                                    "to the original employee. Their roster "
                                    "Calendar event was restored.",
                                )
                        else:
                            messages.warning(
                                request,
                                "Booking details and employee assignment were "
                                "saved, but the new employee's roster Calendar "
                                "event could not be synchronized. Retry the edit "
                                "to synchronize it.",
                            )
                    else:
                        messages.warning(
                            request,
                            "Booking updated, but the employee schedule could "
                            "not be synced. Check the employee's Google Calendar "
                            "connection and application logs.",
                        )

            return {
                "booking": updated_booking,
                "form": form,
                "old_status": old_status,
                "new_status": new_status,
                "reassignment_requested": reassignment_requested,
                "reassignment_failed": reassignment_failed,
                "saved": True,
            }
    except (DatabaseError, RosterSyncLockError):
        logger.exception(
            "Could not safely save and synchronize booking %s.",
            booking.pk,
        )
        if old_roster_event_deleted and roster:
            try:
                restore_roster_event(roster)
            except Exception:
                logger.exception(
                    "Could not restore the old roster Calendar event after "
                    "booking %s synchronization failed.",
                    booking.pk,
                )
                messages.error(
                    request,
                    "The booking update could not be completed, and Calendar "
                    "recovery is still pending. Retry the edit to synchronize it.",
                )
            else:
                messages.error(
                    request,
                    "The booking update could not be completed. The old "
                    "employee's roster Calendar event was restored.",
                )
        else:
            messages.error(
                request,
                "The booking update could not be safely serialized. No changes "
                "were saved; please retry.",
            )
        return {
            "form": form,
            "saved": False,
            "invalid": False,
        }


@admin_required
def edit_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    work_order_initial = _booking_work_order_initial(booking)

    if request.method == "POST":
        form = BookingForm(request.POST, instance=booking)
        work_order_formset = (
            BookingWorkOrderFormSet(request.POST, prefix="work_orders")
            if "work_orders-TOTAL_FORMS" in request.POST
            else None
        )
        if form.is_valid() and (
            work_order_formset is None or work_order_formset.is_valid()
        ):
            result = _save_and_sync_booking_edit(
                request,
                booking,
                form,
                work_order_formset,
            )
            form = result["form"]
            work_order_formset = result.get("work_order_formset") or work_order_formset
            if not result["saved"]:
                if result.get("invalid"):
                    pass
                else:
                    return render(
                        request,
                        "bookings/booking_form.html",
                        {
                            "form": form,
                            "work_order_formset": work_order_formset,
                            "page_title": "Edit Booking",
                            "button_text": "Update Booking",
                        },
                    )
            else:
                updated_booking = result["booking"]
                old_status = result["old_status"]
                new_status = result["new_status"]
                reassignment_requested = result["reassignment_requested"]
                reassignment_failed = result["reassignment_failed"]

                if reassignment_requested and not reassignment_failed:
                    assigned_employee = updated_booking.assigned_employee
                    if assigned_employee and assigned_employee.user:
                        Notification.objects.create(
                            user=assigned_employee.user,
                            title="Booking Assigned",
                            message=(
                                f"You have a job: {updated_booking.service_type} "
                                f"on {updated_booking.booking_date}."
                            ),
                            notification_type="booking",
                            link=f"/employee/jobs/{updated_booking.pk}/",
                        )
                    customer = updated_booking.customer
                    if old_status != new_status and customer and customer.user:
                        Notification.objects.create(
                            user=customer.user,
                            title="Booking Updated",
                            message=(
                                f"Your booking for {updated_booking.service_type} is now "
                                f"{updated_booking.get_status_display()}."
                            ),
                            notification_type="booking",
                            link=f"/portal/bookings/{updated_booking.pk}/",
                        )

                if not reassignment_failed and old_status != new_status:
                    logger.info(
                        "Booking status transition detected: booking=%s old=%s new=%s",
                        updated_booking.id,
                        old_status,
                        new_status,
                    )
                    if send_booking_confirmation_email(
                        request,
                        updated_booking,
                        old_status,
                    ):
                        messages.success(
                            request,
                            f"✅ Customer notified by email: booking status is now {updated_booking.get_status_display()}.",
                        )
                    else:
                        messages.warning(
                            request,
                            "⚠️ Booking updated, but the customer status email could not be sent.",
                        )

                if not reassignment_failed and updated_booking.status == "completed":
                    invoice, invoice_created = get_or_create_invoice_for_booking(
                        updated_booking
                    )
                    if not invoice_created:
                        messages.info(
                            request,
                            f"Invoice already exists: {invoice.invoice_number}",
                        )
                    else:
                        messages.success(
                            request,
                            f"Invoice automatically created: {invoice.invoice_number}",
                        )
                        if send_invoice_email(request, invoice):
                            messages.success(
                                request,
                                f"Invoice {invoice.invoice_number} emailed to "
                                f"{invoice.booking.customer.email}.",
                            )
                        else:
                            messages.warning(
                                request,
                                f"Invoice {invoice.invoice_number} was created, "
                                "but the customer invoice email could not be sent.",
                            )

                if not reassignment_failed:
                    try:
                        create_or_update_booking_event(updated_booking)
                    except Exception:
                        logger.exception(
                            "Google Calendar sync failed after editing booking %s.",
                            updated_booking.pk,
                        )
                        messages.warning(
                            request,
                            "Booking updated, but Google Calendar could not be synced automatically.",
                        )

                if (
                    not reassignment_failed
                    and updated_booking.assigned_employee
                    and updated_booking.assigned_employee.user
                ):
                    Notification.objects.create(
                        user=updated_booking.assigned_employee.user,
                        title="Booking Updated",
                        message=(
                            f"Booking updated: "
                            f"{updated_booking.service_type} "
                            f"on {updated_booking.booking_date} "
                            f"at {updated_booking.booking_time}."
                        ),
                        notification_type="booking",
                        link="/employee/jobs/",
                    )

                create_activity_log(
                    request.user,
                    "booking",
                    "Booking Updated",
                    f"{updated_booking.customer.full_name if updated_booking.customer else 'No customer'} "
                    f"- {updated_booking.service_type} on {updated_booking.booking_date}",
                )

                if not reassignment_failed:
                    messages.success(request, "✅ Booking updated successfully.")
                return redirect("booking_list")

    else:
        form = BookingForm(instance=booking)
        work_order_formset = BookingWorkOrderFormSet(
            prefix="work_orders",
            initial=work_order_initial,
        )

    return render(
        request,
        "bookings/booking_form.html",
        {
            "form": form,
            "work_order_formset": work_order_formset,
            "page_title": "Edit Booking",
            "button_text": "Update Booking",
        },
    )


@require_http_methods(["GET", "POST"])
@admin_required
@_lock_booking_mutations("booking_list")
def delete_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    customer_name = booking.customer.full_name if booking.customer else "No customer"
    booking_name = f"{customer_name} - {booking.service_type} on {booking.booking_date}"

    if request.method == "POST":
        calendar_cleanup_failed = False

        for roster in booking.rosters.all():
            if not roster.google_calendar_event_id:
                continue
            try:
                if not delete_roster_event(roster):
                    calendar_cleanup_failed = True
                    logger.warning(
                        "Could not remove calendar event for roster %s "
                        "while deleting booking %s.",
                        roster.pk,
                        booking.pk,
                    )
            except Exception:
                calendar_cleanup_failed = True
                logger.exception(
                    "Calendar cleanup failed for roster %s while deleting "
                    "booking %s.",
                    roster.pk,
                    booking.pk,
                )

        if booking.google_calendar_event_id:
            try:
                if not delete_booking_event(booking):
                    calendar_cleanup_failed = True
                    logger.warning(
                        "Could not remove calendar event for booking %s.",
                        booking.pk,
                    )
            except Exception:
                calendar_cleanup_failed = True
                logger.exception(
                    "Calendar cleanup failed for booking %s.",
                    booking.pk,
                )

        booking.delete()

        create_activity_log(request.user, "booking", "Booking Deleted", booking_name)

        if calendar_cleanup_failed:
            messages.warning(
                request,
                "Booking deleted, but one or more Google Calendar events could "
                "not be removed.",
            )
        else:
            messages.success(request, "✅ Booking deleted successfully.")
        return redirect("booking_list")

    return render(
        request,
        "shared/confirm_delete.html",
        {
            "object_name": booking_name,
            "cancel_url": "/dashboard/bookings/",
        },
    )


@login_required
def booking_calendar(request):
    today = timezone.now().date()

    start_date = request.GET.get("start")

    if start_date:
        try:
            week_start = timezone.datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            week_start = today
    else:
        week_start = today - timedelta(days=today.weekday())

    week_end = week_start + timedelta(days=6)

    previous_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)

    bookings = (
        Booking.objects.filter(booking_date__gte=week_start, booking_date__lte=week_end)
        .exclude(status="cancelled")
        .select_related("customer", "assigned_employee")
        .order_by("booking_date", "booking_time")
    )

    week_days = []


    for i in range(7):
        day = week_start + timedelta(days=i)

        day_bookings = bookings.filter(booking_date=day)

        day_rosters = (
            Roster.objects.filter(shift_date=day)
            .exclude(status="cancelled")
            .select_related(
                "employee",
                "booking",
                "booking__customer",
            )
            .order_by("start_time")
        )

        day_leave = LeaveRequest.objects.filter(
            status="approved",
            start_date__lte=day,
            end_date__gte=day,
        ).select_related("employee")

        week_days.append(
            {
                "date": day,
                "bookings": day_bookings,
                "rosters": day_rosters,
                "leave_requests": day_leave,
            }
        )

    today_jobs = (
        Booking.objects.filter(booking_date=today).exclude(status="cancelled").count()
    )

    tomorrow_jobs = (
        Booking.objects.filter(booking_date=today + timedelta(days=1))
        .exclude(status="cancelled")
        .count()
    )

    week_jobs = bookings.count()

    unassigned_jobs = bookings.filter(assigned_employee__isnull=True).count()

    return render(
        request,
        "bookings/booking_calendar.html",
        {
            "week_days": week_days,
            "today": today,
            "week_start": week_start,
            "week_end": week_end,
            "previous_week": previous_week,
            "next_week": next_week,
            "today_jobs": today_jobs,
            "tomorrow_jobs": tomorrow_jobs,
            "week_jobs": week_jobs,
            "unassigned_jobs": unassigned_jobs,
        },
    )



def send_invoice_email(request, invoice):
    """
    Send a newly created invoice to the customer with the invoice PDF attached.
    """

    booking = invoice.booking
    customer = booking.customer

    if not customer:
        logger.warning(
            "Invoice %s has no customer. Invoice email not sent.",
            invoice.invoice_number,
        )
        return False

    if not customer.email:
        logger.warning(
            "Customer %s has no email address. Invoice %s email not sent.",
            customer.full_name,
            invoice.invoice_number,
        )
        return False

    subject = (
        f"Invoice {invoice.invoice_number} — "
        f"YD Commercial Cleaning Services"
    )

    portal_url = f"{settings.SITE_URL.rstrip('/')}/portal/"

    email_context = {
        "customer": customer,
        "booking": booking,
        "invoice": invoice,
        "portal_url": portal_url,
        "payment_url": request.build_absolute_uri(
            reverse(
                "create_stripe_checkout_session",
                kwargs={"invoice_id": invoice.id},
            )
        ),
    }

    try:
        text_body = render_to_string(
            "emails/invoices/invoice.txt",
            email_context,
        )

        html_body = render_to_string(
            "emails/invoices/invoice.html",
            email_context,
        )

        # Generate the invoice PDF using the existing PDF generator.
        pdf_buffer = generate_invoice_pdf(invoice)

        pdf_content = pdf_buffer.getvalue()

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[customer.email],
        )

        email.attach_alternative(
            html_body,
            "text/html",
        )

        email.attach(
            f"{invoice.invoice_number}.pdf",
            pdf_content,
            "application/pdf",
        )

        logger.info(
            "Sending invoice email: invoice=%s customer=%s recipient=%s",
            invoice.invoice_number,
            customer.full_name,
            customer.email,
        )

        sent_count = email.send(fail_silently=False)

        if not sent_count:
            logger.error(
                "Invoice email returned no successful sends: invoice=%s recipient=%s",
                invoice.invoice_number,
                customer.email,
            )
            return False

        logger.info(
            "Invoice email sent successfully: invoice=%s recipient=%s",
            invoice.invoice_number,
            customer.email,
        )

    except Exception:
        logger.exception(
            "INVOICE EMAIL FAILED: invoice=%s customer=%s email=%s",
            invoice.invoice_number,
            customer.full_name,
            customer.email,
        )
        return False

    # --------------------------------------------------
    # Mark invoice as sent only after successful email send
    # --------------------------------------------------

    if invoice.status not in {"paid", "cancelled"}:
        try:
            Invoice.objects.filter(pk=invoice.pk).update(
                status="sent",
                updated_at=timezone.now(),
            )
            invoice.status = "sent"
        except Exception:
            logger.exception(
                "Invoice email was sent but invoice status could not "
                "be changed to sent: invoice=%s",
                invoice.invoice_number,
            )

    # --------------------------------------------------
    # Email log
    # --------------------------------------------------

    try:
        EmailLog.objects.create(
            sent_by=request.user,
            email_type="invoice",
            recipient_name=customer.full_name,
            recipient_email=customer.email,
            subject=subject,
            related_object=f"Invoice {invoice.invoice_number}",
        )
    except Exception:
        logger.exception(
            "Invoice email was sent but EmailLog creation failed: invoice=%s",
            invoice.invoice_number,
        )

    # --------------------------------------------------
    # Activity log
    # --------------------------------------------------

    try:
        create_activity_log(
            request.user,
            "invoice",
            "Invoice Emailed",
            (
                f"Invoice {invoice.invoice_number} was emailed to "
                f"{customer.full_name}."
            ),
        )
    except Exception:
        logger.exception(
            "Invoice email was sent but activity logging failed: invoice=%s",
            invoice.invoice_number,
        )

    return True


@admin_required
def employee_list(request):
    employees = Employee.objects.select_related("user").order_by("-created_at")
    created_employee = None
    created_employee_id = request.session.pop("employee_created_id", None)
    created_login = request.session.pop("employee_created_login", False)
    created_access_mode = request.session.pop("employee_created_access_mode", "none")
    if created_employee_id:
        created_employee = Employee.objects.select_related("user").filter(
            pk=created_employee_id
        ).first()

    context = {
        "employees": employees,
        "total_count": employees.count(),
        "active_count": employees.filter(active=True).count(),
        "portal_count": employees.filter(user__isnull=False).count(),
        "available_count": employees.filter(availability="available", active=True).count(),
        "created_employee": created_employee,
        "created_login": created_login,
        "created_access_mode": created_access_mode,
        "role_choices": Employee.ROLE_CHOICES,
    }
    return render(request, "employees/employee_list.html", context)


@admin_required
def add_employee(request):
    if request.method == "POST":
        form = EmployeeCreateForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                employee, portal_enabled = create_employee_from_form(form)
            except ValidationError as error:
                form.add_error(None, error)
            except (IntegrityError, DatabaseError):
                logger.exception(
                    "Employee creation failed for dashboard user %s",
                    request.user.pk,
                )
                form.add_error(
                    None,
                    "We could not save this employee. Check for a duplicate login and try again.",
                )
            else:
                if form.cleaned_data["access_mode"] == "create" and employee.user_id:
                    try:
                        from security.views import _send_user_activation_email

                        _send_user_activation_email(
                            request,
                            employee.user,
                            activate_account=employee.active,
                        )
                    except Exception:
                        logger.exception(
                            "Employee account verification email failed: employee=%s",
                            employee.pk,
                        )
                        messages.warning(
                            request,
                            "Employee was added, but the account verification email could not be sent. Resend it from Users & Positions.",
                        )
                    else:
                        messages.success(
                            request,
                            "A verification link was sent to the employee's email address. Their account is inactive until verified.",
                        )

                try:
                    create_activity_log(
                        request.user,
                        "employee",
                        "Employee Added",
                        f"{employee.full_name} was added to the employee database.",
                    )
                except DatabaseError:
                    logger.exception(
                        "Employee activity logging failed: employee=%s",
                        employee.pk,
                    )

                request.session["employee_created_id"] = employee.pk
                request.session["employee_created_login"] = portal_enabled
                request.session["employee_created_access_mode"] = form.cleaned_data["access_mode"]
                return redirect("employee_list")
    else:
        form = EmployeeCreateForm()

    return render(
        request,
        "employees/add.html",
        {
            "form": form,
            "username_required": form.fields["username"].required,
        },
    )


@admin_required
def edit_employee(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)

    if request.method == "POST":
        form = EmployeeForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            updated_employee = form.save()
            create_activity_log(
                request.user,
                "employee",
                "Employee Updated",
                f"{updated_employee.full_name}'s profile was updated.",
            )
            messages.success(request, "✅ Employee updated successfully.")
            return redirect("employee_list")
    else:
        form = EmployeeForm(instance=employee)

    return render(
        request,
        "employees/employee_form.html",
        {
            "form": form,
            "page_title": "Edit Employee",
            "button_text": "Update Employee",
        },
    )


@require_POST
@admin_required
def delete_employee(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    employee_name = employee.full_name
    employee.delete()

    create_activity_log(
        request.user,
        "employee",
        "Employee Deleted",
        f"{employee_name} was removed from the employee database.",
    )
    messages.success(request, "✅ Employee deleted successfully.")
    return redirect("employee_list")


# ============================================================
# Gallery Dashboard
# ============================================================

@login_required
def gallery_list(request):

    items = (
        GalleryItem.objects
        .prefetch_related("additional_images")
        .all()
        .order_by("-id")
    )

    return render(
        request,
        "dashboard/gallery/dashboard_gallery_list.html",
        {
            "items": items,
            "source_count": items.values("source").distinct().count(),
        },
    )


@admin_required
def property_damage_report_list(request):
    reports = (
        PropertyDamageReport.objects
        .select_related("employee__user", "booking", "closed_by")
        .prefetch_related("images", "replies__responder")
        .order_by("-created_at")
    )
    paginator = Paginator(reports, 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    for report in page_obj.object_list:
        report.reply_form = PropertyDamageReportReplyForm(
            prefix=f"reply-{report.pk}"
        )

    return render(
        request,
        "dashboard/employees/property_damage_reports.html",
        {
            "page_obj": page_obj,
            "report_count": reports.count(),
            "open_report_count": reports.filter(
                status=PropertyDamageReport.STATUS_OPEN
            ).count(),
            "closed_report_count": reports.filter(
                status=PropertyDamageReport.STATUS_CLOSED
            ).count(),
            "today_report_count": reports.filter(
                created_at__date=timezone.localdate()
            ).count(),
            "reporting_employee_count": (
                reports.exclude(employee__isnull=True)
                .values("employee_id")
                .distinct()
                .count()
            ),
        },
    )


@admin_required
@require_POST
def property_damage_report_set_status(request, report_id):
    with transaction.atomic():
        report = get_object_or_404(
            PropertyDamageReport.objects.select_for_update(),
            pk=report_id,
        )
        if report.status == PropertyDamageReport.STATUS_OPEN:
            report.status = PropertyDamageReport.STATUS_CLOSED
            report.closed_at = timezone.now()
            report.closed_by = request.user
            action = "closed"
        else:
            report.status = PropertyDamageReport.STATUS_OPEN
            report.closed_at = None
            report.closed_by = None
            action = "reopened"
        report.save(update_fields=["status", "closed_at", "closed_by"])

    employee_user = report.employee.user if report.employee else None
    if employee_user:
        notify_user(
            employee_user,
            f"Property damage report #{report.pk} {action}",
            (
                f"The dashboard team {action} your property damage report "
                f"#{report.pk}."
            ),
            notification_type="damage_report",
            link=f"/employee/damage-report/#report-{report.pk}",
        )

    messages.success(
        request,
        (
            f"Property damage report #{report.pk} "
            f"{'resolved and closed' if action == 'closed' else 'reopened'}."
        ),
    )
    return redirect(f"{reverse('property_damage_report_list')}#report-{report.pk}")


@admin_required
@require_http_methods(["GET", "POST"])
def property_damage_report_conversation(request, report_id):
    report = get_object_or_404(
        PropertyDamageReport.objects.select_related("employee__user"),
        pk=report_id,
    )
    if request.method == "POST":
        typing_value = request.POST.get("is_typing")
        if typing_value not in {"true", "false"}:
            return JsonResponse(
                {"error": "A valid typing state is required."},
                status=400,
            )
        update_report_presence(
            report,
            request.user,
            is_typing=typing_value == "true",
        )
    else:
        update_report_presence(report, request.user)
    return conversation_response(report, request.user, other_side="employee")


@admin_required
@require_POST
def property_damage_report_reply(request, report_id):
    report = get_object_or_404(
        PropertyDamageReport.objects.select_related("employee__user"),
        pk=report_id,
    )
    form = PropertyDamageReportReplyForm(
        request.POST,
        prefix=f"reply-{report.pk}",
    )
    if not form.is_valid():
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(
                {"error": "Please enter a reply before sending it."},
                status=400,
            )
        messages.error(request, "Please enter a reply before sending it.")
        return redirect(f"{reverse('property_damage_report_list')}#report-{report.pk}")

    with transaction.atomic():
        report = PropertyDamageReport.objects.select_for_update().get(pk=report.pk)
        reply = form.save(commit=False)
        reply.report = report
        reply.responder = request.user
        reply.save()
        if report.status == PropertyDamageReport.STATUS_CLOSED:
            report.status = PropertyDamageReport.STATUS_OPEN
            report.closed_at = None
            report.closed_by = None
            report.save(update_fields=["status", "closed_at", "closed_by"])

    employee_user = report.employee.user if report.employee else None
    if employee_user:
        notify_user(
            employee_user,
            f"Reply to property damage report #{report.pk}",
            (
                f"{request.user.get_full_name() or request.user.get_username()} "
                f"replied to your report: {reply.message[:180]}"
            ),
            notification_type="damage_report",
            link=f"/employee/damage-report/#report-{report.pk}",
        )
    else:
        logger.warning(
            "Reply saved for property damage report %s, but its employee has "
            "no linked portal user to notify.",
            report.pk,
        )
        messages.warning(
            request,
            "Reply saved, but the employee has no linked portal account for notification.",
        )
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True})
        return redirect(f"{reverse('property_damage_report_list')}#report-{report.pk}")

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    messages.success(request, "Your reply was sent to the employee.")
    return redirect(f"{reverse('property_damage_report_list')}#report-{report.pk}")


def _persist_gallery_form_uploads(request, form, gallery_item, item_id=None):
    nonce = request.POST.get("gallery_upload_nonce", "").strip()
    if not nonce:
        primary_files = {
            name: form.cleaned_data.get(name)
            for name in ("image", "before_image", "after_image")
        }
        return save_gallery_uploads(
            gallery_item,
            primary_files,
            form.cleaned_data.get("additional_images", []),
        )

    if request.FILES:
        raise ValueError("Choose either direct-uploaded or form-uploaded images, not both.")

    batches = request.session.get(GALLERY_UPLOAD_SESSION_KEY, {})
    batch = batches.get(nonce)
    if (
        not batch
        or batch.get("user_id") != request.user.pk
        or batch.get("item_id") != item_id
        or batch.get("expires_at", 0) <= int(timezone.now().timestamp())
        or not batch.get("finalized")
        or not batch.get("verified_assets")
    ):
        raise ValueError("The uploaded gallery images expired. Please upload them again.")

    try:
        return save_verified_gallery_uploads(
            gallery_item,
            batch["verified_assets"],
        )
    finally:
        batches.pop(nonce, None)
        request.session[GALLERY_UPLOAD_SESSION_KEY] = batches


def _gallery_upload_context(request, form, item_id=None):
    nonce = request.POST.get("gallery_upload_nonce", "").strip()
    batches = request.session.get(GALLERY_UPLOAD_SESSION_KEY, {})
    batch = batches.get(nonce)
    staged_images = []
    if (
        batch
        and batch.get("user_id") == request.user.pk
        and batch.get("item_id") == item_id
        and batch.get("expires_at", 0) > int(timezone.now().timestamp())
        and batch.get("finalized")
    ):
        storage = GalleryItem._meta.get_field("image").storage
        for asset in batch.get("verified_assets", []):
            public_id = asset["public_id"]
            staged_images.append(
                {
                    "slot": asset["slot"],
                    "name": public_id.rsplit("/", 1)[-1],
                    "public_id": public_id,
                    "url": storage.url(public_id),
                }
            )
    else:
        nonce = ""
    return {
        "form": form,
        "gallery_upload_nonce": nonce,
        "staged_gallery_images": staged_images,
    }


@login_required
def add_gallery_item(request):

    if request.method == "POST":

        form = GalleryItemForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            gallery_item = form.save(commit=False)
            try:
                _persist_gallery_form_uploads(request, form, gallery_item)
            except Exception:
                logger.exception("Gallery upload failed while adding an item")
                form.add_error(None, "The gallery images could not be saved. Please try again.")
            else:
                messages.success(request, "✅ Gallery item added successfully.")
                return redirect("gallery_list")

        messages.error(
            request,
            "❌ Please check the gallery form.",
        )

    else:

        form = GalleryItemForm()


    context = _gallery_upload_context(request, form)
    context.update(
        {
            "page_title": "Add Gallery Item",
            "button_text": "Save Gallery Item",
        }
    )
    return render(request, "dashboard/gallery/dashboard_gallery_form.html", context)


@login_required
def edit_gallery_item(
    request,
    item_id
):

    item = get_object_or_404(
        GalleryItem,
        id=item_id,
    )


    if request.method == "POST":

        form = GalleryItemForm(
            request.POST,
            request.FILES,
            instance=item,
        )

        if form.is_valid():
            gallery_item = form.save(commit=False)
            try:
                _persist_gallery_form_uploads(request, form, gallery_item, item.pk)
            except Exception:
                logger.exception("Gallery upload failed while editing item %s", item.pk)
                form.add_error(None, "The gallery images could not be saved. Please try again.")
            else:
                messages.success(request, "✅ Gallery item updated successfully.")
                return redirect("gallery_list")

        messages.error(
            request,
            "❌ Please check the gallery form.",
        )

    else:

        form = GalleryItemForm(
            instance=item
        )


    context = _gallery_upload_context(request, form, item.pk)
    context.update(
        {
            "page_title": "Edit Gallery Item",
            "button_text": "Update Gallery Item",
        }
    )
    return render(request, "dashboard/gallery/dashboard_gallery_form.html", context)


@require_POST
@admin_required
def delete_gallery_item(request, item_id):

    item = get_object_or_404(
        GalleryItem,
        id=item_id,
    )


    if request.method == "POST":

        item.delete()

        messages.success(
            request,
            "✅ Gallery item deleted successfully.",
        )

        return redirect(
            "gallery_list"
        )


    return render(
        request,
        "shared/confirm_delete.html",
        {
            "object_name": str(item),
            "cancel_url": "/dashboard/gallery/",
        },
    )


@login_required
def review_list(request):
    reviews = Review.objects.all().order_by("-created_at", "-pk")
    query = request.GET.get("q", "").strip()
    rating = request.GET.get("rating", "").strip()
    if query:
        reviews = reviews.filter(
            Q(customer_name__icontains=query)
            | Q(suburb__icontains=query)
            | Q(review_text__icontains=query)
        )
    if rating in {"1", "2", "3", "4", "5"}:
        reviews = reviews.filter(rating=int(rating))
    else:
        rating = ""
    paginator = Paginator(reviews, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "dashboard/reviews/dashboard_review_list.html",
        {
            "reviews": page_obj.object_list,
            "page_obj": page_obj,
            "query": query,
            "rating": rating,
            "rating_choices": Review.RATING_CHOICES,
            "total_reviews": Review.objects.count(),
            "featured_count": Review.objects.filter(featured=True).count(),
            "average_rating": Review.objects.aggregate(average=Avg("rating"))[
                "average"
            ] or 0,
        },
    )


@login_required
def add_review(request):
    if request.method == "POST":
        form = ReviewForm(request.POST)

        if form.is_valid():
            review = form.save()

            create_activity_log(
                request.user,
                "review",
                "Review Added",
                f"{review.customer_name} review added with {review.rating} stars.",
            )

            messages.success(request, "✅ Review added successfully.")
            return redirect("review_list")

        messages.error(request, "❌ Please check the review form.")
    else:
        initial_data = {}

        customer_name = request.GET.get("customer_name")
        suburb = request.GET.get("suburb")

        if customer_name:
            initial_data["customer_name"] = customer_name

        if suburb:
            initial_data["suburb"] = suburb

        form = ReviewForm(initial=initial_data)

    return render(
        request,
        "dashboard/reviews/dashboard_review_form.html",
        {
            "form": form,
            "page_title": "Add Review",
            "button_text": "Save Review",
        },
    )


@login_required
def edit_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)

    if request.method == "POST":
        form = ReviewForm(request.POST, instance=review)

        if form.is_valid():
            updated_review = form.save()

            create_activity_log(
                request.user,
                "review",
                "Review Updated",
                f"{updated_review.customer_name} review was updated.",
            )

            messages.success(request, "✅ Review updated successfully.")
            return redirect("review_list")

        messages.error(request, "❌ Please check the review form.")
    else:
        form = ReviewForm(instance=review)

    return render(
        request,
        "dashboard/reviews/dashboard_review_form.html",
        {
            "form": form,
            "page_title": "Edit Review",
            "button_text": "Update Review",
        },
    )


@admin_required
@require_http_methods(["GET", "POST"])
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)

    review_name = review.customer_name

    if request.method == "POST":
        review.delete()

        create_activity_log(
            request.user,
            "review",
            "Review Deleted",
            f"{review_name} review was deleted.",
        )

        messages.success(request, "✅ Review deleted successfully.")
        return redirect("review_list")

    return render(
        request,
        "dashboard/reviews/review_confirm_delete.html",
        {
            "review": review,
        },
    )


@login_required
def export_quotes_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="yd-cleaning-quotes.csv"'

    writer = csv.writer(response)

    writer.writerow(
        [
            "Name",
            "Email",
            "Phone",
            "Property Type",
            "Suburb/Postcode",
            "Preferred Date",
            "Status",
            "Admin Notes",
            "Message",
            "Created At",
        ]
    )

    for quote in QuoteRequest.objects.all().order_by("-created_at"):
        writer.writerow(
            [
                quote.name,
                quote.email,
                quote.phone,
                quote.property_type,
                quote.suburb_postcode,
                quote.preferred_date,
                quote.get_status_display(),
                quote.admin_notes,
                quote.message,
                quote.created_at,
            ]
        )

    return response


@login_required
def attendance_report(request):
    logs = AttendanceLog.objects.select_related(
        "employee", "booking", "booking__customer"
    ).order_by("-check_in_time", "-created_at")

    completed_logs = logs.filter(check_out_time__isnull=False).count()
    open_logs = logs.filter(check_out_time__isnull=True).count()
    total_hours = (
        logs.aggregate(total=Sum("total_hours"))["total"]
        or 0
    )
    return render(
        request,
        "attendance/attendance_report.html",
        {
            "logs": logs,
            "completed_logs": completed_logs,
            "open_logs": open_logs,
            "total_hours": total_hours,
        },
    )


@login_required
def company_settings(request):
    # Get the first company settings record.
    # If it does not exist, create one automatically.
    settings, created = CompanySettings.objects.get_or_create(id=1)

    if request.method == "POST":
        # Use request.FILES because logo/favicon are file uploads.
        form = CompanySettingsForm(request.POST, request.FILES, instance=settings)

        if form.is_valid():
            form.save()

            # ==================================================
            # Activity Log
            # ==================================================
            create_activity_log(
                request.user,
                "settings",
                "Company Settings Updated",
                "Business settings, branding, contact details or invoice settings were updated.",
            )

            messages.success(request, "✅ Company settings updated successfully.")

            return redirect("company_settings")

        messages.error(request, "❌ Please check the settings form.")

    else:
        form = CompanySettingsForm(instance=settings)

    return render(
        request,
        "dashboard/core/company_settings.html",
        {
            "form": form,
            "settings": settings,
        },
    )


# ==========================================================
# Employee Performance Dashboard
# Purpose:
# Show employee jobs, hours, payroll and revenue performance.
# ==========================================================


@login_required
def employee_performance(request):
    employees = Employee.objects.filter(active=True).order_by("full_name")

    performance_rows = []

    for employee in employees:
        jobs_completed = Booking.objects.filter(
            assigned_employee=employee, status="completed"
        ).count()

        assigned_jobs = Booking.objects.filter(assigned_employee=employee).count()

        revenue_generated = (
            Booking.objects.filter(
                assigned_employee=employee, status="completed"
            ).aggregate(total=Sum("quoted_price"))["total"]
            or 0
        )

        attendance_logs = AttendanceLog.objects.filter(
            employee=employee, check_out_time__isnull=False
        )

        total_hours = 0

        for log in attendance_logs:
            if log.total_hours:
                total_hours += float(log.total_hours)

        payroll_total = (
            PayrollRecord.objects.filter(employee=employee).aggregate(
                total=Sum("gross_pay")
            )["total"]
            or 0
        )

        revenue_per_hour = 0
        efficiency = 0

        if total_hours > 0:
            revenue_per_hour = round(float(revenue_generated) / total_hours, 2)

        if payroll_total > 0:
            efficiency = round(
                (float(revenue_generated) / float(payroll_total)) * 100, 2
            )

        performance_rows.append(
            {
                "employee": employee,
                "assigned_jobs": assigned_jobs,
                "jobs_completed": jobs_completed,
                "total_hours": round(total_hours, 2),
                "revenue_generated": revenue_generated,
                "payroll_total": payroll_total,
                "revenue_per_hour": revenue_per_hour,
                "efficiency": efficiency,
            }
        )


    top_performer = max(
        performance_rows, key=lambda row: row["efficiency"], default=None
    )

    highest_revenue = max(
        performance_rows, key=lambda row: row["revenue_generated"], default=None
    )

    most_jobs_completed = max(
        performance_rows, key=lambda row: row["jobs_completed"], default=None
    )

    highest_efficiency = max(
        performance_rows, key=lambda row: row["efficiency"], default=None
    )

    employee_labels = [row["employee"].full_name for row in performance_rows]

    revenue_data = [float(row["revenue_generated"]) for row in performance_rows]

    jobs_data = [row["jobs_completed"] for row in performance_rows]

    efficiency_data = [float(row["efficiency"]) for row in performance_rows]

    return render(
        request,
        "employees/employee_performance.html",
        {
            "performance_rows": performance_rows,
            "top_performer": top_performer,
            "highest_revenue": highest_revenue,
            "most_jobs_completed": most_jobs_completed,
            "highest_efficiency": highest_efficiency,
            "employee_labels": employee_labels,
            "revenue_data": revenue_data,
            "jobs_data": jobs_data,
            "efficiency_data": efficiency_data,
        },
    )


# ==========================================================
# Activity Log Dashboard
# Purpose:
# Show recent CRM actions.
# ==========================================================


@login_required
def activity_log_list(request):

    activities = ActivityLog.objects.select_related("user").all()[:200]

    return render(request, "dashboard/core/activity_log.html", {"activities": activities})


# ==========================================================
# Business Health Dashboard
# Purpose:
# Owner-level overview of revenue, quotes, payroll and jobs.
# ==========================================================


@login_required
def business_health(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)
    next_month_start = (
        month_start.replace(year=month_start.year + 1, month=1)
        if month_start.month == 12
        else month_start.replace(month=month_start.month + 1)
    )
    total_revenue = (
        Booking.objects.filter(status="completed").aggregate(total=Sum("quoted_price"))[
            "total"
        ]
        or 0
    )

    monthly_revenue = (
        Booking.objects.filter(
            status="completed",
            booking_date__gte=month_start,
            booking_date__lt=next_month_start,
        ).aggregate(total=Sum("quoted_price"))["total"]
        or 0
    )

    completed_jobs = Booking.objects.filter(status="completed").count()

    average_job_value = 0

    if completed_jobs > 0:
        average_job_value = round(float(total_revenue) / completed_jobs, 2)

    total_quotes = QuoteRequest.objects.count()
    booked_quotes = QuoteRequest.objects.filter(
        status__in=["booked", "completed"]
    ).count()

    quote_conversion_rate = 0

    if total_quotes > 0:
        quote_conversion_rate = round((booked_quotes / total_quotes) * 100, 2)

    payroll_total = (
        PayrollRecord.objects.aggregate(total=Sum("gross_pay"))["total"] or 0
    )

    payroll_cost_percent = 0

    if total_revenue > 0:
        payroll_cost_percent = round(
            (float(payroll_total) / float(total_revenue)) * 100, 2
        )

    top_service = (
        Booking.objects.filter(status="completed")
        .values("service_type")
        .annotate(total=Count("id"))
        .order_by("-total")
        .first()
    )

    top_employee = (
        Booking.objects.filter(status="completed", assigned_employee__isnull=False)
        .values("assigned_employee__full_name")
        .annotate(total=Count("id"))
        .order_by("-total")
        .first()
    )

    upcoming_jobs = (
        Booking.objects.filter(booking_date__gte=today)
        .exclude(status="cancelled")
        .count()
    )

    pending_bookings = Booking.objects.filter(status="pending").count()

    return render(
        request,
        "dashboard/finance/business_health.html",
        {
            "today": today,
            "total_revenue": total_revenue,
            "monthly_revenue": monthly_revenue,
            "completed_jobs": completed_jobs,
            "average_job_value": average_job_value,
            "quote_conversion_rate": quote_conversion_rate,
            "payroll_total": payroll_total,
            "payroll_cost_percent": payroll_cost_percent,
            "top_service": top_service,
            "top_employee": top_employee,
            "upcoming_jobs": upcoming_jobs,
            "pending_bookings": pending_bookings,
        },
    )


@login_required
def financial_dashboard(request):
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    week_due_end = today + timedelta(days=7)

    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    next_month_start = (
        month_start.replace(year=month_start.year + 1, month=1)
        if month_start.month == 12
        else month_start.replace(month=month_start.month + 1)
    )
    next_year_start = year_start.replace(year=year_start.year + 1)

    paid_invoice_qs = Invoice.objects.filter(status="paid")
    today_revenue = paid_invoice_qs.filter(
        paid_at__date=today
    ).aggregate(total=Sum("total_amount"))["total"] or 0

    week_revenue = (
        paid_invoice_qs.filter(
            paid_at__date__gte=week_start,
            paid_at__date__lte=today,
        ).aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    month_revenue = (
        paid_invoice_qs.filter(
            paid_at__date__gte=month_start,
            paid_at__date__lt=next_month_start,
        ).aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    year_revenue = (
        paid_invoice_qs.filter(
            paid_at__date__gte=year_start,
            paid_at__date__lt=next_year_start,
        ).aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    paid_invoices = paid_invoice_qs.count()
    unpaid_invoices = Invoice.objects.exclude(status__in=["paid", "cancelled"]).count()
    overdue_invoices = Invoice.objects.filter(status="overdue").count()

    due_this_week = Invoice.objects.filter(
        status__in=["draft", "sent", "overdue"],
        due_date__gte=today,
        due_date__lte=week_due_end,
    ).count()

    outstanding_balance = (
        Invoice.objects.exclude(status__in=["paid", "cancelled"]).aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    payroll_total = (
        PayrollRecord.objects.filter(
            period_end__gte=year_start,
            period_end__lt=next_year_start,
        ).aggregate(total=Sum("gross_pay"))["total"]
        or 0
    )
    year_expenses = Expense.objects.filter(
        date__gte=year_start,
        date__lt=next_year_start,
    ).aggregate(total=Sum("amount"))["total"] or 0
    estimated_profit = year_revenue - payroll_total - year_expenses

    recent_outstanding_invoices = (
        Invoice.objects.exclude(status__in=["paid", "cancelled"])
        .select_related("booking", "booking__customer")
        .order_by("due_date", "-created_at")[:10]
    )

    # -----------------------------
    # Revenue Trend Chart
    # -----------------------------
    revenue_trend = (
        paid_invoice_qs.filter(
            paid_at__date__gte=year_start,
            paid_at__date__lt=next_year_start,
        )
        .annotate(day=TruncDate("paid_at"))
        .values("day")
        .annotate(total=Sum("total_amount"))
        .order_by("day")
    )

    revenue_labels = [
        item["day"].strftime("%d %b") for item in revenue_trend if item["day"]
    ]

    revenue_values = [float(item["total"] or 0) for item in revenue_trend]

    # -----------------------------
    # Top Customers
    # -----------------------------
    top_customers = Customer.objects.order_by("-total_revenue")[:10]

    customer_labels = [customer.full_name for customer in top_customers]

    customer_values = [float(customer.total_revenue) for customer in top_customers]

    return render(
        request,
        "dashboard/finance/financial_dashboard.html",
        {
            "today_revenue": today_revenue,
            "today": today,
            "week_revenue": week_revenue,
            "month_revenue": month_revenue,
            "year_revenue": year_revenue,
            "paid_invoices": paid_invoices,
            "unpaid_invoices": unpaid_invoices,
            "overdue_invoices": overdue_invoices,
            "due_this_week": due_this_week,
            "outstanding_balance": outstanding_balance,
            "payroll_total": payroll_total,
            "year_expenses": year_expenses,
            "estimated_profit": estimated_profit,
            "recent_outstanding_invoices": recent_outstanding_invoices,
            "revenue_labels": revenue_labels,
            "revenue_values": revenue_values,
            "customer_labels": customer_labels,
            "customer_values": customer_values,
        },
    )


@login_required
def executive_dashboard(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)

    total_revenue = (
        Invoice.objects.filter(status="paid").aggregate(total=Sum("total_amount"))[
            "total"
        ]
        or 0
    )

    monthly_revenue = (
        Invoice.objects.filter(status="paid", paid_at__date__gte=month_start).aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    outstanding_balance = (
        Invoice.objects.exclude(status__in=["paid", "cancelled"]).aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    payroll_total = (
        PayrollRecord.objects.aggregate(total=Sum("gross_pay"))["total"] or 0
    )

    profit_estimate = float(total_revenue) - float(payroll_total)

    payroll_percent = 0
    if total_revenue:
        payroll_percent = round((float(payroll_total) / float(total_revenue)) * 100, 2)

    total_quotes = QuoteRequest.objects.count()
    booked_quotes = QuoteRequest.objects.filter(
        status__in=["booked", "completed"]
    ).count()

    conversion_rate = 0
    if total_quotes:
        conversion_rate = round((booked_quotes / total_quotes) * 100, 2)

    upcoming_jobs = (
        Booking.objects.filter(booking_date__gte=today)
        .exclude(status="cancelled")
        .count()
    )

    pending_bookings = Booking.objects.filter(status="pending").count()

    top_service = (
        Booking.objects.filter(status="completed")
        .values("service_type")
        .annotate(total=Count("id"))
        .order_by("-total")
        .first()
    )

    top_employee = (
        Booking.objects.filter(status="completed", assigned_employee__isnull=False)
        .values("assigned_employee__full_name")
        .annotate(total=Count("id"))
        .order_by("-total")
        .first()
    )

    recent_activity = ActivityLog.objects.select_related("user").all()[:10]

    return render(
        request,
        "dashboard/finance/executive_dashboard.html",
        {
            "total_revenue": total_revenue,
            "monthly_revenue": monthly_revenue,
            "outstanding_balance": outstanding_balance,
            "payroll_total": payroll_total,
            "profit_estimate": profit_estimate,
            "payroll_percent": payroll_percent,
            "conversion_rate": conversion_rate,
            "upcoming_jobs": upcoming_jobs,
            "pending_bookings": pending_bookings,
            "top_service": top_service,
            "top_employee": top_employee,
            "recent_activity": recent_activity,
        },
    )


@login_required
def reminder_center(request):
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)
    week_end = today + timedelta(days=7)
    overdue_quote_date = today - timedelta(days=2)

    overdue_invoices = (
        Invoice.objects.exclude(status="paid")
        .filter(due_date__lt=today)
        .select_related("booking__customer")
        .order_by("due_date")
    )

    jobs_tomorrow = (
        Booking.objects.filter(booking_date=tomorrow)
        .exclude(status="cancelled")
        .select_related("customer", "assigned_employee")
        .order_by("booking_time")
    )

    upcoming_jobs = (
        Booking.objects.filter(booking_date__gte=today, booking_date__lte=week_end)
        .exclude(status="cancelled")
        .select_related("customer", "assigned_employee")
        .order_by("booking_date", "booking_time")
    )

    unassigned_jobs = (
        Booking.objects.filter(assigned_employee__isnull=True, booking_date__gte=today)
        .exclude(status="cancelled")
        .select_related("customer")
        .order_by("booking_date", "booking_time")
    )

    pending_quotes = QuoteRequest.objects.filter(
        status__in=["new", "contacted", "quoted"],
        created_at__date__lte=overdue_quote_date,
    ).order_by("created_at")

    urgent_count = (
        overdue_invoices.count() + unassigned_jobs.count() + pending_quotes.count()
    )

    return render(
        request,
        "dashboard/communications/reminder_center.html",
        {
            "today": today,
            "tomorrow": tomorrow,
            "overdue_invoices": overdue_invoices,
            "jobs_tomorrow": jobs_tomorrow,
            "upcoming_jobs": upcoming_jobs,
            "unassigned_jobs": unassigned_jobs,
            "pending_quotes": pending_quotes,
            "urgent_count": urgent_count,
        },
    )


# ==========================================================
# Email Center
# Purpose:
# Send invoice reminders, booking reminders and quote follow-ups.
# ==========================================================


@login_required
def email_center(request):
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)
    overdue_quote_date = today - timedelta(days=2)

    overdue_invoices = (
        Invoice.objects.exclude(status="paid")
        .filter(due_date__lt=today)
        .order_by("due_date")
    )

    tomorrow_bookings = (
        Booking.objects.filter(booking_date=tomorrow)
        .exclude(status="cancelled")
        .order_by("booking_time")
    )

    quote_followups = QuoteRequest.objects.filter(
        status__in=["new", "contacted", "quoted"],
        created_at__date__lte=overdue_quote_date,
    ).order_by("created_at")

    return render(
        request,
        "dashboard/communications/email_center.html",
        {
            "overdue_invoices": overdue_invoices,
            "tomorrow_bookings": tomorrow_bookings,
            "quote_followups": quote_followups,
        },
    )


@require_POST
@admin_required
@permission_required(
    ("invoices.change_invoice", "dashboard.add_emaillog"),
    raise_exception=True,
)
def send_invoice_reminder(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    customer = invoice.booking.customer

    if not customer or not customer.email:
        messages.error(
            request,
            "❌ The booking has no customer with an email address.",
        )
        return redirect("email_center")

    subject = f"Payment Reminder - Invoice {invoice.invoice_number}"

    # Build the customer payment URL.
    payment_url = request.build_absolute_uri(
        reverse(
            "create_stripe_checkout_session",
            kwargs={"invoice_id": invoice.id},
        )
    )

    context = {
        "invoice": invoice,
        "customer": customer,
        "payment_url": payment_url,
    }

    # Render both HTML and plain-text versions.
    html_message = render_to_string(
        "invoices/reminder.html",
        context,
    )

    text_message = render_to_string(
        "invoices/reminder.txt",
        context,
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[customer.email],
    )

    email.attach_alternative(
        html_message,
        "text/html",
    )

    # Attach invoice PDF.
    pdf_buffer = generate_invoice_pdf(invoice)

    email.attach(
        f"{invoice.invoice_number}.pdf",
        pdf_buffer.getvalue(),
        "application/pdf",
    )

    # Send through the existing Resend email backend.
    email.send(fail_silently=False)

    # Record email activity.
    EmailLog.objects.create(
        sent_by=request.user,
        email_type="invoice_reminder",
        recipient_name=customer.full_name,
        recipient_email=customer.email,
        subject=subject,
        related_object=invoice.invoice_number,
    )

    create_activity_log(
        request.user,
        "invoice",
        "Invoice Reminder Sent",
        f"Reminder sent for {invoice.invoice_number} to {customer.full_name}.",
    )

    messages.success(
        request,
        "✅ Invoice reminder email sent successfully.",
    )

    return redirect("email_center")

@require_POST
@admin_required
@permission_required(
    ("bookings.change_booking", "dashboard.add_emaillog"),
    raise_exception=True,
)
def send_booking_reminder(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    customer = booking.customer

    if request.method == "POST":
        if customer and customer.email:
            subject = "Cleaning Booking Reminder"

            message = f"""
Dear {customer.full_name},

This is a reminder for your upcoming cleaning booking.

Service: {booking.service_type}
Date: {booking.booking_date}
Time: {booking.booking_time}
Address: {booking.address}, {booking.suburb_postcode}

Thank you,
YD Commercial Cleaning Services
"""

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [customer.email],
                fail_silently=False,
            )

            EmailLog.objects.create(
                sent_by=request.user,
                email_type="booking_reminder",
                recipient_name=customer.full_name,
                recipient_email=customer.email,
                subject=subject,
                related_object=f"Booking #{booking.id}",
            )

            create_activity_log(
                request.user,
                "booking",
                "Booking Reminder Sent",
                f"Reminder sent to {customer.full_name} for booking #{booking.id}.",
            )

            messages.success(request, "✅ Booking reminder email sent successfully.")
        else:
            messages.error(request, "❌ Customer does not have an email address.")

    return redirect("email_center")

@require_POST
@admin_required
@permission_required(
    ("quotes.change_quoterequest", "dashboard.add_emaillog"),
    raise_exception=True,
)
def send_quote_followup(request, quote_id):
    quote = get_object_or_404(QuoteRequest, id=quote_id)

    if not quote.email:
        messages.error(
            request,
            "❌ Quote request does not have an email address."
        )
        return redirect("email_center")

    # ---------------------------------------------------------
    # Customer details
    # ---------------------------------------------------------

    customer_name = (quote.name or "Customer").strip()

    property_type = (
        str(quote.property_type).strip()
        if quote.property_type
        else "To be confirmed"
    )

    suburb_postcode = (
        str(quote.suburb_postcode).strip()
        if quote.suburb_postcode
        else "To be confirmed"
    )

    # ---------------------------------------------------------
    # Preferred date
    # ---------------------------------------------------------

    if quote.preferred_date:
        try:
            preferred_date = quote.preferred_date.strftime(
                "%d %B %Y"
            )
        except (AttributeError, TypeError):
            preferred_date = str(quote.preferred_date)
    else:
        preferred_date = "To be confirmed"

    # ---------------------------------------------------------
    # Quote reference
    # ---------------------------------------------------------

    quote_reference = f"YD-Q-{quote.id:05d}"

    subject = (
        f"Following Up on Your Cleaning Quote — "
        f"{quote_reference}"
    )

    # ---------------------------------------------------------
    # Email context
    # ---------------------------------------------------------

    context = {
        "email_subject": subject,
        "preheader": (
            f"We're following up regarding your cleaning quote "
            f"{quote_reference}."
        ),
        "customer_name": customer_name,
        "quote_reference": quote_reference,
        "property_type": property_type,
        "suburb_postcode": suburb_postcode,
        "preferred_date": preferred_date,
        "business_email": settings.DEFAULT_FROM_EMAIL,
    }

    # ---------------------------------------------------------
    # Render HTML + plain text
    # ---------------------------------------------------------

    html_message = render_to_string(
        "emails/quotes/followup.html",
        context,
    )

    text_message = render_to_string(
        "emails/quotes/followup.txt",
        context,
    )

    # ---------------------------------------------------------
    # Send email
    # ---------------------------------------------------------

    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[quote.email],
            reply_to=[settings.DEFAULT_FROM_EMAIL],
        )

        email.attach_alternative(
            html_message,
            "text/html",
        )

        email.send(fail_silently=False)

        # -----------------------------------------------------
        # Email log
        # -----------------------------------------------------

        EmailLog.objects.create(
            sent_by=request.user,
            email_type="quote_followup",
            recipient_name=customer_name,
            recipient_email=quote.email,
            subject=subject,
            related_object=f"Quote #{quote.id}",
        )

        # -----------------------------------------------------
        # Activity log
        # -----------------------------------------------------

        create_activity_log(
            request.user,
            "quote",
            "Quote Follow-up Sent",
            f"Follow-up email sent to {customer_name}.",
        )

        messages.success(
            request,
            "✅ Quote follow-up email sent successfully."
        )

    except Exception:
        logger.exception(
            "Failed to send quote follow-up email for Quote #%s",
            quote.id,
        )

        messages.error(
            request,
            "❌ We couldn't send the quote follow-up email. "
            "Please try again."
        )

    return redirect("email_center")


@login_required
def email_log_list(request):
    email_logs = EmailLog.objects.select_related("sent_by").all()[:200]

    return render(request, "dashboard/communications/email_log_list.html", {"email_logs": email_logs})


@login_required
def customer_analytics(request):

    total_customers = Customer.objects.count()

    current_month = timezone.now().month
    current_year = timezone.now().year

    new_customers = Customer.objects.filter(
        created_at__month=current_month, created_at__year=current_year
    ).count()

    repeat_customers = Customer.objects.filter(jobs_completed__gt=1).count()

    retention_rate = 0

    if total_customers > 0:
        retention_rate = round((repeat_customers / total_customers) * 100, 2)

    top_customers = Customer.objects.order_by("-total_revenue")[:10]

    customer_labels = [customer.full_name for customer in top_customers]

    revenue_data = [float(customer.total_revenue) for customer in top_customers]

    booking_data = [customer.jobs_completed for customer in top_customers]

    return render(
        request,
        "customers/customer_analytics.html",
        {
            "total_customers": total_customers,
            "new_customers": new_customers,
            "repeat_customers": repeat_customers,
            "retention_rate": retention_rate,
            "top_customers": top_customers,
            "customer_labels": customer_labels,
            "revenue_data": revenue_data,
            "booking_data": booking_data,
        },
    )


@login_required
def customer_behaviour(request):
    """
    Website visitor behaviour dashboard.

    This is separate from Customer Analytics.

    Customer Analytics:
        Tracks existing customers and their business activity.

    Customer Behaviour:
        Tracks anonymous website visitors and their interactions
        with the YD Cleaning website.
    """

    now = timezone.now()

    today_start = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    last_30_days = now - timedelta(days=30)

    # ---------------------------------------------
    # Visitor statistics
    # ---------------------------------------------

    total_visitors = Visitor.objects.count()

    visitors_today = Visitor.objects.filter(
        first_seen__gte=today_start
    ).count()

    visitors_30_days = Visitor.objects.filter(
        first_seen__gte=last_30_days
    ).count()

    returning_visitors = Visitor.objects.filter(
        is_returning=True
    ).count()

    # ---------------------------------------------
    # Session statistics
    # ---------------------------------------------

    sessions_today = VisitorSession.objects.filter(
        started_at__gte=today_start
    ).count()

    active_sessions = VisitorSession.objects.filter(
        is_active=True,
        last_activity__gte=now - timedelta(minutes=5),
    ).count()

    # ---------------------------------------------
    # Page views
    # ---------------------------------------------

    page_views_today = ActivityEvent.objects.filter(
        event_type="PAGE_VIEW",
        created_at__gte=today_start,
    ).count()

    page_views_30_days = ActivityEvent.objects.filter(
        event_type="PAGE_VIEW",
        created_at__gte=last_30_days,
    ).count()

    # ---------------------------------------------
    # Customer intent / conversion actions
    # ---------------------------------------------

    phone_clicks = ActivityEvent.objects.filter(
        event_type="PHONE_CLICK",
        created_at__gte=last_30_days,
    ).count()

    email_clicks = ActivityEvent.objects.filter(
        event_type="EMAIL_CLICK",
        created_at__gte=last_30_days,
    ).count()

    quote_starts = ActivityEvent.objects.filter(
        event_type="QUOTE_START",
        created_at__gte=last_30_days,
    ).count()

    quote_submissions = ActivityEvent.objects.filter(
        event_type="QUOTE_SUBMIT",
        created_at__gte=last_30_days,
    ).count()

    booking_starts = ActivityEvent.objects.filter(
        event_type="BOOKING_START",
        created_at__gte=last_30_days,
    ).count()

    booking_completions = ActivityEvent.objects.filter(
        event_type="BOOKING_COMPLETE",
        created_at__gte=last_30_days,
    ).count()

    # ---------------------------------------------
    # Most visited pages
    # ---------------------------------------------

    popular_pages = (
        ActivityEvent.objects
        .filter(
            event_type="PAGE_VIEW",
            created_at__gte=last_30_days,
        )
        .exclude(page_url="")
        .values("page_url")
        .annotate(total=Count("id"))
        .order_by("-total")[:15]
    )

    # ---------------------------------------------
    # Most clicked elements
    # ---------------------------------------------

    popular_clicks = (
        ActivityEvent.objects
        .filter(
            event_type__in=[
                "CLICK",
                "CTA_CLICK",
                "PHONE_CLICK",
                "EMAIL_CLICK",
                "QUOTE_START",
                "BOOKING_START",
            ],
            created_at__gte=last_30_days,
        )
        .exclude(element="")
        .values(
            "event_type",
            "element",
        )
        .annotate(total=Count("id"))
        .order_by("-total")[:15]
    )

    # ---------------------------------------------
    # Popular website searches
    # ---------------------------------------------

    popular_searches = (
        SearchEvent.objects
        .filter(
            created_at__gte=last_30_days,
        )
        .values("query")
        .annotate(total=Count("id"))
        .order_by("-total")[:15]
    )

    # ---------------------------------------------
    # Device breakdown
    # ---------------------------------------------

    devices = (
        Visitor.objects
        .exclude(device_type="")
        .values("device_type")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    # ---------------------------------------------
    # Recent visitor activity
    # ---------------------------------------------

    recent_activity = (
        ActivityEvent.objects
        .select_related("visitor", "session")
        .order_by("-created_at")[:30]
    )

    context = {
        "total_visitors": total_visitors,
        "visitors_today": visitors_today,
        "visitors_30_days": visitors_30_days,
        "returning_visitors": returning_visitors,

        "sessions_today": sessions_today,
        "active_sessions": active_sessions,

        "page_views_today": page_views_today,
        "page_views_30_days": page_views_30_days,

        "phone_clicks": phone_clicks,
        "email_clicks": email_clicks,
        "quote_starts": quote_starts,
        "quote_submissions": quote_submissions,
        "booking_starts": booking_starts,
        "booking_completions": booking_completions,

        "popular_pages": popular_pages,
        "popular_clicks": popular_clicks,
        "popular_searches": popular_searches,

        "devices": devices,

        "recent_activity": recent_activity,
    }

    return render(
        request,
        "customers/customer_behaviour.html",
        context,
    )

@login_required
def review_requests(request):
    completed_bookings = Booking.objects.filter(status="completed").select_related(
        "customer", "review_request_log"
    ).order_by("-booking_date", "-pk")
    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    if query:
        completed_bookings = completed_bookings.filter(
            Q(customer__full_name__icontains=query)
            | Q(customer__email__icontains=query)
            | Q(service_type__icontains=query)
        )
    if status_filter == "sent":
        completed_bookings = completed_bookings.filter(
            review_request_log__isnull=False
        )
    elif status_filter == "not_sent":
        completed_bookings = completed_bookings.filter(
            review_request_log__isnull=True
        )
    else:
        status_filter = ""
    paginator = Paginator(completed_bookings, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "dashboard/reviews/review_requests.html",
        {
            "completed_bookings": page_obj.object_list,
            "page_obj": page_obj,
            "query": query,
            "status_filter": status_filter,
            "eligible_count": Booking.objects.filter(
                status="completed",
                review_request_log__isnull=True,
            ).exclude(customer__email="").exclude(customer__email__isnull=True).count(),
            "requests_sent": ReviewRequestLog.objects.count(),
        },
    )

@require_POST
@admin_required
@permission_required(
    (
        "bookings.view_booking",
        "dashboard.add_reviewrequestlog",
        "dashboard.change_reviewrequestlog",
        "dashboard.add_emaillog",
        "dashboard.add_activitylog",
    ),
    raise_exception=True,
)
def send_review_request(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related("customer"),
        id=booking_id,
    )

    customer = booking.customer

    if not customer.email:
        messages.error(
            request,
            "❌ This customer does not have an email address.",
        )
        return redirect("review_requests")

    subject = "We'd Love Your Feedback — YD Commercial Cleaning Services"

    review_link = "https://g.page/r/CXH9ygKf16Y4EBM/review"

    email_context = {
        "customer": customer,
        "customer_name": customer.full_name,
        "booking": booking,
        "review_link": review_link,
    }

    html_message = render_to_string(
        "emails/reviews/review_request.html",
        email_context,
    )

    text_message = render_to_string(
        "emails/reviews/review_request.txt",
        email_context,
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[customer.email],
    )

    email.attach_alternative(
        html_message,
        "text/html",
    )

    email.send(fail_silently=False)

    EmailLog.objects.create(
        sent_by=request.user,
        email_type="system",
        recipient_name=customer.full_name,
        recipient_email=customer.email,
        subject=subject,
        related_object=f"Review Request Booking #{booking.id}",
    )

    review_log, created = ReviewRequestLog.objects.get_or_create(
        booking=booking,
        defaults={
            "sent_by": request.user,
            "sent_count": 1,
            "last_sent_at": timezone.now(),
        },
    )

    if not created:
        review_log.sent_count += 1
        review_log.sent_by = request.user
        review_log.last_sent_at = timezone.now()
        review_log.save(
            update_fields=[
                "sent_count",
                "sent_by",
                "last_sent_at",
                "updated_at",
            ]
        )

    create_activity_log(
        request.user,
        "review",
        "Review Request Sent",
        f"Review request sent to {customer.full_name}",
    )

    messages.success(
        request,
        "✅ Review request email sent.",
    )

    return redirect("review_requests")

@login_required
def review_analytics(request):
    total_reviews = Review.objects.count()

    featured_reviews = Review.objects.filter(featured=True).count()

    average_rating = Review.objects.aggregate(average=Avg("rating"))["average"] or 0

    average_rating = round(average_rating, 2)

    five_star_reviews = Review.objects.filter(rating=5).count()

    review_requests_sent = ReviewRequestLog.objects.count()

    completed_booking_queryset = Booking.objects.filter(status="completed")
    completed_bookings = completed_booking_queryset.count()
    completed_bookings_with_request = completed_booking_queryset.filter(
        review_request_log__isnull=False
    ).count()
    review_request_coverage = (
        round((completed_bookings_with_request / completed_bookings) * 100, 2)
        if completed_bookings
        else 0
    )

    rating_breakdown = {
        "five": Review.objects.filter(rating=5).count(),
        "four": Review.objects.filter(rating=4).count(),
        "three": Review.objects.filter(rating=3).count(),
        "two": Review.objects.filter(rating=2).count(),
        "one": Review.objects.filter(rating=1).count(),
    }
    lower_rating_reviews = (
        rating_breakdown["three"]
        + rating_breakdown["two"]
        + rating_breakdown["one"]
    )
    rating_rows = [
        (rating, rating_breakdown[label])
        for rating, label in ((5, "five"), (4, "four"), (3, "three"), (2, "two"), (1, "one"))
    ]

    latest_reviews = Review.objects.order_by("-created_at")[:10]

    return render(
        request,
        "dashboard/reviews/review_analytics.html",
        {
            "total_reviews": total_reviews,
            "featured_reviews": featured_reviews,
            "average_rating": average_rating,
            "five_star_reviews": five_star_reviews,
            "review_requests_sent": review_requests_sent,
            "review_request_coverage": review_request_coverage,
            "completed_bookings_with_request": completed_bookings_with_request,
            "completed_bookings": completed_bookings,
            "rating_breakdown": rating_breakdown,
            "lower_rating_reviews": lower_rating_reviews,
            "rating_rows": rating_rows,
            "latest_reviews": latest_reviews,
        },
    )


@login_required
def customer_loyalty(request):

    customers = Customer.objects.all().order_by("-total_revenue")

    vip_count = 0
    repeat_count = 0
    new_count = 0

    loyalty_rows = []

    for customer in customers:

        if customer.total_revenue >= 1000 or customer.jobs_completed >= 5:
            level = "VIP"
            vip_count += 1

        elif customer.jobs_completed >= 2:
            level = "Repeat"
            repeat_count += 1

        else:
            level = "New"
            new_count += 1

        loyalty_rows.append(
            {
                "customer": customer,
                "level": level,
            }
        )

    return render(
        request,
        "customers/customer_loyalty.html",
        {
            "loyalty_rows": loyalty_rows,
            "vip_count": vip_count,
            "repeat_count": repeat_count,
            "new_count": new_count,
            "total_customers": customers.count(),
        },
    )


@login_required
def customer_profile_360(request, customer_id):

    customer = get_object_or_404(Customer, id=customer_id)

    bookings = Booking.objects.filter(customer=customer).order_by("-booking_date")

    invoices = Invoice.objects.filter(booking__customer=customer).order_by(
        "-created_at"
    )

    reviews = Review.objects.filter(customer_name=customer.full_name).order_by(
        "-created_at"
    )

    email_logs = EmailLog.objects.filter(recipient_email=customer.email).order_by(
        "-sent_at"
    )[:20]

    total_bookings = bookings.count()

    outstanding_invoices = invoices.exclude(status="paid").count()

    total_quotes = QuoteRequest.objects.filter(email=customer.email).count()

    completed_bookings = bookings.filter(status="completed").count()

    total_spent = (
        invoices.filter(status="paid").aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    customer_lifetime_value = 0

    if total_bookings > 0:

        customer_lifetime_value = round(total_spent / total_bookings, 2)

    last_booking = bookings.first()

    customer_risk = "New Customer"

    if last_booking:

        days_since_last_booking = (
            timezone.localdate() - last_booking.booking_date
        ).days

        if days_since_last_booking >= 120:
            customer_risk = "High Risk"

        elif days_since_last_booking >= 60:
            customer_risk = "Medium Risk"

        else:
            customer_risk = "Active Customer"
    else:
        days_since_last_booking = None

    loyalty_level = "New"

    if customer.total_revenue >= 1000 or customer.jobs_completed >= 5:
        loyalty_level = "VIP"

    elif customer.jobs_completed >= 2:
        loyalty_level = "Repeat"

    timeline_events = []

    for booking in bookings:
        timeline_events.append(
            {
                "date": booking.created_at,
                "type": "Booking",
                "title": "Booking Created",
                "description": f"{booking.service_type} booked for {booking.booking_date}",
            }
        )

        if booking.status == "completed":
            timeline_events.append(
                {
                    "date": timezone.make_aware(
                        datetime.combine(booking.booking_date, time.min)
                    ),
                    "type": "Job",
                    "title": "Job Completed",
                    "description": f"{booking.service_type} marked as completed.",
                }
            )

    for invoice in invoices:
        timeline_events.append(
            {
                "date": invoice.created_at,
                "type": "Invoice",
                "title": "Invoice Created",
                "description": (
                    f"{invoice.invoice_number} - ${invoice.total_amount:.2f}"
                ),
            }
        )

        if invoice.status == "paid" and invoice.paid_at:
            timeline_events.append(
                {
                    "date": invoice.paid_at,
                    "type": "Payment",
                    "title": "Invoice Paid",
                    "description": f"{invoice.invoice_number} was paid.",
                }
            )

    for review in reviews:
        timeline_events.append(
            {
                "date": review.created_at,
                "type": "Review",
                "title": "Review Added",
                "description": f"{review.rating} star review added.",
            }
        )

    for email in email_logs:
        timeline_events.append(
            {
                "date": email.sent_at,
                "type": "Email",
                "title": email.get_email_type_display(),
                "description": email.subject,
            }
        )

    timeline_events = sorted(
        timeline_events,
        key=lambda item: (
            datetime.combine(item["date"], time.min)
            if not isinstance(item["date"], datetime)
            else item["date"]
        ),
        reverse=True,
    )

    return render(
        request,
        "customers/customer_profile_360.html",
        {
            "customer": customer,
            "bookings": bookings,
            "invoices": invoices,
            "reviews": reviews,
            "email_logs": email_logs,
            "total_bookings": total_bookings,
            "completed_bookings": completed_bookings,
            "outstanding_invoices": outstanding_invoices,
            "total_quotes": total_quotes,
            "total_spent": total_spent,
            "customer_lifetime_value": customer_lifetime_value,
            "customer_risk": customer_risk,
            "days_since_last_booking": days_since_last_booking,
            "loyalty_level": loyalty_level,
            "timeline_events": timeline_events,
        },
    )


@login_required
def employee_bonuses(request):
    employees = Employee.objects.filter(active=True).order_by("full_name")

    bonus_rows = []

    total_bonus = 0
    top_bonus_employee = None

    for employee in employees:
        completed_bookings = Booking.objects.filter(
            assigned_employee=employee, status="completed"
        )

        jobs_completed = completed_bookings.count()

        revenue_generated = (
            completed_bookings.aggregate(total=Sum("quoted_price"))["total"] or 0
        )

        # Bonus Rule:
        # 5% of revenue generated from completed jobs.
        revenue_bonus = float(revenue_generated) * 0.05

        # Bonus Rule:
        # $10 per completed job.
        job_bonus = jobs_completed * 10

        total_employee_bonus = round(revenue_bonus + job_bonus, 2)

        total_bonus += total_employee_bonus

        row = {
            "employee": employee,
            "jobs_completed": jobs_completed,
            "revenue_generated": revenue_generated,
            "revenue_bonus": round(revenue_bonus, 2),
            "job_bonus": job_bonus,
            "total_bonus": total_employee_bonus,
        }

        bonus_rows.append(row)

        if (
            top_bonus_employee is None
            or total_employee_bonus > top_bonus_employee["total_bonus"]
        ):
            top_bonus_employee = row

    bonus_rows = sorted(bonus_rows, key=lambda row: row["total_bonus"], reverse=True)

    return render(
        request,
        "employees/employee_bonuses.html",
        {
            "bonus_rows": bonus_rows,
            "total_bonus": round(total_bonus, 2),
            "top_bonus_employee": top_bonus_employee,
            "bonus_rate": 5,
            "job_bonus_amount": 10,
        },
    )


@login_required
@require_POST
@permission_required(
    (
        "customers.add_marketingsubscriber",
        "customers.change_marketingsubscriber",
        "dashboard.add_emaillog",
        "dashboard.add_activitylog",
    ),
    raise_exception=True,
)
def dashboard_newsletter_subscribe(request):
    if request.method != "POST":
        return redirect("campaign_center")

    form = MarketingSignupForm(request.POST)

    if not form.is_valid():
        messages.error(
            request,
            "Please enter a valid email address and confirm newsletter consent.",
        )
        return redirect("campaign_center")

    email = form.cleaned_data["email"]

    subscriber, created = MarketingSubscriber.objects.get_or_create(
        email=email,
        defaults={
            "consent_given": True,
            "consented_at": timezone.now(),
            "source": "dashboard_newsletter",
            "is_active": True,
        },
    )

    if not created:
        subscriber.consent_given = True
        subscriber.consented_at = timezone.now()
        subscriber.is_active = True
        subscriber.save(
            update_fields=[
                "consent_given",
                "consented_at",
                "is_active",
                "updated_at",
            ]
        )

    customer_subject = "Welcome to YD Commercial Cleaning Services"

    customer_message = f"""Hello,

Thank you for subscribing to the YD Commercial Cleaning Services newsletter.

You will now receive our latest cleaning offers, updates and promotions.

Thank you,
YD Commercial Cleaning Services
"""

    company_subject = "New Newsletter Subscriber"

    company_message = f"""A new newsletter subscriber has been added.

Email: {email}
Source: Dashboard Newsletter
Status: Active
"""

    try:
        send_mail(
            customer_subject,
            customer_message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )

        EmailLog.objects.create(
            sent_by=request.user,
            email_type="system",
            recipient_name="Newsletter Subscriber",
            recipient_email=email,
            subject=customer_subject,
            related_object="Newsletter Subscription",
        )

        admin_email = getattr(settings, "ADMIN_EMAIL", "").strip()

        if admin_email:
            send_mail(
                company_subject,
                company_message,
                settings.DEFAULT_FROM_EMAIL,
                [admin_email],
                fail_silently=False,
            )

            EmailLog.objects.create(
                sent_by=request.user,
                email_type="system",
                recipient_name="YD Commercial Cleaning Services",
                recipient_email=admin_email,
                subject=company_subject,
                related_object="Newsletter Subscription",
            )

        create_activity_log(
            request.user,
            "customer",
            "Newsletter Subscriber Added",
            f"Newsletter subscriber added: {email}",
        )

        messages.success(
            request,
            f"Newsletter subscription saved and confirmation sent to {email}.",
        )

    except Exception:
        logging.exception("Newsletter subscription email failed for %s", email)

        messages.warning(
            request,
            f"Newsletter subscription was saved for {email}, but the email notification could not be sent.",
        )

    return redirect("campaign_center")


@login_required
def newsletter_subscriber_detail(request, subscriber_id):
    subscriber = get_object_or_404(
        MarketingSubscriber,
        id=subscriber_id,
    )

    return render(
        request,
        "dashboard/marketing/newsletter_subscriber_detail.html",
        {
            "subscriber": subscriber,
        },
    )


@login_required
def edit_newsletter_subscriber(request, subscriber_id):
    subscriber = get_object_or_404(
        MarketingSubscriber,
        id=subscriber_id,
    )

    if request.method == "POST":
        form = MarketingSubscriberForm(
            request.POST,
            instance=subscriber,
        )

        if form.is_valid():
            updated_subscriber = form.save()

            create_activity_log(
                request.user,
                "customer",
                "Newsletter Subscriber Updated",
                f"Newsletter subscriber {updated_subscriber.email} was updated.",
            )

            messages.success(
                request,
                "✅ Newsletter subscriber updated successfully.",
            )

            return redirect(
                "newsletter_subscriber_detail",
                subscriber_id=updated_subscriber.pk,
            )

        messages.error(
            request,
            "❌ Please check the newsletter subscriber form.",
        )

    else:
        form = MarketingSubscriberForm(instance=subscriber)

    return render(
        request,
        "dashboard/marketing/newsletter_subscriber_form.html",
        {
            "form": form,
            "subscriber": subscriber,
            "page_title": "Edit Newsletter Subscriber",
            "button_text": "Update Subscriber",
        },
    )


@admin_required
@require_http_methods(["GET", "POST"])
def delete_newsletter_subscriber(request, subscriber_id):
    subscriber = get_object_or_404(
        MarketingSubscriber,
        id=subscriber_id,
    )

    subscriber_email = subscriber.email

    if request.method == "POST":
        subscriber.delete()

        create_activity_log(
            request.user,
            "customer",
            "Newsletter Subscriber Deleted",
            f"Newsletter subscriber {subscriber_email} was removed.",
        )

        messages.success(
            request,
            "✅ Newsletter subscriber deleted successfully.",
        )

        return redirect("campaign_center")

    return render(
        request,
        "dashboard/marketing/newsletter_subscriber_confirm_delete.html",
        {
            "subscriber": subscriber,
        },
    )


def _customers_with_marketing_consent(customers):
    consenting_emails = {
        email.casefold()
        for email in MarketingSubscriber.objects.filter(
            is_active=True,
            consent_given=True,
        ).values_list("email", flat=True)
    }
    return [
        customer
        for customer in customers
        if customer.email and customer.email.casefold() in consenting_emails
    ]


@login_required
def campaign_history_detail(request, campaign_id):
    campaign = get_object_or_404(
        CampaignLog,
        id=campaign_id,
    )

    return render(
        request,
        "dashboard/marketing/campaign_history_detail.html",
        {
            "campaign": campaign,
        },
    )


@login_required
def edit_campaign_history(request, campaign_id):
    campaign = get_object_or_404(
        CampaignLog,
        id=campaign_id,
    )

    if request.method == "POST":
        form = CampaignLogForm(
            request.POST,
            instance=campaign,
        )

        if form.is_valid():
            updated_campaign = form.save()

            create_activity_log(
                request.user,
                "campaign",
                "Campaign History Updated",
                f"Campaign history '{updated_campaign.title}' was updated.",
            )

            messages.success(
                request,
                "✅ Campaign history updated successfully.",
            )

            return redirect(
                "campaign_history_detail",
                campaign_id=updated_campaign.pk,
            )

        messages.error(
            request,
            "❌ Please check the campaign form.",
        )

    else:
        form = CampaignLogForm(instance=campaign)

    return render(
        request,
        "dashboard/marketing/campaign_history_form.html",
        {
            "form": form,
            "campaign": campaign,
            "page_title": "Edit Campaign History",
            "button_text": "Update Campaign",
        },
    )


@admin_required
@require_http_methods(["GET", "POST"])
def delete_campaign_history(request, campaign_id):
    campaign = get_object_or_404(
        CampaignLog,
        id=campaign_id,
    )

    campaign_title = campaign.title

    if request.method == "POST":
        campaign.delete()

        create_activity_log(
            request.user,
            "campaign",
            "Campaign History Deleted",
            f"Campaign history '{campaign_title}' was removed.",
        )

        messages.success(
            request,
            "✅ Campaign history deleted successfully.",
        )

        return redirect("campaign_center")

    return render(
        request,
        "dashboard/marketing/campaign_confirm_delete.html",
        {
            "campaign": campaign,
        },
    )


@login_required
def campaign_center(request):
    vip_customers = _customers_with_marketing_consent(
        Customer.objects.filter(total_revenue__gte=1000)
        .exclude(email="")
        .exclude(email__isnull=True)
        .order_by("-total_revenue")
    )

    inactive_customers = _customers_with_marketing_consent(
        Customer.objects.filter(jobs_completed__lte=1)
        .exclude(email="")
        .exclude(email__isnull=True)
        .order_by("full_name")
    )

    # -----------------------------------------------------
    # Review campaign eligibility
    # -----------------------------------------------------

    completed_bookings = (
        Booking.objects
        .filter(status="completed")
        .select_related("customer")
    )

    # Completed bookings that already received a review request.
    review_already_requested = ReviewRequestLog.objects.filter(
        booking__status="completed"
    ).count()

    # Completed bookings without a review request and with an email.
    review_opportunities = completed_bookings.filter(
        review_request_log__isnull=True,
    ).exclude(
        customer__email=""
    ).exclude(
        customer__email__isnull=True
    )

    # Completed bookings where the customer has no email.
    review_missing_email = completed_bookings.filter(
        Q(customer__email__isnull=True) |
        Q(customer__email="")
    ).count()

    campaigns_sent = CampaignLog.objects.count()

    campaign_history_paginator = Paginator(CampaignLog.objects.all(), 10)
    campaign_history_page = campaign_history_paginator.get_page(
        request.GET.get("campaign_page")
    )

    newsletter_subscriber_paginator = Paginator(
        MarketingSubscriber.objects.all(),
        15,
    )
    newsletter_subscriber_page = newsletter_subscriber_paginator.get_page(
        request.GET.get("subscriber_page")
    )

    newsletter_subscriber_count = MarketingSubscriber.objects.count()

    active_newsletter_subscriber_count = (
        MarketingSubscriber.objects.filter(
            is_active=True,
            consent_given=True,
        ).count()
    )

    return render(
        request,
        "dashboard/marketing/campaign_center.html",
        {
            "vip_count": len(vip_customers),
            "inactive_count": len(inactive_customers),

            # Review campaign metrics
            "review_count": review_opportunities.count(),
            "review_completed_count": completed_bookings.count(),
            "review_already_requested": review_already_requested,
            "review_missing_email": review_missing_email,

            "campaigns_sent": campaigns_sent,
            "campaign_history": campaign_history_page.object_list,
            "campaign_history_page": campaign_history_page,
            "newsletter_subscribers": newsletter_subscriber_page.object_list,
            "newsletter_subscriber_page": newsletter_subscriber_page,
            "newsletter_subscriber_count": newsletter_subscriber_count,
            "active_newsletter_subscriber_count": active_newsletter_subscriber_count,
        },
    )


@require_POST
@admin_required
@permission_required(
    ("customers.view_customer", "dashboard.add_campaignlog", "dashboard.add_emaillog", "dashboard.add_activitylog"),
    raise_exception=True,
)
def send_vip_campaign(request):
    vip_customers = _customers_with_marketing_consent(
        Customer.objects.filter(total_revenue__gte=1000)
        .exclude(email="")
        .exclude(email__isnull=True)
        .order_by("-total_revenue")
    )

    sent_count = 0

    if request.method == "POST":
        for customer in vip_customers:
            subject = "Exclusive Offer from YD Commercial Cleaning Services"

            message = f"""
Dear {customer.full_name},

Thank you for being one of our valued VIP customers.

YD Commercial Cleaning Services appreciates your continued support.

We would like to offer you priority booking access and exclusive promotions.

Thank you,
YD Commercial Cleaning Services
"""

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [customer.email],
                fail_silently=False,
            )

            EmailLog.objects.create(
                sent_by=request.user,
                email_type="system",
                recipient_name=customer.full_name,
                recipient_email=customer.email,
                subject=subject,
                related_object="VIP Customer Campaign",
            )

            sent_count += 1

        CampaignLog.objects.create(
            sent_by=request.user,
            campaign_type="vip",
            title="VIP Customer Campaign",
            recipients_count=sent_count,
        )

        create_activity_log(
            request.user,
            "customer",
            "VIP Campaign Sent",
            f"VIP campaign sent to {sent_count} customers.",
        )

        messages.success(request, f"✅ VIP campaign sent to {sent_count} customers.")

    return redirect("campaign_center")


@require_POST
@admin_required
@permission_required(
    ("customers.view_customer", "dashboard.add_campaignlog", "dashboard.add_emaillog", "dashboard.add_activitylog"),
    raise_exception=True,
)
def send_inactive_campaign(request):
    inactive_customers = _customers_with_marketing_consent(
        Customer.objects.filter(jobs_completed__lte=1)
        .exclude(email="")
        .exclude(email__isnull=True)
        .order_by("full_name")
    )

    sent_count = 0

    if request.method == "POST":
        for customer in inactive_customers:
            subject = "We Miss You - YD Commercial Cleaning Services"

            message = f"""
Dear {customer.full_name},

We have not seen you for a while.

YD Commercial Cleaning Services would love to help with your next cleaning service.

Book again and enjoy a special returning customer offer.

Thank you,
YD Commercial Cleaning Services
"""

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [customer.email],
                fail_silently=False,
            )

            EmailLog.objects.create(
                sent_by=request.user,
                email_type="system",
                recipient_name=customer.full_name,
                recipient_email=customer.email,
                subject=subject,
                related_object="Inactive Customer Campaign",
            )

            sent_count += 1

        CampaignLog.objects.create(
            sent_by=request.user,
            campaign_type="inactive",
            title="Inactive Customer Campaign",
            recipients_count=sent_count,
        )

        create_activity_log(
            request.user,
            "customer",
            "Inactive Customer Campaign Sent",
            f"Inactive customer campaign sent to {sent_count} customers.",
        )

        messages.success(
            request, f"✅ Inactive campaign sent to {sent_count} customers."
        )

    return redirect("campaign_center")


@require_POST
@admin_required
@permission_required(
    (
        "bookings.view_booking",
        "dashboard.add_reviewrequestlog",
        "dashboard.add_emaillog",
        "dashboard.add_campaignlog",
        "dashboard.add_activitylog",
    ),
    raise_exception=True,
)
def send_review_campaign(request):
    completed_bookings = (
        Booking.objects
        .filter(status="completed")
        .select_related("customer")
        .prefetch_related("review_request_log")
        .order_by("-booking_date")
    )

    sent_count = 0
    skipped_count = 0

    review_link = "https://g.page/r/CXH9ygKf16Y4EBM/review"

    subject = "We'd Love Your Feedback — YD Commercial Cleaning Services"

    if request.method == "POST":

        for booking in completed_bookings:

            customer = booking.customer

            # Skip customers without an email address.
            if not customer.email:
                skipped_count += 1
                continue

            # Prevent duplicate review requests.
            if ReviewRequestLog.objects.filter(booking=booking).exists():
                skipped_count += 1
                continue

            email_context = {
                "customer": customer,
                "customer_name": customer.full_name,
                "booking": booking,
                "review_link": review_link,
            }

            html_message = render_to_string(
                "emails/reviews/review_request.html",
                email_context,
            )

            text_message = render_to_string(
                "emails/reviews/review_request.txt",
                email_context,
            )

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[customer.email],
            )

            email.attach_alternative(
                html_message,
                "text/html",
            )

            email.send(fail_silently=False)

            # Record email history.
            EmailLog.objects.create(
                sent_by=request.user,
                email_type="system",
                recipient_name=customer.full_name,
                recipient_email=customer.email,
                subject=subject,
                related_object=f"Review Campaign Booking #{booking.id}",
            )

            # Create review request tracking record.
            ReviewRequestLog.objects.create(
                booking=booking,
                sent_by=request.user,
                sent_count=1,
                last_sent_at=timezone.now(),
            )

            # Record dashboard activity.
            create_activity_log(
                request.user,
                "review",
                "Review Campaign Sent",
                f"Review request sent to {customer.full_name}",
            )

            sent_count += 1


        # Record campaign history only when at least one email was sent.
        if sent_count > 0:
            CampaignLog.objects.create(
                sent_by=request.user,
                campaign_type="review",
                title="Review Follow-up Campaign",
                recipients_count=sent_count,
            )

        # Record campaign activity.
        create_activity_log(
            request.user,
            "review",
            "Review Campaign Sent",
            f"Review campaign sent to {sent_count} customers.",
        )

        messages.success(
            request,
            f"✅ Review campaign completed. "
            f"{sent_count} request(s) sent"
            + (
                f", {skipped_count} skipped."
                if skipped_count
                else "."
            ),
        )

    return redirect("campaign_center")



@login_required
def campaign_preview(request, campaign_type):

    recipients = []
    title = ""
    recipient_count = 0

    if campaign_type == "vip":
        title = "VIP Campaign Recipients"

        recipients = _customers_with_marketing_consent(
            Customer.objects
            .filter(total_revenue__gte=1000)
            .exclude(email="")
            .exclude(email__isnull=True)
            .order_by("-total_revenue")
        )

        recipient_count = len(recipients)

    elif campaign_type == "inactive":
        title = "Inactive Campaign Recipients"

        recipients = _customers_with_marketing_consent(
            Customer.objects
            .filter(jobs_completed__lte=1)
            .exclude(email="")
            .exclude(email__isnull=True)
            .order_by("full_name")
        )

        recipient_count = len(recipients)

    elif campaign_type == "review":
        title = "Review Campaign Recipients"

        completed_bookings = (
            Booking.objects
            .filter(status="completed")
            .select_related("customer")
            .order_by("-booking_date")
        )

        # Only completed bookings that:
        # 1. Have a customer email address
        # 2. Have NOT already received a review request
        eligible_bookings = []

        for booking in completed_bookings:

            customer = booking.customer

            if not customer.email:
                continue

            if ReviewRequestLog.objects.filter(
                booking=booking
            ).exists():
                continue

            eligible_bookings.append(booking)

        recipients = eligible_bookings
        recipient_count = len(eligible_bookings)

    else:
        messages.error(request, "Invalid campaign type.")
        return redirect("campaign_center")

    paginator = Paginator(recipients, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "dashboard/marketing/campaign_preview.html",
        {
            "campaign_type": campaign_type,
            "title": title,
            "recipients": page_obj.object_list,
            "recipient_count": recipient_count,
            "page_obj": page_obj,
        },
    )


@login_required
def campaign_performance(request):

    campaigns = CampaignLog.objects.all()

    total_campaigns = campaigns.count()
    email_logs_related_to_campaigns = EmailLog.objects.filter(
        related_object__icontains="campaign"
    ).count()
    general_email_log_count = EmailLog.objects.exclude(
        related_object__icontains="campaign"
    ).count()
    standalone_review_requests = ReviewRequestLog.objects.aggregate(
        total=Sum("sent_count")
    )["total"] or 0

    total_emails_sent = campaigns.aggregate(total=Sum("recipients_count"))[
        "total"
    ] or 0

    vip_campaigns = campaigns.filter(campaign_type="vip").count()

    inactive_campaigns = campaigns.filter(campaign_type="inactive").count()

    review_campaigns = campaigns.filter(campaign_type="review").count()

    campaign_type_totals = {
        "VIP Campaign": vip_campaigns,
        "Inactive Campaign": inactive_campaigns,
        "Review Campaign": review_campaigns,
    }

    most_used_campaign_type  = (
        max(campaign_type_totals, key=campaign_type_totals.get)
        if total_campaigns
        else "N/A"
    )

    campaign_type_filter = request.GET.get("type", "").strip()
    if campaign_type_filter in {"vip", "inactive", "review"}:
        campaigns = campaigns.filter(campaign_type=campaign_type_filter)
    else:
        campaign_type_filter = ""
    paginator = Paginator(campaigns.select_related("sent_by"), 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "dashboard/marketing/campaign_performance.html",
        {
            "campaigns": page_obj.object_list,
            "page_obj": page_obj,
            "campaign_type_filter": campaign_type_filter,
            "total_campaigns": total_campaigns,
            "total_emails_sent": total_emails_sent,
            "vip_campaigns": vip_campaigns,
            "inactive_campaigns": inactive_campaigns,
            "review_campaigns": review_campaigns,
            "most_used_campaign_type": most_used_campaign_type,
            "email_logs_related_to_campaigns": email_logs_related_to_campaigns,
            "general_email_log_count": general_email_log_count,
            "standalone_review_requests": standalone_review_requests,
        },
    )


@login_required
def profit_loss_dashboard(request):
    current_year = timezone.localdate().year
    try:
        selected_year = int(request.GET.get("year", current_year))
    except (TypeError, ValueError):
        selected_year = current_year
    if selected_year < current_year - 10 or selected_year > current_year:
        selected_year = current_year
    period_start = date(selected_year, 1, 1)
    period_end = date(selected_year + 1, 1, 1)

    paid_revenue = (
        Invoice.objects.filter(
            status="paid",
            paid_at__date__gte=period_start,
            paid_at__date__lt=period_end,
        ).aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    payroll_cost = PayrollRecord.objects.filter(
        period_end__gte=period_start,
        period_end__lt=period_end,
    ).aggregate(total=Sum("gross_pay"))["total"] or 0

    completed_bookings = Booking.objects.filter(
        status="completed",
        assigned_employee__active=True,
    )
    completed_bookings = completed_bookings.filter(
        booking_date__gte=period_start,
        booking_date__lt=period_end,
    )
    bonus_basis = completed_bookings.aggregate(
        revenue=Sum("quoted_price"),
        jobs=Count("pk"),
    )
    bonus_cost = (
        (bonus_basis["revenue"] or Decimal("0.00")) * Decimal("0.05")
        + Decimal(bonus_basis["jobs"] or 0) * Decimal("10.00")
    )
    expense_cost = Expense.objects.filter(
        date__gte=period_start,
        date__lt=period_end,
    ).aggregate(total=Sum("amount"))["total"] or 0

    estimated_profit = paid_revenue - payroll_cost - bonus_cost - expense_cost
    profit_margin = (
        (estimated_profit / paid_revenue * Decimal("100")).quantize(
            Decimal("0.01")
        )
        if paid_revenue
        else Decimal("0.00")
    )

    return render(
        request,
        "dashboard/finance/profit_loss_dashboard.html",
        {
            "paid_revenue": paid_revenue,
            "payroll_cost": payroll_cost,
            "bonus_cost": bonus_cost,
            "expense_cost": expense_cost,
            "estimated_profit": estimated_profit,
            "profit_margin": profit_margin,
            "total_costs": payroll_cost + bonus_cost + expense_cost,
            "selected_year": selected_year,
            "years": range(current_year, current_year - 6, -1),
        },
    )


@login_required
def business_kpis(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)
    next_month_start = (
        month_start.replace(year=month_start.year + 1, month=1)
        if month_start.month == 12
        else month_start.replace(month=month_start.month + 1)
    )

    today_revenue = (
        Invoice.objects.filter(status="paid", paid_at__date=today).aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    month_revenue = Invoice.objects.filter(
        status="paid",
        paid_at__date__gte=month_start,
        paid_at__date__lt=next_month_start,
    ).aggregate(total=Sum("total_amount"))["total"] or 0

    outstanding_invoices = (
        Invoice.objects.exclude(status__in=["paid", "cancelled"]).aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    payroll_month = (
        PayrollRecord.objects.filter(
            period_start__lte=today,
            period_end__gte=month_start,
        ).aggregate(total=Sum("gross_pay"))["total"]
        or 0
    )
    expenses_month = Expense.objects.filter(
        date__gte=month_start,
        date__lt=next_month_start,
    ).aggregate(total=Sum("amount"))["total"] or 0

    completed_jobs_month = Booking.objects.filter(
        status="completed", booking_date__gte=month_start
    ).count()

    upcoming_jobs = (
        Booking.objects.filter(booking_date__gte=today)
        .exclude(status="cancelled")
        .count()
    )

    active_customers = Customer.objects.count()

    new_customers_month = Customer.objects.filter(
        created_at__date__gte=month_start
    ).count()

    total_employees = Employee.objects.filter(active=True).count()

    average_rating = Review.objects.aggregate(average=Avg("rating"))["average"] or 0

    average_rating = round(average_rating, 2)

    reviews_received = Review.objects.count()

    campaigns_sent = CampaignLog.objects.count()

    vip_customers = Customer.objects.filter(total_revenue__gte=1000).count()

    estimated_profit_month = (
        float(month_revenue) - float(payroll_month) - float(expenses_month)
    )

    profit_margin = 0

    if month_revenue:
        profit_margin = round((estimated_profit_month / float(month_revenue)) * 100, 2)

    health_score = 0

    if month_revenue > 0:
        health_score += 25

    if profit_margin > 20:
        health_score += 25
    elif profit_margin > 0:
        health_score += 15

    if average_rating >= 4.5:
        health_score += 20
    elif average_rating >= 4:
        health_score += 15

    if new_customers_month > 0:
        health_score += 15

    if outstanding_invoices == 0:
        health_score += 15
    else:
        health_score += 5

    if health_score >= 85:
        health_status = "Excellent"
    elif health_score >= 65:
        health_status = "Good"
    elif health_score >= 40:
        health_status = "Needs Attention"
    else:
        health_status = "Critical"

    return render(
        request,
        "dashboard/finance/business_kpis.html",
        {
            "today_revenue": today_revenue,
            "month_revenue": month_revenue,
            "outstanding_invoices": outstanding_invoices,
            "payroll_month": payroll_month,
            "expenses_month": expenses_month,
            "completed_jobs_month": completed_jobs_month,
            "upcoming_jobs": upcoming_jobs,
            "active_customers": active_customers,
            "new_customers_month": new_customers_month,
            "total_employees": total_employees,
            "average_rating": average_rating,
            "reviews_received": reviews_received,
            "campaigns_sent": campaigns_sent,
            "vip_customers": vip_customers,
            "estimated_profit_month": round(estimated_profit_month, 2),
            "profit_margin": profit_margin,
            "health_score": health_score,
            "health_status": health_status,
        },
    )


# leave_management.LeaveRequest already imported near the top of this module
# (duplicate import removed to avoid redefinition warnings)


@login_required
def employee_schedule(request):
    today = timezone.now().date()

    start_date = request.GET.get("start")

    if start_date:
        try:
            week_start = timezone.datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            week_start = today - timedelta(days=today.weekday())
    else:
        week_start = today - timedelta(days=today.weekday())

    week_end = week_start + timedelta(days=6)

    previous_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)

    employees = Employee.objects.filter(active=True).order_by("full_name")

    week_days = []

    for i in range(7):
        week_days.append(week_start + timedelta(days=i))

    schedule_rows = []

    for employee in employees:
        employee_days = []

        total_jobs = 0

        for day in week_days:
            jobs = list(
                Booking.objects.filter(assigned_employee=employee, booking_date=day)
                .exclude(status="cancelled")
                .select_related("customer")
                .order_by("booking_time")
            )
            total_jobs += len(jobs)
            approved_leave = LeaveRequest.objects.filter(
                employee=employee,
                status="approved",
                start_date__lte=day,
                end_date__gte=day,
            ).first()
            employee_days.append(
                {
                    "date": day,
                    "jobs": jobs,
                    "approved_leave": approved_leave,
                }
            )

        schedule_rows.append(
          
           {
                "employee": employee,
                "days": employee_days,
                "total_jobs": total_jobs,
            }
        )

    return render(
        request,
        "employees/employee_schedule.html",
        {
            "week_start": week_start,
            "week_end": week_end,
            "previous_week": previous_week,
            "next_week": next_week,
            "week_days": week_days,
            "schedule_rows": schedule_rows,
        },
    )


@login_required
def gst_report(request):
    current_year = timezone.localdate().year
    try:
        selected_year = int(request.GET.get("year", current_year))
    except (TypeError, ValueError):
        selected_year = current_year
    if selected_year < current_year - 10 or selected_year > current_year:
        selected_year = current_year
    period_start = date(selected_year, 1, 1)
    period_end = date(selected_year + 1, 1, 1)
    company_gst_rate = 10

    paid_revenue = (
        Invoice.objects.filter(
            status="paid",
            paid_at__date__gte=period_start,
            paid_at__date__lt=period_end,
        ).aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    gst_collected = (
        Invoice.objects.filter(
            status="paid",
            paid_at__date__gte=period_start,
            paid_at__date__lt=period_end,
        ).aggregate(total=Sum("gst_amount"))["total"]
        or Decimal("0.00")
    )
    total_expenses = Expense.objects.filter(
        date__gte=period_start,
        date__lt=period_end,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    gst_paid = (total_expenses / Decimal("11")).quantize(Decimal("0.01"))
    net_gst_payable = gst_collected - gst_paid

    return render(
        request,
        "dashboard/finance/gst_report.html",
        {
            "paid_revenue": paid_revenue,
            "total_expenses": total_expenses,
            "gst_collected": gst_collected,
            "gst_paid": gst_paid,
            "net_gst_payable": net_gst_payable,
            "company_gst_rate": company_gst_rate,
            "selected_year": selected_year,
            "years": range(current_year, current_year - 6, -1),
        },
    )


@login_required
def finance_trends(request):
    from django.db.models.functions import TruncMonth

    today = timezone.localdate()
    month_starts = []
    year, month = today.year, today.month
    for _ in range(12):
        month_starts.append(date(year, month, 1))
        month -= 1
        if month == 0:
            year -= 1
            month = 12
    month_starts.reverse()
    range_start = month_starts[0]
    range_end = (
        date(today.year + 1, 1, 1)
        if today.month == 12
        else date(today.year, today.month + 1, 1)
    )
    revenue_data = (
        Invoice.objects.filter(
            status="paid",
            paid_at__date__gte=range_start,
            paid_at__date__lt=range_end,
        )
        .annotate(month=TruncMonth("paid_at"))
        .values("month")
        .annotate(total=Sum("total_amount"))
        .order_by("month")
    )

    expense_data = (
        Expense.objects.filter(
            date__gte=range_start,
            date__lt=range_end,
        ).annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )

    payroll_data = (
        PayrollRecord.objects.filter(
            period_end__gte=range_start,
            period_end__lt=range_end,
        ).annotate(month=TruncMonth("period_end"))
        .values("month")
        .annotate(total=Sum("gross_pay"))
        .order_by("month")
    )

    revenue_map = {}
    expense_map = {}
    payroll_map = {}

    for item in revenue_data:
        if item["month"]:
            revenue_map[(item["month"].year, item["month"].month)] = float(item["total"] or 0)

    for item in expense_data:
        if item["month"]:
            expense_map[(item["month"].year, item["month"].month)] = float(item["total"] or 0)

    for item in payroll_data:
        if item["month"]:
            payroll_map[(item["month"].year, item["month"].month)] = float(item["total"] or 0)

    months = [month_start.strftime("%b %Y") for month_start in month_starts]
    revenue_values = []
    expense_values = []
    payroll_values = []
    profit_values = []

    for month_start in month_starts:
        key = (month_start.year, month_start.month)
        revenue = revenue_map.get(key, 0)
        expenses = expense_map.get(key, 0)
        payroll = payroll_map.get(key, 0)
        profit = revenue - expenses - payroll

        revenue_values.append(revenue)
        expense_values.append(expenses)
        payroll_values.append(payroll)
        profit_values.append(round(profit, 2))

    return render(
        request,
        "dashboard/finance/finance_trends.html",
        {
            "months": months,
            "revenue_values": revenue_values,
            "expense_values": expense_values,
            "payroll_values": payroll_values,
            "profit_values": profit_values,
            "period_label": f"{month_starts[0].strftime('%b %Y')} – {today.strftime('%b %Y')}",
            "revenue_total": sum(revenue_values),
            "expense_total": sum(expense_values),
            "payroll_total": sum(payroll_values),
            "profit_total": sum(profit_values),
        },
    )


def _save_quick_status_and_sync(request, booking_id, new_status):
    from notifications.utils import temporary_instance_flags
    from rosters.services import (
        RosterSyncNotConfigured,
        RosterSyncPending,
        booking_roster_sync_lock,
        sync_booking_roster,
    )

    with booking_roster_sync_lock(booking_id):
        booking = get_object_or_404(
            Booking.objects.select_for_update(),
            pk=booking_id,
        )
        old_status = booking.status
        booking.status = new_status
        with temporary_instance_flags(
            booking,
            _suppress_customer_status_notification=True,
        ):
            booking.save()

        roster_sync_succeeded = True
        try:
            roster_sync = sync_booking_roster(booking)
            if isinstance(roster_sync, RosterSyncPending):
                raise roster_sync.error
            if isinstance(roster_sync, RosterSyncNotConfigured):
                messages.info(
                    request,
                    "Employee Calendar sync is not configured; booking status was saved.",
                )
        except Exception:
            roster_sync_succeeded = False
            logger.exception("Roster sync failed for booking %s.", booking.pk)
            messages.warning(
                request,
                "Booking status was saved, but the employee schedule could not be synced automatically.",
            )

        if (
            roster_sync_succeeded
            and old_status != new_status
            and booking.customer
            and booking.customer.user
        ):
            Notification.objects.create(
                user=booking.customer.user,
                title="Booking Updated",
                message=(
                    f"Your booking for {booking.service_type} is now "
                    f"{booking.get_status_display()}."
                ),
                notification_type="booking",
                link=f"/portal/bookings/{booking.pk}/",
            )

        if roster_sync_succeeded:
            try:
                if new_status == "cancelled":
                    delete_booking_event(booking)
                else:
                    create_or_update_booking_event(booking)
            except Exception:
                logger.exception(
                    "Google Calendar sync failed for booking %s.",
                    booking.pk,
                )
                messages.warning(
                    request,
                    "Booking updated, but Google Calendar could not be synced automatically.",
                )

    return booking, old_status, roster_sync_succeeded


@require_POST
@admin_required
def update_booking_quick_status(request, booking_id, new_status):
    allowed_statuses = {
        "pending",
        "confirmed",
        "assigned",
        "in_progress",
        "completed",
        "cancelled",
    }

    if new_status not in allowed_statuses:
        messages.error(request, "❌ Invalid booking status.")
        return redirect("booking_calendar")

    from rosters.services import RosterSyncLockError

    try:
        booking, old_status, roster_sync_succeeded = (
            _save_quick_status_and_sync(request, booking_id, new_status)
        )
    except (DatabaseError, RosterSyncLockError):
        logger.exception(
            "Could not safely serialize quick status update for booking %s.",
            booking_id,
        )
        messages.error(
            request,
            "The booking could not be safely updated right now. Please retry.",
        )
        return redirect("booking_calendar")

    if roster_sync_succeeded and old_status != new_status:
        logger.info(
            "Booking status transition detected: booking=%s old=%s new=%s",
            booking.id,
            old_status,
            new_status,
        )

        if send_booking_confirmation_email(request, booking, old_status):
            messages.success(
                request,
                f"✅ Customer notified by email: booking status is now {booking.get_status_display()}.",
            )
        else:
            messages.warning(
                request,
                "⚠️ Booking updated, but the customer status email could not be sent.",
            )

    if roster_sync_succeeded and new_status == "completed":
        invoice, invoice_created = get_or_create_invoice_for_booking(booking)
        if not invoice_created:
            messages.info(
                request,
                f"Invoice already exists: {invoice.invoice_number}",
            )
        elif send_invoice_email(request, invoice):
            messages.success(
                request,
                f"Invoice {invoice.invoice_number} created and emailed "
                f"to {invoice.booking.customer.email}.",
            )
        else:
            messages.warning(
                request,
                f"Invoice {invoice.invoice_number} was created, "
                "but the customer invoice email could not be sent.",
            )

    create_activity_log(
        request.user,
        "booking",
        "Booking Status Updated",
        (
            f"{booking.customer.full_name if booking.customer else 'No customer'} booking "
            f"changed from {old_status} to {new_status}."
        ),
    )

    if roster_sync_succeeded:
        messages.success(
            request,
            "✅ Booking status updated successfully.",
        )

    return redirect("booking_calendar")


# ==========================================================
# Equipment Inventory
# ==========================================================


@login_required
def equipment_list(request):
    from datetime import timedelta

    from django.utils import timezone

    from .models import Equipment

    today = timezone.localdate()
    due_limit = today + timedelta(days=30)

    equipment = Equipment.objects.select_related("assigned_employee").all()
    query = request.GET.get("q", "").strip()
    condition = request.GET.get("condition", "").strip()
    service_filter = request.GET.get("service", "").strip()
    if query:
        equipment = equipment.filter(
            Q(name__icontains=query)
            | Q(serial_number__icontains=query)
            | Q(assigned_employee__full_name__icontains=query)
        )
    if condition in {value for value, _ in Equipment.CONDITION_CHOICES}:
        equipment = equipment.filter(condition=condition)
    else:
        condition = ""
    if service_filter == "overdue":
        equipment = equipment.filter(next_service_date__lt=today)
    elif service_filter == "due_soon":
        equipment = equipment.filter(
            next_service_date__gte=today,
            next_service_date__lte=due_limit,
        )
    elif service_filter == "not_scheduled":
        equipment = equipment.filter(next_service_date__isnull=True)
    else:
        service_filter = ""

    page_obj = Paginator(equipment.order_by("name", "pk"), 25).get_page(
        request.GET.get("page")
    )
    for item in page_obj.object_list:
        if not item.next_service_date:
            item.service_status = "not_scheduled"
        elif item.next_service_date < today:
            item.service_status = "overdue"
        elif item.next_service_date == today:
            item.service_status = "today"
        elif item.next_service_date <= due_limit:
            item.service_status = "upcoming"
        else:
            item.service_status = "ok"
    all_equipment = Equipment.objects.all()

    return render(
        request,
        "dashboard/inventory/equipment_list.html",
        {
            "equipment_items": page_obj.object_list,
            "page_obj": page_obj,
            "query": query,
            "condition": condition,
            "service_filter": service_filter,
            "condition_choices": Equipment.CONDITION_CHOICES,
            "total_equipment": all_equipment.count(),
            "overdue_equipment": all_equipment.filter(
                next_service_date__lt=today
            ).count(),
            "due_soon_equipment": all_equipment.filter(
                next_service_date__gte=today,
                next_service_date__lte=due_limit,
            ).count(),
            "equipment_needing_repair": all_equipment.filter(
                condition="repair"
            ).count(),
            "today": today,
        },
    )


@login_required
def add_equipment(request):
    from .forms import EquipmentForm

    if request.method == "POST":
        form = EquipmentForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "✅ Equipment added successfully.")
            return redirect("equipment_list")

        messages.error(request, "❌ Please check the equipment form.")
    else:
        form = EquipmentForm()

    return render(
        request,
        "dashboard/inventory/equipment_form.html",
        {
            "form": form,
            "page_title": "Add Equipment",
            "button_text": "Save Equipment",
        },
    )


@login_required
def edit_equipment(request, equipment_id):
    from .forms import EquipmentForm
    from .models import Equipment

    equipment = get_object_or_404(Equipment, id=equipment_id)

    if request.method == "POST":
        form = EquipmentForm(request.POST, instance=equipment)

        if form.is_valid():
            form.save()
            messages.success(request, "✅ Equipment updated successfully.")
            return redirect("equipment_list")

        messages.error(request, "❌ Please check the equipment form.")
    else:
        form = EquipmentForm(instance=equipment)

    return render(
        request,
        "dashboard/inventory/equipment_form.html",
        {
            "form": form,
            "page_title": "Edit Equipment",
            "button_text": "Update Equipment",
        },
    )


@admin_required
@require_http_methods(["GET", "POST"])
def delete_equipment(request, equipment_id):
    from .models import Equipment

    equipment = get_object_or_404(Equipment, id=equipment_id)

    if request.method == "POST":
        equipment.delete()
        messages.success(request, "✅ Equipment deleted successfully.")
        return redirect("equipment_list")

    return render(
        request,
        "dashboard/inventory/equipment_confirm_delete.html",
        {
            "equipment": equipment,
        },
    )


@login_required
def supplies_list(request):

    from .models import CleaningSupply

    supplies = CleaningSupply.objects.all()
    query = request.GET.get("q", "").strip()
    stock_filter = request.GET.get("stock", "").strip()
    category = request.GET.get("category", "").strip()
    if query:
        supplies = supplies.filter(
            Q(name__icontains=query)
            | Q(category__icontains=query)
            | Q(supplier_name__icontains=query)
        )
    if stock_filter == "low":
        supplies = supplies.filter(current_stock__lte=F("minimum_stock"))
    elif stock_filter == "healthy":
        supplies = supplies.filter(current_stock__gt=F("minimum_stock"))
    else:
        stock_filter = ""
    if category:
        supplies = supplies.filter(category=category)
    page_obj = Paginator(supplies.order_by("name", "pk"), 25).get_page(
        request.GET.get("page")
    )
    all_supplies = CleaningSupply.objects.all()
    stock_value = all_supplies.aggregate(
        total=Sum(
            ExpressionWrapper(
                F("current_stock") * F("unit_cost"),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
    )["total"] or 0

    return render(
        request,
        "dashboard/inventory/supplies_list.html",
        {
            "supplies": page_obj.object_list,
            "page_obj": page_obj,
            "query": query,
            "stock_filter": stock_filter,
            "category": category,
            "categories": CleaningSupply.objects.exclude(
                category=""
            ).order_by("category").values_list("category", flat=True).distinct(),
            "total_supplies": all_supplies.count(),
            "low_stock_count": all_supplies.filter(
                current_stock__lte=F("minimum_stock")
            ).count(),
            "total_stock_units": all_supplies.aggregate(
                total=Sum("current_stock")
            )["total"] or 0,
            "stock_value": stock_value,
        },
    )


@login_required
def add_supply(request):

    from .forms import CleaningSupplyForm

    if request.method == "POST":

        form = CleaningSupplyForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(request, "Supply added successfully.")

            return redirect("supplies_list")

    else:
        form = CleaningSupplyForm()

    return render(
        request,
        "dashboard/inventory/supply_form.html",
        {
            "form": form,
            "title": "Add Supply",
        },
    )


@login_required
def edit_supply(request, supply_id):

    from .forms import CleaningSupplyForm
    from .models import CleaningSupply

    supply = get_object_or_404(CleaningSupply, id=supply_id)

    if request.method == "POST":

        form = CleaningSupplyForm(request.POST, instance=supply)

        if form.is_valid():
            form.save()

            messages.success(request, "Supply updated successfully.")

            return redirect("supplies_list")

    else:

        form = CleaningSupplyForm(instance=supply)

    return render(
        request,
        "dashboard/inventory/supply_form.html",
        {
            "form": form,
            "title": "Edit Supply",
        },
    )


@login_required
def purchase_orders(request):

    from .models import PurchaseOrder

    orders = PurchaseOrder.objects.select_related("supply").all()
    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    if query:
        orders = orders.filter(
            Q(supply__name__icontains=query)
            | Q(supplier_name__icontains=query)
            | Q(notes__icontains=query)
        )
    if status_filter in {value for value, _ in PurchaseOrder.STATUS_CHOICES}:
        orders = orders.filter(status=status_filter)
    else:
        status_filter = ""
    page_obj = Paginator(orders.order_by("-order_date", "-pk"), 25).get_page(
        request.GET.get("page")
    )
    all_orders = PurchaseOrder.objects.all()
    order_value = all_orders.aggregate(
        total=Sum(
            ExpressionWrapper(
                F("quantity") * F("unit_cost"),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
    )["total"] or 0

    return render(
        request,
        "dashboard/inventory/purchase_orders.html",
        {
            "orders": page_obj.object_list,
            "page_obj": page_obj,
            "query": query,
            "status_filter": status_filter,
            "status_choices": PurchaseOrder.STATUS_CHOICES,
            "total_orders": all_orders.count(),
            "open_orders": all_orders.filter(
                status__in=("draft", "ordered")
            ).count(),
            "received_orders": all_orders.filter(status="received").count(),
            "order_value": order_value,
        },
    )


@login_required
def add_purchase_order(request):

    from .forms import PurchaseOrderForm
    from .models import Supplier

    if request.method == "POST":

        form = PurchaseOrderForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(request, "Purchase Order Created.")

            return redirect("purchase_orders")

    else:

        form = PurchaseOrderForm()

    return render(
        request,
        "dashboard/inventory/purchase_order_form.html",
        {
            "form": form,
            "active_suppliers": Supplier.objects.filter(active=True).order_by("name"),
        },
    )


@login_required
@require_POST
@permission_required(
    ("dashboard.change_purchaseorder", "dashboard.change_cleaningsupply"),
    raise_exception=True,
)
def receive_purchase_order(request, order_id):

    from .models import PurchaseOrder

    with transaction.atomic():
        order = get_object_or_404(
            PurchaseOrder.objects.select_for_update(),
            id=order_id,
        )
        if order.status in {"draft", "ordered"}:
            supply = get_object_or_404(
                CleaningSupply.objects.select_for_update(),
                id=order.supply_id,
            )
            supply.current_stock += order.quantity
            supply.save(update_fields=["current_stock"])

            order.status = "received"
            order.save(update_fields=["status"])
            received_quantity = order.quantity
        else:
            received_quantity = 0

    if received_quantity:
        messages.success(
            request,
            f"{received_quantity} units added to stock.",
        )
    elif order.status == "cancelled":
        messages.warning(
            request,
            "Cancelled purchase orders cannot be received.",
        )

    return redirect("purchase_orders")


@login_required
def supplier_list(request):
    from .models import Supplier

    suppliers = Supplier.objects.all()
    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    if query:
        suppliers = suppliers.filter(
            Q(name__icontains=query)
            | Q(contact_person__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
        )
    if status_filter == "active":
        suppliers = suppliers.filter(active=True)
    elif status_filter == "inactive":
        suppliers = suppliers.filter(active=False)
    else:
        status_filter = ""
    page_obj = Paginator(suppliers.order_by("name", "pk"), 25).get_page(
        request.GET.get("page")
    )
    all_suppliers = Supplier.objects.all()

    return render(
        request,
        "dashboard/inventory/supplier_list.html",
        {
            "suppliers": page_obj.object_list,
            "page_obj": page_obj,
            "query": query,
            "status_filter": status_filter,
            "total_suppliers": all_suppliers.count(),
            "active_suppliers": all_suppliers.filter(active=True).count(),
            "inactive_suppliers": all_suppliers.filter(active=False).count(),
            "contactable_suppliers": all_suppliers.exclude(email="")
            .exclude(phone="")
            .count(),
        },
    )


@login_required
def add_supplier(request):
    from .forms import SupplierForm

    if request.method == "POST":
        form = SupplierForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "✅ Supplier added successfully.")
            return redirect("supplier_list")
    else:
        form = SupplierForm()

    return render(
        request,
        "dashboard/inventory/supplier_form.html",
        {
            "form": form,
            "title": "Add Supplier",
        },
    )


@login_required
def edit_supplier(request, supplier_id):
    from .forms import SupplierForm
    from .models import Supplier

    supplier = get_object_or_404(Supplier, id=supplier_id)

    if request.method == "POST":
        form = SupplierForm(request.POST, instance=supplier)

        if form.is_valid():
            form.save()
            messages.success(request, "✅ Supplier updated successfully.")
            return redirect("supplier_list")
    else:
        form = SupplierForm(instance=supplier)

    return render(
        request,
        "dashboard/inventory/supplier_form.html",
        {
            "form": form,
            "title": "Edit Supplier",
        },
    )


@login_required
def vehicle_list(request):
    from .models import Vehicle

    today = timezone.localdate()
    vehicles = Vehicle.objects.select_related("assigned_employee").all()
    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    alert_filter = request.GET.get("alert", "").strip()
    if query:
        vehicles = vehicles.filter(
            Q(vehicle_name__icontains=query)
            | Q(registration_number__icontains=query)
            | Q(make__icontains=query)
            | Q(model__icontains=query)
            | Q(assigned_employee__full_name__icontains=query)
        )
    if status_filter in {value for value, _ in Vehicle.STATUS_CHOICES}:
        vehicles = vehicles.filter(status=status_filter)
    else:
        status_filter = ""
    if alert_filter == "overdue":
        vehicles = vehicles.filter(
            Q(service_due_date__lt=today)
            | Q(insurance_expiry__lt=today)
            | Q(registration_expiry__lt=today)
        )
    elif alert_filter == "due_soon":
        due_limit = today + timedelta(days=30)
        vehicles = vehicles.filter(
            Q(
                service_due_date__gte=today,
                service_due_date__lte=due_limit,
            )
            | Q(
                insurance_expiry__gte=today,
                insurance_expiry__lte=due_limit,
            )
            | Q(
                registration_expiry__gte=today,
                registration_expiry__lte=due_limit,
            )
        )
    else:
        alert_filter = ""
    page_obj = Paginator(vehicles.order_by("vehicle_name", "pk"), 25).get_page(
        request.GET.get("page")
    )
    all_vehicles = Vehicle.objects.all()
    due_limit = today + timedelta(days=30)
    for vehicle in page_obj.object_list:
        vehicle.date_alerts = []
        for label, due_date in (
            ("Insurance", vehicle.insurance_expiry),
            ("Registration", vehicle.registration_expiry),
            ("Service", vehicle.service_due_date),
        ):
            if due_date and due_date < today:
                vehicle.date_alerts.append((label, due_date, "overdue"))
            elif due_date and due_date <= due_limit:
                vehicle.date_alerts.append((label, due_date, "due_soon"))

    return render(
        request,
        "dashboard/inventory/vehicle_list.html",
        {
            "vehicles": page_obj.object_list,
            "page_obj": page_obj,
            "query": query,
            "status_filter": status_filter,
            "alert_filter": alert_filter,
            "status_choices": Vehicle.STATUS_CHOICES,
            "today": today,
            "total_vehicles": all_vehicles.count(),
            "active_vehicles": all_vehicles.filter(status="active").count(),
            "vehicles_in_maintenance": all_vehicles.filter(
                status="maintenance"
            ).count(),
            "vehicle_alerts": all_vehicles.filter(
                Q(service_due_date__lte=due_limit)
                | Q(insurance_expiry__lte=due_limit)
                | Q(registration_expiry__lte=due_limit)
            ).count(),
        },
    )


@login_required
def add_vehicle(request):
    from .forms import VehicleForm

    if request.method == "POST":
        form = VehicleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Vehicle added successfully.")
            return redirect("vehicle_list")
    else:
        form = VehicleForm()

    return render(
        request,
        "dashboard/inventory/vehicle_form.html",
        {
            "form": form,
            "title": "Add Vehicle",
        },
    )


@login_required
def edit_vehicle(request, vehicle_id):
    from .forms import VehicleForm
    from .models import Vehicle

    vehicle = get_object_or_404(Vehicle, id=vehicle_id)

    if request.method == "POST":
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Vehicle updated successfully.")
            return redirect("vehicle_list")
    else:
        form = VehicleForm(instance=vehicle)

    return render(
        request,
        "dashboard/inventory/vehicle_form.html",
        {
            "form": form,
            "title": "Edit Vehicle",
        },
    )


@login_required
def maintenance_list(request):

    from .models import MaintenanceHistory

    today = timezone.localdate()
    records = MaintenanceHistory.objects.all()
    query = request.GET.get("q", "").strip()
    asset_type = request.GET.get("type", "").strip()
    if query:
        records = records.filter(
            Q(asset_name__icontains=query)
            | Q(description__icontains=query)
            | Q(performed_by__icontains=query)
        )
    if asset_type in {value for value, _ in MaintenanceHistory.ASSET_TYPE_CHOICES}:
        records = records.filter(asset_type=asset_type)
    else:
        asset_type = ""
    page_obj = Paginator(records.order_by("-maintenance_date", "-pk"), 25).get_page(
        request.GET.get("page")
    )
    all_records = MaintenanceHistory.objects.all()

    return render(
        request,
        "dashboard/inventory/maintenance_list.html",
        {
            "records": page_obj.object_list,
            "page_obj": page_obj,
            "today": today,
            "query": query,
            "asset_type": asset_type,
            "asset_type_choices": MaintenanceHistory.ASSET_TYPE_CHOICES,
            "total_records": all_records.count(),
            "vehicle_records": all_records.filter(asset_type="vehicle").count(),
            "equipment_records": all_records.filter(asset_type="equipment").count(),
            "overdue_services": all_records.filter(
                next_service_date__lt=today
            ).count(),
            "maintenance_cost": all_records.aggregate(total=Sum("cost"))[
                "total"
            ] or 0,
        },
    )


@login_required
def add_maintenance(request):

    from .forms import MaintenanceHistoryForm

    if request.method == "POST":

        form = MaintenanceHistoryForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(request, "Maintenance record added.")

            return redirect("maintenance_list")

    else:

        form = MaintenanceHistoryForm()

    return render(request, "dashboard/inventory/maintenance_form.html", {"form": form})


@login_required
def reminder_centre(request):
    today = timezone.localdate()
    from dashboard.reminders import get_reminder_center_items, get_reminder_keys
    from notifications.models import ReminderCenterReadState

    context = get_reminder_center_items(today)
    read_state, _ = ReminderCenterReadState.objects.get_or_create(user=request.user)
    read_state.seen_reminder_keys = get_reminder_keys(context)
    read_state.save(update_fields=["seen_reminder_keys", "updated_at"])

    return render(request, "dashboard/communications/reminder_centre.html", context)


@login_required
def business_intelligence(request):

    today = timezone.localdate()
    current_month = today.month
    current_year = today.year

    if current_month == 1:

        previous_month = 12
        previous_year = current_year - 1

    else:

        previous_month = current_month - 1
        previous_year = current_year
    month_start = today.replace(day=1)
    next_month_start = (
        month_start.replace(year=month_start.year + 1, month=1)
        if month_start.month == 12
        else month_start.replace(month=month_start.month + 1)
    )

    monthly_expenses = (
        Expense.objects.filter(
            date__gte=month_start,
            date__lt=next_month_start,
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    monthly_revenue = (
        Invoice.objects.filter(
            status="paid",
            paid_at__date__gte=month_start,
            paid_at__date__lt=next_month_start,
        ).aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    this_month_revenue = (
        Invoice.objects.filter(
            status="paid", paid_at__month=current_month, paid_at__year=current_year
        ).aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    last_month_revenue = (
        Invoice.objects.filter(
            status="paid", paid_at__month=previous_month, paid_at__year=previous_year
        ).aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    monthly_growth = 0

    if last_month_revenue > 0:

        monthly_growth = round(
            ((this_month_revenue - last_month_revenue) / last_month_revenue) * 100, 2
        )

    estimated_profit = float(monthly_revenue) - float(monthly_expenses)

    expense_categories = (
        Expense.objects.values("category")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    revenue_trend = (
        Invoice.objects.filter(status="paid")
        .annotate(month=TruncMonth("paid_at"))
        .values("month")
        .annotate(total=Sum("total_amount"))
        .order_by("month")
    )

    expense_trend = (
        Expense.objects.annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )

    revenue_labels = [
        item["month"].strftime("%b %Y") for item in revenue_trend if item["month"]
    ]

    revenue_values = [float(item["total"] or 0) for item in revenue_trend]

    expense_map = {}

    for item in expense_trend:

        if item["month"]:

            expense_map[item["month"].strftime("%b %Y")] = float(item["total"] or 0)

    profit_values = []

    for i, month in enumerate(revenue_labels):

        revenue = revenue_values[i]

        expenses = expense_map.get(month, 0)

        profit_values.append(round(revenue - expenses, 2))

    category_labels = [item["category"] for item in expense_categories]

    category_values = [float(item["total"] or 0) for item in expense_categories]

    top_customers = Customer.objects.annotate(
        total_bookings=Count("bookings")
    ).order_by("-total_bookings")[:5]

    top_employees = (
        Employee.objects.filter(active=True)
        .annotate(
            completed_jobs=Count(
                "assigned_bookings", filter=Q(assigned_bookings__status="completed")
            )
        )
        .order_by("-completed_jobs")[:5]
    )

    employee_revenue = (
        Employee.objects.filter(active=True)
        .annotate(
            completed_jobs=Count(
                "assigned_bookings", filter=Q(assigned_bookings__status="completed")
            ),
            revenue_generated=Sum(
                "assigned_bookings__quoted_price",
                filter=Q(assigned_bookings__status="completed"),
            ),
        )
        .order_by("-revenue_generated")[:10]
    )

    total_quotes = QuoteRequest.objects.count()

    accepted_quotes = QuoteRequest.objects.filter(
        status__in=["booked", "completed"]
    ).count()

    quote_conversion_rate = 0

    if total_quotes > 0:

        quote_conversion_rate = round((accepted_quotes / total_quotes) * 100, 2)

    new_customers_this_month = Customer.objects.filter(
        created_at__month=current_month, created_at__year=current_year
    ).count()

    completed_jobs = Booking.objects.filter(
        status="completed",
        booking_date__gte=month_start,
        booking_date__lt=next_month_start,
    )
    completed_jobs_count = completed_jobs.count()
    completed_job_value = completed_jobs.aggregate(
        total=Sum("quoted_price")
    )["total"] or 0

    average_job_value = 0

    if completed_jobs_count > 0:
        average_job_value = round(
            float(completed_job_value) / completed_jobs_count,
            2,
        )

    revenue_by_service = (
        Booking.objects.filter(status="completed")
        .values("service_type")
        .annotate(total_revenue=Sum("quoted_price"), total_jobs=Count("id"))
        .order_by("-total_revenue")[:10]
    )

    revenue_by_suburb = (
        Booking.objects.filter(status="completed")
        .values("suburb_postcode")
        .annotate(total_revenue=Sum("quoted_price"), total_jobs=Count("id"))
        .order_by("-total_revenue")[:10]
    )

    top_10_customers = Customer.objects.annotate(total_jobs=Count("bookings")).order_by(
        "-total_revenue"
    )[:10]

    top_services = (
        Booking.objects.values("service_type")
        .annotate(total_jobs=Count("id"))
        .order_by("-total_jobs")[:5]
    )

    top_revenue_customers = Customer.objects.order_by("-total_revenue")[:5]

    customer_lifetime_value = Customer.objects.annotate(
        booking_count=Count("bookings")
    ).order_by("-total_revenue")[:10]

    top_suburbs = (
        Booking.objects.values("suburb_postcode")
        .annotate(total_jobs=Count("id"))
        .order_by("-total_jobs")[:10]
    )

    repeat_customers = Customer.objects.annotate(
        booking_count=Count("bookings")
    ).filter(booking_count__gt=1)

    repeat_customer_count = repeat_customers.count()

    total_customer_count = Customer.objects.count()

    repeat_customer_rate = 0

    if total_customer_count > 0:
        repeat_customer_rate = round(
            (repeat_customer_count / total_customer_count) * 100, 2
        )

    health_score = 0

    # Revenue Growth

    if monthly_growth >= 20:
        health_score += 25
    elif monthly_growth >= 10:
        health_score += 20
    elif monthly_growth > 0:
        health_score += 15

    # Repeat Customer Rate

    if repeat_customer_rate >= 50:
        health_score += 25
    elif repeat_customer_rate >= 30:
        health_score += 20
    elif repeat_customer_rate >= 15:
        health_score += 10

    # Quote Conversion

    if quote_conversion_rate >= 50:
        health_score += 25
    elif quote_conversion_rate >= 30:
        health_score += 20
    elif quote_conversion_rate >= 15:
        health_score += 10

    # Average Job Value

    if average_job_value >= 1000:
        health_score += 25
    elif average_job_value >= 500:
        health_score += 20
    elif average_job_value >= 250:
        health_score += 10

    if health_score >= 80:

        health_status = "Excellent"

    elif health_score >= 60:

        health_status = "Good"

    elif health_score >= 40:

        health_status = "Average"

    else:

        health_status = "Needs Attention"

    today_jobs = Booking.objects.filter(booking_date=today).count()

    outstanding_invoices = Invoice.objects.exclude(
        status__in=["paid", "cancelled"]
    ).count()

    low_stock_items = CleaningSupply.objects.filter(
        current_stock__lte=F("minimum_stock")
    ).count()

    overdue_equipment = Equipment.objects.filter(next_service_date__lt=today).count()

    vehicles_due_service = Vehicle.objects.filter(service_due_date__lt=today).count()

    executive_alerts = (
        outstanding_invoices
        + low_stock_items
        + overdue_equipment
        + vehicles_due_service
    )

    context = {
        "monthly_revenue": monthly_revenue,
        "monthly_expenses": monthly_expenses,
        "estimated_profit": round(estimated_profit, 2),
        "category_labels": category_labels,
        "category_values": category_values,
        "revenue_labels": revenue_labels,
        "revenue_values": revenue_values,
        "profit_values": profit_values,
        "top_customers": top_customers,
        "top_employees": top_employees,
        "top_services": top_services,
        "top_revenue_customers": top_revenue_customers,
        "customer_lifetime_value": customer_lifetime_value,
        "top_suburbs": top_suburbs,
        "repeat_customer_count": repeat_customer_count,
        "total_customer_count": total_customer_count,
        "repeat_customer_rate": repeat_customer_rate,
        "top_employees": top_employees,
        "employee_revenue": employee_revenue,
        "total_quotes": total_quotes,
        "accepted_quotes": accepted_quotes,
        "quote_conversion_rate": quote_conversion_rate,
        "new_customers_this_month": new_customers_this_month,
        "completed_jobs_count": completed_jobs_count,
        "average_job_value": average_job_value,
        "revenue_by_service": revenue_by_service,
        "revenue_by_suburb": revenue_by_suburb,
        "top_10_customers": top_10_customers,
        "health_score": health_score,
        "health_status": health_status,
        "today_jobs": today_jobs,
        "outstanding_invoices": outstanding_invoices,
        "low_stock_items": low_stock_items,
        "overdue_equipment": overdue_equipment,
        "vehicles_due_service": vehicles_due_service,
        "executive_alerts": executive_alerts,
    }

    return render(request, "dashboard/finance/business_intelligence.html", context)


@login_required
def export_business_report(request):

    response = HttpResponse(content_type="application/pdf")

    response["Content-Disposition"] = 'attachment; filename="business_report.pdf"'

    doc = SimpleDocTemplate(response)

    styles = getSampleStyleSheet()

    content = []

    monthly_expenses = Expense.objects.aggregate(total=Sum("amount"))["total"] or 0

    monthly_revenue = (
        Invoice.objects.filter(status="paid").aggregate(total=Sum("total_amount"))[
            "total"
        ]
        or 0
    )

    estimated_profit = monthly_revenue - monthly_expenses

    content.append(Paragraph("YD Commercial Cleaning Services", styles["Title"]))

    content.append(Spacer(1, 20))

    content.append(Paragraph("Business Intelligence Report", styles["Heading2"]))

    content.append(Spacer(1, 20))

    content.append(Paragraph(f"Generated: {timezone.localdate()}", styles["Normal"]))

    content.append(Spacer(1, 20))

    content.append(Paragraph(f"Revenue: ${monthly_revenue}", styles["Normal"]))

    content.append(Paragraph(f"Expenses: ${monthly_expenses}", styles["Normal"]))

    content.append(Paragraph(f"Profit: ${estimated_profit}", styles["Normal"]))

    doc.build(content)

    return response


@login_required
@require_POST
@permission_required(("expenses.view_expense", "invoices.view_invoice"), raise_exception=True)
def email_business_report(request):

    from io import BytesIO

    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()

    content = []

    monthly_expenses = Expense.objects.aggregate(total=Sum("amount"))["total"] or 0

    monthly_revenue = (
        Invoice.objects.filter(status="paid").aggregate(total=Sum("total_amount"))[
            "total"
        ]
        or 0
    )

    estimated_profit = monthly_revenue - monthly_expenses

    content.append(Paragraph("YD Commercial Cleaning Services", styles["Title"]))

    content.append(Spacer(1, 20))

    content.append(Paragraph("Business Intelligence Report", styles["Heading2"]))

    content.append(Spacer(1, 20))

    content.append(Paragraph(f"Revenue: ${monthly_revenue}", styles["Normal"]))

    content.append(Paragraph(f"Expenses: ${monthly_expenses}", styles["Normal"]))

    content.append(Paragraph(f"Profit: ${estimated_profit}", styles["Normal"]))

    doc.build(content)

    pdf = buffer.getvalue()

    buffer.close()

    email = EmailMessage(
        subject="Business Intelligence Report",
        body="Attached is your latest business report.",
        to=["ydcommercialcleaning@gmail.com"],
    )

    email.attach("business_report.pdf", pdf, "application/pdf")

    email.send()

    messages.success(request, "PDF report emailed successfully.")

    return redirect("business_intelligence")


@login_required
def operations_command_centre(request):

    today = timezone.localdate()
    due_limit = today + timedelta(days=30)

    overdue_equipment = Equipment.objects.filter(next_service_date__lt=today)
    vehicles_due_service = Vehicle.objects.filter(service_due_date__lt=today)

    low_stock_supplies = CleaningSupply.objects.filter(
        current_stock__lte=F("minimum_stock")
    )

    open_purchase_orders = PurchaseOrder.objects.filter(
        status__in=["draft", "ordered"]
    )

    outstanding_invoices = Invoice.objects.exclude(
        status__in=["paid", "cancelled"]
    ).select_related("booking", "booking__customer").order_by("due_date")

    unassigned_jobs = Booking.objects.filter(
        assigned_employee__isnull=True,
        booking_date__gte=today,
    ).exclude(status="cancelled").select_related("customer").order_by(
        "booking_date", "booking_time"
    )
    upcoming_equipment = Equipment.objects.filter(
        next_service_date__gte=today,
        next_service_date__lte=due_limit,
    )
    vehicles_due_soon = Vehicle.objects.filter(
        service_due_date__gte=today,
        service_due_date__lte=due_limit,
    )

    context = {
        "today": today,
        "overdue_equipment": overdue_equipment,
        "upcoming_equipment": upcoming_equipment,
        "vehicles_due_service": vehicles_due_service,
        "vehicles_due_soon": vehicles_due_soon,
        "low_stock_supplies": low_stock_supplies,
        "open_purchase_orders": open_purchase_orders,
        "outstanding_invoices": outstanding_invoices,
        "unassigned_jobs": unassigned_jobs,
    }

    return render(request, "dashboard/command_centres/operations_command_centre.html", context)


@login_required
def customer_360(request, customer_id):

    customer = Customer.objects.get(id=customer_id)

    bookings = customer.bookings.all().order_by("-created_at")[:10]

    customer_invoices = Invoice.objects.filter(booking__customer=customer)
    invoices = (
        customer_invoices
        .select_related("booking")
        .order_by("-created_at")[:10]
    )

    quotes = QuoteRequest.objects.filter(email=customer.email).order_by("-created_at")[
        :10
    ]

    outstanding_invoices = customer_invoices.exclude(status="paid").count()

    context = {
        "customer": customer,
        "bookings": bookings,
        "invoices": invoices,
        "total_revenue": (
            Invoice.objects.filter(booking__customer=customer, status="paid").aggregate(
                total=Sum("total_amount")
            )["total"]
            or 0
        ),
        "quotes": quotes,
        "outstanding_invoices": outstanding_invoices,
    }

    return render(request, "customers/customer_360.html", context)


@login_required
@require_POST
@permission_required("customers.change_customer", raise_exception=True)
def send_customer_followup(request, customer_id):

    customer = get_object_or_404(Customer, id=customer_id)

    send_mail(
        subject="We Miss You!",
        message=f"""
Hi {customer.full_name},

It's been a while since we last helped you.

YD Commercial Cleaning Services would love to assist you again.

Contact us anytime for your next cleaning service.

Thank you.
""",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[customer.email],
        fail_silently=False,
    )

    messages.success(request, "Follow-up email sent successfully.")

    return redirect("customer_profile_360", customer_id=customer.id)


@login_required
def employee_performance_centre(request):

    employees = Employee.objects.filter(active=True).order_by("full_name")

    employee_rows = []

    for employee in employees:

        completed_jobs = Booking.objects.filter(
            assigned_employee=employee, status="completed"
        ).count()

        total_jobs = Booking.objects.filter(assigned_employee=employee).count()

        revenue_generated = (
            Booking.objects.filter(
                assigned_employee=employee, status="completed"
            ).aggregate(total=Sum("quoted_price"))["total"]
            or 0
        )

        payroll_total = (
            PayrollRecord.objects.filter(employee=employee).aggregate(
                total=Sum("gross_pay")
            )["total"]
            or 0
        )

        profit_contribution = revenue_generated - payroll_total
        kpi_score = 0

        # Completed Jobs (40 points)

        if completed_jobs >= 50:
            kpi_score += 40

        elif completed_jobs >= 25:
            kpi_score += 30

        elif completed_jobs >= 10:
            kpi_score += 20

        # Revenue (30 points)

        if revenue_generated >= 20000:
            kpi_score += 30

        elif revenue_generated >= 10000:
            kpi_score += 20

        elif revenue_generated >= 5000:
            kpi_score += 10

        # Profit (30 points)

        if profit_contribution >= 10000:
            kpi_score += 30

        elif profit_contribution >= 5000:
            kpi_score += 20

        elif profit_contribution >= 2500:
            kpi_score += 10

        if kpi_score >= 90:
            bonus_recommendation = 500
        elif kpi_score >= 80:
            bonus_recommendation = 300
        elif kpi_score >= 70:
            bonus_recommendation = 150
        else:
            bonus_recommendation = 0

        profit_contribution = revenue_generated - payroll_total

        attendance_logs = AttendanceLog.objects.filter(employee=employee)

        total_attendance = attendance_logs.count()

        completed_attendance = attendance_logs.filter(
            check_out_time__isnull=False
        ).count()

        attendance_score = 0

        if total_attendance > 0:
            attendance_score = round((completed_attendance / total_attendance) * 100, 2)

        employee_rows.append(
            {
                "employee": employee,
                "completed_jobs": completed_jobs,
                "total_jobs": total_jobs,
                "revenue_generated": revenue_generated,
                "payroll_total": payroll_total,
                "profit_contribution": profit_contribution,
                "kpi_score": kpi_score,
                "attendance_score": attendance_score,
                "bonus_recommendation": bonus_recommendation,
            }
        )

        employee_rows = sorted(
            employee_rows, key=lambda row: row["kpi_score"], reverse=True
        )

        top_performer = employee_rows[0] if employee_rows else None
        second_performer = employee_rows[1] if len(employee_rows) > 1 else None
        third_performer = employee_rows[2] if len(employee_rows) > 2 else None

    return render(
        request,
        "employees/employee_performance_centre.html",
        {
            "employee_rows": employee_rows,
            "top_performer": top_performer,
            "second_performer": second_performer,
            "third_performer": third_performer,
        },
    )


@login_required
def employee_performance_detail(request, employee_id):

    employee = get_object_or_404(Employee, id=employee_id)

    bookings = (
        Booking.objects.filter(assigned_employee=employee)
        .select_related("customer")
        .order_by("-booking_date")
    )

    payrolls = PayrollRecord.objects.filter(employee=employee).order_by("-created_at")

    leave_requests = LeaveRequest.objects.filter(employee=employee).order_by(
        "-created_at"
    )

    completed_jobs = bookings.filter(status="completed").count()

    revenue_generated = (
        bookings.filter(status="completed").aggregate(total=Sum("quoted_price"))[
            "total"
        ]
        or 0
    )

    payroll_total = payrolls.aggregate(total=Sum("gross_pay"))["total"] or 0

    profit_contribution = revenue_generated - payroll_total

    return render(
        request,
        "employees/employee_performance_detail.html",
        {
            "employee": employee,
            "bookings": bookings,
            "payrolls": payrolls,
            "leave_requests": leave_requests,
            "completed_jobs": completed_jobs,
            "revenue_generated": revenue_generated,
            "payroll_total": payroll_total,
            "profit_contribution": profit_contribution,
        },
    )


@login_required
def export_employee_performance_pdf(request):

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        'attachment; filename="employee_performance_report.pdf"'
    )

    doc = SimpleDocTemplate(response, pagesize=landscape(A4))

    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("YD Commercial Cleaning Services", styles["Title"]))
    content.append(Paragraph("Employee Performance Report", styles["Heading2"]))
    content.append(Spacer(1, 20))

    data = [
        [
            "Employee",
            "Total Jobs",
            "Completed",
            "Revenue",
            "Payroll",
            "Profit",
            "KPI",
            "Attendance",
            "Bonus",
        ]
    ]

    employees = Employee.objects.filter(active=True).order_by("full_name")

    for employee in employees:

        completed_jobs = Booking.objects.filter(
            assigned_employee=employee, status="completed"
        ).count()

        total_jobs = Booking.objects.filter(assigned_employee=employee).count()

        revenue_generated = (
            Booking.objects.filter(
                assigned_employee=employee, status="completed"
            ).aggregate(total=Sum("quoted_price"))["total"]
            or 0
        )

        payroll_total = (
            PayrollRecord.objects.filter(employee=employee).aggregate(
                total=Sum("gross_pay")
            )["total"]
            or 0
        )

        profit = revenue_generated - payroll_total

        data.append(
            [
                employee.full_name,
                total_jobs,
                completed_jobs,
                f"${revenue_generated}",
                f"${payroll_total}",
                f"${profit}",
                "-",
                "-",
                "-",
            ]
        )

    table = Table(data)

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ]
        )
    )

    content.append(table)

    doc.build(content)

    return response


@login_required
@require_POST
@permission_required(
    ("attendance.view_attendancelog", "bookings.view_booking", "employees.view_employee", "payroll.view_payrollrecord"),
    raise_exception=True,
)
def email_employee_performance_report(request):

    from io import BytesIO

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))

    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("YD Commercial Cleaning Services", styles["Title"]))

    content.append(Paragraph("Employee Performance Report", styles["Heading2"]))

    content.append(Spacer(1, 20))

    data = [
        [
            "Employee",
            "Jobs",
            "Revenue",
            "Payroll",
        ]
    ]

    employees = Employee.objects.filter(active=True)

    for employee in employees:

        total_jobs = Booking.objects.filter(assigned_employee=employee).count()

        revenue = (
            Booking.objects.filter(
                assigned_employee=employee, status="completed"
            ).aggregate(total=Sum("quoted_price"))["total"]
            or 0
        )

        payroll = (
            PayrollRecord.objects.filter(employee=employee).aggregate(
                total=Sum("gross_pay")
            )["total"]
            or 0
        )

        data.append(
            [
                employee.full_name,
                total_jobs,
                f"${revenue}",
                f"${payroll}",
            ]
        )

    table = Table(data)

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )

    content.append(table)

    doc.build(content)

    pdf = buffer.getvalue()

    buffer.close()

    email = EmailMessage(
        subject="Employee Performance Report",
        body="Attached is the latest Employee Performance Report.",
        to=["ydcommercialcleaning@gmail.com"],
    )

    email.attach("employee_performance_report.pdf", pdf, "application/pdf")

    email.send()

    messages.success(request, "Employee Performance PDF emailed successfully.")

    return redirect("employee_performance_centre")


@login_required
def employee_attendance_analytics(request):

    employees = Employee.objects.filter(active=True)

    analytics_rows = []

    for employee in employees:

        attendance_count = AttendanceLog.objects.filter(employee=employee).count()

        completed_attendance = AttendanceLog.objects.filter(
            employee=employee, check_out_time__isnull=False
        ).count()

        attendance_percentage = 0

        if attendance_count > 0:
            attendance_percentage = round(
                (completed_attendance / attendance_count) * 100, 2
            )

        leave_count = LeaveRequest.objects.filter(employee=employee).count()

        approved_leave_count = LeaveRequest.objects.filter(
            employee=employee, status="approved"
        ).count()

        analytics_rows.append(
            {
                "employee": employee,
                "attendance_count": attendance_count,
                "completed_attendance_count": completed_attendance,
                "attendance_percentage": attendance_percentage,
                "leave_count": leave_count,
                "approved_leave_count": approved_leave_count,
            }
        )

    return render(
        request,
        "employees/employee_attendance_analytics.html",
        {
            "analytics_rows": analytics_rows,
            "attendance_total": sum(
                row["attendance_count"] for row in analytics_rows
            ),
            "attendance_completed": sum(
                row["completed_attendance_count"] for row in analytics_rows
            ),
            "approved_leave_total": sum(
                row["approved_leave_count"] for row in analytics_rows
            ),
        },
    )


@login_required
def owner_command_centre(request):

    today = timezone.localdate()
    month_start = today.replace(day=1)
    next_month_start = (
        month_start.replace(year=month_start.year + 1, month=1)
        if month_start.month == 12
        else month_start.replace(month=month_start.month + 1)
    )
    due_limit = today + timedelta(days=30)

    low_stock_supplies = CleaningSupply.objects.filter(
        current_stock__lte=F("minimum_stock")
    )
    overdue_equipment = Equipment.objects.filter(next_service_date__lt=today)
    vehicles_due_service = Vehicle.objects.filter(service_due_date__lt=today)
    draft_purchase_orders = PurchaseOrder.objects.filter(
        status__in=["draft", "ordered"]
    )
    outstanding_invoices = Invoice.objects.exclude(
        status__in=["paid", "cancelled"]
    )
    unassigned_jobs = Booking.objects.filter(
        assigned_employee__isnull=True,
        booking_date__gte=today,
    ).exclude(status="cancelled")
    today_jobs = Booking.objects.filter(booking_date=today).exclude(
        status="cancelled"
    ).count()
    monthly_revenue = Invoice.objects.filter(
        status="paid",
        paid_at__date__gte=month_start,
        paid_at__date__lt=next_month_start,
    ).aggregate(total=Sum("total_amount"))["total"] or 0
    monthly_expenses = Expense.objects.filter(
        date__gte=month_start,
        date__lt=next_month_start,
    ).aggregate(total=Sum("amount"))["total"] or 0
    payroll_month = PayrollRecord.objects.filter(
        period_start__lte=today,
        period_end__gte=month_start,
    ).aggregate(total=Sum("gross_pay"))["total"] or 0

    context = {
        "today": today,
        "today_jobs": today_jobs,
        "outstanding_invoices": outstanding_invoices.count(),
        "monthly_revenue": monthly_revenue,
        "monthly_expenses": monthly_expenses,
        "estimated_profit": monthly_revenue - monthly_expenses - payroll_month,
        "low_stock_items": low_stock_supplies.count(),
        "overdue_equipment": overdue_equipment.count(),
        "vehicles_due_service": vehicles_due_service.count(),
        "pending_leave_requests": LeaveRequest.objects.filter(
            status="pending"
        ).count(),
        "draft_purchase_orders": draft_purchase_orders.count(),
        "unassigned_jobs": unassigned_jobs.count(),
        "equipment_due_soon": Equipment.objects.filter(
            next_service_date__gte=today,
            next_service_date__lte=due_limit,
        ).count(),
        "vehicle_due_soon": Vehicle.objects.filter(
            service_due_date__gte=today,
            service_due_date__lte=due_limit,
        ).count(),
    }

    return render(request, "dashboard/command_centres/owner_command_centre.html", context)


@login_required
def business_forecasting_centre(request):

    today = timezone.localdate()
    month_start = today.replace(day=1)
    next_month_start = (
        month_start.replace(year=month_start.year + 1, month=1)
        if month_start.month == 12
        else month_start.replace(month=month_start.month + 1)
    )
    days_in_month = (next_month_start - month_start).days
    elapsed_days = today.day

    current_revenue = Decimal(
        str(
            Invoice.objects.filter(
                status="paid",
                paid_at__date__gte=month_start,
                paid_at__date__lt=next_month_start,
            ).aggregate(total=Sum("total_amount"))["total"]
            or 0
        )
    )
    current_expenses = Decimal(
        str(
            Expense.objects.filter(
                date__gte=month_start,
                date__lt=next_month_start,
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )
    )
    current_payroll = Decimal(
        str(
            PayrollRecord.objects.filter(
                period_start__lte=today,
                period_end__gte=month_start,
            ).aggregate(total=Sum("gross_pay"))["total"]
            or 0
        )
    )

    current_profit = current_revenue - current_expenses - current_payroll
    current_total_costs = current_expenses + current_payroll

    projected_revenue = round(
        (current_revenue / elapsed_days) * days_in_month,
        2,
    )
    projected_expenses = round(
        (current_expenses / elapsed_days) * days_in_month,
        2,
    )
    projected_payroll = round(
        (current_payroll / elapsed_days) * days_in_month,
        2,
    )

    projected_profit = round(
        projected_revenue - projected_expenses - projected_payroll,
        2,
    )
    projected_costs = projected_expenses + projected_payroll

    return render(
        request,
        "dashboard/command_centres/business_forecasting_centre.html",
        {
            "today": today,
            "days_in_month": days_in_month,
            "elapsed_days": elapsed_days,
            "current_revenue": current_revenue,
            "current_expenses": current_expenses,
            "current_payroll": current_payroll,
            "current_total_costs": current_total_costs,
            "current_profit": current_profit,
            "projected_revenue": projected_revenue,
            "projected_expenses": projected_expenses,
            "projected_payroll": projected_payroll,
            "projected_costs": projected_costs,
            "projected_profit": projected_profit,
            "revenue_chart": [
                float(current_revenue),
                float(projected_revenue),
            ],
            "expense_chart": [
                float(current_total_costs),
                float(projected_costs),
            ],
            "profit_chart": [
                float(current_profit),
                float(projected_profit),
            ],
        },
    )


@login_required
def ai_quote_estimator(request):

    from .forms import QuoteEstimateForm

    estimated_price = None
    confidence_level = None
    estimate_basis = ""
    historical_job_count = Booking.objects.filter(status="completed").count()

    if request.method == "POST":
        form = QuoteEstimateForm(request.POST)
        if form.is_valid():
            bedrooms = form.cleaned_data["bedrooms"]
            bathrooms = form.cleaned_data["bathrooms"]
            property_type = form.cleaned_data["property_type"]

            completed_jobs = Booking.objects.filter(status="completed")
            historical_average = completed_jobs.aggregate(
                avg=Avg("quoted_price")
            )["avg"]
            pricing_history_count = historical_job_count
            if historical_average is not None:
                estimate_basis = (
                    "Based on the average quoted value across "
                    f"{historical_job_count} completed jobs."
                )
                confidence_level = (
                    "High"
                    if historical_job_count >= 100
                    else "Medium"
                    if historical_job_count >= 25
                    else "Low"
                )
            else:
                paid_invoices = Invoice.objects.filter(status="paid")
                historical_average = paid_invoices.aggregate(
                    avg=Avg("total_amount")
                )["avg"]
                pricing_history_count = paid_invoices.count()
                if historical_average is not None:
                    estimate_basis = (
                        "Based on average paid invoice value across "
                        f"{pricing_history_count} paid invoices."
                    )
                    confidence_level = "Low"

            if historical_average is None:
                average_job_value = Decimal("250.00")
                estimate_basis = (
                    "No completed-job or paid-invoice pricing history is available. "
                    "A starter baseline is used; treat this as a rough guide only."
                )
                confidence_level = "No history"
            else:
                average_job_value = historical_average

            estimated_price = average_job_value
            estimated_price += Decimal(bedrooms) * Decimal("20.00")
            estimated_price += Decimal(bathrooms) * Decimal("15.00")

            if property_type == "house":
                estimated_price += Decimal("50.00")
            elif property_type == "commercial":
                estimated_price += Decimal("150.00")

            estimated_price = estimated_price.quantize(Decimal("0.01"))
    else:
        form = QuoteEstimateForm()

    return render(
        request,
        "dashboard/marketing/ai_quote_estimator.html",
        {
            "form": form,
            "estimated_price": estimated_price,
            "confidence_level": confidence_level,
            "estimate_basis": estimate_basis,
            "historical_job_count": historical_job_count,
        },
    )


@login_required
def quote_conversion_analytics(request):
    quotes = QuoteRequest.objects.all()
    total_quotes = quotes.count()
    booked_quotes = quotes.filter(status__in=["booked", "completed"]).count()
    declined_quotes = quotes.filter(status="lost").count()
    open_quotes = quotes.filter(
        status__in=["new", "contacted", "quoted"]
    ).count()

    total_quote_value = (
        QuoteRequest.objects.aggregate(total=Sum("estimated_price"))["total"] or 0
    )

    booked_revenue = (
        QuoteRequest.objects.filter(status__in=["booked", "completed"]).aggregate(
            total=Sum("estimated_price")
        )["total"]
        or 0
    )

    lost_revenue = (
        QuoteRequest.objects.filter(status="lost").aggregate(
            total=Sum("estimated_price")
        )["total"]
        or 0
    )

    average_quote_value = (
        QuoteRequest.objects.aggregate(avg=Avg("estimated_price"))["avg"] or 0
    )

    lost_quote_value = (
        QuoteRequest.objects.filter(status="lost").aggregate(
            total=Sum("estimated_price")
        )["total"]
        or 0
    )

    conversion_rate = 0

    source_rows = []

    source_aggregates = (
        QuoteRequest.objects.values("lead_source")
        .annotate(
            total=Count("pk"),
            booked=Count("pk", filter=Q(status__in=["booked", "completed"])),
        )
        .order_by("lead_source")
    )
    for aggregate in source_aggregates:
        source_total = aggregate["total"]
        source_booked = aggregate["booked"]
        source_rate = (
            round((source_booked / source_total) * 100, 2)
            if source_total
            else 0
        )

        source_rows.append(
            {
                "source": dict(QuoteRequest.LEAD_SOURCE_CHOICES).get(
                    aggregate["lead_source"],
                    aggregate["lead_source"] or "Unknown",
                ),
                "total": source_total,
                "booked": source_booked,
                "rate": source_rate,
            }
        )

    if total_quotes > 0:
        conversion_rate = round((booked_quotes / total_quotes) * 100, 2)

    return render(
        request,
        "dashboard/marketing/quote_conversion_analytics.html",
        {
            "total_quotes": total_quotes,
            "accepted_quotes": booked_quotes,
            "booked_quotes": booked_quotes,
            "declined_quotes": declined_quotes,
            "open_quotes": open_quotes,
            "conversion_rate": conversion_rate,
            "lost_quote_value": lost_quote_value,
            "source_rows": source_rows,
            "total_quote_value": total_quote_value,
            "booked_revenue": booked_revenue,
            "lost_revenue": lost_revenue,
            "average_quote_value": round(average_quote_value, 2),
        },
    )


@admin_required
def quote_followup_centre(request):

    followup_date = timezone.now() - timedelta(days=2)

    quotes = QuoteRequest.objects.filter(
        status="quoted", created_at__lte=followup_date
    ).order_by("-created_at")
    query = request.GET.get("q", "").strip()
    if query:
        quotes = quotes.filter(
            Q(name__icontains=query)
            | Q(email__icontains=query)
            | Q(property_type__icontains=query)
            | Q(suburb_postcode__icontains=query)
        )
    page_obj = Paginator(quotes, 25).get_page(request.GET.get("page"))

    return render(
        request,
        "dashboard/marketing/quote_followup_centre.html",
        {
            "quotes": page_obj.object_list,
            "page_obj": page_obj,
            "query": query,
        },
    )


@login_required
@require_POST
@permission_required("quotes.change_quoterequest", raise_exception=True)
def send_quote_followup_email(request, quote_id):

    quote = get_object_or_404(QuoteRequest, id=quote_id)

    send_mail(
        subject="Following Up On Your Cleaning Quote",
        message=f"""
Hi {quote.name},

We recently sent your cleaning quote.

If you have any questions or would like to proceed with the booking, please let us know.

YD Commercial Cleaning Services
""",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[quote.email],
        fail_silently=False,
    )

    messages.success(request, "Follow-up email sent.")

    return redirect("quote_followup_centre")


@require_POST
@admin_required
@permission_required(
    ("quotes.change_quoterequest", "bookings.add_booking"),
    raise_exception=True,
)
def convert_quote_to_booking(request, quote_id):

    quote = get_object_or_404(QuoteRequest, id=quote_id)

    try:
        booking, _ = convert_quote_service(
            quote_id=quote.id,
            booking_date=quote.preferred_date or timezone.localdate(),
            booking_time=time(9, 0),
        )
    except ValueError:
        logger.exception("Quote conversion failed for QuoteRequest %s.", quote.pk)
        messages.error(
            request,
            "This quote could not be converted to a booking. Please check its details or contact an administrator.",
        )
        return redirect("lead_list")

    try:
        create_or_update_booking_event(booking)
    except Exception:
        logger.exception(
            "Google Calendar sync failed after quote conversion for booking %s.",
            booking.pk,
        )
        messages.warning(
            request,
            "Booking created, but Google Calendar could not be synced automatically.",
        )

    messages.success(request, "Quote converted to booking successfully.")
    return redirect("booking_list")

@require_POST
@admin_required
@permission_required(
    ("bookings.view_booking", "invoices.add_invoice"),
    raise_exception=True,
)
def create_invoice_from_booking(request, booking_id):

    booking = get_object_or_404(Booking, id=booking_id)
    invoice, created = get_or_create_invoice_for_booking(booking)
    if not created:
        messages.warning(request, "Invoice already exists.")
        return redirect("invoice_detail", invoice_id=invoice.id)

    messages.success(request, "Invoice created successfully.")

    return redirect("invoice_detail", invoice_id=invoice.id)


@login_required
def owner_alert_centre(request):
    today = timezone.localdate()
    due_limit = today + timedelta(days=30)
    overdue_invoices = Invoice.objects.exclude(
        status__in=["paid", "cancelled"]
    ).filter(due_date__lt=today)
    expiring_contracts = CleaningContract.objects.filter(
        status="active",
        end_date__gte=today,
        end_date__lte=due_limit,
    )
    overdue_equipment = Equipment.objects.filter(next_service_date__lt=today)
    low_stock_supplies = CleaningSupply.objects.filter(
        current_stock__lte=F("minimum_stock")
    )
    vehicles_due_service = Vehicle.objects.filter(
        Q(service_due_date__lt=today)
        | Q(insurance_expiry__lt=today)
        | Q(registration_expiry__lt=today)
    )
    pending_leave = LeaveRequest.objects.filter(status="pending")
    unassigned_jobs = Booking.objects.filter(
        assigned_employee__isnull=True,
        booking_date__gte=today,
    ).exclude(status="cancelled")
    context = {
        "today": today,
        "overdue_invoices": overdue_invoices,
        "expiring_contracts": expiring_contracts,
        "pending_leave_requests": pending_leave,
        "low_stock_items": low_stock_supplies,
        "overdue_equipment": overdue_equipment,
        "vehicles_due_service": vehicles_due_service,
        "unassigned_jobs": unassigned_jobs,
        "alert_count": (
            overdue_invoices.count()
            + expiring_contracts.count()
            + pending_leave.count()
            + low_stock_supplies.count()
            + overdue_equipment.count()
            + vehicles_due_service.count()
            + unassigned_jobs.count()
        ),
    }

    return render(request, "dashboard/command_centres/owner_alert_centre.html", context)


@login_required
def customer_value_dashboard(request):

    customers = Customer.objects.all().order_by("-total_revenue")

    top_customer = customers.first()

    total_customer_revenue = (
        customers.aggregate(total=Sum("total_revenue"))["total"] or 0
    )

    average_customer_value = customers.aggregate(avg=Avg("total_revenue"))["avg"] or 0

    return render(
        request,
        "customers/customer_value_dashboard.html",
        {
            "customers": customers,
            "top_customer": top_customer,
            "total_customer_revenue": total_customer_revenue,
            "average_customer_value": average_customer_value,
        },
    )


@login_required
def vip_campaigns(request):

    vip_customers = Customer.objects.filter(total_revenue__gte=1000).order_by(
        "-total_revenue"
    )

    gold_customers = Customer.objects.filter(
        total_revenue__gte=500, total_revenue__lt=1000
    ).order_by("-total_revenue")

    inactive_customers = Customer.objects.filter(jobs_completed=0)

    context = {
        "vip_customers": vip_customers,
        "gold_customers": gold_customers,
        "inactive_customers": inactive_customers,
        "vip_count": vip_customers.count(),
        "gold_count": gold_customers.count(),
        "inactive_count": inactive_customers.count(),
    }

    return render(request, "dashboard/marketing/vip_campaigns.html", context)


@login_required
def job_profitability_dashboard(request):
    bookings = Booking.objects.select_related("customer").prefetch_related(
        "invoices"
    )
    query = request.GET.get("q", "").strip()
    if query:
        bookings = bookings.filter(
            Q(customer__full_name__icontains=query)
            | Q(service_type__icontains=query)
            | Q(suburb_postcode__icontains=query)
        )
    status_filter = request.GET.get("status", "").strip()
    if status_filter in {value for value, _ in Booking.STATUS_CHOICES}:
        bookings = bookings.filter(status=status_filter)
    else:
        status_filter = ""
    bookings = bookings.order_by("-booking_date", "-pk")
    paginator = Paginator(bookings, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    job_rows = []

    for booking in page_obj.object_list:
        invoices = [
            invoice
            for invoice in booking.invoices.all()
            if invoice.status != "cancelled"
        ]
        invoice_total = sum(
            (invoice.total_amount for invoice in invoices),
            Decimal("0.00"),
        )

        invoice_variance = invoice_total - (booking.quoted_price or Decimal("0.00"))

        job_rows.append(
            {
                "booking": booking,
                "invoices": invoices,
                "invoice_total": invoice_total,
                "quoted_price": booking.quoted_price,
                "invoice_variance": invoice_variance,
            }
        )

    all_bookings = Booking.objects.exclude(status="cancelled")
    booking_total = all_bookings.aggregate(
        total=Sum("quoted_price")
    )["total"] or Decimal("0.00")
    invoice_total = Invoice.objects.exclude(status="cancelled").aggregate(
        total=Sum("total_amount")
    )["total"] or Decimal("0.00")
    completed_jobs = Booking.objects.filter(status="completed").count()
    return render(
        request,
        "dashboard/finance/job_profitability_dashboard.html",
        {
            "job_rows": job_rows,
            "page_obj": page_obj,
            "booking_total": booking_total,
            "invoice_total": invoice_total,
            "invoice_variance_total": invoice_total - booking_total,
            "completed_jobs": completed_jobs,
            "query": query,
            "status_filter": status_filter,
            "status_choices": Booking.STATUS_CHOICES,
        },
    )


@login_required
def service_performance_dashboard(request):
    completed_bookings = Booking.objects.filter(status="completed")
    service_rows = list(
        completed_bookings.values("service_type")
        .annotate(
            jobs=Count("pk"),
            revenue=Sum("quoted_price"),
        )
        .order_by("-revenue", "service_type")
    )
    monthly_rows = list(
        completed_bookings.annotate(month=TruncMonth("booking_date"))
        .values("month")
        .annotate(revenue=Sum("quoted_price"))
        .order_by("month")
    )
    revenue_labels = [
        row["month"].strftime("%b %Y")
        for row in monthly_rows
        if row["month"]
    ]
    revenue_values = [
        float(row["revenue"] or 0)
        for row in monthly_rows
        if row["month"]
    ]
    total_completed_jobs = completed_bookings.count()
    total_completed_revenue = completed_bookings.aggregate(
        total=Sum("quoted_price")
    )["total"] or 0
    average_job_value = (
        total_completed_revenue / total_completed_jobs
        if total_completed_jobs
        else 0
    )
    service_labels = [row["service_type"] for row in service_rows]
    service_revenues = [float(row["revenue"] or 0) for row in service_rows]

    return render(
        request,
        "dashboard/finance/service_performance_dashboard.html",
        {
            "service_rows": service_rows,
            "service_labels": service_labels,
            "service_revenues": service_revenues,
            "revenue_labels": revenue_labels,
            "revenue_values": revenue_values,
            "total_completed_jobs": total_completed_jobs,
            "total_completed_revenue": total_completed_revenue,
            "average_job_value": average_job_value,
        },
    )


@login_required
def executive_bi_dashboard(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)
    next_month_start = (
        month_start.replace(year=month_start.year + 1, month=1)
        if month_start.month == 12
        else month_start.replace(month=month_start.month + 1)
    )
    completed_bookings = Booking.objects.filter(status="completed")
    total_revenue = Invoice.objects.filter(status="paid").aggregate(
        total=Sum("total_amount")
    )["total"] or 0
    monthly_revenue = Invoice.objects.filter(
        status="paid",
        paid_at__date__gte=month_start,
        paid_at__date__lt=next_month_start,
    ).aggregate(total=Sum("total_amount"))["total"] or 0

    booking_months = list(
        completed_bookings.annotate(month=TruncMonth("booking_date"))
        .values("month")
        .annotate(revenue=Sum("quoted_price"), bookings=Count("pk"))
        .order_by("month")
    )
    monthly_booking_labels = [
        row["month"].strftime("%b %Y")
        for row in booking_months
        if row["month"]
    ]
    monthly_booking_values = [
        row["bookings"]
        for row in booking_months
        if row["month"]
    ]
    invoice_months = list(
        Invoice.objects.filter(status="paid")
        .annotate(month=TruncMonth("paid_at"))
        .values("month")
        .annotate(revenue=Sum("total_amount"))
        .order_by("month")
    )
    monthly_revenue_labels = [
        row["month"].strftime("%b %Y")
        for row in invoice_months
        if row["month"]
    ]
    monthly_revenue_values = [
        float(row["revenue"] or 0)
        for row in invoice_months
        if row["month"]
    ]

    customer_months = list(
        Customer.objects.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(customers=Count("pk"))
        .order_by("month")
    )
    service_rows = list(
        completed_bookings.values("service_type")
        .annotate(revenue=Sum("quoted_price"))
        .order_by("-revenue", "service_type")
    )
    contract_rows = list(
        CleaningContract.objects.filter(status="active")
        .values("frequency")
        .annotate(revenue=Sum("price_per_visit"))
        .order_by("frequency")
    )

    context = {
        "today": today,
        "total_customers": Customer.objects.count(),
        "total_bookings": Booking.objects.exclude(status="cancelled").count(),
        "completed_bookings": completed_bookings.count(),
        "total_contracts": CleaningContract.objects.filter(status="active").count(),
        "total_revenue": total_revenue,
        "monthly_revenue": monthly_revenue,
        "vip_customers": Customer.objects.filter(total_revenue__gte=1000).count(),
        "monthly_revenue_labels": monthly_revenue_labels,
        "monthly_revenue_values": monthly_revenue_values,
        "monthly_booking_labels": monthly_booking_labels,
        "monthly_booking_values": monthly_booking_values,
        "customer_growth_labels": [
            row["month"].strftime("%b %Y")
            for row in customer_months
            if row["month"]
        ],
        "customer_growth_values": [
            row["customers"] for row in customer_months if row["month"]
        ],
        "service_revenue_labels": [row["service_type"] for row in service_rows],
        "service_revenue_values": [
            float(row["revenue"] or 0) for row in service_rows
        ],
        "contract_revenue_labels": [
            dict(CleaningContract.FREQUENCY_CHOICES).get(
                row["frequency"],
                row["frequency"],
            )
            for row in contract_rows
        ],
        "contract_revenue_values": [
            float(row["revenue"] or 0) for row in contract_rows
        ],
    }

    return render(
        request,
        "dashboard/finance/executive_bi_dashboard.html",
        context,
    )


@login_required
def employee_kpi_dashboard(request):

    employees = Employee.objects.all()

    employee_rows = []

    for employee in employees:

        booking_count = Booking.objects.filter(assigned_employee=employee).count()

        revenue = (
            Booking.objects.filter(assigned_employee=employee).aggregate(
                total=Sum("quoted_price")
            )["total"]
            or 0
        )

        hours_worked = (
            AttendanceLog.objects.filter(employee=employee).aggregate(
                total=Sum("total_hours")
            )["total"]
            or 0
        )

        employee_rows.append(
            {
                "employee": employee,
                "booking_count": booking_count,
                "revenue": revenue,
                "hours_worked": hours_worked,
                "revenue_per_hour": (
                    round(float(revenue) / float(hours_worked), 2)
                    if hours_worked
                    else 0
                ),
            }
        )

    employee_rows = sorted(employee_rows, key=lambda x: x["revenue"], reverse=True)
    total_employee_revenue = sum(
        (row["revenue"] for row in employee_rows), 0
    )
    total_employee_hours = sum(
        (row["hours_worked"] for row in employee_rows), 0
    )
    total_employee_bookings = sum(
        row["booking_count"] for row in employee_rows
    )

    return render(
        request,
        "employees/employee_kpi_dashboard.html",
        {
            "employee_rows": employee_rows,
            "total_employee_revenue": total_employee_revenue,
            "total_employee_hours": total_employee_hours,
            "total_employee_bookings": total_employee_bookings,
        },
    )


@login_required
def staff_schedule_dashboard(request):

    today = timezone.localdate()

    bookings = Booking.objects.filter(booking_date=today).select_related(
        "customer", "assigned_employee"
    )

    return render(
        request,
        "dashboard/finance/staff_schedule_dashboard.html",
        {
            "bookings": bookings,
            "today": today,
        },
    )


def _build_dashboard_gallery_groups(gallery_items):
    grouped_map = defaultdict(list)

    for item in gallery_items:
        customer = None
        if item.job_photo and item.job_photo.booking and item.job_photo.booking.customer:
            customer = item.job_photo.booking.customer
            key = f"customer-{customer.id}"
        else:
            key = f"item-{item.id}"

        grouped_map[key].append(item)

    gallery_groups = []
    for key, items in grouped_map.items():
        items = sorted(items, key=lambda x: x.created_at, reverse=True)
        first_item = items[0]
        customer = None
        if first_item.job_photo and first_item.job_photo.booking and first_item.job_photo.booking.customer:
            customer = first_item.job_photo.booking.customer

        gallery_groups.append(
            {
                "customer": customer,
                "items": items,
                "title": customer.gallery_display_name if customer else first_item.title,
                "service_type": first_item.service_type,
                "suburb": customer.suburb_postcode if customer and customer.suburb_postcode else first_item.suburb,
                "image_count": len(items),
            }
        )

    return gallery_groups
