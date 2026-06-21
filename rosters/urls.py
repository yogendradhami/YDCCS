from django.urls import path

from .views import (
    add_roster,
    employee_roster,
    roster_list,
)

urlpatterns = [
    path("dashboard/rosters/", roster_list, name="roster_list"),
    path("dashboard/rosters/add/", add_roster, name="add_roster"),
    path("employee/roster/", employee_roster, name="employee_roster"),
]
