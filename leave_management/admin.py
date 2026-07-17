from django.contrib import admin
<<<<<<< HEAD

=======
>>>>>>> 5815f15 (Initial project commit)
from .models import LeaveRequest


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):

    list_display = (
        "employee",
        "leave_type",
        "start_date",
        "end_date",
        "status",
    )

    list_filter = (
        "status",
        "leave_type",
    )

<<<<<<< HEAD
    search_fields = ("employee__full_name",)
=======
    search_fields = (
        "employee__full_name",
    )
>>>>>>> 5815f15 (Initial project commit)
