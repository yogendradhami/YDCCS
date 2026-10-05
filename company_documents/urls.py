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
]