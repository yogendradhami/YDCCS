from django.contrib import admin

from .models import CleaningContract


@admin.register(CleaningContract)
class CleaningContractAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "service_type",
        "frequency",
        "start_date",
        "end_date",
        "price_per_visit",
        "status",
        "assigned_employee",
    )

    list_filter = (
        "frequency",
        "status",
        "start_date",
    )

    search_fields = (
        "customer__full_name",
        "service_type",
        "address",
        "suburb_postcode",
    )
