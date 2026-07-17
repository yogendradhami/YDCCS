# ==========================================================
# File: payroll/urls.py
# Purpose:
# Payroll URL routes.
# ==========================================================

from django.urls import path

from .views import (
<<<<<<< HEAD
    approve_payroll,
    download_payslip_pdf,
    employee_payslips,
    generate_payroll,
    mark_payroll_paid,
    payroll_list,
)

urlpatterns = [
    path("dashboard/payroll/", payroll_list, name="payroll_list"),
    path("dashboard/payroll/generate/", generate_payroll, name="generate_payroll"),
    path(
        "dashboard/payroll/<int:payroll_id>/approve/",
        approve_payroll,
        name="approve_payroll",
    ),
    path(
        "dashboard/payroll/<int:payroll_id>/paid/",
        mark_payroll_paid,
        name="mark_payroll_paid",
    ),
    path(
        "dashboard/payroll/<int:payroll_id>/download/",
        download_payslip_pdf,
        name="download_payslip_pdf",
    ),
    path("employee/payslips/", employee_payslips, name="employee_payslips"),
]
=======
    payroll_list,
    generate_payroll,
    approve_payroll,
    mark_payroll_paid,
    download_payslip_pdf,
    employee_payslips,
)


urlpatterns = [
    path("dashboard/payroll/", payroll_list, name="payroll_list"),

    path(
        "dashboard/payroll/generate/",
        generate_payroll,
        name="generate_payroll"
    ),

    path(
        "dashboard/payroll/<int:payroll_id>/approve/",
        approve_payroll,
        name="approve_payroll"
    ),

    path(
        "dashboard/payroll/<int:payroll_id>/paid/",
        mark_payroll_paid,
        name="mark_payroll_paid"
    ),

    path(
        "dashboard/payroll/<int:payroll_id>/download/",
        download_payslip_pdf,
        name="download_payslip_pdf"
    ),
    path(
    "employee/payslips/",
    employee_payslips,
    name="employee_payslips"
),
]
>>>>>>> 5815f15 (Initial project commit)
