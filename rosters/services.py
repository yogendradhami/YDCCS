from datetime import datetime, timedelta

from django.db import transaction

from .models import Roster


def sync_booking_roster(booking):
    """
    Keep the Booking and its employee Roster synchronised.

    Booking -> Roster:
        - Assigned employee + booking -> create/update roster
        - Booking date/time -> roster date/time
        - Booking completed -> roster completed
        - Booking cancelled -> roster cancelled

    Existing completed/cancelled roster statuses are preserved when a
    booking is merely edited or reassigned, unless the booking itself
    explicitly becomes completed/cancelled.

    Google Calendar synchronisation continues through the existing
    roster calendar utility.
    """

    from google_reviews.calendar_utils import (
        create_or_update_roster_event,
    )

    employee = booking.assigned_employee

    # ----------------------------------------------------------
    # Find an existing roster for this booking
    # ----------------------------------------------------------

    roster = (
        Roster.objects
        .filter(booking=booking)
        .order_by("id")
        .first()
    )

    # ----------------------------------------------------------
    # No assigned employee
    # ----------------------------------------------------------

    if not employee:

        if roster:
            # Keep the roster record, but cancel it so that the
            # booking no longer appears as an active employee shift.
            roster.status = "cancelled"
            roster.save(update_fields=["status"])

            try:
                create_or_update_roster_event(roster)
            except Exception:
                # Calendar errors should not break booking saving.
                pass

        return roster

    # ----------------------------------------------------------
    # Calculate the two-hour roster shift
    # ----------------------------------------------------------

    start_time = booking.booking_time

    start_datetime = datetime.combine(
        booking.booking_date,
        start_time,
    )

    end_datetime = start_datetime + timedelta(hours=2)

    end_time = end_datetime.time()

    # ----------------------------------------------------------
    # Determine roster status
    # ----------------------------------------------------------

    if booking.status == "cancelled":

        roster_status = "cancelled"

    elif booking.status == "completed":

        roster_status = "completed"

    elif roster and roster.status in {
        "completed",
        "cancelled",
    }:

        # IMPORTANT:
        # Do not destroy a status that was already deliberately
        # set from the roster side.

        roster_status = roster.status

    else:

        roster_status = "scheduled"

    # ----------------------------------------------------------
    # Create or update roster
    # ----------------------------------------------------------

    with transaction.atomic():

        if roster:

            roster.employee = employee
            roster.shift_date = booking.booking_date
            roster.start_time = start_time
            roster.end_time = end_time
            roster.status = roster_status
            roster.notes = booking.notes

            roster.save(
                update_fields=[
                    "employee",
                    "shift_date",
                    "start_time",
                    "end_time",
                    "status",
                    "notes",
                ]
            )

        else:

            roster = Roster.objects.create(
                employee=employee,
                booking=booking,
                shift_date=booking.booking_date,
                start_time=start_time,
                end_time=end_time,
                status=roster_status,
                notes=booking.notes,
            )

    # ----------------------------------------------------------
    # Google Calendar
    # ----------------------------------------------------------

    create_or_update_roster_event(roster)

    return roster