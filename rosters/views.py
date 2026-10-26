# ==========================================================
# File: roster/views.py
# Purpose:
# Roster management and employee schedules.
# ==========================================================

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from bookings.models import Booking
from dashboard.decorators import admin_required
from employees.decorators import employee_required
from rosters.services import (
    RosterSyncLockError,
    RosterSyncNotConfigured,
    RosterSyncPending,
    booking_roster_sync_lock,
    sync_booking_roster,
)

from .forms import RosterForm
from .models import Roster

import logging

logger = logging.getLogger(__name__)

# ==========================================================
# Admin Roster List
# ==========================================================


@admin_required
def roster_list(request):

    rosters = Roster.objects.select_related(
        "employee",
        "booking",
        "booking__customer",
    ).all()

    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "").strip()
    date = request.GET.get("date", "").strip()

    if search:
        from django.db.models import Q

        rosters = rosters.filter(
            Q(employee__full_name__icontains=search)
            | Q(booking__customer__full_name__icontains=search)
            | Q(booking__service_type__icontains=search)
        )

    if status:
        rosters = rosters.filter(status=status)

    if date:
        rosters = rosters.filter(shift_date=date)

    # --------------------------------------------------
    # Separate upcoming/active and past rosters
    # --------------------------------------------------

    active_rosters = []
    past_rosters = []

    for roster in rosters:
        if roster.time_status in ["upcoming", "in_progress"]:
            active_rosters.append(roster)
        elif roster.time_status in ["time_passed", "completed", "cancelled"]:
            past_rosters.append(roster)

    # --------------------------------------------------
    # Summary counts
    # --------------------------------------------------

    total_count = rosters.count()

    scheduled_count = rosters.filter(
        status="scheduled"
    ).count()

    completed_count = rosters.filter(
        status="completed"
    ).count()

    synced_count = rosters.exclude(
        google_calendar_event_id__isnull=True
    ).exclude(
        google_calendar_event_id=""
    ).count()

    return render(
        request,
        "rosters/roster_list.html",
        {
            "rosters": rosters,
            "active_rosters": active_rosters,
            "past_rosters": past_rosters,

            "total_count": total_count,
            "scheduled_count": scheduled_count,
            "completed_count": completed_count,
            "synced_count": synced_count,

            "search": search,
            "selected_status": status,
            "selected_date": date,
            "status_choices": Roster.STATUS_CHOICES,
        },
    )




# ==========================================================
# Add Roster
# ==========================================================


@admin_required
def add_roster(request):

    if request.method == "POST":

        form = RosterForm(request.POST)

        if form.is_valid():
            try:
                booking_id = form.cleaned_data["booking"].pk
                with booking_roster_sync_lock(booking_id):
                    with transaction.atomic():
                        booking = Booking.objects.select_for_update().get(
                            pk=booking_id
                        )
                        employee = form.cleaned_data["employee"]
                        if booking.assigned_employee_id != employee.pk:
                            form.add_error(
                                "employee",
                                "The selected employee must match the booking assignment.",
                            )
                        else:
                            roster = form.save(commit=False)
                            roster.booking = booking
                            roster.save()
                            roster_sync = sync_booking_roster(booking)
                if form.errors:
                    return render(
                        request,
                        "rosters/roster_form.html",
                        {"form": form},
                    )
                if isinstance(roster_sync, RosterSyncPending):
                    messages.warning(
                        request,
                        "Roster shift was created, but Calendar sync is pending. Retry synchronization.",
                    )
                elif isinstance(roster_sync, RosterSyncNotConfigured):
                    messages.info(
                        request,
                        "Roster shift was created. Employee Calendar is not configured.",
                    )
                else:
                    messages.success(
                        request,
                        "Roster shift created.",
                    )
            except (DatabaseError, RosterSyncLockError):
                logger.exception(
                    "Could not safely create roster for booking %s.",
                    form.cleaned_data["booking"].pk,
                )
                messages.warning(
                    request,
                    "Roster shift could not be safely created. Please retry.",
                )

            return redirect("roster_list")

    else:
        form = RosterForm()

    return render(
        request,
        "rosters/roster_form.html",
        {"form": form},
    )



# ==========================================================
# Employee Schedule
# ==========================================================


@login_required
def employee_roster(request):

    employee = request.user.employee_profile

    today = timezone.now().date()# ==========================================================
# File: rosters/views.py
# Purpose:
# Roster management and employee schedules.
# ==========================================================

# ==========================================================
# Admin Roster List
# ==========================================================


# ==========================================================
# Add Roster
# ==========================================================

@admin_required
def add_roster(request):

    if request.method == "POST":

        form = RosterForm(request.POST)

        if form.is_valid():
            try:
                booking_id = form.cleaned_data["booking"].pk
                with booking_roster_sync_lock(booking_id):
                    with transaction.atomic():
                        booking = Booking.objects.select_for_update().get(
                            pk=booking_id
                        )
                        employee = form.cleaned_data["employee"]
                        if booking.assigned_employee_id != employee.pk:
                            form.add_error(
                                "employee",
                                "The selected employee must match the booking assignment.",
                            )
                        else:
                            roster = form.save(commit=False)
                            roster.booking = booking
                            roster.save()
                            roster_sync = sync_booking_roster(booking)
                if form.errors:
                    return render(
                        request,
                        "rosters/roster_form.html",
                        {"form": form},
                    )
                if isinstance(roster_sync, RosterSyncPending):
                    messages.warning(
                        request,
                        "Roster shift was created, but Calendar sync is pending. Retry synchronization.",
                    )
                elif isinstance(roster_sync, RosterSyncNotConfigured):
                    messages.info(
                        request,
                        "Roster shift was created. Employee Calendar is not configured.",
                    )
                else:
                    messages.success(
                        request,
                        "Roster shift created.",
                    )
            except (DatabaseError, RosterSyncLockError):
                logger.exception(
                    "Could not safely create roster for booking %s.",
                    form.cleaned_data["booking"].pk,
                )
                messages.warning(
                    request,
                    "Roster shift could not be safely created. Please retry.",
                )

            return redirect("roster_list")

    else:
        form = RosterForm()

    return render(
        request,
        "rosters/roster_form.html",
        {"form": form},
    )


# ==========================================================
# Edit Roster
# ==========================================================

@admin_required
def edit_roster(request, roster_id):
    roster = get_object_or_404(Roster, id=roster_id)

    if request.method == "POST":
        form = RosterForm(request.POST, instance=roster)
        form.fields["employee"].disabled = True
        form.fields["booking"].disabled = True
        try:
            with booking_roster_sync_lock(roster.booking_id):
                with transaction.atomic():
                    booking = Booking.objects.select_for_update().get(
                        pk=roster.booking_id
                    )
                    roster = Roster.objects.select_for_update().get(
                        pk=roster_id,
                        booking=booking,
                    )
                    form = RosterForm(request.POST, instance=roster)
                    form.fields["employee"].disabled = True
                    form.fields["booking"].disabled = True
                    if form.is_valid():
                        if (
                            not booking.assigned_employee_id
                            or roster.employee_id
                            != booking.assigned_employee_id
                        ):
                            form.add_error(
                                None,
                                "Correct the employee assignment in the booking before editing this roster.",
                            )
                        else:
                            updated_roster = form.save(commit=False)
                            updated_roster.booking = booking
                            updated_roster.save()

                            booking_status_map = {
                                "scheduled": "assigned",
                                "completed": "completed",
                                "cancelled": "cancelled",
                            }
                            new_booking_status = booking_status_map.get(
                                updated_roster.status
                            )
                            if (
                                new_booking_status
                                and booking.status != new_booking_status
                            ):
                                booking.status = new_booking_status
                                from notifications.utils import (
                                    temporary_instance_flags,
                                )

                                with temporary_instance_flags(
                                    booking,
                                    _suppress_customer_status_notification=True,
                                ):
                                    booking.save(update_fields=["status"])
                                booking_status_changed = True
                            else:
                                booking_status_changed = False

                if form.is_valid():
                    calendar_sync_succeeded = True
                    try:
                        from google_reviews.calendar_utils import (
                            CalendarNotConfigured,
                            create_or_update_roster_event,
                        )

                        event = create_or_update_roster_event(updated_roster)
                        if event is None:
                            raise CalendarNotConfigured(
                                "Employee Calendar is not configured."
                            )
                    except CalendarNotConfigured:
                        messages.info(
                            request,
                            "Roster shift and booking status were updated. Employee Calendar is not configured.",
                        )
                    except Exception:
                        calendar_sync_succeeded = False
                        logger.exception(
                            "Roster Calendar sync failed for roster %s.",
                            roster_id,
                        )
                        messages.warning(
                            request,
                            "Roster shift and booking were updated, but Calendar sync is pending.",
                        )
                    else:
                        messages.success(
                            request,
                            "Roster shift updated, booking status synchronized, and Calendar updated.",
                        )
                    if (
                        calendar_sync_succeeded
                        and booking_status_changed
                        and booking.customer
                        and booking.customer.user
                    ):
                        from notifications.utils import notify_user

                        notify_user(
                            booking.customer.user,
                            "Booking Updated",
                            (
                                f"Your booking for {booking.service_type} is now "
                                f"{booking.get_status_display()}."
                            ),
                            "booking",
                            f"/portal/bookings/{booking.pk}/",
                        )
                    return redirect("roster_list")
        except (DatabaseError, RosterSyncLockError):
            logger.exception(
                "Could not safely update roster %s.",
                roster_id,
            )
            messages.error(
                request,
                "Roster shift could not be safely updated. Please retry.",
            )
            roster.refresh_from_db()
            form = RosterForm(request.POST, instance=roster)
            form.fields["employee"].disabled = True
            form.fields["booking"].disabled = True

    else:
        form = RosterForm(instance=roster)
        form.fields["employee"].disabled = True
        form.fields["booking"].disabled = True

    return render(
        request,
        "rosters/roster_form.html",
        {
            "form": form,
            "editing": True,
            "roster": roster,
        },
    )

# ==========================================================
# Delete Roster
# ==========================================================

@admin_required
@require_http_methods(["GET", "POST"])
def delete_roster(request, roster_id):

    roster = get_object_or_404(Roster, id=roster_id)

    if request.method == "POST":
        try:
            with booking_roster_sync_lock(roster.booking_id):
                with transaction.atomic():
                    booking = Booking.objects.select_for_update().get(
                        pk=roster.booking_id
                    )
                    roster = Roster.objects.select_for_update().get(
                        pk=roster_id,
                        booking=booking,
                    )
                    if roster.google_calendar_event_id:
                        from google_reviews.calendar_utils import (
                            delete_roster_event,
                        )

                        try:
                            deleted = delete_roster_event(roster)
                        except Exception:
                            logger.exception(
                                "Could not remove Calendar event for roster %s.",
                                roster_id,
                            )
                            deleted = False
                        if not deleted:
                            messages.warning(
                                request,
                                "Roster was not deleted because its Calendar event could not be removed. Retry synchronization.",
                            )
                            return redirect("roster_list")
                    roster.delete()
        except (DatabaseError, RosterSyncLockError):
            logger.exception(
                "Could not safely delete roster %s.",
                roster_id,
            )
            messages.error(
                request,
                "Roster shift could not be safely deleted. Please retry.",
            )
            return redirect("roster_list")

        messages.success(request, "Roster shift deleted.")
        return redirect("roster_list")

    return render(
        request,
        "rosters/roster_confirm_delete.html",
        {"roster": roster},
    )


# ==========================================================
# Employee Schedule
# ==========================================================

@employee_required
def employee_roster(request):

    employee = request.user.employee_profile

    today = timezone.now().date()

    rosters = (
        Roster.objects
        .filter(employee=employee)
        .select_related("booking")
    )

    today_shifts = rosters.filter(
        shift_date=today
    )

    upcoming_shifts = rosters.filter(
        shift_date__gt=today
    )

    completed_shifts = rosters.filter(
        status="completed"
    )

    return render(
        request,
        "employees/employee_roster.html",
        {
            "employee": employee,
            "rosters": rosters,
            "today_shifts": today_shifts,
            "upcoming_shifts": upcoming_shifts,
            "completed_shifts": completed_shifts.count(),
        },
    )

    rosters = Roster.objects.filter(employee=employee).select_related("booking")

    today_shifts = rosters.filter(shift_date=today)

    upcoming_shifts = rosters.filter(shift_date__gt=today)

    completed_shifts = rosters.filter(status="completed")

    return render(
        request,
        "employees/employee_roster.html",
        {
            "rosters": rosters,
            "today_shifts": today_shifts,
            "upcoming_shifts": upcoming_shifts,
            "completed_shifts": completed_shifts.count(),
        },
    )
