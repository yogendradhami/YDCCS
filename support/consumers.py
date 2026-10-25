import asyncio
import json
import logging
import re
from datetime import timedelta

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import DatabaseError, transaction
from django.utils import timezone
from django.core import signing

from .chat_faq import FAQ_RESPONSES
from .chat_intent import analyze_message
from .chat_workflow import (
    create_confirmed_booking,
    create_confirmed_quote,
    handle_message,
)
from .models import (
    LiveChatConversation,
    LiveChatMessage,
)
from .rate_limits import allow_live_chat_action
from .realtime import DASHBOARD_GROUP, has_chat_permission, queue_dashboard_update


# =========================================================
# SETTINGS
# =========================================================

# Automatically close a conversation after this many
# minutes without customer/staff activity.
INACTIVITY_TIMEOUT_MINUTES = 10

# How often the connected WebSocket checks inactivity.
INACTIVITY_CHECK_INTERVAL_SECONDS = 60

logger = logging.getLogger(__name__)


class LiveChatConsumer(
    AsyncJsonWebsocketConsumer
):

    # =====================================================
    # SESSION VALIDATION
    # =====================================================

    @staticmethod
    def is_valid_session_key(
        session_key,
    ):
        return bool(
            session_key
            and len(session_key) <= 100
            and not any(
                character.isspace()
                for character in session_key
            )
            and not any(
                ord(character) < 32
                for character in session_key
            )
        )

    @database_sync_to_async
    def validate_customer_token(self, token):
        try:
            payload = signing.loads(
                token,
                salt="support.live-chat.session",
                max_age=60 * 60 * 24 * 14,
            )
        except (signing.BadSignature, TypeError, ValueError):
            return None
        session_key = payload.get("session_key")
        session = self.scope.get("session")
        if (
            not isinstance(session_key, str)
            or not session
            or session.get("live_chat_session_key") != session_key
        ):
            return None
        return session_key

    @database_sync_to_async
    def has_permission(self, action):
        return has_chat_permission(
            self.scope.get("user"),
            action,
        )

    @database_sync_to_async
    def rate_limit(self, identity, action, limit):
        return allow_live_chat_action(identity, action, limit)

    @database_sync_to_async
    def schedule_dashboard_update(self, conversation_id, event_name):
        queue_dashboard_update(conversation_id, event_name)

    # =====================================================
    # RAW RECEIVE
    # =====================================================

    async def receive(
        self,
        text_data=None,
        bytes_data=None,
    ):
        """
        Return a safe protocol error for malformed JSON
        payloads.
        """

        try:

            await super().receive(
                text_data=text_data,
                bytes_data=bytes_data,
            )

        except (
            json.JSONDecodeError,
            UnicodeDecodeError,
            TypeError,
        ):

            await self.send_json(
                {
                    "type": "error",
                    "message": (
                        "Invalid WebSocket request."
                    ),
                }
            )

    # =====================================================
    # CONNECT
    # =====================================================

    async def connect(
        self,
    ):

        self.conversation_id = None
        self.conversation = None
        self.session_key = None
        self.is_staff = False
        self.chat_role = None
        self.room_group_name = None

        self.inactivity_task = None
        self.chat_closed = False

        client = self.scope.get("client") or ("unknown", 0)
        if not await self.rate_limit(
            f"ip:{client[0]}",
            "connect",
            40,
        ):
            await self.close(code=4429)
            return

        await self.accept()

        # -------------------------------------------------
        # Determine whether this is a staff connection.
        # -------------------------------------------------

        user = self.scope.get(
            "user"
        )

        self.is_staff = bool(
            user
            and user.is_authenticated
            and user.is_staff
        )

        await self.send_json(
            {
                "type": "connection",
                "success": True,
            }
        )

    # =====================================================
    # DISCONNECT
    # =====================================================

    async def disconnect(
        self,
        close_code,
    ):

        # -------------------------------------------------
        # Stop inactivity background task.
        # -------------------------------------------------

        if self.inactivity_task:

            self.inactivity_task.cancel()

            try:

                await self.inactivity_task

            except asyncio.CancelledError:
                pass

            except Exception:
                logger.exception("Could not stop the live-chat inactivity monitor.")

            self.inactivity_task = None

        # -------------------------------------------------
        # Leave channel group.
        # -------------------------------------------------

        if self.room_group_name:

            try:

                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name,
                )

            except Exception:
                logger.exception("Could not leave the live-chat conversation group.")

        if getattr(self, "dashboard_group_joined", False):
            try:
                await self.channel_layer.group_discard(
                    DASHBOARD_GROUP,
                    self.channel_name,
                )
            except Exception:
                logger.exception("Could not leave the live-chat dashboard group.")

    # =====================================================
    # RECEIVE JSON
    # =====================================================

    async def receive_json(
        self,
        content,
        **kwargs,
    ):

        # =================================================
        # BASIC VALIDATION
        # =================================================

        if not isinstance(
            content,
            dict,
        ):

            await self.send_json(
                {
                    "type": "error",
                    "message": (
                        "Invalid WebSocket request."
                    ),
                }
            )

            return

        action = content.get(
            "action",
            "",
        )

        if (
            not isinstance(
                action,
                str,
            )
            or not action.strip()
        ):

            await self.send_json(
                {
                    "type": "error",
                    "message": (
                        "Chat action is required."
                    ),
                }
            )

            return

        action = action.strip()

        conversation_id = content.get(
            "conversation_id"
        )

        if conversation_id is not None:

            if isinstance(
                conversation_id,
                bool,
            ):

                await self.send_json(
                    {
                        "type": "error",
                        "message": (
                            "Invalid conversation ID."
                        ),
                    }
                )

                return

            try:

                conversation_id = int(
                    conversation_id
                )

            except (
                TypeError,
                ValueError,
            ):

                await self.send_json(
                    {
                        "type": "error",
                        "message": (
                            "Invalid conversation ID."
                        ),
                    }
                )

                return

            if conversation_id <= 0:

                await self.send_json(
                    {
                        "type": "error",
                        "message": (
                            "Invalid conversation ID."
                        ),
                    }
                )

                return

        # =================================================
        # UPDATE STAFF STATUS
        # =================================================

        user = self.scope.get(
            "user"
        )

        self.is_staff = bool(
            user
            and user.is_authenticated
            and user.is_staff
        )

        if action == "dashboard_join":
            if not await self.has_permission("view"):
                await self.send_json(
                    {"type": "error", "message": "Support chat access required."}
                )
                return
            await self.channel_layer.group_add(
                DASHBOARD_GROUP,
                self.channel_name,
            )
            self.dashboard_group_joined = True
            await self.send_json(
                {"type": "dashboard_joined", "success": True}
            )
            return

        # =================================================
        # JOIN ACTIONS
        # =================================================

        if action in (
            "customer_join",
            "staff_join",
        ):

            # =================================================
            # CUSTOMER JOIN
            # =================================================

            if action == "customer_join":

                session_key = await self.validate_customer_token(
                    content.get("session_token", "")
                )
                if not session_key:

                    await self.send_json(
                        {
                            "type": "error",
                            "message": (
                                "Chat session is invalid or expired. Refresh the page and retry."
                            ),
                        }
                    )

                    return

                self.chat_role = "customer"
                self.session_key = (
                    session_key
                )
                raw_name = content.get("name", "Website Visitor")
                raw_email = content.get("email", "")
                raw_phone = content.get("phone", "")
                if not all(
                    isinstance(value, str)
                    for value in (raw_name, raw_email, raw_phone)
                ):
                    await self.send_json(
                        {"type": "error", "message": "Invalid visitor details."}
                    )
                    return
                name = " ".join(raw_name.split()) or "Website Visitor"
                email = raw_email.strip().lower()
                phone = raw_phone.strip()
                if len(name) > 150 or len(email) > 254 or len(phone) > 30:
                    await self.send_json(
                        {"type": "error", "message": "Visitor details are too long."}
                    )
                    return
                if email:
                    try:
                        validate_email(email)
                    except ValidationError:
                        await self.send_json(
                            {"type": "error", "message": "Please provide a valid email address."}
                        )
                        return
                if phone and not re.fullmatch(r"[0-9+(). -]{1,30}", phone):
                    await self.send_json(
                        {"type": "error", "message": "Please provide a valid phone number."}
                    )
                    return

                conversation = (
                    await self.get_or_create_customer_conversation(
                        session_key=session_key,
                        name=name,
                        email=email,
                        phone=phone,
                    )
                )

                if not conversation:

                    await self.send_json(
                        {
                            "type": "error",
                            "message": (
                                "Unable to create live chat "
                                "conversation."
                            ),
                        }
                    )

                    return

            # =================================================
            # STAFF JOIN
            # =================================================

            else:

                if not await self.has_permission("view"):

                    await self.send_json(
                        {
                            "type": "error",
                            "message": (
                                "Staff access required."
                            ),
                        }
                    )

                    return

                conversation_id = (
                    content.get(
                        "conversation_id"
                    )
                )

                if not conversation_id:

                    await self.send_json(
                        {
                            "type": "error",
                            "message": (
                                "Conversation ID is required."
                            ),
                        }
                    )

                    return

                conversation = (
                    await self.get_conversation(
                        conversation_id
                    )
                )

                if not conversation:

                    await self.send_json(
                        {
                            "type": "error",
                            "message": (
                                "Conversation not found."
                            ),
                        }
                    )

                    return

                self.chat_role = "staff"

            # -------------------------------------------------
            # Set current conversation.
            # -------------------------------------------------

            previous_group = getattr(self, "room_group_name", None)
            next_group = f"live_chat_{conversation.id}"
            if previous_group and previous_group != next_group:
                await self.channel_layer.group_discard(
                    previous_group,
                    self.channel_name,
                )
            self.conversation = (
                conversation
            )

            self.conversation_id = (
                conversation.id
            )

            self.room_group_name = next_group

            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name,
            )

            # -------------------------------------------------
            # Check inactivity before continuing.
            # -------------------------------------------------

            if await self.check_inactivity(
                conversation
            ):

                await self.send_json(
                    {
                        "type": "chat_closed",
                        "success": False,
                        "reason": "inactivity",
                        "message": (
                            "This conversation was automatically "
                            "closed because there was no activity "
                            f"for {INACTIVITY_TIMEOUT_MINUTES} "
                            "minutes."
                        ),
                    }
                )

                self.chat_closed = True

                return

            conversation = await self.get_conversation(conversation.id)
            if conversation is None:
                await self.send_json(
                    {"type": "error", "message": "Conversation not found."}
                )
                return
            if conversation.status == "closed":
                await self.send_json(
                    {
                        "type": "chat_closed",
                        "success": False,
                        "message": "This conversation has been closed.",
                    }
                )
                self.chat_closed = True
                return
            self.conversation = conversation

            # -------------------------------------------------
            # Start inactivity monitor.
            # -------------------------------------------------

            self.start_inactivity_monitor()

            # -------------------------------------------------
            # Send successful connection.
            # -------------------------------------------------

            await self.send_json(
                {
                    "type": "connection",
                    "success": True,
                    "conversation_id": (
                        conversation.id
                    ),
                    "status": (
                        conversation.status
                    ),
                    "message": (
                        "Live chat connected."
                    ),
                    "assigned_to_id": conversation.assigned_to_id,
                    "assigned_to": (
                        conversation.assigned_to.get_full_name()
                        or conversation.assigned_to.username
                        if conversation.assigned_to
                        else ""
                    ),
                }
            )

            return

        # =================================================
        # REQUIRE CONVERSATION FOR OTHER ACTIONS
        # =================================================

        if not conversation_id:

            conversation_id = getattr(
                self,
                "conversation_id",
                None,
            )

        if not conversation_id:

            await self.send_json(
                {
                    "type": "error",
                    "message": (
                        "No active conversation."
                    ),
                }
            )

            return

        if conversation_id != getattr(self, "conversation_id", None):
            await self.send_json(
                {
                    "type": "error",
                    "message": "Join this conversation before performing chat actions.",
                }
            )
            return

        # -------------------------------------------------
        # Staff can access conversations by ID.
        # Customers must prove session ownership.
        # -------------------------------------------------

        if self.is_staff and self.chat_role != "customer":

            conversation = (
                await self.get_conversation(
                    conversation_id
                )
            )

        else:
            session_key = getattr(self, "session_key", None)
            if not session_key or conversation_id != self.conversation_id:

                await self.send_json(
                    {
                        "type": "error",
                        "message": (
                            "Chat session authorization is required."
                        ),
                    }
                )

                return

            conversation = (
                await self.get_customer_conversation(
                    conversation_id,
                    getattr(
                        self,
                        "session_key",
                        None,
                    ),
                )
            )

        if not conversation:

            await self.send_json(
                {
                    "type": "error",
                    "message": (
                        "Conversation not found."
                    ),
                }
            )

            return

        self.conversation = (
            conversation
        )

        self.conversation_id = (
            conversation.id
        )

        # =================================================
        # IMPORTANT:
        #
        # Inactivity check happens before processing
        # any message or action.
        # =================================================

        if await self.check_inactivity(
            conversation
        ):

            await self.send_json(
                {
                    "type": "chat_closed",
                    "success": False,
                    "reason": "inactivity",
                    "message": (
                        "This conversation was automatically "
                        "closed because there was no activity "
                        f"for {INACTIVITY_TIMEOUT_MINUTES} "
                        "minutes."
                    ),
                }
            )

            self.chat_closed = True

            return

        # =================================================
        # CLOSED CHAT CHECK
        # =================================================

        if conversation.status == "closed":

            await self.send_json(
                {
                    "type": "chat_closed",
                    "success": False,
                    "message": (
                        "This conversation has been closed."
                    ),
                }
            )

            self.chat_closed = True

            return

        if (
            action in {"customer_message", "message"}
            and self.is_staff
            and self.chat_role != "customer"
        ):
            await self.send_json(
                {
                    "type": "error",
                    "message": "Staff must use the authorized staff message action.",
                }
            )
            return

        # =================================================
        # STAFF TAKEOVER
        # =================================================

        if action == "staff_takeover":

            if self.chat_role != "staff" or not await self.has_permission("change"):

                await self.send_json(
                    {
                        "type": "error",
                        "message": (
                            "Staff access required."
                        ),
                    }
                )

                return

            user = self.scope["user"]

            takeover_message_id = await self.takeover_conversation(
                conversation.id,
                user.id,
            )
            if not takeover_message_id:
                await self.send_json(
                    {
                        "type": "error",
                        "message": "This chat is closed or already assigned to another staff member.",
                    }
                )
                return

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_system",
                    "message": (
                        f"{user.get_full_name() or user.username} "
                        "has taken over this conversation."
                    ),
                    "message_id": takeover_message_id,
                    "status": "active",
                },
            )

            return

        # =================================================
        # STAFF CLOSE
        # =================================================

        if action == "staff_close":

            if self.chat_role != "staff" or not await self.has_permission("change"):

                await self.send_json(
                    {
                        "type": "error",
                        "message": (
                            "Staff access required."
                        ),
                    }
                )

                return

            user = self.scope["user"]

            close_message = (
                "This conversation was closed by "
                f"{user.get_full_name() or user.username}."
            )

            close_message_id = await self.close_conversation(
                conversation.id,
                sender_name=(
                    user.get_full_name()
                    or user.username
                    or "YD Cleaning Support"
                ),
                message=close_message,
            )
            if not close_message_id:
                await self.send_json(
                    {"type": "error", "message": "This conversation is already closed."}
                )
                return
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_system",
                    "message": close_message,
                    "message_id": close_message_id,
                    "status": "closed",
                },
            )

            self.chat_closed = True

            return

        # =================================================
        # STAFF MESSAGE
        # =================================================

        if action == "staff_message":

            if self.chat_role != "staff" or not await self.has_permission("change"):

                await self.send_json(
                    {
                        "type": "error",
                        "message": (
                            "Staff access required."
                        ),
                    }
                )

                return

            message_value = content.get(
                "message",
                "",
            )

            if not isinstance(
                message_value,
                str,
            ):

                await self.send_json(
                    {
                        "type": "error",
                        "message": (
                            "Invalid message."
                        ),
                    }
                )

                return

            message = (
                message_value.strip()
            )

            if len(message) > 2000 or len(message.encode("utf-8")) > 8000:

                await self.send_json(
                    {
                        "type": "error",
                        "message": (
                            "Message cannot exceed "
                            "2000 characters."
                        ),
                    }
                )

                return

            if not message:

                await self.send_json(
                    {
                        "type": "error",
                        "message": (
                            "Message cannot be empty."
                        ),
                    }
                )

                return

            if not await self.rate_limit(
                f"staff:{self.scope['user'].pk}",
                "message",
                30,
            ):
                await self.send_json(
                    {"type": "error", "message": "Message rate limit reached. Please wait and retry."}
                )
                return

            user = self.scope["user"]

            sender_name = (
                user.get_full_name()
                or user.username
                or "YD Cleaning Support"
            )

            try:
                message_record_id = await self.save_message(
                    conversation.id,
                    "staff",
                    sender_name,
                    message,
                    sender_id=user.pk,
                )
            except (PermissionError, ValueError) as exc:
                await self.send_json(
                    {"type": "error", "message": str(exc)}
                )
                return

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "sender_type": "staff",
                    "sender_name": sender_name,
                    "message": message,
                    "message_id": message_record_id,
                },
            )

            return

        # =================================================
        # CUSTOMER MESSAGE
        # =================================================

        if action in (
            "customer_message",
            "message",
        ):

            message_value = content.get(
                "message",
                "",
            )

            if not isinstance(
                message_value,
                str,
            ):

                await self.send_json(
                    {
                        "type": "error",
                        "message": (
                            "Invalid message."
                        ),
                    }
                )

                return

            message = (
                message_value.strip()
            )

            if len(message) > 2000 or len(message.encode("utf-8")) > 8000:

                await self.send_json(
                    {
                        "type": "error",
                        "message": (
                            "Message cannot exceed "
                            "2000 characters."
                        ),
                    }
                )

                return

            if not message:

                await self.send_json(
                    {
                        "type": "error",
                        "message": (
                            "Message cannot be empty."
                        ),
                    }
                )

                return

            sender_name = (
                conversation.name
                or "Website Visitor"
            )

            if not await self.rate_limit(
                f"customer:{conversation.session_key}",
                "message",
                20,
            ):
                await self.send_json(
                    {"type": "error", "message": "Message rate limit reached. Please wait and retry."}
                )
                return

            try:
                message_record_id = await self.save_message(
                    conversation.id,
                    "customer",
                    sender_name,
                    message,
                )
            except ValueError:
                await self.send_json(
                    {
                        "type": "chat_closed",
                        "success": False,
                        "message": "This conversation has been closed.",
                    }
                )
                return

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "sender_type": "customer",
                    "sender_name": sender_name,
                    "message": message,
                    "message_id": message_record_id,
                },
            )

            # -------------------------------------------------
            # Refresh authoritative conversation state.
            #
            # This ensures a staff takeover or close occurring
            # on another socket wins over stale in-memory state.
            # -------------------------------------------------

            conversation = (
                await self.get_customer_conversation(
                    conversation.id,
                    self.session_key,
                )
            )

            if not conversation:
                return

            if conversation.status == "closed":

                self.chat_closed = True

                await self.send_json(
                    {
                        "type": "chat_closed",
                        "success": False,
                        "message": (
                            "This conversation has been closed."
                        ),
                    }
                )

                return

            # -------------------------------------------------
            # AI is allowed to continue only when the current
            # authoritative conversation is still in AI mode.
            # -------------------------------------------------

            if conversation.mode == "ai":

                analysis = analyze_message(
                    message
                )

                faq_response = (
                    self.find_faq_response(
                        message
                    )
                )

                result = handle_message(
                    conversation,
                    message,
                    analysis,
                    faq_response=faq_response,
                )

                try:
                    await self.persist_workflow_result(
                        conversation.id,
                        result,
                        analysis,
                    )
                except ValueError:
                    await self.send_json(
                        {
                            "type": "error",
                            "message": "This conversation changed. Reconnect to continue.",
                        }
                    )
                    return
                except DatabaseError as exc:
                    logger.warning(
                        "Live-chat workflow persistence failed for conversation %s (%s).",
                        conversation.id,
                        type(exc).__name__,
                    )
                    await self.send_json(
                        {
                            "type": "error",
                            "message": "Your message was received, but chat processing is temporarily unavailable.",
                        }
                    )
                    return

                result_action = result.get(
                    "action"
                )

                # =================================================
                # HUMAN HANDOFF
                # =================================================

                if result_action == "request_human":

                    handoff_message = (
                        result.get("reply")
                        or (
                            "I’ll connect you with a team member "
                            "to help with this."
                        )
                    )

                    await self.handoff_to_human(
                        conversation.id,
                        handoff_message,
                    )

                    await self.send_bot_message(
                        handoff_message
                    )

                    return

                # =================================================
                # CREATE QUOTE
                # =================================================

                if result_action == "create_quote":

                    try:

                        conversation = (
                            await self.get_conversation(
                                conversation.id
                            )
                        )

                        if not conversation:

                            return

                        if conversation.status == "closed":

                            self.chat_closed = True
                            return

                        if conversation.mode != "ai":

                            return

                        result_state = (
                            result.get("state")
                            or {}
                        )

                        quote, created = (
                            await self.create_quote_from_chat(
                                conversation,
                                result_state,
                            )
                        )

                        bot_response = (
                            "Your quote request has been "
                            "submitted successfully. "
                            f"Your quote request number is "
                            f"#{quote.id}. "
                            "Our team will review the details "
                            "and contact you."
                        )

                        await self.mark_workflow_completed(
                            conversation.id,
                            result_state,
                            "quote",
                            quote.id,
                        )

                    except DatabaseError as exc:
                        logger.warning(
                            "Live chat quote persistence failed for conversation %s (%s).",
                            conversation.id,
                            type(exc).__name__,
                        )
                        await self.send_json(
                            {
                                "type": "error",
                                "message": "The quote could not be completed due to a temporary chat issue.",
                            }
                        )
                        return
                    except (ValueError, TypeError) as exc:

                        logger.warning(
                            "Live chat quote workflow failed "
                            "for conversation %s (%s).",
                            conversation.id,
                            type(exc).__name__,
                        )

                        bot_response = (
                            "I couldn't submit the quote request "
                            "with those details. I'll connect you "
                            "with our team so they can help."
                        )

                        await self.handoff_to_human(
                            conversation.id,
                            bot_response,
                        )

                        await self.send_bot_message(
                            bot_response
                        )

                    else:

                        await self.send_bot_message(
                            bot_response
                        )

                    return

                # =================================================
                # CREATE BOOKING
                # =================================================

                if result_action == "create_booking":

                    try:

                        conversation = (
                            await self.get_conversation(
                                conversation.id
                            )
                        )

                        if not conversation:

                            return

                        if conversation.status == "closed":

                            self.chat_closed = True
                            return

                        if conversation.mode != "ai":

                            return

                        result_state = (
                            result.get("state")
                            or {}
                        )

                        booking, created = (
                            await self.create_booking_from_chat(
                                conversation,
                                result_state,
                            )
                        )

                        bot_response = (
                            "Your booking request has been "
                            "submitted successfully. "
                            f"Booking request #{booking.id} "
                            "has been recorded. "
                            "Our team will confirm availability "
                            "and the final booking details."
                        )

                        await self.mark_workflow_completed(
                            conversation.id,
                            result_state,
                            "booking",
                            booking.id,
                        )

                    except DatabaseError as exc:
                        logger.warning(
                            "Live chat booking persistence failed for conversation %s (%s).",
                            conversation.id,
                            type(exc).__name__,
                        )
                        await self.send_json(
                            {
                                "type": "error",
                                "message": "The booking could not be completed due to a temporary chat issue.",
                            }
                        )
                        return
                    except (ValueError, TypeError) as exc:

                        logger.warning(
                            "Live chat booking workflow failed "
                            "for conversation %s (%s).",
                            conversation.id,
                            type(exc).__name__,
                        )

                        bot_response = (
                            "I couldn't submit the booking request "
                            "with those details. I'll connect you "
                            "with our team so they can help."
                        )

                        await self.handoff_to_human(
                            conversation.id,
                            bot_response,
                        )

                        await self.send_bot_message(
                            bot_response
                        )

                    else:

                        await self.send_bot_message(
                            bot_response
                        )

                    return

                # =================================================
                # NORMAL AI RESPONSE
                # =================================================

                if result.get("reply"):

                    await self.send_bot_message(
                        result["reply"]
                    )

            return

        # =================================================
        # UNKNOWN ACTION
        # =================================================

        await self.send_json(
            {
                "type": "error",
                "message": (
                    f"Unknown chat action: {action}"
                ),
            }
        )

    # =====================================================
    # START INACTIVITY MONITOR
    # =====================================================

    def start_inactivity_monitor(
        self,
    ):

        if self.inactivity_task:

            if not self.inactivity_task.done():
                return

        self.inactivity_task = (
            asyncio.create_task(
                self.monitor_inactivity()
            )
        )

    # =====================================================
    # BACKGROUND INACTIVITY MONITOR
    # =====================================================

    async def monitor_inactivity(
        self,
    ):

        try:

            while not self.chat_closed:

                await asyncio.sleep(
                    INACTIVITY_CHECK_INTERVAL_SECONDS
                )

                if not self.conversation_id:
                    continue

                conversation = (
                    await self.get_conversation(
                        self.conversation_id
                    )
                )

                if not conversation:

                    self.chat_closed = True
                    return

                if conversation.status == "closed":

                    self.chat_closed = True
                    return

                inactive = (
                    await self.check_inactivity(
                        conversation
                    )
                )

                if inactive:

                    self.chat_closed = True

                    if self.room_group_name:

                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                "type": (
                                    "chat_inactivity_closed"
                                ),
                                "message": (
                                    "This conversation was "
                                    "automatically closed because "
                                    "there was no activity for "
                                    f"{INACTIVITY_TIMEOUT_MINUTES} "
                                    "minutes."
                                ),
                                "status": "closed",
                            },
                        )

                    return

        except asyncio.CancelledError:

            raise

        except Exception:

            logger.exception(
                "Live chat inactivity monitor failed",
                extra={
                    "conversation_id": (
                        self.conversation_id
                    ),
                    "event": (
                        "inactivity_monitor"
                    ),
                },
            )

    # =====================================================
    # INACTIVITY CHECK
    # =====================================================

    @database_sync_to_async
    def check_inactivity(
        self,
        conversation,
    ):

        now = timezone.now()

        timeout = timedelta(
            minutes=INACTIVITY_TIMEOUT_MINUTES
        )

        with transaction.atomic():

            current = (
                LiveChatConversation.objects
                .select_for_update()
                .get(
                    id=conversation.id
                )
            )

            # -------------------------------------------------
            # IMPORTANT:
            #
            # A conversation already closed by staff/user is
            # NOT an inactivity closure.
            #
            # Returning False allows the normal closed-chat
            # handler to send the correct message.
            # -------------------------------------------------

            if current.status == "closed":

                return False

            # -------------------------------------------------
            # Re-read activity while holding the database lock.
            # -------------------------------------------------

            last_activity = (
                current.updated_at
                or current.created_at
            )

            if not last_activity:

                return False

            if now - last_activity < timeout:

                return False

            # -------------------------------------------------
            # Automatically close.
            # -------------------------------------------------

            current.status = "closed"
            current.mode = "closed"
            current.updated_at = now
            current.closed_at = now

            current.save(
                update_fields=[
                    "status",
                    "mode",
                    "updated_at",
                    "closed_at",
                ]
            )
            queue_dashboard_update(current.pk, "conversation.closed")

            # -------------------------------------------------
            # Create ONE system message inside the transaction.
            # -------------------------------------------------

            LiveChatMessage.objects.create(
                conversation=current,
                sender_type="system",
                sender_name="YD Cleaning Support",
                message=(
                    "This conversation was automatically "
                    "closed due to inactivity."
                ),
            )

            return True

    # =====================================================
    # DATABASE HELPERS
    # =====================================================

    # =====================================================
    # GET OR CREATE CUSTOMER CONVERSATION
    # =====================================================

    @database_sync_to_async
    def get_or_create_customer_conversation(
        self,
        session_key,
        name,
        email,
        phone,
    ):

        with transaction.atomic():

            conversation, created = (
                LiveChatConversation.objects
                .select_for_update()
                .get_or_create(
                    session_key=session_key,
                    defaults={
                        "name": (
                            name
                            or "Website Visitor"
                        ),
                        "email": email,
                        "phone": phone,
                        "status": "waiting",
                        "mode": "ai",
                        "intent": "unknown",
                        "lead_status": "none",
                        "conversation_state": {},
                    },
                )
            )

            if created:

                LiveChatMessage.objects.create(
                    conversation=conversation,
                    sender_type="system",
                    sender_name="YD Cleaning",
                    message=(
                        "You are connected to YD Commercial "
                        "Cleaning live chat."
                    ),
                )
                queue_dashboard_update(
                    conversation.pk,
                    "conversation.created",
                )

                return conversation

        # -------------------------------------------------
            if conversation.status == "closed":
                conversation.status = "waiting"
                conversation.mode = "ai"
                conversation.assigned_to = None
                conversation.closed_at = None
                conversation.updated_at = timezone.now()
                conversation.save(
                    update_fields=[
                        "status",
                        "mode",
                        "assigned_to",
                        "closed_at",
                        "updated_at",
                    ]
                )
                queue_dashboard_update(
                    conversation.pk,
                    "conversation.reopened",
                )

            changed_fields = []
            for field, value in (
                ("name", name),
                ("email", email),
                ("phone", phone),
            ):
                if value and getattr(conversation, field) != value:
                    setattr(conversation, field, value)
                    changed_fields.append(field)
            if changed_fields:
                conversation.updated_at = timezone.now()
                conversation.save(
                    update_fields=[*changed_fields, "updated_at"]
                )
                queue_dashboard_update(
                    conversation.pk,
                    "conversation.updated",
                )

            return conversation

    # =====================================================
    # GET CONVERSATION
    # =====================================================

    @database_sync_to_async
    def get_conversation(
        self,
        conversation_id,
    ):

        try:

            return (
                LiveChatConversation.objects
                .select_related(
                    "assigned_to"
                )
                .get(
                    id=conversation_id
                )
            )

        except LiveChatConversation.DoesNotExist:

            return None

    # =====================================================
    # GET CUSTOMER CONVERSATION
    # =====================================================

    @database_sync_to_async
    def get_customer_conversation(
        self,
        conversation_id,
        session_key,
    ):
        """
        Load a conversation only when its session key
        belongs to this customer socket.
        """

        try:

            return (
                LiveChatConversation.objects
                .get(
                    id=conversation_id,
                    session_key=session_key,
                )
            )

        except LiveChatConversation.DoesNotExist:

            return None

    # =====================================================
    # PERSIST WORKFLOW RESULT
    # =====================================================

    @database_sync_to_async
    def persist_workflow_result(
        self,
        conversation_id,
        result,
        analysis,
    ):

        with transaction.atomic():
            conversation = (
                LiveChatConversation.objects.select_for_update().get(
                    id=conversation_id
                )
            )
            if conversation.status == "closed" or conversation.mode != "ai":
                raise ValueError("This conversation is no longer available to AI chat.")

            state = result.get("state") or {}
            customer = state.get("customer") or {}
            conversation.conversation_state = state

            intent = analysis.get("intent")
            if intent and conversation.intent == "unknown":
                conversation.intent = intent

            service = analysis.get("service")
            if service and not conversation.service:
                conversation.service = service

            if customer.get("name") and not conversation.name:
                conversation.name = customer["name"][:150]
            if customer.get("email"):
                conversation.email = customer["email"][:254]
            if customer.get("phone"):
                conversation.phone = customer["phone"][:30]

            if result.get("state_updated"):
                workflow_type = state.get("workflow", {}).get("type")
                if workflow_type in {"quote", "booking"}:
                    conversation.lead_status = "collecting"

            conversation.save(
                update_fields=[
                    "conversation_state",
                    "intent",
                    "service",
                    "name",
                    "email",
                    "phone",
                    "lead_status",
                    "updated_at",
                ]
            )
            queue_dashboard_update(
                conversation.pk,
                "conversation.updated",
            )

    # =====================================================
    # CREATE QUOTE FROM CHAT
    # =====================================================

    @database_sync_to_async
    def create_quote_from_chat(
        self,
        conversation,
        state,
    ):
        with transaction.atomic():
            current = LiveChatConversation.objects.select_for_update().get(
                pk=conversation.pk
            )
            if current.status == "closed" or current.mode != "ai":
                raise ValueError("This conversation is no longer available to AI chat.")
            return create_confirmed_quote(current, state)

    # =====================================================
    # CREATE BOOKING FROM CHAT
    # =====================================================

    @database_sync_to_async
    def create_booking_from_chat(
        self,
        conversation,
        state,
    ):
        with transaction.atomic():
            current = LiveChatConversation.objects.select_for_update().get(
                pk=conversation.pk
            )
            if current.status == "closed" or current.mode != "ai":
                raise ValueError("This conversation is no longer available to AI chat.")
            return create_confirmed_booking(current, state)

    # =====================================================
    # MARK WORKFLOW COMPLETED
    # =====================================================

     # =====================================================
    # MARK WORKFLOW COMPLETED
    # =====================================================

    @database_sync_to_async
    def mark_workflow_completed(
        self,
        conversation_id,
        state,
        workflow_type,
        record_id,
    ):

        with transaction.atomic():
            conversation = LiveChatConversation.objects.select_for_update().get(
                id=conversation_id
            )
            if conversation.status == "closed" or conversation.mode != "ai":
                raise ValueError("This conversation is no longer available to AI chat.")

            new_state = dict(state or {})

        # -------------------------------------------------
        # Keep customer details for future conversations,
        # but clear the completed workflow so a new quote
        # or booking starts fresh.
        # -------------------------------------------------

            customer_state = dict(new_state.get("customer") or {})

            new_state["customer"] = customer_state

            new_state["quote"] = {}
            new_state["booking"] = {}

            new_state["workflow"] = {
                "type": "none",
                "step": "idle",
                "awaiting_confirmation": False,
            }

            conversation.conversation_state = new_state

            conversation.lead_status = (
                "qualified" if workflow_type == "quote" else "converted"
            )

            conversation.save(
                update_fields=[
                    "conversation_state",
                    "lead_status",
                    "updated_at",
                ]
            )
        
    # =====================================================
    # HANDOFF TO HUMAN
    # =====================================================

    @database_sync_to_async
    def handoff_to_human(
        self,
        conversation_id,
        message,
    ):

        with transaction.atomic():
            conversation = LiveChatConversation.objects.select_for_update().get(
                id=conversation_id
            )
            if conversation.status == "closed" or conversation.mode in {
                "human",
                "waiting_for_human",
            }:
                return

            conversation.mode = "waiting_for_human"
            conversation.status = "waiting"
            if conversation.lead_status in {"collecting", "qualified"}:
                conversation.lead_status = "qualified"
            conversation.assigned_to = None
            conversation.updated_at = timezone.now()
            conversation.save(
                update_fields=[
                    "mode",
                    "status",
                    "lead_status",
                    "assigned_to",
                    "updated_at",
                ]
            )
            queue_dashboard_update(
                conversation.pk,
                "conversation.waiting",
            )

    # =====================================================
    # SEND BOT MESSAGE
    # =====================================================

    async def send_bot_message(
        self,
        message,
    ):

        # -------------------------------------------------
        # Do not send bot responses into a closed conversation.
        # -------------------------------------------------

        conversation = (
            await self.get_conversation(
                self.conversation.id
            )
        )

        if not conversation:
            return

        if conversation.status == "closed":

            self.chat_closed = True
            return

        if conversation.mode != "ai":
            return
        try:
            message_record_id = await self.save_message(
                conversation.id,
                "bot",
                "YD Cleaning Assistant",
                message,
            )
        except ValueError:
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "sender_type": "bot",
                "sender_name": (
                    "YD Cleaning Assistant"
                ),
                "message": message,
                "message_id": message_record_id,
            },
        )

    # =====================================================
    # LEGACY / COMPATIBILITY STATE UPDATE
    # =====================================================

    @database_sync_to_async
    @transaction.atomic
    def update_conversation_state(
        self,
        conversation_id,
        analysis,
    ):

        conversation = LiveChatConversation.objects.select_for_update().get(
            id=conversation_id
        )

        state = dict(
            conversation.conversation_state
            or {}
        )

        state.setdefault(
            "schema_version",
            1,
        )

        intent = analysis.get(
            "intent"
        )

        if (
            conversation.intent == "unknown"
            and intent
        ):

            conversation.intent = (
                intent
            )

        service = analysis.get(
            "service"
        )

        if (
            service
            and not conversation.service
        ):

            conversation.service = service

        entities = (
            analysis.get("entities")
            or {}
        )

        if entities:

            quote_state = dict(
                state.get("quote")
                or {}
            )

            booking_state = dict(
                state.get("booking")
                or {}
            )

            customer_state = dict(
                state.get("customer")
                or {}
            )

            # -------------------------------------------------
            # Quote fields.
            # -------------------------------------------------

            for key in (
                "property_type",
                "approximate_size",
                "frequency",
                "suburb",
            ):

                if (
                    entities.get(key)
                    and not quote_state.get(key)
                ):

                    quote_state[key] = (
                        _property_type(
                            entities[key]
                        )
                        if key == "property_type"
                        else entities[key]
                    )

            # -------------------------------------------------
            # Customer contact fields.
            # -------------------------------------------------

            for key in (
                "email",
                "phone",
            ):

                if (
                    entities.get(key)
                    and not customer_state.get(key)
                ):

                    customer_state[key] = (
                        entities[key]
                    )

            if quote_state:

                state["quote"] = (
                    quote_state
                )

            if booking_state:

                state["booking"] = (
                    booking_state
                )

            if customer_state:

                state["customer"] = (
                    customer_state
                )

        conversation.conversation_state = state
        conversation.save(
            update_fields=[
                "intent",
                "service",
                "conversation_state",
            ]
        )
        queue_dashboard_update(
            conversation.pk,
            "conversation.updated",
        )

    # =====================================================
    # SAVE MESSAGE
    # =====================================================

    @database_sync_to_async
    def save_message(
        self,
        conversation_id,
        sender_type,
        sender_name,
        message,
        sender_id=None,
    ):
        from notifications.utils import notify_admins

        with transaction.atomic():
            conversation = (
                LiveChatConversation.objects.select_for_update().get(
                    id=conversation_id
                )
            )
            if conversation.status == "closed":
                raise ValueError("This conversation is closed.")
            if (
                sender_type == "staff"
                and conversation.assigned_to_id != sender_id
            ):
                raise PermissionError(
                    "This conversation is not assigned to this staff member."
                )
            if sender_type == "bot" and conversation.mode != "ai":
                raise ValueError("AI responses are no longer enabled for this conversation.")

            saved_message = LiveChatMessage.objects.create(
                conversation=conversation,
                sender_type=sender_type,
                sender_name=sender_name,
                message=message,
            )
            conversation.updated_at = timezone.now()
            conversation.save(update_fields=["updated_at"])
            queue_dashboard_update(
                conversation.pk,
                "conversation.message",
            )

            if sender_type == "customer":
                notify_admins(
                    "New Website Chat Message",
                    f"A visitor sent a message in live chat #{conversation.pk}.",
                    "support",
                    "/dashboard/support/",
                )
            return saved_message.pk

    # =====================================================
    # TAKEOVER
    # =====================================================

    @database_sync_to_async
    def takeover_conversation(
        self,
        conversation_id,
        user_id,
    ):

        with transaction.atomic():
            conversation = LiveChatConversation.objects.select_for_update().get(
                id=conversation_id
            )
            if conversation.status == "closed":
                return False
            if (
                conversation.status == "active"
                and conversation.assigned_to_id not in {None, user_id}
            ):
                return False
            user = User.objects.get(id=user_id)
            conversation.status = "active"
            conversation.mode = "human"
            conversation.assigned_to = user
            conversation.updated_at = timezone.now()
            conversation.save(
                update_fields=[
                    "status",
                    "mode",
                    "assigned_to",
                    "updated_at",
                ]
            )
            system_message = LiveChatMessage.objects.create(
                conversation=conversation,
                sender_type="system",
                sender_name="YD Cleaning Support",
                message=(
                    f"{user.get_full_name() or user.username} "
                    "has taken over this conversation."
                ),
            )
            from dashboard.models import ActivityLog

            ActivityLog.objects.create(
                user=user,
                action_type="system",
                title="Live Chat Taken Over",
                description=f"Conversation #{conversation.pk} assigned to staff.",
            )
            queue_dashboard_update(
                conversation.pk,
                "conversation.assigned",
            )
            return system_message.pk

    # =====================================================
    # CLOSE CONVERSATION
    # =====================================================

    @database_sync_to_async
    def close_conversation(
        self,
        conversation_id,
        sender_name,
        message,
    ):

        with transaction.atomic():
            conversation = LiveChatConversation.objects.select_for_update().get(
                id=conversation_id
            )
            if conversation.status == "closed":
                return None
            now = timezone.now()
            conversation.status = "closed"
            conversation.mode = "closed"
            conversation.closed_at = now
            conversation.updated_at = now
            conversation.save(
                update_fields=[
                    "status",
                    "mode",
                    "closed_at",
                    "updated_at",
                ]
            )
            system_message = LiveChatMessage.objects.create(
                conversation=conversation,
                sender_type="system",
                sender_name=sender_name[:150],
                message=message[:2000],
            )
            user = getattr(self, "scope", {}).get("user")
            from dashboard.models import ActivityLog

            ActivityLog.objects.create(
                user=user if getattr(user, "is_authenticated", False) else None,
                action_type="system",
                title="Live Chat Closed",
                description=f"Conversation #{conversation.pk} closed by staff.",
            )
            queue_dashboard_update(
                conversation.pk,
                "conversation.closed",
            )
            return system_message.pk

    # =====================================================
    # FAQ
    # =====================================================

    def find_faq_response(
        self,
        message,
    ):

        normalized = (
            message
            .lower()
            .strip()
        )

        if not normalized:
            return None

        # =================================================
        # GREETINGS
        # =================================================

        greetings = {
            "hi",
            "hello",
            "hey",
            "hiya",
            "good morning",
            "good afternoon",
            "good evening",
            "morning",
            "afternoon",
            "evening",
        }

        if normalized in greetings:

            return (
                "Hi! 👋 Welcome to YD Commercial Cleaning. "
                "How can we help you today? You can ask me about "
                "our cleaning services, quotes, bookings, or "
                "service areas."
            )

        # =================================================
        # THANK YOU
        # =================================================

        if normalized in {
            "thanks",
            "thank you",
            "thankyou",
            "thx",
        }:

            return (
                "You're very welcome! 😊 If you have any questions "
                "about our cleaning services, pricing or bookings, "
                "I'm happy to help."
            )

        # =================================================
        # GOODBYE
        # =================================================

        if normalized in {
            "bye",
            "goodbye",
            "see you",
            "see ya",
        }:

            return (
                "Thanks for contacting YD Commercial Cleaning! 👋 "
                "Have a great day. If you need cleaning services "
                "in the future, we're always happy to help."
            )

        # =================================================
        # FAQ CATEGORY KEYWORDS
        # =================================================

        keyword_map = {

            "services": [
                "service",
                "services",
                "cleaning service",
                "cleaning services",
                "what do you clean",
                "what cleaning",
            ],

            "areas": [
                "area",
                "areas",
                "suburb",
                "suburbs",
                "where do you service",
                "where do you clean",
            ],

            "quote": [
                "quote",
                "quotation",
                "price",
                "pricing",
                "cost",
                "how much",
                "estimate",
            ],

            "booking": [
                "book",
                "booking",
                "appointment",
                "schedule",
                "reserve",
                "reservation",
            ],

            "bond": [
                "bond",
                "end of lease",
                "end-of-lease",
                "lease",
                "move out",
                "moving out",
            ],

            "commercial": [
                "commercial",
                "office",
                "business",
                "workplace",
            ],

            "oven": [
                "oven",
                "oven cleaning",
            ],

            "carpet": [
                "carpet",
                "carpet cleaning",
            ],

            "window": [
                "window",
                "windows",
                "window cleaning",
            ],

            "contact": [
                "contact",
                "phone",
                "email",
                "call",
                "speak to someone",
                "talk to someone",
                "support",
            ],
        }

        # =================================================
        # FIND FAQ RESPONSE
        # =================================================

        for faq_key, keywords in (
            keyword_map.items()
        ):

            for keyword in keywords:

                if keyword in normalized:

                    faq = FAQ_RESPONSES.get(
                        faq_key
                    )

                    if faq:

                        return faq.get(
                            "answer"
                        )

        # =================================================
        # ORIGINAL FAQ KEY MATCH
        # =================================================

        if normalized in FAQ_RESPONSES:

            faq = FAQ_RESPONSES[
                normalized
            ]

            return faq.get(
                "answer"
            )

        # =================================================
        # ORIGINAL GENERIC FAQ MATCHING
        # =================================================

        for key, faq in (
            FAQ_RESPONSES.items()
        ):

            key_normalized = (
                str(key)
                .lower()
                .replace(
                    "-",
                    " ",
                )
                .replace(
                    "_",
                    " ",
                )
            )

            keywords = (
                key_normalized
                .split()
            )

            if not keywords:
                continue

            matched = sum(
                1
                for keyword in keywords
                if keyword in normalized
            )

            if matched >= max(
                1,
                len(keywords) // 2,
            ):

                return faq.get(
                    "answer"
                )

        return None

    # =====================================================
    # CHANNEL GROUP MESSAGE HANDLER
    # =====================================================

    async def chat_message(
        self,
        event,
    ):

        await self.send_json(
            {
                "type": "message",
                "sender_type": event.get(
                    "sender_type",
                    "system",
                ),
                "sender_name": event.get(
                    "sender_name",
                    "System",
                ),
                "message": event.get(
                    "message",
                    "",
                ),
                "message_id": event.get("message_id"),
            }
        )

    async def dashboard_update(self, event):
        if not await self.has_permission("view"):
            await self.channel_layer.group_discard(
                DASHBOARD_GROUP,
                self.channel_name,
            )
            self.dashboard_group_joined = False
            return
        await self.send_json(
            {
                "type": "dashboard_update",
                "event": event.get("event", "conversation.updated"),
                "conversation": event.get("conversation"),
                "conversation_id": event.get("conversation_id"),
                "occurred_at": event.get("occurred_at"),
            }
        )

    # =====================================================
    # SYSTEM MESSAGE HANDLER
    # =====================================================

    async def chat_system(
        self,
        event,
    ):

        await self.send_json(
            {
                "type": "system",
                "message": event.get(
                    "message",
                    "",
                ),
                "status": event.get(
                    "status",
                ),
                "message_id": event.get("message_id"),
                "assigned_to_id": event.get("assigned_to_id"),
                "assigned_to": event.get("assigned_to"),
            }
        )

        # -------------------------------------------------
        # Only an active status means staff joined.
        # -------------------------------------------------

        if event.get(
            "status"
        ) == "active":

            await self.send_json(
                {
                    "type": "staff_joined",
                    "status": "active",
                }
            )

    # =====================================================
    # AUTOMATIC INACTIVITY CLOSE HANDLER
    # =====================================================

    async def chat_inactivity_closed(
        self,
        event,
    ):

        message = event.get(
            "message",
            (
                "This conversation was automatically "
                "closed due to inactivity."
            ),
        )

        self.chat_closed = True

        await self.send_json(
            {
                "type": "chat_closed",
                "success": False,
                "reason": "inactivity",
                "message": message,
            }
        )

        await self.send_json(
            {
                "type": "system",
                "message": message,
                "status": "closed",
            }
        )