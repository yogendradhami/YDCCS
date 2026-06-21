from datetime import timedelta

from django.db.models import F
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
from support.models import SupportTicket


def notification_context(request):
    if request.user.is_authenticated:
        notifications = request.user.notifications.all()[:10]
        unread_count = request.user.notifications.filter(is_read=False).count()

        # ==================================================
        # Reminder Center Count
        # ==================================================

        today = timezone.now().date()
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

        # ==================================================
        # Sidebar Notification Counts
        # ==================================================

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
            "support": SupportTicket.objects.filter(status="open").count(),
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

    else:
        notifications = []
        unread_count = 0
        notification_counts = {}

    return {
        "global_notifications": notifications,
        "global_unread_notifications": unread_count,
        "notification_counts": notification_counts,
    }
