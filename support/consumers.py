import asyncio
from datetime import timedelta

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from .chat_faq import FAQ_RESPONSES
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
# 60 seconds is enough and avoids unnecessary database load.
INACTIVITY_CHECK_INTERVAL_SECONDS = 60


class LiveChatConsumer(AsyncJsonWebsocketConsumer):

    # =====================================================
    # CONNECT
    # =====================================================

    async def connect(self):

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

        user = self.scope.get("user")

        self.is_staff = bool(
            user
            and user.is_authenticated
            and user.is_staff
        )

        await self.send_json(
            {
                "type": "connection",
                "success": True,
                "message": "Live chat connected.",
            }
        )

    # =====================================================
    # DISCONNECT
    # =====================================================

    async def disconnect(self, close_code):

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

        if not isinstance(content, dict):

            await self.send_json(
                {
                    "type": "error",
                    "message": "Invalid WebSocket request.",
                }
            )

            return

        action = content.get(
            "action",
            "",
        )

        conversation_id = content.get(
            "conversation_id"
        )

        if conversation_id is not None:
            try:
                conversation_id = int(conversation_id)
            except (TypeError, ValueError):
                await self.send_json(
                    {
                        "type": "error",
                        "message": "Invalid conversation ID.",
                    }
                )
                return

        # =================================================
        # UPDATE STAFF STATUS
        # =================================================

        user = self.scope.get("user")

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

                if not session_key:

                    await self.send_json(
                        {
                            "type": "error",
                            "message": (
                                "Chat session could not be "
                                "identified."
                            ),
                        }
                    )

                    return

                self.session_key = session_key

                conversation = await self.get_or_create_customer_conversation(
                    session_key=session_key,
                    name=str(
                        content.get(
                            "name",
                            "Website Visitor",
                        )
                    ).strip() or "Website Visitor",
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

                conversation_id = content.get(
                    "conversation_id"
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

                conversation = await self.get_conversation(
                    conversation_id
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

            self.conversation = conversation

            self.conversation_id = conversation.id

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
                            f"for {INACTIVITY_TIMEOUT_MINUTES} minutes."
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
                    "conversation_id": conversation.id,
                    "status": conversation.status,
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

            conversation_id = self.conversation_id

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

        conversation = await self.get_conversation(
            conversation_id
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

        self.conversation = conversation

        self.conversation_id = conversation.id

        if not self.is_staff:
            session_key = str(content.get("session_key", "")).strip()
            if session_key != self.session_key:
                await self.send_json(
                    {
                        "type": "error",
                        "message": "This conversation is not available to this chat session.",
                    }
                )
                return

        # =================================================
        # IMPORTANT:
        #
        # INACTIVITY CHECK MUST HAPPEN BEFORE PROCESSING
        # ANY MESSAGE OR ACTION.
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
                        f"for {INACTIVITY_TIMEOUT_MINUTES} minutes."
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

            await self.close_conversation(
                conversation.id,
                sender_name=(
                    user.get_full_name()
                    or user.username
                    or "YD Cleaning Support"
                ),
                message=(
                    "This conversation was closed by "
                    f"{user.get_full_name() or user.username}."
                ),
            )

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_system",
                    "message": (
                        "This conversation was closed by "
                        f"{user.get_full_name() or user.username}."
                    ),
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

            message = str(
                content.get(
                    "message",
                    "",
                )
            ).strip()

            if len(message) > 2000:
                await self.send_json(
                    {
                        "type": "error",
                        "message": "Message cannot exceed 2000 characters.",
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

            message = str(
                content.get(
                    "message",
                    "",
                )
            ).strip()

            if len(message) > 2000:
                await self.send_json(
                    {
                        "type": "error",
                        "message": "Message cannot exceed 2000 characters.",
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

            sender_name = conversation.name or "Website Visitor"

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

            # =============================================
            # FAQ / BOT RESPONSE
            # =============================================

            bot_response = self.find_faq_response(
                message
            )

            if bot_response:

                await self.save_message(
                    conversation.id,
                    "bot",
                    "YD Cleaning Assistant",
                    bot_response,
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
                        "message": bot_response,
                    },
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

    def start_inactivity_monitor(self):

        # -------------------------------------------------
        # Do not create duplicate monitoring tasks.
        # -------------------------------------------------

        if self.inactivity_task:

            if not self.inactivity_task.done():

                return

        self.inactivity_task = asyncio.create_task(
            self.monitor_inactivity()
        )

    # =====================================================
    # BACKGROUND INACTIVITY MONITOR
    # =====================================================

    async def monitor_inactivity(self):

        try:

            while not self.chat_closed:

                await asyncio.sleep(
                    INACTIVITY_CHECK_INTERVAL_SECONDS
                )

                # -----------------------------------------
                # No conversation = nothing to monitor.
                # -----------------------------------------

                if not self.conversation_id:

                    continue

                conversation = await self.get_conversation(
                    self.conversation_id
                )

                if not conversation:

                    self.chat_closed = True

                    return

                # -----------------------------------------
                # Already closed.
                # -----------------------------------------

                if conversation.status == "closed":

                    self.chat_closed = True

                    return

                # -----------------------------------------
                # Check inactivity.
                # -----------------------------------------

                inactive = await self.check_inactivity(
                    conversation
                )

                if inactive:

                    self.chat_closed = True

                    # -------------------------------------
                    # Notify everyone connected to this
                    # conversation.
                    # -------------------------------------

                    if self.room_group_name:

                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                "type": "chat_inactivity_closed",
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

        except Exception as error:

            # Do not kill the WebSocket because of a monitor
            # error. Log it and stop the monitor safely.

            print(
                "Live chat inactivity monitor error:",
                error,
            )

    # =====================================================
    # INACTIVITY CHECK
    # =====================================================

    @database_sync_to_async
    def check_inactivity(
        self,
        conversation,
    ):

        # -------------------------------------------------
        # Already closed.
        # -------------------------------------------------

        if conversation.status == "closed":

            return True

        now = timezone.now()

        last_activity = (
            conversation.updated_at
        )

        if not last_activity:

            last_activity = (
                conversation.created_at
            )

        if not last_activity:

            return False

        timeout = timedelta(
            minutes=INACTIVITY_TIMEOUT_MINUTES
        )

        inactive_for = (
            now - last_activity
        )

        # -------------------------------------------------
        # Still active.
        # -------------------------------------------------

        if inactive_for < timeout:

            return False

        # -------------------------------------------------
        # Automatically close.
        # -------------------------------------------------

        with transaction.atomic():
            current = LiveChatConversation.objects.select_for_update().get(
                id=conversation.id
            )

            if current.status == "closed":
                return True

            current.status = "closed"
            current.updated_at = now
            current.save(update_fields=["status", "updated_at"])

        # -------------------------------------------------
        # Create ONE system message.
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
                LiveChatConversation.objects.select_for_update().get_or_create(
                    session_key=session_key,
                    defaults={
                        "name": name or "Website Visitor",
                        "email": email,
                        "phone": phone,
                        "status": "waiting",
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

            # Keep one conversation per browser session across refreshes.
            if conversation.status == "closed":
                conversation.status = "waiting"
                conversation.assigned_to = None
                conversation.updated_at = timezone.now()
                conversation.save(
                    update_fields=["status", "assigned_to", "updated_at"]
                )

            # Update visitor details when available.

            changed = False

            if name and conversation.name != name:

                conversation.name = name

                changed = True

            if email and conversation.email != email:

                conversation.email = email

                changed = True

            if phone and conversation.phone != phone:

                conversation.phone = phone

                changed = True

            if changed:

                conversation.updated_at = timezone.now()

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



    @database_sync_to_async
    def get_conversation(
        self,
        conversation_id,
    ):

        try:

            return (
                LiveChatConversation.objects
                .select_related("assigned_to")
                .get(
                    id=conversation_id
                )
            )

        except LiveChatConversation.DoesNotExist:

            return None

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

        conversation.updated_at = timezone.now()

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

        conversation.status = "active"

        conversation.assigned_to = user

        conversation.updated_at = timezone.now()

        conversation.save(
            update_fields=[
                "status",
                "assigned_to",
                "updated_at",
            ]
        )

        # -------------------------------------------------
        # NOTE:
        #
        # We intentionally DO NOT create the system message
        # here. The group event below sends it to connected
        # clients and avoids duplicate messages.
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

        conversation.status = "closed"

        conversation.updated_at = timezone.now()

        conversation.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        # -------------------------------------------------
        # Create ONE system message in database.
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

        # =====================================================
        # GREETINGS
        # =====================================================

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

        # =====================================================
        # THANK YOU
        # =====================================================

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

        # =====================================================
        # GOODBYE
        # =====================================================

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

        # =====================================================
        # FAQ CATEGORY KEYWORDS
        # =====================================================

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

        # =====================================================
        # FIND FAQ RESPONSE
        # =====================================================

        for faq_key, keywords in keyword_map.items():

            for keyword in keywords:

                if keyword in normalized:

                    faq = FAQ_RESPONSES.get(
                        faq_key
                    )

                    if faq:

                        return faq.get(
                            "answer"
                        )

        # =====================================================
        # ORIGINAL FAQ KEY MATCH
        # =====================================================

        if normalized in FAQ_RESPONSES:

            faq = FAQ_RESPONSES[
                normalized
            ]

            return faq.get(
                "answer"
            )

        # =====================================================
        # ORIGINAL GENERIC FAQ MATCHING
        # =====================================================

        for key, faq in FAQ_RESPONSES.items():

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

        if event.get("status"):

            await self.send_json(
                {
                    "type": "staff_joined",
                    "status": event.get(
                        "status"
                    ),
                }
            )

    # =====================================================
    # AUTOMATIC INACTIVITY CLOSE HANDLER
    # =====================================================

    async def chat_inactivity_closed(
        self,
        event,
    ):

        await self.send_json(
            {
                "type": "chat_closed",
                "success": False,
                "reason": "inactivity",
                "message": event.get(
                    "message",
                    (
                        "This conversation was automatically "
                        "closed due to inactivity."
                    ),
                ),
            }
        )

        await self.send_json(
            {
                "type": "system",
                "message": event.get(
                    "message",
                    (
                        "This conversation was automatically "
                        "closed due to inactivity."
                    ),
                ),
                "status": "closed",
            }
        )

        await self.send_json(
            {
                "type": "staff_joined",
                "status": "closed",
            }
        )