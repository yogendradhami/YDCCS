from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from bookings.models import Booking
from employees.models import Employee
from rosters.models import Roster

from .models import GoogleReview
from .calendar_utils import delete_booking_event, delete_roster_event
from .review_utils import get_google_reviews_api, get_public_google_reviews
from googleapiclient.errors import HttpError

from google_reviews.calendar_utils import (
    CalendarNotConfigured,
    CalendarServiceUnavailable,
    create_or_update_booking_event,
    create_or_update_roster_event,
)


class GoogleReviewsUtilsTests(TestCase):
    def test_get_public_google_reviews_returns_db_reviews(self):
        GoogleReview.objects.create(
            review_id="review-1",
            reviewer_name="Alicia",
            comment="Excellent service and attention to detail.",
            rating="5",
            review_date=timezone.now(),
        )

        reviews = get_public_google_reviews(limit=3)

        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["reviewer_name"], "Alicia")
        self.assertEqual(reviews[0]["comment"], "Excellent service and attention to detail.")
        self.assertEqual(reviews[0]["rating"], "⭐⭐⭐⭐⭐")


class CalendarDeleteRetryTests(TestCase):
    def setUp(self):
        self.employee = Employee.objects.create(
            full_name="Calendar Employee",
            phone="0400000000",
        )
        self.booking = Booking.objects.create(
            service_type="Office Cleaning",
            booking_date=timezone.localdate(),
            booking_time=timezone.localtime().time().replace(second=0, microsecond=0),
            address="1 King Street",
            suburb_postcode="Adelaide 5000",
            assigned_employee=self.employee,
            google_calendar_event_id="booking-event-1",
        )
        self.roster = Roster.objects.create(
            employee=self.employee,
            booking=self.booking,
            shift_date=self.booking.booking_date,
            start_time=self.booking.booking_time,
            end_time=self.booking.booking_time,
            google_calendar_event_id="roster-event-1",
        )

    def test_booking_delete_failure_preserves_event_id_for_retry(self):
        service = MagicMock()
        service.events.return_value.delete.return_value.execute.side_effect = RuntimeError(
            "calendar unavailable"
        )
        with patch(
            "google_reviews.calendar_utils.get_employee_google_calendar_service",
            return_value=service,
        ), self.assertLogs("google_reviews.calendar_utils", level="ERROR"):
            result = delete_booking_event(self.booking)

        self.assertFalse(result)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.google_calendar_event_id, "booking-event-1")

    def test_roster_delete_failure_preserves_event_id_for_retry(self):
        service = MagicMock()
        service.events.return_value.delete.return_value.execute.side_effect = RuntimeError(
            "calendar unavailable"
        )
        with patch(
            "google_reviews.calendar_utils.get_employee_google_calendar_service",
            return_value=service,
        ), self.assertLogs("google_reviews.calendar_utils", level="ERROR"):
            result = delete_roster_event(self.roster)

        self.assertFalse(result)
        self.roster.refresh_from_db()
        self.assertEqual(self.roster.google_calendar_event_id, "roster-event-1")

    def test_get_google_reviews_api_returns_empty_without_account(self):
        with patch("google_reviews.review_utils.GoogleAccount.objects") as objects_mock:
            objects_mock.first.return_value = None
            self.assertEqual(get_google_reviews_api(), [])

    def test_get_google_reviews_api_parses_reviews_successfully(self):
        account = MagicMock(
            access_token="test_token",
            refresh_token="refresh_token",
            save=MagicMock(),
        )

        def request_side_effect(url, headers, timeout):
            response = MagicMock()
            if url.endswith("/accounts"):
                response.status_code = 200
                response.json.return_value = {"accounts": [{"name": "accounts/123"}]}
            elif "/reviews" in url:
                response.status_code = 200
                response.json.return_value = {
                    "reviews": [
                        {
                            "reviewer": {"displayName": "Sam"},
                            "comment": "Great job",
                            "starRating": "FIVE",
                            "createTime": "2026-07-23T12:00:00Z",
                        }
                    ]
                }
            elif "/locations" in url:
                response.status_code = 200
                response.json.return_value = {
                    "locations": [{"name": "accounts/123/locations/456"}]
                }
            else:
                response.status_code = 404
                response.json.return_value = {}
            return response

        with patch("google_reviews.review_utils.GoogleAccount.objects") as objects_mock:
            objects_mock.first.return_value = account
            with patch("google_reviews.review_utils.requests.get", side_effect=request_side_effect):
                reviews = get_google_reviews_api()

        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["reviewer_name"], "Sam")
        self.assertEqual(reviews[0]["comment"], "Great job")
        self.assertEqual(reviews[0]["rating"], "⭐⭐⭐⭐⭐")



    def test_booking_delete_404_clears_stale_event_id(self):
        service = MagicMock()
        service.events.return_value.delete.return_value.execute.side_effect = (
            HttpError(
                MagicMock(status=404),
                b'{"error": {"message": "Not Found"}}',
            )
        )

        with patch(
            "google_reviews.calendar_utils.get_employee_google_calendar_service",
            return_value=service,
        ):
            result = delete_booking_event(self.booking)

        self.assertTrue(result)
        self.booking.refresh_from_db()
        self.assertIsNone(self.booking.google_calendar_event_id)

    def test_roster_delete_404_clears_stale_event_id(self):
        service = MagicMock()
        service.events.return_value.delete.return_value.execute.side_effect = (
            HttpError(
                MagicMock(status=404),
                b'{"error": {"message": "Not Found"}}',
            )
        )

        with patch(
            "google_reviews.calendar_utils.get_employee_google_calendar_service",
            return_value=service,
        ):
            result = delete_roster_event(self.roster)

        self.assertTrue(result)
        self.roster.refresh_from_db()
        self.assertIsNone(self.roster.google_calendar_event_id)




class CalendarEventRecoveryTests(CalendarDeleteRetryTests):
    """Regression tests for stale Google Calendar event IDs."""

    def _not_found_error(self):
        return HttpError(
            MagicMock(status=404),
            b'{"error": {"message": "Not Found"}}',
        )

    def _make_calendar_service(self, update_error=None):
        service = MagicMock()

        if update_error is not None:
            service.events.return_value.update.return_value.execute.side_effect = (
                update_error
            )

        service.events.return_value.insert.return_value.execute.return_value = {
            "id": "replacement-event-123"
        }

        return service

    def test_booking_update_404_creates_replacement_event(self):
        service = self._make_calendar_service(self._not_found_error())

        with patch(
            "google_reviews.calendar_utils.get_employee_google_calendar_service",
            return_value=service,
        ):
            create_or_update_booking_event(self.booking)

        service.events.return_value.insert.assert_called_once()
        self.booking.refresh_from_db()
        self.assertEqual(
            self.booking.google_calendar_event_id,
            "replacement-event-123",
        )

    def test_roster_update_404_creates_replacement_event(self):
        service = self._make_calendar_service(self._not_found_error())

        with patch(
            "google_reviews.calendar_utils.get_employee_google_calendar_service",
            return_value=service,
        ):
            create_or_update_roster_event(self.roster)

        service.events.return_value.insert.assert_called_once()
        self.roster.refresh_from_db()
        self.assertEqual(
            self.roster.google_calendar_event_id,
            "replacement-event-123",
        )

    def test_roster_create_retry_reuses_stable_event_id(self):
        service = MagicMock()
        update_attempts = 0

        def update_event():
            nonlocal update_attempts
            update_attempts += 1
            if update_attempts == 1:
                raise self._not_found_error()
            return {"id": self.roster.google_calendar_event_id}

        service.events.return_value.update.return_value.execute.side_effect = (
            update_event
        )
        service.events.return_value.insert.return_value.execute.side_effect = (
            RuntimeError("Calendar response unavailable")
        )
        self.roster.google_calendar_event_id = None
        self.roster.save(update_fields=["google_calendar_event_id"])

        with patch(
            "google_reviews.calendar_utils.get_employee_google_calendar_service",
            return_value=service,
        ):
            with self.assertRaises(RuntimeError):
                create_or_update_roster_event(self.roster)

            self.roster.refresh_from_db()
            stable_event_id = self.roster.google_calendar_event_id
            self.assertRegex(stable_event_id, r"^r[0-9a-v]{52}$")
            self.assertEqual(
                service.events.return_value.insert.call_args.kwargs["body"]["id"],
                stable_event_id,
            )

            create_or_update_roster_event(self.roster)

        self.roster.refresh_from_db()
        self.assertEqual(self.roster.google_calendar_event_id, stable_event_id)
        service.events.return_value.insert.assert_called_once()
        self.assertEqual(service.events.return_value.update.call_count, 2)

    def test_missing_roster_calendar_service_is_explicit(self):
        with patch(
            "google_reviews.calendar_utils.get_employee_google_calendar_service",
            return_value=None,
        ):
            with self.assertRaises(CalendarNotConfigured):
                create_or_update_roster_event(self.roster)

        self.roster.refresh_from_db()
        self.assertEqual(self.roster.google_calendar_event_id, "roster-event-1")

    def test_booking_update_non_404_error_does_not_insert(self):
        service = self._make_calendar_service(
            HttpError(
                MagicMock(status=403),
                b'{"error": {"message": "Forbidden"}}',
            )
        )

        with patch(
            "google_reviews.calendar_utils.get_employee_google_calendar_service",
            return_value=service,
        ):
            with self.assertRaises(HttpError):
                create_or_update_booking_event(self.booking)

        service.events.return_value.insert.assert_not_called()
        self.booking.refresh_from_db()
        self.assertEqual(
            self.booking.google_calendar_event_id,
            "booking-event-1",
        )
