# ==========================================================
# File: dashboard/context_processors.py
# Purpose:
# Make company settings available in every template.
# This allows base.html, invoices, reports and emails
# to use business details from Dashboard → Settings.
# ==========================================================

<<<<<<< HEAD
from datetime import timedelta

from django.db.models import F
from django.utils import timezone

from bookings.models import Booking
from dashboard.models import (
    CleaningSupply,
    Equipment,
    PurchaseOrder,
    Supplier,
)
from invoices.models import Invoice
from quotes.models import QuoteRequest

from .models import CompanySettings
=======
import json
from urllib.parse import urljoin
from .models import CompanySettings
from dashboard.models import Supplier
from datetime import timedelta

from django.utils import timezone
from django.db.models import F
from django.templatetags.static import static

from invoices.models import Invoice
from bookings.models import Booking
from quotes.models import QuoteRequest
from dashboard.models import (
    Equipment,
    CleaningSupply,
    PurchaseOrder,
    Supplier,
)
>>>>>>> 5815f15 (Initial project commit)


def company_settings(request):
    # Get the first company settings record.
    # If it does not exist yet, return None safely.
    settings = CompanySettings.objects.first()

<<<<<<< HEAD
    return {"company_settings": settings}
=======
    site_url = request.build_absolute_uri("/").rstrip("/")
    business_name = settings.business_name if settings else "YD Commercial Cleaning Services"
    default_description = (
        f"{business_name} provides professional commercial, office, bond and residential cleaning across Adelaide, South Australia. "
        "Reliable, fully insured cleaning with fast quotes and local customer support."
    )
    address_text = settings.address if settings else ""
    address_parts = [part.strip() for part in address_text.split(",") if part.strip()]
    postal_code = ""
    address_region = "SA"
    address_locality = "Adelaide"
    street_address = address_text

    if len(address_parts) >= 2:
        street_address = address_parts[0]
        address_locality = address_parts[1]
    if len(address_parts) >= 3:
        address_region = address_parts[2].split()[0]
    if len(address_parts) >= 2:
        postal_code_search = [part for part in address_parts if part.strip().isdigit()]
        if postal_code_search:
            postal_code = postal_code_search[-1]

    default_image_path = static('images/logo.jpeg')
    default_image_url = urljoin(site_url + '/', default_image_path)
    open_graph_image = default_image_url
    if settings and getattr(settings, 'logo', None):
        open_graph_image = urljoin(site_url + '/', settings.logo.url)

    same_as = [
        url for url in [
            settings.facebook_url if settings else None,
            settings.instagram_url if settings else None,
            settings.linkedin_url if settings else None,
            settings.tiktok_url if settings else None,
        ]
        if url
    ]

    return {
        "company_settings": settings,
        "site_url": site_url,
        "default_seo_description": default_description,
        "default_seo_keywords": (
            "Adelaide cleaning service, commercial cleaning Adelaide, office cleaning Adelaide, end of lease cleaning, "
            "bond cleaning Adelaide, window cleaning Adelaide, deep cleaning Adelaide, local cleaners SA"
        ),
        "address_street": street_address,
        "address_locality": address_locality,
        "address_region": address_region,
        "address_postal_code": postal_code,
        "address_country": "Australia",
        "open_graph_image": open_graph_image,
        "twitter_image": open_graph_image,
        "same_as_urls": json.dumps(same_as),
        "opening_hours": json.dumps([
            {
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                "opens": "08:00",
                "closes": "12:00"
            }
        ]),
        "service_area_list": json.dumps([
            "Adelaide CBD",
            "Unley",
            "Norwood",
            "Glenelg",
            "Burnside",
            "Prospect",
            "Mawson Lakes",
            "Modbury",
            "North Adelaide",
            "Salisbury"
        ]),
    }
>>>>>>> 5815f15 (Initial project commit)


def notification_context(request):
    if request.user.is_authenticated:
        notifications = request.user.notifications.all()[:10]

<<<<<<< HEAD
        unread_count = request.user.notifications.filter(is_read=False).count()
=======
        unread_count = request.user.notifications.filter(
            is_read=False
        ).count()
>>>>>>> 5815f15 (Initial project commit)

        today = timezone.localdate()
        overdue_quote_date = today - timedelta(days=2)

<<<<<<< HEAD
        overdue_invoices_count = (
            Invoice.objects.exclude(status="paid").filter(due_date__lt=today).count()
        )

        unassigned_jobs_count = (
            Booking.objects.filter(
                assigned_employee__isnull=True, booking_date__gte=today
            )
            .exclude(status="cancelled")
            .count()
        )

        pending_quotes_count = QuoteRequest.objects.filter(
            status__in=["new", "contacted", "quoted"],
            created_at__date__lte=overdue_quote_date,
        ).count()

        reminder_count = (
            overdue_invoices_count + unassigned_jobs_count + pending_quotes_count
=======
        overdue_invoices_count = Invoice.objects.exclude(
            status="paid"
        ).filter(
            due_date__lt=today
        ).count()

        unassigned_jobs_count = Booking.objects.filter(
            assigned_employee__isnull=True,
            booking_date__gte=today
        ).exclude(
            status="cancelled"
        ).count()

        pending_quotes_count = QuoteRequest.objects.filter(
            status__in=["new", "contacted", "quoted"],
            created_at__date__lte=overdue_quote_date
        ).count()

        reminder_count = (
            overdue_invoices_count
            + unassigned_jobs_count
            + pending_quotes_count
>>>>>>> 5815f15 (Initial project commit)
        )

        notification_counts = {
            "reminders": reminder_count,
<<<<<<< HEAD
            "quote": request.user.notifications.filter(
                notification_type="quote", is_read=False
            ).count(),
            "booking": request.user.notifications.filter(
                notification_type="booking", is_read=False
            ).count(),
            "invoice": request.user.notifications.filter(
                notification_type="invoice", is_read=False
            ).count(),
            "customer": request.user.notifications.filter(
                notification_type="customer", is_read=False
            ).count(),
            "employee": request.user.notifications.filter(
                notification_type="employee", is_read=False
            ).count(),
            "gallery": request.user.notifications.filter(
                notification_type="gallery", is_read=False
            ).count(),
            "review": request.user.notifications.filter(
                notification_type="review", is_read=False
            ).count(),
            "report": request.user.notifications.filter(
                notification_type="report", is_read=False
            ).count(),
            "contract": request.user.notifications.filter(
                notification_type="contract", is_read=False
            ).count(),
            "attendance": request.user.notifications.filter(
                notification_type="attendance", is_read=False
            ).count(),
            "payroll": request.user.notifications.filter(
                notification_type="payroll", is_read=False
            ).count(),
            "leave": request.user.notifications.filter(
                notification_type="leave", is_read=False
            ).count(),
            "roster": request.user.notifications.filter(
                notification_type="roster", is_read=False
            ).count(),
=======
            "quote": request.user.notifications.filter(notification_type="quote", is_read=False).count(),
            "booking": request.user.notifications.filter(notification_type="booking", is_read=False).count(),
            "invoice": request.user.notifications.filter(notification_type="invoice", is_read=False).count(),
            "customer": request.user.notifications.filter(notification_type="customer", is_read=False).count(),
            "employee": request.user.notifications.filter(notification_type="employee", is_read=False).count(),
            "gallery": request.user.notifications.filter(notification_type="gallery", is_read=False).count(),
            "review": request.user.notifications.filter(notification_type="review", is_read=False).count(),
            "report": request.user.notifications.filter(notification_type="report", is_read=False).count(),
            "contract": request.user.notifications.filter(notification_type="contract", is_read=False).count(),
            "attendance": request.user.notifications.filter(notification_type="attendance", is_read=False).count(),
            "payroll": request.user.notifications.filter(notification_type="payroll", is_read=False).count(),
            "leave": request.user.notifications.filter(notification_type="leave", is_read=False).count(),
            "roster": request.user.notifications.filter(notification_type="roster", is_read=False).count(),
>>>>>>> 5815f15 (Initial project commit)
        }

        notification_counts["equipment"] = Equipment.objects.filter(
            next_service_date__lt=today
        ).count()

        notification_counts["supplies"] = CleaningSupply.objects.filter(
            current_stock__lte=F("minimum_stock")
        ).count()

        notification_counts["purchase_orders"] = PurchaseOrder.objects.filter(
            status="draft"
        ).count()

<<<<<<< HEAD
        notification_counts["suppliers"] = Supplier.objects.filter(active=False).count()
=======
        notification_counts["suppliers"] = Supplier.objects.filter(
            active=False
        ).count()
>>>>>>> 5815f15 (Initial project commit)

    else:
        notifications = []
        unread_count = 0
        notification_counts = {}

    return {
        "global_notifications": notifications,
        "global_unread_notifications": unread_count,
        "notification_counts": notification_counts,
<<<<<<< HEAD
    }
=======
    }
>>>>>>> 5815f15 (Initial project commit)
