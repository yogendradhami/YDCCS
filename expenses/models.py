from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models


class Expense(models.Model):
    class PaymentStatus(models.TextChoices):
        UNCONFIRMED = "unconfirmed", "Unconfirmed"
        UNPAID = "unpaid", "Unpaid"
        PAID = "paid", "Paid"

    CATEGORY_CHOICES = [
        ("fuel", "Fuel"),
        ("cleaning_supplies", "Cleaning Supplies"),
        ("equipment", "Equipment"),
        ("marketing", "Marketing"),
        ("insurance", "Insurance"),
        ("vehicle", "Vehicle"),
        ("software", "Software"),
        ("office", "Office"),
        ("other", "Other"),
    ]

    date = models.DateField()
    category = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES, default="other"
    )
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    receipt = models.FileField(upload_to="expense_receipts/", blank=True, null=True)

    invoice_review = models.OneToOneField(
        "company_documents.InvoiceDocumentReview",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="expense",
    )
    supplier = models.ForeignKey(
        "dashboard.Supplier",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="expenses",
    )
    purchase_order = models.ForeignKey(
        "dashboard.PurchaseOrder",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="expenses",
    )
    invoice_number = models.CharField(max_length=150, blank=True)
    due_date = models.DateField(null=True, blank=True)
    gst_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    payment_status = models.CharField(
        max_length=16,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNCONFIRMED,
        db_index=True,
    )
    recorded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_expenses",
    )

    paid_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.get_category_display()} - ${self.amount}"

    def delete(self, *args, **kwargs):
        if self.invoice_review_id:
            raise ValidationError(
                "Expenses linked to supplier invoice reviews are retained for audit."
            )
        return super().delete(*args, **kwargs)
