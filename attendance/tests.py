from datetime import date, time
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking
from employees.models import Employee
from induction.models import EmployeeInduction, InductionProgramme

from .models import AttendanceLog


class AttendanceWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("attendance-employee")
        self.employee = Employee.objects.create(
            user=self.user,
            full_name="Attendance Employee",
            phone="0400000000",
        )
        programme = InductionProgramme.objects.create(name="Attendance induction")
        EmployeeInduction.objects.create(
            employee=self.employee,
            programme=programme,
            status="completed",
        )
        self.booking = Booking.objects.create(
            service_type="Office Cleaning",
            booking_date=date.today(),
            booking_time=time(9, 0),
            address="1 King Street",
            suburb_postcode="Adelaide 5000",
            assigned_employee=self.employee,
            status="in_progress",
        )
        self.client.force_login(self.user)

    def test_check_out_without_check_in_does_not_raise_or_write_checkout(self):
        log = AttendanceLog.objects.create(
            booking=self.booking,
            employee=self.employee,
        )

        response = self.client.post(reverse("check_out", args=[self.booking.pk]))

        self.assertRedirects(response, reverse("attendance_dashboard"))
        log.refresh_from_db()
        self.assertIsNone(log.check_out_time)
        self.assertEqual(log.total_hours, Decimal("0"))

    def test_repeated_check_in_keeps_one_attendance_log(self):
        url = reverse("check_in", args=[self.booking.pk])

        self.client.post(url, {"latitude": "-34.9285", "longitude": "138.6007"})
        log = AttendanceLog.objects.get(booking=self.booking, employee=self.employee)
        original_time = log.check_in_time
        self.client.post(url, {"latitude": "-34.9000", "longitude": "138.6000"})

        self.assertEqual(
            AttendanceLog.objects.filter(booking=self.booking, employee=self.employee).count(),
            1,
        )
        log.refresh_from_db()
        self.assertEqual(log.check_in_time, original_time)
        self.assertEqual(log.check_in_latitude, Decimal("-34.92850000"))

    def test_invalid_location_coordinates_are_not_persisted(self):
        response = self.client.post(
            reverse("check_in", args=[self.booking.pk]),
            {"latitude": "-100", "longitude": "138.6007"},
        )

        self.assertRedirects(response, reverse("attendance_dashboard"))
        self.assertFalse(AttendanceLog.objects.exists())

    def test_check_out_after_check_in_is_idempotent(self):
        log = AttendanceLog.objects.create(
            booking=self.booking,
            employee=self.employee,
            check_in_time=timezone.now(),
        )
        url = reverse("check_out", args=[self.booking.pk])

        first = self.client.post(url)
        log.refresh_from_db()
        first_checkout = log.check_out_time
        second = self.client.post(url)
        log.refresh_from_db()

        self.assertRedirects(first, reverse("attendance_dashboard"))
        self.assertRedirects(second, reverse("attendance_dashboard"))
        self.assertIsNotNone(first_checkout)
        self.assertEqual(log.check_out_time, first_checkout)
        self.assertGreaterEqual(log.total_hours, Decimal("0"))
