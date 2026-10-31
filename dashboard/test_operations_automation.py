from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse

from company_documents.models import CompanyDocument, InvoiceDocumentReview
from dashboard.models import (
    CleaningSupply,
    Equipment,
    MaintenanceHistory,
    OperationsAutomationEvent,
    PurchaseOrder,
    Supplier,
    Vehicle,
)
from employees.models import Employee, SupplyRequest
from expenses.models import Expense

from .operations_automation import run_operations_automation


class OperationsAutomationTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_superuser(
            username="operations-manager",
            email="operations@example.com",
            password="test-password",
        )
        self.employee_user = User.objects.create_user(
            username="cleaner",
            email="cleaner@example.com",
        )
        self.employee = Employee.objects.create(
            user=self.employee_user,
            full_name="Jordan Lee",
            phone="0400123456",
            email="cleaner@example.com",
        )
        self.supplier = Supplier.objects.create(name="Acme Cleaning Supplies")

    def create_due_invoice(self, *, status=Expense.PaymentStatus.UNCONFIRMED):
        document = CompanyDocument.objects.create(
            name="Acme invoice",
            category=CompanyDocument.Category.FINANCE,
            document_type="Supplier Invoice",
            related_type=CompanyDocument.RelatedType.SUPPLIER,
            supplier=self.supplier,
            file="company_documents/invoice.pdf",
            original_filename="invoice.pdf",
            uploaded_by=self.manager,
        )
        review = InvoiceDocumentReview.objects.create(
            document=document,
            status=InvoiceDocumentReview.Status.APPROVED,
            supplier=self.supplier,
        )
        return Expense.objects.create(
            invoice_review=review,
            supplier=self.supplier,
            invoice_number="AC-26-01",
            date=date(2025, 12, 1),
            due_date=date(2026, 1, 4),
            category="cleaning_supplies",
            description="Cleaning products",
            amount=Decimal("110.00"),
            gst_amount=Decimal("10.00"),
            payment_status=status,
        )

    def test_reminders_are_logged_notified_and_idempotent(self):
        as_of = date(2026, 1, 1)
        supply = CleaningSupply.objects.create(
            name="Disinfectant",
            current_stock=1,
            minimum_stock=5,
        )
        SupplyRequest.objects.create(
            employee=self.employee,
            job_location="Client site",
            reason="Restock products",
            urgency=SupplyRequest.Urgency.HIGH,
        )
        order = PurchaseOrder.objects.create(
            supply=supply,
            supplier_name=self.supplier.name,
            quantity=10,
            unit_cost=Decimal("5.00"),
            status="ordered",
            expected_delivery_date=date(2025, 12, 30),
        )
        MaintenanceHistory.objects.create(
            asset_type="equipment",
            asset_name="Floor scrubber",
            maintenance_date=date(2025, 12, 1),
            next_service_date=date(2026, 1, 10),
            description="Routine service",
        )
        Equipment.objects.create(
            name="Steam cleaner",
            next_service_date=date(2026, 1, 12),
        )
        Vehicle.objects.create(
            vehicle_name="Service van",
            registration_number="AUTO-01",
            registration_expiry=date(2026, 1, 3),
            insurance_expiry=date(2026, 1, 6),
        )
        due_invoice = self.create_due_invoice()
        self.create_due_invoice(status=Expense.PaymentStatus.PAID)

        with patch("dashboard.operations_automation.notify_admins") as notify_admins:
            with self.captureOnCommitCallbacks(execute=True):
                first = run_operations_automation(as_of=as_of)
                initial_event_count = OperationsAutomationEvent.objects.count()
                second = run_operations_automation(as_of=as_of)

        supply.refresh_from_db()
        due_invoice.refresh_from_db()
        self.assertGreater(first["events_created"], 0)
        self.assertEqual(second["events_created"], 0)
        self.assertGreater(second["duplicates_skipped"], 0)
        self.assertEqual(OperationsAutomationEvent.objects.count(), initial_event_count)
        self.assertEqual(supply.current_stock, 1)
        self.assertEqual(due_invoice.payment_status, Expense.PaymentStatus.UNCONFIRMED)
        self.assertTrue(
            OperationsAutomationEvent.objects.filter(
                metadata__purchase_order_id=order.pk
            ).exists()
        )
        self.assertTrue(
            OperationsAutomationEvent.objects.filter(
                metadata__expense_id=due_invoice.pk
            ).exists()
        )
        self.assertTrue(
            OperationsAutomationEvent.objects.filter(
                metadata__equipment_id__isnull=False
            ).exists()
        )
        self.assertTrue(
            OperationsAutomationEvent.objects.filter(
                event__contains="Monthly expense summary"
            ).exists()
        )
        self.assertEqual(notify_admins.call_count, first["events_created"] + 1)
        self.assertIn(
            reverse("operations_automation"),
            [call.args[3] for call in notify_admins.call_args_list],
        )
        self.assertIn(
            reverse("operations_automation_history"),
            [call.args[3] for call in notify_admins.call_args_list],
        )

    def test_automation_center_and_history_render_for_authorised_manager(self):
        self.client.force_login(self.manager)

        center = self.client.get(reverse("operations_automation"))
        history = self.client.get(reverse("operations_automation_history"))

        self.assertEqual(center.status_code, 200)
        self.assertContains(center, "Reorder suggestions")
        self.assertEqual(history.status_code, 200)
        self.assertContains(history, "Every trigger and outcome")

    def test_management_command_accepts_a_date_and_rejects_invalid_date(self):
        call_command(
            "run_operations_automation",
            "--as-of",
            "2026-01-01",
            stdout=None,
        )
        self.assertTrue(
            OperationsAutomationEvent.objects.filter(
                idempotency_key="automation-run:2026-01-01"
            ).exists()
        )
        with self.assertRaises(CommandError):
            call_command(
                "run_operations_automation",
                "--as-of",
                "not-a-date",
            )
