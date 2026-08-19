from django.contrib import admin

from .models import (
    ActivityLog,
    CampaignLog,
    CleaningSupply,
    CompanySettings,
    EmailLog,
    Equipment,
    MaintenanceHistory,
    CareerApplication,
    PurchaseOrder,
    ReviewRequestLog,
    Supplier,
    Vehicle,
)

from core.models import TeamMember


admin.site.register(Vehicle)

admin.site.register(CompanySettings)
admin.site.register(ActivityLog)
admin.site.register(EmailLog)
admin.site.register(ReviewRequestLog)
admin.site.register(CampaignLog)
admin.site.register(Equipment)
admin.site.register(CleaningSupply)
admin.site.register(PurchaseOrder)
admin.site.register(Supplier)
admin.site.register(MaintenanceHistory)
admin.site.register(CareerApplication)


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "role",
        "display_order",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "role",
    )

    search_fields = (
        "name",
        "role",
        "short_bio",
        "email",
    )

    ordering = (
        "display_order",
        "name",
    )

    list_editable = (
        "display_order",
        "is_active",
    )