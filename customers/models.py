# ====================================================
# YD Commercial Cleaning Services
# File: customers/models.py
# Purpose:
# - Customer CRM database
# - Links customer records to login accounts
# ====================================================

<<<<<<< HEAD
from django.contrib.auth.models import User
from django.db import models
=======
from django.db import models
from django.contrib.auth.models import User
>>>>>>> 5815f15 (Initial project commit)


class Customer(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
<<<<<<< HEAD
        related_name="customer_profile",
=======
        related_name="customer_profile"
>>>>>>> 5815f15 (Initial project commit)
    )

    full_name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30)
    address = models.CharField(max_length=255, blank=True)

    property_type = models.CharField(max_length=100, blank=True)
    suburb_postcode = models.CharField(max_length=150, blank=True)
    notes = models.TextField(blank=True)

    jobs_completed = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)

<<<<<<< HEAD
=======
        # ----------------------------------------------------
    # Email verification
    # ----------------------------------------------------

    email_verified = models.BooleanField(
        default=False,
        help_text="Has customer verified email address?"
    )

    verification_token = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Email verification token"
    )

>>>>>>> 5815f15 (Initial project commit)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
<<<<<<< HEAD
        return self.full_name
=======
        return self.full_name
>>>>>>> 5815f15 (Initial project commit)
