from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from django.test import TestCase

from customers.models import Customer
from notifications.models import Notification

from .consumers import LiveChatConsumer
from .models import LiveChatConversation, LiveChatMessage


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
		self.assertEqual(
			LiveChatConversation.objects.filter(
				session_key="closed-session"
			).count(),
			1,
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
