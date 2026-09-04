from django.contrib.auth.models import User
from django.test import TestCase

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

		self.assertRedirects(response, "/portal/dashboard/")
		user = User.objects.get(username="jane.smith@example.com")
		customer = Customer.objects.get(user=user)
		self.assertEqual(customer.full_name, "Jane Smith")
		self.assertTrue(user.check_password("A secure password 123!"))
