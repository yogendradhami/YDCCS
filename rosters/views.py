# ==========================================================
# File: roster/views.py
# Purpose:
# Roster management and employee schedules.
# ==========================================================

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import RosterForm
from .models import Roster

# ==========================================================
# Admin Roster List
# ==========================================================


@login_required
def roster_list(request):

    rosters = Roster.objects.select_related("employee", "booking")

    return render(request, "rosters/roster_list.html", {"rosters": rosters})


# ==========================================================
# Add Roster
# ==========================================================


@login_required
def add_roster(request):

    if request.method == "POST":

        form = RosterForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("roster_list")

    else:
        form = RosterForm()

    return render(request, "rosters/roster_form.html", {"form": form})


# ==========================================================
# Employee Schedule
# ==========================================================


@login_required
def employee_roster(request):

    employee = request.user.employee_profile

    today = timezone.now().date()

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
