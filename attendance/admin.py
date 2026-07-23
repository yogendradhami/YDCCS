from django.contrib import admin

from .models import AttendanceLog


@admin.register(AttendanceLog)
class AttendanceLogAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "booking",
        "check_in_time",
        "check_out_time",
        "total_hours",
    )

    list_filter = (
        "check_in_time",
        "check_out_time",
    )

    search_fields = ("employee__full_name",)
