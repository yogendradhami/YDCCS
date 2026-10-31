import uuid

from django.db import migrations, models


OPENING_NOTE = "Migrated opening balance; pre-ledger transaction history is unavailable."


def seed_inventory_opening_balances(apps, schema_editor):
    database = schema_editor.connection.alias
    Supply = apps.get_model("dashboard", "CleaningSupply")
    Equipment = apps.get_model("dashboard", "Equipment")
    PurchaseOrder = apps.get_model("dashboard", "PurchaseOrder")
    Allocation = apps.get_model("dashboard", "EquipmentAllocation")
    Movement = apps.get_model("dashboard", "InventoryMovement")

    PurchaseOrder.objects.using(database).filter(status="received").update(
        quantity_received=models.F("quantity")
    )

    for supply in Supply.objects.using(database).filter(current_stock__gt=0).iterator():
        Movement.objects.using(database).create(
            supply_id=supply.pk,
            movement_type="opening",
            quantity_delta=supply.current_stock,
            balance_before=0,
            balance_after=supply.current_stock,
            idempotency_key=uuid.uuid4(),
            actor_id=None,
            notes=OPENING_NOTE,
        )

    for equipment in Equipment.objects.using(database).filter(
        assigned_employee__isnull=False
    ).iterator():
        allocation = Allocation.objects.using(database).create(
            equipment_id=equipment.pk,
            employee_id=equipment.assigned_employee_id,
            request_item_id=None,
            issued_by_id=None,
            received_by_id=equipment.assigned_employee.user_id,
            returned_by_id=None,
            return_notes=OPENING_NOTE,
        )
        Movement.objects.using(database).create(
            equipment_id=equipment.pk,
            movement_type="opening",
            quantity_delta=-1,
            balance_before=1,
            balance_after=0,
            equipment_allocation_id=allocation.pk,
            idempotency_key=uuid.uuid4(),
            actor_id=None,
            employee_id=equipment.assigned_employee_id,
            notes=OPENING_NOTE,
        )


def remove_migrated_inventory_opening_balances(apps, schema_editor):
    database = schema_editor.connection.alias
    Movement = apps.get_model("dashboard", "InventoryMovement")
    Allocation = apps.get_model("dashboard", "EquipmentAllocation")
    PurchaseOrder = apps.get_model("dashboard", "PurchaseOrder")

    Movement.objects.using(database).filter(
        actor_id__isnull=True,
        movement_type="opening",
        notes=OPENING_NOTE,
    ).delete()
    Allocation.objects.using(database).filter(
        issued_by_id__isnull=True,
        request_item_id__isnull=True,
        return_notes=OPENING_NOTE,
    ).delete()
    PurchaseOrder.objects.using(database).filter(status="received").update(
        quantity_received=0
    )


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0018_equipmentallocation_request_item_and_more"),
        ("employees", "0010_supplyrequest_supplyrequestattachment_and_more"),
    ]

    operations = [
        migrations.RunPython(
            seed_inventory_opening_balances,
            remove_migrated_inventory_opening_balances,
        ),
    ]
