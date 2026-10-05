from django.contrib.auth.models import User
from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io
import tempfile
from unittest.mock import patch

from .models import Employee


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


class EmployeeDashboardWorkflowTests(TestCase):
	def setUp(self):
		self.admin = User.objects.create_user(
			username="hr-admin",
			password="Admin password 123!",
			is_staff=True,
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
