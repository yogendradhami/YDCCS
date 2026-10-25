from django.db import transaction

from bookings.models import Booking

from .models import Invoice


def get_or_create_invoice_for_booking(booking):
    """Return the first invoice for a booking, creating a draft if needed."""
    with transaction.atomic():
        locked_booking = Booking.objects.select_for_update().get(pk=booking.pk)
        invoice = (
            Invoice.objects.filter(booking=locked_booking)
            .order_by("pk")
            .first()
        )
        if invoice:
            return invoice, False

        invoice = Invoice.objects.create(
            booking=locked_booking,
            description=(
                f"{locked_booking.service_type} completed on "
                f"{locked_booking.booking_date}"
            ),
            amount=locked_booking.quoted_price,
            status="draft",
            notes=locked_booking.notes,
        )
        return invoice, True
