from django.contrib import admin

from .models import (
    ChatEnquiry,
    ChatConversation,
    ChatMessage,
    SupportTicket,
)


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
    )

@admin.register(ChatEnquiry)
class ChatEnquiryAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "phone",
        "email",
        "enquiry_type",
        "service",
        "suburb",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "enquiry_type",
        "created_at",
    )

    search_fields = (
        "name",
        "phone",
        "email",
        "service",
        "suburb",
        "message",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)


@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "email",
        "phone",
        "status",
        "assigned_staff",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "name",
        "email",
        "phone",
        "session_key",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = ("-updated_at",)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):

    list_display = (
        "conversation",
        "sender_type",
        "sender",
        "is_automatic",
        "created_at",
    )

    list_filter = (
        "sender_type",
        "is_automatic",
        "created_at",
    )

    search_fields = (
        "message",
        "conversation__name",
        "conversation__email",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = ("-created_at",)