# ==========================================================
# File: payroll/admin.py
# Purpose:
# Admin panel settings for Payroll records.
# ==========================================================

from django.contrib import admin

from .models import PayrollRecord


@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    # Fields displayed in Django admin payroll list.
    list_display = (
        "employee",
        "period_start",
        "period_end",
        "total_hours",
        "hourly_rate",
        "gross_pay",
        "status",
    )

    # Filters shown on the right side of Django admin.
    list_filter = (
        "status",
        "period_start",
        "period_end",
    )

    # Search by employee name.
<<<<<<< HEAD
    search_fields = ("employee__full_name",)
=======
    search_fields = (
        "employee__full_name",
    )
>>>>>>> 5815f15 (Initial project commit)

    # Make newest payroll records appear first.
    ordering = (
        "-period_end",
        "employee__full_name",
<<<<<<< HEAD
    )
=======
    )
>>>>>>> 5815f15 (Initial project commit)
