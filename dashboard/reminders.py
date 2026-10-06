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

    for item in items["overdue_equipment"].values_list("pk", "next_service_date"):
        reminder_keys.append(f"equipment:{item[0]}:{item[1]}")

    for item in items["low_stock_supplies"].values_list(
        "pk", "current_stock", "minimum_stock"
    ):
        reminder_keys.append(
            f"supply:{item[0]}:{item[1]}:{item[2]}"
        )

    for item in items["draft_purchase_orders"].values_list("pk", "order_date"):
        reminder_keys.append(f"purchase-order:{item[0]}:{item[1]}")

    for item in items["vehicle_alerts"].values_list("pk", "service_due_date"):
        reminder_keys.append(f"vehicle:{item[0]}:{item[1]}")

    for item in items["maintenance_due"].values_list("pk", "next_service_date"):
        reminder_keys.append(f"maintenance:{item[0]}:{item[1]}")

    for item in items["contracts_expiring"].values_list("pk", "end_date", "status"):
        reminder_keys.append(f"contract:{item[0]}:{item[1]}:{item[2]}")

    return reminder_keys


def count_unseen_reminders(user, items):
    current_keys = set(get_reminder_keys(items))
    if not current_keys:
        return 0

    read_state = ReminderCenterReadState.objects.filter(user=user).first()
    seen_keys = set(read_state.seen_reminder_keys) if read_state else set()
    return len(current_keys - seen_keys)
