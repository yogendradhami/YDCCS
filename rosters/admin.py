import logging

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction

from bookings.models import Booking
from google_reviews.calendar_utils import (
    CalendarNotConfigured,
    create_or_update_roster_event,
    delete_roster_event,
)

from .models import Roster
from .services import (
    RosterSyncLockError,
    booking_roster_sync_lock,
)

logger = logging.getLogger(__name__)


@admin.register(Roster)
class RosterAdmin(admin.ModelAdmin):

    list_display = (
        "employee",
        "shift_date",
        "start_time",
        "end_time",
        "status",
    )

    list_filter = (
        "status",
        "shift_date",
    )

    search_fields = ("employee__full_name",)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj:
            return (*readonly_fields, "employee", "booking")
        return readonly_fields

    def save_model(self, request, obj, form, change):
        calendar_state = "synced"
        try:
            with booking_roster_sync_lock(obj.booking_id):
                with transaction.atomic():
                    booking = Booking.objects.select_for_update().get(
                        pk=obj.booking_id
                    )
                    if booking.assigned_employee_id != obj.employee_id:
                        raise ValidationError(
                            "The roster employee must match the booking assignment."
                        )
                    super().save_model(request, obj, form, change)
                try:
                    event = create_or_update_roster_event(obj)
                    if event is None:
                        raise CalendarNotConfigured(
                            "Employee Calendar is not configured."
                        )
                except DatabaseError:
                    raise
                except CalendarNotConfigured:
                    calendar_state = "not_configured"
                except Exception:
                    calendar_state = "pending"
                    logger.exception(
                        "Calendar sync failed after saving roster %s in Django admin.",
                        obj.pk,
                    )
        except (DatabaseError, RosterSyncLockError) as exc:
            logger.exception(
                "Could not safely save roster %s in Django admin.",
                obj.pk,
            )
            raise ValidationError(
                "The roster could not be safely saved. Please retry."
            ) from exc

        if calendar_state == "not_configured":
            messages.info(
                request,
                "Roster saved. Employee Calendar is not configured.",
            )
        elif calendar_state == "pending":
            messages.warning(
                request,
                "Roster saved, but Calendar synchronization is pending.",
            )

    def delete_model(self, request, obj):
        try:
            with booking_roster_sync_lock(obj.booking_id):
                with transaction.atomic():
                    Booking.objects.select_for_update().get(pk=obj.booking_id)
                    roster = Roster.objects.select_for_update().get(pk=obj.pk)
                    if (
                        roster.google_calendar_event_id
                        and not delete_roster_event(roster)
                    ):
                        raise ValidationError(
                            "The roster was kept because its Calendar event could not be removed."
                        )
                    roster.delete()
        except RosterSyncLockError as exc:
            logger.exception(
                "Could not safely delete roster %s in Django admin.",
                obj.pk,
            )
            raise ValidationError(
                "The roster could not be safely deleted. Please retry."
            ) from exc

    def delete_queryset(self, request, queryset):
        for roster in queryset.select_related("booking"):
            self.delete_model(request, roster)
