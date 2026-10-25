from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from django.db import DatabaseError, DEFAULT_DB_ALIAS, transaction
from django.utils import timezone

from bookings.models import Booking
from notifications.utils import temporary_instance_flags
from .models import Roster, RosterSyncLock

logger = logging.getLogger(__name__)


class RosterSyncLockError(RuntimeError):
    pass


@dataclass(frozen=True)
class RosterSyncPending:
    roster: Roster | None
    error: Exception


@dataclass(frozen=True)
class RosterSyncNotConfigured:
    roster: Roster | None


@contextmanager
def booking_roster_sync_lock(booking_id, using=DEFAULT_DB_ALIAS):
    """Lock in order: sync-lock row, Booking row, then Roster row."""
    try:
        RosterSyncLock.objects.using(using).get_or_create(booking_id=booking_id)
    except DatabaseError as exc:
        raise RosterSyncLockError(
            f"Could not initialize the roster sync lock for booking {booking_id}."
        ) from exc

    acquiring = True
    try:
        with transaction.atomic(using=using):
            lock = RosterSyncLock.objects.using(using).select_for_update().get(
                booking_id=booking_id
            )
            lock.touched_at = timezone.now()
            lock.save(using=using, update_fields=["touched_at"])
            acquiring = False
            yield
    except (DatabaseError, RosterSyncLock.DoesNotExist) as exc:
        if not acquiring:
            raise
        raise RosterSyncLockError(
            f"Could not acquire the roster sync lock for booking {booking_id}."
        ) from exc


def sync_booking_roster(booking):
    """Keep the booking's roster shift and calendar event in sync."""
    using = booking._state.db or DEFAULT_DB_ALIAS
    with booking_roster_sync_lock(booking.pk, using=using):
        return _sync_booking_roster_locked(booking.pk, using=using)


def _sync_booking_roster_locked(booking_id, using=DEFAULT_DB_ALIAS):
    from google_reviews.calendar_utils import (
        CalendarNotConfigured,
        create_or_update_roster_event,
        delete_roster_event,
    )

    delete_event = False
    employee_changed = False
    with transaction.atomic(using=using):
        locked_booking = (
            Booking.objects.using(using).select_for_update()
            .select_related("assigned_employee")
            .get(pk=booking_id)
        )
        employee = locked_booking.assigned_employee
        roster = (
            Roster.objects.using(using).select_for_update()
            .filter(booking=locked_booking)
            .order_by("id")
            .first()
        )

        if roster is None and locked_booking.status == "cancelled":
            return None
        employee_changed = bool(
            roster
            and employee
            and roster.employee_id != employee.pk
        )
        if employee_changed and roster.google_calendar_event_id:
            delete_event = True
        elif roster and (
            not employee
            or (
                locked_booking.status == "cancelled"
                and not employee_changed
            )
        ):
            roster.status = "cancelled"
            roster.save(update_fields=["status"])
            delete_event = bool(roster.google_calendar_event_id)
        elif not employee:
            return roster
        else:
            start_time = locked_booking.booking_time
            start_datetime = datetime.combine(
                locked_booking.booking_date,
                start_time,
            )
            end_time = (start_datetime + timedelta(hours=2)).time()

            if locked_booking.status == "cancelled":
                roster_status = "cancelled"
            elif locked_booking.status == "completed":
                roster_status = "completed"
            elif roster and roster.status in {"completed", "cancelled"}:
                roster_status = roster.status
            else:
                roster_status = "scheduled"

            if roster:
                if employee_changed:
                    with temporary_instance_flags(
                        roster,
                        _suppress_roster_notifications=True,
                    ):
                        roster.employee = employee
                        roster.shift_date = locked_booking.booking_date
                        roster.start_time = start_time
                        roster.end_time = end_time
                        roster.status = roster_status
                        roster.notes = locked_booking.notes
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
                    roster.employee = employee
                    roster.shift_date = locked_booking.booking_date
                    roster.start_time = start_time
                    roster.end_time = end_time
                    roster.status = roster_status
                    roster.notes = locked_booking.notes
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
                    booking=locked_booking,
                    shift_date=locked_booking.booking_date,
                    start_time=start_time,
                    end_time=end_time,
                    status=roster_status,
                    notes=locked_booking.notes,
                )

    if delete_event:
        current_booking = (
            Booking.objects.using(using)
            .select_for_update()
            .get(pk=booking_id)
        )
        current_roster = (
            Roster.objects.using(using)
            .select_for_update()
            .get(pk=roster.pk)
        )
        if (
            (
                employee_changed
                and current_booking.assigned_employee_id
                == current_roster.employee_id
            )
            or current_roster.google_calendar_event_id
            != roster.google_calendar_event_id
        ):
            return _sync_booking_roster_locked(booking_id, using=using)
        roster = current_roster
        try:
            deleted = delete_roster_event(roster)
        except DatabaseError:
            raise
        except Exception as exc:
            deleted = False
            logger.exception(
                "Roster Calendar deletion raised an exception for booking %s.",
                booking_id,
            )
        else:
            exc = RuntimeError(
                "The existing roster calendar event could not be removed."
            )
        if not deleted:
            if employee_changed:
                Booking.objects.using(using).filter(pk=booking_id).update(
                    assigned_employee_id=roster.employee_id
                )
            return RosterSyncPending(roster=roster, error=exc)
        if employee_changed:
            return _sync_booking_roster_locked(booking_id, using=using)
        return roster

    if (
        roster
        and locked_booking.assigned_employee_id
        and locked_booking.status != "cancelled"
    ):
        current_booking = (
            Booking.objects.using(using)
            .select_for_update()
            .get(pk=booking_id)
        )
        current_roster = (
            Roster.objects.using(using)
            .select_for_update()
            .get(pk=roster.pk)
        )
        current_employee_id = current_booking.assigned_employee_id
        if current_employee_id != current_roster.employee_id:
            return _sync_booking_roster_locked(booking_id, using=using)
        roster = current_roster
        try:
            event = create_or_update_roster_event(roster)
            if event is None:
                raise CalendarNotConfigured(
                    "The employee's Calendar integration is not configured."
                )
        except CalendarNotConfigured:
            return RosterSyncNotConfigured(roster=roster)
        except DatabaseError:
            raise
        except Exception as exc:
            logger.exception(
                "Roster Calendar synchronization failed for booking %s.",
                booking_id,
            )
            return RosterSyncPending(roster=roster, error=exc)

    if employee_changed and roster:
        from notifications.utils import notify_admins, notify_user

        notify_admins(
            "Roster Shift Updated",
            f"{roster.employee.full_name}'s roster shift for "
            f"{roster.shift_date} was updated.",
            "roster",
            "/dashboard/rosters/",
        )
        if roster.employee.user:
            if roster.status == "cancelled":
                employee_message = (
                    f"Your shift on {roster.shift_date} was cancelled."
                )
            else:
                employee_message = (
                    f"You have a shift on {roster.shift_date} from "
                    f"{roster.start_time} to {roster.end_time}."
                )
            notify_user(
                roster.employee.user,
                "Roster Shift Updated",
                employee_message,
                "roster",
                "/employee/roster/",
            )
    return roster
