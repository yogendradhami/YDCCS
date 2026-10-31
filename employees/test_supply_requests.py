import json
import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from dashboard.inventory_services import receive_purchase_order_goods
from dashboard.models import (
    CleaningSupply,
    Equipment,
    EquipmentAllocation,
    GoodsReceipt,
    InventoryMovement,
    PurchaseOrder,
)
from dashboard.inventory_services import record_opening_supply_stock
from notifications.models import Notification
from core.test_utils import grant_dashboard_permissions
from induction.models import EmployeeInduction, InductionProgramme

from .models import Employee, SupplyRequest, SupplyRequestItem
from .supply_services import (
    approve_supply_request,
    issue_supply_request,
    reject_supply_request,
    return_equipment_allocation,
)


class EmployeeSupplyRequestTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.employee_user = user_model.objects.create_user(
            username="supply-employee",
            password="test-pass",
        )
        cls.employee = Employee.objects.create(
            user=cls.employee_user,
            full_name="Supply Employee",
            phone="0400000000",
        )
        cls.other_user = user_model.objects.create_user(
            username="other-employee",
            password="test-pass",
        )
        cls.other_employee = Employee.objects.create(
            user=cls.other_user,
            full_name="Other Employee",
            phone="0400000001",
        )
        cls.manager = user_model.objects.create_user(
            username="supply-manager",
            password="test-pass",
            is_staff=True,
        )
        grant_dashboard_permissions(
            cls.manager,
            "employees.manage_supply_requests",
        )
        programme = InductionProgramme.objects.create(
            name="Supply request test induction"
        )
        for employee in (cls.employee, cls.other_employee):
            EmployeeInduction.objects.create(
                employee=employee,
                programme=programme,
                status="completed",
            )
    def setUp(self):
        self.supply = CleaningSupply.objects.create(
            name="Neutral cleaner",
            current_stock=0,
            minimum_stock=2,
            unit="bottle",
        )
        record_opening_supply_stock(
            supply_id=self.supply.pk,
            quantity=10,
            actor=self.manager,
        )
        self.supply.refresh_from_db()

    def create_request(self, *, quantity=5, asset=None, employee=None):
        request_record = SupplyRequest.objects.create(
            employee=employee or self.employee,
            job_location="Customer site, Sydney",
            reason="Restock for scheduled cleaning",
            urgency=SupplyRequest.Urgency.NORMAL,
        )
        if asset is None:
            asset = self.supply
        item = SupplyRequestItem.objects.create(
            request=request_record,
            supply=asset if isinstance(asset, CleaningSupply) else None,
            equipment=asset if isinstance(asset, Equipment) else None,
            requested_quantity=quantity,
            unit=asset.unit if isinstance(asset, CleaningSupply) else "unit",
        )
        return request_record, item

    def test_employee_can_submit_multiple_item_request_and_managers_are_notified(self):
        second_supply = CleaningSupply.objects.create(name="Microfibre cloths")
        self.client.force_login(self.employee_user)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("employee_supply_requests"),
                {
                    "idempotency_key": uuid.uuid4(),
                    "job_location": "Customer site, Sydney",
                    "reason": "Prepare for a deep clean",
                    "urgency": "high",
                    "request_items": json.dumps(
                        [
                            {"kind": "supply", "id": self.supply.pk, "quantity": 3},
                            {"kind": "supply", "id": second_supply.pk, "quantity": 2},
                        ]
                    ),
                },
            )

        self.assertRedirects(response, reverse("employee_supply_requests"))
        request_record = SupplyRequest.objects.get(employee=self.employee)
        self.assertEqual(request_record.items.count(), 2)
        self.assertEqual(request_record.status, SupplyRequest.Status.PENDING)
        self.supply.refresh_from_db()
        self.assertEqual(self.supply.current_stock, 10)
        self.assertTrue(
            Notification.objects.filter(
                user=self.manager,
                title__contains=f"#{request_record.pk}",
            ).exists()
        )

    def test_submission_is_idempotent_for_replayed_form_token(self):
        token = uuid.uuid4()
        payload = {
            "idempotency_key": token,
            "job_location": "Customer site",
            "reason": "Need supplies",
            "urgency": "normal",
            "request_items": json.dumps(
                [{"kind": "supply", "id": self.supply.pk, "quantity": 2}]
            ),
        }
        self.client.force_login(self.employee_user)

        self.client.post(reverse("employee_supply_requests"), payload)
        self.client.post(reverse("employee_supply_requests"), payload)

        self.assertEqual(SupplyRequest.objects.filter(employee=self.employee).count(), 1)

    def test_employee_history_only_shows_their_own_requests(self):
        self.create_request()
        other_request, _ = self.create_request(employee=self.other_employee)
        self.client.force_login(self.employee_user)

        response = self.client.get(reverse("employee_supply_requests"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["requests"].values_list("pk", flat=True)),
            [SupplyRequest.objects.get(employee=self.employee).pk],
        )
        self.assertNotContains(response, f"Request #{other_request.pk}")

    def test_employee_cannot_access_manager_request_management(self):
        self.client.force_login(self.employee_user)

        response = self.client.get(reverse("supply_request_management"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("employee_dashboard"))

    def test_manager_can_approve_without_deducting_inventory(self):
        request_record, item = self.create_request(quantity=4)
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse("supply_request_approve", args=[request_record.pk]),
            {f"quantity_{item.pk}": 4, "comments": ""},
        )

        request_record.refresh_from_db()
        self.supply.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(request_record.status, SupplyRequest.Status.APPROVED)
        self.assertEqual(self.supply.current_stock, 10)
        self.assertFalse(
            InventoryMovement.objects.filter(
                request_item=item,
                movement_type=InventoryMovement.MovementType.ISSUE,
            ).exists()
        )

    def test_manager_can_partially_approve_with_reason(self):
        request_record, item = self.create_request(quantity=5)

        approve_supply_request(
            request_id=request_record.pk,
            actor=self.manager,
            quantities={item.pk: 2},
            comments="Only two are available for this job.",
        )

        request_record.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(request_record.status, SupplyRequest.Status.PARTIALLY_APPROVED)
        self.assertEqual(item.approved_quantity, 2)
        self.assertEqual(self.supply.current_stock, 10)

    def test_manager_rejection_requires_and_records_reason(self):
        request_record, _ = self.create_request()

        reject_supply_request(
            request_id=request_record.pk,
            actor=self.manager,
            comments="This item is not needed for this location.",
        )

        request_record.refresh_from_db()
        self.assertEqual(request_record.status, SupplyRequest.Status.REJECTED)
        self.assertEqual(
            request_record.decision_comments,
            "This item is not needed for this location.",
        )

    def test_partial_and_full_handover_keep_stock_and_ledger_in_sync(self):
        request_record, item = self.create_request(quantity=5)
        approve_supply_request(
            request_id=request_record.pk,
            actor=self.manager,
            quantities={item.pk: 5},
        )
        first_key = uuid.uuid4()

        request_record, first_issued = issue_supply_request(
            request_id=request_record.pk,
            actor=self.manager,
            quantities={item.pk: 2},
            idempotency_key=first_key,
        )
        item.refresh_from_db()
        self.supply.refresh_from_db()
        self.assertTrue(first_issued)
        self.assertEqual(request_record.status, SupplyRequest.Status.PARTIALLY_ISSUED)
        self.assertEqual(item.issued_quantity, 2)
        self.assertEqual(self.supply.current_stock, 8)

        issue_supply_request(
            request_id=request_record.pk,
            actor=self.manager,
            quantities={item.pk: 3},
            idempotency_key=uuid.uuid4(),
        )
        item.refresh_from_db()
        request_record.refresh_from_db()
        self.supply.refresh_from_db()
        self.assertEqual(item.issued_quantity, 5)
        self.assertEqual(request_record.status, SupplyRequest.Status.ISSUED)
        self.assertEqual(self.supply.current_stock, 5)
        self.assertEqual(
            sum(
                InventoryMovement.objects.filter(supply=self.supply).values_list(
                    "quantity_delta", flat=True
                )
            ),
            self.supply.current_stock,
        )

    def test_insufficient_stock_prevents_handover_without_partial_mutation(self):
        request_record, item = self.create_request(quantity=12)
        approve_supply_request(
            request_id=request_record.pk,
            actor=self.manager,
            quantities={item.pk: 12},
        )

        with self.assertRaises(ValidationError):
            issue_supply_request(
                request_id=request_record.pk,
                actor=self.manager,
                quantities={item.pk: 12},
                idempotency_key=uuid.uuid4(),
            )

        item.refresh_from_db()
        self.supply.refresh_from_db()
        self.assertEqual(item.issued_quantity, 0)
        self.assertEqual(self.supply.current_stock, 10)
        self.assertFalse(
            InventoryMovement.objects.filter(
                request_item=item,
                movement_type=InventoryMovement.MovementType.ISSUE,
            ).exists()
        )

    def test_replayed_issue_token_cannot_deduct_stock_twice(self):
        request_record, item = self.create_request(quantity=4)
        approve_supply_request(
            request_id=request_record.pk,
            actor=self.manager,
            quantities={item.pk: 4},
        )
        key = uuid.uuid4()
        issue_supply_request(
            request_id=request_record.pk,
            actor=self.manager,
            quantities={item.pk: 4},
            idempotency_key=key,
        )

        with self.assertRaises(ValidationError):
            issue_supply_request(
                request_id=request_record.pk,
                actor=self.manager,
                quantities={item.pk: 4},
                idempotency_key=key,
            )

        self.supply.refresh_from_db()
        self.assertEqual(self.supply.current_stock, 6)
        self.assertEqual(
            InventoryMovement.objects.filter(
                request_item=item,
                movement_type=InventoryMovement.MovementType.ISSUE,
            ).count(),
            1,
        )

    def test_equipment_handover_records_issuer_receiver_and_return(self):
        equipment = Equipment.objects.create(name="Commercial vacuum")
        request_record, item = self.create_request(
            quantity=1,
            asset=equipment,
        )
        approve_supply_request(
            request_id=request_record.pk,
            actor=self.manager,
            quantities={item.pk: 1},
        )
        issue_supply_request(
            request_id=request_record.pk,
            actor=self.manager,
            quantities={item.pk: 1},
            idempotency_key=uuid.uuid4(),
        )
        allocation = EquipmentAllocation.objects.get(equipment=equipment)
        self.assertEqual(allocation.issued_by, self.manager)
        self.assertEqual(allocation.received_by, self.employee_user)
        self.assertEqual(equipment.__class__.objects.get(pk=equipment.pk).assigned_employee, self.employee)

        return_equipment_allocation(
            allocation_id=allocation.pk,
            actor=self.manager,
            notes="Returned in good condition.",
        )

        allocation.refresh_from_db()
        equipment.refresh_from_db()
        self.assertIsNotNone(allocation.returned_at)
        self.assertEqual(allocation.returned_by, self.manager)
        self.assertIsNone(equipment.assigned_employee_id)
        self.assertEqual(
            InventoryMovement.objects.filter(
                equipment=equipment,
                movement_type=InventoryMovement.MovementType.RETURN,
            ).count(),
            1,
        )

    def test_partial_goods_receipt_updates_stock_only_after_confirmation(self):
        order = PurchaseOrder.objects.create(
            supply=self.supply,
            supplier_name="Supply partner",
            quantity=5,
        )
        key = uuid.uuid4()

        receipt, created = receive_purchase_order_goods(
            order_id=order.pk,
            quantity=2,
            actor=self.manager,
            idempotency_key=key,
            notes="First delivery",
        )
        self.assertTrue(created)
        repeated_receipt, created_again = receive_purchase_order_goods(
            order_id=order.pk,
            quantity=2,
            actor=self.manager,
            idempotency_key=key,
            notes="Replayed submission",
        )
        self.assertFalse(created_again)
        self.assertEqual(receipt.pk, repeated_receipt.pk)
        self.supply.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.supply.current_stock, 12)
        self.assertEqual(order.quantity_received, 2)
        self.assertEqual(order.status, "ordered")
        self.assertEqual(GoodsReceipt.objects.count(), 1)

        receive_purchase_order_goods(
            order_id=order.pk,
            quantity=3,
            actor=self.manager,
            idempotency_key=uuid.uuid4(),
            notes="Balance received",
        )
        self.supply.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.supply.current_stock, 15)
        self.assertEqual(order.quantity_received, 5)
        self.assertEqual(order.status, "received")

    def test_goods_receipt_cannot_exceed_open_purchase_order_quantity(self):
        order = PurchaseOrder.objects.create(
            supply=self.supply,
            supplier_name="Supply partner",
            quantity=2,
        )

        with self.assertRaises(ValidationError):
            receive_purchase_order_goods(
                order_id=order.pk,
                quantity=3,
                actor=self.manager,
                idempotency_key=uuid.uuid4(),
            )

        self.supply.refresh_from_db()
        self.assertEqual(self.supply.current_stock, 10)
        self.assertEqual(GoodsReceipt.objects.count(), 0)

    def test_attachment_upload_is_signature_checked_and_only_owner_can_download(self):
        self.client.force_login(self.employee_user)
        response = self.client.post(
            reverse("employee_supply_requests"),
            {
                "idempotency_key": uuid.uuid4(),
                "job_location": "Customer site",
                "reason": "Explain product requirement",
                "urgency": "normal",
                "request_items": json.dumps(
                    [{"kind": "supply", "id": self.supply.pk, "quantity": 1}]
                ),
                "attachments": SimpleUploadedFile(
                    "purchase.pdf",
                    b"%PDF-1.4 test supporting document",
                    content_type="application/pdf",
                ),
            },
        )

        self.assertEqual(response.status_code, 302)
        attachment = SupplyRequest.objects.get(employee=self.employee).attachments.get()
        self.assertEqual(
            self.client.get(
                reverse("employee_supply_request_attachment", args=[attachment.pk])
            ).status_code,
            200,
        )
        self.client.force_login(self.other_user)
        self.assertEqual(
            self.client.get(
                reverse("employee_supply_request_attachment", args=[attachment.pk])
            ).status_code,
            404,
        )

    def test_manager_request_pages_render_with_permission(self):
        request_record, _ = self.create_request()
        self.client.force_login(self.manager)

        self.assertEqual(
            self.client.get(reverse("supply_request_management")).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse("supply_request_detail", args=[request_record.pk])
            ).status_code,
            200,
        )
