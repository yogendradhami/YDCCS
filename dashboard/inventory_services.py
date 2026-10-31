import uuid

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import (
    ActivityLog,
    CleaningSupply,
    GoodsReceipt,
    GoodsReceiptItem,
    InventoryMovement,
    PurchaseOrder,
)


def _record_inventory_activity(*, actor, title, description):
    ActivityLog.objects.create(
        user=actor,
        action_type="system",
        title=title,
        description=description,
    )
    from .operations_automation import record_operations_event

    record_operations_event(
        module=(
            "Goods Received"
            if title == "Purchase order goods received"
            else "Inventory"
        ),
        event=title,
        trigger="Management recorded an inventory transaction.",
        action_taken=description,
        actor=actor,
        link=(
            "/dashboard/goods-received/"
            if title == "Purchase order goods received"
            else "/dashboard/inventory-transactions/"
        ),
    )


def _queue_low_stock_alert(supply, *, actor=None, threshold_crossed=False):
    if not supply.is_low_stock() or not (threshold_crossed or supply.current_stock <= supply.minimum_stock):
        return
    from .operations_automation import record_operations_event

    as_of = timezone.localdate()
    record_operations_event(
        module="Inventory",
        event=f"Low stock: {supply.name}",
        trigger="On-hand quantity is at or below the reorder threshold.",
        action_taken="Created an in-app management notification.",
        result=(
            f"{supply.current_stock} {supply.get_unit_display().lower()} remain; "
            "a reorder quantity is suggested but no order was placed."
        ),
        actor=actor,
        metadata={
            "supply_id": supply.pk,
            "current_stock": supply.current_stock,
            "minimum_stock": supply.minimum_stock,
        },
        idempotency_key=f"automation:low-stock:{supply.pk}:{as_of.isoformat()}",
        link="/dashboard/supplies/",
    )


@transaction.atomic
def record_opening_supply_stock(*, supply_id, quantity, actor):
    if quantity < 0:
        raise ValidationError("Opening stock cannot be negative.")
    supply = CleaningSupply.objects.select_for_update().get(pk=supply_id)
    if supply.current_stock != 0:
        raise ValidationError("Opening stock can only be recorded for an empty balance.")
    if not quantity:
        return None

    movement = InventoryMovement.objects.create(
        supply=supply,
        movement_type=InventoryMovement.MovementType.OPENING,
        quantity_delta=quantity,
        balance_before=0,
        balance_after=quantity,
        idempotency_key=uuid.uuid4(),
        actor=actor,
        notes="Initial on-hand quantity at item creation.",
    )
    supply.current_stock = quantity
    supply.save(update_fields=["current_stock"])
    _queue_low_stock_alert(supply, actor=actor)
    return movement


@transaction.atomic
def adjust_supply_stock(
    *, supply_id, quantity_delta, actor, notes, idempotency_key=None
):
    idempotency_key = idempotency_key or uuid.uuid4()
    existing = InventoryMovement.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing
    if not quantity_delta:
        raise ValidationError("Enter a non-zero stock adjustment.")
    if not notes.strip():
        raise ValidationError("Explain why this stock adjustment is needed.")

    supply = CleaningSupply.objects.select_for_update().get(pk=supply_id)
    existing = InventoryMovement.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing
    balance_after = supply.current_stock + quantity_delta
    if balance_after < 0:
        raise ValidationError("The adjustment cannot reduce stock below zero.")

    movement = InventoryMovement.objects.create(
        supply=supply,
        movement_type=InventoryMovement.MovementType.ADJUSTMENT,
        quantity_delta=quantity_delta,
        balance_before=supply.current_stock,
        balance_after=balance_after,
        idempotency_key=idempotency_key,
        actor=actor,
        notes=notes.strip(),
    )
    supply.current_stock = balance_after
    supply.save(update_fields=["current_stock"])
    if supply.current_stock <= supply.minimum_stock < movement.balance_before:
        _queue_low_stock_alert(supply, actor=actor, threshold_crossed=True)
    _record_inventory_activity(
        actor=actor,
        title="Inventory stock adjusted",
        description=(
            f"{supply.name}: {quantity_delta:+} units. {notes.strip()}"
        ),
    )
    return movement


@transaction.atomic
def reverse_supply_movement(*, movement_id, actor, notes):
    if not notes.strip():
        raise ValidationError("Explain why this movement is being reversed.")

    movement = InventoryMovement.objects.select_for_update().get(pk=movement_id)
    if movement.supply_id is None:
        raise ValidationError(
            "Equipment movements must be reversed through their allocation record."
        )
    if movement.movement_type == InventoryMovement.MovementType.REVERSAL:
        raise ValidationError("A reversal cannot itself be reversed.")
    if movement.reversal_movements.exists():
        raise ValidationError("This inventory movement has already been reversed.")

    supply = CleaningSupply.objects.select_for_update().get(pk=movement.supply_id)
    quantity_delta = -movement.quantity_delta
    balance_after = supply.current_stock + quantity_delta
    if balance_after < 0:
        raise ValidationError(
            "This movement cannot be reversed because the stock has already been used."
        )

    reversal = InventoryMovement.objects.create(
        supply=supply,
        movement_type=InventoryMovement.MovementType.REVERSAL,
        quantity_delta=quantity_delta,
        balance_before=supply.current_stock,
        balance_after=balance_after,
        reversed_movement=movement,
        idempotency_key=uuid.uuid4(),
        actor=actor,
        notes=notes.strip(),
    )
    supply.current_stock = balance_after
    supply.save(update_fields=["current_stock"])

    if movement.request_item_id:
        from employees.models import SupplyRequest

        request_item = movement.request_item.__class__.objects.select_for_update().get(
            pk=movement.request_item_id
        )
        quantity_to_restore = -movement.quantity_delta
        if request_item.issued_quantity < quantity_to_restore:
            raise ValidationError("The request handover balance is inconsistent.")
        request_item.issued_quantity -= quantity_to_restore
        request_item.save(update_fields=["issued_quantity"])
        request_record = SupplyRequest.objects.select_for_update().get(
            pk=request_item.request_id
        )
        has_issued = request_record.items.filter(issued_quantity__gt=0).exists()
        has_remaining = request_record.items.filter(
            approved_quantity__gt=F("issued_quantity")
        ).exists()
        if has_remaining:
            partially_approved = request_record.items.filter(
                approved_quantity__lt=F("requested_quantity")
            ).exists()
            request_record.status = (
                SupplyRequest.Status.PARTIALLY_ISSUED
                if has_issued
                else (
                    SupplyRequest.Status.PARTIALLY_APPROVED
                    if partially_approved
                    else SupplyRequest.Status.APPROVED
                )
            )
        else:
            request_record.status = SupplyRequest.Status.ISSUED
        request_record.save(update_fields=["status", "updated_at"])

    if movement.goods_receipt_id:
        order = PurchaseOrder.objects.select_for_update().get(
            pk=movement.goods_receipt.purchase_order_id
        )
        received_quantity = movement.quantity_delta
        if received_quantity <= 0 or order.quantity_received < received_quantity:
            raise ValidationError("The purchase-order receipt balance is inconsistent.")
        order.quantity_received -= received_quantity
        order.status = "ordered"
        order.save(update_fields=["quantity_received", "status"])
    _record_inventory_activity(
        actor=actor,
        title="Inventory movement reversed",
        description=f"Movement #{movement.pk} reversed: {notes.strip()}",
    )
    return reversal


@transaction.atomic
def receive_purchase_order_goods(
    *,
    order_id,
    quantity,
    actor,
    idempotency_key,
    notes="",
):
    existing_receipt = GoodsReceipt.objects.filter(
        idempotency_key=idempotency_key
    ).first()
    if existing_receipt:
        return existing_receipt, False
    if quantity <= 0:
        raise ValidationError("Enter a received quantity greater than zero.")

    order = PurchaseOrder.objects.select_for_update().get(pk=order_id)
    existing_receipt = GoodsReceipt.objects.filter(
        idempotency_key=idempotency_key
    ).first()
    if existing_receipt:
        if existing_receipt.purchase_order_id != order.pk:
            raise ValidationError("This receipt token belongs to another purchase order.")
        return existing_receipt, False
    if order.status not in {"draft", "ordered"}:
        raise ValidationError("This purchase order is not open for receiving.")

    remaining = order.quantity - order.quantity_received
    if quantity > remaining:
        raise ValidationError(
            f"Only {remaining} more units can be received for this order."
        )

    supply = CleaningSupply.objects.select_for_update().get(pk=order.supply_id)
    balance_after = supply.current_stock + quantity
    receipt = GoodsReceipt.objects.create(
        purchase_order=order,
        received_by=actor,
        idempotency_key=idempotency_key,
        notes=notes.strip(),
    )
    GoodsReceiptItem.objects.create(
        receipt=receipt,
        purchase_order=order,
        quantity=quantity,
    )
    InventoryMovement.objects.create(
        supply=supply,
        movement_type=InventoryMovement.MovementType.RECEIPT,
        quantity_delta=quantity,
        balance_before=supply.current_stock,
        balance_after=balance_after,
        goods_receipt=receipt,
        idempotency_key=uuid.uuid4(),
        actor=actor,
        notes=notes.strip(),
    )

    supply.current_stock = balance_after
    supply.save(update_fields=["current_stock"])
    order.quantity_received += quantity
    if order.quantity_received == order.quantity:
        order.status = "received"
        order.save(update_fields=["quantity_received", "status"])
    else:
        order.status = "ordered"
        order.save(update_fields=["quantity_received", "status"])

    _record_inventory_activity(
        actor=actor,
        title="Purchase order goods received",
        description=(
            f"{quantity} {supply.get_unit_display().lower()} of {supply.name} "
            f"received against PO #{order.pk}."
        ),
    )
    return receipt, True


def build_low_stock_suggestions():
    return [
        {
            "supply": supply,
            "suggested_quantity": max(
                supply.minimum_stock - supply.current_stock,
                supply.minimum_stock,
            ),
        }
        for supply in CleaningSupply.objects.filter(
            current_stock__lte=F("minimum_stock")
        ).order_by("name")
    ]
