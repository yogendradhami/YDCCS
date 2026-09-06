import asyncio
import json
import logging
from datetime import timedelta

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

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
        self.room_group_name = None

        self.inactivity_task = None
        self.chat_closed = False

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
                pass

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
                pass

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

                session_key = str(
                    content.get(
                        "session_key",
                        "",
                    )
                ).strip()

                if not self.is_valid_session_key(
                    session_key
                ):

                    await self.send_json(
                        {
                            "type": "error",
                            "message": (
                                "Chat session could not "
                                "be identified."
                            ),
                        }
                    )

                    return

                self.session_key = (
                    session_key
                )

                conversation = (
                    await self.get_or_create_customer_conversation(
                        session_key=session_key,
                        name=str(
                            content.get(
                                "name",
                                "Website Visitor",
                            )
                        ).strip()
                        or "Website Visitor",
                        email=str(
                            content.get(
                                "email",
                                "",
                            )
                        ).strip(),
                        phone=str(
                            content.get(
                                "phone",
                                "",
                            )
                        ).strip(),
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

                if not self.is_staff:

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

            # -------------------------------------------------
            # Set current conversation.
            # -------------------------------------------------

            self.conversation = (
                conversation
            )

            self.conversation_id = (
                conversation.id
            )

            self.room_group_name = (
                f"live_chat_{conversation.id}"
            )

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

        # -------------------------------------------------
        # Staff can access conversations by ID.
        # Customers must prove session ownership.
        # -------------------------------------------------

        if self.is_staff:

            conversation = (
                await self.get_conversation(
                    conversation_id
                )
            )

        else:

            session_key = str(
                content.get(
                    "session_key",
                    "",
                )
            ).strip()

            if session_key != getattr(
                self,
                "session_key",
                None,
            ):

                await self.send_json(
                    {
                        "type": "error",
                        "message": (
                            "This conversation is not "
                            "available to this chat session."
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

        # =================================================
        # STAFF TAKEOVER
        # =================================================

        if action == "staff_takeover":

            if not self.is_staff:

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

            await self.takeover_conversation(
                conversation.id,
                user.id,
            )

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_system",
                    "message": (
                        f"{user.get_full_name() or user.username} "
                        "has taken over this conversation."
                    ),
                    "status": "active",
                },
            )

            return

        # =================================================
        # STAFF CLOSE
        # =================================================

        if action == "staff_close":

            if not self.is_staff:

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

            await self.close_conversation(
                conversation.id,
                sender_name=(
                    user.get_full_name()
                    or user.username
                    or "YD Cleaning Support"
                ),
                message=close_message,
            )

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_system",
                    "message": close_message,
                    "status": "closed",
                },
            )

            self.chat_closed = True

            return

        # =================================================
        # STAFF MESSAGE
        # =================================================

        if action == "staff_message":

            if not self.is_staff:

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

            if len(message) > 2000:

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

            user = self.scope["user"]

            sender_name = (
                user.get_full_name()
                or user.username
                or "YD Cleaning Support"
            )

            await self.save_message(
                conversation.id,
                "staff",
                sender_name,
                message,
            )

            await self.touch_conversation(
                conversation.id
            )

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "sender_type": "staff",
                    "sender_name": sender_name,
                    "message": message,
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

            if len(message) > 2000:

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

            await self.save_message(
                conversation.id,
                "customer",
                sender_name,
                message,
            )

            await self.touch_conversation(
                conversation.id
            )

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "sender_type": "customer",
                    "sender_name": sender_name,
                    "message": message,
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

                await self.persist_workflow_result(
                    conversation.id,
                    result,
                    analysis,
                )

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

                    except (
                        ValueError,
                        TypeError,
                    ) as exc:

                        logger.warning(
                            "Live chat quote workflow failed "
                            "for conversation %s: %s",
                            conversation.id,
                            exc,
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

                    except (
                        ValueError,
                        TypeError,
                    ) as exc:

                        logger.warning(
                            "Live chat booking workflow failed "
                            "for conversation %s: %s",
                            conversation.id,
                            exc,
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

            current.save(
                update_fields=[
                    "status",
                    "mode",
                    "updated_at",
                ]
            )

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

                return conversation

        # -------------------------------------------------
        # Existing conversation.
        # -------------------------------------------------

        if conversation:

            # -------------------------------------------------
            # Reopen closed browser-session conversation.
            # -------------------------------------------------

            if conversation.status == "closed":

                conversation.status = "waiting"
                conversation.mode = "ai"
                conversation.assigned_to = None
                conversation.updated_at = timezone.now()

                conversation.save(
                    update_fields=[
                        "status",
                        "mode",
                        "assigned_to",
                        "updated_at",
                    ]
                )

            # -------------------------------------------------
            # Update visitor details when available.
            # -------------------------------------------------

            changed = False

            if (
                name
                and conversation.name != name
            ):

                conversation.name = name
                changed = True

            if (
                email
                and conversation.email != email
            ):

                conversation.email = email
                changed = True

            if (
                phone
                and conversation.phone != phone
            ):

                conversation.phone = phone
                changed = True

            if changed:

                conversation.updated_at = (
                    timezone.now()
                )

                conversation.save(
                    update_fields=[
                        "name",
                        "email",
                        "phone",
                        "updated_at",
                    ]
                )

            return conversation

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

        conversation = (
            LiveChatConversation.objects.get(
                id=conversation_id
            )
        )

        state = (
            result.get("state")
            or {}
        )

        customer = (
            state.get("customer")
            or {}
        )

        conversation.conversation_state = (
            state
        )

        intent = analysis.get(
            "intent"
        )

        if (
            intent
            and conversation.intent == "unknown"
        ):

            conversation.intent = intent

        service = analysis.get(
            "service"
        )

        if (
            service
            and not conversation.service
        ):

            conversation.service = service

        if (
            customer.get("name")
            and not conversation.name
        ):

            conversation.name = (
                customer["name"][:150]
            )

        if customer.get("email"):

            conversation.email = (
                customer["email"][:254]
            )

        if customer.get("phone"):

            conversation.phone = (
                customer["phone"][:30]
            )

        if result.get(
            "state_updated"
        ):

            workflow_type = (
                state
                .get("workflow", {})
                .get("type")
            )

            if workflow_type in {
                "quote",
                "booking",
            }:

                conversation.lead_status = (
                    "collecting"
                )

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

    # =====================================================
    # CREATE QUOTE FROM CHAT
    # =====================================================

    @database_sync_to_async
    def create_quote_from_chat(
        self,
        conversation,
        state,
    ):

        return create_confirmed_quote(
            conversation,
            state,
        )

    # =====================================================
    # CREATE BOOKING FROM CHAT
    # =====================================================

    @database_sync_to_async
    def create_booking_from_chat(
        self,
        conversation,
        state,
    ):

        return create_confirmed_booking(
            conversation,
            state,
        )

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

        conversation = (
            LiveChatConversation.objects.get(
                id=conversation_id
            )
        )

        new_state = dict(
            state or {}
        )

        workflow = dict(
            new_state.get("workflow")
            or {}
        )

        workflow.update(
            {
                "type": workflow_type,
                "step": "submitted",
                "awaiting_confirmation": False,
                "record_id": record_id,
            }
        )

        new_state["workflow"] = (
            workflow
        )

        conversation.conversation_state = (
            new_state
        )

        conversation.lead_status = (
            "qualified"
            if workflow_type == "quote"
            else "converted"
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

        conversation = (
            LiveChatConversation.objects.get(
                id=conversation_id
            )
        )

        if conversation.mode not in {
            "human",
            "waiting_for_human",
        }:

            conversation.mode = (
                "waiting_for_human"
            )

            conversation.status = (
                "waiting"
            )

            conversation.lead_status = (
                "qualified"
                if conversation.lead_status
                in {
                    "collecting",
                    "qualified",
                }
                else conversation.lead_status
            )

            conversation.assigned_to = None
            conversation.updated_at = (
                timezone.now()
            )

            conversation.save(
                update_fields=[
                    "mode",
                    "status",
                    "lead_status",
                    "assigned_to",
                    "updated_at",
                ]
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

        await self.save_message(
            conversation.id,
            "bot",
            "YD Cleaning Assistant",
            message,
        )

        await self.touch_conversation(
            conversation.id
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "sender_type": "bot",
                "sender_name": (
                    "YD Cleaning Assistant"
                ),
                "message": message,
            },
        )

    # =====================================================
    # LEGACY / COMPATIBILITY STATE UPDATE
    # =====================================================

    @database_sync_to_async
    def update_conversation_state(
        self,
        conversation_id,
        analysis,
    ):

        conversation = (
            LiveChatConversation.objects.get(
                id=conversation_id
            )
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

        conversation.conversation_state = (
            state
        )

        conversation.save(
            update_fields=[
                "intent",
                "service",
                "conversation_state",
            ]
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
    ):

        conversation = (
            LiveChatConversation.objects.get(
                id=conversation_id
            )
        )

        LiveChatMessage.objects.create(
            conversation=conversation,
            sender_type=sender_type,
            sender_name=sender_name,
            message=message,
        )

    # =====================================================
    # TOUCH CONVERSATION
    # =====================================================

    @database_sync_to_async
    def touch_conversation(
        self,
        conversation_id,
    ):

        conversation = (
            LiveChatConversation.objects.get(
                id=conversation_id
            )
        )

        # -------------------------------------------------
        # Never update a closed conversation.
        # -------------------------------------------------

        if conversation.status == "closed":
            return

        conversation.updated_at = (
            timezone.now()
        )

        conversation.save(
            update_fields=[
                "updated_at",
            ]
        )

    # =====================================================
    # TAKEOVER
    # =====================================================

    @database_sync_to_async
    def takeover_conversation(
        self,
        conversation_id,
        user_id,
    ):

        conversation = (
            LiveChatConversation.objects.get(
                id=conversation_id
            )
        )

        user = User.objects.get(
            id=user_id
        )

        conversation.status = (
            "active"
        )

        conversation.mode = (
            "human"
        )

        conversation.assigned_to = (
            user
        )

        conversation.updated_at = (
            timezone.now()
        )

        conversation.save(
            update_fields=[
                "status",
                "mode",
                "assigned_to",
                "updated_at",
            ]
        )

        # -------------------------------------------------
        # Intentionally no duplicate system DB message.
        # The group event handles the notification.
        # -------------------------------------------------

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

        conversation = (
            LiveChatConversation.objects.get(
                id=conversation_id
            )
        )

        conversation.status = (
            "closed"
        )

        conversation.mode = (
            "closed"
        )

        conversation.updated_at = (
            timezone.now()
        )

        conversation.save(
            update_fields=[
                "status",
                "mode",
                "updated_at",
            ]
        )

        # -------------------------------------------------
        # Create ONE system message in the database.
        # -------------------------------------------------

        LiveChatMessage.objects.create(
            conversation=conversation,
            sender_type="system",
            sender_name=sender_name,
            message=message,
        )

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