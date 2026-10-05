from io import BytesIO

import cloudinary
import requests
from cloudinary.utils import cloudinary_url

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import CompanyDocumentForm
from .models import CompanyDocument, CompanyDocumentAudit


# ==========================================================
# ACCESS CONTROL
# ==========================================================

def can_manage_documents(user):
    """
    Company document management is restricted to staff/superusers.
    """

    return bool(
        user.is_authenticated
        and (user.is_superuser or user.is_staff)
    )


def can_access_document(user, document):
    """
    Determine whether the current user can access a document.

    Sensitive documents require either:
    - superuser access
    - explicit download_sensitive_companydocument permission
    """

    if not can_manage_documents(user):
        return False

    if document.is_sensitive:
        return bool(
            user.is_superuser
            or user.has_perm(
                "company_documents.download_sensitive_companydocument"
            )
        )

    return True


# ==========================================================
# AUDIT LOGGING
# ==========================================================

def create_audit(document, user, action, metadata=None):
    """
    Create a company document audit record.

    Kept intentionally compatible with the current
    CompanyDocumentAudit model.
    """

    return CompanyDocumentAudit.objects.create(
        document=document,
        user=user,
        action=action,
        metadata=metadata or {},
    )


# ==========================================================
# CLOUDINARY RAW DOCUMENT HELPERS
# ==========================================================

def upload_raw_document(uploaded_file):
    """
    Upload a document directly to Cloudinary as a RAW resource.

    This intentionally bypasses the FileField storage backend
    because company documents can contain formats such as:

    PDF
    DOC
    DOCX
    XLS
    XLSX
    PPT
    PPTX
    CSV
    TXT
    ZIP
    JPG
    PNG
    WEBP
    etc.
    """

    folder = timezone.now().strftime(
        "company_documents/%Y/%m"
    )

    result = cloudinary.uploader.upload(
        uploaded_file,
        resource_type="raw",
        folder=folder,
        use_filename=True,
        unique_filename=True,
        overwrite=False,
    )

    public_id = result.get("public_id")

    if not public_id:
        raise ValueError(
            "Cloudinary did not return a document public ID."
        )

    return public_id


def delete_raw_document(file_name):
    """
    Delete a RAW document from Cloudinary.

    Fail silently so that deleting a database record is not
    blocked by a Cloudinary cleanup failure.
    """

    if not file_name:
        return

    try:
        cloudinary.uploader.destroy(
            file_name,
            resource_type="raw",
            type="upload",
            invalidate=True,
        )
    except Exception:
        pass


def get_raw_document_url(file_name):
    """
    Generate a secure RAW Cloudinary URL.
    """

    if not file_name:
        raise ValueError("Document does not have a stored file.")

    raw_url, _ = cloudinary_url(
        file_name,
        resource_type="raw",
        type="upload",
        secure=True,
    )

    return raw_url


def download_raw_document(file_name):
    """
    Download RAW document bytes from Cloudinary.
    """

    raw_url = get_raw_document_url(file_name)

    response = requests.get(
        raw_url,
        timeout=60,
    )

    response.raise_for_status()

    return response.content


# ==========================================================
# DOCUMENT LIST
# ==========================================================

@login_required
def document_list(request):
    """
    Company document centre.
    """

    if not can_manage_documents(request.user):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    documents = (
        CompanyDocument.objects
        .select_related(
            "employee",
            "customer",
            "vehicle",
            "supplier",
            "contract",
            "uploaded_by",
        )
        .all()
    )

    # ------------------------------------------------------
    # SEARCH
    # ------------------------------------------------------

    query = request.GET.get("q", "").strip()

    if query:
        documents = documents.filter(
            Q(name__icontains=query)
            | Q(document_type__icontains=query)
            | Q(document_reference__icontains=query)
            | Q(description__icontains=query)
            | Q(original_filename__icontains=query)
        )

    # ------------------------------------------------------
    # CATEGORY
    # ------------------------------------------------------

    category = request.GET.get("category", "").strip()

    if category:
        documents = documents.filter(
            category=category
        )

    # ------------------------------------------------------
    # STATUS
    # ------------------------------------------------------

    status = request.GET.get("status", "").strip()

    if status:
        documents = documents.filter(
            status=status
        )

    # ------------------------------------------------------
    # EXPIRY FILTER
    # ------------------------------------------------------

    expiry = request.GET.get("expiry", "").strip()

    today = timezone.localdate()

    if expiry == "expired":
        documents = documents.filter(
            expiry_date__lt=today
        )

    elif expiry == "30":
        documents = documents.filter(
            expiry_date__gte=today,
            expiry_date__lte=today + timezone.timedelta(days=30),
        )

    elif expiry == "60":
        documents = documents.filter(
            expiry_date__gte=today,
            expiry_date__lte=today + timezone.timedelta(days=60),
        )

    elif expiry == "90":
        documents = documents.filter(
            expiry_date__gte=today,
            expiry_date__lte=today + timezone.timedelta(days=90),
        )

    # ------------------------------------------------------
    # ORDERING
    # ------------------------------------------------------

    documents = documents.order_by("-uploaded_at")

    # ------------------------------------------------------
    # PAGINATION
    # ------------------------------------------------------

    paginator = Paginator(
        documents,
        15,
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    # ------------------------------------------------------
    # KPI STATISTICS
    # ------------------------------------------------------

    all_documents = CompanyDocument.objects.all()

    total_documents = all_documents.count()

    active_documents = all_documents.filter(
        status=CompanyDocument.Status.ACTIVE
    ).count()

    archived_documents = all_documents.filter(
        status=CompanyDocument.Status.ARCHIVED
    ).count()

    expired_documents = all_documents.filter(
        expiry_date__lt=today,
        status=CompanyDocument.Status.ACTIVE,
    ).count()

    expiring_30_days = all_documents.filter(
        expiry_date__gte=today,
        expiry_date__lte=today + timezone.timedelta(days=30),
        status=CompanyDocument.Status.ACTIVE,
    ).count()

    context = {
        "documents": page_obj,
        "page_obj": page_obj,
        "paginator": paginator,

        "query": query,
        "selected_category": category,
        "selected_status": status,
        "selected_expiry": expiry,

        "categories": CompanyDocument.Category.choices,
        "statuses": CompanyDocument.Status.choices,

        "total_documents": total_documents,
        "active_documents": active_documents,
        "archived_documents": archived_documents,
        "expired_documents": expired_documents,
        "expiring_30_days": expiring_30_days,
    }

    return render(
        request,
        "dashboard/company_documents/list.html",
        context,
    )


# ==========================================================
# UPLOAD
# ==========================================================

@login_required
@require_http_methods(["GET", "POST"])
def document_upload(request):
    """
    Upload a new company document.
    """

    if not can_manage_documents(request.user):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    if request.method == "POST":

        form = CompanyDocumentForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            uploaded_file = form.cleaned_data.get(
                "file"
            )

            if not uploaded_file:
                form.add_error(
                    "file",
                    "Please select a document to upload.",
                )
            else:

                max_size = getattr(
                    settings,
                    "COMPANY_DOCUMENT_MAX_SIZE",
                    50 * 1024 * 1024,
                )

                if uploaded_file.size > max_size:
                    form.add_error(
                        "file",
                        "The selected file is larger than "
                        "the maximum allowed size of 50 MB.",
                    )

                else:

                    cloudinary_public_id = None

                    try:
                        # Upload directly to Cloudinary RAW.
                        cloudinary_public_id = (
                            upload_raw_document(
                                uploaded_file
                            )
                        )

                        document = form.save(
                            commit=False
                        )

                        document.file.name = (
                            cloudinary_public_id
                        )

                        document.file._committed = True

                        document.uploaded_by = (
                            request.user
                        )

                        document.original_filename = (
                            uploaded_file.name
                        )

                        document.file_size = (
                            uploaded_file.size
                        )

                        document.mime_type = (
                            uploaded_file.content_type
                            or "application/octet-stream"
                        )

                        document.version = (
                            document.version or 1
                        )

                        document.save()

                        create_audit(
                            document=document,
                            user=request.user,
                            action="uploaded",
                        )

                        messages.success(
                            request,
                            f'"{document.name}" was uploaded successfully.',
                        )

                        return redirect(
                            "company_documents:detail",
                            pk=document.pk,
                        )

                    except Exception as exc:

                        if cloudinary_public_id:
                            delete_raw_document(
                                cloudinary_public_id
                            )

                        form.add_error(
                            "file",
                            (
                                "The document could not be uploaded. "
                                f"Cloudinary returned: {exc}"
                            ),
                        )

    else:

        form = CompanyDocumentForm()

    context = {
        "form": form,
        "page_title": "Upload document",
        "page_subtitle": (
            "Securely add a document to the company document centre."
        ),
        "is_edit": False,
        "document": None,
    }

    return render(
        request,
        "dashboard/company_documents/form.html",
        context,
    )


# ==========================================================
# EDIT / REPLACE DOCUMENT
# ==========================================================


@login_required
@require_http_methods(["GET", "POST"])
def document_edit(request, pk):
    """
    Edit an existing company document.

    Important:
    - Editing metadata does NOT require a new file.
    - Cloudinary is only contacted when an actual replacement
      file has been uploaded.
    - The existing Cloudinary file is preserved when no file
      is selected.
    """

    if not can_manage_documents(request.user):
        raise Http404

    document = get_object_or_404(
        CompanyDocument,
        pk=pk,
    )

    if request.method == "POST":

        # ---------------------------------------------------------
        # IMPORTANT
        #
        # Check the actual FILES dictionary instead of relying
        # only on form.cleaned_data.
        #
        # If the user did not select a replacement file,
        # this will be None.
        # ---------------------------------------------------------

        replacement_file = request.FILES.get("file")

        form = CompanyDocumentForm(
            request.POST,
            request.FILES,
            instance=document,
        )

        if form.is_valid():

            try:
                # =================================================
                # CASE 1
                # No replacement file
                #
                # Only update database metadata.
                # DO NOT contact Cloudinary.
                # =================================================

                if replacement_file is None:
                    updated_document = form.save(
                        commit=False
                    )

                    # Preserve the existing Cloudinary file.
                    updated_document.file = document.file

                    # Preserve original file metadata.
                    updated_document.original_filename = (
                        document.original_filename
                    )

                    updated_document.file_size = (
                        document.file_size
                    )

                    updated_document.mime_type = (
                        document.mime_type
                    )

                    updated_document.version = (
                        document.version
                    )

                    updated_document.uploaded_by = (
                        document.uploaded_by
                    )

                    updated_document.uploaded_at = (
                        document.uploaded_at
                    )

                    updated_document.save()

                    create_audit(
                        document=updated_document,
                        user=request.user,
                        action="updated",
                    )

                    messages.success(
                        request,
                        "Document updated successfully.",
                    )

                    return redirect(
                        "company_documents:detail",
                        pk=updated_document.pk,
                    )

                # =================================================
                # CASE 2
                # Replacement file was actually uploaded
                # =================================================

                uploaded_size = getattr(
                    replacement_file,
                    "size",
                    None,
                )

                # Safety check.
                if uploaded_size is None:
                    messages.error(
                        request,
                        "The replacement file could not be "
                        "read. Please select the file again.",
                    )

                    return render(
                        request,
                        "dashboard/company_documents/form.html",
                        {
                            "form": form,
                            "document": document,
                            "is_edit": True,
                        },
                    )

                # -------------------------------------------------
                # Maximum file size
                # -------------------------------------------------

                max_size = getattr(
                    settings,
                    "COMPANY_DOCUMENT_MAX_SIZE",
                    50 * 1024 * 1024,
                )

                if uploaded_size > max_size:
                    messages.error(
                        request,
                        "The selected file is larger than "
                        "the maximum allowed size of 50 MB.",
                    )

                    return render(
                        request,
                        "dashboard/company_documents/form.html",
                        {
                            "form": form,
                            "document": document,
                            "is_edit": True,
                        },
                    )

                # =================================================
                # Upload replacement to Cloudinary
                # =================================================

                upload_result = upload_raw_document(
                    replacement_file
                )

                new_public_id = upload_result.get(
                    "public_id"
                )

                if not new_public_id:
                    raise ValueError(
                        "Cloudinary did not return a public ID "
                        "for the replacement file."
                    )

                # -------------------------------------------------
                # Keep reference to old Cloudinary file
                # -------------------------------------------------

                old_file_name = None

                if document.file:
                    old_file_name = document.file.name

                # -------------------------------------------------
                # Update database object
                # -------------------------------------------------

                updated_document = form.save(
                    commit=False
                )

                updated_document.file.name = new_public_id
                updated_document._committed = True

                updated_document.original_filename = (
                    replacement_file.name
                )

                updated_document.file_size = (
                    uploaded_size
                )

                updated_document.mime_type = (
                    getattr(
                        replacement_file,
                        "content_type",
                        None,
                    )
                    or "application/octet-stream"
                )

                updated_document.version = (
                    (document.version or 1) + 1
                )

                updated_document.previous_version = (
                    document
                )

                updated_document.save()

                # =================================================
                # Audit
                # =================================================

                create_audit(
                    document=updated_document,
                    user=request.user,
                    action="version_replaced",
                )

                # =================================================
                # Delete old Cloudinary file
                #
                # Only after the new file and database record
                # have successfully been created.
                # =================================================

                if old_file_name:
                    try:
                        delete_raw_document(
                            old_file_name
                        )
                    except Exception:
                        # Do not make a successful document
                        # update fail just because cleanup
                        # of the old Cloudinary resource failed.
                        pass

                messages.success(
                    request,
                    "Document updated successfully and the "
                    "file was replaced.",
                )

                return redirect(
                    "company_documents:detail",
                    pk=updated_document.pk,
                )

            except Exception as exc:
                messages.error(
                    request,
                    f"The document could not be updated. "
                    f"Cloudinary returned: {exc}",
                )

        # ---------------------------------------------------------
        # Form validation failed
        # ---------------------------------------------------------

        return render(
            request,
            "dashboard/company_documents/form.html",
            {
                "form": form,
                "document": document,
                "is_edit": True,
            },
        )

    # =============================================================
    # GET
    # =============================================================

    form = CompanyDocumentForm(
        instance=document
    )

    return render(
        request,
        "dashboard/company_documents/form.html",
        {
            "form": form,
            "document": document,
            "is_edit": True,
        },
    )

# ==========================================================
# DETAIL
# ==========================================================

@login_required
def document_detail(request, pk):
    """
    Display document details and audit history.
    """

    if not can_manage_documents(request.user):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    document = get_object_or_404(
        CompanyDocument.objects.select_related(
            "employee",
            "customer",
            "vehicle",
            "supplier",
            "contract",
            "uploaded_by",
        ),
        pk=pk,
    )

    if not can_access_document(
        request.user,
        document,
    ):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    create_audit(
        document=document,
        user=request.user,
        action="viewed",
    )

    audit_events = (
        document.audit_events
        .select_related("user")
        .order_by("-created_at")[:50]
    )

    context = {
        "document": document,
        "audit_events": audit_events,
        "audits": audit_events,
    }

    return render(
        request,
        "dashboard/company_documents/detail.html",
        context,
    )


# ==========================================================
# DOWNLOAD
# ==========================================================

@login_required
def document_download(request, pk):
    """
    Securely download a company document from Cloudinary RAW.
    """

    if not can_manage_documents(request.user):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    document = get_object_or_404(
        CompanyDocument,
        pk=pk,
    )

    if not can_access_document(
        request.user,
        document,
    ):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    if not document.file:
        raise Http404(
            "This document does not have a stored file."
        )

    try:

        file_content = download_raw_document(
            document.file.name
        )

    except requests.RequestException as exc:

        raise Http404(
            f"Unable to retrieve the document: {exc}"
        )

    except Exception as exc:

        raise Http404(
            f"Unable to retrieve the document: {exc}"
        )

    create_audit(
        document=document,
        user=request.user,
        action="downloaded",
    )

    filename = (
        document.original_filename
        or document.name
        or "document"
    )

    response = FileResponse(
        BytesIO(file_content),
        as_attachment=True,
        filename=filename,
    )

    if document.mime_type:
        response["Content-Type"] = document.mime_type

    response["Content-Length"] = str(
        len(file_content)
    )

    return response


# ==========================================================
# EMAIL DOCUMENT
# ==========================================================

@login_required
@require_http_methods(["GET", "POST"])
def document_email(request, pk):
    """
    Email a company document as an attachment.
    """

    if not can_manage_documents(request.user):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    document = get_object_or_404(
        CompanyDocument,
        pk=pk,
    )

    if not can_access_document(
        request.user,
        document,
    ):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    if request.method == "POST":

        recipient = (
            request.POST.get(
                "recipient",
                "",
            )
            .strip()
        )

        subject = (
            request.POST.get(
                "subject",
                "",
            )
            .strip()
        )

        message = (
            request.POST.get(
                "message",
                "",
            )
            .strip()
        )

        if not recipient:

            messages.error(
                request,
                "Please enter a recipient email address.",
            )

        elif not subject:

            messages.error(
                request,
                "Please enter an email subject.",
            )

        else:

            try:

                # --------------------------------------------------
                # RETRIEVE RAW FILE FROM CLOUDINARY
                # --------------------------------------------------

                file_content = download_raw_document(
                    document.file.name
                )

                attachment_name = (
                    document.original_filename
                    or document.name
                    or "document"
                )

                mime_type = (
                    document.mime_type
                    or "application/octet-stream"
                )

                email = EmailMessage(
                    subject=subject,
                    body=message,
                    from_email=getattr(
                        settings,
                        "DEFAULT_FROM_EMAIL",
                        None,
                    ),
                    to=[recipient],
                )

                email.attach(
                    attachment_name,
                    file_content,
                    mime_type,
                )

                email.send(
                    fail_silently=False
                )

                create_audit(
                    document=document,
                    user=request.user,
                    action="emailed",
                )

                messages.success(
                    request,
                    f'"{document.name}" was emailed successfully to {recipient}.',
                )

                return redirect(
                    "company_documents:detail",
                    pk=document.pk,
                )

            except requests.RequestException as exc:

                messages.error(
                    request,
                    (
                        "Unable to retrieve the document for email: "
                        f"{exc}"
                    ),
                )

            except Exception as exc:

                messages.error(
                    request,
                    (
                        "Unable to send the document email: "
                        f"{exc}"
                    ),
                )

    context = {
        "document": document,
    }

    return render(
        request,
        "dashboard/company_documents/email.html",
        context,
    )


# ==========================================================
# ARCHIVE
# ==========================================================

@login_required
@require_http_methods(["POST"])
def document_archive(request, pk):
    """
    Archive a company document.
    """

    if not can_manage_documents(request.user):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    document = get_object_or_404(
        CompanyDocument,
        pk=pk,
    )

    if not can_access_document(
        request.user,
        document,
    ):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    document.status = (
        CompanyDocument.Status.ARCHIVED
    )

    document.archived_at = timezone.now()

    document.save(
        update_fields=[
            "status",
            "archived_at",
            "updated_at",
        ]
        if hasattr(
            CompanyDocument,
            "updated_at",
        )
        else [
            "status",
            "archived_at",
        ]
    )

    create_audit(
        document=document,
        user=request.user,
        action="archived",
    )

    messages.success(
        request,
        f'"{document.name}" has been archived.',
    )

    return redirect(
        "company_documents:detail",
        pk=document.pk,
    )


# ==========================================================
# DELETE
# ==========================================================

@login_required
@require_http_methods(["POST"])
def document_delete(request, pk):
    """
    Permanently delete a document and attempt to remove
    its Cloudinary RAW file.
    """

    if not can_manage_documents(request.user):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    document = get_object_or_404(
        CompanyDocument,
        pk=pk,
    )

    if not can_access_document(
        request.user,
        document,
    ):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    document_name = document.name

    file_name = (
        document.file.name
        if document.file
        else None
    )

    # Delete the Cloudinary RAW file first.
    delete_raw_document(
        file_name
    )

    # Delete database record.
    document.delete()

    messages.success(
        request,
        f'"{document_name}" was permanently deleted.',
    )

    return redirect(
        "company_documents:list"
    )