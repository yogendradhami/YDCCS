from threading import Event, Thread
from datetime import timedelta
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.test_utils import grant_dashboard_permissions
from dashboard.models import Equipment
from dashboard.reminders import count_unseen_reminders, get_reminder_center_items
from .utils import temporary_instance_flags
from .models import Notification


class TemporaryInstanceFlagTests(TestCase):
    def test_restores_original_flag_state_after_success_and_exception(self):
        instance = SimpleNamespace(existing_flag="preserve")

        with temporary_instance_flags(
            instance,
            existing_flag=True,
            temporary_flag=True,
        ):
            self.assertTrue(instance.existing_flag)
            self.assertTrue(instance.temporary_flag)

        self.assertEqual(instance.existing_flag, "preserve")
        self.assertFalse(hasattr(instance, "temporary_flag"))

        with self.assertRaises(RuntimeError):
            with temporary_instance_flags(
                instance,
                existing_flag="temporary",
                new_flag=True,
            ):
                raise RuntimeError("test failure")

        self.assertEqual(instance.existing_flag, "preserve")
        self.assertFalse(hasattr(instance, "new_flag"))

    def test_nested_and_concurrent_flag_scopes_restore_each_other(self):
        instance = SimpleNamespace(status_flag="original")

        with temporary_instance_flags(instance, status_flag="outer"):
            with temporary_instance_flags(
                instance,
                status_flag="inner",
                temporary_flag=True,
            ):
                self.assertEqual(instance.status_flag, "inner")
            self.assertEqual(instance.status_flag, "outer")
            self.assertFalse(hasattr(instance, "temporary_flag"))

        first_entered = Event()
        release_first = Event()
        second_entered = Event()

        def first_scope():
            with temporary_instance_flags(instance, status_flag="first"):
                first_entered.set()
                release_first.wait(timeout=2)

        def second_scope():
            with temporary_instance_flags(instance, status_flag="second"):
                second_entered.set()

        first_thread = Thread(target=first_scope, daemon=True)
        second_thread = Thread(target=second_scope, daemon=True)
        first_thread.start()
        self.assertTrue(first_entered.wait(timeout=2))
        second_thread.start()
        try:
            self.assertFalse(second_entered.wait(timeout=0.05))
        finally:
            release_first.set()
        first_thread.join(timeout=2)
        second_thread.join(timeout=2)

        self.assertFalse(first_thread.is_alive())
        self.assertFalse(second_thread.is_alive())
        self.assertTrue(second_entered.is_set())
        self.assertEqual(instance.status_flag, "original")


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
        grant_dashboard_permissions(
            user,
            "dashboard.view_equipment",
            "dashboard.view_cleaningsupply",
            "dashboard.view_purchaseorder",
            "dashboard.view_vehicle",
            "dashboard.view_maintenancehistory",
            "contracts.view_cleaningcontract",
        )
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
