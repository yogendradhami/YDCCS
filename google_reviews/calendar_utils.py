import base64
import hashlib
import logging
from datetime import datetime, timedelta

from django.conf import settings
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from bookings.models import Booking
from employees.models import EmployeeGoogleAccount
from googleapiclient.errors import HttpError
from .models import GoogleAccount

logger = logging.getLogger(__name__)


class CalendarServiceUnavailable(RuntimeError):
    pass


class CalendarNotConfigured(RuntimeError):
    pass


EMPLOYEE_GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
]

COMPANY_GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
]


def get_company_google_calendar_service():
    google_account = GoogleAccount.objects.order_by(
        "-updated_at", "-id"
    ).first()
    if not google_account or not google_account.access_token:
        return None

    credentials = Credentials(
        token=google_account.access_token,
        refresh_token=google_account.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=COMPANY_GOOGLE_SCOPES,
        expiry=google_account.updated_at + timedelta(minutes=55),
    )

    if credentials.expired:
        if not credentials.refresh_token:
            raise CalendarNotConfigured(
                "The company Google Calendar token expired without a refresh token. "
                "Reconnect the company Google account."
            )

        credentials.refresh(Request())
        google_account.access_token = credentials.token
        if credentials.refresh_token:
            google_account.refresh_token = credentials.refresh_token
        google_account.save(
            update_fields=["access_token", "refresh_token", "updated_at"]
        )

    return build("calendar", "v3", credentials=credentials)


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
        expiry=google_account.updated_at + timedelta(minutes=55),
    )

    # Refresh expired access token automatically.
    if credentials.expired:
        if not credentials.refresh_token:
            raise CalendarNotConfigured(
                f"Employee {employee.pk}'s Google Calendar access expired "
                "without a refresh token. Reconnect Google Calendar."
            )
        credentials.refresh(Request())

        google_account.access_token = credentials.token
        if credentials.refresh_token:
            google_account.refresh_token = credentials.refresh_token
        google_account.save(
            update_fields=[
                "access_token",
                "refresh_token",
                "updated_at",
            ]
        )

    return build(
        "calendar",
        "v3",
        credentials=credentials,
    )



def _upsert_calendar_event(service, event_id, event_body, resource_type, resource_id):
    """Update an existing Calendar event or recreate it if it no longer exists."""
    if event_id:
        try:
            return (
                service.events()
                .update(
                    calendarId="primary",
                    eventId=event_id,
                    body=event_body,
                )
                .execute()
            )
        except HttpError as exc:
            if getattr(exc.resp, "status", None) != 404:
                logger.exception(
                    "Could not update Google Calendar event for %s %s.",
                    resource_type,
                    resource_id,
                )
                raise

            logger.info(
                "Google Calendar event for %s %s was not found; creating a replacement.",
                resource_type,
                resource_id,
            )

    try:
        return (
            service.events()
            .insert(
                calendarId="primary",
                body=event_body,
            )
            .execute()
        )
    except HttpError as exc:
        if getattr(exc.resp, "status", None) != 409 or not event_id:
            raise

        logger.info(
            "Google Calendar event ID for %s %s already exists; updating it.",
            resource_type,
            resource_id,
        )
        return (
            service.events()
            .update(
                calendarId="primary",
                eventId=event_id,
                body=event_body,
            )
            .execute()
        )



def create_or_update_booking_event(booking, *, service=None):
    """
    Create or update the booking event in the company Google Calendar.
    """

    employee = booking.assigned_employee

    if not service:
        service = get_company_google_calendar_service()
        if not service:
            raise CalendarNotConfigured(
                "The company Google Calendar is not connected."
            )

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

    employee_name = employee.full_name if employee else "Unassigned"
    customer = booking.customer
    customer_name = customer.full_name if customer else "No customer"
    customer_phone = customer.phone if customer else "Not provided"
    customer_email = customer.email if customer else "Not provided"

    event_body = {
        "summary": (
            f"{booking.service_type} - "
            f"{customer_name}"
        ),
        "location": (
            f"{booking.address}, "
            f"{booking.suburb_postcode}"
        ),
        "description": (
            f"Customer: {customer_name}\n"
            f"Phone: {customer_phone}\n"
            f"Email: {customer_email}\n"
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


    event = _upsert_calendar_event(
        service,
        booking.google_calendar_event_id,
        event_body,
        "booking",
        booking.pk,
    )

    new_event_id = event.get("id")
    if new_event_id and new_event_id != booking.google_calendar_event_id:
        booking.google_calendar_event_id = new_event_id
        booking.save(update_fields=["google_calendar_event_id"])

    return event




def create_or_update_roster_event(roster):
    """
    Create or update a roster event in the assigned employee's
    Google Calendar.
    """

    employee = roster.employee

    if not employee:
        raise CalendarServiceUnavailable(
            f"Roster {roster.pk} has no assigned employee for Calendar sync."
        )

    service = get_employee_google_calendar_service(employee)

    if not service:
        raise CalendarNotConfigured(
            f"Google Calendar is not configured for employee {employee.pk}."
        )

    booking = roster.booking
    customer = booking.customer
    customer_name = customer.full_name if customer else "No customer"
    customer_phone = customer.phone if customer else "Not provided"
    customer_email = customer.email if customer else "Not provided"

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
            f"{customer_name} - "
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
            f"Customer: {customer_name}\n"
            f"Customer Phone: {customer_phone}\n"
            f"Customer Email: {customer_email}\n\n"
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

    event_id = roster.google_calendar_event_id
    if not event_id:
        stable_id_source = f"roster:{roster.pk}:employee:{employee.pk}".encode()
        event_id = (
            "r"
            + base64.b32hexencode(
                hashlib.sha256(stable_id_source).digest()
            )
            .decode("ascii")
            .lower()
            .rstrip("=")
        )
        roster.google_calendar_event_id = event_id
        roster.save(update_fields=["google_calendar_event_id"])
    event_body["id"] = event_id

    event = _upsert_calendar_event(
        service,
        event_id,
        event_body,
        "roster",
        roster.pk,
    )

    new_event_id = event.get("id")
    if new_event_id and new_event_id != roster.google_calendar_event_id:
        roster.google_calendar_event_id = new_event_id
        roster.save(update_fields=["google_calendar_event_id"])

    return event





def _delete_calendar_event(service, event_id, resource_type, resource_id):
    """Delete a Google Calendar event, treating HTTP 404 as success."""
    try:
        service.events().delete(
            calendarId="primary",
            eventId=event_id,
        ).execute()
    except HttpError as exc:
        if getattr(exc.resp, "status", None) != 404:
            logger.exception(
                "Could not delete Google Calendar event for %s %s.",
                resource_type,
                resource_id,
            )
            return False
    except Exception:
        logger.exception(
            "Could not delete Google Calendar event for %s %s.",
            resource_type,
            resource_id,
        )
        return False

    return True


def delete_booking_event(booking):
    """Delete the booking event from the company Google Calendar."""
    event_id = booking.google_calendar_event_id

    if not event_id:
        return False

    service = get_company_google_calendar_service()
    if not service:
        return False

    if not _delete_calendar_event(service, event_id, "booking", booking.pk):
        return False

    booking.google_calendar_event_id = None
    booking.save(update_fields=["google_calendar_event_id"])
    return True


def sync_existing_bookings_to_company_calendar():
    """Backfill non-cancelled bookings into the connected company calendar."""
    service = get_company_google_calendar_service()
    if not service:
        raise CalendarNotConfigured("The company Google Calendar is not connected.")

    synced_count = 0
    failed_count = 0

    for booking in Booking.objects.exclude(status="cancelled").order_by("id"):
        try:
            event = create_or_update_booking_event(booking, service=service)
            if event is None:
                raise CalendarServiceUnavailable(
                    "Google Calendar did not return an event for the booking."
                )
        except Exception:
            failed_count += 1
            logger.exception(
                "Could not sync booking %s to the company Google Calendar.",
                booking.pk,
            )
        else:
            synced_count += 1

    return synced_count, failed_count


def delete_roster_event(roster):
    """Delete the roster event from the employee's calendar."""
    employee = roster.employee
    event_id = roster.google_calendar_event_id

    if not employee or not event_id:
        return False

    service = get_employee_google_calendar_service(employee)
    if not service:
        return False

    if not _delete_calendar_event(service, event_id, "roster", roster.pk):
        return False

    roster.google_calendar_event_id = None
    roster.save(update_fields=["google_calendar_event_id"])
    return True
