# ==========================================================
# File: payroll/urls.py
# Purpose:
# Payroll URL routes.
# ==========================================================

from django.urls import path

from .views import (
    approve_payroll,
    delete_payroll,
    download_payslip_pdf,
    edit_payroll,
    employee_payslips,
    generate_payroll,
    mark_payroll_paid,
    payroll_detail,
    payroll_list,
)

urlpatterns = [
    path("dashboard/payroll/", payroll_list, name="payroll_list"),
    path("dashboard/payroll/generate/", generate_payroll, name="generate_payroll"),
    path(
        "dashboard/payroll/<int:payroll_id>/",
        payroll_detail,
        name="payroll_detail",
    ),
    path(
        "dashboard/payroll/<int:payroll_id>/edit/",
        edit_payroll,
        name="edit_payroll",
    ),
    path(
        "dashboard/payroll/<int:payroll_id>/delete/",
        delete_payroll,
        name="delete_payroll",
    ),
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
    path(
        "employee/payslips/<int:payroll_id>/download/",
        download_payslip_pdf,
        name="employee_download_payslip_pdf",
    ),
    path("employee/payslips/", employee_payslips, name="employee_payslips"),
]
