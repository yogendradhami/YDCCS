# Create your tests here.
from django.contrib.auth.models import User
from django.urls import reverse
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


class CustomerDirectoryViewTests(TestCase):
	def test_directory_renders_customer_metrics_and_account_status_counts(self):
		user = User.objects.create_user("directory-customer", is_staff=True)
		Customer.objects.create(
			user=user,
			full_name="Linked Customer",
			email="linked@example.com",
			phone="0400",
			jobs_completed=3,
			total_revenue="450.50",
		)
		Customer.objects.create(
			full_name="Unlinked Customer",
			email="unlinked@example.com",
			phone="0401",
			jobs_completed=2,
			total_revenue="125.00",
		)
		self.client.force_login(user)

		response = self.client.get(reverse("customer_list"))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context["customer_count"], 2)
		self.assertEqual(response.context["linked_customer_count"], 1)
		self.assertEqual(response.context["unlinked_customer_count"], 1)
		self.assertEqual(response.context["customer_jobs_total"], 5)
		self.assertEqual(response.context["customer_revenue_total"], 575.5)

	def test_edit_page_renders_customer_profile_sections(self):
		user = User.objects.create_user("customer-editor", is_staff=True)
		customer = Customer.objects.create(
			full_name="Edit Customer",
			email="edit@example.com",
			phone="0402",
		)
		self.client.force_login(user)

		response = self.client.get(reverse("edit_customer", args=[customer.pk]))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Customer details")
		self.assertContains(response, "Service profile")
		self.assertContains(response, "Internal notes")
