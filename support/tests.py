from asgiref.sync import async_to_sync
from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from unittest.mock import AsyncMock

from customers.models import Customer
from notifications.models import Notification

from .consumers import LiveChatConsumer
from .chat_intent import analyze_message, detect_intent, detect_service, detect_entities
from .chat_workflow import handle_message
from .models import LiveChatConversation, LiveChatMessage


class IntentDetectionTests(TestCase):
	def test_supported_intents_are_detected_conservatively(self):
		cases = {
			"hello there": "general_question",
			"what services do you provide": "service_enquiry",
			"how much does it cost": "pricing_enquiry",
			"I need a quotation": "quote_request",
			"can I book a cleaner": "booking_enquiry",
			"what about my existing booking": "existing_booking",
			"I want to make a complaint": "complaint",
			"where is my invoice": "invoice_question",
			"I have a payment question": "payment_question",
			"let me speak to a real person": "human_agent",
			"something unrelated": "unknown",
		}
		for message, expected in cases.items():
			self.assertEqual(detect_intent(message), expected)

	def test_services_and_entities_are_detected(self):
		self.assertEqual(detect_service("office cleaning please"), "office_cleaning")
		self.assertEqual(detect_service("commercial cleaners"), "commercial_cleaning")
		self.assertEqual(detect_service("clean my windows"), "window_cleaning")
		self.assertEqual(detect_service("oven needs cleaning"), "oven_cleaning")
		self.assertEqual(detect_service("carpet cleaning"), "carpet_cleaning")
		self.assertEqual(detect_service("spring clean"), "spring_cleaning")
		self.assertEqual(detect_service("deep clean"), "deep_cleaning")
		self.assertEqual(
			detect_service("end of lease cleaning"),
			"end_of_lease_cleaning",
		)
		entities = detect_entities(
			"We need an office in Prospect, 500 sqm, weekly. "
			"Email me at customer@example.com on 0400 123 456."
		)
		self.assertEqual(entities["email"], "customer@example.com")
		self.assertEqual(entities["phone"], "0400 123 456")
		self.assertEqual(entities["approximate_size"], "500 sqm")
		self.assertEqual(entities["frequency"], "weekly")
		self.assertEqual(entities["property_type"], "office")
		self.assertEqual(entities["suburb"], "Prospect")


class LiveChatConversationTests(TestCase):
	def test_same_session_key_reuses_one_conversation(self):
		consumer = LiveChatConsumer()
		get_conversation = async_to_sync(
			consumer.get_or_create_customer_conversation
		)

		first = get_conversation("browser-session", "Visitor", "", "")
		second = get_conversation("browser-session", "Visitor", "", "")

		self.assertEqual(first.pk, second.pk)
		self.assertEqual(
			LiveChatConversation.objects.filter(
				session_key="browser-session"
			).count(),
			1,
		)
		self.assertEqual(
			LiveChatMessage.objects.filter(conversation=first).count(),
			1,
		)
		self.assertEqual(first.mode, "ai")
		self.assertEqual(first.intent, "unknown")
		self.assertEqual(first.lead_status, "none")
		self.assertEqual(first.conversation_state, {})

	def test_conversation_state_fields_persist(self):
		conversation = LiveChatConversation.objects.create(
			name="Visitor",
			session_key="state-session",
			intent="quote_request",
			service="office_cleaning",
			lead_status="collecting",
			conversation_state={"quote": {"suburb": "Adelaide"}},
		)

		conversation.refresh_from_db()
		self.assertEqual(conversation.intent, "quote_request")
		self.assertEqual(conversation.service, "office_cleaning")
		self.assertEqual(conversation.lead_status, "collecting")
		self.assertEqual(
			conversation.conversation_state,
			{"quote": {"suburb": "Adelaide"}},
		)

	def test_status_mode_defaults_are_backward_compatible(self):
		waiting = LiveChatConversation.objects.create(
			name="Waiting",
			session_key="waiting-session",
			status="waiting",
		)
		active = LiveChatConversation.objects.create(
			name="Active",
			session_key="active-session",
			status="active",
			mode="human",
		)
		closed = LiveChatConversation.objects.create(
			name="Closed",
			session_key="closed-mode-session",
			status="closed",
			mode="closed",
		)

		self.assertEqual(waiting.mode, "ai")
		self.assertEqual(active.mode, "human")
		self.assertEqual(closed.mode, "closed")

	def test_closed_session_is_reopened_without_creating_duplicate(self):
		conversation = LiveChatConversation.objects.create(
			name="Visitor",
			session_key="closed-session",
			status="closed",
		)
		consumer = LiveChatConsumer()

		reopened = async_to_sync(
			consumer.get_or_create_customer_conversation
		)("closed-session", "Visitor", "", "")

		conversation.refresh_from_db()
		self.assertEqual(reopened.pk, conversation.pk)
		self.assertEqual(conversation.status, "waiting")
		self.assertEqual(conversation.mode, "ai")
		self.assertEqual(
			LiveChatConversation.objects.filter(
				session_key="closed-session"
			).count(),
			1,
		)

	def test_customer_cannot_load_another_sessions_conversation(self):
		LiveChatConversation.objects.create(
			name="Customer A",
			session_key="session-a",
		)
		conversation_b = LiveChatConversation.objects.create(
			name="Customer B",
			session_key="session-b",
		)
		consumer = LiveChatConsumer()

		conversation = async_to_sync(consumer.get_customer_conversation)(
			conversation_b.id,
			"session-a",
		)

		self.assertIsNone(conversation)

	def test_invalid_existing_conversation_id_is_rejected(self):
		consumer = LiveChatConsumer()
		consumer.session_key = "session-a"
		consumer.scope = {"user": None}
		consumer.send_json = AsyncMock()

		async_to_sync(consumer.receive_json)(
			{
				"action": "customer_message",
				"conversation_id": "not-an-id",
				"session_key": "session-a",
				"message": "Hello",
			}
		)

		consumer.send_json.assert_awaited_once_with(
			{"type": "error", "message": "Invalid conversation ID."}
		)

	def test_nonexistent_conversation_id_is_rejected(self):
		consumer = LiveChatConsumer()
		consumer.session_key = "session-a"
		consumer.scope = {"user": None}
		consumer.send_json = AsyncMock()

		async_to_sync(consumer.receive_json)(
			{
				"action": "customer_message",
				"conversation_id": 999999,
				"session_key": "session-a",
				"message": "Hello",
			}
		)

		consumer.send_json.assert_awaited_once_with(
			{"type": "error", "message": "Conversation not found."}
		)

	def test_malformed_json_is_rejected_without_exception(self):
		consumer = LiveChatConsumer()
		consumer.send_json = AsyncMock()

		async_to_sync(consumer.receive)(text_data="{not-json")

		consumer.send_json.assert_awaited_once_with(
			{"type": "error", "message": "Invalid WebSocket request."}
		)

	def test_missing_action_and_invalid_session_key_are_rejected(self):
		consumer = LiveChatConsumer()
		consumer.scope = {"user": None}
		consumer.send_json = AsyncMock()

		async_to_sync(consumer.receive_json)({})
		consumer.send_json.assert_awaited_once_with(
			{"type": "error", "message": "Chat action is required."}
		)

		consumer.send_json.reset_mock()
		async_to_sync(consumer.receive_json)(
			{"action": "customer_join", "session_key": "bad key"}
		)
		consumer.send_json.assert_awaited_once_with(
			{
				"type": "error",
				"message": "Chat session could not be identified.",
			}
		)

	def test_customer_message_validation_and_faq_behavior(self):
		conversation = LiveChatConversation.objects.create(
			name="Customer",
			session_key="session-a",
		)
		consumer = LiveChatConsumer()
		consumer.session_key = "session-a"
		consumer.scope = {"user": None}
		consumer.send_json = AsyncMock()
		consumer.check_inactivity = AsyncMock(return_value=False)

		for message in ("", "   ", "x" * 2001):
			consumer.send_json.reset_mock()
			async_to_sync(consumer.receive_json)(
				{
					"action": "customer_message",
					"conversation_id": conversation.id,
					"session_key": "session-a",
					"message": message,
				}
			)
			self.assertTrue(consumer.send_json.await_count == 1)

		self.assertIn(
			"Welcome to YD Commercial Cleaning",
			consumer.find_faq_response("hello"),
		)

	def test_ai_customer_message_updates_intent_service_and_state(self):
		conversation = LiveChatConversation.objects.create(
			name="Customer",
			session_key="analysis-session",
		)
		consumer = LiveChatConsumer()
		consumer.session_key = conversation.session_key
		consumer.scope = {"user": None}
		consumer.send_json = AsyncMock()
		consumer.check_inactivity = AsyncMock(return_value=False)
		consumer.save_message = AsyncMock()
		consumer.touch_conversation = AsyncMock()
		consumer.channel_layer = type(
			"ChannelLayer",
			(),
			{"group_send": AsyncMock()},
		)()
		consumer.room_group_name = f"live_chat_{conversation.id}"

		async_to_sync(consumer.receive_json)(
			{
				"action": "customer_message",
				"conversation_id": conversation.id,
				"session_key": conversation.session_key,
				"message": "I need office cleaning in Prospect, 500 sqm weekly",
			}
		)

		conversation.refresh_from_db()
		self.assertEqual(conversation.intent, "service_enquiry")
		self.assertEqual(conversation.service, "office_cleaning")
		self.assertEqual(conversation.conversation_state["schema_version"], 1)
		self.assertEqual(conversation.conversation_state["quote"]["suburb"], "Prospect")
		self.assertEqual(conversation.conversation_state["quote"]["approximate_size"], "500 sqm")
		self.assertEqual(conversation.conversation_state["quote"]["frequency"], "weekly")

	def test_existing_state_is_not_overwritten_by_missing_entities(self):
		conversation = LiveChatConversation.objects.create(
			name="Customer",
			session_key="preserve-session",
			intent="quote_request",
			service="office_cleaning",
			conversation_state={"schema_version": 1, "quote": {"suburb": "Prospect"}},
		)
		consumer = LiveChatConsumer()
		async_to_sync(consumer.update_conversation_state)(
			conversation.id,
			analyze_message("hello"),
		)
		conversation.refresh_from_db()
		self.assertEqual(conversation.intent, "quote_request")
		self.assertEqual(conversation.service, "office_cleaning")
		self.assertEqual(conversation.conversation_state["quote"]["suburb"], "Prospect")

	def test_human_and_waiting_for_human_modes_suppress_bot_response(self):
		for mode in ("human", "waiting_for_human"):
			conversation = LiveChatConversation.objects.create(
				name="Customer",
				session_key=f"{mode}-session",
				mode=mode,
			)
			consumer = LiveChatConsumer()
			consumer.session_key = conversation.session_key
			consumer.scope = {"user": None}
			consumer.send_json = AsyncMock()
			consumer.check_inactivity = AsyncMock(return_value=False)
			consumer.save_message = AsyncMock()
			consumer.touch_conversation = AsyncMock()
			consumer.channel_layer = type(
				"ChannelLayer",
				(),
				{"group_send": AsyncMock()},
			)()
			consumer.room_group_name = f"live_chat_{conversation.id}"

			async_to_sync(consumer.receive_json)(
				{
					"action": "customer_message",
					"conversation_id": conversation.id,
					"session_key": conversation.session_key,
					"message": "hello",
				}
			)

			self.assertEqual(consumer.save_message.await_count, 1)

	def test_customer_reconnect_closed_conversation_is_safe(self):
		conversation = LiveChatConversation.objects.create(
			name="Customer",
			session_key="session-a",
			status="closed",
		)
		consumer = LiveChatConsumer()

		reconnected = async_to_sync(
			consumer.get_or_create_customer_conversation
		)("session-a", "Customer", "", "")

		conversation.refresh_from_db()
		self.assertEqual(reconnected.id, conversation.id)
		self.assertEqual(conversation.status, "waiting")

	def test_closed_conversation_rejects_customer_message(self):
		conversation = LiveChatConversation.objects.create(
			name="Customer",
			session_key="session-a",
			status="closed",
		)
		consumer = LiveChatConsumer()
		consumer.session_key = "session-a"
		consumer.scope = {"user": None}
		consumer.send_json = AsyncMock()

		async_to_sync(consumer.receive_json)(
			{
				"action": "customer_message",
				"conversation_id": conversation.id,
				"session_key": "session-a",
				"message": "Hello",
			}
		)

		self.assertEqual(
			consumer.send_json.await_args.args[0]["type"],
			"chat_closed",
		)

	def test_unauthorized_staff_join_and_missing_conversation_fail_safely(self):
		consumer = LiveChatConsumer()
		consumer.scope = {"user": None}
		consumer.send_json = AsyncMock()

		async_to_sync(consumer.receive_json)(
			{"action": "staff_join", "conversation_id": 1}
		)
		consumer.send_json.assert_awaited_once_with(
			{"type": "error", "message": "Staff access required."}
		)

		consumer.send_json.reset_mock()
		async_to_sync(consumer.receive_json)(
			{"action": "customer_message", "message": "Hello"}
		)
		consumer.send_json.assert_awaited_once_with(
			{"type": "error", "message": "No active conversation."}
		)

	def test_staff_takeover_and_close_preserve_lifecycle(self):
		staff = User.objects.create_user(
			username="support-staff",
			is_staff=True,
		)
		conversation = LiveChatConversation.objects.create(
			name="Customer",
			session_key="session-lifecycle",
		)
		consumer = LiveChatConsumer()

		async_to_sync(consumer.takeover_conversation)(conversation.id, staff.id)
		conversation.refresh_from_db()
		self.assertEqual(conversation.status, "active")
		self.assertEqual(conversation.assigned_to_id, staff.id)
		self.assertEqual(conversation.mode, "human")

		async_to_sync(consumer.close_conversation)(
			conversation.id,
			"YD Cleaning Support",
			"Conversation closed.",
		)
		conversation.refresh_from_db()
		self.assertEqual(conversation.status, "closed")
		self.assertEqual(conversation.mode, "closed")

	def test_inactivity_closes_conversation_and_sets_closed_mode(self):
		conversation = LiveChatConversation.objects.create(
			name="Inactive Customer",
			session_key="inactive-session",
		)
		LiveChatConversation.objects.filter(id=conversation.id).update(
			updated_at=timezone.now() - timedelta(minutes=11)
		)
		conversation.refresh_from_db()
		consumer = LiveChatConsumer()

		was_inactive = async_to_sync(consumer.check_inactivity)(conversation)

		conversation.refresh_from_db()
		self.assertTrue(was_inactive)
		self.assertEqual(conversation.status, "closed")
		self.assertEqual(conversation.mode, "closed")

	def test_http_staff_takeover_and_close_update_mode(self):
		staff = User.objects.create_user(
			username="http-support-staff",
			is_staff=True,
		)
		conversation = LiveChatConversation.objects.create(
			name="HTTP Customer",
			session_key="http-lifecycle-session",
		)
		self.client.force_login(staff)

		response = self.client.post(
			f"/dashboard/support/live-chat/{conversation.id}/takeover/"
		)
		self.assertEqual(response.status_code, 200)
		conversation.refresh_from_db()
		self.assertEqual(conversation.status, "active")
		self.assertEqual(conversation.mode, "human")

		response = self.client.post(
			f"/dashboard/support/live-chat/{conversation.id}/close/"
		)
		self.assertEqual(response.status_code, 200)
		conversation.refresh_from_db()
		self.assertEqual(conversation.status, "closed")
		self.assertEqual(conversation.mode, "closed")


class SupportTicketWorkflowTests(TestCase):
	def setUp(self):
		self.customer_user = User.objects.create_user(
			username="customer@example.com",
			password="test-password",
		)
		self.customer = Customer.objects.create(
			user=self.customer_user,
			full_name="Customer Example",
			email="customer@example.com",
			phone="0400123456",
		)
		self.staff_user = User.objects.create_user(
			username="staff",
			password="test-password",
			is_staff=True,
		)

	def test_customer_creates_and_views_ticket(self):
		self.client.force_login(self.customer_user)
		response = self.client.post(
			"/portal/support/new/",
			{"subject": "Booking question", "message": "Please help.", "priority": "medium"},
		)

		self.assertRedirects(response, "/portal/support/")
		ticket = self.customer.support_tickets.get()
		self.assertTrue(
			self.client.get(f"/portal/support/{ticket.id}/").status_code == 200
		)
		self.assertEqual(Notification.objects.filter(user=self.staff_user).count(), 1)

	def test_staff_updates_ticket_and_replies_to_customer(self):
		from .models import SupportTicket

		ticket = SupportTicket.objects.create(
			customer=self.customer,
			subject="Booking question",
			message="Please help.",
		)
		self.client.force_login(self.staff_user)
		self.assertEqual(
			self.client.get(f"/portal/support/{ticket.id}/").status_code,
			200,
		)
		response = self.client.post(
			f"/dashboard/support/tickets/{ticket.id}/update/",
			{
				"status": "in_progress",
				"priority": "high",
				"message": "We are reviewing this now.",
			},
		)

		self.assertRedirects(response, f"/portal/support/{ticket.id}/")
		ticket.refresh_from_db()
		self.assertEqual(ticket.status, "in_progress")
		self.assertEqual(ticket.priority, "high")
		self.assertEqual(ticket.replies.count(), 1)
		self.assertGreater(Notification.objects.filter(user=self.customer_user).count(), 0)


class ChatWorkflowIntegrationTests(TestCase):
	def _conversation(self, **kwargs):
		defaults = {
			"name": "Test Visitor",
			"email": "visitor@example.com",
			"phone": "0400123456",
			"session_key": "workflow-session",
			"mode": "ai",
			"status": "waiting",
			"intent": "unknown",
			"conversation_state": {},
		}
		defaults.update(kwargs)
		return LiveChatConversation.objects.create(**defaults)

	def test_quote_workflow_collects_state_and_reaches_confirmation(self):
		conversation = self._conversation(
			session_key="quote-workflow-session",
			email="",
			phone="",
		)

		result = handle_message(
			conversation,
			"I need a quote for my house, 150 sqm, weekly, in Prospect.",
			analyze_message(
				"I need a quote for my house, 150 sqm, weekly, in Prospect."
			),
			faq_response=None,
		)

		self.assertEqual(result["action"], "collect_quote")
		state = result["state"]

		self.assertEqual(state["quote"]["property_type"], "House")
		self.assertEqual(state["quote"]["approximate_size"], "150 sqm")
		self.assertEqual(state["quote"]["frequency"], "weekly")
		self.assertEqual(state["quote"]["suburb"], "Prospect")

		# Persist the workflow state before continuing the conversation.
		conversation.conversation_state = state

		for message in (
			"visitor@example.com",
			"0400123456",
		):
			result = handle_message(
				conversation,
				message,
				analyze_message(message),
				faq_response=None,
			)

			conversation.conversation_state = result["state"]

		result = handle_message(
			conversation,
			"yes",
			analyze_message("yes"),
			faq_response=None,
		)

		self.assertEqual(result["action"], "create_quote")
		self.assertTrue(result["state"]["workflow"]["awaiting_confirmation"])

	def test_booking_workflow_collects_date_time_address_and_contact(self):
		conversation = self._conversation(
			session_key="booking-workflow-session",
			email="",
			phone="",
		)

		messages = (
			"book office cleaning",
			"15 September 2026",
			"10am",
			"123 King Street",
			"Adelaide",
			"visitor@example.com",
			"0400123456",
		)

		state = {}
		for message in messages:
			conversation.conversation_state = state
			result = handle_message(
				conversation,
				message,
				analyze_message(message),
				faq_response=None,
			)
			state = result["state"]

		self.assertEqual(state["booking"]["service"], "office_cleaning")
		self.assertEqual(state["booking"]["preferred_date"], "2026-09-15")
		self.assertEqual(state["booking"]["preferred_time"], "10:00")
		self.assertEqual(state["booking"]["address"], "123 King Street")
		self.assertEqual(state["booking"]["suburb"], "Adelaide")
		self.assertEqual(state["customer"]["email"], "visitor@example.com")
		self.assertEqual(state["customer"]["phone"], "0400123456")
		self.assertEqual(result["action"], "collect_booking")
		self.assertTrue(state["workflow"]["awaiting_confirmation"])

	def test_human_request_never_enters_automated_workflow(self):
		conversation = self._conversation(
			session_key="human-workflow-session",
		)

		result = handle_message(
			conversation,
			"I want to speak to a real person",
			analyze_message("I want to speak to a real person"),
			faq_response="This is an FAQ answer that must not win.",
		)

		self.assertEqual(result["action"], "request_human")
		self.assertTrue(result["needs_human"])
		self.assertEqual(result["state"]["workflow"]["type"], "human")

	def test_existing_human_mode_stays_out_of_bot_workflow(self):
		conversation = self._conversation(
			session_key="human-mode-session",
			mode="human",
			status="active",
		)

		result = handle_message(
			conversation,
			"I need a quote",
			analyze_message("I need a quote"),
			faq_response="FAQ",
		)

		self.assertEqual(result["action"], "none")
		self.assertIsNone(result["reply"])

	def test_date_and_time_entities_are_extracted(self):
		analysis = analyze_message(
			"I'd like office cleaning on 15 September 2026 at 10:30am."
		)

		self.assertEqual(
			analysis["entities"]["preferred_date"],
			"2026-09-15",
		)
		self.assertEqual(
			analysis["entities"]["preferred_time"],
			"10:30",
		)


	def test_general_enquiry_is_not_accepted_as_booking_address(self):
		conversation = self._conversation(
			session_key="address-validation-session",
		)

		state = {
			"workflow": {
				"type": "booking",
				"step": "address",
				"awaiting_confirmation": False,
			},
			"booking": {},
			"quote": {},
			"customer": {},
		}

		conversation.conversation_state = state

		result = handle_message(
			conversation,
			"Hi, I need a quote for office cleaning in Prospect.",
			analyze_message(
				"Hi, I need a quote for office cleaning in Prospect."
			),
			faq_response=None,
		)

		self.assertNotEqual(
			result["state"]["booking"].get("address"),
			"Hi, I need a quote for office cleaning in Prospect.",
		)