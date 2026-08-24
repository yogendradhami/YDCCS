# ==========================================================
# File: roster/views.py
# Purpose:
# Roster management and employee schedules.
# ==========================================================

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from google_reviews.calendar_utils import create_or_update_booking_event

from .forms import RosterForm
from .models import Roster

# ==========================================================
# Admin Roster List
# ==========================================================


@login_required
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


@login_required
def add_roster(request):

    if request.method == "POST":

        form = RosterForm(request.POST)

        if form.is_valid():

            roster = form.save()

            try:
                from google_reviews.calendar_utils import (
                    create_or_update_roster_event,
                )

                create_or_update_roster_event(roster)

                messages.success(
                    request,
                    "Roster shift created and synced to Google Calendar.",
                )

            except Exception as error:

                messages.warning(
                    request,
                    (
                        "Roster shift was created, "
                        f"but Google Calendar sync failed: {error}"
                    ),
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

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import RosterForm
from .models import Roster


# ==========================================================
# Admin Roster List
# ==========================================================


# ==========================================================
# Add Roster
# ==========================================================

@login_required
def add_roster(request):

    if request.method == "POST":

        form = RosterForm(request.POST)

        if form.is_valid():

            roster = form.save()

            try:
                from google_reviews.calendar_utils import (
                    create_or_update_roster_event,
                )

                create_or_update_roster_event(roster)

                messages.success(
                    request,
                    "Roster shift created and synced to Google Calendar.",
                )

            except Exception as error:

                messages.warning(
                    request,
                    (
                        "Roster shift was created, "
                        f"but Google Calendar sync failed: {error}"
                    ),
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

@login_required
def edit_roster(request, roster_id):

    roster = get_object_or_404(Roster, id=roster_id)

    if request.method == "POST":

        form = RosterForm(
            request.POST,
            instance=roster,
        )

        if form.is_valid():

            updated_roster = form.save()

            # --------------------------------------------------
            # Synchronise Roster status back to Booking
            # --------------------------------------------------

            booking = updated_roster.booking

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
                booking.save(
                    update_fields=["status"]
                )

            # --------------------------------------------------
            # Synchronise roster changes to Google Calendar
            # --------------------------------------------------

            try:

                from google_reviews.calendar_utils import (
                    create_or_update_roster_event,
                )

                create_or_update_roster_event(
                    updated_roster
                )

                messages.success(
                    request,
                    (
                        "Roster shift updated, booking status "
                        "synchronised, and Google Calendar updated."
                    ),
                )

            except Exception as error:

                messages.warning(
                    request,
                    (
                        "Roster shift and booking were updated, "
                        f"but Google Calendar sync failed: {error}"
                    ),
                )

            return redirect("roster_list")

    else:

        form = RosterForm(
            instance=roster
        )

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

@login_required
def delete_roster(request, roster_id):

    roster = get_object_or_404(Roster, id=roster_id)

    if request.method == "POST":

        try:
            from google_reviews.calendar_utils import (
                delete_roster_event,
            )

            delete_roster_event(roster)

            calendar_message = (
                "Google Calendar event removed."
            )

        except Exception as error:

            calendar_message = (
                f"Google Calendar sync warning: {error}"
            )

        roster.delete()

        messages.success(
            request,
            f"Roster shift deleted. {calendar_message}",
        )

        return redirect("roster_list")

    return render(
        request,
        "rosters/roster_confirm_delete.html",
        {"roster": roster},
    )


# ==========================================================
# Employee Schedule
# ==========================================================

@login_required
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
