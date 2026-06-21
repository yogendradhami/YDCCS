# ====================================================
# YD Commercial Cleaning Services
# File: customers/models.py
# Purpose:
# - Customer CRM database
# - Links customer records to login accounts
# ====================================================

from django.contrib.auth.models import User
from django.db import models


class Customer(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_profile",
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name
