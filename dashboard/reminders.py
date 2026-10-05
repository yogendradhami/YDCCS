from datetime import timedelta

from django.db.models import F
from django.utils import timezone

from contracts.models import CleaningContract
from dashboard.models import (
    CleaningSupply,
    Equipment,
    MaintenanceHistory,
    PurchaseOrder,
    Vehicle,
)
from notifications.models import ReminderCenterReadState


def get_reminder_center_items(today=None):
    today = today or timezone.localdate()

    return {
        "overdue_equipment": Equipment.objects.filter(next_service_date__lt=today),
        "low_stock_supplies": CleaningSupply.objects.filter(
            current_stock__lte=F("minimum_stock")
        ),
        "draft_purchase_orders": PurchaseOrder.objects.filter(status="draft"),
        "vehicle_alerts": Vehicle.objects.filter(service_due_date__lt=today),
        "maintenance_due": MaintenanceHistory.objects.filter(
            next_service_date__lt=today
        ),
        "contracts_expiring": CleaningContract.objects.filter(
            end_date__lte=today + timedelta(days=30)
        ),
    }


def get_reminder_keys(items):
    reminder_keys = []

    for item in items["overdue_equipment"]:
        reminder_keys.append(f"equipment:{item.pk}:{item.next_service_date}")

    for item in items["low_stock_supplies"]:
        reminder_keys.append(
            f"supply:{item.pk}:{item.current_stock}:{item.minimum_stock}"
        )

    for item in items["draft_purchase_orders"]:
        reminder_keys.append(f"purchase-order:{item.pk}:{item.order_date}")

    for item in items["vehicle_alerts"]:
        reminder_keys.append(f"vehicle:{item.pk}:{item.service_due_date}")

    for item in items["maintenance_due"]:
        reminder_keys.append(f"maintenance:{item.pk}:{item.next_service_date}")

    for item in items["contracts_expiring"]:
        reminder_keys.append(f"contract:{item.pk}:{item.end_date}:{item.status}")

    return reminder_keys


def count_unseen_reminders(user, items):
    current_keys = set(get_reminder_keys(items))
    if not current_keys:
        return 0

    read_state = ReminderCenterReadState.objects.filter(user=user).first()
    seen_keys = set(read_state.seen_reminder_keys) if read_state else set()
    return len(current_keys - seen_keys)
