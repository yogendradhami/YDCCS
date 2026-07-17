from django.contrib import admin
<<<<<<< HEAD

=======
>>>>>>> 5815f15 (Initial project commit)
from .models import SupportTicket


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):

    list_display = (
        "subject",
        "customer",
        "priority",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "priority",
    )

    search_fields = (
        "subject",
        "customer__full_name",
<<<<<<< HEAD
    )
=======
    )
>>>>>>> 5815f15 (Initial project commit)
