
from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from bookings.models import Booking
from customers.models import Customer
from employees.models import Employee


User = get_user_model()


class MobileApiCustomerTests(APITestCase):
    """Customer authentication, profile and booking API tests."""

    def setUp(self):
        self.password = "MobileTest!Pass2026-Strong"

        self.user = User.objects.create_user(
            username="mobile.customer@example.com",
            email="mobile.customer@example.com",
            password=self.password,
        )

        self.customer = Customer.objects.create(
            user=self.user,
            full_name="Mobile Test Customer",
            email="mobile.customer@example.com",
            phone="0400000000",
        )

        self.token_url = "/api/v1/auth/token/"
        self.me_url = "/api/v1/me/"
        self.bookings_url = "/api/v1/bookings/"

    def authenticate(self):
        response = self.client.post(
            self.token_url,
            {
                "username": self.user.username,
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
        )

    def test_customer_can_obtain_jwt_tokens(self):
        response = self.client.post(
            self.token_url,
            {
                "username": self.user.username,
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_invalid_password_cannot_obtain_token(self):
        response = self.client.post(
            self.token_url,
            {
                "username": self.user.username,
                "password": "DefinitelyWrongPassword123!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_profile_requires_authentication(self):
        response = self.client.get(self.me_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_authenticated_customer_can_view_profile(self):
        self.authenticate()

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("customer", response.data["roles"])
        self.assertEqual(
            response.data["customer"]["id"],
            self.customer.id,
        )

    def test_customer_can_create_booking(self):
        self.authenticate()

        response = self.client.post(
            self.bookings_url,
            {
                "service_type": "Commercial Cleaning",
                "booking_date": (
                    timezone.localdate() + timedelta(days=2)
                ).isoformat(),
                "booking_time": "10:00:00",
                "address": "10 Test Street",
                "suburb_postcode": "Melbourne VIC 3000",
                "notes": "Mobile API test booking",
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY="mobile-test-booking-001",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        self.assertTrue(
            Booking.objects.filter(
                customer=self.customer,
                idempotency_key="mobile-test-booking-001",
            ).exists()
        )

    def test_duplicate_booking_request_does_not_create_second_booking(self):
        self.authenticate()

        payload = {
            "service_type": "Commercial Cleaning",
            "booking_date": (
                timezone.localdate() + timedelta(days=2)
            ).isoformat(),
            "booking_time": "10:00:00",
            "address": "10 Test Street",
            "suburb_postcode": "Melbourne VIC 3000",
            "notes": "Duplicate request test",
        }

        headers = {
            "HTTP_IDEMPOTENCY_KEY": "mobile-test-booking-002",
        }

        first_response = self.client.post(
            self.bookings_url,
            payload,
            format="json",
            **headers,
        )

        second_response = self.client.post(
            self.bookings_url,
            payload,
            format="json",
            **headers,
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
            first_response.data,
        )
        self.assertEqual(
            second_response.status_code,
            status.HTTP_200_OK,
            second_response.data,
        )

        self.assertEqual(
            Booking.objects.filter(
                customer=self.customer,
                idempotency_key="mobile-test-booking-002",
            ).count(),
            1,
        )

    def test_customer_cannot_access_another_customers_booking(self):
        other_user = User.objects.create_user(
            username="another.customer@example.com",
            email="another.customer@example.com",
            password="AnotherTest!Pass2026",
        )

        other_customer = Customer.objects.create(
            user=other_user,
            full_name="Another Customer",
            email="another.customer@example.com",
            phone="0400000001",
        )

        booking = Booking.objects.create(
            customer=other_customer,
            service_type="Commercial Cleaning",
            booking_date=timezone.localdate() + timedelta(days=3),
            booking_time=time(11, 0),
            address="20 Private Street",
            suburb_postcode="Melbourne VIC 3000",
        )

        self.authenticate()

        response = self.client.get(
            f"{self.bookings_url}{booking.pk}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )


class MobileApiEmployeeTests(APITestCase):
    """Employee roster authentication and access-control tests."""

    def setUp(self):
        self.password = "EmployeeTest!Pass2026"

        self.employee_user = User.objects.create_user(
            username="employee.one@example.com",
            email="employee.one@example.com",
            password=self.password,
        )

        self.employee = Employee.objects.create(
            user=self.employee_user,
            full_name="Employee One",
            email="employee.one@example.com",
            phone="0400000001",
            role="cleaner",
            active=True,
        )

        self.other_user = User.objects.create_user(
            username="employee.two@example.com",
            email="employee.two@example.com",
            password=self.password,
        )

        self.other_employee = Employee.objects.create(
            user=self.other_user,
            full_name="Employee Two",
            email="employee.two@example.com",
            phone="0400000002",
            role="cleaner",
            active=True,
        )

    def authenticate(self, user, password=None):
        password = password or self.password

        response = self.client.post(
            "/api/v1/auth/token/",
            {
                "username": user.username,
                "password": password,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
        )

    def test_active_employee_can_access_own_roster(self):
        self.authenticate(self.employee_user)

        response = self.client.get("/api/v1/employee/roster/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )

    def test_inactive_employee_cannot_access_roster(self):
        self.employee.active = False
        self.employee.save(update_fields=["active"])

        self.authenticate(self.employee_user)

        response = self.client.get("/api/v1/employee/roster/")

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_customer_cannot_access_employee_roster(self):
        customer_password = "CustomerTest!Pass2026"

        customer_user = User.objects.create_user(
            username="roster.customer@example.com",
            email="roster.customer@example.com",
            password=customer_password,
        )

        Customer.objects.create(
            user=customer_user,
            full_name="Roster Customer",
            email="roster.customer@example.com",
            phone="0400000003",
        )

        self.authenticate(
            customer_user,
            password=customer_password,
        )

        response = self.client.get("/api/v1/employee/roster/")

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )


class MobileApiCompanyPermissionTests(APITestCase):
    """Company summary access-control tests."""

    def setUp(self):
        self.customer_password = "CustomerTest!Pass2026"

        self.customer_user = User.objects.create_user(
            username="company.customer@example.com",
            email="company.customer@example.com",
            password=self.customer_password,
        )

    def authenticate(self, user, password):
        response = self.client.post(
            "/api/v1/auth/token/",
            {
                "username": user.username,
                "password": password,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
        )

    def test_customer_cannot_access_company_summary(self):
        self.authenticate(
            self.customer_user,
            self.customer_password,
        )

        response = self.client.get("/api/v1/company/summary/")

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_anonymous_user_cannot_access_company_summary(self):
        response = self.client.get("/api/v1/company/summary/")

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_superuser_can_access_company_summary(self):
        admin_password = "AdminTest!Pass2026"

        admin_user = User.objects.create_superuser(
            username="mobile.admin@example.com",
            email="mobile.admin@example.com",
            password=admin_password,
        )

        self.authenticate(admin_user, admin_password)

        response = self.client.get("/api/v1/company/summary/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )
        self.assertIn("bookings_today", response.data)
        self.assertIn("active_employees", response.data)
