from django.urls import path

from .views import (
<<<<<<< HEAD
    add_roster,
    employee_roster,
    roster_list,
)

urlpatterns = [
    path("dashboard/rosters/", roster_list, name="roster_list"),
    path("dashboard/rosters/add/", add_roster, name="add_roster"),
    path("employee/roster/", employee_roster, name="employee_roster"),
]
=======
    roster_list,
    add_roster,
    employee_roster,
)

urlpatterns = [

    path(
        "dashboard/rosters/",
        roster_list,
        name="roster_list"
    ),

    path(
        "dashboard/rosters/add/",
        add_roster,
        name="add_roster"
    ),

    path(
        "employee/roster/",
        employee_roster,
        name="employee_roster"
    ),
]
>>>>>>> 5815f15 (Initial project commit)
