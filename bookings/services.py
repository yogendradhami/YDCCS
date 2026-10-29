from datetime import date, time
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from leave_management.models import LeaveRequest
from employees.models import Employee
from services.models import Service

from .models import Booking, BookingWorkOrder

SERVICE_MAPPING = {
    "commercial_cleaning": "Commercial Cleaning",
    "office_cleaning": "Office Cleaning",
    "window_cleaning": "Window Cleaning",
    "deep_cleaning": "Deep Cleaning",
    "end_of_lease_cleaning": "End of Lease Cleaning",
}


def map_service(service):
    return SERVICE_MAPPING.get(service)


def get_booking_service_choices():
    service_names = dict(Booking.SERVICE_CHOICES)
    existing_values = set(service_names)
    active_services = Service.objects.filter(is_active=True).order_by("name")

    for service_name in active_services.values_list("name", flat=True):
        if service_name not in existing_values:
            service_names[service_name] = service_name
            existing_values.add(service_name)

    return [
        (value, label.removesuffix(" Adelaide").strip())
        for value, label in service_names.items()
    ]


def replace_booking_work_orders(booking, work_orders):
    normalized_work_orders = list(work_orders)
    if not normalized_work_orders:
        raise ValueError("At least one work order is required.")

    booking.work_orders.all().delete()
    BookingWorkOrder.objects.bulk_create(
        [
            BookingWorkOrder(
                booking=booking,
                service_type=work_order["service_type"],
                price=Decimal(str(work_order["price"])),
                position=position,
            )
            for position, work_order in enumerate(normalized_work_orders)
        ]
    )
    booking.service_type = normalized_work_orders[0]["service_type"]
    booking.quoted_price = sum(
        (Decimal(str(work_order["price"])) for work_order in normalized_work_orders),
        Decimal("0.00"),
    )
    booking.save(update_fields=["service_type", "quoted_price"])
    return booking.quoted_price


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


def create_booking(*, customer=None, service_type, booking_date, booking_time, address, suburb_postcode, quoted_price=0, notes="", assigned_employee=None, workflow_key=None, trusted_assignment=False, work_orders=None):
    normalized_work_orders = work_orders or [
        {"service_type": service_type, "price": quoted_price}
    ]
    valid_services = dict(get_booking_service_choices())
    if not normalized_work_orders:
        raise ValueError("At least one work order is required.")
    for work_order in normalized_work_orders:
        if work_order["service_type"] not in valid_services:
            raise ValueError("Unsupported booking service.")
        if Decimal(str(work_order["price"])) < 0:
            raise ValueError("Work order prices cannot be negative.")
    service_type = normalized_work_orders[0]["service_type"]
    quoted_price = sum(
        (Decimal(str(work_order["price"])) for work_order in normalized_work_orders),
        Decimal("0.00"),
    )
    if not isinstance(booking_date, date) or not isinstance(booking_time, time):
        raise ValueError("A valid booking date and time are required.")
    if not address or not suburb_postcode:
        raise ValueError("Address and suburb/postcode are required.")
    if assigned_employee is not None and not trusted_assignment:
        raise ValueError("Employee assignment must come from trusted staff logic.")
    if assigned_employee is not None and not assigned_employee.active:
        raise ValueError("An inactive employee cannot be assigned to a booking.")

    try:
        with transaction.atomic():
            if workflow_key:
                existing = Booking.objects.filter(idempotency_key=workflow_key).first()
                if existing:
                    return existing, False

            if assigned_employee:
                # Serialize availability checks for this employee so concurrent
                # booking requests cannot both pass when no conflicting row exists.
                Employee.objects.select_for_update().get(pk=assigned_employee.pk)
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
            replace_booking_work_orders(booking, normalized_work_orders)
    except IntegrityError:
        if workflow_key:
            existing = Booking.objects.filter(idempotency_key=workflow_key).first()
            if existing:
                return existing, False
        raise
    return booking, True
