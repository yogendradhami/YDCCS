from datetime import date, time
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking
from customers.models import Customer
from invoices.models import Invoice

from .models import Expense


class FinancePageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="finance-admin",
            email="finance-admin@example.com",
            password="test-password",
        )
        self.client.force_login(self.user)
        today = timezone.localdate()
        customer = Customer.objects.create(
            full_name="Finance Test Customer",
            email="finance-customer@example.com",
            phone="0400000000",
        )
        booking = Booking.objects.create(
            customer=customer,
            service_type="Office Cleaning",
            booking_date=today,
            booking_time=time(10, 0),
            address="1 King Street",
            suburb_postcode="Prospect 5082",
            quoted_price=Decimal("100.00"),
        )
        self.invoice = Invoice.objects.create(
            booking=booking,
            amount=Decimal("110.00"),
            status="paid",
            paid_at=timezone.now(),
        )
        self.expense = Expense.objects.create(
            date=today,
            category="fuel",
            description="Van fuel",
            amount=Decimal("110.00"),
            paid_by=self.user,
        )

    def test_finance_pages_render_with_shared_navigation(self):
        routes = (
            "financial_dashboard",
            "expense_list",
            "profit_loss_dashboard",
            "gst_report",
            "finance_trends",
            "job_profitability_dashboard",
        )
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Finance navigation")

    def test_profit_and_gst_reports_use_selected_year_and_recorded_invoice_gst(self):
        current_year = timezone.localdate().year
        profit_response = self.client.get(
            reverse("profit_loss_dashboard"),
            {"year": current_year},
        )
        gst_response = self.client.get(reverse("gst_report"), {"year": current_year})

        self.assertEqual(profit_response.status_code, 200)
        self.assertEqual(gst_response.status_code, 200)
        self.assertEqual(
            profit_response.context["paid_revenue"],
            self.invoice.total_amount,
        )
        self.assertEqual(
            profit_response.context["expense_cost"],
            self.expense.amount,
        )
        self.assertEqual(
            gst_response.context["gst_collected"],
            self.invoice.gst_amount,
        )
        self.assertEqual(gst_response.context["gst_paid"], Decimal("10.00"))

    def test_expense_search_and_category_filters_apply_and_invalid_date_is_explained(self):
        matching = self.client.get(
            reverse("expense_list"),
            {"q": "van", "category": "fuel"},
        )
        self.assertEqual(matching.status_code, 200)
        self.assertContains(matching, "Van fuel")
        self.assertEqual(matching.context["filtered_total"], self.expense.amount)

        invalid_range = self.client.get(
            reverse("expense_list"),
            {"date_from": "2026-10-31", "date_to": "2026-10-01"},
        )
        self.assertContains(invalid_range, "The start date must be on or before the end date.")

    def test_expense_add_edit_and_delete_pages_render(self):
        self.assertEqual(self.client.get(reverse("add_expense")).status_code, 200)
        self.assertEqual(
            self.client.get(
                reverse("edit_expense", args=[self.expense.pk])
            ).status_code,
            200,
        )
        delete_response = self.client.get(
            reverse("delete_expense", args=[self.expense.pk])
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertContains(delete_response, "Delete expense")
