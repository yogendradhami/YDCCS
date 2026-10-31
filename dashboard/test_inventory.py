from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dashboard.forms import PurchaseOrderForm
from dashboard.models import (
    CampaignLog,
    CleaningSupply,
    EmailLog,
    Equipment,
    InventoryMovement,
    MaintenanceHistory,
    PurchaseOrder,
    Supplier,
    Vehicle,
)


class OperationsInventoryDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser(
            username="inventory-admin",
            email="inventory-admin@example.com",
            password="test-password",
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_inventory_register_and_linked_form_pages_render(self):
        paths = (
            reverse("equipment_list"),
            reverse("add_equipment"),
            reverse("supplies_list"),
            reverse("add_supply"),
            reverse("purchase_orders"),
            reverse("add_purchase_order"),
            reverse("supplier_list"),
            reverse("add_supplier"),
            reverse("vehicle_list"),
            reverse("add_vehicle"),
            reverse("maintenance_list"),
            reverse("add_maintenance"),
        )

        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_campaign_performance_distinguishes_campaign_batches_from_other_email(self):
        EmailLog.objects.create(
            sent_by=self.admin,
            email_type="system",
            recipient_name="Test recipient",
            recipient_email="recipient@example.com",
            subject="Invoice notification",
            related_object="Invoice YD-TEST",
        )

        response = self.client.get(reverse("campaign_performance"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_campaigns"], 0)
        self.assertEqual(response.context["total_emails_sent"], 0)
        self.assertEqual(response.context["general_email_log_count"], 1)
        self.assertContains(response, "No campaign batch history has been recorded yet")

        CampaignLog.objects.create(
            sent_by=self.admin,
            campaign_type="vip",
            title="VIP test send",
            recipients_count=4,
        )
        response = self.client.get(reverse("campaign_performance"))

        self.assertEqual(response.context["total_campaigns"], 1)
        self.assertEqual(response.context["total_emails_sent"], 4)
        self.assertEqual(response.context["vip_campaigns"], 1)
        self.assertNotContains(response, "No campaign batch history has been recorded yet")

    def test_supply_register_filters_stock_and_calculates_inventory_value(self):
        CleaningSupply.objects.create(
            name="Floor cleaner",
            category="Chemicals",
            current_stock=2,
            minimum_stock=5,
            unit="bottle",
            unit_cost=Decimal("8.50"),
        )
        CleaningSupply.objects.create(
            name="Gloves",
            category="PPE",
            current_stock=20,
            minimum_stock=5,
            unit="box",
            unit_cost=Decimal("4.00"),
        )

        response = self.client.get(reverse("supplies_list"), {"stock": "low"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_supplies"], 2)
        self.assertEqual(response.context["low_stock_count"], 1)
        self.assertEqual(response.context["stock_value"], Decimal("97.00"))
        self.assertEqual(
            [supply.name for supply in response.context["supplies"]],
            ["Floor cleaner"],
        )

    def test_inventory_transactions_render_movements_without_an_actor(self):
        supply = CleaningSupply.objects.create(name="Sanitiser", current_stock=2)
        InventoryMovement.objects.create(
            supply=supply,
            movement_type=InventoryMovement.MovementType.ADJUSTMENT,
            quantity_delta=1,
            balance_before=1,
            balance_after=2,
            idempotency_key="f635c4b8-bef9-4475-99d5-3d3cc2206077",
            actor=None,
        )

        response = self.client.get(reverse("inventory_transactions"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "System")

    def test_receiving_purchase_order_is_post_only_and_adds_stock_once(self):
        supply = CleaningSupply.objects.create(
            name="Disinfectant",
            current_stock=3,
            minimum_stock=2,
            unit="bottle",
        )
        order = PurchaseOrder.objects.create(
            supply=supply,
            supplier_name="Clean Supplies Co",
            quantity=5,
            unit_cost=Decimal("7.25"),
        )
        url = reverse("receive_purchase_order", args=[order.pk])
        order_list = self.client.get(reverse("purchase_orders"))
        self.assertContains(order_list, f'action="{url}"')
        self.assertContains(order_list, 'method="post"')

        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(supply.current_stock, 3)

        first_response = self.client.post(url)
        supply.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(supply.current_stock, 8)
        self.assertEqual(order.status, "received")

        self.client.post(url)
        supply.refresh_from_db()
        self.assertEqual(supply.current_stock, 8)

    def test_cancelled_order_cannot_increase_supply_stock(self):
        supply = CleaningSupply.objects.create(
            name="Paper towel",
            current_stock=4,
            minimum_stock=2,
        )
        order = PurchaseOrder.objects.create(
            supply=supply,
            supplier_name="Paper Co",
            quantity=6,
            status="cancelled",
        )

        self.client.post(reverse("receive_purchase_order", args=[order.pk]))
        supply.refresh_from_db()

        self.assertEqual(supply.current_stock, 4)

    def test_purchase_order_form_cannot_mark_an_order_received_without_receiving_stock(self):
        supply = CleaningSupply.objects.create(
            name="Glass cleaner",
            current_stock=1,
        )

        form = PurchaseOrderForm(
            data={
                "supply": supply.pk,
                "supplier_name": "Glass Supplies",
                "quantity": 3,
                "unit_cost": "5.00",
                "status": "received",
                "notes": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("status", form.errors)
        self.assertEqual(supply.current_stock, 1)

    def test_equipment_delete_requires_confirmation_then_post(self):
        equipment = Equipment.objects.create(name="Floor polisher")
        url = reverse("delete_equipment", args=[equipment.pk])

        confirmation = self.client.get(url)
        self.assertEqual(confirmation.status_code, 200)
        self.assertTrue(Equipment.objects.filter(pk=equipment.pk).exists())
        self.assertContains(confirmation, "Remove this equipment record?")

        response = self.client.post(url)
        self.assertRedirects(response, reverse("equipment_list"))
        self.assertFalse(Equipment.objects.filter(pk=equipment.pk).exists())

    def test_supplier_vehicle_and_maintenance_registers_show_real_records(self):
        today = timezone.localdate()
        Equipment.objects.create(
            name="Steam cleaner",
            next_service_date=today + timedelta(days=10),
        )
        Supplier.objects.create(name="Supply Partner", email="partner@example.com", phone="0400000000")
        Vehicle.objects.create(
            vehicle_name="Service van",
            registration_number="TEST-001",
            insurance_expiry=today + timedelta(days=10),
        )
        MaintenanceHistory.objects.create(
            asset_type="vehicle",
            asset_name="Service van",
            maintenance_date=date(2026, 1, 15),
            cost=Decimal("125.00"),
            description="Scheduled service",
        )

        suppliers = self.client.get(reverse("supplier_list"))
        equipment = self.client.get(reverse("equipment_list"))
        vehicles = self.client.get(reverse("vehicle_list"))
        maintenance = self.client.get(reverse("maintenance_list"))

        self.assertContains(suppliers, "Supply Partner")
        self.assertContains(equipment, "Steam cleaner")
        self.assertContains(equipment, "Due soon")
        self.assertContains(vehicles, "Service van")
        self.assertEqual(vehicles.context["vehicle_alerts"], 1)
        self.assertContains(maintenance, "Scheduled service")
        self.assertEqual(maintenance.context["maintenance_cost"], Decimal("125.00"))
