
from django.contrib import admin

from .models import SecurityFinding
from .models import SecurityAlertDelivery

@admin.register(SecurityFinding)
class SecurityFindingAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "severity",
        "status",
        "source",
        "occurrences",
        "last_seen",
    )
    list_filter = ("severity", "status", "source")
    search_fields = ("title", "description", "path")
    readonly_fields = (
        "fingerprint",
        "first_seen",
        "last_seen",
        "occurrences",
        "resolved_at",
        "resolved_by",
    )
    ordering = ("-last_seen",)


@admin.register(SecurityAlertDelivery)
class SecurityAlertDeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "finding",
        "status",
        "attempts",
        "next_attempt_at",
        "sent_at",
    )
    list_filter = ("status",)
    search_fields = ("finding__title", "last_error")
    readonly_fields = ("created_at", "sent_at")