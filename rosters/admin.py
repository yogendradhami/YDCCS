from django.contrib import admin

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

    search_fields = ("employee__full_name",)
