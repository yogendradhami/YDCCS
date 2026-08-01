# ==========================================================
# File: dashboard/context_processors.py
# Purpose:
# Make company settings available in every template.
# This allows base.html, invoices, reports and emails
# to use business details from Dashboard → Settings.
# ==========================================================

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
from core.models import FAQQuestion
from invoices.models import Invoice
from quotes.models import QuoteRequest

from .models import CompanySettings


def company_settings(request):
    # Return the first company settings record when present.
    # When the database is empty, fall back to a safe default model instance
    # so templates can still render without raising lookup errors.
    settings = CompanySettings.objects.first() or CompanySettings()

    return {"company_settings": settings}


def seo_context(request):
    """Provide default SEO meta description and keywords."""
    return {
        "default_seo_description": "Professional commercial cleaning services in Adelaide. Expert office, house and end-of-lease cleaning.",
        "default_seo_keywords": "commercial cleaning Adelaide, office cleaning, house cleaning, end of lease cleaning, bond cleaning, window cleaning",
        "open_graph_image": "/static/img/og-image.png",
        "twitter_image": "/static/img/twitter-image.png",
        "site_url": "https://www.ydcleaning.com.au",
        "same_as_urls": '["https://www.facebook.com/ydcommercialcleaning","https://www.instagram.com/ydcommercialcleaning"]',
        "service_area_list": '["Adelaide","South Australia"]',
        "address_street": "Adelaide",
        "address_locality": "Adelaide",
        "address_region": "SA",
        "address_postal_code": "5000",
        "address_country": "AU",
    }


def notification_context(request):
    if request.user.is_authenticated:
        notifications = request.user.notifications.all()[:10]

        unread_count = request.user.notifications.filter(is_read=False).count()

        today = timezone.localdate()
        overdue_quote_date = today - timedelta(days=2)

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
        )

        notification_counts = {
            "reminders": reminder_count,
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

        notification_counts["suppliers"] = Supplier.objects.filter(active=False).count()
        notification_counts["faq_questions"] = FAQQuestion.objects.filter(is_published=False).count()

    else:
        notifications = []
        unread_count = 0
        notification_counts = {}

    return {
        "global_notifications": notifications,
        "global_unread_notifications": unread_count,
        "notification_counts": notification_counts,
    }
