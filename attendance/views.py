from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from bookings.models import Booking
from employees.decorators import employee_required
from employees.models import Employee

from .models import AttendanceLog


def _submitted_coordinates(request):
    latitude = (request.POST.get("latitude") or "").strip()
    longitude = (request.POST.get("longitude") or "").strip()
    if not latitude and not longitude:
        return None, None
    if not latitude or not longitude:
        raise ValueError("Both location coordinates are required.")
    try:
        latitude = Decimal(latitude)
        longitude = Decimal(longitude)
    except InvalidOperation as exc:
        raise ValueError("Location coordinates are invalid.") from exc
    if (
        not latitude.is_finite()
        or not longitude.is_finite()
        or not Decimal("-90") <= latitude <= Decimal("90")
        or not Decimal("-180") <= longitude <= Decimal("180")
    ):
        raise ValueError("Location coordinates are invalid.")
    return latitude, longitude


@employee_required
def attendance_dashboard(request):
    employee = get_object_or_404(Employee, user=request.user)
    jobs = Booking.objects.filter(assigned_employee=employee).order_by("booking_date")
    attendance_logs = AttendanceLog.objects.filter(employee=employee)
    return render(
        request,
        "attendance/attendance_dashboard.html",
        {"jobs": jobs, "attendance_logs": attendance_logs},
    )


@employee_required
@require_POST
def check_in(request, booking_id):
    employee = get_object_or_404(Employee, user=request.user)
    try:
        latitude, longitude = _submitted_coordinates(request)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("attendance_dashboard")

    with transaction.atomic():
        booking = get_object_or_404(
            Booking.objects.select_for_update(),
            id=booking_id,
            assigned_employee=employee,
        )
        if booking.status in {"completed", "cancelled"}:
            messages.error(request, "This job is no longer available for check-in.")
            return redirect("attendance_dashboard")

        log = (
            AttendanceLog.objects.select_for_update()
            .filter(booking=booking, employee=employee)
            .order_by("created_at", "id")
            .first()
        )
        if log is None:
            AttendanceLog.objects.create(
                booking=booking,
                employee=employee,
                check_in_time=timezone.now(),
                check_in_latitude=latitude,
                check_in_longitude=longitude,
            )
            messages.success(request, "Successfully checked in.")
        elif log.check_in_time is None:
            log.check_in_time = timezone.now()
            log.check_in_latitude = latitude
            log.check_in_longitude = longitude
            log.save(
                update_fields=[
                    "check_in_time",
                    "check_in_latitude",
                    "check_in_longitude",
                ]
            )
            messages.success(request, "Successfully checked in.")
        else:
            messages.info(request, "You are already checked in for this job.")

    return redirect("attendance_dashboard")


@employee_required
@require_POST
def check_out(request, booking_id):
    employee = get_object_or_404(Employee, user=request.user)
    try:
        latitude, longitude = _submitted_coordinates(request)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("attendance_dashboard")

    with transaction.atomic():
        booking = get_object_or_404(
            Booking.objects.select_for_update(),
            id=booking_id,
            assigned_employee=employee,
        )
        log = (
            AttendanceLog.objects.select_for_update()
            .filter(booking=booking, employee=employee)
            .order_by("created_at", "id")
            .first()
        )
        if log is None or log.check_in_time is None:
            messages.error(request, "Check in before checking out.")
            return redirect("attendance_dashboard")

        if not log.check_out_time:
            log.check_out_time = timezone.now()
            if log.check_out_time < log.check_in_time:
                messages.error(request, "Check-out time cannot be before check-in.")
                return redirect("attendance_dashboard")
            log.check_out_latitude = latitude
            log.check_out_longitude = longitude
            duration = (log.check_out_time - log.check_in_time).total_seconds() / 3600
            log.total_hours = Decimal(str(round(duration, 2)))
            log.save(
                update_fields=[
                    "check_out_time",
                    "check_out_latitude",
                    "check_out_longitude",
                    "total_hours",
                ]
            )
            messages.success(request, "Successfully checked out.")
        else:
            messages.info(request, "You have already checked out for this job.")

    return redirect("attendance_dashboard")
