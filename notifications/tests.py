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
            title="Property damage report",
            message="An employee submitted a property damage report.",
            notification_type="damage_report",
        )
        Notification.objects.create(
            user=user,
            title="New website chat message",
            message="A visitor sent a message in live chat #1.",
            notification_type="support",
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
        self.assertEqual(response.json()["unread_count"], 4)
        self.assertEqual(
            response.json()["unread_by_type"],
            {"quote": 2, "support": 1, "damage_report": 1},
        )

    def test_status_groups_operations_notifications_by_destination(self):
        user = User.objects.create_user("operations-notification-user")
        for link in (
            "/dashboard/supplies/",
            "/dashboard/operations-automation/",
            "/dashboard/operations-automation/history/",
        ):
            Notification.objects.create(
                user=user,
                title="Operations update",
                message="An operation needs attention.",
                link=link,
            )
        self.client.force_login(user)

        response = self.client.get(reverse("notification_status"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["unread_by_area"]["supplies"], 1)
        self.assertEqual(response.json()["unread_by_area"]["operations_automation"], 1)
        self.assertEqual(response.json()["unread_by_area"]["automation_history"], 1)

    def test_mark_cleaning_supply_notifications_read_does_not_clear_other_areas(self):
        user = User.objects.create_user("operations-area-reader")
        other_user = User.objects.create_user("operations-other-reader")
        supply_notification = Notification.objects.create(
            user=user,
            title="Low stock",
            message="Restock is needed.",
            link="/dashboard/supplies/",
        )
        inventory_notification = Notification.objects.create(
            user=user,
            title="Inventory movement",
            message="A transaction was recorded.",
            link="/dashboard/inventory-transactions/",
        )
        other_supply_notification = Notification.objects.create(
            user=other_user,
            title="Low stock",
            message="Private supply notification.",
            link="/dashboard/supplies/",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse(
                "mark_notification_area_read",
                kwargs={"area": "supplies"},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["updated"], 1)
        supply_notification.refresh_from_db()
        inventory_notification.refresh_from_db()
        other_supply_notification.refresh_from_db()
        self.assertTrue(supply_notification.is_read)
        self.assertFalse(inventory_notification.is_read)
        self.assertFalse(other_supply_notification.is_read)

    def test_mark_operations_automation_read_preserves_history_notifications(self):
        user = User.objects.create_user("automation-area-reader")
        automation_notification = Notification.objects.create(
            user=user,
            title="Automation update",
            message="A reminder was generated.",
            link="/dashboard/operations-automation/",
        )
        history_notification = Notification.objects.create(
            user=user,
            title="Automation history",
            message="An event was recorded.",
            link="/dashboard/operations-automation/history/",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse(
                "mark_notification_area_read",
                kwargs={"area": "operations_automation"},
            )
        )

        self.assertEqual(response.status_code, 200)
        automation_notification.refresh_from_db()
        history_notification.refresh_from_db()
        self.assertTrue(automation_notification.is_read)
        self.assertFalse(history_notification.is_read)

    def test_mark_read_only_updates_the_authenticated_users_notifications(self):
        user = User.objects.create_user("notification-owner")
        other_user = User.objects.create_user("other-notification-owner")
        owned_notification = Notification.objects.create(
            user=user,
            title="Supply request update",
            message="Your request was approved.",
        )
        other_notification = Notification.objects.create(
            user=other_user,
            title="Private notification",
            message="This belongs to another user.",
        )
        self.client.force_login(user)

        response = self.client.post(reverse("mark_notifications_read"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["unread_count"], 0)
        owned_notification.refresh_from_db()
        other_notification.refresh_from_db()
        self.assertTrue(owned_notification.is_read)
        self.assertFalse(other_notification.is_read)


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
