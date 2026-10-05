from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dashboard.models import Equipment
from dashboard.reminders import count_unseen_reminders, get_reminder_center_items
from .models import Notification


class NotificationStatusTests(TestCase):
    def test_status_includes_unread_counts_by_notification_type(self):
        user = User.objects.create_user("notification-user")
        Notification.objects.create(
            user=user,
            title="New quote",
            message="A new quote is ready.",
            notification_type="quote",
        )
        Notification.objects.create(
            user=user,
            title="Another quote",
            message="Another quote is ready.",
            notification_type="quote",
        )
        Notification.objects.create(
            user=user,
            title="Read booking",
            message="This booking was read.",
            notification_type="booking",
            is_read=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("notification_status"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["unread_count"], 2)
        self.assertEqual(response.json()["unread_by_type"], {"quote": 2})


class ReminderCenterReadStateTests(TestCase):
    def test_opening_center_acknowledges_current_reminders_and_new_ones_reappear(self):
        user = User.objects.create_user("reminder-user", is_staff=True)
        Equipment.objects.create(
            name="Floor machine",
            next_service_date=timezone.localdate() - timedelta(days=1),
        )
        self.client.force_login(user)

        items = get_reminder_center_items()
        self.assertEqual(count_unseen_reminders(user, items), 1)

        response = self.client.get(reverse("reminder_centre"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["notification_counts"]["reminders"], 0)
        self.assertNotContains(response, "data-reminder-count")
        self.assertEqual(
            count_unseen_reminders(user, get_reminder_center_items()),
            0,
        )

        Equipment.objects.create(
            name="Carpet extractor",
            next_service_date=timezone.localdate() - timedelta(days=2),
        )
        self.assertEqual(
            count_unseen_reminders(user, get_reminder_center_items()),
            1,
        )
