from django.contrib.auth.models import User
from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.urls import reverse
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

from .models import Employee


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
