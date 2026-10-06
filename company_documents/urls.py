from django.urls import path

from . import views


app_name = "company_documents"


urlpatterns = [

    # ------------------------------------------------------
    # DOCUMENT CENTRE
    # ------------------------------------------------------

    path(
        "",
        views.document_list,
        name="list",
    ),

    path(
        "compliance/",
        views.compliance_attention,
        name="compliance",
    ),

    path(
        "compliance/overview/",
        views.compliance_overview,
        name="compliance_overview",
    ),

    path(
        "compliance/overview/",
        views.compliance_overview,
        name="compliance_overview",
    ),

    path(
        "compliance/employees/",
        views.employee_compliance_matrix,
        name="employee_compliance_matrix",
    ),

    path(
        "compliance/employee/<int:employee_id>/",
        views.employee_compliance_profile,
        name="employee_compliance",
    ),

    path(
        "compliance/renewals/",
        views.compliance_renewals,
        name="compliance_renewals",
    ),

    path(
        "compliance/notifications/",
        views.compliance_notifications,
        name="compliance_notifications",
    ),



    # ------------------------------------------------------
    # CREATE
    # ------------------------------------------------------

    path(
        "upload/",
        views.document_upload,
        name="upload",
    ),

    # ------------------------------------------------------
    # DETAIL
    # ------------------------------------------------------

    path(
        "<int:pk>/",
        views.document_detail,
        name="detail",
    ),

    # ------------------------------------------------------
    # EDIT
    # ------------------------------------------------------

    path(
        "<int:pk>/edit/",
        views.document_edit,
        name="edit",
    ),

    # ------------------------------------------------------
    # DOWNLOAD
    # ------------------------------------------------------

    path(
        "<int:pk>/download/",
        views.document_download,
        name="download",
    ),

    # ------------------------------------------------------
    # EMAIL
    # ------------------------------------------------------

    path(
        "<int:pk>/email/",
        views.document_email,
        name="email",
    ),

    # ------------------------------------------------------
    # ARCHIVE
    # ------------------------------------------------------

    path(
        "<int:pk>/archive/",
        views.document_archive,
        name="archive",
    ),

    # ------------------------------------------------------
    # DELETE
    # ------------------------------------------------------

    path(
        "<int:pk>/delete/",
        views.document_delete,
        name="delete",
    ),

    path(
        "bulk-import/",
        views.bulk_import_list,
        name="bulk_import_list",
    ),

    path(
        "bulk-import/upload/",
        views.bulk_import_upload,
        name="bulk_import_upload",
    ),

    path(
        "bulk-import/<int:pk>/",
        views.bulk_import_review,
        name="bulk_import_review",
    ),

    path(
        "bulk-import/<int:pk>/analyse/",
        views.bulk_import_analyse,
        name="bulk_import_analyse",
    ),

    path(
        "bulk-import/<int:pk>/approve/",
        views.bulk_import_approve,
        name="bulk_import_approve",
    ),

    path(
        "bulk-import/<int:pk>/import/",
        views.bulk_import_import,
        name="bulk_import_import",
    ),

    path(
        "bulk-import/item/<int:pk>/edit/",
        views.bulk_import_item_edit,
        name="bulk_import_item_edit",
    ),
]