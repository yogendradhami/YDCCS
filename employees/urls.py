# ==========================================================
# File: employees/urls.py
# Purpose:
# Employee portal URL routes
# - Login / Logout
# - Dashboard
# - Jobs
# - Job details
# - Photo upload
# - Profile
# ==========================================================

from django.urls import path

from .views import (
<<<<<<< HEAD
    employee_dashboard,
    employee_job_detail,
    employee_jobs,
    employee_login,
    employee_logout,
    employee_profile,
    upload_job_photo,
)

=======
    employee_login,
    employee_logout,
    employee_dashboard,
    employee_jobs,
    employee_job_detail,
    upload_job_photo,
    employee_profile,
)


>>>>>>> 5815f15 (Initial project commit)
urlpatterns = [
    # Employee authentication routes
    path("employee/login/", employee_login, name="employee_login"),
    path("employee/logout/", employee_logout, name="employee_logout"),
<<<<<<< HEAD
    # Employee dashboard route
    path("employee/dashboard/", employee_dashboard, name="employee_dashboard"),
    # Employee profile route
    path("employee/profile/", employee_profile, name="employee_profile"),
    # Employee job routes
    path("employee/jobs/", employee_jobs, name="employee_jobs"),
    path(
        "employee/jobs/<int:booking_id>/",
        employee_job_detail,
        name="employee_job_detail",
    ),
    path(
        "employee/jobs/<int:booking_id>/upload-photo/",
        upload_job_photo,
        name="upload_job_photo",
    ),
]
=======

    # Employee dashboard route
    path("employee/dashboard/", employee_dashboard, name="employee_dashboard"),

    # Employee profile route
    path("employee/profile/", employee_profile, name="employee_profile"),

    # Employee job routes
    path("employee/jobs/", employee_jobs, name="employee_jobs"),
    path("employee/jobs/<int:booking_id>/", employee_job_detail, name="employee_job_detail"),
    path("employee/jobs/<int:booking_id>/upload-photo/", upload_job_photo, name="upload_job_photo"),
]
>>>>>>> 5815f15 (Initial project commit)
