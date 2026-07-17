<<<<<<< HEAD
from django.contrib.auth.models import User
from django.db import models
=======
from django.db import models
from django.contrib.auth.models import User
>>>>>>> 5815f15 (Initial project commit)


class Expense(models.Model):
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
<<<<<<< HEAD
        max_length=50, choices=CATEGORY_CHOICES, default="other"
=======
        max_length=50,
        choices=CATEGORY_CHOICES,
        default="other"
>>>>>>> 5815f15 (Initial project commit)
    )
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

<<<<<<< HEAD
    receipt = models.FileField(upload_to="expense_receipts/", blank=True, null=True)

    paid_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
=======
    receipt = models.FileField(
        upload_to="expense_receipts/",
        blank=True,
        null=True
    )

    paid_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
>>>>>>> 5815f15 (Initial project commit)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
<<<<<<< HEAD
        return f"{self.get_category_display()} - ${self.amount}"
=======
        return f"{self.get_category_display()} - ${self.amount}"
>>>>>>> 5815f15 (Initial project commit)
