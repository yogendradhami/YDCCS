from decimal import Decimal
<<<<<<< HEAD

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
=======
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
>>>>>>> 5815f15 (Initial project commit)
from django.utils import timezone

from bookings.models import Booking
from employees.models import Employee

from .models import AttendanceLog


@login_required
def attendance_dashboard(request):

<<<<<<< HEAD
    employee = get_object_or_404(Employee, user=request.user)

    jobs = Booking.objects.filter(assigned_employee=employee).order_by("booking_date")

    attendance_logs = AttendanceLog.objects.filter(employee=employee)

    return render(
        request,
        "attendance_dashboard.html",
        {
            "jobs": jobs,
            "attendance_logs": attendance_logs,
        },
=======
    employee = get_object_or_404(
        Employee,
        user=request.user
    )

    jobs = Booking.objects.filter(
        assigned_employee=employee
    ).order_by("booking_date")

    attendance_logs = AttendanceLog.objects.filter(
        employee=employee
    )

    return render(
        request,
        "attendance/attendance_dashboard.html",
        {
            "jobs": jobs,
            "attendance_logs": attendance_logs,
        }
>>>>>>> 5815f15 (Initial project commit)
    )


@login_required
def check_in(request, booking_id):

<<<<<<< HEAD
    employee = get_object_or_404(Employee, user=request.user)

    booking = get_object_or_404(Booking, id=booking_id)
=======
    employee = get_object_or_404(
        Employee,
        user=request.user
    )

    booking = get_object_or_404(
        Booking,
        id=booking_id
    )
>>>>>>> 5815f15 (Initial project commit)

    latitude = request.POST.get("latitude")
    longitude = request.POST.get("longitude")

    AttendanceLog.objects.get_or_create(
        booking=booking,
        employee=employee,
        defaults={
            "check_in_time": timezone.now(),
            "check_in_latitude": latitude,
            "check_in_longitude": longitude,
<<<<<<< HEAD
        },
    )

    messages.success(request, "Successfully checked in.")
=======
        }
    )

    messages.success(
        request,
        "Successfully checked in."
    )
>>>>>>> 5815f15 (Initial project commit)

    return redirect("attendance_dashboard")


@login_required
def check_out(request, booking_id):

<<<<<<< HEAD
    employee = get_object_or_404(Employee, user=request.user)

    booking = get_object_or_404(Booking, id=booking_id)

    log = get_object_or_404(AttendanceLog, booking=booking, employee=employee)
=======
    employee = get_object_or_404(
        Employee,
        user=request.user
    )

    booking = get_object_or_404(
        Booking,
        id=booking_id
    )

    log = get_object_or_404(
        AttendanceLog,
        booking=booking,
        employee=employee
    )
>>>>>>> 5815f15 (Initial project commit)

    if not log.check_out_time:

        log.check_out_time = timezone.now()

        log.check_out_latitude = request.POST.get("latitude")
        log.check_out_longitude = request.POST.get("longitude")

<<<<<<< HEAD
        duration = (log.check_out_time - log.check_in_time).total_seconds() / 3600
=======
        duration = (
            log.check_out_time -
            log.check_in_time
        ).total_seconds() / 3600
>>>>>>> 5815f15 (Initial project commit)

        log.total_hours = Decimal(str(round(duration, 2)))

        log.save()

<<<<<<< HEAD
    messages.success(request, "Successfully checked out.")

    return redirect("attendance_dashboard")
=======
    messages.success(
        request,
        "Successfully checked out."
    )

    return redirect("attendance_dashboard")
>>>>>>> 5815f15 (Initial project commit)
