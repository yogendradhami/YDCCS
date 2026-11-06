from django.urls import path
from . import views
from .views import (
    dashboard_induction_list,
    dashboard_induction_setup,
    dashboard_induction_detail,
    dashboard_induction_cancel,
    dashboard_induction_publish,
    induction_module_review,
    induction_supervisor_verification,
    induction_training_export,

    employee_induction,
    employee_induction_module,
    employee_induction_complete,

    induction_completion_pdf,
    induction_start_record_pdf,
)


urlpatterns = [

    # =====================================================
    # ADMIN / HR
    # =====================================================

    path(
        "dashboard/induction/",
        dashboard_induction_list,
        name="induction_dashboard",
    ),
    path(
        "dashboard/induction/publish/",
        dashboard_induction_publish,
        name="induction_publish",
    ),
    path(
        "dashboard/induction/<int:induction_id>/publish/",
        dashboard_induction_publish,
        name="induction_publish_for_employee",
    ),

    path(
        "dashboard/employee-training/",
        dashboard_induction_list,
        name="employee_training_dashboard",
    ),

    path(
        "dashboard/induction/<int:induction_id>/setup/",
        dashboard_induction_setup,
        name="induction_setup",
    ),

    path(
        "dashboard/induction/<int:induction_id>/",
        dashboard_induction_detail,
        name="induction_detail",
    ),

    path(
        "dashboard/induction/<int:induction_id>/cancel/",
        dashboard_induction_cancel,
        name="induction_cancel",
    ),
    path(
        "dashboard/induction/<int:induction_id>/module/<int:module_id>/completion/<int:completion_id>/review/",
        induction_module_review,
        name="induction_module_review",
    ),
    path(
        "dashboard/induction/<int:induction_id>/module/<int:module_id>/verification/",
        induction_supervisor_verification,
        name="induction_supervisor_verification",
    ),
    path(
        "dashboard/induction/<int:induction_id>/training-records.csv",
        induction_training_export,
        name="induction_training_export",
    ),

    # =====================================================
    # EMPLOYEE
    # =====================================================

    path(
        "employee/induction/",
        employee_induction,
        name="employee_induction",
    ),

    path(
        "employee/induction/module/<int:module_id>/",
        employee_induction_module,
        name="employee_induction_module",
    ),

    path(
        "employee/induction/complete/",
        employee_induction_complete,
        name="employee_induction_complete",
    ),

    # =====================================================
    # PDF
    # =====================================================

    path(
        "dashboard/induction/<int:induction_id>/completion-pdf/",
        induction_completion_pdf,
        name="induction_completion_pdf",
    ),

    path(
        "dashboard/induction/<int:induction_id>/start-record-pdf/",
        induction_start_record_pdf,
        name="induction_start_record_pdf",
    ),

    path(
        "employee/induction/completion-pdf/",
        induction_completion_pdf,
        name="employee_induction_completion_pdf",
    ),

    path(
        "employee/induction/start-record-pdf/",
        induction_start_record_pdf,
        name="employee_induction_start_record_pdf",
    ),

    path(
        "employee/onboarding/",
        views.employee_onboarding,
        name="employee_onboarding",
    ),

    path(
        "employee/onboarding/upload/<int:requirement_id>/",
        views.employee_onboarding_upload,
        name="employee_onboarding_upload",
    ),

    path(
        "employee/onboarding/document/<int:document_id>/download/",
        views.onboarding_document_download,
        name="onboarding_document_download",
    ),

    path(
        "dashboard/onboarding/",
        views.onboarding_dashboard,
        name="onboarding_dashboard",
    ),

    path(
        "dashboard/onboarding/<int:employee_id>/",
        views.onboarding_detail,
        name="onboarding_detail",
    ),

    path(
        "dashboard/onboarding/document/<int:document_id>/review/",
        views.onboarding_document_review,
        name="onboarding_document_review",
    ),

    path(
        "dashboard/onboarding/<int:employee_id>/status/<str:status>/",
        views.onboarding_set_status,
        name="onboarding_set_status",
    ),
]