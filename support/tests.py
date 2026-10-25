from asgiref.sync import async_to_sync
from datetime import timedelta
from django.contrib.auth.models import User
from django.core.management import call_command, CommandError
from django.db import DatabaseError
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from io import StringIO
from unittest.mock import AsyncMock, patch
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.core import signing

from core.test_utils import grant_dashboard_permissions
from customers.models import Customer
from employees.models import Employee
from notifications.models import Notification

from .consumers import LiveChatConsumer
from .chat_intent import analyze_message, detect_intent, detect_service, detect_entities
from .chat_workflow import handle_message
from .models import LiveChatConversation, LiveChatMessage
from .realtime import DASHBOARD_GROUP


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
	def test_customer_message_notifies_staff_dashboard_without_exposing_message(self):
		staff_user = User.objects.create_user(
			"live-chat-staff",
			is_staff=True,
		)
		User.objects.create_user("live-chat-customer")
		conversation = LiveChatConversation.objects.create(
			name="Website Visitor",
			session_key="notification-session",
		)
		consumer = LiveChatConsumer()

		async_to_sync(consumer.save_message)(
			conversation.pk,
			"customer",
			"Website Visitor",
			"Please call me about a private issue.",
		)

		notification = Notification.objects.get(user=staff_user)
		self.assertEqual(notification.title, "New Website Chat Message")
		self.assertEqual(notification.notification_type, "support")
		self.assertEqual(notification.link, "/dashboard/support/")
		self.assertIn(f"#{conversation.pk}", notification.message)
		self.assertNotIn(
			"private issue",
			notification.message,
		)
		self.assertEqual(
			Notification.objects.filter(
				user__username="live-chat-customer",
			).count(),
			0,
		)
		self.assertTrue(
			LiveChatMessage.objects.filter(
				conversation=conversation,
				sender_type="customer",
				message="Please call me about a private issue.",
			).exists()
		)

	def test_staff_message_does_not_notify_dashboard(self):
		staff_user = User.objects.create_user(
			"live-chat-staff-sender",
			is_staff=True,
		)
		conversation = LiveChatConversation.objects.create(
			name="Website Visitor",
			session_key="staff-message-session",
		)
		consumer = LiveChatConsumer()

		async_to_sync(consumer.save_message)(
			conversation.pk,
			"staff",
			"Support Agent",
			"How can I help?",
		)

		self.assertFalse(
			Notification.objects.filter(user=staff_user).exists()
		)

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
			{
				"type": "error",
				"message": "Join this conversation before performing chat actions.",
			}
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
				"message": "Chat session is invalid or expired. Refresh the page and retry.",
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
		consumer.conversation_id = conversation.id

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
		consumer.conversation_id = conversation.id
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
			consumer.conversation_id = conversation.id
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
		consumer.conversation_id = conversation.id

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

	def test_staff_without_change_permission_cannot_send_chat_messages(self):
		staff = User.objects.create_user(
			username="view-only-chat-staff",
			is_staff=True,
		)
		grant_dashboard_permissions(staff, "support.view_livechatconversation")
		conversation = LiveChatConversation.objects.create(
			name="Customer",
			session_key="view-only-session",
			status="active",
			mode="human",
			assigned_to=staff,
		)
		consumer = LiveChatConsumer()
		consumer.scope = {"user": staff}
		consumer.is_staff = True
		consumer.chat_role = "staff"
		consumer.conversation_id = conversation.pk
		consumer.check_inactivity = AsyncMock(return_value=False)
		consumer.send_json = AsyncMock()
		consumer.save_message = AsyncMock()

		for action in ("staff_message", "message"):
			consumer.send_json.reset_mock()
			async_to_sync(consumer.receive_json)(
				{
					"action": action,
					"conversation_id": conversation.pk,
					"message": "Not authorized",
				}
			)
			consumer.send_json.assert_awaited_once()
			consumer.save_message.assert_not_awaited()

	def test_customer_token_is_bound_to_the_current_browser_session(self):
		consumer = LiveChatConsumer()
		consumer.scope = {"session": {"live_chat_session_key": "browser-session-a"}}
		token = signing.dumps(
			{"session_key": "browser-session-a"},
			salt="support.live-chat.session",
		)

		self.assertEqual(
			async_to_sync(consumer.validate_customer_token)(token),
			"browser-session-a",
		)
		consumer.scope["session"]["live_chat_session_key"] = "browser-session-b"
		self.assertIsNone(
			async_to_sync(consumer.validate_customer_token)(token)
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
		self.assertIsNotNone(conversation.closed_at)

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
		self.assertIsNotNone(conversation.closed_at)

	def test_http_staff_takeover_and_close_update_mode(self):
		staff = User.objects.create_user(
			username="http-support-staff",
			is_staff=True,
		)
		grant_dashboard_permissions(
			staff,
			"support.view_livechatconversation",
			"support.change_livechatconversation",
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
		self.assertIsNotNone(conversation.closed_at)

	def test_http_chat_assignment_is_permission_checked_and_audited(self):
		agent = User.objects.create_user(
			username="assignable-chat-agent",
			first_name="Avery",
			is_staff=True,
		)
		grant_dashboard_permissions(
			agent,
			"support.view_livechatconversation",
			"support.change_livechatconversation",
		)
		staff_without_dashboard_access = User.objects.create_user(
			username="support-permission-without-dashboard",
			first_name="Internal User",
			is_staff=True,
		)
		grant_dashboard_permissions(
			staff_without_dashboard_access,
			"support.view_livechatconversation",
			"support.change_livechatconversation",
		)
		from django.contrib.auth.models import Permission

		staff_without_dashboard_access.user_permissions.remove(
			Permission.objects.get(
				content_type__app_label="security",
				codename="access_dashboard",
			)
		)
		employee_operator = User.objects.create_user(
			username="employee-chat-operator",
			first_name="Employee Operator",
			is_staff=True,
		)
		grant_dashboard_permissions(
			employee_operator,
			"support.view_livechatconversation",
			"support.change_livechatconversation",
		)
		Employee.objects.create(
			user=employee_operator,
			full_name="Employee Operator",
			phone="0400000000",
		)
		manager = User.objects.create_user(
			username="chat-assignment-manager",
			is_staff=True,
		)
		grant_dashboard_permissions(
			manager,
			"support.view_livechatconversation",
			"support.change_livechatconversation",
			"support.view_chatenquiry",
		)
		conversation = LiveChatConversation.objects.create(
			name="Waiting Customer",
			session_key="assignment-session",
			status="waiting",
		)

		unauthorized = User.objects.create_user(
			username="unauthorized-chat-operator",
			is_staff=True,
		)
		self.client.force_login(unauthorized)
		response = self.client.post(
			f"/dashboard/support/live-chat/{conversation.pk}/assign/",
			{"staff_user_id": agent.pk},
		)
		self.assertEqual(response.status_code, 403)
		self.client.force_login(manager)
		dashboard_response = self.client.get("/dashboard/support/")
		self.assertEqual(dashboard_response.status_code, 200)
		self.assertContains(dashboard_response, 'id="assignChatStaff"')
		self.assertContains(dashboard_response, "Avery")
		self.assertNotContains(dashboard_response, "Internal User")
		self.assertNotContains(dashboard_response, "Employee Operator")
		response = self.client.post(
			f"/dashboard/support/live-chat/{conversation.pk}/assign/",
			{"staff_user_id": employee_operator.pk},
		)
		self.assertEqual(response.status_code, 400)

		response = self.client.post(
			f"/dashboard/support/live-chat/{conversation.pk}/assign/",
			{"staff_user_id": staff_without_dashboard_access.pk},
		)
		self.assertEqual(response.status_code, 400)

		response = self.client.post(
			f"/dashboard/support/live-chat/{conversation.pk}/assign/",
			{"staff_user_id": agent.pk},
		)

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.json()["success"])
		self.assertEqual(response.json()["assigned_to_id"], agent.pk)
		conversation.refresh_from_db()
		self.assertEqual(conversation.assigned_to_id, agent.pk)
		self.assertEqual(conversation.status, "active")
		self.assertEqual(conversation.mode, "human")
		self.assertTrue(
			conversation.messages.filter(
				sender_type="system",
				message__contains="was assigned",
			).exists()
		)
		from dashboard.models import ActivityLog

		self.assertTrue(
			ActivityLog.objects.filter(
				user=manager,
				title="Live Chat Assigned",
			).exists()
		)

		replacement_agent = User.objects.create_user(
			username="replacement-chat-agent",
			first_name="Jordan",
			is_staff=True,
		)
		grant_dashboard_permissions(
			replacement_agent,
			"support.view_livechatconversation",
			"support.change_livechatconversation",
		)
		second_manager = User.objects.create_user(
			username="chat-transfer-manager",
			is_staff=True,
		)
		grant_dashboard_permissions(
			second_manager,
			"support.view_livechatconversation",
			"support.change_livechatconversation",
		)
		self.client.force_login(second_manager)
		response = self.client.post(
			f"/dashboard/support/live-chat/{conversation.pk}/assign/",
			{
				"staff_user_id": replacement_agent.pk,
				"expected_assigned_to_id": "",
			},
		)
		self.assertEqual(response.status_code, 409)
		conversation.refresh_from_db()
		self.assertEqual(conversation.assigned_to_id, agent.pk)

		transfer_manager = User.objects.create_user(
			username="chat-transfer-manager-success",
			is_staff=True,
		)
		grant_dashboard_permissions(
			transfer_manager,
			"support.view_livechatconversation",
			"support.change_livechatconversation",
		)
		self.client.force_login(transfer_manager)
		response = self.client.post(
			f"/dashboard/support/live-chat/{conversation.pk}/assign/",
			{
				"staff_user_id": replacement_agent.pk,
				"expected_assigned_to_id": agent.pk,
			},
		)

		self.assertEqual(response.status_code, 200)
		conversation.refresh_from_db()
		self.assertEqual(conversation.assigned_to_id, replacement_agent.pk)
		self.assertTrue(
			conversation.messages.filter(
				sender_type="system",
				message__contains="reassigned from Avery to Jordan",
			).exists()
		)
		self.assertTrue(
			ActivityLog.objects.filter(
				user=transfer_manager,
				title="Live Chat Reassigned",
			).exists()
		)


@override_settings(
	CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
)
class LiveChatRealtimeTests(TransactionTestCase):
	def test_staff_browser_customer_widget_messages_follow_signed_customer_role(self):
		staff = User.objects.create_user(
			username="staff-using-customer-widget",
			is_staff=True,
		)
		grant_dashboard_permissions(
			staff,
			"support.view_livechatconversation",
			"support.change_livechatconversation",
		)
		session_key = "staff-browser-customer-chat"
		conversation = LiveChatConversation.objects.create(
			name="Website Visitor",
			session_key=session_key,
		)
		token = signing.dumps(
			{"session_key": session_key},
			salt="support.live-chat.session",
		)

		async def scenario():
			communicator = WebsocketCommunicator(
				LiveChatConsumer.as_asgi(),
				"/ws/live-chat/",
			)
			communicator.scope["user"] = staff
			communicator.scope["session"] = {
				"live_chat_session_key": session_key,
			}
			connected, _ = await communicator.connect()
			await communicator.receive_json_from()
			await communicator.send_json_to(
				{
					"action": "customer_join",
					"session_token": token,
					"name": "Website Visitor",
					"email": "",
					"phone": "",
				}
			)
			joined = await communicator.receive_json_from()
			await communicator.send_json_to(
				{
					"action": "customer_message",
					"message": "hello",
				}
			)
			message = await communicator.receive_json_from()
			bot_response = await communicator.receive_json_from()
			await communicator.disconnect()
			return connected, joined, message, bot_response

		connected, joined, message, bot_response = async_to_sync(scenario)()

		self.assertTrue(connected)
		self.assertEqual(joined["type"], "connection")
		self.assertEqual(joined["conversation_id"], conversation.pk)
		self.assertEqual(message["type"], "message")
		self.assertEqual(message["sender_type"], "customer")
		self.assertEqual(bot_response["type"], "message")
		self.assertEqual(bot_response["sender_type"], "bot")
		self.assertTrue(
			LiveChatMessage.objects.filter(
				conversation=conversation,
				sender_type="customer",
				message="hello",
			).exists()
		)
		self.assertTrue(bot_response["message"])

	def test_assigned_staff_can_join_and_send_authorized_replies(self):
		staff = User.objects.create_user(
			username="assigned-chat-agent",
			first_name="Assigned",
			is_staff=True,
		)
		grant_dashboard_permissions(
			staff,
			"support.view_livechatconversation",
			"support.change_livechatconversation",
		)
		conversation = LiveChatConversation.objects.create(
			name="Assigned visitor",
			session_key="assigned-websocket-session",
			status="active",
			mode="human",
			assigned_to=staff,
		)

		async def scenario():
			communicator = WebsocketCommunicator(
				LiveChatConsumer.as_asgi(),
				"/ws/live-chat/",
			)
			communicator.scope["user"] = staff
			connected, _ = await communicator.connect()
			await communicator.receive_json_from()
			await communicator.send_json_to(
				{
					"action": "staff_join",
					"conversation_id": conversation.pk,
				}
			)
			joined = await communicator.receive_json_from()
			await communicator.send_json_to(
				{
					"action": "staff_message",
					"conversation_id": conversation.pk,
					"message": "I can help with that.",
				}
			)
			message = await communicator.receive_json_from()
			await communicator.disconnect()
			return connected, joined, message

		connected, joined, message = async_to_sync(scenario)()

		self.assertTrue(connected)
		self.assertEqual(joined["type"], "connection")
		self.assertEqual(joined["assigned_to_id"], staff.pk)
		self.assertIsInstance(joined["conversation_id"], int)
		self.assertEqual(message["type"], "message")
		self.assertEqual(message["sender_type"], "staff")
		self.assertTrue(
			LiveChatMessage.objects.filter(
				conversation=conversation,
				sender_type="staff",
				message="I can help with that.",
			).exists()
		)

	def test_new_conversation_is_broadcast_to_dashboard_group(self):
		async def scenario():
			layer = get_channel_layer()
			channel_name = await layer.new_channel("support-test.")
			await layer.group_add(DASHBOARD_GROUP, channel_name)
			consumer = LiveChatConsumer()
			conversation = await consumer.get_or_create_customer_conversation(
				"realtime-session",
				"Website Visitor",
				"",
				"",
			)
			event = await layer.receive(channel_name)
			await layer.group_discard(DASHBOARD_GROUP, channel_name)
			return conversation, event

		conversation, event = async_to_sync(scenario)()
		self.assertEqual(event["type"], "dashboard_update")
		self.assertEqual(event["event"], "conversation.created")
		self.assertEqual(event["conversation"]["id"], conversation.pk)
		self.assertEqual(event["conversation"]["status"], "waiting")

	def test_new_messages_broadcast_updated_preview_and_message_id(self):
		conversation = LiveChatConversation.objects.create(
			name="Visitor",
			session_key="message-realtime-session",
		)

		async def scenario():
			layer = get_channel_layer()
			channel_name = await layer.new_channel("support-test.")
			await layer.group_add(DASHBOARD_GROUP, channel_name)
			consumer = LiveChatConsumer()
			message_id = await consumer.save_message(
				conversation.pk,
				"customer",
				"Visitor",
				"Need help with an office clean.",
			)
			event = await layer.receive(channel_name)
			await layer.group_discard(DASHBOARD_GROUP, channel_name)
			return event, message_id

		event, message_id = async_to_sync(scenario)()
		self.assertEqual(event["event"], "conversation.message")
		self.assertEqual(event["conversation"]["last_message_id"], message_id)
		self.assertEqual(
			event["conversation"]["preview"],
			"Need help with an office clean.",
		)

	def test_staff_websocket_requires_support_model_permission(self):
		staff = User.objects.create_user(
			username="staff-without-chat-permissions",
			is_staff=True,
		)

		async def scenario():
			communicator = WebsocketCommunicator(
				LiveChatConsumer.as_asgi(),
				"/ws/live-chat/",
			)
			communicator.scope["user"] = staff
			connected, _ = await communicator.connect()
			await communicator.receive_json_from()
			await communicator.send_json_to({"action": "dashboard_join"})
			response = await communicator.receive_json_from()
			await communicator.disconnect()
			return connected, response

		connected, response = async_to_sync(scenario)()
		self.assertTrue(connected)
		self.assertEqual(response["type"], "error")
		self.assertEqual(response["message"], "Support chat access required.")

	def test_reconnect_history_returns_only_messages_after_cursor(self):
		staff = User.objects.create_user(
			username="history-support-staff",
			is_staff=True,
		)
		grant_dashboard_permissions(staff, "support.view_livechatconversation")
		conversation = LiveChatConversation.objects.create(
			name="History visitor",
			session_key="history-session",
		)
		first = LiveChatMessage.objects.create(
			conversation=conversation,
			sender_type="customer",
			message="Before reconnect",
		)
		second = LiveChatMessage.objects.create(
			conversation=conversation,
			sender_type="customer",
			message="Missed during disconnect",
		)
		self.client.force_login(staff)

		response = self.client.get(
			f"/dashboard/support/live-chat/{conversation.pk}/?after_id={first.pk}"
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(
			[item["id"] for item in response.json()["messages"]],
			[second.pk],
		)


@override_settings(LIVE_CHAT_RETENTION_DAYS=180)
class LiveChatRetentionTests(TestCase):
	def setUp(self):
		self.cutoff_expired = timezone.now() - timedelta(days=181)
		self.expired = LiveChatConversation.objects.create(
			name="Expired",
			session_key="expired-retention-session",
			status="closed",
			closed_at=self.cutoff_expired,
		)
		self.active = LiveChatConversation.objects.create(
			name="Active",
			session_key="active-retention-session",
			status="active",
			closed_at=self.cutoff_expired,
		)
		self.waiting = LiveChatConversation.objects.create(
			name="Waiting",
			session_key="waiting-retention-session",
			status="waiting",
			closed_at=self.cutoff_expired,
		)
		self.held = LiveChatConversation.objects.create(
			name="Legal hold",
			session_key="held-retention-session",
			status="closed",
			closed_at=self.cutoff_expired,
			legal_hold=True,
		)
		self.recent = LiveChatConversation.objects.create(
			name="Recent",
			session_key="recent-retention-session",
			status="closed",
			closed_at=timezone.now() - timedelta(days=179),
		)
		self.expired_message = LiveChatMessage.objects.create(
			conversation=self.expired,
			sender_type="customer",
			message="This message should cascade on deletion.",
		)

	def test_dry_run_reports_candidates_and_deletes_nothing(self):
		output = StringIO()
		call_command(
			"cleanup_expired_live_chats",
			"--dry-run",
			stdout=output,
		)

		self.assertIn("eligible=1", output.getvalue())
		self.assertTrue(
			LiveChatConversation.objects.filter(pk=self.expired.pk).exists()
		)
		self.assertTrue(
			LiveChatMessage.objects.filter(pk=self.expired_message.pk).exists()
		)

	def test_delete_only_expired_closed_not_held_and_is_repeatable(self):
		call_command("cleanup_expired_live_chats", "--delete")

		self.assertFalse(
			LiveChatConversation.objects.filter(pk=self.expired.pk).exists()
		)
		self.assertFalse(
			LiveChatMessage.objects.filter(pk=self.expired_message.pk).exists()
		)
		for conversation in (self.active, self.waiting, self.held, self.recent):
			self.assertTrue(
				LiveChatConversation.objects.filter(pk=conversation.pk).exists()
			)

		output = StringIO()
		call_command("cleanup_expired_live_chats", "--delete", stdout=output)
		self.assertIn("eligible=0", output.getvalue())

	def test_batch_size_and_failed_item_do_not_delete_other_candidates(self):
		second_expired = LiveChatConversation.objects.create(
			name="Second expired",
			session_key="second-expired-retention-session",
			status="closed",
			closed_at=self.cutoff_expired,
		)
		with patch.object(
			LiveChatConversation,
			"delete",
			side_effect=DatabaseError("simulated delete failure"),
		):
			with self.assertRaises(CommandError):
				call_command(
					"cleanup_expired_live_chats",
					"--delete",
					"--batch-size",
					"1",
					stdout=StringIO(),
				)
		self.assertTrue(
			LiveChatConversation.objects.filter(pk=self.expired.pk).exists()
		)
		self.assertTrue(
			LiveChatConversation.objects.filter(pk=second_expired.pk).exists()
		)

		call_command(
			"cleanup_expired_live_chats",
			"--delete",
			"--batch-size",
			"1",
			stdout=StringIO(),
		)
		self.assertFalse(
			LiveChatConversation.objects.filter(pk=self.expired.pk).exists()
		)
		self.assertTrue(
			LiveChatConversation.objects.filter(pk=second_expired.pk).exists()
		)


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
		grant_dashboard_permissions(
			self.staff_user,
			"support.view_supportticket",
			"support.change_supportticket",
		)

	def test_customer_creates_and_views_ticket(self):
		self.client.force_login(self.customer_user)
		tickets_page = self.client.get("/portal/support/")
		self.assertEqual(tickets_page.status_code, 200)
		self.assertNotContains(tickets_page, 'class="crm-sidebar"')

		create_page = self.client.get("/portal/support/new/")
		self.assertEqual(create_page.status_code, 200)
		self.assertNotContains(create_page, 'class="crm-sidebar"')

		response = self.client.post(
			"/portal/support/new/",
			{"subject": "Booking question", "message": "Please help.", "priority": "medium"},
		)

		self.assertRedirects(response, "/portal/support/")
		ticket = self.customer.support_tickets.get()
		detail_page = self.client.get(f"/portal/support/{ticket.id}/")
		self.assertEqual(detail_page.status_code, 200)
		self.assertNotContains(detail_page, 'class="crm-sidebar"')
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
