from django.urls import path

from .views import (
    attendance_dashboard,
    check_in,
    check_out,
)

urlpatterns = [
<<<<<<< HEAD
    path("employee/attendance/", attendance_dashboard, name="attendance_dashboard"),
    path("employee/check-in/<int:booking_id>/", check_in, name="check_in"),
    path("employee/check-out/<int:booking_id>/", check_out, name="check_out"),
]
=======
    path(
        "employee/attendance/",
        attendance_dashboard,
        name="attendance_dashboard"
    ),

    path(
        "employee/check-in/<int:booking_id>/",
        check_in,
        name="check_in"
    ),

    path(
        "employee/check-out/<int:booking_id>/",
        check_out,
        name="check_out"
    ),
]
>>>>>>> 5815f15 (Initial project commit)
