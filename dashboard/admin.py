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
@admin.register(CareerApplication)
class CareerApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "position",
        "employment_type",
        "email",
        "phone",
        "status",
        "created_at",
    )

    list_filter = (
        "position",
        "employment_type",
        "status",
        "work_rights",
        "has_drivers_license",
        "has_vehicle",
        "created_at",
    )

    search_fields = (
        "full_name",
        "email",
        "phone",
        "suburb",
        "position",
        "skills",
    )

    ordering = ("-created_at",)

    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Applicant Information", {"fields": ("full_name", "email", "phone", "address", "suburb", "date_of_birth")} ),
        ("Position & Employment", {"fields": ("position", "employment_type")} ),
        ("Work Eligibility", {"fields": ("work_rights", "work_rights_details")} ),
        ("Experience & Skills", {"fields": ("years_cleaning_experience", "previous_cleaning_experience", "skills")} ),
        ("Availability", {"fields": ("has_drivers_license", "has_vehicle", "availability_days", "availability_hours", "preferred_start_date")} ),
        ("Application Documents", {"fields": ("cover_letter", "resume")} ),
        ("References", {"fields": ("reference_name", "reference_phone", "reference_relationship")} ),
        ("Internal Management", {"fields": ("status", "admin_notes")} ),
    )


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