from django.urls import path

from .views import (
<<<<<<< HEAD
    add_leave_request,
    approve_leave_request,
    employee_apply_leave,
    employee_leave_history,
    leave_list,
    reject_leave_request,
=======
    leave_list,
    add_leave_request,
    approve_leave_request,
    reject_leave_request,
    employee_leave_history,
    employee_apply_leave,
>>>>>>> 5815f15 (Initial project commit)
)

urlpatterns = [
    path("dashboard/leave/", leave_list, name="leave_list"),
    path("dashboard/leave/add/", add_leave_request, name="add_leave_request"),
<<<<<<< HEAD
    path(
        "dashboard/leave/<int:leave_id>/approve/",
        approve_leave_request,
        name="approve_leave_request",
    ),
    path(
        "dashboard/leave/<int:leave_id>/reject/",
        reject_leave_request,
        name="reject_leave_request",
    ),
    path("employee/leave/", employee_leave_history, name="employee_leave_history"),
    path("employee/leave/request/", employee_apply_leave, name="employee_apply_leave"),
]
=======
    path("dashboard/leave/<int:leave_id>/approve/", approve_leave_request, name="approve_leave_request"),
    path("dashboard/leave/<int:leave_id>/reject/", reject_leave_request, name="reject_leave_request"),

    path("employee/leave/", employee_leave_history, name="employee_leave_history"),
    path("employee/leave/request/", employee_apply_leave, name="employee_apply_leave"),
]
>>>>>>> 5815f15 (Initial project commit)
