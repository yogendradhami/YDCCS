from django.urls import path

from .views import (
    add_roster,
    delete_roster,
    edit_roster,
    employee_roster,
    roster_list,
)

urlpatterns = [
    path(
        "dashboard/rosters/",
        roster_list,
        name="roster_list",
    ),

    path(
        "dashboard/rosters/add/",
        add_roster,
        name="add_roster",
    ),

    path(
        "dashboard/rosters/<int:roster_id>/edit/",
        edit_roster,
        name="edit_roster",
    ),

    path(
        "dashboard/rosters/<int:roster_id>/delete/",
        delete_roster,
        name="delete_roster",
    ),

    path(
        "employee/roster/",
        employee_roster,
        name="employee_roster",
    ),
]