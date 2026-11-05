from decimal import Decimal

from django.db import migrations
from django.db.models import Sum


def reconcile_paid_invoice_bookings(apps, schema_editor):
    Invoice = apps.get_model("invoices", "Invoice")
    Booking = apps.get_model("bookings", "Booking")
    Customer = apps.get_model("customers", "Customer")
    database = schema_editor.connection.alias

    customer_ids = set()
    paid_booking_totals = (
        Invoice.objects.using(database)
        .filter(status="paid")
        .values("booking_id")
        .annotate(amount=Sum("amount"), discounts=Sum("discount_amount"))
        .iterator()
    )

    for paid_booking_total in paid_booking_totals:
        booking = Booking.objects.using(database).get(
            pk=paid_booking_total["booking_id"]
        )
        booking.status = "completed"
        booking.quoted_price = max(
            (paid_booking_total["amount"] or Decimal("0.00"))
            - (paid_booking_total["discounts"] or Decimal("0.00")),
            Decimal("0.00"),
        )
        booking.save(using=database, update_fields=["status", "quoted_price"])
        if booking.customer_id:
            customer_ids.add(booking.customer_id)

    for customer_id in customer_ids:
        completed_jobs = Booking.objects.using(database).filter(
            customer_id=customer_id,
            status="completed",
        ).count()
        total_revenue = (
            Invoice.objects.using(database)
            .filter(booking__customer_id=customer_id, status="paid")
            .aggregate(total=Sum("total_amount"))["total"]
            or Decimal("0.00")
        )
        Customer.objects.using(database).filter(pk=customer_id).update(
            jobs_completed=completed_jobs,
            total_revenue=total_revenue,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0004_invoiceworkorder"),
        ("customers", "0006_marketingsubscriber"),
    ]

    operations = [
        migrations.RunPython(
            reconcile_paid_invoice_bookings,
            migrations.RunPython.noop,
        ),
    ]
