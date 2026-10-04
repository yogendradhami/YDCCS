from datetime import timedelta

from django.db.models import Count, F
from django.utils import timezone

from bookings.models import Booking
from dashboard.models import (
    CleaningSupply,
    Equipment,
    MaintenanceHistory,
    PurchaseOrder,
    Supplier,
    Vehicle,
)
from employees.models import Employee
from invoices.models import Invoice
from leave_management.models import LeaveRequest
from quotes.models import QuoteRequest
from support.models import LiveChatConversation, SupportTicket
from corporate.models import CorporateLead


def notification_context(request):
    if not request.user.is_authenticated:
        return {
            "global_notifications": [],
            "global_unread_notifications": 0,
            "notification_counts": {},
        }

    notifications = request.user.notifications.order_by("-created_at")[:10]
    unread_count = request.user.notifications.filter(is_read=False).count()

    if not (
        request.path.startswith("/dashboard/")
        or request.path.startswith("/employee/")
        or request.path.startswith("/portal/")
    ):
        return {
            "global_notifications": list(notifications),
            "global_unread_notifications": unread_count,
            "notification_counts": {},
        }

    today = timezone.now().date()
    overdue_quote_date = today - timedelta(days=2)

    unread_by_type = {
        entry["notification_type"]: entry["total"]
        for entry in request.user.notifications.filter(is_read=False)
        .values("notification_type")
        .annotate(total=Count("id"))
    }

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
        "quote": unread_by_type.get("quote", 0),
        "corporate_leads": CorporateLead.objects.filter(status="new").count(),
        "booking": unread_by_type.get("booking", 0),
        "invoice": unread_by_type.get("invoice", 0),
        "customer": unread_by_type.get("customer", 0),
        "employee": unread_by_type.get("employee", 0),
        "gallery": unread_by_type.get("gallery", 0),
        "system": unread_by_type.get("system", 0),
        "review": unread_by_type.get("review", 0),
        "report": unread_by_type.get("report", 0),
        "contract": unread_by_type.get("contract", 0),
        "attendance": unread_by_type.get("attendance", 0),
        "payroll": unread_by_type.get("payroll", 0),
        "leave": unread_by_type.get("leave", 0),
        "roster": unread_by_type.get("roster", 0),
        "support": (
            SupportTicket.objects.filter(status="open").count()
            + LiveChatConversation.objects.filter(status="waiting").count()
        ),
    }

    notification_counts["equipment"] = Equipment.objects.filter(
        next_service_date__lt=timezone.localdate()
    ).count()

    notification_counts["supplies"] = CleaningSupply.objects.filter(
        current_stock__lte=F("minimum_stock")
    ).count()

    notification_counts["purchase_orders"] = PurchaseOrder.objects.filter(
        status="draft"
    ).count()

    notification_counts["executive_alerts"] = (
        notification_counts["equipment"]
        + notification_counts["supplies"]
        + notification_counts["purchase_orders"]
    )

    notification_counts["suppliers"] = Supplier.objects.filter(active=False).count()

    notification_counts["vehicles"] = (
        Vehicle.objects.filter(insurance_expiry__lt=today).count()
        + Vehicle.objects.filter(registration_expiry__lt=today).count()
        + Vehicle.objects.filter(service_due_date__lt=today).count()
    )

    notification_counts["forecasting"] = (
        notification_counts["equipment"]
        + notification_counts["supplies"]
        + notification_counts["vehicles"]
    )

    notification_counts["maintenance"] = MaintenanceHistory.objects.filter(
        next_service_date__lt=today
    ).count()

    notification_counts["quote_followups"] = QuoteRequest.objects.filter(
        status="quoted", created_at__lte=timezone.now() - timedelta(days=2)
    ).count()

    notification_counts["employee_performance"] = Employee.objects.filter(
        active=False
    ).count()

    notification_counts["attendance_analytics"] = LeaveRequest.objects.filter(
        status="pending"
    ).count()

    sidebar_count_keys = (
        "loyalty",
        "customer_analytics",
        "site_images",
        "blog",
        "services",
        "bonuses",
        "profit_loss",
        "gst_report",
        "finance_trends",
        "review_request",
        "review_analytics",
        "campaigns",
        "campaign_performance",
        "business_kpis",
        "email",
        "email_logs",
    )
    for key in sidebar_count_keys:
        notification_counts.setdefault(key, 0)

    return {
        "global_notifications": list(notifications),
        "global_unread_notifications": unread_count,
        "notification_counts": notification_counts,
    }
