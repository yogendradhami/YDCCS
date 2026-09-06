from datetime import date, time

from django.db import transaction
from django.utils import timezone

from leave_management.models import LeaveRequest

from .models import Booking

SERVICE_MAPPING = {
    "commercial_cleaning": "Commercial Cleaning",
    "office_cleaning": "Office Cleaning",
    "window_cleaning": "Window Cleaning",
    "deep_cleaning": "Deep Cleaning",
    "end_of_lease_cleaning": "End of Lease Cleaning",
}


def map_service(service):
    return SERVICE_MAPPING.get(service)


def check_booking_availability(*, booking_date, booking_time, assigned_employee=None):
    if not assigned_employee:
        return {
            "available": False,
            "determinable": False,
            "reason": "general_unassigned_availability_not_configured",
        }

    if LeaveRequest.objects.filter(
        employee=assigned_employee,
        status="approved",
        start_date__lte=booking_date,
        end_date__gte=booking_date,
    ).exists():
        return {"available": False, "determinable": True, "reason": "employee_on_leave"}

    conflict = Booking.objects.filter(
        assigned_employee=assigned_employee,
        booking_date=booking_date,
        booking_time=booking_time,
    ).exclude(status="cancelled").exists()
    return {
        "available": not conflict,
        "determinable": True,
        "reason": "employee_conflict" if conflict else "available",
    }


def create_booking(*, customer, service_type, booking_date, booking_time, address, suburb_postcode, quoted_price=0, notes="", assigned_employee=None, workflow_key=None, trusted_assignment=False):
    if not customer:
        raise ValueError("A customer is required.")
    if service_type not in dict(Booking.SERVICE_CHOICES):
        raise ValueError("Unsupported booking service.")
    if not isinstance(booking_date, date) or not isinstance(booking_time, time):
        raise ValueError("A valid booking date and time are required.")
    if not address or not suburb_postcode:
        raise ValueError("Address and suburb/postcode are required.")
    if assigned_employee is not None and not trusted_assignment:
        raise ValueError("Employee assignment must come from trusted staff logic.")

    with transaction.atomic():
        if workflow_key:
            existing = Booking.objects.filter(idempotency_key=workflow_key).first()
            if existing:
                return existing, False

        if assigned_employee:
            if LeaveRequest.objects.filter(
                employee=assigned_employee,
                status="approved",
                start_date__lte=booking_date,
                end_date__gte=booking_date,
            ).exists():
                raise ValueError("The assigned employee is on approved leave.")
            if Booking.objects.select_for_update().filter(
                assigned_employee=assigned_employee,
                booking_date=booking_date,
                booking_time=booking_time,
            ).exclude(status="cancelled").exists():
                raise ValueError("The assigned employee is not available.")

        booking = Booking.objects.create(
            customer=customer,
            service_type=service_type,
            booking_date=booking_date,
            booking_time=booking_time,
            address=address,
            suburb_postcode=suburb_postcode,
            quoted_price=quoted_price,
            assigned_employee=assigned_employee,
            notes=notes,
            idempotency_key=workflow_key,
        )
    return booking, True
