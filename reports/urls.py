from django.urls import path

from .views import (
    cleaning_report_detail,
    download_cleaning_report_pdf,
    email_cleaning_report,
    report_list,
)

urlpatterns = [
    path("dashboard/reports/", report_list, name="report_list"),
    path(
        "reports/booking/<int:booking_id>/",
        cleaning_report_detail,
        name="cleaning_report_detail",
    ),
    path(
        "reports/booking/<int:booking_id>/download/",
        download_cleaning_report_pdf,
        name="download_cleaning_report_pdf",
    ),
    path(
        "reports/booking/<int:booking_id>/email/",
        email_cleaning_report,
        name="email_cleaning_report",
    ),
]
