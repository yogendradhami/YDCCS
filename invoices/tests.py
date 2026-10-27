from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from bookings.models import Booking
from core.test_utils import grant_dashboard_permissions
from .models import Invoice
from .services import get_or_create_invoice_for_booking


class InvoiceBookingServiceTests(TestCase):
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
