from datetime import datetime, timedelta

from django.conf import settings
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from employees.models import EmployeeGoogleAccount


EMPLOYEE_GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
]


def get_employee_google_calendar_service(employee):
    """
    Return a Google Calendar API service for the specified employee.

    Each employee has their own Google Calendar OAuth account.
    """

    try:
        google_account = EmployeeGoogleAccount.objects.get(
            employee=employee
        )
    except EmployeeGoogleAccount.DoesNotExist:
        return None

    if not google_account.access_token:
        return None

    credentials = Credentials(
        token=google_account.access_token,
        refresh_token=google_account.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=EMPLOYEE_GOOGLE_SCOPES,
    )

    # Refresh expired access token automatically.
    if credentials.expired and credentials.refresh_token:

        credentials.refresh(Request())

        google_account.access_token = credentials.token
        google_account.save(
            update_fields=[
                "access_token",
                "updated_at",
            ]
        )

    return build(
        "calendar",
        "v3",
        credentials=credentials,
    )


def create_or_update_booking_event(booking):
    """
    Create or update the booking event in the assigned
    employee's Google Calendar.
    """

    employee = booking.assigned_employee

    if not employee:
        return None

    service = get_employee_google_calendar_service(employee)

    if not service:
        return None

    start_time = booking.booking_time
    end_time = None

    roster = (
        booking.rosters
        .filter(status="scheduled")
        .order_by("start_time")
        .first()
    )

    if roster:
        start_time = roster.start_time
        end_time = roster.end_time

    start_datetime = datetime.combine(
        booking.booking_date,
        start_time,
    )

    if end_time:
        end_datetime = datetime.combine(
            booking.booking_date,
            end_time,
        )
    else:
        end_datetime = start_datetime + timedelta(hours=2)

    employee_name = employee.full_name

    event_body = {
        "summary": (
            f"{booking.service_type} - "
            f"{booking.customer.full_name}"
        ),
        "location": (
            f"{booking.address}, "
            f"{booking.suburb_postcode}"
        ),
        "description": (
            f"Customer: {booking.customer.full_name}\n"
            f"Phone: {booking.customer.phone}\n"
            f"Email: {booking.customer.email}\n"
            f"Service: {booking.service_type}\n"
            f"Employee: {employee_name}\n"
            f"Status: {booking.get_status_display()}\n"
            f"Price: ${booking.quoted_price}\n\n"
            f"Created by YD Commercial Cleaning Services CRM"
        ),
        "start": {
            "dateTime": start_datetime.isoformat(),
            "timeZone": "Australia/Adelaide",
        },
        "end": {
            "dateTime": end_datetime.isoformat(),
            "timeZone": "Australia/Adelaide",
        },
    }

    if booking.google_calendar_event_id:

        event = (
            service.events()
            .update(
                calendarId="primary",
                eventId=booking.google_calendar_event_id,
                body=event_body,
            )
            .execute()
        )

    else:

        event = (
            service.events()
            .insert(
                calendarId="primary",
                body=event_body,
            )
            .execute()
        )

        booking.google_calendar_event_id = event.get("id")

        booking.save(
            update_fields=[
                "google_calendar_event_id"
            ]
        )

    return event


def delete_booking_event(booking):
    """
    Delete the booking event from the assigned employee's
    Google Calendar.
    """

    employee = booking.assigned_employee

    if not employee:
        return False

    service = get_employee_google_calendar_service(employee)

    if not service:
        return False

    if not booking.google_calendar_event_id:
        return False

    try:

        service.events().delete(
            calendarId="primary",
            eventId=booking.google_calendar_event_id,
        ).execute()

    except Exception:
        pass

    booking.google_calendar_event_id = None

    booking.save(
        update_fields=[
            "google_calendar_event_id"
        ]
    )

    return True


def create_or_update_roster_event(roster):
    """
    Create or update a roster event in the assigned employee's
    Google Calendar.
    """

    employee = roster.employee

    if not employee:
        return None

    service = get_employee_google_calendar_service(employee)

    if not service:
        return None

    booking = roster.booking

    start_datetime = datetime.combine(
        roster.shift_date,
        roster.start_time,
    )

    end_datetime = datetime.combine(
        roster.shift_date,
        roster.end_time,
    )

    event_body = {
        "summary": (
            f"{booking.service_type} - "
            f"{booking.customer.full_name} - "
            f"{employee.full_name}"
        ),
        "location": (
            f"{booking.address}, "
            f"{booking.suburb_postcode}"
        ),
        "description": (
            f"EMPLOYEE ROSTER\n\n"
            f"Employee: {employee.full_name}\n"
            f"Employee Phone: {employee.phone}\n"
            f"Employee Email: {employee.email}\n\n"
            f"Customer: {booking.customer.full_name}\n"
            f"Customer Phone: {booking.customer.phone}\n"
            f"Customer Email: {booking.customer.email}\n\n"
            f"Service: {booking.service_type}\n"
            f"Booking Status: {booking.get_status_display()}\n"
            f"Roster Status: {roster.get_status_display()}\n"
            f"Shift: {roster.start_time} - {roster.end_time}\n"
            f"Price: ${booking.quoted_price}\n\n"
            f"Notes: {roster.notes}\n\n"
            f"Created by YD Commercial Cleaning Services CRM"
        ),
        "start": {
            "dateTime": start_datetime.isoformat(),
            "timeZone": "Australia/Adelaide",
        },
        "end": {
            "dateTime": end_datetime.isoformat(),
            "timeZone": "Australia/Adelaide",
        },
    }

    if roster.google_calendar_event_id:

        event = (
            service.events()
            .update(
                calendarId="primary",
                eventId=roster.google_calendar_event_id,
                body=event_body,
            )
            .execute()
        )

    else:

        event = (
            service.events()
            .insert(
                calendarId="primary",
                body=event_body,
            )
            .execute()
        )

        roster.google_calendar_event_id = event.get("id")

        roster.save(
            update_fields=[
                "google_calendar_event_id"
            ]
        )

    return event


def delete_roster_event(roster):
    """
    Delete the roster event from the employee's
    Google Calendar.
    """

    employee = roster.employee

    if not employee:
        return False

    service = get_employee_google_calendar_service(employee)

    if not service:
        return False

    if not roster.google_calendar_event_id:
        return False

    try:

        service.events().delete(
            calendarId="primary",
            eventId=roster.google_calendar_event_id,
        ).execute()

    except Exception:
        pass

    roster.google_calendar_event_id = None

    roster.save(
        update_fields=[
            "google_calendar_event_id"
        ]
    )

    return True