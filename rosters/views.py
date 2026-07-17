# ==========================================================
# File: roster/views.py
# Purpose:
# Roster management and employee schedules.
# ==========================================================

<<<<<<< HEAD
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import RosterForm
from .models import Roster
=======
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import Roster
from .forms import RosterForm

>>>>>>> 5815f15 (Initial project commit)

# ==========================================================
# Admin Roster List
# ==========================================================

<<<<<<< HEAD

@login_required
def roster_list(request):

    rosters = Roster.objects.select_related("employee", "booking")

    return render(request, "roster_list.html", {"rosters": rosters})
=======
@login_required
def roster_list(request):

    rosters = Roster.objects.select_related(
        "employee",
        "booking"
    )

    return render(
        request,
        "rosters/roster_list.html",
        {
            "rosters": rosters
        }
    )
>>>>>>> 5815f15 (Initial project commit)


# ==========================================================
# Add Roster
# ==========================================================

<<<<<<< HEAD

=======
>>>>>>> 5815f15 (Initial project commit)
@login_required
def add_roster(request):

    if request.method == "POST":

        form = RosterForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("roster_list")

    else:
        form = RosterForm()

<<<<<<< HEAD
    return render(request, "roster_form.html", {"form": form})
=======
    return render(
        request,
        "rosters/roster_form.html",
        {
            "form": form
        }
    )
>>>>>>> 5815f15 (Initial project commit)


# ==========================================================
# Employee Schedule
# ==========================================================

<<<<<<< HEAD

=======
>>>>>>> 5815f15 (Initial project commit)
@login_required
def employee_roster(request):

    employee = request.user.employee_profile

    today = timezone.now().date()

<<<<<<< HEAD
    rosters = Roster.objects.filter(employee=employee).select_related("booking")

    today_shifts = rosters.filter(shift_date=today)

    upcoming_shifts = rosters.filter(shift_date__gt=today)

    completed_shifts = rosters.filter(status="completed")

    return render(
        request,
        "employee_roster.html",
=======
    rosters = Roster.objects.filter(
        employee=employee
    ).select_related(
        "booking"
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
>>>>>>> 5815f15 (Initial project commit)
        {
            "rosters": rosters,
            "today_shifts": today_shifts,
            "upcoming_shifts": upcoming_shifts,
            "completed_shifts": completed_shifts.count(),
<<<<<<< HEAD
        },
    )
=======
        }
    )
>>>>>>> 5815f15 (Initial project commit)
