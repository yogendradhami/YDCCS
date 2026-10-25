from datetime import date, time
from unittest.mock import call, patch

from django.contrib.auth.models import User
from django.db import connection
from django.test import Client, TestCase
from django.urls import reverse

from bookings.models import Booking
from employees.models import Employee

from .models import Roster
from .services import (
    RosterSyncNotConfigured,
    RosterSyncPending,
    sync_booking_roster,
)


class BookingRosterSyncTests(TestCase):
    def setUp(self):
        self.old_user = User.objects.create_user("old-roster-employee")
        self.new_user = User.objects.create_user("new-roster-employee")
        self.old_employee = Employee.objects.create(
            user=self.old_user,
            full_name="Old Employee",
            phone="0400000000",
        )
        self.new_employee = Employee.objects.create(
            user=self.new_user,
            full_name="New Employee",
            phone="0400000001",
        )
        self.booking = Booking.objects.create(
            service_type="Office Cleaning",
            booking_date=date(2026, 10, 23),
            booking_time=time(9, 0),
            address="1 King Street",
            suburb_postcode="Adelaide 5000",
            assigned_employee=self.old_employee,
        )
        self.roster = Roster.objects.create(
            employee=self.old_employee,
            booking=self.booking,
            shift_date=self.booking.booking_date,
            start_time=self.booking.booking_time,
            end_time=time(11, 0),
            google_calendar_event_id="old-calendar-event",
        )

    @patch("google_reviews.calendar_utils.create_or_update_roster_event")
    @patch("google_reviews.calendar_utils.delete_roster_event")
    def test_reassignment_removes_old_employee_event_before_moving_roster(
        self, delete_event, update_event
    ):
        def delete_and_clear(roster):
            roster.google_calendar_event_id = None
            roster.save(update_fields=["google_calendar_event_id"])
            return True

        delete_event.side_effect = delete_and_clear
        self.booking.assigned_employee = self.new_employee
        self.booking.save(update_fields=["assigned_employee"])

        roster = sync_booking_roster(self.booking)

        roster.refresh_from_db()
        self.assertEqual(roster.employee, self.new_employee)
        self.assertIsNone(roster.google_calendar_event_id)
        delete_event.assert_called_once()
        update_event.assert_called_once_with(roster)

    @patch("google_reviews.calendar_utils.create_or_update_roster_event")
    @patch("google_reviews.calendar_utils.delete_roster_event", return_value=False)
    def test_failed_reassignment_delete_keeps_old_assignment_and_event_id(
        self, delete_event, update_event
    ):
        self.booking.assigned_employee = self.new_employee
        self.booking.save(update_fields=["assigned_employee"])

        result = sync_booking_roster(self.booking)

        self.roster.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertIsInstance(result, RosterSyncPending)
        self.assertEqual(self.booking.assigned_employee_id, self.old_employee.pk)
        self.assertEqual(self.roster.employee, self.old_employee)
        self.assertEqual(
            self.roster.google_calendar_event_id,
            "old-calendar-event",
        )
        delete_event.assert_called_once()
        update_event.assert_not_called()

    @patch("google_reviews.calendar_utils.create_or_update_roster_event")
    @patch("google_reviews.calendar_utils.delete_roster_event", return_value=False)
    def test_failed_reassignment_does_not_change_roster_assignment(
        self, delete_event, update_event
    ):
        self.booking.assigned_employee = self.new_employee
        self.booking.save(update_fields=["assigned_employee"])

        result = sync_booking_roster(self.booking)

        self.roster.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertIsInstance(result, RosterSyncPending)
        self.assertEqual(self.booking.assigned_employee_id, self.old_employee.pk)
        self.assertEqual(self.roster.employee, self.old_employee)
        self.assertEqual(
            self.roster.google_calendar_event_id,
            "old-calendar-event",
        )
        delete_event.assert_called_once()
        update_event.assert_not_called()

    @patch("google_reviews.calendar_utils.create_or_update_roster_event")
    @patch("google_reviews.calendar_utils.delete_roster_event", return_value=False)
    def test_cancelled_booking_keeps_event_id_when_remote_delete_fails(
        self, delete_event, update_event
    ):
        self.booking.status = "cancelled"
        self.booking.save(update_fields=["status"])

        result = sync_booking_roster(self.booking)

        self.roster.refresh_from_db()
        self.assertIsInstance(result, RosterSyncPending)
        self.assertEqual(self.roster.status, "cancelled")
        self.assertEqual(
            self.roster.google_calendar_event_id,
            "old-calendar-event",
        )
        delete_event.assert_called_once()
        update_event.assert_not_called()

    @patch("google_reviews.calendar_utils.create_or_update_roster_event", return_value=None)
    def test_missing_calendar_service_is_distinguished_from_sync_failure(
        self, update_event
    ):
        result = sync_booking_roster(self.booking)

        self.roster.refresh_from_db()
        self.assertIsInstance(result, RosterSyncNotConfigured)
        self.assertEqual(self.roster.google_calendar_event_id, "old-calendar-event")
        update_event.assert_called_once()

    @patch("google_reviews.calendar_utils.create_or_update_roster_event")
    def test_calendar_exception_is_pending_and_retry_can_succeed(self, update_event):
        update_event.side_effect = [
            RuntimeError("Calendar temporarily unavailable"),
            {"id": "old-calendar-event"},
        ]

        result = sync_booking_roster(self.booking)

        self.assertIsInstance(result, RosterSyncPending)
        self.roster.refresh_from_db()
        self.assertEqual(
            self.roster.google_calendar_event_id,
            "old-calendar-event",
        )

        result = sync_booking_roster(self.booking)

        self.assertIsInstance(result, Roster)
        update_event.assert_has_calls(
            [call(self.roster), call(self.roster)]
        )

    @patch("google_reviews.calendar_utils.create_or_update_roster_event")
    @patch("google_reviews.calendar_utils.delete_roster_event")
    def test_stale_sync_rechecks_assignment_after_calendar_deletion(
        self, delete_event, update_event
    ):
        latest_employee = Employee.objects.create(
            full_name="Latest Employee",
            phone="0400000002",
        )

        def delete_old_event(roster):
            roster.google_calendar_event_id = None
            roster.save(update_fields=["google_calendar_event_id"])
            Booking.objects.filter(pk=self.booking.pk).update(
                assigned_employee=latest_employee
            )
            return True

        def create_latest_event(roster):
            self.assertTrue(connection.in_atomic_block)
            self.assertEqual(roster.employee_id, latest_employee.pk)
            return {"id": "latest-employee-event"}

        delete_event.side_effect = delete_old_event
        update_event.side_effect = create_latest_event
        self.booking.assigned_employee = self.new_employee
        self.booking.save(update_fields=["assigned_employee"])

        roster = sync_booking_roster(self.booking)

        self.booking.refresh_from_db()
        roster.refresh_from_db()
        self.assertEqual(self.booking.assigned_employee_id, latest_employee.pk)
        self.assertEqual(roster.employee_id, latest_employee.pk)
        update_event.assert_called_once()
        delete_event.assert_called_once()

    @patch("google_reviews.calendar_utils.create_or_update_roster_event")
    @patch("google_reviews.calendar_utils.delete_roster_event")
    def test_roster_suppression_flag_is_restored_after_save_error(
        self, delete_event, update_event
    ):
        captured_rosters = []
        self.roster.google_calendar_event_id = None
        self.roster.save(update_fields=["google_calendar_event_id"])
        self.booking.assigned_employee = self.new_employee
        self.booking.save(update_fields=["assigned_employee"])

        from django.db.models import Model

        original_save = Model.save

        def fail_roster_move(roster, *args, **kwargs):
            if kwargs.get("update_fields") and "employee" in kwargs["update_fields"]:
                captured_rosters.append(roster)
                raise RuntimeError("database unavailable")
            return original_save(roster, *args, **kwargs)

        with patch("rosters.models.Roster.save", autospec=True, side_effect=fail_roster_move):
            with self.assertRaises(RuntimeError):
                sync_booking_roster(self.booking)

        self.assertEqual(len(captured_rosters), 1)
        self.assertFalse(
            hasattr(captured_rosters[0], "_suppress_roster_notifications")
        )
        update_event.assert_not_called()


class RosterMutationAuthorizationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "roster-admin",
            is_staff=True,
        )
        self.employee_user = User.objects.create_user("roster-employee")
        self.other_user = User.objects.create_user("other-roster-employee")
        self.employee = Employee.objects.create(
            user=self.employee_user,
            full_name="Roster Employee",
            phone="0400000000",
        )
        self.other_employee = Employee.objects.create(
            user=self.other_user,
            full_name="Other Employee",
            phone="0400000001",
        )
        self.booking = Booking.objects.create(
            service_type="Office Cleaning",
            booking_date=date(2026, 10, 23),
            booking_time=time(9, 0),
            address="1 King Street",
            suburb_postcode="Adelaide 5000",
            assigned_employee=self.employee,
        )
        self.roster = Roster.objects.create(
            employee=self.employee,
            booking=self.booking,
            shift_date=self.booking.booking_date,
            start_time=self.booking.booking_time,
            end_time=time(11, 0),
            google_calendar_event_id="roster-event",
        )
        self.client = Client()

    def test_employee_cannot_add_edit_or_delete_rosters(self):
        self.client.force_login(self.employee_user)

        add_response = self.client.post(reverse("add_roster"), {})
        edit_response = self.client.post(
            reverse("edit_roster", args=[self.roster.pk]),
            {},
        )
        delete_response = self.client.post(
            reverse("delete_roster", args=[self.roster.pk]),
        )
        edit_page_response = self.client.get(
            reverse("edit_roster", args=[self.roster.pk]),
        )
        delete_page_response = self.client.get(
            reverse("delete_roster", args=[self.roster.pk]),
        )

        self.assertEqual(add_response.status_code, 403)
        self.assertEqual(edit_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)
        self.assertEqual(edit_page_response.status_code, 403)
        self.assertEqual(delete_page_response.status_code, 403)
        self.assertTrue(Roster.objects.filter(pk=self.roster.pk).exists())
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.assigned_employee_id, self.employee.pk)

    @patch("google_reviews.calendar_utils.create_or_update_roster_event")
    def test_admin_can_add_and_edit_rosters_without_changing_assignment(
        self, update_event
    ):
        update_event.return_value = {"id": "new-event"}
        self.client.force_login(self.admin)
        new_booking = Booking.objects.create(
            service_type="Office Cleaning",
            booking_date=date(2026, 10, 24),
            booking_time=time(10, 0),
            address="2 Queen Street",
            suburb_postcode="Adelaide 5000",
            assigned_employee=self.employee,
        )

        response = self.client.post(
            reverse("add_roster"),
            {
                "employee": self.employee.pk,
                "booking": new_booking.pk,
                "shift_date": "2026-10-24",
                "start_time": "10:00",
                "end_time": "12:00",
                "status": "scheduled",
                "notes": "New shift",
            },
        )
        self.assertRedirects(
            response,
            reverse("roster_list"),
            fetch_redirect_response=False,
        )
        created_roster = Roster.objects.get(booking=new_booking)

        response = self.client.post(
            reverse("edit_roster", args=[self.roster.pk]),
            {
                "employee": self.other_employee.pk,
                "booking": new_booking.pk,
                "shift_date": "2026-10-25",
                "start_time": "11:00",
                "end_time": "13:00",
                "status": "scheduled",
                "notes": "Updated shift",
            },
        )

        self.assertRedirects(
            response,
            reverse("roster_list"),
            fetch_redirect_response=False,
        )
        self.roster.refresh_from_db()
        self.assertEqual(self.roster.employee_id, self.employee.pk)
        self.assertEqual(self.roster.booking_id, self.booking.pk)
        self.assertEqual(self.roster.shift_date, date(2026, 10, 25))
        self.assertEqual(self.roster.notes, "Updated shift")
        self.assertTrue(Roster.objects.filter(pk=created_roster.pk).exists())
        update_event.assert_called()

    @patch("google_reviews.calendar_utils.delete_roster_event", return_value=True)
    def test_admin_can_delete_roster(self, delete_event):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("delete_roster", args=[self.roster.pk]),
        )

        self.assertRedirects(
            response,
            reverse("roster_list"),
            fetch_redirect_response=False,
        )
        self.assertFalse(Roster.objects.filter(pk=self.roster.pk).exists())
        delete_event.assert_called_once()

    @patch("google_reviews.calendar_utils.delete_roster_event", return_value=False)
    def test_failed_calendar_delete_preserves_roster_for_retry(self, delete_event):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("delete_roster", args=[self.roster.pk]),
        )

        self.assertRedirects(
            response,
            reverse("roster_list"),
            fetch_redirect_response=False,
        )
        self.roster.refresh_from_db()
        self.assertEqual(
            self.roster.google_calendar_event_id,
            "roster-event",
        )
        self.assertTrue(Roster.objects.filter(pk=self.roster.pk).exists())
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("was not deleted" in str(message) for message in messages))
