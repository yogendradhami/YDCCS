import uuid

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.urls import reverse
from django.utils import timezone

from dashboard.models import (
    ActivityLog,
    CleaningSupply,
    Equipment,
    EquipmentAllocation,
    InventoryMovement,
)
from notifications.utils import notify_user

from .models import SupplyRequest, SupplyRequestItem


def _record_operation_activity(*, actor, title, description):
    ActivityLog.objects.create(
        user=actor,
        action_type="system",
        title=title,
        description=description,
    )
    from dashboard.operations_automation import record_operations_event

    if "supply request" in title.casefold():
        module = "Supply Requests"
        link = "/dashboard/supply-requests/"
    elif title == "Equipment returned":
        module = "Equipment"
        link = "/dashboard/equipment/"
    else:
        module = "Inventory"
        link = "/dashboard/inventory-transactions/"

    record_operations_event(
        module=module,
        event=title,
        trigger="Management recorded an inventory or supply-request action.",
        action_taken=description,
        actor=actor,
        link=link,
    )


@transaction.atomic
def approve_supply_request(*, request_id, actor, quantities, comments=""):
    request_record = SupplyRequest.objects.select_for_update().get(pk=request_id)
    if request_record.status != SupplyRequest.Status.PENDING:
        raise ValidationError("Only pending requests can be approved.")

    items = list(
        SupplyRequestItem.objects.select_for_update()
        .filter(request=request_record)
        .order_by("pk")
    )
    approved_values = []
    for item in items:
        quantity = quantities[item.pk]
        if quantity < 0 or quantity > item.requested_quantity:
            raise ValidationError("An approved quantity is outside the requested range.")
        if item.equipment_id and quantity not in {0, 1}:
            raise ValidationError("Equipment is individually tracked.")
        item.approved_quantity = quantity
        item.approval_comment = comments.strip()
        item.save(update_fields=["approved_quantity", "approval_comment"])
        approved_values.append(quantity)

    if not any(approved_values):
        raise ValidationError("Approve at least one positive item quantity.")

    request_record.status = (
        SupplyRequest.Status.APPROVED
        if all(
            quantity == item.requested_quantity
            for item, quantity in zip(items, approved_values)
        )
        else SupplyRequest.Status.PARTIALLY_APPROVED
    )
    request_record.decision_comments = comments.strip()
    request_record.decided_by = actor
    request_record.decided_at = timezone.now()
    request_record.save(
        update_fields=[
            "status",
            "decision_comments",
            "decided_by",
            "decided_at",
            "updated_at",
        ]
    )
    _record_operation_activity(
        actor=actor,
        title="Employee supply request approved",
        description=f"Request #{request_record.pk} approved: {comments.strip()}",
    )
    transaction.on_commit(
        lambda: notify_user(
            request_record.employee.user,
            f"Supply request #{request_record.pk} reviewed",
            f"Your request has been {request_record.get_status_display().lower()}.",
            "system",
        )
    )
    return request_record


@transaction.atomic
def reject_supply_request(*, request_id, actor, comments):
    comments = comments.strip()
    if len(comments) < 3:
        raise ValidationError("Provide a reason for rejecting the request.")

    request_record = SupplyRequest.objects.select_for_update().get(pk=request_id)
    if request_record.status != SupplyRequest.Status.PENDING:
        raise ValidationError("Only pending requests can be rejected.")

    request_record.status = SupplyRequest.Status.REJECTED
    request_record.decision_comments = comments
    request_record.decided_by = actor
    request_record.decided_at = timezone.now()
    request_record.save(
        update_fields=[
            "status",
            "decision_comments",
            "decided_by",
            "decided_at",
            "updated_at",
        ]
    )
    _record_operation_activity(
        actor=actor,
        title="Employee supply request rejected",
        description=f"Request #{request_record.pk} rejected: {comments}",
    )
    transaction.on_commit(
        lambda: notify_user(
            request_record.employee.user,
            f"Supply request #{request_record.pk} rejected",
            comments,
            "system",
        )
    )
    return request_record


@transaction.atomic
def issue_supply_request(
    *,
    request_id,
    actor,
    quantities,
    idempotency_key,
    notes="",
):
    request_record = SupplyRequest.objects.select_for_update().get(pk=request_id)
    if request_record.status not in {
        SupplyRequest.Status.APPROVED,
        SupplyRequest.Status.PARTIALLY_APPROVED,
        SupplyRequest.Status.PARTIALLY_ISSUED,
    }:
        raise ValidationError("Only approved requests can be issued.")

    items = list(
        SupplyRequestItem.objects.select_for_update()
        .filter(request=request_record)
        .order_by("pk")
    )
    issued_any = False
    for item in items:
        quantity = quantities.get(item.pk, 0)
        if quantity < 0 or quantity > item.remaining_to_issue:
            raise ValidationError(
                f"The issue quantity for {item.item_name} exceeds its approved remainder."
            )
        if not quantity:
            continue

        movement_key = uuid.uuid5(idempotency_key, f"request-item-{item.pk}")
        if InventoryMovement.objects.filter(idempotency_key=movement_key).exists():
            continue

        if item.supply_id:
            supply = CleaningSupply.objects.select_for_update().get(pk=item.supply_id)
            if quantity > supply.current_stock:
                raise ValidationError(
                    f"Insufficient stock for {supply.name}: "
                    f"{supply.current_stock} {supply.unit} available."
                )
            balance_before = supply.current_stock
            supply.current_stock -= quantity
            supply.save(update_fields=["current_stock"])
            InventoryMovement.objects.create(
                supply=supply,
                movement_type=InventoryMovement.MovementType.ISSUE,
                quantity_delta=-quantity,
                balance_before=balance_before,
                balance_after=supply.current_stock,
                request_item=item,
                idempotency_key=movement_key,
                actor=actor,
                employee=request_record.employee,
                notes=notes.strip(),
            )
            if balance_before > supply.minimum_stock >= supply.current_stock:
                from dashboard.inventory_services import _queue_low_stock_alert

                _queue_low_stock_alert(
                    supply,
                    actor=actor,
                    threshold_crossed=True,
                )
        else:
            if quantity != 1:
                raise ValidationError("Equipment is individually tracked.")
            equipment = Equipment.objects.select_for_update().get(pk=item.equipment_id)
            if equipment.assigned_employee_id or equipment.condition in {"repair", "retired"}:
                raise ValidationError(f"{equipment.name} is no longer available.")
            if not request_record.employee.user_id:
                raise ValidationError("This employee has no portal account to confirm receipt.")
            allocation = EquipmentAllocation.objects.create(
                equipment=equipment,
                employee=request_record.employee,
                request_item=item,
                issued_by=actor,
                received_by=request_record.employee.user,
            )
            equipment.assigned_employee = request_record.employee
            equipment.save(update_fields=["assigned_employee"])
            InventoryMovement.objects.create(
                equipment=equipment,
                movement_type=InventoryMovement.MovementType.ISSUE,
                quantity_delta=-1,
                balance_before=1,
                balance_after=0,
                request_item=item,
                equipment_allocation=allocation,
                idempotency_key=movement_key,
                actor=actor,
                employee=request_record.employee,
                notes=notes.strip(),
            )

        item.issued_quantity += quantity
        item.save(update_fields=["issued_quantity"])
        issued_any = True

    if issued_any:
        still_to_issue = SupplyRequestItem.objects.filter(
            request=request_record,
            approved_quantity__gt=0,
            issued_quantity__lt=F("approved_quantity"),
        ).exists()
        request_record.status = (
            SupplyRequest.Status.PARTIALLY_ISSUED
            if still_to_issue
            else SupplyRequest.Status.ISSUED
        )
        request_record.save(update_fields=["status", "updated_at"])
        _record_operation_activity(
            actor=actor,
            title="Employee supply handover recorded",
            description=f"Inventory issued for employee supply request #{request_record.pk}.",
        )
        transaction.on_commit(
            lambda: notify_user(
                request_record.employee.user,
                f"Supply request #{request_record.pk} handover recorded",
                "The issued quantities have been recorded in your request history.",
                "system",
            )
        )
    return request_record, issued_any


@transaction.atomic
def return_equipment_allocation(*, allocation_id, actor, notes=""):
    allocation = (
        EquipmentAllocation.objects.select_for_update()
        .select_related("equipment")
        .get(pk=allocation_id)
    )
    if not allocation.is_active:
        raise ValidationError("This equipment has already been returned.")

    equipment = Equipment.objects.select_for_update().get(pk=allocation.equipment_id)
    if equipment.assigned_employee_id != allocation.employee_id:
        raise ValidationError("The equipment assignment has changed; verify it first.")

    equipment.assigned_employee = None
    equipment.save(update_fields=["assigned_employee"])
    allocation.returned_by = actor
    allocation.returned_at = timezone.now()
    allocation.return_notes = notes.strip()
    allocation.save(update_fields=["returned_by", "returned_at", "return_notes"])
    InventoryMovement.objects.create(
        equipment=equipment,
        movement_type=InventoryMovement.MovementType.RETURN,
        quantity_delta=1,
        balance_before=0,
        balance_after=1,
        equipment_allocation=allocation,
        idempotency_key=uuid.uuid4(),
        actor=actor,
        employee=allocation.employee,
        notes=notes.strip(),
    )
    _record_operation_activity(
        actor=actor,
        title="Equipment returned",
        description=(
            f"{equipment.name} returned by {allocation.employee.full_name}; "
            f"allocation #{allocation.pk}."
        ),
    )
    return allocation


@transaction.atomic
def return_supply_stock(
    *, supply_id, quantity, employee, actor, notes, idempotency_key=None
):
    idempotency_key = idempotency_key or uuid.uuid4()
    existing = InventoryMovement.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing
    notes = notes.strip()
    if quantity <= 0 or not notes:
        raise ValidationError("Enter a positive return quantity and handover note.")
    supply = CleaningSupply.objects.select_for_update().get(pk=supply_id)
    existing = InventoryMovement.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing
    balance_before = supply.current_stock
    supply.current_stock += quantity
    supply.save(update_fields=["current_stock"])
    movement = InventoryMovement.objects.create(
        supply=supply,
        movement_type=InventoryMovement.MovementType.RETURN,
        quantity_delta=quantity,
        balance_before=balance_before,
        balance_after=supply.current_stock,
        idempotency_key=idempotency_key,
        actor=actor,
        employee=employee,
        notes=notes,
    )
    _record_operation_activity(
        actor=actor,
        title="Cleaning supplies returned",
        description=(
            f"{quantity} {supply.get_unit_display().lower()} of {supply.name} "
            f"returned by {employee.full_name}."
        ),
    )
    return movement
