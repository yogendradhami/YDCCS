import uuid
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import F, Sum
from django.urls import reverse
from django.utils import timezone

from notifications.utils import notify_admins

from .models import OperationsAutomationEvent


REMINDER_WINDOW_DAYS = 14


def record_operations_event(
    *,
    module,
    event,
    trigger,
    action_taken,
    result="Completed",
    actor=None,
    metadata=None,
    idempotency_key=None,
    notify=True,
    link="",
):
    key = idempotency_key or uuid.uuid4().hex
    event_record, created = OperationsAutomationEvent.objects.get_or_create(
        idempotency_key=key,
        defaults={
            "module": module,
            "event": event,
            "trigger": trigger,
            "action_taken": action_taken,
            "result": result,
            "actor": actor,
            "metadata": metadata or {},
        },
    )
    if created and notify:
        notification_links = {
            "Finance": reverse("company_documents:invoice_review_list"),
            "Inventory": reverse("inventory_transactions"),
            "Supply Requests": reverse("supply_request_management"),
            "Goods Received": reverse("goods_received"),
            "Purchasing": reverse("purchase_orders"),
            "Equipment": reverse("equipment_list"),
            "Suppliers": reverse("supplier_list"),
            "Fleet": reverse("vehicle_list"),
            "Maintenance": reverse("maintenance_list"),
        }
        link = link or notification_links.get(
            module,
            reverse("operations_automation"),
        )
        transaction.on_commit(
            lambda: notify_admins(
                event[:200],
                f"{module}: {result}",
                "system",
                link,
            ),
            robust=True,
        )
    return event_record, created


def run_operations_automation(*, as_of=None):
    from dashboard.models import (
        CleaningSupply,
        Equipment,
        MaintenanceHistory,
        PurchaseOrder,
        Vehicle,
    )
    from employees.models import SupplyRequest
    from expenses.models import Expense

    as_of = as_of or timezone.localdate()
    reminder_cutoff = as_of + timedelta(days=REMINDER_WINDOW_DAYS)
    created_count = 0
    duplicate_count = 0

    def create_alert(*, key, module, event, trigger, message, metadata):
        nonlocal created_count, duplicate_count
        record, created = record_operations_event(
            idempotency_key=key,
            module=module,
            event=event,
            trigger=trigger,
            action_taken="Created an in-app management notification.",
            result=message,
            metadata=metadata,
            link={
                "Inventory": "/dashboard/supplies/",
                "Supply Requests": "/dashboard/supply-requests/",
                "Purchasing": "/dashboard/purchase-orders/",
                "Maintenance": "/dashboard/maintenance/",
                "Fleet": "/dashboard/vehicles/",
                "Finance": "/dashboard/company-documents/invoice-review/",
            }.get(module, ""),
        )
        if created:
            created_count += 1
        else:
            duplicate_count += 1
        return record, created

    for supply in CleaningSupply.objects.filter(
        current_stock__lte=F("minimum_stock")
    ).order_by("pk"):
        suggested_quantity = max(
            supply.minimum_stock - supply.current_stock,
            supply.minimum_stock,
        )
        create_alert(
            key=f"automation:low-stock:{supply.pk}:{as_of.isoformat()}",
            module="Inventory",
            event=f"Low stock: {supply.name}",
            trigger="On-hand quantity is at or below the reorder threshold.",
            message=(
                f"{supply.current_stock} {supply.get_unit_display().lower()} remain. "
                f"Suggested reorder: {suggested_quantity}. No purchase order was created."
            ),
            metadata={
                "supply_id": supply.pk,
                "current_stock": supply.current_stock,
                "minimum_stock": supply.minimum_stock,
                "suggested_quantity": suggested_quantity,
            },
        )

    for supply_request in SupplyRequest.objects.filter(
        status=SupplyRequest.Status.PENDING
    ).select_related("employee").order_by("pk"):
        create_alert(
            key=f"automation:supply-request:{supply_request.pk}:{as_of.isoformat()}",
            module="Supply Requests",
            event=f"Supply request #{supply_request.pk} needs review",
            trigger="Employee submitted a pending supply request.",
            message=(
                f"{supply_request.employee.full_name} has a "
                f"{supply_request.get_urgency_display().lower()}-priority request."
            ),
            metadata={"request_id": supply_request.pk},
        )

    for order in PurchaseOrder.objects.filter(
        status__in=("draft", "ordered"),
        expected_delivery_date__lt=as_of,
    ).select_related("supply").order_by("pk"):
        create_alert(
            key=f"automation:overdue-po:{order.pk}:{as_of.isoformat()}",
            module="Purchasing",
            event=f"Purchase order #{order.pk} is overdue",
            trigger="Expected delivery date has passed and the order is still open.",
            message=(
                f"PO #{order.pk} for {order.supply.name} was due "
                f"{order.expected_delivery_date:%d %b %Y}; verify delivery before recording goods received."
            ),
            metadata={"purchase_order_id": order.pk},
        )

    for maintenance in MaintenanceHistory.objects.filter(
        next_service_date__isnull=False,
        next_service_date__lte=reminder_cutoff,
    ).order_by("pk"):
        create_alert(
            key=f"automation:maintenance:{maintenance.pk}:{as_of.isoformat()}",
            module="Maintenance",
            event=f"Maintenance due: {maintenance.asset_name}",
            trigger="Next service date is due within the reminder window.",
            message=(
                f"{maintenance.asset_name} service is due "
                f"{maintenance.next_service_date:%d %b %Y}."
            ),
            metadata={"maintenance_id": maintenance.pk},
        )

    equipment_with_service_history = MaintenanceHistory.objects.filter(
        asset_type="equipment",
        next_service_date__isnull=False,
        next_service_date__lte=reminder_cutoff,
    ).values("asset_name")
    for equipment in Equipment.objects.filter(
        next_service_date__isnull=False,
        next_service_date__lte=reminder_cutoff,
    ).exclude(name__in=equipment_with_service_history).order_by("pk"):
        create_alert(
            key=(
                f"automation:equipment-service:{equipment.pk}:"
                f"{equipment.next_service_date.isoformat()}:{as_of.isoformat()}"
            ),
            module="Maintenance",
            event=f"Equipment service due: {equipment.name}",
            trigger="Equipment next service date is due within the reminder window.",
            message=(
                f"{equipment.name} service is due "
                f"{equipment.next_service_date:%d %b %Y}."
            ),
            metadata={
                "equipment_id": equipment.pk,
                "due_date": equipment.next_service_date.isoformat(),
            },
        )

    for vehicle in Vehicle.objects.filter(status="active").order_by("pk"):
        for field_name, label in (
            ("registration_expiry", "registration"),
            ("insurance_expiry", "insurance"),
            ("service_due_date", "service"),
        ):
            due_date = getattr(vehicle, field_name)
            if due_date and due_date <= reminder_cutoff:
                create_alert(
                    key=(
                        f"automation:vehicle:{vehicle.pk}:{field_name}:"
                        f"{due_date.isoformat()}:{as_of.isoformat()}"
                    ),
                    module="Fleet",
                    event=f"Vehicle {label} reminder: {vehicle.vehicle_name}",
                    trigger=f"Vehicle {label} date is due within the reminder window.",
                    message=(
                        f"{vehicle.vehicle_name} ({vehicle.registration_number}) "
                        f"{label} is due {due_date:%d %b %Y}."
                    ),
                    metadata={
                        "vehicle_id": vehicle.pk,
                        "date_field": field_name,
                        "due_date": due_date.isoformat(),
                    },
                )

    for expense in Expense.objects.filter(
        invoice_review__isnull=False,
        due_date__isnull=False,
        due_date__lte=reminder_cutoff,
    ).exclude(payment_status=Expense.PaymentStatus.PAID).select_related(
        "supplier", "invoice_review"
    ).order_by("pk"):
        create_alert(
            key=f"automation:invoice-due:{expense.pk}:{as_of.isoformat()}",
            module="Finance",
            event=f"Supplier invoice due: {expense.invoice_number}",
            trigger="Verified supplier invoice due date is approaching or past.",
            message=(
                f"{expense.supplier.name} invoice {expense.invoice_number} "
                f"for ${expense.amount:.2f} is due {expense.due_date:%d %b %Y}. "
                "Payment status has not been changed."
            ),
            metadata={"expense_id": expense.pk, "invoice_review_id": expense.invoice_review_id},
        )

    previous_month = as_of.replace(day=1) - timedelta(days=1)
    month_start = previous_month.replace(day=1)
    month_end = as_of.replace(day=1)
    monthly_total = (
        Expense.objects.filter(date__gte=month_start, date__lt=month_end).aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )
    previous_month_label = month_start.strftime("%B %Y")
    create_alert(
        key=f"automation:monthly-expense-summary:{month_start.isoformat()}",
        module="Finance",
        event=f"Monthly expense summary: {previous_month_label}",
        trigger="Monthly expense summary for the previous calendar month.",
        message=(
            f"Recorded expenses for {previous_month_label} total "
            f"${monthly_total:.2f}. The summary is informational and does not change records."
        ),
        metadata={
            "period_start": month_start.isoformat(),
            "period_end": month_end.isoformat(),
            "total": format(monthly_total, ".2f"),
        },
    )

    _, run_created = record_operations_event(
        module="Automation",
        event="Operations automation checks completed",
        trigger="Scheduled or manager-requested daily check.",
        action_taken="Evaluated inventory, supply requests, purchasing, fleet, maintenance and invoices.",
        result=(
            f"{created_count} new alerts recorded; "
            f"{duplicate_count} duplicate alerts skipped."
        ),
        metadata={"as_of": as_of.isoformat()},
        idempotency_key=f"automation-run:{as_of.isoformat()}",
        link=reverse("operations_automation"),
    )
    if run_created:
        created_count += 1
        transaction.on_commit(
            lambda: notify_admins(
                "Automation history updated",
                f"Daily operations check for {as_of:%d %b %Y} was recorded.",
                "system",
                reverse("operations_automation_history"),
            ),
            robust=True,
        )
    else:
        duplicate_count += 1

    return {
        "events_created": created_count,
        "duplicates_skipped": duplicate_count,
        "as_of": as_of,
    }
