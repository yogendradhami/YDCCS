from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from bookings.models import Booking
from employees.models import Employee
from employees.decorators import employee_required
from django.views.decorators.http import require_POST

from .models import AttendanceLog


@employee_required
def attendance_dashboard(request):

    employee = get_object_or_404(Employee, user=request.user)

    jobs = Booking.objects.filter(assigned_employee=employee).order_by("booking_date")

    attendance_logs = AttendanceLog.objects.filter(employee=employee)

    return render(
        request,
        "attendance/attendance_dashboard.html",
        {
            "jobs": jobs,
            "attendance_logs": attendance_logs,
        },
    )


@employee_required
@require_POST
def check_in(request, booking_id):

    employee = get_object_or_404(Employee, user=request.user)

    booking = get_object_or_404(
        Booking, id=booking_id, assigned_employee=employee
    )

    latitude = request.POST.get("latitude")
    longitude = request.POST.get("longitude")

    AttendanceLog.objects.get_or_create(
        booking=booking,
        employee=employee,
        defaults={
            "check_in_time": timezone.now(),
            "check_in_latitude": latitude,
            "check_in_longitude": longitude,
        },
    )

    messages.success(request, "Successfully checked in.")

    return redirect("attendance_dashboard")


@employee_required
@require_POST
def check_out(request, booking_id):

    employee = get_object_or_404(Employee, user=request.user)

    booking = get_object_or_404(
        Booking, id=booking_id, assigned_employee=employee
    )

    log = get_object_or_404(AttendanceLog, booking=booking, employee=employee)

    if not log.check_out_time:

        log.check_out_time = timezone.now()

        log.check_out_latitude = request.POST.get("latitude")
        log.check_out_longitude = request.POST.get("longitude")

        duration = (log.check_out_time - log.check_in_time).total_seconds() / 3600

        log.total_hours = Decimal(str(round(duration, 2)))

        log.save()

    messages.success(request, "Successfully checked out.")

    return redirect("attendance_dashboard")
