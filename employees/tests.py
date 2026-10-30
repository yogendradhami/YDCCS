from django.contrib.auth.models import User
from django.db import DatabaseError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io
import tempfile
from unittest.mock import patch
from datetime import date, time

from core.test_utils import grant_dashboard_permissions
from induction.models import EmployeeInduction, InductionProgramme
from bookings.models import Booking, JobPhoto
from customers.models import Customer
from invoices.models import Invoice
from quotes.models import QuoteRequest
from notifications.models import Notification

from .models import (
	Employee,
	EmployeeGoogleAccount,
	PropertyDamageImage,
	PropertyDamageReport,
	PropertyDamageReportPresence,
	PropertyDamageReportReply,
)


def _damage_report_image(name):
	buffer = io.BytesIO()
	Image.new("RGB", (16, 16), color="red").save(buffer, format="JPEG")
	return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


class EmployeeDamageReportTests(TestCase):
	def setUp(self):
		self.media_directory = tempfile.TemporaryDirectory()
		self.addCleanup(self.media_directory.cleanup)
		self.media_settings = override_settings(MEDIA_ROOT=self.media_directory.name)
		self.media_settings.enable()
		self.addCleanup(self.media_settings.disable)

		self.user = User.objects.create_user(
			username="damage-report-employee",
			password="test-password",
		)
		self.employee = Employee.objects.create(
			user=self.user,
			full_name="Damage Report Employee",
			phone="0400000000",
		)
		programme = InductionProgramme.objects.create(
			name="Damage report induction",
		)
		EmployeeInduction.objects.create(
			employee=self.employee,
			programme=programme,
			status="completed",
		)
		self.booking = Booking.objects.create(
			service_type="House Cleaning",
			booking_date=date(2026, 10, 29),
			booking_time=time(9, 0),
			address="12 King Street",
			suburb_postcode="Adelaide 5000",
			assigned_employee=self.employee,
		)
		self.client.force_login(self.user)

	def test_employee_can_submit_report_with_multiple_images(self):
		response = self.client.post(
			reverse("employee_damage_report"),
			{
				"booking": self.booking.pk,
				"description": "A tile was cracked near the kitchen sink.",
				"images": [
					_damage_report_image("damage-one.jpg"),
					_damage_report_image("damage-two.jpg"),
				],
			},
		)

		self.assertRedirects(response, reverse("employee_damage_report"))
		report = PropertyDamageReport.objects.get()
		self.assertEqual(report.employee, self.employee)
		self.assertEqual(report.booking, self.booking)
		self.assertEqual(
			report.description,
			"A tile was cracked near the kitchen sink.",
		)
		self.assertEqual(PropertyDamageImage.objects.filter(report=report).count(), 2)

	def test_new_damage_report_notifies_dashboard_staff(self):
		staff_user = User.objects.create_user(
			username="damage-report-dashboard-staff",
			password="test-password",
			is_staff=True,
		)

		response = self.client.post(
			reverse("employee_damage_report"),
			{
				"booking": self.booking.pk,
				"description": "A tile was cracked near the kitchen sink.",
			},
		)

		report = PropertyDamageReport.objects.get()
		self.assertRedirects(response, reverse("employee_damage_report"))
		notification = Notification.objects.get(user=staff_user)
		self.assertEqual(notification.notification_type, "damage_report")
		self.assertEqual(
			notification.link,
			f"/dashboard/property-damage-reports/#report-{report.pk}",
		)

	def test_dashboard_reply_is_saved_and_notifies_employee_portal(self):
		report = PropertyDamageReport.objects.create(
			employee=self.employee,
			booking=self.booking,
			description="A tile was cracked near the kitchen sink.",
		)
		admin = User.objects.create_user(
			username="damage-report-reply-admin",
			password="test-password",
			is_staff=True,
		)
		grant_dashboard_permissions(
			admin,
			"employees.change_propertydamagereport",
		)
		self.client.force_login(admin)

		response = self.client.post(
			reverse("property_damage_report_reply", args=[report.pk]),
			{f"reply-{report.pk}-message": "Thank you for reporting this."},
		)

		self.assertEqual(response.status_code, 302)
		reply = PropertyDamageReportReply.objects.get(report=report)
		self.assertEqual(reply.responder, admin)
		self.assertEqual(reply.message, "Thank you for reporting this.")
		notification = Notification.objects.get(
			user=self.user,
			notification_type="damage_report",
		)
		self.assertEqual(notification.notification_type, "damage_report")
		self.assertEqual(
			notification.link,
			f"/employee/damage-report/#report-{report.pk}",
		)

		self.client.force_login(self.user)
		employee_response = self.client.get(reverse("employee_damage_report"))
		self.assertEqual(employee_response.status_code, 200)
		self.assertContains(employee_response, "Thank you for reporting this.")

	def test_dashboard_can_close_and_reopen_ticket_and_employee_is_notified(self):
		report = PropertyDamageReport.objects.create(
			employee=self.employee,
			booking=self.booking,
			description="A tile was cracked near the kitchen sink.",
		)
		admin = User.objects.create_user(
			username="damage-report-close-admin",
			password="test-password",
			is_staff=True,
		)
		grant_dashboard_permissions(
			admin,
			"employees.change_propertydamagereport",
		)
		self.client.force_login(admin)

		close_response = self.client.post(
			reverse("property_damage_report_set_status", args=[report.pk]),
		)

		self.assertEqual(close_response.status_code, 302)
		report.refresh_from_db()
		self.assertEqual(report.status, PropertyDamageReport.STATUS_CLOSED)
		self.assertIsNotNone(report.closed_at)
		self.assertEqual(report.closed_by, admin)
		self.assertTrue(
			Notification.objects.filter(
				user=self.user,
				title=f"Property damage report #{report.pk} closed",
			).exists()
		)

		self.client.force_login(self.user)
		employee_response = self.client.get(reverse("employee_damage_report"))
		self.assertContains(employee_response, "Resolved &amp; closed")
		self.assertContains(employee_response, "This report has been resolved and closed.")

		self.client.force_login(admin)
		reopen_response = self.client.post(
			reverse("property_damage_report_set_status", args=[report.pk]),
		)

		self.assertEqual(reopen_response.status_code, 302)
		report.refresh_from_db()
		self.assertEqual(report.status, PropertyDamageReport.STATUS_OPEN)
		self.assertIsNone(report.closed_at)
		self.assertIsNone(report.closed_by)

	def test_conversation_polling_and_typing_presence_work_for_both_sides(self):
		report = PropertyDamageReport.objects.create(
			employee=self.employee,
			booking=self.booking,
			description="A damaged tile needs review.",
		)
		admin = User.objects.create_user(
			username="damage-report-live-admin",
			password="test-password",
			is_staff=True,
		)
		grant_dashboard_permissions(
			admin,
			"employees.view_employee",
			"employees.change_propertydamagereport",
		)

		employee_url = reverse(
			"employee_property_damage_report_conversation",
			args=[report.pk],
		)
		employee_poll = self.client.get(employee_url)
		self.assertEqual(employee_poll.status_code, 200)
		self.assertEqual(employee_poll.json()["replies"], [])
		presence = PropertyDamageReportPresence.objects.get(
			report=report,
			user=self.user,
		)
		self.assertFalse(presence.is_typing)

		typing_response = self.client.post(
			employee_url,
			{"is_typing": "true"},
		)
		self.assertEqual(typing_response.status_code, 200)

		self.client.force_login(admin)
		dashboard_url = reverse(
			"property_damage_report_conversation",
			args=[report.pk],
		)
		dashboard_poll = self.client.get(dashboard_url)
		self.assertEqual(dashboard_poll.status_code, 200)
		self.assertEqual(
			dashboard_poll.json()["presence"],
			[{"name": self.employee.full_name, "is_typing": True}],
		)

		reply_response = self.client.post(
			reverse("property_damage_report_reply", args=[report.pk]),
			{f"reply-{report.pk}-message": "We are looking into this now."},
			HTTP_X_REQUESTED_WITH="XMLHttpRequest",
		)
		self.assertEqual(reply_response.status_code, 200)
		self.assertEqual(reply_response.json(), {"ok": True})

		self.client.force_login(self.user)
		updated_conversation = self.client.get(employee_url).json()
		self.assertEqual(
			updated_conversation["replies"][0]["message"],
			"We are looking into this now.",
		)
		self.assertEqual(
			updated_conversation["replies"][0]["role"],
			"dashboard",
		)

		self.client.force_login(admin)
		admin_typing = self.client.post(
			dashboard_url,
			{"is_typing": "true"},
		)
		self.assertEqual(admin_typing.status_code, 200)
		self.client.force_login(self.user)
		employee_presence = self.client.get(employee_url).json()["presence"]
		self.assertEqual(
			employee_presence,
			[{"name": admin.username, "is_typing": True}],
		)

		employee_reply_response = self.client.post(
			reverse(
				"employee_property_damage_report_reply",
				args=[report.pk],
			),
			{"message": "Thanks, I will wait for your update."},
			HTTP_X_REQUESTED_WITH="XMLHttpRequest",
		)
		self.assertEqual(employee_reply_response.status_code, 200)
		self.assertEqual(employee_reply_response.json(), {"ok": True})
		self.client.force_login(admin)
		dashboard_replies = self.client.get(dashboard_url).json()["replies"]
		self.assertEqual(
			dashboard_replies[-1]["message"],
			"Thanks, I will wait for your update.",
		)
		self.assertEqual(dashboard_replies[-1]["role"], "employee")

	def test_employee_conversation_endpoint_cannot_read_other_employee_report(self):
		other_employee = Employee.objects.create(
			full_name="Other Live Chat Employee",
			phone="0400000003",
		)
		report = PropertyDamageReport.objects.create(
			employee=other_employee,
			booking=self.booking,
			description="Private damage report.",
		)

		response = self.client.get(
			reverse(
				"employee_property_damage_report_conversation",
				args=[report.pk],
			)
		)

		self.assertEqual(response.status_code, 404)

	def test_employee_can_respond_to_own_report_and_notifies_dashboard(self):
		report = PropertyDamageReport.objects.create(
			employee=self.employee,
			booking=self.booking,
			description="A tile was cracked near the kitchen sink.",
		)
		staff_user = User.objects.create_user(
			username="damage-report-response-staff",
			password="test-password",
			is_staff=True,
		)

		response = self.client.post(
			reverse(
				"employee_property_damage_report_reply",
				args=[report.pk],
			),
			{"message": "I have added a close-up photo for clarity."},
		)

		self.assertRedirects(
			response,
			f"{reverse('employee_damage_report')}#report-{report.pk}",
			fetch_redirect_response=False,
		)
		reply = PropertyDamageReportReply.objects.get(report=report)
		self.assertEqual(reply.responder, self.user)
		self.assertEqual(
			reply.message,
			"I have added a close-up photo for clarity.",
		)
		notification = Notification.objects.get(
			user=staff_user,
			notification_type="damage_report",
		)
		self.assertEqual(
			notification.link,
			f"/dashboard/property-damage-reports/#report-{report.pk}",
		)
		report.refresh_from_db()
		self.assertEqual(report.status, PropertyDamageReport.STATUS_OPEN)

		portal_response = self.client.get(reverse("employee_damage_report"))
		self.assertContains(portal_response, "I have added a close-up photo for clarity.")
		self.assertContains(portal_response, ">You</strong>")

	def test_employee_reply_reopens_closed_ticket_and_notifies_dashboard(self):
		report = PropertyDamageReport.objects.create(
			employee=self.employee,
			booking=self.booking,
			description="Resolved damage report.",
			status=PropertyDamageReport.STATUS_CLOSED,
			closed_at=timezone.now(),
		)
		staff_user = User.objects.create_user(
			username="damage-report-reopen-staff",
			password="test-password",
			is_staff=True,
		)

		response = self.client.post(
			reverse("employee_property_damage_report_reply", args=[report.pk]),
			{"message": "The issue needs further attention."},
		)

		self.assertEqual(response.status_code, 302)
		report.refresh_from_db()
		self.assertEqual(report.status, PropertyDamageReport.STATUS_OPEN)
		self.assertIsNone(report.closed_at)
		self.assertIsNone(report.closed_by)
		self.assertTrue(
			Notification.objects.filter(
				user=staff_user,
				title=f"Reopened property damage report #{report.pk}",
			).exists()
		)

	def test_employee_cannot_respond_to_another_employees_report(self):
		other_employee = Employee.objects.create(
			full_name="Other Damage Report Employee",
			phone="0400000002",
		)
		report = PropertyDamageReport.objects.create(
			employee=other_employee,
			booking=self.booking,
			description="A report belonging to another employee.",
		)

		response = self.client.post(
			reverse(
				"employee_property_damage_report_reply",
				args=[report.pk],
			),
			{"message": "I should not be able to respond to this report."},
		)

		self.assertEqual(response.status_code, 404)
		self.assertFalse(PropertyDamageReportReply.objects.filter(report=report).exists())

	def test_employee_cannot_report_against_another_employees_booking(self):
		other_employee = Employee.objects.create(
			full_name="Another Employee",
			phone="0400000001",
		)
		other_booking = Booking.objects.create(
			service_type="Office Cleaning",
			booking_date=date(2026, 10, 30),
			booking_time=time(10, 0),
			address="1 King William Road",
			suburb_postcode="Adelaide 5000",
			assigned_employee=other_employee,
		)

		response = self.client.post(
			reverse("employee_damage_report"),
			{
				"booking": other_booking.pk,
				"description": "A report outside my assigned jobs.",
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(PropertyDamageReport.objects.count(), 0)
		self.assertContains(response, "Select a valid choice")

	def test_report_requires_an_assigned_job(self):
		response = self.client.post(
			reverse("employee_damage_report"),
			{"description": "Damage without a selected job."},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(PropertyDamageReport.objects.count(), 0)
		self.assertContains(response, "This field is required.")

	def test_dashboard_lists_reports_for_staff_only(self):
		report = PropertyDamageReport.objects.create(
			employee=self.employee,
			booking=self.booking,
			description="Damage next to the kitchen sink.",
		)
		report.images.create(image=_damage_report_image("damage.jpg"))

		response = self.client.get(reverse("property_damage_report_list"))
		self.assertIn(response.status_code, (302, 403))

		staff_user = User.objects.create_user(
			username="damage-report-manager",
			password="test-password",
			is_staff=True,
		)
		grant_dashboard_permissions(
			staff_user,
			"employees.view_employee",
		)
		staff_client = Client()
		staff_client.force_login(staff_user)
		response = staff_client.get(reverse("property_damage_report_list"))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Damage next to the kitchen sink.")
		self.assertContains(response, "Damage Report Employee")
		self.assertContains(response, "12 King Street")
		self.assertContains(response, "Open")
		self.assertContains(response, "Mark resolved &amp; close ticket")
		self.assertContains(response, report.images.get().image.url)
		self.assertContains(
			response,
			f'href="{reverse("property_damage_report_list")}"',
		)


class EmployeePortalLayoutTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			username="employee-layout@example.com",
			password="Employee password 123!",
		)
		self.employee = Employee.objects.create(
			user=self.user,
			full_name="Portal Employee",
			phone="0400123456",
			email=self.user.email,
		)
		programme = InductionProgramme.objects.create(name="Layout test induction")
		EmployeeInduction.objects.create(
			employee=self.employee,
			programme=programme,
			status="completed",
		)

	def test_employee_portal_has_one_portal_header_without_public_sections(self):
		self.client.force_login(self.user)
		response = self.client.get("/employee/jobs/")
		content = response.content.decode()

		self.assertEqual(response.status_code, 200, response.headers.get("Location"))
		self.assertEqual(content.count('class="employee-portal-header"'), 1)
		self.assertContains(response, 'aria-label="Employee portal navigation"')
		self.assertNotContains(response, 'class="yd-main-header"')
		self.assertNotContains(response, 'id="offerBanner"')
		self.assertNotContains(response, 'class="yd-why-choose-section"')
		self.assertNotContains(response, 'id="yd-faq-section"')

	def test_employee_dashboard_offers_google_calendar_connection(self):
		self.client.force_login(self.user)

		response = self.client.get(reverse("employee_dashboard"))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Connect Google Calendar")
		self.assertContains(
			response,
			f'href="{reverse("employee_google_connect")}"',
		)

		EmployeeGoogleAccount.objects.create(
			employee=self.employee,
			access_token="connected-token",
		)
		connected_response = self.client.get(reverse("employee_dashboard"))
		self.assertContains(connected_response, "Reconnect Google Calendar")

	def test_employee_login_keeps_public_header_without_duplicate_brand(self):
		response = self.client.get("/employee/login/")

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'class="auth-card"')
		self.assertContains(response, "Employee Portal")
		self.assertContains(response, 'name="username"')
		self.assertContains(response, 'name="password"')
		self.assertContains(response, 'class="yd-main-header"')
		self.assertContains(response, 'id="offerBanner"')
		self.assertContains(response, 'class="premium-footer"')
		self.assertNotContains(response, 'class="portal-auth-brand"')
		self.assertNotContains(response, "Secure portal access")
		self.assertNotContains(
			response,
			'<img src="/static/images/company/logoo-256.webp"',
		)
		self.assertNotContains(response, 'class="yd-why-choose-section"')
		self.assertNotContains(response, 'id="yd-faq-section"')


class EmployeePasswordChangeTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			username="employee@example.com",
			password="Original password 123!",
		)
		self.employee = Employee.objects.create(
			user=self.user,
			full_name="Test Employee",
			phone="0400123456",
			email="employee@example.com",
		)
		programme = InductionProgramme.objects.create(
			name="Password test induction",
		)
		EmployeeInduction.objects.create(
			employee=self.employee,
			programme=programme,
			status="completed",
		)

	def test_employee_password_change_rejects_wrong_current_password(self):
		self.client.force_login(self.user)
		response = self.client.post(
			"/employee/profile/",
			{
				"form_type": "password",
				"old_password": "wrong password",
				"new_password1": "New secure password 456!",
				"new_password2": "New secure password 456!",
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertTrue(self.user.check_password("Original password 123!"))

	def test_employee_password_change_updates_password(self):
		self.client.force_login(self.user)
		response = self.client.post(
			"/employee/profile/",
			{
				"form_type": "password",
				"old_password": "Original password 123!",
				"new_password1": "New secure password 456!",
				"new_password2": "New secure password 456!",
			},
		)

		self.assertRedirects(response, "/employee/profile/")
		self.user.refresh_from_db()
		self.assertTrue(self.user.check_password("New secure password 456!"))


class EmployeePortalSecurityTests(TestCase):
	def test_employee_cannot_update_booking_assigned_to_another_employee(self):
		user = User.objects.create_user("scoped-employee", "test-password")
		Employee.objects.create(
			user=user,
			full_name="Scoped Employee",
			phone="0400000000",
		)
		employee = Employee.objects.get(user=user)
		programme = InductionProgramme.objects.create(
			name="Scoped booking security induction",
		)
		EmployeeInduction.objects.create(
			employee=employee,
			programme=programme,
			status="completed",
		)
		other_employee = Employee.objects.create(
			full_name="Other Employee",
			phone="0400000001",
		)
		booking = Booking.objects.create(
			service_type="Office Cleaning",
			booking_date=date(2026, 10, 23),
			booking_time=time(9, 0),
			address="1 King Street",
			suburb_postcode="Adelaide 5000",
			assigned_employee=other_employee,
			status="in_progress",
		)
		self.client.force_login(user)

		response = self.client.post(
			reverse("employee_job_detail", args=[booking.pk]),
			{"status": "completed", "notes": "Unauthorized update"},
		)

		self.assertEqual(response.status_code, 404)
		booking.refresh_from_db()
		self.assertEqual(booking.status, "in_progress")
		self.assertEqual(booking.notes, "")

	def test_inactive_employee_session_cannot_access_portal_pages(self):
		user = User.objects.create_user("inactive-employee", password="Password 123!")
		Employee.objects.create(
			user=user,
			full_name="Inactive Employee",
			phone="0400000000",
			active=False,
		)
		self.client.force_login(user)

		for url_name in (
			"employee_dashboard",
			"employee_jobs",
			"employee_profile",
			"employee_google_connect",
			"employee_google_callback",
		):
			with self.subTest(url_name=url_name):
				response = self.client.get(reverse(url_name))
				self.assertRedirects(response, reverse("employee_login"))

	@patch("employees.views.notify_admins")
	@patch("rosters.services.sync_booking_roster")
	@patch("google_reviews.calendar_utils.create_or_update_booking_event")
	def test_employee_completion_creates_report_draft_invoice_and_completes_quote(
		self, _calendar_sync, _roster_sync, _notify_admins
	):
		user = User.objects.create_user("active-employee", password="Password 123!")
		employee = Employee.objects.create(
			user=user,
			full_name="Active Employee",
			phone="0400000000",
		)
		programme = InductionProgramme.objects.create(name="Workflow induction")
		EmployeeInduction.objects.create(
			employee=employee,
			programme=programme,
			status="completed",
		)
		customer = Customer.objects.create(
			full_name="Workflow Customer",
			email="workflow@example.com",
			phone="0400000001",
		)
		booking = Booking.objects.create(
			customer=customer,
			service_type="Office Cleaning",
			booking_date=date(2026, 10, 23),
			booking_time=time(9, 0),
			address="1 King Street",
			suburb_postcode="Adelaide 5000",
			quoted_price="250.00",
			assigned_employee=employee,
			status="in_progress",
		)
		QuoteRequest.objects.create(
			name=customer.full_name,
			email=customer.email,
			phone=customer.phone,
			property_type="Office",
			suburb_postcode="Adelaide 5000",
			idempotency_key=f"quote:{booking.pk}",
		)
		JobPhoto.objects.create(
			booking=booking,
			employee=employee,
			photo_type="before",
			image="job_photos/before.jpg",
			employee_signature="signatures/employee.jpg",
		)
		JobPhoto.objects.create(
			booking=booking,
			employee=employee,
			photo_type="after",
			image="job_photos/after.jpg",
		)
		self.client.force_login(user)

		response = self.client.post(
			reverse("employee_job_detail", args=[booking.pk]),
			{"status": "completed", "notes": "Job completed."},
		)

		self.assertRedirects(
			response,
			reverse("employee_job_detail", args=[booking.pk]),
		)
		booking.refresh_from_db()
		self.assertEqual(booking.status, "completed")
		self.assertTrue(hasattr(booking, "cleaning_report"))
		invoice = Invoice.objects.get(booking=booking)
		self.assertEqual(invoice.status, "draft")
		self.assertEqual(invoice.amount, booking.quoted_price)
		quote = QuoteRequest.objects.get(idempotency_key=f"quote:{booking.pk}")
		self.assertEqual(quote.status, "completed")


class EmployeeDashboardWorkflowTests(TestCase):
	def setUp(self):
		self.admin = User.objects.create_user(
			username="hr-admin",
			password="Admin password 123!",
			is_staff=True,
		)
		grant_dashboard_permissions(
			self.admin,
			"employees.view_employee",
			"employees.add_employee",
			"employees.change_employee",
		)
		self.client.force_login(self.admin)

	def employee_data(self, **overrides):
		data = {
			"full_name": "Jordan Lee",
			"phone": "0400123456",
			"email": "jordan@example.com",
			"address": "12 King Street",
			"role": "cleaner",
			"availability": "available",
			"hourly_rate": "36.50",
			"jobs_completed": "0",
			"active": "on",
			"access_mode": "none",
		}
		data.update(overrides)
		return data

	def post_employee(self, data, files=None):
		return self.client.post(reverse("add_employee"), data={**data, **(files or {})})

	def test_create_employee_without_login(self):
		response = self.post_employee(self.employee_data())
		self.assertRedirects(response, reverse("employee_list"))
		employee = Employee.objects.get(full_name="Jordan Lee")
		self.assertIsNone(employee.user)
		self.assertEqual(User.objects.count(), 1)

	def test_create_employee_with_hashed_non_privileged_login(self):
		response = self.post_employee(self.employee_data(
			access_mode="create",
			login_email="jordan.portal@example.com",
			username="jordan-lee",
			password1="River!Quartz9Cedar",
			password2="River!Quartz9Cedar",
		))
		self.assertRedirects(response, reverse("employee_list"))
		employee = Employee.objects.get(full_name="Jordan Lee")
		account = employee.user
		self.assertEqual(account.email, "jordan.portal@example.com")
		self.assertTrue(account.check_password("River!Quartz9Cedar"))
		self.assertFalse(account.is_staff)
		self.assertFalse(account.is_superuser)
		self.assertNotIn("River!Quartz9Cedar", response.content.decode())

	def test_link_existing_active_unlinked_user(self):
		account = User.objects.create_user(
			username="jordan-login",
			email="jordan.login@example.com",
			password="Existing password 456!",
		)
		response = self.post_employee(self.employee_data(
			access_mode="link",
			existing_user=str(account.pk),
		))
		self.assertRedirects(response, reverse("employee_list"))
		self.assertEqual(Employee.objects.get(full_name="Jordan Lee").user, account)

	def test_already_linked_user_cannot_be_selected_again(self):
		account = User.objects.create_user(
			username="linked-login",
			password="Existing password 456!",
		)
		Employee.objects.create(
			user=account,
			full_name="Existing Employee",
			phone="0400111222",
		)
		response = self.post_employee(self.employee_data(
			access_mode="link",
			existing_user=str(account.pk),
		))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(Employee.objects.count(), 1)
		self.assertContains(response, "Select a valid choice")

	def test_negative_hourly_rate_is_rejected(self):
		response = self.post_employee(self.employee_data(hourly_rate="-1"))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(Employee.objects.count(), 0)
		self.assertContains(response, "Hourly rate cannot be negative.")

	def test_duplicate_login_email_is_rejected(self):
		User.objects.create_user(
			username="already-used",
			email="taken@example.com",
			password="Existing password 456!",
		)
		response = self.post_employee(self.employee_data(
			access_mode="create",
			login_email="taken@example.com",
			username="new-login",
			password1="River!Quartz9Cedar",
			password2="River!Quartz9Cedar",
		))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(Employee.objects.count(), 0)
		self.assertContains(response, "An account already uses this email.")

	def test_duplicate_username_is_rejected(self):
		User.objects.create_user(
			username="existing-login",
			email="someone@example.com",
			password="Existing password 456!",
		)
		response = self.post_employee(self.employee_data(
			access_mode="create",
			login_email="new@example.com",
			username="existing-login",
			password1="River!Quartz9Cedar",
			password2="River!Quartz9Cedar",
		))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(Employee.objects.count(), 0)
		self.assertContains(response, "This username is already in use.")

	def test_invalid_password_is_rejected(self):
		response = self.post_employee(self.employee_data(
			access_mode="create",
			login_email="jordan.portal@example.com",
			username="jordan-lee",
			password1="123",
			password2="123",
		))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(Employee.objects.count(), 0)
		self.assertEqual(User.objects.count(), 1)

	def test_account_is_rolled_back_if_employee_save_fails(self):
		with patch("employees.models.Employee.save", side_effect=DatabaseError("forced failure")):
			response = self.post_employee(self.employee_data(
				access_mode="create",
				login_email="jordan.portal@example.com",
				username="jordan-lee",
				password1="River!Quartz9Cedar",
				password2="River!Quartz9Cedar",
			))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(Employee.objects.count(), 0)
		self.assertFalse(User.objects.filter(username="jordan-lee").exists())
		self.assertContains(response, "We could not save this employee.")

	def test_employee_is_not_saved_if_user_creation_fails(self):
		with patch("django.contrib.auth.models.UserManager.create_user", side_effect=DatabaseError("forced failure")):
			response = self.post_employee(self.employee_data(
				access_mode="create",
				login_email="jordan.portal@example.com",
				username="jordan-lee",
				password1="River!Quartz9Cedar",
				password2="River!Quartz9Cedar",
			))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(Employee.objects.count(), 0)
		self.assertFalse(User.objects.filter(username="jordan-lee").exists())
		self.assertContains(response, "We could not save this employee.")

	def test_non_staff_user_cannot_create_employee_or_login(self):
		self.client.force_login(User.objects.create_user(
			username="regular-user",
			password="Regular password 123!",
		))
		response = self.client.post(reverse("add_employee"), self.employee_data(
			access_mode="create",
			login_email="blocked@example.com",
			username="blocked-login",
			password1="River!Quartz9Cedar",
			password2="River!Quartz9Cedar",
		))
		self.assertIn(response.status_code, {302, 403})
		self.assertEqual(Employee.objects.count(), 0)
		self.assertFalse(User.objects.filter(username="blocked-login").exists())

	def test_employee_photo_upload_is_saved(self):
		image_buffer = io.BytesIO()
		Image.new("RGB", (4, 4), color="teal").save(image_buffer, format="PNG")
		image_buffer.seek(0)
		photo = SimpleUploadedFile(
			"jordan.png",
			image_buffer.read(),
			content_type="image/png",
		)
		with tempfile.TemporaryDirectory() as media_root:
			with override_settings(MEDIA_ROOT=media_root):
				response = self.post_employee(self.employee_data(), {"image": photo})
		self.assertRedirects(response, reverse("employee_list"))
		self.assertTrue(Employee.objects.get(full_name="Jordan Lee").image.name)

	def test_existing_employee_edit_still_updates_profile(self):
		employee = Employee.objects.create(
			full_name="Jordan Lee",
			phone="0400123456",
			email="jordan@example.com",
		)
		data = self.employee_data(full_name="Jordan Lee Updated")
		data["user"] = ""
		response = self.client.post(
			reverse("edit_employee", args=[employee.pk]),
			data=data,
		)
		self.assertRedirects(response, reverse("employee_list"))
		employee.refresh_from_db()
		self.assertEqual(employee.full_name, "Jordan Lee Updated")
