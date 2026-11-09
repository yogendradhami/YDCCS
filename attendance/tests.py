from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking
from employees.models import Employee
from induction.models import EmployeeInduction, InductionProgramme
from rosters.models import Roster
from attendance.services import sync_roster_attendance

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

    def test_team_member_can_see_and_check_in_to_shared_booking(self):
        teammate_user = User.objects.create_user("attendance-teammate")
        teammate = Employee.objects.create(
            user=teammate_user,
            full_name="Attendance Teammate",
            phone="0400000001",
        )
        induction = EmployeeInduction.objects.get(employee=teammate)
        induction.status = "completed"
        induction.save(update_fields=["status"])
        self.booking.assigned_employees.add(teammate)
        self.client.force_login(teammate_user)

        response = self.client.get(reverse("attendance_dashboard"))
        self.assertContains(response, self.booking.service_type)

        response = self.client.post(
            reverse("check_in", args=[self.booking.pk]),
            {"latitude": "-34.9285", "longitude": "138.6007"},
        )

        self.assertRedirects(response, reverse("attendance_dashboard"))
        self.assertTrue(
            AttendanceLog.objects.filter(
                booking=self.booking,
                employee=teammate,
                check_in_time__isnull=False,
            ).exists()
        )

    def test_employee_roster_keeps_all_schedule_sections_and_navigation(self):
        Roster.objects.create(
            employee=self.employee,
            booking=self.booking,
            shift_date=date.today(),
            start_time=time(9, 0),
            end_time=time(11, 0),
        )
        response = self.client.get(reverse("employee_roster"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Today's Shifts")
        self.assertContains(response, "Upcoming Shifts")
        self.assertContains(response, "All Roster Records")
        self.assertContains(response, "My Jobs")
        self.assertContains(response, "Attendance")
        self.assertContains(response, "Apply Leave")
        self.assertContains(response, "My Payslips")

    def test_roster_creates_and_updates_allocated_attendance(self):
        roster = Roster.objects.create(
            employee=self.employee,
            booking=self.booking,
            shift_date=date(2026, 11, 9),
            start_time=time(9, 0),
            end_time=time(11, 0),
        )

        log = sync_roster_attendance(roster)

        self.assertEqual(log.source, AttendanceLog.Source.ROSTER)
        self.assertEqual(log.total_hours, Decimal("2.00"))

        roster.end_time = time(12, 30)
        roster.save(update_fields=["end_time"])
        updated_log = sync_roster_attendance(roster)

        self.assertEqual(updated_log.pk, log.pk)
        self.assertEqual(updated_log.total_hours, Decimal("3.50"))
        self.assertEqual(AttendanceLog.objects.filter(roster=roster).count(), 1)

    def test_roster_allocation_does_not_block_portal_check_in(self):
        roster = Roster.objects.create(
            employee=self.employee,
            booking=self.booking,
            shift_date=date.today(),
            start_time=time(9, 0),
            end_time=time(11, 0),
            status="scheduled",
        )
        sync_roster_attendance(roster)

        response = self.client.post(
            reverse("check_in", args=[self.booking.pk]),
            {"latitude": "-34.9285", "longitude": "138.6007"},
        )

        self.assertRedirects(response, reverse("attendance_dashboard"))
        self.assertTrue(
            AttendanceLog.objects.filter(
                booking=self.booking,
                employee=self.employee,
                source=AttendanceLog.Source.PORTAL,
                check_in_time__isnull=False,
            ).exists()
        )

    def test_completed_portal_punch_replaces_roster_hours(self):
        roster = Roster.objects.create(
            employee=self.employee,
            booking=self.booking,
            shift_date=date.today(),
            start_time=time(9, 0),
            end_time=time(11, 0),
            status="scheduled",
        )
        sync_roster_attendance(roster)
        AttendanceLog.objects.create(
            booking=self.booking,
            employee=self.employee,
            check_in_time=timezone.now() - timedelta(hours=1),
        )

        self.client.post(reverse("check_out", args=[self.booking.pk]))

        self.assertFalse(AttendanceLog.objects.filter(roster=roster).exists())
        self.assertEqual(
            AttendanceLog.objects.filter(
                booking=self.booking,
                employee=self.employee,
                source=AttendanceLog.Source.PORTAL,
            ).count(),
            1,
        )


class AttendanceManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="attendance-manager",
            email="attendance-manager@example.com",
            password="test-password",
        )
        self.employee = Employee.objects.create(
            full_name="Rostered Employee",
            phone="0400000010",
        )
        self.booking = Booking.objects.create(
            service_type="Office Cleaning",
            booking_date=date(2026, 11, 9),
            booking_time=time(9, 0),
            address="2 King Street",
            suburb_postcode="Adelaide 5000",
            assigned_employee=self.employee,
            status="completed",
        )
        self.client.force_login(self.admin)

    def test_attendance_register_groups_records_under_each_employee(self):
        AttendanceLog.objects.create(
            employee=self.employee,
            booking=self.booking,
            check_in_time=timezone.now() - timedelta(hours=3),
            check_out_time=timezone.now() - timedelta(hours=2),
            total_hours=Decimal("1.00"),
        )
        AttendanceLog.objects.create(
            employee=self.employee,
            booking=self.booking,
            check_in_time=timezone.now() - timedelta(hours=2),
            check_out_time=timezone.now() - timedelta(hours=1),
            total_hours=Decimal("1.00"),
        )

        response = self.client.get(reverse("attendance_report"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["attendance_groups"]), 1)
        self.assertContains(response, "attendance records")
        self.assertContains(response, "Employee attendance records")

    def test_attendance_detail_is_linked_from_employee_record_card(self):
        attendance = AttendanceLog.objects.create(
            employee=self.employee,
            booking=self.booking,
            check_in_time=timezone.now() - timedelta(hours=3),
            check_out_time=timezone.now() - timedelta(hours=1),
            total_hours=Decimal("2.00"),
        )

        register_response = self.client.get(reverse("attendance_report"))
        detail_response = self.client.get(
            reverse("attendance_log_detail", args=[attendance.pk])
        )

        self.assertContains(
            register_response,
            reverse("attendance_log_detail", args=[attendance.pk]),
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Rostered Employee")
        self.assertContains(detail_response, "Worked hours")

    def test_attendance_create_edit_and_delete(self):
        create_response = self.client.post(
            reverse("attendance_log_create"),
            {
                "employee": self.employee.pk,
                "booking": self.booking.pk,
                "check_in_time": "2026-11-09T09:00",
                "check_out_time": "2026-11-09T11:30",
            },
        )
        self.assertRedirects(create_response, reverse("attendance_report"))
        attendance = AttendanceLog.objects.get(
            employee=self.employee,
            booking=self.booking,
            source=AttendanceLog.Source.PORTAL,
        )
        self.assertEqual(attendance.total_hours, Decimal("2.50"))

        edit_response = self.client.post(
            reverse("attendance_log_edit", args=[attendance.pk]),
            {
                "employee": self.employee.pk,
                "booking": self.booking.pk,
                "check_in_time": "2026-11-09T09:00",
                "check_out_time": "2026-11-09T12:00",
            },
        )
        self.assertRedirects(edit_response, reverse("attendance_report"))
        attendance.refresh_from_db()
        self.assertEqual(attendance.total_hours, Decimal("3.00"))

        confirm_response = self.client.get(
            reverse("attendance_log_delete", args=[attendance.pk])
        )
        self.assertEqual(confirm_response.status_code, 200)
        delete_response = self.client.post(
            reverse("attendance_log_delete", args=[attendance.pk])
        )
        self.assertRedirects(delete_response, reverse("attendance_report"))
        self.assertFalse(AttendanceLog.objects.filter(pk=attendance.pk).exists())

    def test_roster_attendance_is_managed_by_roster(self):
        roster = Roster.objects.create(
            employee=self.employee,
            booking=self.booking,
            shift_date=date(2026, 11, 9),
            start_time=time(9, 0),
            end_time=time(11, 0),
        )
        attendance = sync_roster_attendance(roster)

        self.assertEqual(
            self.client.get(
                reverse("attendance_log_edit", args=[attendance.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                reverse("attendance_log_delete", args=[attendance.pk])
            ).status_code,
            404,
        )
        response = self.client.get(reverse("attendance_report"))
        self.assertContains(response, "Edit roster")
        self.assertContains(
            response,
            reverse("delete_roster", args=[roster.pk]),
        )

    def test_cancelled_roster_removes_allocated_attendance(self):
        roster = Roster.objects.create(
            employee=self.employee,
            booking=self.booking,
            shift_date=date(2026, 11, 9),
            start_time=time(9, 0),
            end_time=time(11, 0),
            status="completed",
        )
        sync_roster_attendance(roster)

        roster.status = "cancelled"
        roster.save(update_fields=["status"])
        sync_roster_attendance(roster)

        self.assertFalse(AttendanceLog.objects.filter(roster=roster).exists())
