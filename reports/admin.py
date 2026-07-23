from django.contrib import admin

from .models import CleaningReport


@admin.register(CleaningReport)
class CleaningReportAdmin(admin.ModelAdmin):
    list_display = ("booking", "emailed_to_customer", "generated_at")
    search_fields = ("booking__id",)
    list_filter = ("emailed_to_customer",)
    ordering = ("-generated_at",)
