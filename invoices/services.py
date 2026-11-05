from django.db import transaction
from decimal import Decimal

from bookings.models import Booking, BookingWorkOrder

from .models import Invoice, InvoiceWorkOrder


def get_booking_work_order_initial(booking):
    work_orders = list(booking.work_orders.all())
    if work_orders:
        return [
            {"description": item.service_type, "price": item.price}
            for item in work_orders
        ]
    return [
        {
            "description": booking.service_type,
            "price": booking.quoted_price,
        }
    ]


def create_booking_for_invoice(source_booking, work_orders, quoted_price):
    """Create a distinct job using the selected booking's scheduling details."""
    booking = Booking.objects.create(
        customer=source_booking.customer,
        service_type=source_booking.service_type,
        booking_date=source_booking.booking_date,
        booking_time=source_booking.booking_time,
        address=source_booking.address,
        suburb_postcode=source_booking.suburb_postcode,
        quoted_price=quoted_price,
        assigned_employee=source_booking.assigned_employee,
        status="pending",
        notes=source_booking.notes,
    )
    BookingWorkOrder.objects.bulk_create(
        [
            BookingWorkOrder(
                booking=booking,
                service_type=item["description"],
                price=Decimal(str(item["price"])),
                position=position,
            )
            for position, item in enumerate(work_orders)
        ]
    )
    return booking


def replace_invoice_work_orders(invoice, work_orders):
    normalized_work_orders = list(work_orders)
    if not normalized_work_orders:
        raise ValueError("At least one invoice work order is required.")

    invoice.work_orders.all().delete()
    InvoiceWorkOrder.objects.bulk_create(
        [
            InvoiceWorkOrder(
                invoice=invoice,
                description=item["description"],
                price=Decimal(str(item["price"])),
                position=position,
            )
            for position, item in enumerate(normalized_work_orders)
        ]
    )
    invoice.amount = sum(
        (Decimal(str(item["price"])) for item in normalized_work_orders),
        Decimal("0.00"),
    )
    invoice.save()
    return invoice


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

        booking_work_orders = list(locked_booking.work_orders.all())
        amount = (
            sum((item.price for item in booking_work_orders), Decimal("0.00"))
            if booking_work_orders
            else locked_booking.quoted_price
        )
        invoice = Invoice.objects.create(
            booking=locked_booking,
            description=(
                f"{locked_booking.service_type} completed on "
                f"{locked_booking.booking_date}"
            ),
            amount=amount,
            status="draft",
            notes=locked_booking.notes,
        )
        replace_invoice_work_orders(
            invoice,
            (
                [
                    {"description": item.service_type, "price": item.price}
                    for item in booking_work_orders
                ]
                if booking_work_orders
                else [
                    {
                        "description": locked_booking.service_type,
                        "price": locked_booking.quoted_price,
                    }
                ]
            ),
        )
        return invoice, True
