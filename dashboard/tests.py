from unittest.mock import patch
from datetime import date, datetime, time, timedelta

from django.contrib.messages import get_messages
from django.test import TestCase, Client, override_settings
from django.core import mail
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.db.models import Model
from django.utils import timezone

from core.test_utils import grant_dashboard_permissions, mark_public_email_verified
from bookings.forms import BookingForm
from customers.models import Customer
from dashboard.models import CareerApplication
from bookings.models import Booking
from employees.models import Employee
from rosters.models import Roster
from quotes.models import QuoteRequest
from quotes.models import QuoteImage
from invoices.models import Invoice


class DashboardLoginLayoutTests(TestCase):
    def test_login_omits_why_choose_and_faq_sections(self):
        response = self.client.get(reverse("dashboard_login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="yd-main-header"')
        self.assertContains(response, 'class="premium-footer"')
        self.assertNotContains(response, 'class="yd-why-choose-section"')
        self.assertNotContains(response, 'id="yd-faq-section"')


@override_settings(
	EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
	ADMIN_EMAIL="admin@example.com",
)
class CareerEmailTests(TestCase):
	def setUp(self):
		self.client = Client()
		mail.get_connection()
		mail.outbox.clear()

	def test_application_submission_sends_email(self):
		data = {
			"full_name": "Test Applicant",
			"email": "applicant@example.com",
			"phone": "0412345678",
			"position": "residential_cleaner",
			"years_cleaning_experience": "1",
			"cover_letter": "I am interested.",
			"consent": "on",
		}
		resume = SimpleUploadedFile("resume.pdf", b"%PDF-1.4 fakepdf", content_type="application/pdf")
		mark_public_email_verified(self.client, data["email"])

		response = self.client.post(reverse("careers"), data={**data}, files={"resume": resume})
		self.assertEqual(response.status_code, 302)

		self.assertEqual(len(mail.outbox), 2)
		confirmation, notification = mail.outbox
		self.assertIn("Application Received", confirmation.subject)
		self.assertEqual(confirmation.to, ["applicant@example.com"])
		self.assertIn("New Career Application", notification.subject)
		self.assertEqual(notification.to, ["admin@example.com"])

		app = CareerApplication.objects.filter(email="applicant@example.com").first()
		self.assertIsNotNone(app)

	def test_admin_update_sends_email(self):
		app = CareerApplication.objects.create(full_name="Jane Doe", email="jane@example.com")

		User = get_user_model()
		admin = User.objects.create_user("admin", "admin@example.com", "pass")
		admin.is_staff = True
		admin.save()
		grant_dashboard_permissions(admin, "dashboard.change_careerapplication")

		self.client.force_login(admin)

		url = reverse("career_detail", args=[app.id])
		response = self.client.post(url, {"status": "reviewing", "admin_notes": "Please review CV."})
		self.assertEqual(response.status_code, 302)

		# One email should be sent
		self.assertGreaterEqual(len(mail.outbox), 1)
		last = mail.outbox[-1]
		self.assertIn("Application Update", last.subject)
		app.refresh_from_db()
		self.assertEqual(app.status, "reviewing")


class BookingCalendarDeletionTests(TestCase):
	def setUp(self):
		user_model = get_user_model()
		self.admin = user_model.objects.create_user(
			"booking-admin",
			password="Admin password 123!",
			is_staff=True,
		)
		grant_dashboard_permissions(self.admin, "bookings.delete_booking")
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
			google_calendar_event_id="booking-event",
		)
		self.roster = Roster.objects.create(
			employee=self.employee,
			booking=self.booking,
			shift_date=self.booking.booking_date,
			start_time=self.booking.booking_time,
			end_time=self.booking.booking_time,
			google_calendar_event_id="roster-event",
		)
		self.client.force_login(self.admin)

	@patch("dashboard.views.delete_booking_event", return_value=True)
	@patch("dashboard.views.delete_roster_event", return_value=True)
	def test_booking_delete_link_opens_confirmation_and_deletes_booking(
		self, delete_roster_event_mock, delete_booking_event_mock
	):
		booking_id = self.booking.pk
		delete_url = reverse("delete_booking", args=[booking_id])
		response = self.client.get(delete_url)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Confirm Delete")
		self.assertTrue(Booking.objects.filter(pk=booking_id).exists())

		response = self.client.post(delete_url)

		self.assertRedirects(
			response,
			reverse("booking_list"),
			fetch_redirect_response=False,
		)
		self.assertFalse(Booking.objects.filter(pk=booking_id).exists())
		delete_roster_event_mock.assert_called_once()
		delete_booking_event_mock.assert_called_once()

	@patch("dashboard.views.delete_booking_event", return_value=True)
	@patch("dashboard.views.delete_roster_event", return_value=False)
	def test_booking_is_deleted_when_roster_calendar_event_cannot_be_removed(
		self, delete_roster_event_mock, delete_booking_event_mock
	):
		booking_id = self.booking.pk
		response = self.client.post(reverse("delete_booking", args=[booking_id]))

		self.assertRedirects(response, reverse("booking_list"), fetch_redirect_response=False)
		self.assertFalse(Booking.objects.filter(pk=booking_id).exists())
		self.assertFalse(Roster.objects.filter(pk=self.roster.pk).exists())
		delete_roster_event_mock.assert_called_once_with(self.roster)
		delete_booking_event_mock.assert_called_once()
		self.assertTrue(
			any("Booking deleted" in str(message) for message in get_messages(response.wsgi_request))
		)

	@patch("dashboard.views.delete_booking_event", return_value=True)
	@patch("dashboard.views.delete_roster_event", return_value=True)
	def test_booking_and_related_invoice_can_be_deleted(
		self, delete_roster_event_mock, delete_booking_event_mock
	):
		invoice = Invoice.objects.create(booking=self.booking)

		response = self.client.post(reverse("delete_booking", args=[self.booking.pk]))

		self.assertRedirects(
			response,
			reverse("booking_list"),
			fetch_redirect_response=False,
		)
		self.assertFalse(Booking.objects.filter(pk=self.booking.pk).exists())
		self.assertFalse(Invoice.objects.filter(pk=invoice.pk).exists())


class QuoteCompletionStateTests(TestCase):
	def setUp(self):
		self.admin = get_user_model().objects.create_user(
			"quote-admin",
			password="Admin password 123!",
			is_staff=True,
		)
		grant_dashboard_permissions(
			self.admin,
			"quotes.change_quoterequest",
			"bookings.add_booking",
		)
		self.client.force_login(self.admin)
		self.quote = QuoteRequest.objects.create(
			name="Quote Customer",
			email="quote-state@example.com",
			phone="0400000000",
			property_type="Office",
			suburb_postcode="Adelaide 5000",
		)

	def test_quote_cannot_be_marked_completed_before_linked_booking(self):
		response = self.client.post(
			reverse("update_quote_status", args=[self.quote.pk]),
			{"status": "completed"},
		)

		self.assertEqual(response.status_code, 302)
		self.quote.refresh_from_db()
		self.assertEqual(self.quote.status, "new")

	def test_quote_can_be_completed_after_linked_booking_completion(self):
		booking = Booking.objects.create(
			service_type="Office Cleaning",
			booking_date=date(2026, 10, 23),
			booking_time=time(9, 0),
			address="1 King Street",
			suburb_postcode="Adelaide 5000",
			status="completed",
			idempotency_key=f"quote:{self.quote.pk}",
		)

		response = self.client.post(
			reverse("update_quote_status", args=[self.quote.pk]),
			{"status": "completed"},
		)

		self.assertEqual(response.status_code, 302)
		self.quote.refresh_from_db()
		self.assertEqual(self.quote.status, "completed")
		self.assertEqual(booking.idempotency_key, f"quote:{self.quote.pk}")


@override_settings(
	EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
	ADMIN_EMAIL="company@example.com",
)
class DashboardBookingEmailTests(TestCase):
	def setUp(self):
		mail.outbox.clear()
		self.admin = get_user_model().objects.create_user(
			"booking-email-admin",
			email="booking-admin@example.com",
			password="test-password",
			is_staff=True,
		)
		grant_dashboard_permissions(self.admin, "bookings.add_booking")
		self.client.force_login(self.admin)
		self.customer = Customer.objects.create(
			full_name="Booking Email Customer",
			email="booking-customer@example.com",
			phone="0400000000",
		)

	@patch("dashboard.views.create_or_update_booking_event")
	@patch("rosters.services.sync_booking_roster", return_value=None)
	def test_new_booking_emails_customer_and_company(
		self,
		_sync_roster,
		_sync_company_calendar,
	):
		response = self.client.post(
			reverse("add_booking"),
			{
				"customer": self.customer.pk,
				"service_type": "Office Cleaning",
				"quoted_price": "125.00",
				"booking_date": (date.today() + timedelta(days=3)).isoformat(),
				"booking_time": "10:00",
				"address": "1 King Street",
				"suburb_postcode": "Adelaide 5000",
				"assigned_employee": "",
				"status": "pending",
				"notes": "",
				"work_orders-TOTAL_FORMS": "1",
				"work_orders-INITIAL_FORMS": "0",
				"work_orders-MIN_NUM_FORMS": "1",
				"work_orders-MAX_NUM_FORMS": "1000",
				"work_orders-0-service_type": "Office Cleaning",
				"work_orders-0-price": "125.00",
			},
		)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(len(mail.outbox), 2)
		customer_email, company_email = mail.outbox
		self.assertEqual(customer_email.to, ["booking-customer@example.com"])
		self.assertIn("Booking request received", customer_email.subject)
		self.assertEqual(company_email.to, ["company@example.com"])
		self.assertIn("New booking created", company_email.subject)
		self.assertIn("Office Cleaning", company_email.body)


class QuoteLeadManagementTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            "lead-manager",
            password="test-password",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(self.admin)

    def make_quote(self, **overrides):
        data = {
            "name": "Lead Customer",
            "email": "lead@example.com",
            "phone": "0400000000",
            "property_type": "House",
            "suburb_postcode": "Adelaide 5000",
            "message": "Please quote my home cleaning",
            "bedrooms": 3,
            "bathrooms": 2,
            "lead_source": "website",
            "estimated_price": 260,
            "status": "new",
        }
        data.update(overrides)
        return QuoteRequest.objects.create(**data)

    def test_lead_list_filters_search_and_paginates(self):
        self.make_quote(name="Filter Match", email="match@example.com")
        for index in range(12):
            self.make_quote(
                name=f"Other Lead {index}",
                email=f"other-{index}@example.com",
                status="contacted",
            )

        response = self.client.get(
            reverse("lead_list"),
            {
                "q": "Filter Match",
                "status": "new",
                "page_size": "10",
                "page": "1",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["filtered_count"], 1)
        self.assertEqual(len(response.context["quotes"]), 1)
        self.assertEqual(response.context["quotes"][0].name, "Filter Match")

    def test_lead_list_paginates_filtered_results_and_keeps_filters(self):
        for index in range(12):
            self.make_quote(
                name=f"Paged Lead {index}",
                email=f"paged-{index}@example.com",
                status="contacted",
            )
        response = self.client.get(
            reverse("lead_list"),
            {"status": "contacted", "page_size": "10", "page": "2"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["quotes"]), 2)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertContains(response, "status=contacted")
        self.assertContains(response, "page_size=10")

    def test_lead_list_filters_by_property_source_and_submission_date(self):
        matching = self.make_quote(
            name="Date Filter Match",
            property_type="Office",
            lead_source="referral",
        )
        outside = self.make_quote(
            name="Date Filter Outside",
            email="outside@example.com",
            property_type="House",
            lead_source="website",
        )
        QuoteRequest.objects.filter(pk=matching.pk).update(
            created_at=timezone.make_aware(
                datetime(2026, 10, 20), timezone.get_current_timezone()
            )
        )
        QuoteRequest.objects.filter(pk=outside.pk).update(
            created_at=timezone.make_aware(
                datetime(2026, 10, 10), timezone.get_current_timezone()
            )
        )

        response = self.client.get(
            reverse("lead_list"),
            {
                "property_type": "Office",
                "lead_source": "referral",
                "date_from": "2026-10-15",
                "date_to": "2026-10-25",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["filtered_count"], 1)
        self.assertEqual(response.context["quotes"][0].pk, matching.pk)

    def test_lead_list_shows_every_public_submission_field(self):
        quote = self.make_quote(
            name="All Fields Customer",
            property_type="Office",
            suburb_postcode="Norwood 5067",
            preferred_date=date(2026, 11, 5),
            message="Clean office and meeting rooms",
            lead_source="referral",
            window_cleaning=True,
            carpet_shampooing=True,
            grout_cleaning=True,
            upholstery_cleaning=True,
            laundry_service=True,
        )

        response = self.client.get(reverse("lead_list"))

        self.assertEqual(response.status_code, 200)
        for expected in (
            quote.name,
            quote.email,
            quote.phone,
            "Office",
            "Norwood 5067",
            "Nov",
            "Clean office and meeting rooms",
            "Bedrooms",
            "Bathrooms",
            "Referral",
            "Window cleaning",
            "Carpet shampooing",
            "Grout cleaning",
            "Upholstery cleaning",
            "Laundry service",
        ):
            with self.subTest(expected=expected):
                self.assertContains(response, expected)

    def test_delete_lead_requires_post_and_removes_quote_images(self):
        quote = self.make_quote()
        QuoteImage.objects.create(quote=quote, image="quote_images/test-lead.jpg")
        storage = QuoteImage._meta.get_field("image").storage

        with patch.object(storage, "delete") as delete_image:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    reverse("delete_quote_request", args=[quote.pk])
                )
            delete_image.assert_called_once_with("quote_images/test-lead.jpg")

        self.assertRedirects(response, reverse("lead_list"))
        self.assertFalse(QuoteRequest.objects.filter(pk=quote.pk).exists())
        self.assertFalse(QuoteImage.objects.filter(quote_id=quote.pk).exists())

    def test_delete_lead_rejects_get(self):
        quote = self.make_quote()
        response = self.client.get(
            reverse("delete_quote_request", args=[quote.pk])
        )
        self.assertEqual(response.status_code, 405)
        self.assertTrue(QuoteRequest.objects.filter(pk=quote.pk).exists())

    def test_delete_lead_requires_delete_permission(self):
        quote = self.make_quote()
        user = get_user_model().objects.create_user(
            "lead-viewer", password="test-password", is_staff=True
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("delete_quote_request", args=[quote.pk])
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(QuoteRequest.objects.filter(pk=quote.pk).exists())




class BookingReassignmentFailureTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            "reassignment-admin",
            password="Admin password 123!",
            is_staff=True,
        )
        grant_dashboard_permissions(self.admin, "bookings.change_booking")
        self.old_user = user_model.objects.create_user("old-reassignment-employee")
        self.new_user = user_model.objects.create_user("new-reassignment-employee")

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
            google_calendar_event_id="old-roster-event",
        )
        self.client.force_login(self.admin)

    def _post_booking(self, **changes):
        data = {
            "service_type": self.booking.service_type,
            "booking_date": self.booking.booking_date.isoformat(),
            "booking_time": "09:00",
            "address": self.booking.address,
            "suburb_postcode": self.booking.suburb_postcode,
            "quoted_price": str(self.booking.quoted_price),
            "assigned_employee": str(self.old_employee.pk),
            "status": self.booking.status,
            "notes": self.booking.notes,
        }
        data.update(changes)
        return self.client.post(
            reverse("edit_booking", args=[self.booking.pk]),
            data,
            follow=False,
        )

    @patch("dashboard.views.create_or_update_booking_event")
    @patch("google_reviews.calendar_utils.create_or_update_roster_event")
    @patch("dashboard.views.Notification.objects.create")
    @patch("dashboard.views.get_or_create_invoice_for_booking")
    @patch("dashboard.views.send_booking_confirmation_email")
    @patch("dashboard.views.delete_roster_event", return_value=False)
    def test_failed_reassignment_preserves_consistent_assignment(
        self,
        delete_event,
        send_status_email,
        create_invoice,
        create_notification,
        update_roster_event,
        update_booking_event,
    ):
        create_invoice.invoice_number = "INV-TEST"
        create_invoice.return_value = (create_invoice, False)
        response = self._post_booking(
            address="2 Queen Street",
            assigned_employee=str(self.new_employee.pk),
            status="completed",
        )

        self.booking.refresh_from_db()
        self.roster.refresh_from_db()

        self.assertEqual(self.booking.assigned_employee_id, self.old_employee.pk)
        self.assertEqual(self.booking.address, "2 Queen Street")
        self.assertEqual(self.booking.status, "completed")
        self.assertEqual(self.roster.employee_id, self.old_employee.pk)
        self.assertEqual(
            self.roster.google_calendar_event_id,
            "old-roster-event",
        )
        delete_event.assert_called_once()
        send_status_email.assert_not_called()
        create_invoice.assert_not_called()
        create_notification.assert_not_called()
        update_roster_event.assert_not_called()
        update_booking_event.assert_not_called()
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("booking_list"),
            fetch_redirect_response=False,
        )
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("could not be synced" in str(message) for message in messages))
        self.assertFalse(
            any("Booking updated successfully" in str(message) for message in messages)
        )
        self.assertFalse(
            any("Invoice automatically created" in str(message) for message in messages)
        )

    @patch(
        "dashboard.views.BookingForm.save",
        autospec=True,
        side_effect=RuntimeError("database unavailable"),
    )
    @patch("google_reviews.calendar_utils.create_or_update_roster_event")
    @patch("dashboard.views.delete_roster_event")
    def test_database_save_failure_restores_deleted_old_calendar_event(
        self, delete_event, restore_event, save_booking
    ):
        def delete_old_event(roster):
            self.assertTrue(connection.in_atomic_block)
            roster.google_calendar_event_id = None
            roster.save(update_fields=["google_calendar_event_id"])
            return True

        def restore_old_event(roster):
            roster.google_calendar_event_id = "restored-old-roster-event"
            roster.save(update_fields=["google_calendar_event_id"])
            return {"id": roster.google_calendar_event_id}

        delete_event.side_effect = delete_old_event
        restore_event.side_effect = restore_old_event

        response = self._post_booking(
            assigned_employee=str(self.new_employee.pk),
        )

        self.booking.refresh_from_db()
        self.roster.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.booking.assigned_employee_id, self.old_employee.pk)
        self.assertEqual(self.roster.employee_id, self.old_employee.pk)
        self.assertEqual(
            self.roster.google_calendar_event_id,
            "restored-old-roster-event",
        )
        delete_event.assert_called_once()
        restore_event.assert_called_once()
        save_booking.assert_called_once()
        saved_form = save_booking.call_args.args[0]
        self.assertFalse(
            hasattr(
                saved_form.instance,
                "_suppress_employee_assignment_notification",
            )
        )
        self.assertFalse(
            hasattr(
                saved_form.instance,
                "_suppress_customer_status_notification",
            )
        )
        messages = list(response.wsgi_request._messages)
        self.assertTrue(
            any("booking could not be saved" in str(message) for message in messages)
        )
        self.assertFalse(
            any("Booking updated successfully" in str(message) for message in messages)
        )

    @patch("dashboard.views.BookingForm.save", autospec=True, side_effect=RuntimeError("database unavailable"))
    @patch(
        "google_reviews.calendar_utils.create_or_update_roster_event",
        return_value=None,
    )
    @patch("dashboard.views.delete_roster_event")
    def test_missing_calendar_service_during_restoration_is_reported(
        self, delete_event, restore_event, save_booking
    ):
        def delete_old_event(roster):
            roster.google_calendar_event_id = None
            roster.save(update_fields=["google_calendar_event_id"])
            return True

        delete_event.side_effect = delete_old_event
        response = self._post_booking(
            assigned_employee=str(self.new_employee.pk),
        )

        self.booking.refresh_from_db()
        self.roster.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.booking.assigned_employee_id, self.old_employee.pk)
        self.assertEqual(self.roster.employee_id, self.old_employee.pk)
        self.assertIsNone(self.roster.google_calendar_event_id)
        restore_event.assert_called_once()
        save_booking.assert_called_once()
        messages = list(response.wsgi_request._messages)
        self.assertTrue(
            any("could not be restored yet" in str(message) for message in messages)
        )
        self.assertFalse(
            any("Calendar event was restored" in str(message) for message in messages)
        )

    @patch("rosters.models.Roster.save", autospec=True)
    @patch("google_reviews.calendar_utils.create_or_update_roster_event")
    @patch("dashboard.views.delete_roster_event")
    def test_roster_database_failure_restores_old_calendar_event(
        self, delete_event, restore_event, save_roster
    ):
        def fail_roster_move(roster, *args, **kwargs):
            if "employee" in kwargs.get("update_fields", ()):
                raise RuntimeError("database unavailable")
            return Model.save(roster, *args, **kwargs)

        save_roster.side_effect = fail_roster_move

        def delete_old_event(roster):
            roster.google_calendar_event_id = None
            roster.save(update_fields=["google_calendar_event_id"])
            return True

        def restore_old_event(roster):
            roster.google_calendar_event_id = "restored-old-roster-event"
            roster.save(update_fields=["google_calendar_event_id"])
            return {"id": roster.google_calendar_event_id}

        delete_event.side_effect = delete_old_event
        restore_event.side_effect = restore_old_event

        response = self._post_booking(
            assigned_employee=str(self.new_employee.pk),
        )

        self.booking.refresh_from_db()
        self.roster.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.booking.assigned_employee_id, self.old_employee.pk)
        self.assertEqual(self.roster.employee_id, self.old_employee.pk)
        self.assertEqual(
            self.roster.google_calendar_event_id,
            "restored-old-roster-event",
        )
        delete_event.assert_called_once()
        restore_event.assert_called_once()
        messages = list(response.wsgi_request._messages)
        self.assertTrue(
            any("reassignment failed and was rolled back" in str(message) for message in messages)
        )

    @patch("dashboard.views.create_or_update_booking_event")
    @patch("dashboard.views.Notification.objects.create")
    @patch("dashboard.views.get_or_create_invoice_for_booking")
    @patch("dashboard.views.send_booking_confirmation_email")
    @patch("google_reviews.calendar_utils.create_or_update_roster_event")
    @patch("dashboard.views.delete_roster_event")
    def test_new_employee_calendar_failure_keeps_consistent_retryable_assignment(
        self,
        delete_event,
        update_roster_event,
        send_status_email,
        create_invoice,
        create_notification,
        update_booking_event,
    ):
        def delete_old_event(roster):
            roster.google_calendar_event_id = None
            roster.save(update_fields=["google_calendar_event_id"])
            return True

        create_attempts = 0

        def create_new_event(roster):
            nonlocal create_attempts
            create_attempts += 1
            roster.google_calendar_event_id = "retryable-new-roster-event"
            roster.save(update_fields=["google_calendar_event_id"])
            if create_attempts == 1:
                raise RuntimeError("Calendar unavailable")
            return {"id": roster.google_calendar_event_id}

        delete_event.side_effect = delete_old_event
        update_roster_event.side_effect = create_new_event
        create_invoice.invoice_number = "INV-TEST"
        create_invoice.return_value = (create_invoice, False)

        response = self._post_booking(
            assigned_employee=str(self.new_employee.pk),
            status="completed",
        )

        self.booking.refresh_from_db()
        self.roster.refresh_from_db()
        self.assertEqual(self.booking.assigned_employee_id, self.new_employee.pk)
        self.assertEqual(self.roster.employee_id, self.new_employee.pk)
        self.assertEqual(
            self.roster.google_calendar_event_id,
            "retryable-new-roster-event",
        )
        self.assertEqual(response.status_code, 302)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(
            any(
                "new employee's roster Calendar event could not be synchronized"
                in str(message)
                for message in messages
            )
        )
        self.assertFalse(
            any("Booking updated successfully" in str(message) for message in messages)
        )
        send_status_email.assert_not_called()
        create_invoice.assert_not_called()
        create_notification.assert_not_called()
        update_booking_event.assert_not_called()

        retry_response = self._post_booking(
            assigned_employee=str(self.new_employee.pk),
            status="completed",
        )

        self.roster.refresh_from_db()
        self.assertEqual(retry_response.status_code, 302)
        self.assertEqual(self.roster.employee_id, self.new_employee.pk)
        self.assertEqual(
            self.roster.google_calendar_event_id,
            "retryable-new-roster-event",
        )
        self.assertEqual(update_roster_event.call_count, 2)

    @patch("dashboard.views.create_or_update_booking_event")
    @patch("google_reviews.calendar_utils.create_or_update_roster_event")
    @patch("dashboard.views.Notification.objects.create")
    @patch("dashboard.views.delete_roster_event")
    def test_successful_reassignment_moves_roster_and_updates_calendar(
        self, delete_event, create_notification, update_roster_event, update_booking_event
    ):
        def delete_old_event(roster):
            self.assertTrue(connection.in_atomic_block)
            roster.google_calendar_event_id = None
            roster.save(update_fields=["google_calendar_event_id"])
            return True

        def create_new_event(roster):
            roster.google_calendar_event_id = "new-roster-event"
            roster.save(update_fields=["google_calendar_event_id"])
            return {"id": "new-roster-event"}

        delete_event.side_effect = delete_old_event
        update_roster_event.side_effect = create_new_event

        response = self._post_booking(
            assigned_employee=str(self.new_employee.pk),
        )

        self.booking.refresh_from_db()
        self.roster.refresh_from_db()
        self.assertEqual(self.booking.assigned_employee_id, self.new_employee.pk)
        self.assertEqual(self.roster.employee_id, self.new_employee.pk)
        self.assertEqual(
            self.roster.google_calendar_event_id,
            "new-roster-event",
        )
        delete_event.assert_called_once()
        self.assertEqual(
            delete_event.call_args.args[0].employee_id,
            self.old_employee.pk,
        )
        update_roster_event.assert_called_once()
        self.assertEqual(
            update_roster_event.call_args.args[0].employee_id,
            self.new_employee.pk,
        )
        update_booking_event.assert_called_once()
        create_notification.assert_any_call(
            user=self.new_user,
            title="Booking Updated",
            message=(
                f"Booking updated: {self.booking.service_type} "
                f"on {self.booking.booking_date} at {self.booking.booking_time}."
            ),
            notification_type="booking",
            link="/employee/jobs/",
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("booking_list"),
            fetch_redirect_response=False,
        )

    @patch("dashboard.views.create_or_update_booking_event")
    @patch("dashboard.views.Notification.objects.create")
    @patch("dashboard.views.get_or_create_invoice_for_booking")
    @patch("dashboard.views.send_booking_confirmation_email")
    @patch(
        "google_reviews.calendar_utils.create_or_update_roster_event",
        return_value=None,
    )
    @patch("dashboard.views.delete_roster_event")
    def test_missing_new_employee_calendar_service_keeps_assignment_consistent(
        self,
        delete_event,
        update_roster_event,
        send_status_email,
        create_invoice,
        create_notification,
        update_booking_event,
    ):
        def delete_old_event(roster):
            roster.google_calendar_event_id = None
            roster.save(update_fields=["google_calendar_event_id"])
            return True

        delete_event.side_effect = delete_old_event

        response = self._post_booking(
            assigned_employee=str(self.new_employee.pk),
            status="completed",
        )

        self.booking.refresh_from_db()
        self.roster.refresh_from_db()
        self.assertEqual(self.booking.assigned_employee_id, self.new_employee.pk)
        self.assertEqual(self.roster.employee_id, self.new_employee.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(self.roster.google_calendar_event_id)
        update_roster_event.assert_called_once()
        send_status_email.assert_not_called()
        create_invoice.assert_not_called()
        create_notification.assert_not_called()
        update_booking_event.assert_not_called()
        messages = list(response.wsgi_request._messages)
        self.assertTrue(
            any(
                "new employee has not connected Google Calendar"
                in str(message)
                for message in messages
            )
        )
        self.assertFalse(
            any("Booking updated successfully" in str(message) for message in messages)
        )

    @patch("dashboard.views.create_or_update_booking_event")
    @patch("google_reviews.calendar_utils.create_or_update_roster_event")
    @patch("dashboard.views.delete_roster_event")
    def test_reassignment_suppression_flags_are_restored_after_success(
        self, delete_event, update_roster_event, update_booking_event
    ):
        original_form_save = BookingForm.save
        saved_instances = []

        def save_and_capture(form, *args, **kwargs):
            saved_instances.append(form.instance)
            self.assertTrue(
                form.instance._suppress_employee_assignment_notification
            )
            self.assertTrue(
                form.instance._suppress_customer_status_notification
            )
            return original_form_save(form, *args, **kwargs)

        def delete_old_event(roster):
            roster.google_calendar_event_id = None
            roster.save(update_fields=["google_calendar_event_id"])
            return True

        delete_event.side_effect = delete_old_event
        with patch(
            "dashboard.views.BookingForm.save",
            autospec=True,
            side_effect=save_and_capture,
        ):
            response = self._post_booking(
                assigned_employee=str(self.new_employee.pk),
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(saved_instances), 1)
        self.assertFalse(
            hasattr(
                saved_instances[0],
                "_suppress_employee_assignment_notification",
            )
        )
        self.assertFalse(
            hasattr(
                saved_instances[0],
                "_suppress_customer_status_notification",
            )
        )
        update_booking_event.assert_called_once()

    @patch("dashboard.views.delete_roster_event")
    @patch("rosters.services.booking_roster_sync_lock")
    def test_reassignment_fails_safely_when_database_lock_is_unavailable(
        self, acquire_lock, delete_event
    ):
        from rosters.services import RosterSyncLockError

        acquire_lock.side_effect = RosterSyncLockError("lock unavailable")

        response = self._post_booking(
            assigned_employee=str(self.new_employee.pk),
        )

        self.booking.refresh_from_db()
        self.roster.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.booking.assigned_employee_id, self.old_employee.pk)
        self.assertEqual(self.roster.employee_id, self.old_employee.pk)
        self.assertEqual(
            self.roster.google_calendar_event_id,
            "old-roster-event",
        )
        delete_event.assert_not_called()
        messages = list(response.wsgi_request._messages)
        self.assertTrue(
            any("could not be safely serialized" in str(message) for message in messages)
        )
        self.assertFalse(
            any("Booking updated successfully" in str(message) for message in messages)
        )

    @patch("dashboard.views.create_or_update_booking_event")
    @patch("google_reviews.calendar_utils.create_or_update_roster_event")
    @patch("dashboard.views.Notification.objects.create")
    def test_ordinary_booking_edit_still_updates_booking_and_roster(
        self, create_notification, update_roster_event, update_booking_event
    ):
        response = self._post_booking(
            address="2 Queen Street",
            notes="Use the side entrance",
        )

        self.booking.refresh_from_db()
        self.roster.refresh_from_db()
        self.assertEqual(self.booking.address, "2 Queen Street")
        self.assertEqual(self.roster.notes, "Use the side entrance")
        self.assertEqual(self.booking.assigned_employee_id, self.old_employee.pk)
        update_roster_event.assert_called_once_with(self.roster)
        update_booking_event.assert_called_once()
        create_notification.assert_called_once()
        self.assertEqual(response.status_code, 302)

    @patch("dashboard.views.create_or_update_booking_event")
    @patch("google_reviews.calendar_utils.create_or_update_roster_event")
    @patch("dashboard.views.send_booking_confirmation_email", return_value=True)
    def test_status_transition_still_sends_customer_email(
        self, send_status_email, update_roster_event, update_booking_event
    ):
        response = self._post_booking(status="confirmed")

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "confirmed")
        send_status_email.assert_called_once()
        self.assertEqual(send_status_email.call_args.args[2], "pending")
        update_roster_event.assert_called_once()
        update_booking_event.assert_called_once()
        self.assertEqual(response.status_code, 302)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(
            any("Customer notified by email" in str(message) for message in messages)
        )

    @patch("dashboard.views.create_or_update_booking_event")
    @patch("dashboard.views.send_invoice_email")
    @patch("dashboard.views.get_or_create_invoice_for_booking")
    @patch("dashboard.views.send_booking_confirmation_email")
    @patch("rosters.services.sync_booking_roster")
    def test_quick_status_sync_failure_suppresses_success_and_downstream_effects(
        self,
        sync_roster,
        send_status_email,
        create_invoice,
        send_invoice,
        sync_booking_event,
    ):
        from rosters.services import RosterSyncPending

        sync_roster.return_value = RosterSyncPending(
            roster=self.roster,
            error=RuntimeError("Calendar unavailable"),
        )

        response = self.client.post(
            reverse(
                "update_booking_quick_status",
                args=[self.booking.pk, "completed"],
            ),
        )

        self.booking.refresh_from_db()
        messages = list(response.wsgi_request._messages)
        self.assertEqual(self.booking.status, "completed")
        send_status_email.assert_not_called()
        create_invoice.assert_not_called()
        send_invoice.assert_not_called()
        sync_booking_event.assert_not_called()
        self.assertFalse(
            any("status updated successfully" in str(message) for message in messages)
        )
        self.assertTrue(
            any("could not be synced" in str(message) for message in messages)
        )

    @patch("google_reviews.calendar_utils.create_or_update_roster_event")
    @patch("dashboard.views.delete_roster_event")
    def test_reassignment_to_no_employee_cancels_roster_after_deletion(
        self, delete_event, update_roster_event
    ):
        def delete_old_event(roster):
            roster.google_calendar_event_id = None
            roster.save(update_fields=["google_calendar_event_id"])
            return True

        delete_event.side_effect = delete_old_event

        self._post_booking(assigned_employee="")

        self.booking.refresh_from_db()
        self.roster.refresh_from_db()
        self.assertIsNone(self.booking.assigned_employee_id)
        self.assertEqual(self.roster.employee_id, self.old_employee.pk)
        self.assertEqual(self.roster.status, "cancelled")
        self.assertIsNone(self.roster.google_calendar_event_id)
        delete_event.assert_called_once()
        update_roster_event.assert_not_called()

    @patch("google_reviews.calendar_utils.create_or_update_roster_event")
    @patch("google_reviews.calendar_utils.delete_roster_event")
    def test_cancellation_still_cancels_roster_and_removes_event(
        self, delete_event, update_roster_event
    ):
        def delete_old_event(roster):
            roster.google_calendar_event_id = None
            roster.save(update_fields=["google_calendar_event_id"])
            return True

        delete_event.side_effect = delete_old_event

        self._post_booking(status="cancelled")

        self.booking.refresh_from_db()
        self.roster.refresh_from_db()
        self.assertEqual(self.booking.status, "cancelled")
        self.assertEqual(self.roster.status, "cancelled")
        self.assertIsNone(self.roster.google_calendar_event_id)
        delete_event.assert_called_once()
        update_roster_event.assert_not_called()

    @patch("dashboard.views.create_or_update_booking_event")
    @patch("google_reviews.calendar_utils.create_or_update_roster_event")
    @patch("dashboard.views.delete_roster_event")
    def test_cancelled_reassignment_keeps_booking_and_roster_assignments_aligned(
        self, delete_event, update_roster_event, update_booking_event
    ):
        def delete_old_event(roster):
            roster.google_calendar_event_id = None
            roster.save(update_fields=["google_calendar_event_id"])
            return True

        delete_event.side_effect = delete_old_event

        response = self._post_booking(
            assigned_employee=str(self.new_employee.pk),
            status="cancelled",
        )

        self.booking.refresh_from_db()
        self.roster.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.booking.assigned_employee_id, self.new_employee.pk)
        self.assertEqual(self.roster.employee_id, self.new_employee.pk)
        self.assertEqual(self.roster.status, "cancelled")
        self.assertIsNone(self.roster.google_calendar_event_id)
        delete_event.assert_called_once()
        update_roster_event.assert_not_called()
        update_booking_event.assert_called_once()
