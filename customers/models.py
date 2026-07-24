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

    @property
    def title_prefix(self):
        parts = (self.full_name or "").strip().split()
        if not parts:
            return ""

        prefix = parts[0].lower()
        mapping = {
            "mr": "Mr.",
            "mrs": "Mrs.",
            "ms": "Ms.",
            "miss": "Miss",
            "master": "Master",
            "dr": "Dr.",
        }

        if prefix.rstrip(".") in mapping:
            return mapping[prefix.rstrip(".")]

        return ""

    @property
    def last_name(self):
        parts = (self.full_name or "").strip().split()
        if len(parts) <= 1:
            return parts[0] if parts else ""
        return parts[-1]

    @property
    def gallery_display_name(self):
        title = self.title_prefix
        last_name = self.last_name
        if title and last_name:
            return f"{title} {last_name}"
        return self.full_name or last_name

    def __str__(self):
        return self.full_name
