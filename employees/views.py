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

<<<<<<< HEAD
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from bookings.forms import JobPhotoForm
from bookings.models import Booking

from .forms import EmployeeJobStatusForm, EmployeeLoginForm
from .models import Employee
from .profile_forms import (
    EmployeePasswordForm,
    EmployeeProfileForm,
)

=======
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from bookings.models import Booking
from bookings.forms import JobPhotoForm

from .models import Employee
from .forms import EmployeeLoginForm, EmployeeJobStatusForm
from .profile_forms import (
    EmployeeProfileForm,
    EmployeePasswordForm,
)

from .decorators import employee_required
from dashboard.models import ActivityLog


>>>>>>> 5815f15 (Initial project commit)
# ==========================================================
# Employee Login
# ==========================================================

<<<<<<< HEAD

=======
>>>>>>> 5815f15 (Initial project commit)
def employee_login(request):

    if request.method == "POST":

<<<<<<< HEAD
        form = EmployeeLoginForm(request, data=request.POST)
=======
        form = EmployeeLoginForm(
            request,
            data=request.POST
        )
>>>>>>> 5815f15 (Initial project commit)

        if form.is_valid():

            user = form.get_user()

            if not hasattr(user, "employee_profile"):
                messages.error(
<<<<<<< HEAD
                    request, "❌ This account is not linked to an employee profile."
=======
                    request,
                    "❌ This account is not linked to an employee profile."
>>>>>>> 5815f15 (Initial project commit)
                )
                return redirect("employee_login")

            if not user.employee_profile.active:
<<<<<<< HEAD
                messages.error(request, "❌ This employee account is not active.")
                return redirect("employee_login")

            login(request, user)

            return redirect("employee_dashboard")

        messages.error(request, "❌ Invalid username/email or password.")
=======
                messages.error(
                    request,
                    "❌ This employee account is not active."
                )
                return redirect("employee_login")

            login(request, user)
            ActivityLog.objects.create(
                user=user,
                action_type="LOGIN",
                title="Employee Login",
                description=f"Employee {user.username} logged into employee portal."
            )

            return redirect("employee_dashboard")

        messages.error(
            request,
            "❌ Invalid username/email or password."
        )
>>>>>>> 5815f15 (Initial project commit)

    else:
        form = EmployeeLoginForm()

<<<<<<< HEAD
    return render(request, "employee_portal_login.html", {"form": form})
=======
    return render(
        request,
        "employees/employee_portal_login.html",
        {
            "form": form
        }
    )
>>>>>>> 5815f15 (Initial project commit)


# ==========================================================
# Employee Logout
# ==========================================================

<<<<<<< HEAD

def employee_logout(request):
=======
def employee_logout(request):
    ActivityLog.objects.create(
        user=request.user,
        action_type="LOGOUT",
        title="Employee Logout",
        description=f"Employee {request.user.username} logged out of employee portal."
    )


>>>>>>> 5815f15 (Initial project commit)
    logout(request)
    return redirect("employee_login")


# ==========================================================
# Employee Dashboard
# ==========================================================

<<<<<<< HEAD

@login_required
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
=======
@employee_required
def employee_dashboard(request):

    employee = get_object_or_404(
        Employee,
        user=request.user
    )

    today = timezone.now().date()

    today_jobs = Booking.objects.filter(
        assigned_employee=employee,
        booking_date=today
    ).exclude(
        status="cancelled"
    ).order_by(
        "booking_time"
    )

    upcoming_jobs = Booking.objects.filter(
        assigned_employee=employee,
        booking_date__gte=today
    ).exclude(
        status="cancelled"
    ).order_by(
        "booking_date",
        "booking_time"
    )[:10]

    completed_jobs = Booking.objects.filter(
        assigned_employee=employee,
        status="completed"
>>>>>>> 5815f15 (Initial project commit)
    ).count()

    return render(
        request,
<<<<<<< HEAD
        "employee_portal_dashboard.html",
=======
        "employees/employee_portal_dashboard.html",
>>>>>>> 5815f15 (Initial project commit)
        {
            "employee": employee,
            "today_jobs": today_jobs,
            "upcoming_jobs": upcoming_jobs,
            "completed_jobs": completed_jobs,
<<<<<<< HEAD
        },
=======
        }
>>>>>>> 5815f15 (Initial project commit)
    )


# ==========================================================
# Employee Jobs
# ==========================================================

<<<<<<< HEAD

@login_required
def employee_jobs(request):

    employee = get_object_or_404(Employee, user=request.user)

    jobs = Booking.objects.filter(assigned_employee=employee).order_by(
        "-booking_date", "-booking_time"
=======
@employee_required
def employee_jobs(request):

    employee = get_object_or_404(
        Employee,
        user=request.user
    )

    jobs = Booking.objects.filter(
        assigned_employee=employee
    ).order_by(
        "-booking_date",
        "-booking_time"
>>>>>>> 5815f15 (Initial project commit)
    )

    return render(
        request,
<<<<<<< HEAD
        "employee_portal_jobs.html",
        {
            "employee": employee,
            "jobs": jobs,
        },
=======
        "employees/employee_portal_jobs.html",
        {
            "employee": employee,
            "jobs": jobs,
        }
>>>>>>> 5815f15 (Initial project commit)
    )


# ==========================================================
# Job Detail
# ==========================================================

<<<<<<< HEAD

@login_required
def employee_job_detail(request, booking_id):

    employee = get_object_or_404(Employee, user=request.user)

    booking = get_object_or_404(Booking, id=booking_id, assigned_employee=employee)

    before_photos = booking.job_photos.filter(photo_type="before").order_by(
        "-uploaded_at"
    )

    after_photos = booking.job_photos.filter(photo_type="after").order_by(
=======
@employee_required
def employee_job_detail(request, booking_id):

    employee = get_object_or_404(
        Employee,
        user=request.user
    )

    booking = get_object_or_404(
        Booking,
        id=booking_id,
        assigned_employee=employee
    )

    before_photos = booking.job_photos.filter(
        photo_type="before"
    ).order_by(
        "-uploaded_at"
    )

    after_photos = booking.job_photos.filter(
        photo_type="after"
    ).order_by(
>>>>>>> 5815f15 (Initial project commit)
        "-uploaded_at"
    )

    has_employee_signature = booking.job_photos.filter(
        employee_signature__isnull=False
    ).exists()

    if request.method == "POST":

<<<<<<< HEAD
        form = EmployeeJobStatusForm(request.POST, instance=booking)
=======
        form = EmployeeJobStatusForm(
            request.POST,
            instance=booking
        )
>>>>>>> 5815f15 (Initial project commit)

        if form.is_valid():

            updated_booking = form.save(commit=False)

            if updated_booking.status == "completed":

                if not before_photos.exists():
                    messages.error(
                        request,
<<<<<<< HEAD
                        "❌ Please upload at least one before photo before completing this job.",
                    )

                    return redirect("employee_job_detail", booking_id=booking.id)
=======
                        "❌ Please upload at least one before photo before completing this job."
                    )

                    return redirect(
                        "employee_job_detail",
                        booking_id=booking.id
                    )
>>>>>>> 5815f15 (Initial project commit)

                if not after_photos.exists():
                    messages.error(
                        request,
<<<<<<< HEAD
                        "❌ Please upload at least one after photo before completing this job.",
                    )

                    return redirect("employee_job_detail", booking_id=booking.id)
=======
                        "❌ Please upload at least one after photo before completing this job."
                    )

                    return redirect(
                        "employee_job_detail",
                        booking_id=booking.id
                    )
>>>>>>> 5815f15 (Initial project commit)

                if not has_employee_signature:
                    messages.error(
                        request,
<<<<<<< HEAD
                        "❌ Please upload employee signature before completing this job.",
                    )

                    return redirect("employee_job_detail", booking_id=booking.id)
=======
                        "❌ Please upload employee signature before completing this job."
                    )

                    return redirect(
                        "employee_job_detail",
                        booking_id=booking.id
                    )
>>>>>>> 5815f15 (Initial project commit)

            updated_booking.save()

            if updated_booking.status == "completed":
                from reports.models import CleaningReport

<<<<<<< HEAD
                CleaningReport.objects.get_or_create(booking=updated_booking)
=======
                CleaningReport.objects.get_or_create(
                    booking=updated_booking
                )

>>>>>>> 5815f15 (Initial project commit)

            if updated_booking.status == "completed":

                employee.jobs_completed = Booking.objects.filter(
<<<<<<< HEAD
                    assigned_employee=employee, status="completed"
=======
                    assigned_employee=employee,
                    status="completed"
>>>>>>> 5815f15 (Initial project commit)
                ).count()

                employee.save()

<<<<<<< HEAD
                try:

                    from django.conf import settings
                    from django.core.mail import send_mail

                    customer = booking.customer

                    google_review_link = "https://g.page/r/CXH9ygKf16Y4EBM/review"
=======
                ActivityLog.objects.create(
                    user=request.user,
                    action_type="JOB",
                    title="Job Completed",
                    description=f"{employee.full_name} completed booking #{booking.id}"
                )

                try:

                    from django.core.mail import send_mail
                    from django.conf import settings

                    customer = booking.customer

                    google_review_link = (
                        "https://g.page/r/CXH9ygKf16Y4EBM/review"
                    )
>>>>>>> 5815f15 (Initial project commit)

                    send_mail(
                        subject="How was your cleaning service?",
                        message=f"""
            Hi {customer.full_name},

            Thank you for choosing YD Commercial Cleaning Services.

            Your cleaning service has been completed successfully.

            We would greatly appreciate your feedback.

            Leave a Google Review:
            {google_review_link}

            Thank you for supporting our local business.

            YD Commercial Cleaning Services
            0430 049 865
            www.ydcleaning.com
            """,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[customer.email],
                        fail_silently=True,
                    )

                except Exception as e:
                    print("Review email failed:", e)

<<<<<<< HEAD
            messages.success(request, "✅ Job updated successfully.")

            return redirect("employee_job_detail", booking_id=booking.id)

        messages.error(request, "❌ Please check the job update form.")

    else:

        form = EmployeeJobStatusForm(instance=booking)

    return render(
        request,
        "employee_portal_job_detail.html",
=======



            messages.success(
                request,
                "✅ Job updated successfully."
            )

            return redirect(
                "employee_job_detail",
                booking_id=booking.id
            )

        messages.error(
            request,
            "❌ Please check the job update form."
        )

    else:

        form = EmployeeJobStatusForm(
            instance=booking
        )

    return render(
        request,
        "employees/employee_portal_job_detail.html",
>>>>>>> 5815f15 (Initial project commit)
        {
            "employee": employee,
            "booking": booking,
            "form": form,
            "before_photos": before_photos,
            "after_photos": after_photos,
            "has_employee_signature": has_employee_signature,
<<<<<<< HEAD
        },
    )


=======
        }
    )

>>>>>>> 5815f15 (Initial project commit)
# ==========================================================
# Upload Job Photo
# ==========================================================

<<<<<<< HEAD

@login_required
def upload_job_photo(request, booking_id):

    employee = get_object_or_404(Employee, user=request.user)

    booking = get_object_or_404(Booking, id=booking_id, assigned_employee=employee)

    if request.method == "POST":

        form = JobPhotoForm(request.POST, request.FILES)
=======
@employee_required
def upload_job_photo(request, booking_id):

    employee = get_object_or_404(
        Employee,
        user=request.user
    )

    booking = get_object_or_404(
        Booking,
        id=booking_id,
        assigned_employee=employee
    )

    if request.method == "POST":

        form = JobPhotoForm(
            request.POST,
            request.FILES
        )
>>>>>>> 5815f15 (Initial project commit)

        if form.is_valid():

            images = request.FILES.getlist("images")

<<<<<<< HEAD
            employee_signature = request.FILES.get("employee_signature")

            customer_signature = request.FILES.get("customer_signature")
=======
            employee_signature = request.FILES.get(
                "employee_signature"
            )

            customer_signature = request.FILES.get(
                "customer_signature"
            )
>>>>>>> 5815f15 (Initial project commit)

            uploaded_count = 0

            for image in images:

                photo = form.save(commit=False)

                photo.pk = None

                photo.booking = booking
                photo.employee = employee

                photo.image = image

                if employee_signature:
                    photo.employee_signature = employee_signature
                    photo.employee_signed_at = timezone.now()

                if customer_signature:
                    photo.customer_signature = customer_signature
                    photo.customer_signed_at = timezone.now()

                photo.save()

                uploaded_count += 1

<<<<<<< HEAD
            messages.success(
                request, f"✅ {uploaded_count} image(s) uploaded successfully."
            )

            return redirect("employee_job_detail", booking_id=booking.id)

        messages.error(request, "❌ Please check the upload form.")
=======
                ActivityLog.objects.create(
                    user=request.user,
                    action_type="PHOTO",
                    title="Job Photos Uploaded",
                    description=f"{employee.full_name} uploaded {uploaded_count} photos for booking #{booking.id}"
                )

            messages.success(
                request,
                f"✅ {uploaded_count} image(s) uploaded successfully."
            )

            return redirect(
                "employee_job_detail",
                booking_id=booking.id
            )

        messages.error(
            request,
            "❌ Please check the upload form."
        )
>>>>>>> 5815f15 (Initial project commit)

    else:

        form = JobPhotoForm()

    return render(
        request,
<<<<<<< HEAD
        "upload_job_photo.html",
=======
        "employees/upload_job_photo.html",
>>>>>>> 5815f15 (Initial project commit)
        {
            "employee": employee,
            "booking": booking,
            "form": form,
<<<<<<< HEAD
        },
    )


=======
        }
    )

>>>>>>> 5815f15 (Initial project commit)
# ==========================================================
# Employee Profile
# ==========================================================

<<<<<<< HEAD

@login_required
def employee_profile(request):

    employee = get_object_or_404(Employee, user=request.user)

    profile_form = EmployeeProfileForm(instance=employee)

    password_form = EmployeePasswordForm(user=request.user)

    if request.method == "POST":

        form_type = request.POST.get("form_type")
=======
@employee_required
def employee_profile(request):

    employee = get_object_or_404(
        Employee,
        user=request.user
    )

    profile_form = EmployeeProfileForm(
        instance=employee
    )

    password_form = EmployeePasswordForm(
        user=request.user
    )

    if request.method == "POST":

        form_type = request.POST.get(
            "form_type"
        )
>>>>>>> 5815f15 (Initial project commit)

        # -----------------------------------
        # Update Profile
        # -----------------------------------

        if form_type == "profile":

<<<<<<< HEAD
            profile_form = EmployeeProfileForm(request.POST, instance=employee)
=======
            profile_form = EmployeeProfileForm(
                request.POST,
                instance=employee
            )
>>>>>>> 5815f15 (Initial project commit)

            if profile_form.is_valid():

                profile_form.save()

<<<<<<< HEAD
                messages.success(request, "✅ Profile updated successfully.")

                return redirect("employee_profile")
=======
                messages.success(
                    request,
                    "✅ Profile updated successfully."
                )

                return redirect(
                    "employee_profile"
                )
>>>>>>> 5815f15 (Initial project commit)

        # -----------------------------------
        # Change Password
        # -----------------------------------

        if form_type == "password":

<<<<<<< HEAD
            password_form = EmployeePasswordForm(user=request.user, data=request.POST)
=======
            password_form = EmployeePasswordForm(
                user=request.user,
                data=request.POST
            )
>>>>>>> 5815f15 (Initial project commit)

            if password_form.is_valid():

                user = password_form.save()

<<<<<<< HEAD
                update_session_auth_hash(request, user)

                messages.success(request, "✅ Password updated successfully.")

                return redirect("employee_profile")

    return render(
        request,
        "employee_profile.html",
=======
                update_session_auth_hash(
                    request,
                    user
                )

                messages.success(
                    request,
                    "✅ Password updated successfully."
                )

                return redirect(
                    "employee_profile"
                )

    return render(
        request,
        "employees/employee_profile.html",
>>>>>>> 5815f15 (Initial project commit)
        {
            "employee": employee,
            "profile_form": profile_form,
            "password_form": password_form,
<<<<<<< HEAD
        },
    )
=======
        }
    )
>>>>>>> 5815f15 (Initial project commit)
