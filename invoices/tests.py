from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from bookings.models import Booking
from core.test_utils import grant_dashboard_permissions
from customers.models import Customer
from .models import Invoice
from .services import get_or_create_invoice_for_booking


class ManualInvoiceEmailTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            full_name="Invoice Recipient",
            email="recipient@example.com",
            phone="0400000000",
        )
        self.booking = Booking.objects.create(
            customer=self.customer,
            service_type="Office Cleaning",
            booking_date=date.today() + timedelta(days=1),
            booking_time=time(10, 0),
            address="1 King Street",
            suburb_postcode="Adelaide 5000",
            quoted_price="250.00",
        )
        user = get_user_model().objects.create_user(
            username="manual-invoice-admin",
            password="test-password",
            is_staff=True,
        )
        grant_dashboard_permissions(user, "invoices.add_invoice")
        self.client.force_login(user)
        self.form_data = {
            "booking": self.booking.pk,
            "issue_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
            "description": "Office cleaning",
            "amount": "250.00",
            "status": "draft",
            "notes": "",
        }

    @patch("dashboard.views.send_invoice_email", return_value=True)
    def test_manual_invoice_is_emailed_after_creation(self, send_invoice_email):
        response = self.client.post(reverse("create_invoice"), self.form_data)

        self.assertEqual(response.status_code, 302, response.content[:500])
        invoice = Invoice.objects.get()
        self.assertRedirects(
            response,
            reverse("invoice_detail", args=[invoice.pk]),
            fetch_redirect_response=False,
        )
        send_invoice_email.assert_called_once_with(response.wsgi_request, invoice)
        self.assertEqual(invoice.booking_id, self.booking.pk)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(
            any("created and emailed" in message.message for message in messages)
        )

    @patch("dashboard.views.send_invoice_email", return_value=False)
    def test_failed_email_reports_invoice_was_created(self, send_invoice_email):
        response = self.client.post(reverse("create_invoice"), self.form_data)

        self.assertEqual(response.status_code, 302, response.content[:500])
        self.assertEqual(Invoice.objects.count(), 1)
        send_invoice_email.assert_called_once()
        messages = list(response.wsgi_request._messages)
        self.assertTrue(
            any("could not be sent" in message.message for message in messages)
        )


class InvoiceBookingServiceTests(TestCase):
    def test_invoice_detail_formats_currency_to_two_decimal_places(self):
        booking = Booking.objects.create(
            service_type="Office Cleaning",
            booking_date=date.today() + timedelta(days=1),
            booking_time=time(10, 0),
            address="1 King Street",
            suburb_postcode="Adelaide 5000",
            quoted_price="100.00",
        )
        invoice = Invoice.objects.create(booking=booking, amount=Decimal("100.00"))
        user = get_user_model().objects.create_user(
            username="invoice-detail-admin",
            password="test-password",
            is_staff=True,
        )
        grant_dashboard_permissions(user, "invoices.view_invoice")
        self.client.force_login(user)

        response = self.client.get(
            reverse("invoice_detail", args=[invoice.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "$110.00")
        self.assertNotContains(response, "$110.0000")

    def test_invoice_creation_is_idempotent_for_a_booking(self):
        booking = Booking.objects.create(
            service_type="Office Cleaning",
            booking_date=date.today() + timedelta(days=1),
            booking_time=time(10, 0),
            address="1 King Street",
            suburb_postcode="Adelaide 5000",
            quoted_price="250.00",
        )

        first, created = get_or_create_invoice_for_booking(booking)
        second, second_created = get_or_create_invoice_for_booking(booking)

        self.assertTrue(created)
        self.assertFalse(second_created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.booking_id, booking.pk)
        self.assertEqual(first.invoice_number, "YD-00001")
        self.assertEqual(first.amount, Decimal("250.00"))
        self.assertEqual(first.status, "draft")
        self.assertEqual(Invoice.objects.count(), 1)

    def test_invoice_for_booking_without_customer_can_be_deleted(self):
        booking = Booking.objects.create(
            service_type="Office Cleaning",
            booking_date=date.today() + timedelta(days=1),
            booking_time=time(10, 0),
            address="1 King Street",
            suburb_postcode="Adelaide 5000",
            quoted_price="250.00",
        )
        invoice = Invoice.objects.create(booking=booking)
        additional_invoice = Invoice.objects.create(booking=booking)
        admin = get_user_model().objects.create_user(
            username="invoice-admin",
            password="test-password",
            is_staff=True,
        )
        grant_dashboard_permissions(admin, "invoices.delete_invoice")
        self.client.force_login(admin)

        response = self.client.post(reverse("delete_invoice", args=[invoice.pk]))

        self.assertRedirects(
            response,
            reverse("invoice_list"),
            fetch_redirect_response=False,
        )
        self.assertFalse(Invoice.objects.filter(pk=invoice.pk).exists())
        self.assertFalse(Invoice.objects.filter(pk=additional_invoice.pk).exists())
        self.assertFalse(Booking.objects.filter(pk=booking.pk).exists())

    def test_invoice_list_renders_kpis_from_stats_context(self):
        booking = Booking.objects.create(
            service_type="Office Cleaning",
            booking_date=date.today() + timedelta(days=1),
            booking_time=time(10, 0),
            address="1 King Street",
            suburb_postcode="Adelaide 5000",
            quoted_price="100.00",
        )
        Invoice.objects.create(booking=booking, amount=Decimal("100.00"), status="paid")
        Invoice.objects.create(booking=booking, amount=Decimal("100.00"), status="sent")
        admin = get_user_model().objects.create_user(
            username="invoice-list-admin",
            password="test-password",
            is_staff=True,
        )
        grant_dashboard_permissions(admin, "invoices.view_invoice")
        self.client.force_login(admin)

        response = self.client.get(reverse("invoice_list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["invoices"].count(), 2)
        self.assertEqual(response.context["stats"]["total_invoiced"], Decimal("220.000"))
        self.assertEqual(response.context["stats"]["paid_total"], Decimal("110.000"))
        self.assertEqual(response.context["stats"]["outstanding_total"], Decimal("110.000"))
        self.assertEqual(response.context["stats"]["invoice_count"], 2)
        self.assertEqual(response.context["stats"]["paid_count"], 1)
        self.assertContains(response, "$220.00")
        self.assertContains(response, "$110.00")
