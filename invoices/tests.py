from datetime import date, time, timedelta
from decimal import Decimal

from django.test import TestCase

from bookings.models import Booking
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
        self.assertEqual(first.amount, Decimal("250.00"))
        self.assertEqual(first.status, "draft")
        self.assertEqual(Invoice.objects.count(), 1)
