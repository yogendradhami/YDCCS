# Create your tests here.
from django.contrib.auth.models import User
from django.test import TestCase

from .models import Customer
from .services import resolve_customer


class CustomerServiceTests(TestCase):
	def test_authenticated_customer_takes_precedence(self):
		user = User.objects.create_user("customer", password="password")
		customer = Customer.objects.create(
			user=user, full_name="Customer", email="customer@example.com", phone="0400"
		)
		resolved, created = resolve_customer(
			user=user, email="other@example.com", create=True
		)
		self.assertEqual(resolved, customer)
		self.assertFalse(created)

	def test_email_lookup_is_normalized_and_reused(self):
		customer = Customer.objects.create(
			full_name="Customer", email="Customer@Example.com", phone="0400"
		)
		resolved, created = resolve_customer(email=" customer@example.com ")
		self.assertEqual(resolved, customer)
		self.assertFalse(created)

	def test_customer_is_created_only_when_requested(self):
		resolved, created = resolve_customer(email="new@example.com")
		self.assertIsNone(resolved)
		self.assertFalse(created)
		resolved, created = resolve_customer(
			email="new@example.com", name="New Customer", phone="0400", create=True
		)
		self.assertTrue(created)
		self.assertEqual(resolved.email, "new@example.com")

	def test_arbitrary_customer_id_is_not_an_input(self):
		resolved, created = resolve_customer(email="new@example.com", create=False)
		self.assertIsNone(resolved)
		self.assertFalse(created)

	def test_retry_resolution_does_not_duplicate(self):
		first, first_created = resolve_customer(
			email="retry@example.com", name="Retry", phone="0400", create=True
		)
		second, second_created = resolve_customer(
			email="retry@example.com", name="Retry", phone="0400", create=True
		)
		self.assertTrue(first_created)
		self.assertFalse(second_created)
		self.assertEqual(first.pk, second.pk)
		self.assertEqual(
			Customer.objects.filter(email__iexact="retry@example.com").count(),
			1,
		)
