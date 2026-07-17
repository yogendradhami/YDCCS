from django.contrib import admin
<<<<<<< HEAD

=======
>>>>>>> 5815f15 (Initial project commit)
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

<<<<<<< HEAD
    search_fields = ("employee__full_name",)
=======
    search_fields = (
        "employee__full_name",
    )
>>>>>>> 5815f15 (Initial project commit)
