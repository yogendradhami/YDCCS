from django.contrib import admin

from .models import (
    ActivityLog,
    CampaignLog,
    CleaningSupply,
    CompanySettings,
    EmailLog,
    Equipment,
    MaintenanceHistory,
    PurchaseOrder,
    ReviewRequestLog,
    Supplier,
    Vehicle,
)

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
