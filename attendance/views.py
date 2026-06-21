from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from bookings.models import Booking
from employees.models import Employee

from .models import AttendanceLog


@login_required
def attendance_dashboard(request):

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
    )


@login_required
def check_in(request, booking_id):

    employee = get_object_or_404(Employee, user=request.user)

    booking = get_object_or_404(Booking, id=booking_id)

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


@login_required
def check_out(request, booking_id):

    employee = get_object_or_404(Employee, user=request.user)

    booking = get_object_or_404(Booking, id=booking_id)

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
