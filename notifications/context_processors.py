from datetime import timedelta

from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone

from dashboard.reminders import (
    count_unseen_reminder_keys,
    get_reminder_center_items,
    get_reminder_keys,
)
from employees.models import Employee
from leave_management.models import LeaveRequest
from quotes.models import QuoteRequest
from support.models import LiveChatConversation, SupportTicket
from corporate.models import CorporateLead
from .utils import NOTIFICATION_AREAS


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
    cache_key = f"notification-counts:{request.user.pk}:{today.isoformat()}"
    cached_counts = cache.get(cache_key)
    if cached_counts is not None:
        return {
            "global_notifications": list(notifications),
            "global_unread_notifications": unread_count,
            "notification_counts": cached_counts,
        }

    unread_by_type = {
        entry["notification_type"]: entry["total"]
        for entry in request.user.notifications.filter(is_read=False)
        .values("notification_type")
        .annotate(total=Count("id"))
    }

    reminder_keys = cache.get_or_set(
        f"dashboard-reminder-keys:{today.isoformat()}",
        lambda: get_reminder_keys(get_reminder_center_items(today)),
        30,
    )
    reminder_count = count_unseen_reminder_keys(request.user, reminder_keys)

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
        "damage_report": unread_by_type.get("damage_report", 0),
        "contract": unread_by_type.get("contract", 0),
        "attendance": unread_by_type.get("attendance", 0),
        "payroll": unread_by_type.get("payroll", 0),
        "leave": unread_by_type.get("leave", 0),
        "roster": unread_by_type.get("roster", 0),
        "support_notifications": unread_by_type.get("support", 0),
        "support": (
            SupportTicket.objects.filter(status="open").count()
            + LiveChatConversation.objects.filter(status="waiting").count()
        ),
    }

    area_count_filters = {}
    area_count_aliases = {}
    for index, (area, path) in enumerate(NOTIFICATION_AREAS.items()):
        condition = Q(is_read=False, link__startswith=path)
        if area == "operations_automation":
            condition &= ~Q(
                link__startswith=NOTIFICATION_AREAS["automation_history"]
            )
        alias = f"area_{index}"
        area_count_aliases[area] = alias
        area_count_filters[alias] = Count("pk", filter=condition)

    area_count_values = request.user.notifications.aggregate(**area_count_filters)
    area_counts = {
        area: area_count_values[alias] or 0
        for area, alias in area_count_aliases.items()
    }
    notification_counts.update(area_counts)
    notification_counts["equipment"] = area_counts["equipment"]
    notification_counts["supplies"] = area_counts["supplies"]
    notification_counts["purchase_orders"] = area_counts["purchase_orders"]

    notification_counts["executive_alerts"] = (
        notification_counts["equipment"]
        + notification_counts["supplies"]
        + notification_counts["purchase_orders"]
    )

    notification_counts["suppliers"] = area_counts["suppliers"]
    notification_counts["vehicles"] = area_counts["vehicles"]

    notification_counts["forecasting"] = (
        notification_counts["equipment"]
        + notification_counts["supplies"]
        + notification_counts["vehicles"]
    )

    notification_counts["maintenance"] = area_counts["maintenance"]

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

    cache.set(cache_key, notification_counts, 60)

    return {
        "global_notifications": list(notifications),
        "global_unread_notifications": unread_count,
        "notification_counts": notification_counts,
    }
