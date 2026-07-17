from django.contrib import admin
<<<<<<< HEAD

=======
>>>>>>> 5815f15 (Initial project commit)
from .models import Roster


@admin.register(Roster)
class RosterAdmin(admin.ModelAdmin):

    list_display = (
        "employee",
        "shift_date",
        "start_time",
        "end_time",
        "status",
    )

    list_filter = (
        "status",
        "shift_date",
    )

<<<<<<< HEAD
    search_fields = ("employee__full_name",)
=======
    search_fields = (
        "employee__full_name",
    )
>>>>>>> 5815f15 (Initial project commit)
