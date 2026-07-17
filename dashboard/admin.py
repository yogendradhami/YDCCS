from django.contrib import admin
<<<<<<< HEAD

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
=======
from .models import Vehicle
admin.site.register(Vehicle)

from .models import (
    CompanySettings,
    ActivityLog,
    EmailLog,
    ReviewRequestLog,
    CampaignLog,
    Equipment,
    CleaningSupply,
    PurchaseOrder,
    Supplier,
    MaintenanceHistory

)

from .models import SiteImage
>>>>>>> 5815f15 (Initial project commit)

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
<<<<<<< HEAD
=======
admin.site.register(SiteImage)
>>>>>>> 5815f15 (Initial project commit)
