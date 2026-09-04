from django.urls import path

from .views import (
    create_ticket,
    customer_tickets,
    live_chat_close,
    live_chat_detail,
    live_chat_takeover,
    submit_chat_enquiry,
    support_dashboard,
    live_chat_counts,
    ticket_detail,
    ticket_reply,
    ticket_update,

)


urlpatterns = [

    # =====================================================
    # CUSTOMER SUPPORT
    # =====================================================

    path(
        "portal/support/",
        customer_tickets,
        name="customer_tickets",
    ),

    path(
        "portal/support/new/",
        create_ticket,
        name="create_ticket",
    ),
    path("portal/support/<int:ticket_id>/", ticket_detail, name="ticket_detail"),
    path("portal/support/<int:ticket_id>/reply/", ticket_reply, name="ticket_reply"),

    # =====================================================
    # STAFF DASHBOARD
    # =====================================================

    path(
        "dashboard/support/",
        support_dashboard,
        name="support_dashboard",
    ),
    path(
        "dashboard/support/tickets/<int:ticket_id>/update/",
        ticket_update,
        name="ticket_update",
    ),

    # =====================================================
    # WEBSITE CHAT ENQUIRY
    # =====================================================

    path(
        "chat/submit/",
        submit_chat_enquiry,
        name="submit_chat_enquiry",
    ),

    # =====================================================
    # LIVE CHAT STAFF API
    # =====================================================

    path(
        "dashboard/support/live-chat/<int:conversation_id>/",
        live_chat_detail,
        name="live_chat_detail",
    ),

    path(
        "dashboard/support/live-chat/<int:conversation_id>/takeover/",
        live_chat_takeover,
        name="live_chat_takeover",
    ),

    path(
        "dashboard/support/live-chat/<int:conversation_id>/close/",
        live_chat_close,
        name="live_chat_close",
    ),

    path(
        "dashboard/support/chat-counts/",
        live_chat_counts,
        name="live_chat_counts",
    ),
]