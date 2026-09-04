from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings

from customers.models import Customer


class CustomerRegistrationTests(TestCase):
	def test_registration_rejects_invalid_customer_fields(self):
		response = self.client.post(
			"/portal/register/",
			{
				"full_name": "!!!",
				"email": "not-an-email",
				"phone": "abc",
				"address": "@@@",
				"suburb_postcode": "???",
				"password": "weak",
				"confirm_password": "different",
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(User.objects.count(), 0)
		self.assertEqual(Customer.objects.count(), 0)

	@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
	def test_registration_creates_user_and_customer_from_valid_fields(self):
		response = self.client.post(
			"/portal/register/",
			{
				"full_name": "Jane Smith",
				"email": "Jane.Smith@example.com",
				"phone": "+61 400 123 456",
				"address": "12 King Street",
				"suburb_postcode": "Prospect 5082",
				"password": "A secure password 123!",
				"confirm_password": "A secure password 123!",
			},
		)

		self.assertRedirects(response, "/portal/login/")
		user = User.objects.get(username="jane.smith@example.com")
		customer = Customer.objects.get(user=user)
		self.assertEqual(customer.full_name, "Jane Smith")
		self.assertTrue(user.check_password("A secure password 123!"))
		self.assertFalse(customer.email_verified)
		self.assertEqual(len(mail.outbox), 1)
		self.assertIn("verify-email", mail.outbox[0].body)

	def test_verification_link_verifies_customer_email(self):
		customer = Customer.objects.create(
			full_name="Jane Smith",
			email="jane@example.com",
			phone="0400123456",
			verification_token="verification-token",
		)

		response = self.client.get("/portal/verify-email/verification-token/")

		self.assertRedirects(response, "/portal/login/")
		customer.refresh_from_db()
		self.assertTrue(customer.email_verified)
		self.assertIsNone(customer.verification_token)

	@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
	def test_password_reset_sends_email_for_customer_account(self):
		User.objects.create_user(
			username="reset@example.com",
			email="reset@example.com",
			password="A secure password 123!",
		)

		response = self.client.post(
			"/portal/password-reset/",
			{"email": "reset@example.com"},
		)

		self.assertRedirects(response, "/portal/password-reset/done/")
		self.assertEqual(len(mail.outbox), 1)
		self.assertIn("/portal/reset/", mail.outbox[0].body)

	@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
	def test_customer_can_resend_verification_email(self):
		user = User.objects.create_user(
			username="unverified@example.com",
			email="unverified@example.com",
			password="A secure password 123!",
		)
		Customer.objects.create(
			user=user,
			full_name="Unverified Customer",
			email=user.email,
			phone="0400123456",
			verification_token="existing-token",
		)

		response = self.client.post(
			"/portal/resend-verification/",
			{"email": user.email},
		)

		self.assertRedirects(response, "/portal/login/")
		self.assertEqual(len(mail.outbox), 1)
		self.assertIn("/portal/verify-email/existing-token/", mail.outbox[0].body)

	def test_customer_password_change_rejects_wrong_current_password(self):
		user = User.objects.create_user(
			username="password@example.com",
			password="Original password 123!",
		)
		Customer.objects.create(
			user=user,
			full_name="Password Customer",
			phone="0400123456",
			email_verified=True,
		)
		self.client.force_login(user)

		response = self.client.post(
			"/portal/profile/",
			{
				"form_type": "password",
				"old_password": "wrong password",
				"new_password1": "New secure password 456!",
				"new_password2": "New secure password 456!",
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertTrue(user.check_password("Original password 123!"))

	def test_customer_password_change_updates_password(self):
		user = User.objects.create_user(
			username="password2@example.com",
			password="Original password 123!",
		)
		Customer.objects.create(
			user=user,
			full_name="Password Customer",
			phone="0400123456",
			email_verified=True,
		)
		self.client.force_login(user)

		response = self.client.post(
			"/portal/profile/",
			{
				"form_type": "password",
				"old_password": "Original password 123!",
				"new_password1": "New secure password 456!",
				"new_password2": "New secure password 456!",
			},
		)

		self.assertRedirects(response, "/portal/profile/")
		user.refresh_from_db()
		self.assertTrue(user.check_password("New secure password 456!"))
