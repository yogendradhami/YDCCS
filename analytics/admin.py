from django.contrib import admin

from .models import (
    Visitor,
    VisitorSession,
    ActivityEvent,
    SearchEvent,
)


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = (
        "visitor_id",
        "first_seen",
        "last_seen",
        "total_sessions",
        "total_page_views",
        "is_returning",
        "device_type",
    )

    search_fields = ("visitor_id",)

    list_filter = (
        "is_returning",
        "device_type",
    )

    readonly_fields = (
        "visitor_id",
        "first_seen",
        "last_seen",
    )


@admin.register(VisitorSession)
class VisitorSessionAdmin(admin.ModelAdmin):
    list_display = (
        "session_id",
        "visitor",
        "started_at",
        "last_activity",
        "landing_page",
        "is_active",
    )

    search_fields = (
        "session_id",
        "visitor__visitor_id",
        "landing_page",
    )

    list_filter = (
        "is_active",
    )

    readonly_fields = (
        "session_id",
        "started_at",
        "last_activity",
    )


@admin.register(ActivityEvent)
class ActivityEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_type",
        "visitor",
        "session",
        "page_url",
        "created_at",
    )

    search_fields = (
        "visitor__visitor_id",
        "page_url",
        "element",
    )

    list_filter = (
        "event_type",
        "created_at",
    )

    readonly_fields = (
        "created_at",
    )


@admin.register(SearchEvent)
class SearchEventAdmin(admin.ModelAdmin):
    list_display = (
        "query",
        "visitor",
        "session",
        "page_url",
        "created_at",
    )

    search_fields = (
        "query",
        "page_url",
    )

    list_filter = (
        "created_at",
    )

    readonly_fields = (
        "created_at",
    )