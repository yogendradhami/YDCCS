# ====================================================
# YD Commercial Cleaning Services
# File: customers/admin.py
# Purpose:
# - Manage customers inside Django Admin
# - Link customers to portal login accounts
# ====================================================

from django.contrib import admin
<<<<<<< HEAD

=======
>>>>>>> 5815f15 (Initial project commit)
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "phone",
        "email",
        "suburb_postcode",
        "user",
        "jobs_completed",
        "total_revenue",
        "created_at",
    )

    search_fields = (
        "full_name",
        "phone",
        "email",
        "suburb_postcode",
        "user__username",
    )

    list_filter = (
        "property_type",
        "created_at",
<<<<<<< HEAD
    )
=======
    )
>>>>>>> 5815f15 (Initial project commit)
