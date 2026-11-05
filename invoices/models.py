# ====================================================
# YD Commercial Cleaning Services
# File: invoices/models.py
# ====================================================

from decimal import Decimal

from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone

from bookings.models import Booking
from customers.models import Customer


class Invoice(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("sent", "Sent"),
        ("paid", "Paid"),
        ("overdue", "Overdue"),
        ("cancelled", "Cancelled"),
    ]

    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="invoices"
    )

    invoice_number = models.CharField(max_length=50, unique=True, blank=True)

    issue_date = models.DateField(default=timezone.now)

    due_date = models.DateField(null=True, blank=True)

    description = models.TextField(blank=True, default="Cleaning service")

    amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )

    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )

    gst_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )

    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    stripe_checkout_session_id = models.CharField(max_length=255, blank=True)

    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)

    paid_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        previous = None
        if self.pk:
            previous = (
                Invoice.objects.filter(pk=self.pk)
                .values("status", "booking_id")
                .first()
            )
        previous_customer_id = None
        if previous:
            previous_customer_id = (
                Booking.objects.filter(pk=previous["booking_id"])
                .values_list("customer_id", flat=True)
                .first()
            )

        if self.status == "paid" and not self.paid_at:
            self.paid_at = timezone.now()
            if kwargs.get("update_fields") is not None:
                kwargs["update_fields"] = set(kwargs["update_fields"]) | {"paid_at"}

        if not self.invoice_number:
            next_number = 1

            last_invoice = (
                Invoice.objects.exclude(invoice_number="").order_by("-id").first()
            )

            if last_invoice and last_invoice.invoice_number:
                try:
                    next_number = (
                        int(last_invoice.invoice_number.replace("YD-", "")) + 1
                    )
                except ValueError:
                    next_number = last_invoice.id + 1

            while True:
                candidate = f"YD-{next_number:05d}"

                if not Invoice.objects.filter(invoice_number=candidate).exists():
                    self.invoice_number = candidate
                    break

                next_number += 1

        if not self.due_date:
            self.due_date = self.issue_date + timezone.timedelta(days=14)

        gst_rate = Decimal("0.10")

        taxable_amount = self.amount - self.discount_amount

        if taxable_amount < 0:
            taxable_amount = Decimal("0.00")

        self.gst_amount = taxable_amount * gst_rate
        self.total_amount = taxable_amount + self.gst_amount

        today = timezone.now().date()

        today = timezone.now().date()

        due_date_value = self.due_date

        if hasattr(due_date_value, "date"):
            due_date_value = due_date_value.date()

        if (
            due_date_value
            and due_date_value < today
            and self.status not in ["paid", "cancelled"]
        ):
            self.status = "overdue"

        with transaction.atomic():
            super().save(*args, **kwargs)

            customer_ids_to_sync = set()
            if self.status == "paid":
                booking = Booking.objects.select_for_update().get(
                    pk=self.booking_id
                )
                paid_invoices = Invoice.objects.filter(status="paid")
                if booking.customer_id:
                    paid_invoices = paid_invoices.filter(
                        booking__customer_id=booking.customer_id
                    )
                else:
                    paid_invoices = paid_invoices.filter(
                        booking_id=self.booking_id
                    )

                paid_booking_totals = paid_invoices.values(
                    "booking_id"
                ).annotate(
                    amount=Sum("amount"),
                    discounts=Sum("discount_amount"),
                )
                for paid_booking_total in paid_booking_totals:
                    paid_booking = Booking.objects.select_for_update().get(
                        pk=paid_booking_total["booking_id"]
                    )
                    paid_booking.status = "completed"
                    paid_booking.quoted_price = max(
                        (paid_booking_total["amount"] or Decimal("0.00"))
                        - (paid_booking_total["discounts"] or Decimal("0.00")),
                        Decimal("0.00"),
                    )
                    paid_booking.save(update_fields=["status", "quoted_price"])

                if booking.customer_id:
                    customer_ids_to_sync.add(booking.customer_id)

            if previous and (
                previous["status"] == "paid" or self.status == "paid"
            ):
                if previous_customer_id:
                    customer_ids_to_sync.add(previous_customer_id)
                current_customer_id = Booking.objects.filter(
                    pk=self.booking_id
                ).values_list("customer_id", flat=True).first()
                if current_customer_id:
                    customer_ids_to_sync.add(current_customer_id)

            for customer_id in customer_ids_to_sync:
                completed_jobs = Booking.objects.filter(
                    customer_id=customer_id,
                    status="completed",
                ).count()
                total_revenue = Invoice.objects.filter(
                    booking__customer_id=customer_id,
                    status="paid",
                ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
                Customer.objects.filter(pk=customer_id).update(
                    jobs_completed=completed_jobs,
                    total_revenue=total_revenue,
                )

    def __str__(self):
        customer = self.booking.customer
        customer_name = customer.full_name if customer else "No customer"
        return f"{self.invoice_number} - {customer_name}"


class InvoiceWorkOrder(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="work_orders",
    )
    description = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "pk"]

    def __str__(self):
        return f"{self.position + 1}. {self.description}"
