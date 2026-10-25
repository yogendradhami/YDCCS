import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone

from .models import LiveChatConversation

logger = logging.getLogger(__name__)
DASHBOARD_GROUP = "support_live_chat_dashboard"


def has_chat_permission(user, action):
    return bool(
        user
        and user.is_authenticated
        and user.is_staff
        and not hasattr(user, "employee_profile")
        and user.has_perm("security.access_dashboard")
        and user.has_perm(f"support.{action}_livechatconversation")
    )


def conversation_summary(conversation_id):
    conversation = (
        LiveChatConversation.objects.select_related("assigned_to")
        .filter(pk=conversation_id)
        .first()
    )
    if conversation is None:
        return None
    latest = conversation.messages.order_by("-pk").first()
    assigned_to = conversation.assigned_to
    return {
        "id": conversation.pk,
        "name": conversation.name or "Website Visitor",
        "status": conversation.status,
        "assigned_to": (
            assigned_to.get_full_name() or assigned_to.username
            if assigned_to
            else ""
        ),
        "assigned_to_id": conversation.assigned_to_id,
        "updated_at": conversation.updated_at.isoformat(),
        "preview": latest.message[:160] if latest else "",
        "last_sender_type": latest.sender_type if latest else "system",
        "last_message_id": latest.pk if latest else None,
        "unread": bool(latest and latest.sender_type == "customer"),
        "legal_hold": conversation.legal_hold,
        "archived": conversation.status == "closed",
    }


def _send_dashboard_update(conversation_id, event_name):
    try:
        summary = conversation_summary(conversation_id)
        channel_layer = get_channel_layer()
        if channel_layer is None:
            raise RuntimeError("The live-chat channel layer is unavailable.")
        async_to_sync(channel_layer.group_send)(
            DASHBOARD_GROUP,
            {
                "type": "dashboard_update",
                "event": event_name,
                "conversation": summary,
                "conversation_id": conversation_id,
                "occurred_at": timezone.now().isoformat(),
            },
        )
    except Exception:
        logger.exception(
            "Live-chat dashboard broadcast failed for conversation %s.",
            conversation_id,
        )


def send_conversation_event(conversation_id, event):
    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            raise RuntimeError("The live-chat channel layer is unavailable.")
        async_to_sync(channel_layer.group_send)(
            f"live_chat_{conversation_id}",
            event,
        )
    except Exception:
        logger.exception(
            "Live-chat conversation broadcast failed for conversation %s.",
            conversation_id,
        )


def queue_dashboard_update(conversation_id, event_name="conversation.updated"):
    transaction.on_commit(
        lambda: _send_dashboard_update(conversation_id, event_name)
    )
