from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from analytics.models import ActivityEvent, Visitor, VisitorSession
from bookings.models import Booking
from customers.models import Customer
from expenses.models import Expense
from invoices.models import Invoice
from payroll.models import PayrollRecord
from quotes.models import QuoteRequest


class BusinessDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser(
            username="business-dashboard-admin",
            email="business-dashboard@example.com",
            password="test-password",
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_requested_business_dashboard_pages_render_with_empty_data(self):
        route_names = (
            "business_health",
            "analytics:dashboard",
            "business_kpis",
            "business_intelligence",
            "job_profitability_dashboard",
            "executive_bi_dashboard",
            "service_performance_dashboard",
            "ai_quote_estimator",
            "quote_conversion_analytics",
            "quote_followup_centre",
            "owner_command_centre",
            "owner_alert_centre",
            "executive_dashboard",
            "business_forecasting_centre",
            "operations_command_centre",
        )

        for route_name in route_names:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)

    def test_executive_bi_renders_each_chart_once_without_contracts(self):
        response = self.client.get(reverse("executive_bi_dashboard"))

        self.assertEqual(response.status_code, 200)
        for canvas_id in (
            "monthlyRevenueChart",
            "monthlyBookingChart",
            "customerGrowthChart",
            "serviceRevenueChart",
            "contractRevenueChart",
        ):
            with self.subTest(canvas_id=canvas_id):
                self.assertContains(response, f'id="{canvas_id}"', count=1)
        self.assertEqual(response.context["contract_revenue_values"], [])

    def test_business_intelligence_reports_all_unpaid_and_overdue_invoice_balances(self):
        booking = Booking.objects.create(
            service_type="Office Cleaning",
            booking_date=date.today() + timedelta(days=1),
            booking_time=time(10, 0),
            address="1 Example Street",
            suburb_postcode="Adelaide 5000",
            quoted_price=Decimal("100.00"),
        )
        Invoice.objects.create(
            booking=booking,
            amount=Decimal("100.00"),
            status="draft",
        )
        Invoice.objects.create(
            booking=booking,
            amount=Decimal("200.00"),
            status="sent",
        )
        Invoice.objects.create(
            booking=booking,
            amount=Decimal("300.00"),
            status="overdue",
        )
        Invoice.objects.create(
            booking=booking,
            amount=Decimal("400.00"),
            status="paid",
        )
        Invoice.objects.create(
            booking=booking,
            amount=Decimal("500.00"),
            status="cancelled",
        )

        response = self.client.get(reverse("business_intelligence"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["monthly_growth"], 0)
        self.assertEqual(
            response.context["outstanding_invoice_balance"],
            Decimal("660.00"),
        )
        self.assertEqual(response.context["outstanding_invoice_count"], 3)
        self.assertEqual(
            response.context["overdue_invoice_balance"],
            Decimal("330.00"),
        )
        self.assertEqual(response.context["overdue_invoice_count"], 1)
        self.assertContains(response, "$660.00")
        self.assertContains(response, "$330.00")
        self.assertContains(response, "3 unpaid invoices")
        self.assertContains(response, "0.0%")

    def test_business_intelligence_customer_table_includes_booking_count(self):
        customer = Customer.objects.create(
            full_name="BI Customer",
            email="bi-customer@example.com",
            phone="0400000000",
        )
        Booking.objects.create(
            customer=customer,
            service_type="Office Cleaning",
            booking_date=timezone.localdate(),
            booking_time=time(10, 0),
            address="1 Example Street",
            suburb_postcode="Adelaide 5000",
            quoted_price=Decimal("100.00"),
            status="completed",
        )
        Booking.objects.create(
            customer=customer,
            service_type="Office Cleaning",
            booking_date=timezone.localdate() + timedelta(days=1),
            booking_time=time(10, 0),
            address="1 Example Street",
            suburb_postcode="Adelaide 5000",
            quoted_price=Decimal("100.00"),
        )
        customer.total_revenue = Decimal("200.00")
        customer.save(update_fields=["total_revenue"])

        response = self.client.get(reverse("business_intelligence"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["top_revenue_customers"][0].booking_count,
            2,
        )
        self.assertEqual(response.context["average_job_value"], Decimal("100.00"))
        self.assertContains(response, "2</td>")

    def test_business_intelligence_compares_adjacent_calendar_months(self):
        booking = Booking.objects.create(
            service_type="Office Cleaning",
            booking_date=date.today() + timedelta(days=1),
            booking_time=time(10, 0),
            address="1 Example Street",
            suburb_postcode="Adelaide 5000",
            quoted_price=Decimal("100.00"),
        )
        current_paid_at = timezone.now()
        previous_paid_at = (
            timezone.localtime(current_paid_at)
            .replace(day=1, hour=12, minute=0, second=0, microsecond=0)
            - timedelta(days=1)
        )
        Invoice.objects.create(
            booking=booking,
            amount=Decimal("200.00"),
            status="paid",
            paid_at=previous_paid_at,
        )
        Invoice.objects.create(
            booking=booking,
            amount=Decimal("100.00"),
            status="paid",
            paid_at=current_paid_at,
        )

        response = self.client.get(reverse("business_intelligence"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["monthly_revenue"], Decimal("110.000"))
        self.assertEqual(response.context["monthly_growth"], Decimal("-50.00"))

    def test_quote_estimator_validates_input_and_displays_history_basis(self):
        invalid_response = self.client.post(
            reverse("ai_quote_estimator"),
            {
                "bedrooms": "-1",
                "bathrooms": "1",
                "property_type": "unit",
            },
        )
        self.assertEqual(invalid_response.status_code, 200)
        self.assertIsNone(invalid_response.context["estimated_price"])
        self.assertIn("bedrooms", invalid_response.context["form"].errors)

        valid_response = self.client.post(
            reverse("ai_quote_estimator"),
            {
                "bedrooms": "2",
                "bathrooms": "1",
                "property_type": "unit",
            },
        )
        self.assertEqual(valid_response.status_code, 200)
        self.assertEqual(valid_response.context["estimated_price"], 305)
        self.assertEqual(valid_response.context["confidence_level"], "No history")
        self.assertContains(valid_response, "starter baseline")

    def test_quote_conversion_uses_real_statuses_and_followups_use_post(self):
        quote = QuoteRequest.objects.create(
            name="Alex Customer",
            email="alex@example.com",
            phone="0400000000",
            property_type="House",
            suburb_postcode="Adelaide 5000",
            estimated_price="500.00",
            status="completed",
        )

        analytics_response = self.client.get(reverse("quote_conversion_analytics"))
        self.assertEqual(analytics_response.status_code, 200)
        self.assertEqual(analytics_response.context["booked_quotes"], 1)
        self.assertEqual(analytics_response.context["conversion_rate"], 100)

        quote.status = "quoted"
        quote.save(update_fields=["status"])
        QuoteRequest.objects.filter(pk=quote.pk).update(
            created_at=timezone.now() - timedelta(days=3)
        )
        followup_response = self.client.get(reverse("quote_followup_centre"))
        self.assertEqual(followup_response.status_code, 200)
        self.assertContains(followup_response, 'method="post"')
        self.assertContains(
            followup_response,
            reverse("send_quote_followup_email", args=[quote.pk]),
        )
        self.assertContains(
            followup_response,
            reverse("convert_quote_to_booking", args=[quote.pk]),
        )

    def test_service_performance_shows_completed_booking_breakdown(self):
        Booking.objects.create(
            service_type="Office Cleaning",
            booking_date=date(2026, 5, 5),
            booking_time=time(9, 0),
            address="10 Example Street",
            suburb_postcode="Adelaide 5000",
            quoted_price=Decimal("420.00"),
            status="completed",
        )

        response = self.client.get(reverse("service_performance_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Office Cleaning")
        self.assertContains(response, "$420.00")
        self.assertEqual(response.context["total_completed_jobs"], 1)

    def test_forecast_normalizes_decimal_and_float_currency_aggregates(self):
        with (
            patch.object(Invoice.objects, "filter") as invoice_filter,
            patch.object(Expense.objects, "filter") as expense_filter,
            patch.object(PayrollRecord.objects, "filter") as payroll_filter,
        ):
            invoice_filter.return_value.aggregate.return_value = {
                "total": Decimal("1000.00")
            }
            expense_filter.return_value.aggregate.return_value = {"total": 125.5}
            payroll_filter.return_value.aggregate.return_value = {
                "total": Decimal("100.00")
            }
            response = self.client.get(reverse("business_forecasting_centre"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["current_revenue"], Decimal("1000.00"))
        self.assertEqual(response.context["current_expenses"], Decimal("125.5"))
        self.assertEqual(response.context["current_payroll"], Decimal("100.00"))
        self.assertEqual(response.context["current_profit"], Decimal("774.50"))
        self.assertEqual(response.context["expense_chart"][0], 225.5)

    def test_website_analytics_shows_period_trend_sources_and_unique_conversion(self):
        visitor = Visitor.objects.create(
            device_type="Mobile",
            browser="Safari",
            operating_system="iOS",
        )
        session = VisitorSession.objects.create(
            visitor=visitor,
            landing_page="/",
            utm_source="spring-campaign",
            referrer="http://[malformed",
        )
        for event_type, page_url in (
            ("PAGE_VIEW", "/"),
            ("PAGE_VIEW", "/services/"),
            ("QUOTE_START", "/quote/"),
            ("QUOTE_SUBMIT", "/quote/"),
            ("QUOTE_SUBMIT", "/quote/"),
        ):
            ActivityEvent.objects.create(
                visitor=visitor,
                session=session,
                event_type=event_type,
                page_url=page_url,
            )
        ActivityEvent.objects.create(
            visitor=visitor,
            session=session,
            event_type="PAGE_VIEW",
            page_url="/analytics/dashboard/",
        )

        response = self.client.get(
            reverse("analytics:dashboard"),
            {"period": "7days"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["visitors_period"], 1)
        self.assertEqual(response.context["page_views_period"], 2)
        self.assertEqual(response.context["quote_visitor_rate"], 100)
        self.assertEqual(response.context["visitors_with_quote_submission"], 1)
        self.assertEqual(len(response.context["traffic_trend"]), 7)
        self.assertEqual(response.context["traffic_trend"][-1]["total"], 2)
        self.assertEqual(response.context["traffic_sources"][0]["source"], "spring-campaign")
        self.assertContains(response, "Daily page views")
        self.assertContains(response, "Review quote leads")
