from django.contrib.auth.models import User
from django.test import TestCase

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
