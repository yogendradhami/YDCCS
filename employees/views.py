# ==========================================================
# File: employees/views.py
# Purpose:
# Employee Portal
# - Login
# - Dashboard
# - Jobs
# - Job Details
# - Upload Photos
# - Profile Management
# ==========================================================

import secrets
import base64
import hashlib
import hmac
import json
import logging
import time
import uuid
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import cloudinary
from cloudinary import api as cloudinary_api
from cloudinary.utils import api_sign_request
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
from django.db import DatabaseError, transaction
from django.http import HttpResponse, JsonResponse
from google_auth_oauthlib.flow import Flow

from .models import (
    Employee,
    EmployeeGoogleAccount,
    PropertyDamageImage,
    PropertyDamageReport,
)
from .decorators import employee_required
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from bookings.forms import JobPhotoForm
from bookings.models import Booking, JobPhoto

from .forms import (
    EmployeeJobStatusForm,
    EmployeeLoginForm,
    PropertyDamageReportForm,
)
from .models import Employee
from .profile_forms import (
    EmployeePasswordForm,
    EmployeeProfileForm,
)
from notifications.utils import notify_admins, temporary_instance_flags

EMPLOYEE_GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
]

MAX_JOB_PHOTOS_PER_UPLOAD = 12
MAX_JOB_PHOTO_SIZE = 25 * 1024 * 1024
MAX_SIGNATURE_SIZE = 5 * 1024 * 1024
JOB_PHOTO_UPLOAD_SESSION_KEY = "pending_job_photo_uploads"
ALLOWED_JOB_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
ALLOWED_JOB_PHOTO_FORMATS = {"jpg", "jpeg", "png", "webp", "heic", "heif"}
logger = logging.getLogger(__name__)
ALLOWED_JOB_PHOTO_FORMATS = {"jpg", "jpeg", "png", "webp", "heic", "heif"}


def _lock_employee_booking_mutations(view):
    @wraps(view)
    def wrapped(request, booking_id, *args, **kwargs):
        if request.method != "POST":
            return view(request, booking_id, *args, **kwargs)

        employee = get_object_or_404(Employee, user=request.user)
        get_object_or_404(
            Booking,
            pk=booking_id,
            assigned_employee=employee,
        )
        from rosters.services import (
            RosterSyncLockError,
            booking_roster_sync_lock,
        )

        try:
            with booking_roster_sync_lock(booking_id):
                Booking.objects.select_for_update().get(
                    pk=booking_id,
                    assigned_employee=employee,
                )
                return view(request, booking_id, *args, **kwargs)
        except (DatabaseError, RosterSyncLockError):
            logger.exception(
                "Could not safely serialize employee update for booking %s.",
                booking_id,
            )
            messages.error(
                request,
                "The job could not be safely updated right now. Please retry.",
            )
            return redirect("employee_job_detail", booking_id=booking_id)

    return wrapped


def _destroy_job_photo_assets(public_ids):
    """Best-effort cleanup for assets created by one signed upload batch."""
    public_ids = list(dict.fromkeys(public_ids))
    if not public_ids:
        return

    cloudinary.config(
        cloud_name=settings.CLOUDINARY_STORAGE["CLOUD_NAME"],
        api_key=settings.CLOUDINARY_STORAGE["API_KEY"],
        api_secret=settings.CLOUDINARY_STORAGE["API_SECRET"],
    )

    def destroy(public_id):
        try:
            cloudinary.uploader.destroy(
                public_id,
                resource_type="image",
                invalidate=True,
            )
        except Exception:
            logger.exception("Could not clean up job photo asset %s", public_id)

    with ThreadPoolExecutor(max_workers=min(3, len(public_ids))) as executor:
        list(executor.map(destroy, public_ids))


def _verify_job_photo_uploads(supplied_uploads, expected_ids, booking_id):
    """Verify Cloudinary's signed receipt and authoritative stored metadata."""
    if (
        not isinstance(supplied_uploads, list)
        or not supplied_uploads
        or len(supplied_uploads) > MAX_JOB_PHOTOS_PER_UPLOAD
        or len(supplied_uploads) != len(expected_ids)
    ):
        raise ValueError("The photo upload batch is incomplete.")

    secret = settings.CLOUDINARY_STORAGE["API_SECRET"]
    response_ids = []
    response_versions = {}
    for result in supplied_uploads:
        if not isinstance(result, dict):
            raise ValueError("Cloudinary returned an invalid photo receipt.")

        public_id = result.get("public_id", "")
        signature = result.get("signature", "")
        try:
            version = int(result.get("version"))
        except (TypeError, ValueError):
            raise ValueError("Cloudinary returned an invalid photo version.")

        if (
            not isinstance(public_id, str)
            or not public_id.startswith(f"job_photos/{booking_id}/")
            or version <= 0
        ):
            raise ValueError("The photo does not belong to this job upload.")

        expected_signature = api_sign_request(
            {"public_id": public_id, "version": version},
            secret,
            signature_version=1,
        )
        if (
            not isinstance(signature, str)
            or not signature.isascii()
            or not hmac.compare_digest(signature, expected_signature)
        ):
            raise ValueError("Cloudinary's photo signature could not be verified.")

        response_ids.append(public_id)
        response_versions[public_id] = version

    if len(set(response_ids)) != len(expected_ids) or set(response_ids) != set(expected_ids):
        raise ValueError("The uploaded photos do not match the signed batch.")

    # Cloudinary response signatures cover public_id and version only. Query
    # the authenticated Admin API for the actual stored format and byte count.
    resources_response = cloudinary_api.resources_by_ids(
        list(expected_ids),
        resource_type="image",
        type="upload",
    )
    resources = resources_response.get("resources", [])
    resources_by_id = {
        resource.get("public_id"): resource
        for resource in resources
        if isinstance(resource, dict)
    }
    if set(resources_by_id) != set(expected_ids):
        raise ValueError("Cloudinary could not confirm every uploaded photo.")

    for public_id, resource in resources_by_id.items():
        try:
            actual_bytes = int(resource.get("bytes", 0))
            actual_version = int(resource.get("version", 0))
        except (TypeError, ValueError):
            raise ValueError("Cloudinary returned incomplete photo metadata.")
        actual_format = str(resource.get("format", "")).lower()
        if (
            resource.get("resource_type") != "image"
            or actual_format not in ALLOWED_JOB_PHOTO_FORMATS
            or not 0 < actual_bytes <= MAX_JOB_PHOTO_SIZE
            or actual_version != response_versions[public_id]
        ):
            raise ValueError("A photo has an unsupported type or exceeds 25 MB.")

    return [{"public_id": public_id} for public_id in response_ids]


def _store_job_photo_files(images, booking_id):
    """Store fallback multipart uploads with bounded Cloudinary concurrency."""
    files = [image for image in images if isinstance(image, UploadedFile)]
    if not files:
        return []

    def store(image):
        suffix = Path(image.name).suffix.lower() or ".jpg"
        image.seek(0)
        return default_storage.save(
            f"job_photos/{booking_id}/{uuid.uuid4().hex}{suffix}",
            image,
        )

    stored_names = [None] * len(files)
    failures = []
    with ThreadPoolExecutor(max_workers=min(3, len(files))) as executor:
        futures = {
            executor.submit(store, image): index
            for index, image in enumerate(files)
        }
        for future in as_completed(futures):
            try:
                stored_names[futures[future]] = future.result()
            except Exception as exc:
                failures.append(exc)

    if failures:
        for name in filter(None, stored_names):
            try:
                default_storage.delete(name)
            except Exception:
                logger.exception("Could not clean up fallback job photo %s", name)
        raise failures[0]

    return stored_names


def get_employee_google_flow():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [
                    settings.GOOGLE_EMPLOYEE_REDIRECT_URI,
                ],
            }
        },
        scopes=EMPLOYEE_GOOGLE_SCOPES,
    )

    flow.redirect_uri = settings.GOOGLE_EMPLOYEE_REDIRECT_URI

    return flow


from .profile_forms import (
    EmployeePasswordForm,
    EmployeeProfileForm,
)

EMPLOYEE_GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
]


def get_employee_google_flow():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [
                    settings.GOOGLE_EMPLOYEE_REDIRECT_URI,
                ],
            }
        },
        scopes=EMPLOYEE_GOOGLE_SCOPES,
    )

    flow.redirect_uri = settings.GOOGLE_EMPLOYEE_REDIRECT_URI

    return flow


@employee_required
def employee_google_connect(request):
    employee = get_object_or_404(Employee, user=request.user)

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [
                    settings.GOOGLE_EMPLOYEE_REDIRECT_URI,
                ],
            }
        },
        scopes=EMPLOYEE_GOOGLE_SCOPES,
    )

    flow.redirect_uri = settings.GOOGLE_EMPLOYEE_REDIRECT_URI

    # ---------------------------------------------------------
    # PKCE
    # ---------------------------------------------------------

    code_verifier = secrets.token_urlsafe(64)

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
        code_challenge=base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode("utf-8")).digest()
        ).decode("utf-8").rstrip("="),
        code_challenge_method="S256",
    )

    # ---------------------------------------------------------
    # Save OAuth session data
    # ---------------------------------------------------------

    request.session["employee_google_oauth_state"] = state
    request.session["employee_google_code_verifier"] = code_verifier
    request.session["employee_google_id"] = employee.id

    request.session.save()

    return redirect(authorization_url)


@employee_required
def employee_google_callback(request):

    state = request.session.get("employee_google_oauth_state")
    employee_id = request.session.get("employee_google_id")
    code_verifier = request.session.get("employee_google_code_verifier")

    if not state or not employee_id or not code_verifier:
        return HttpResponse(
            """
            <h2>Employee Google OAuth session expired</h2>
            <p>Please start the Google Calendar connection again.</p>
            <a href="/employee/google/connect/">Connect Google Calendar</a>
            """
        )

    employee = get_object_or_404(Employee, id=employee_id)

    try:

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [
                        settings.GOOGLE_EMPLOYEE_REDIRECT_URI,
                    ],
                }
            },
            scopes=EMPLOYEE_GOOGLE_SCOPES,
        )

        flow.redirect_uri = settings.GOOGLE_EMPLOYEE_REDIRECT_URI

        flow.oauth2session.state = state

        # ---------------------------------------------------------
        # PKCE verifier
        # ---------------------------------------------------------

        flow.code_verifier = code_verifier

        flow.fetch_token(
            authorization_response=request.build_absolute_uri(),
            code_verifier=code_verifier,
        )

        credentials = flow.credentials

        # ---------------------------------------------------------
        # Save Google account
        # ---------------------------------------------------------

        EmployeeGoogleAccount.objects.update_or_create(
            employee=employee,
            defaults={
                "email": (
                    credentials.id_token.get("email", "")
                    if credentials.id_token
                    else ""
                ),
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token or "",
            },
        )

        # ---------------------------------------------------------
        # Clear OAuth session data
        # ---------------------------------------------------------

        request.session.pop("employee_google_oauth_state", None)
        request.session.pop("employee_google_code_verifier", None)
        request.session.pop("employee_google_id", None)

        request.session.save()

        return HttpResponse(
            f"""
            <h2>✅ Google Calendar connected</h2>
            <p>Google Calendar has been connected for {employee.full_name}.</p>
            <a href="/employee/dashboard/">Return to Employee Dashboard</a>
            """
        )

    except Exception:
        logger.exception(
            "Employee Google Calendar OAuth failed for employee %s.",
            employee.pk,
        )
        return HttpResponse(
            f"""
            <h2>Google Calendar OAuth Error</h2>
            <p>Google Calendar could not be connected. Please try again or contact an administrator.</p>
            """,
            status=500,
        )

# ==========================================================
# Employee Login
# ==========================================================



# ==========================================================
# Employee Login
# ==========================================================



def employee_login(request):

    if request.method == "POST":

        form = EmployeeLoginForm(request, data=request.POST)

        if form.is_valid():

            user = form.get_user()

            if not hasattr(user, "employee_profile"):
                messages.error(
                    request, "❌ This account is not linked to an employee profile."
                )
                return redirect("employee_login")

            if not user.employee_profile.active:
                messages.error(request, "❌ This employee account is not active.")
                return redirect("employee_login")

            login(request, user)

            return redirect("employee_dashboard")

        messages.error(request, "❌ Invalid username/email or password.")

    else:
        form = EmployeeLoginForm()

    return render(request, "employees/employee_portal_login.html", {"form": form})


# ==========================================================
# Employee Logout
# ==========================================================


def employee_logout(request):
    logout(request)
    return redirect("employee_login")


# ==========================================================
# Employee Dashboard
# ==========================================================


@employee_required
def employee_dashboard(request):

    employee = get_object_or_404(Employee, user=request.user)

    today = timezone.now().date()

    today_jobs = (
        Booking.objects.filter(assigned_employee=employee, booking_date=today)
        .exclude(status="cancelled")
        .order_by("booking_time")
    )

    upcoming_jobs = (
        Booking.objects.filter(assigned_employee=employee, booking_date__gte=today)
        .exclude(status="cancelled")
        .order_by("booking_date", "booking_time")[:10]
    )

    completed_jobs = Booking.objects.filter(
        assigned_employee=employee, status="completed"
    ).count()

    return render(
        request,
        "employees/employee_portal_dashboard.html",
        {
            "employee": employee,
            "today_jobs": today_jobs,
            "upcoming_jobs": upcoming_jobs,
            "completed_jobs": completed_jobs,
        },
    )


# ==========================================================
# Employee Jobs
# ==========================================================


@employee_required
def employee_jobs(request):

    employee = get_object_or_404(Employee, user=request.user)

    jobs = Booking.objects.filter(assigned_employee=employee).order_by(
        "-booking_date", "-booking_time"
    )

    return render(
        request,
        "employees/employee_portal_jobs.html",
        {
            "employee": employee,
            "jobs": jobs,
        },
    )


@employee_required
def employee_damage_report(request):
    employee = get_object_or_404(Employee, user=request.user)

    if request.method == "POST":
        form = PropertyDamageReportForm(
            request.POST,
            request.FILES,
            employee=employee,
        )
        if form.is_valid():
            saved_assets = []
            try:
                with transaction.atomic():
                    booking = Booking.objects.select_for_update().get(
                        pk=form.cleaned_data["booking"].pk,
                        assigned_employee=employee,
                    )
                    report = PropertyDamageReport.objects.create(
                        employee=employee,
                        booking=booking,
                        description=form.cleaned_data["description"],
                    )
                    for image in form.cleaned_data["images"]:
                        report_image = PropertyDamageImage(
                            report=report,
                            image=image,
                        )
                        report_image.save()
                        saved_assets.append(
                            (report_image.image.storage, report_image.image.name)
                        )
            except Booking.DoesNotExist:
                form.add_error(
                    "booking",
                    "That job is no longer assigned to your account. Choose another job.",
                )
            except Exception:
                logger.exception(
                    "Could not save a property damage report for employee %s.",
                    employee.pk,
                )
                for storage, name in saved_assets:
                    try:
                        storage.delete(name)
                    except Exception:
                        logger.exception(
                            "Could not clean up property damage image %s.",
                            name,
                        )
                form.add_error(
                    None,
                    "We couldn't save your report right now. Please try again.",
                )
            else:
                messages.success(
                    request,
                    "Your property damage report has been sent to the team.",
                )
                return redirect("employee_damage_report")
    else:
        form = PropertyDamageReportForm(employee=employee)

    return render(
        request,
        "employees/employee_damage_report.html",
        {
            "employee": employee,
            "form": form,
            "has_assigned_jobs": form.fields["booking"].queryset.exists(),
        },
    )


# ==========================================================
# Job Detail
# ==========================================================




@employee_required
@_lock_employee_booking_mutations
def employee_job_detail(request, booking_id):

    employee = get_object_or_404(Employee, user=request.user)

    booking = get_object_or_404(
        Booking,
        id=booking_id,
        assigned_employee=employee,
    )

    before_photos = booking.job_photos.filter(
        photo_type="before"
    ).order_by("-uploaded_at")

    after_photos = booking.job_photos.filter(
        photo_type="after"
    ).order_by("-uploaded_at")

    has_employee_signature = booking.job_photos.filter(
        employee_signature__isnull=False
    ).exists()

    if request.method == "POST":

        form = EmployeeJobStatusForm(
            request.POST,
            instance=booking,
        )

        if form.is_valid():

            changed_fields = tuple(form.changed_data)
            previous_status = booking.status

            updated_booking = form.save(commit=False)

            # Validate job completion requirements.
            if updated_booking.status == "completed":

                if not before_photos.exists():
                    messages.error(
                        request,
                        "❌ Please upload at least one before photo before completing this job.",
                    )

                    return redirect(
                        "employee_job_detail",
                        booking_id=booking.id,
                    )

                if not after_photos.exists():
                    messages.error(
                        request,
                        "❌ Please upload at least one after photo before completing this job.",
                    )

                    return redirect(
                        "employee_job_detail",
                        booking_id=booking.id,
                    )

                if not has_employee_signature:
                    messages.error(
                        request,
                        "❌ Please upload employee signature before completing this job.",
                    )

                    return redirect(
                        "employee_job_detail",
                        booking_id=booking.id,
                    )

            suppression_flags = (
                {"_suppress_customer_status_notification": True}
                if "status" in changed_fields
                else {}
            )

            report_created = False
            invoice_created = False
            with temporary_instance_flags(
                updated_booking,
                **suppression_flags,
            ):
                if updated_booking.status == "completed":
                    try:
                        with transaction.atomic():
                            updated_booking.save()

                            from reports.models import CleaningReport
                            from invoices.services import get_or_create_invoice_for_booking
                            from quotes.models import QuoteRequest

                            _, report_created = CleaningReport.objects.get_or_create(
                                booking=updated_booking,
                            )
                            _, invoice_created = get_or_create_invoice_for_booking(
                                updated_booking
                            )
                            QuoteRequest.objects.filter(
                                idempotency_key=f"quote:{updated_booking.pk}"
                            ).update(status="completed")
                    except Exception:
                        logger.exception(
                            "Could not complete the job record workflow for booking %s.",
                            updated_booking.pk,
                        )
                        messages.error(
                            request,
                            "The job could not be completed right now. Please try again or contact an administrator.",
                        )
                        return redirect(
                            "employee_job_detail",
                            booking_id=booking.id,
                        )
                else:
                    updated_booking.save()

            # Notify administrators about job changes.
            if changed_fields:

                if "status" in changed_fields:
                    details = (
                        f"changed job #{updated_booking.id} "
                        f"from {dict(Booking.STATUS_CHOICES).get(previous_status, previous_status)} "
                        f"to {updated_booking.get_status_display()}"
                    )
                else:
                    details = (
                        f"updated job #{updated_booking.id} details"
                    )

                if "notes" in changed_fields:
                    details += " and added or edited job notes"

                notify_admins(
                    "Employee Updated Job",
                    f"{employee.full_name} {details}.",
                    "booking",
                    "/dashboard/bookings/",
                )

            # Synchronise the employee roster and calendar after the database
            # update. External integration failures leave a safe retry path.
            try:
                from rosters.services import RosterSyncPending, sync_booking_roster

                roster_sync = sync_booking_roster(updated_booking)
                if isinstance(roster_sync, RosterSyncPending):
                    raise roster_sync.error
            except Exception:
                logger.exception(
                    "Roster sync failed after employee update for booking %s.",
                    updated_booking.pk,
                )
                messages.warning(
                    request,
                    "Job updated, but the employee schedule could not be synced automatically.",
                )

            try:
                from google_reviews.calendar_utils import (
                    create_or_update_booking_event,
                )

                create_or_update_booking_event(updated_booking)

            except Exception:
                logger.exception(
                    "Google Calendar booking sync failed for booking %s.",
                    updated_booking.pk,
                )
                messages.warning(
                    request,
                    "Job updated, but Google Calendar could not be synced automatically.",
                )

            # Create the cleaning report if it doesn't exist.
            if updated_booking.status == "completed":
                if report_created:
                    notify_admins(
                        "Cleaning Report Ready",
                        (
                            f"{employee.full_name} completed booking "
                            f"#{updated_booking.id}; its cleaning report "
                            "is ready."
                        ),
                        "report",
                        f"/reports/booking/{updated_booking.id}/",
                    )

                if invoice_created:
                    logger.info(
                        "Draft invoice created for employee-completed booking %s.",
                        updated_booking.pk,
                    )

            # Update employee completion statistics only on the transition
            # to completed.
            if (
                previous_status != "completed"
                and updated_booking.status == "completed"
            ):

                employee.jobs_completed = Booking.objects.filter(
                    assigned_employee=employee,
                    status="completed",
                ).count()

                employee.save()

                # Keep the existing branded review email available behind a
                # setting, but do not send customer emails from the employee
                # portal by default.
                if getattr(
                    settings,
                    "EMPLOYEE_PORTAL_SEND_REVIEW_REQUEST_EMAILS",
                    False,
                ):
                    try:
                        from django.core.mail import EmailMultiAlternatives
                        from django.template.loader import render_to_string

                        customer = updated_booking.customer

                        if not customer.email or not customer.email.strip():

                            logger.error(
                                "Review email not sent: customer email is "
                                "missing for booking #%s.",
                                updated_booking.id,
                            )

                        else:

                            google_review_link = (
                                "https://g.page/r/CXH9ygKf16Y4EBM/review"
                            )

                            context = {
                                "customer_name": customer.full_name,
                                "review_link": google_review_link,
                                "booking": updated_booking,
                            }

                            html_message = render_to_string(
                                "emails/reviews/review_request.html",
                                context,
                            )

                            text_message = render_to_string(
                                "emails/reviews/review_request.txt",
                                context,
                            )

                            email = EmailMultiAlternatives(
                                subject="How was your cleaning service?",
                                body=text_message,
                                from_email=settings.DEFAULT_FROM_EMAIL,
                                to=[customer.email],
                                reply_to=["info@ydcleaning.com.au"],
                            )

                            email.attach_alternative(
                                html_message,
                                "text/html",
                            )

                            sent_count = email.send(
                                fail_silently=False,
                            )

                            if sent_count == 1:

                                logger.info(
                                    "Review email accepted by email backend "
                                    "for booking #%s.",
                                    updated_booking.id,
                                )

                            else:

                                logger.error(
                                    "Review email backend reported no message "
                                    "sent for booking #%s.",
                                    updated_booking.id,
                                )

                    except Exception:
                        logger.exception(
                            "Review email failed for booking #%s.",
                            updated_booking.id,
                        )

            messages.success(
                request,
                "✅ Job updated successfully.",
            )

            return redirect(
                "employee_job_detail",
                booking_id=booking.id,
            )

        messages.error(
            request,
            "❌ Please check the job update form.",
        )

    else:

        form = EmployeeJobStatusForm(
            instance=booking,
        )

    return render(
        request,
        "employees/employee_portal_job_detail.html",
        {
            "employee": employee,
            "booking": booking,
            "form": form,
            "before_photos": before_photos,
            "after_photos": after_photos,
            "has_employee_signature": has_employee_signature,
        },
    )


# ==========================================================
# Upload Job Photo
# ==========================================================


@employee_required
def upload_job_photo(request, booking_id):
    employee = get_object_or_404(Employee, user=request.user)
    booking = get_object_or_404(Booking, id=booking_id, assigned_employee=employee)

    if request.method == "POST" and request.POST.get("upload_action") == "cancel":
        nonce = request.POST.get("nonce", "")
        pending = request.session.get(JOB_PHOTO_UPLOAD_SESSION_KEY, {})
        pending_batch = pending.get(nonce, {})
        if pending_batch and pending_batch.get("expires_at", 0) > int(time.time()):
            _destroy_job_photo_assets(pending_batch.get("public_ids", []))
            pending.pop(nonce, None)
            request.session[JOB_PHOTO_UPLOAD_SESSION_KEY] = pending
        return JsonResponse({"cancelled": True})

    if request.method == "POST" and request.POST.get("upload_action") == "sign":
        try:
            count = int(request.POST.get("count", "0"))
        except (TypeError, ValueError):
            count = 0

        if not 1 <= count <= MAX_JOB_PHOTOS_PER_UPLOAD:
            return JsonResponse(
                {"error": f"Choose between 1 and {MAX_JOB_PHOTOS_PER_UPLOAD} photos per batch."},
                status=400,
            )

        cloudinary.config(
            cloud_name=settings.CLOUDINARY_STORAGE["CLOUD_NAME"],
            api_key=settings.CLOUDINARY_STORAGE["API_KEY"],
            api_secret=settings.CLOUDINARY_STORAGE["API_SECRET"],
        )
        timestamp = int(time.time())
        nonce = secrets.token_urlsafe(18)
        uploads = []
        public_ids = []

        for _ in range(count):
            public_id = f"job_photos/{booking.id}/{uuid.uuid4().hex}"
            params = {
                "public_id": public_id,
                "timestamp": timestamp,
                "allowed_formats": ",".join(sorted(ALLOWED_JOB_PHOTO_FORMATS)),
            }
            uploads.append(
                {
                    "public_id": public_id,
                    "timestamp": timestamp,
                    "allowed_formats": params["allowed_formats"],
                    "signature": api_sign_request(
                        params, settings.CLOUDINARY_STORAGE["API_SECRET"]
                    ),
                    "api_key": settings.CLOUDINARY_STORAGE["API_KEY"],
                }
            )
            public_ids.append(public_id)

        pending_uploads = request.session.get(JOB_PHOTO_UPLOAD_SESSION_KEY, {})
        now = int(time.time())
        pending_uploads = {
            key: value
            for key, value in pending_uploads.items()
            if value.get("expires_at", 0) > now
        }
        pending_uploads[nonce] = {
            "public_ids": public_ids,
            "expires_at": now + 3600,
        }
        request.session[JOB_PHOTO_UPLOAD_SESSION_KEY] = pending_uploads

        return JsonResponse(
            {
                "cloud_name": settings.CLOUDINARY_STORAGE["CLOUD_NAME"],
                "nonce": nonce,
                "uploads": uploads,
            }
        )

    if request.method == "POST":
        form = JobPhotoForm(request.POST, request.FILES)
        upload_nonce = request.POST.get("cloudinary_nonce", "")
        direct_uploads = []

        if form.is_valid():
            images = request.FILES.getlist("images")
            upload_data = request.POST.get("cloudinary_uploads", "")
            upload_nonce = request.POST.get("cloudinary_nonce", "")
            employee_signature = request.FILES.get("employee_signature")
            customer_signature = request.FILES.get("customer_signature")
            direct_uploads = []

            if upload_data:
                try:
                    supplied_uploads = json.loads(upload_data)
                except (TypeError, ValueError):
                    supplied_uploads = None

                pending = request.session.get(JOB_PHOTO_UPLOAD_SESSION_KEY, {})
                pending_batch = pending.get(upload_nonce, {})
                expected_ids = pending_batch.get("public_ids", [])

                if (
                    not pending_batch
                    or pending_batch.get("expires_at", 0) <= int(time.time())
                    or images
                ):
                    _destroy_job_photo_assets(expected_ids)
                    pending.pop(upload_nonce, None)
                    request.session[JOB_PHOTO_UPLOAD_SESSION_KEY] = pending
                    form.add_error(
                        None,
                        "The photo upload expired or could not be verified. Please try again.",
                    )
                else:
                    cloudinary.config(
                        cloud_name=settings.CLOUDINARY_STORAGE["CLOUD_NAME"],
                        api_key=settings.CLOUDINARY_STORAGE["API_KEY"],
                        api_secret=settings.CLOUDINARY_STORAGE["API_SECRET"],
                    )
                    try:
                        verified_uploads = _verify_job_photo_uploads(
                            supplied_uploads,
                            expected_ids,
                            booking.id,
                        )
                    except Exception:
                        logger.exception(
                            "Could not verify signed job photos for booking %s",
                            booking.id,
                        )
                        _destroy_job_photo_assets(expected_ids)
                        pending.pop(upload_nonce, None)
                        request.session[JOB_PHOTO_UPLOAD_SESSION_KEY] = pending
                        form.add_error(
                            None,
                            "One or more uploaded photos could not be verified. Please try again.",
                        )
                    else:
                        pending.pop(upload_nonce, None)
                        request.session[JOB_PHOTO_UPLOAD_SESSION_KEY] = pending
                        direct_uploads = verified_uploads

            if not upload_data and not images:
                form.add_error("photo_type", "Choose at least one photo to upload.")

            if len(images) > MAX_JOB_PHOTOS_PER_UPLOAD:
                form.add_error(
                    "photo_type",
                    f"Choose no more than {MAX_JOB_PHOTOS_PER_UPLOAD} photos per batch.",
                )

            for image in images:
                if Path(image.name).suffix.lower() not in ALLOWED_JOB_PHOTO_EXTENSIONS:
                    form.add_error("photo_type", "Use a JPG, PNG, WebP, or HEIC image.")
                    break
                if image.size > MAX_JOB_PHOTO_SIZE:
                    form.add_error("photo_type", "Each photo must be 25 MB or smaller.")
                    break

            for signature_file in (employee_signature, customer_signature):
                if signature_file and signature_file.size > MAX_SIGNATURE_SIZE:
                    form.add_error("photo_type", "Each signature must be 5 MB or smaller.")
                    break

            if not form.errors:
                stored_names = []
                signature_names = []
                direct_ids = [entry["public_id"] for entry in direct_uploads]
                try:
                    if not direct_uploads:
                        stored_names = _store_job_photo_files(images, booking.id)

                    employee_signature_name = ""
                    customer_signature_name = ""
                    signed_at = timezone.now()
                    if employee_signature:
                        suffix = Path(employee_signature.name).suffix.lower() or ".png"
                        employee_signature_name = default_storage.save(
                            f"signatures/employees/{uuid.uuid4().hex}{suffix}",
                            employee_signature,
                        )
                        signature_names.append(employee_signature_name)
                    if customer_signature:
                        suffix = Path(customer_signature.name).suffix.lower() or ".png"
                        customer_signature_name = default_storage.save(
                            f"signatures/customers/{uuid.uuid4().hex}{suffix}",
                            customer_signature,
                        )
                        signature_names.append(customer_signature_name)

                    if direct_uploads:
                        image_names = [entry["public_id"] for entry in direct_uploads]
                    else:
                        image_names = stored_names

                    photos = []
                    for image_name in image_names:
                        photo = form.save(commit=False)
                        photo.pk = None
                        photo.booking = booking
                        photo.employee = employee
                        photo.image = image_name
                        photo.employee_signature = employee_signature_name or None
                        photo.customer_signature = customer_signature_name or None
                        photo.employee_signed_at = signed_at if employee_signature else None
                        photo.customer_signed_at = signed_at if customer_signature else None
                        photos.append(photo)

                    with transaction.atomic():
                        for photo in photos:
                            # Preserve post_save gallery sync and staff notifications.
                            photo.save()
                except Exception:
                    logger.exception("Could not save job photos for booking %s", booking.id)
                    _destroy_job_photo_assets(direct_ids)
                    direct_uploads = []
                    for name in stored_names + signature_names:
                        try:
                            default_storage.delete(name)
                        except Exception:
                            logger.exception("Could not clean up job upload %s", name)
                    form.add_error(None, "The photos could not be saved. Please try again.")
                else:
                    uploaded_count = len(photos)
                    messages.success(request, f"✅ {uploaded_count} image(s) uploaded successfully.")
                    return redirect("employee_job_detail", booking_id=booking.id)

        if form.errors and upload_nonce:
            if direct_uploads:
                _destroy_job_photo_assets(
                    [entry["public_id"] for entry in direct_uploads]
                )
            pending = request.session.get(JOB_PHOTO_UPLOAD_SESSION_KEY, {})
            pending_batch = pending.pop(upload_nonce, {})
            if pending_batch:
                _destroy_job_photo_assets(pending_batch.get("public_ids", []))
                request.session[JOB_PHOTO_UPLOAD_SESSION_KEY] = pending

        messages.error(request, "❌ Please check the upload form.")

    else:

        form = JobPhotoForm()

    return render(
        request,
        "employees/upload_job_photo.html",
        {
            "employee": employee,
            "booking": booking,
            "form": form,
            "cloudinary_cloud_name": settings.CLOUDINARY_STORAGE["CLOUD_NAME"],
        },
    )


# ==========================================================
# Employee Profile
# ==========================================================


@employee_required
def employee_profile(request):

    employee = get_object_or_404(Employee, user=request.user)

    profile_form = EmployeeProfileForm(instance=employee)

    password_form = EmployeePasswordForm(user=request.user)

    if request.method == "POST":

        form_type = request.POST.get("form_type")

        # -----------------------------------
        # Update Profile
        # -----------------------------------

        if form_type == "profile":

            profile_form = EmployeeProfileForm(
                request.POST,
                request.FILES,
                instance=employee,
            )

            if profile_form.is_valid():

                changed_fields = tuple(profile_form.changed_data)

                profile_form.save()

                if changed_fields:
                    notify_admins(
                        "Employee Updated Profile",
                        f"{employee.full_name} updated their employee profile.",
                        "employee",
                        "/dashboard/employees/",
                    )

                messages.success(request, "✅ Profile updated successfully.")

                return redirect("employee_profile")

        # -----------------------------------
        # Change Password
        # -----------------------------------

        if form_type == "password":

            password_form = EmployeePasswordForm(user=request.user, data=request.POST)

            if password_form.is_valid():

                user = password_form.save()

                notify_admins(
                    "Employee Changed Password",
                    f"{employee.full_name} changed their employee account password.",
                    "employee",
                    "/dashboard/employees/",
                )

                update_session_auth_hash(request, user)

                messages.success(request, "✅ Password updated successfully.")

                return redirect("employee_profile")

    return render(
        request,
        "employees/employee_profile.html",
        {
            "employee": employee,
            "profile_form": profile_form,
            "password_form": password_form,
        },
    )


# ==========================================================
# Delete Job Photo
# ==========================================================

@employee_required
def delete_job_photo(request, photo_id):
    """Delete a job photo uploaded by employee"""
    from bookings.models import JobPhoto
    
    photo = get_object_or_404(JobPhoto, id=photo_id)
    employee = get_object_or_404(Employee, user=request.user)
    
    # Verify employee owns this photo
    if photo.employee != employee:
        messages.error(request, "❌ You can only delete your own photos.")
        return redirect("employee_job_detail", booking_id=photo.booking.id)
    
    booking_id = photo.booking.id
    
    if request.method == "POST":
        photo_type = photo.get_photo_type_display().lower()
        photo.delete()
        notify_admins(
            "Employee Deleted Job Photo",
            f"{employee.full_name} deleted a {photo_type} photo from booking #{booking_id}.",
            "report",
            f"/reports/booking/{booking_id}/",
        )
        messages.success(request, "✅ Photo deleted successfully.")
        return redirect("employee_job_detail", booking_id=booking_id)
    
    return render(
        request,
        "shared/confirm_delete.html",
        {
            "object_name": f"Job Photo",
            "cancel_url": f"/employees/jobs/{booking_id}/",
        },
    )
