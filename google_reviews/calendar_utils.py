from datetime import datetime, timedelta

from django.conf import settings
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .models import GoogleAccount


def get_google_calendar_service():
    google_account = GoogleAccount.objects.first()

    if not google_account:
        return None

    creds = Credentials(
        token=google_account.access_token,
        refresh_token=google_account.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )

<<<<<<< HEAD
    return build("calendar", "v3", credentials=creds)
=======
    return build(
        "calendar",
        "v3",
        credentials=creds
    )
>>>>>>> 5815f15 (Initial project commit)


def create_or_update_booking_event(booking):
    service = get_google_calendar_service()

    if not service:
        return None

<<<<<<< HEAD
    start_datetime = datetime.combine(booking.booking_date, booking.booking_time)
=======
    start_datetime = datetime.combine(
        booking.booking_date,
        booking.booking_time
    )
>>>>>>> 5815f15 (Initial project commit)

    end_datetime = start_datetime + timedelta(hours=2)

    employee_name = "Not assigned"

    if booking.assigned_employee:
        employee_name = booking.assigned_employee.full_name

    event_body = {
        "summary": f"{booking.service_type} - {booking.customer.full_name}",
        "location": f"{booking.address}, {booking.suburb_postcode}",
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
<<<<<<< HEAD
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
        event = service.events().insert(calendarId="primary", body=event_body).execute()
=======
        event = service.events().update(
            calendarId="primary",
            eventId=booking.google_calendar_event_id,
            body=event_body
        ).execute()
    else:
        event = service.events().insert(
            calendarId="primary",
            body=event_body
        ).execute()
>>>>>>> 5815f15 (Initial project commit)

        booking.google_calendar_event_id = event.get("id")
        booking.save(update_fields=["google_calendar_event_id"])

    return event


def delete_booking_event(booking):
    service = get_google_calendar_service()

    if not service:
        return False

    if not booking.google_calendar_event_id:
        return False

    service.events().delete(
<<<<<<< HEAD
        calendarId="primary", eventId=booking.google_calendar_event_id
=======
        calendarId="primary",
        eventId=booking.google_calendar_event_id
>>>>>>> 5815f15 (Initial project commit)
    ).execute()

    booking.google_calendar_event_id = None
    booking.save(update_fields=["google_calendar_event_id"])

<<<<<<< HEAD
    return True
=======
    return True
>>>>>>> 5815f15 (Initial project commit)
