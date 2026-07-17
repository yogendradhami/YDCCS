# ====================================================
# YD Commercial Cleaning Services
# File: invoices/models.py
# ====================================================

from decimal import Decimal

from django.db import models
from django.utils import timezone

from bookings.models import Booking


class Invoice(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("sent", "Sent"),
        ("paid", "Paid"),
        ("overdue", "Overdue"),
        ("cancelled", "Cancelled"),
    ]

    booking = models.ForeignKey(
<<<<<<< HEAD
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
=======
        Booking,
        on_delete=models.CASCADE,
        related_name="invoices"
    )

    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True
    )

    issue_date = models.DateField(
        default=timezone.now
    )

    due_date = models.DateField(
        null=True,
        blank=True
    )

    description = models.TextField(
        blank=True,
        default="Cleaning service"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    gst_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )

    stripe_checkout_session_id = models.CharField(
        max_length=255,
        blank=True
    )

    stripe_payment_intent_id = models.CharField(
        max_length=255,
        blank=True
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )
>>>>>>> 5815f15 (Initial project commit)

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            next_number = 1

            last_invoice = (
<<<<<<< HEAD
                Invoice.objects.exclude(invoice_number="").order_by("-id").first()
=======
                Invoice.objects
                .exclude(invoice_number="")
                .order_by("-id")
                .first()
>>>>>>> 5815f15 (Initial project commit)
            )

            if last_invoice and last_invoice.invoice_number:
                try:
                    next_number = (
<<<<<<< HEAD
                        int(last_invoice.invoice_number.replace("YD-", "")) + 1
=======
                        int(
                            last_invoice.invoice_number.replace(
                                "YD-",
                                ""
                            )
                        )
                        + 1
>>>>>>> 5815f15 (Initial project commit)
                    )
                except ValueError:
                    next_number = last_invoice.id + 1

            while True:
                candidate = f"YD-{next_number:05d}"

<<<<<<< HEAD
                if not Invoice.objects.filter(invoice_number=candidate).exists():
=======
                if not Invoice.objects.filter(
                    invoice_number=candidate
                ).exists():
>>>>>>> 5815f15 (Initial project commit)
                    self.invoice_number = candidate
                    break

                next_number += 1

        if not self.due_date:
<<<<<<< HEAD
            self.due_date = self.issue_date + timezone.timedelta(days=14)
=======
            self.due_date = (
                self.issue_date +
                timezone.timedelta(days=14)
            )
>>>>>>> 5815f15 (Initial project commit)

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

        super().save(*args, **kwargs)

    def __str__(self):
<<<<<<< HEAD
        return f"{self.invoice_number} - " f"{self.booking.customer.full_name}"
=======
        return (
            f"{self.invoice_number} - "
            f"{self.booking.customer.full_name}"
        )
>>>>>>> 5815f15 (Initial project commit)
