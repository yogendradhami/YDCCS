# Create your tests here.
from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from customers.models import Customer
from employees.models import Employee
from induction.models import EmployeeOnboardingProfile
from leave_management.models import LeaveRequest

from .forms import BookingForm, PublicBookingForm
from .models import Booking
from .services import SERVICE_MAPPING, check_booking_availability, create_booking, map_service


class BookingServiceTests(TestCase):
	def setUp(self):
		self.customer = Customer.objects.create(
			full_name="Booking Customer", email="booking@example.com", phone="0400"
		)
		self.employee_user = User.objects.create_user("employee")
		self.employee = Employee.objects.create(
			user=self.employee_user, full_name="Employee", phone="0400"
		)

	def booking_kwargs(self, **overrides):
		data = {
			"customer": self.customer,
			"service_type": "Office Cleaning",
			"booking_date": date.today() + timedelta(days=3),
			"booking_time": time(10, 0),
			"address": "1 King Street",
			"suburb_postcode": "Adelaide 5000",
		}
		data.update(overrides)
		return data

	def test_valid_booking_and_idempotency(self):
		first, created = create_booking(**self.booking_kwargs(), workflow_key="booking-one")
		second, second_created = create_booking(**self.booking_kwargs(), workflow_key="booking-one")
		self.assertTrue(created)
		self.assertFalse(second_created)
		self.assertEqual(first.pk, second.pk)
		self.assertEqual(Booking.objects.count(), 1)

	def test_invalid_inputs_and_untrusted_employee_are_rejected(self):
		for key in ("service_type", "booking_date", "booking_time", "address", "suburb_postcode"):
			data = self.booking_kwargs()
			data[key] = "Invalid" if key == "service_type" else None
			with self.subTest(key=key), self.assertRaises(ValueError):
				create_booking(**data)
		with self.assertRaises(ValueError):
			create_booking(**self.booking_kwargs(assigned_employee=self.employee))

	def test_leave_and_active_conflict_block_but_cancelled_does_not(self):
		data = self.booking_kwargs(assigned_employee=self.employee, trusted_assignment=True)
		EmployeeOnboardingProfile.objects.filter(employee=self.employee).update(
			status="ready"
		)
		leave = LeaveRequest.objects.create(
			employee=self.employee,
			leave_type="annual",
			start_date=data["booking_date"],
			end_date=data["booking_date"],
			reason="Leave",
			status="approved",
		)
		with self.assertRaises(ValueError):
			create_booking(**data, workflow_key="leave-block")
		leave.delete()
		existing, _ = create_booking(**data, workflow_key="existing")
		existing.status = "cancelled"
		existing.save(update_fields=["status"])
		replacement, created = create_booking(**data, workflow_key="replacement")
		self.assertTrue(created)
		self.assertNotEqual(existing.pk, replacement.pk)

	def test_unassigned_availability_is_not_determinable(self):
		result = check_booking_availability(
			booking_date=date.today(), booking_time=time(10, 0)
		)
		self.assertEqual(
			result,
			{
				"available": False,
				"determinable": False,
				"reason": "general_unassigned_availability_not_configured",
			},
		)

	def test_service_mapping_is_explicit(self):
		self.assertEqual(map_service("commercial_cleaning"), "Commercial Cleaning")
		self.assertEqual(map_service("office_cleaning"), "Office Cleaning")
		self.assertEqual(map_service("window_cleaning"), "Window Cleaning")
		self.assertEqual(map_service("deep_cleaning"), "Deep Cleaning")
		self.assertEqual(map_service("end_of_lease_cleaning"), "End of Lease Cleaning")
		for unsupported in ("oven_cleaning", "carpet_cleaning", "spring_cleaning", "other"):
			self.assertNotIn(unsupported, SERVICE_MAPPING)
			self.assertIsNone(map_service(unsupported))

	def test_public_form_has_no_customer_selector_but_staff_form_does(self):
		self.assertNotIn("customer", PublicBookingForm().fields)
		self.assertIn("customer", BookingForm().fields)

	def test_staff_form_allows_booking_without_customer_or_employee(self):
		form = BookingForm(
			data={
				"customer": "",
				"service_type": "Office Cleaning",
				"booking_date": (date.today() + timedelta(days=3)).isoformat(),
				"booking_time": "10:00",
				"address": "1 King Street",
				"suburb_postcode": "Adelaide 5000",
				"quoted_price": "0.00",
				"assigned_employee": "",
				"status": "pending",
				"notes": "",
			}
		)

		self.assertFalse(form.fields["customer"].required)
		self.assertFalse(form.fields["assigned_employee"].required)
		self.assertTrue(form.is_valid(), form.errors)
		booking = form.save()
		self.assertIsNone(booking.customer)
		self.assertIsNone(booking.assigned_employee)
		self.assertEqual(str(booking), f"No customer - Office Cleaning - {booking.booking_date}")

	def test_staff_form_lists_active_employee_without_ready_onboarding(self):
		form = BookingForm()

		self.assertIn(self.employee, form.fields["assigned_employee"].queryset)
		self.assertEqual(
			form.fields["assigned_employee"].label,
			"Assigned Employee (Optional)",
		)

	def test_active_employee_can_be_assigned_before_onboarding_is_ready(self):
		booking, created = create_booking(
			**self.booking_kwargs(assigned_employee=self.employee),
			trusted_assignment=True,
		)

		self.assertTrue(created)
		self.assertEqual(booking.assigned_employee, self.employee)

	def test_booking_service_allows_missing_customer_and_employee(self):
		booking, created = create_booking(
			**self.booking_kwargs(customer=None),
			workflow_key="booking-without-customer",
		)

		self.assertTrue(created)
		self.assertIsNone(booking.customer)
		self.assertIsNone(booking.assigned_employee)
