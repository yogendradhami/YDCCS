# ====================================================
# YD Commercial Cleaning Services
# File: employees/admin.py
# Purpose:
# - Manage employees in Django Admin
# - Link employees to login accounts
# ====================================================

from django.contrib import admin
from django.utils.html import format_html

from .models import Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "phone",
        "email",
        "user",
        "role",
        "availability_badge",
        "hourly_rate",
        "jobs_completed",
        "active",
        "created_at",
    )

    search_fields = (
        "full_name",
        "phone",
        "email",
        "role",
        "user__username",
    )

    list_filter = (
        "role",
        "availability",
        "active",
        "created_at",
    )

    def availability_badge(self, obj):
        colors = {
            "available": "#16a34a",
            "unavailable": "#dc2626",
            "on_leave": "#f59e0b",
        }

        return format_html(
            (
                '<span style="background:{};color:white;padding:5px 10px;'
                'border-radius:20px;font-weight:bold;">{}</span>'
            ),
            colors.get(obj.availability, "#6b7280"),
            obj.get_availability_display(),
        )

    availability_badge.short_description = "Availability"
