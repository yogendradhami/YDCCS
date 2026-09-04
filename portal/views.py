# ====================================================
# YD Commercial Cleaning Services
# File: portal/views.py
# Purpose:
# - Customer registration
# - Customer login/logout
# - Customer dashboard
# - Customer bookings
# - Customer invoices
# - Customer booking details
# - Customer profile management
# ====================================================

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import reverse
from django.utils.crypto import get_random_string

from attendance.models import AttendanceLog
from bookings.models import Booking
from contracts.models import CleaningContract
from customers.models import Customer
from invoices.models import Invoice
from notifications.models import Notification
from reports.models import CleaningReport

from .forms import (
    CustomerPasswordForm,
    CustomerProfileForm,
    CustomerRegisterForm,
    ResendVerificationForm,
)


def send_customer_verification_email(request, customer):
    if not customer.verification_token:
        customer.verification_token = get_random_string(64)
        customer.save(update_fields=["verification_token"])

    verification_url = request.build_absolute_uri(
        reverse("verify_customer_email", args=[customer.verification_token])
    )
    sent = send_mail(
        "Verify your YD Cleaning customer account",
        (
            f"Hi {customer.full_name},\n\n"
            "Please verify your email address by opening this link:\n"
            f"{verification_url}\n\n"
            "If you did not create this account, you can ignore this email."
        ),
        settings.DEFAULT_FROM_EMAIL,
        [customer.email],
        fail_silently=False,
    )
    if sent != 1:
        raise RuntimeError("The verification email could not be queued.")
    return sent


def portal_register(request):
    # Customer account registration view.
    if request.method == "POST":
        form = CustomerRegisterForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                full_name = form.cleaned_data["full_name"]
                email = form.cleaned_data["email"]
                phone = form.cleaned_data["phone"]
                address = form.cleaned_data["address"]
                suburb_postcode = form.cleaned_data["suburb_postcode"]

                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=form.cleaned_data["password"],
                )

                customer = Customer.objects.create(
                    user=user,
                    full_name=full_name or user.username,
                    email=email,
                    phone=phone,
                    address=address,
                    suburb_postcode=suburb_postcode,
                    property_type="House",
                    verification_token=get_random_string(64),
                )

                send_customer_verification_email(request, customer)

            messages.success(
                request,
                "✅ Account created. Check your email to verify your account.",
            )
            return redirect("portal_login")

        messages.error(request, "❌ Please check the registration form.")

    else:
        form = CustomerRegisterForm()

    return render(request, "portal/portal_register.html", {"form": form})


def resend_customer_verification(request):
    if request.method == "POST":
        form = ResendVerificationForm(request.POST)
        if form.is_valid():
            customer = Customer.objects.filter(
                email__iexact=form.cleaned_data["email"]
            ).first()
            if customer and not customer.email_verified and customer.user_id:
                send_customer_verification_email(request, customer)
            messages.success(
                request,
                "If that account needs verification, a new email has been sent.",
            )
            return redirect("portal_login")
    else:
        form = ResendVerificationForm()
    return render(
        request,
        "portal/portal_resend_verification.html",
        {"form": form},
    )


def verify_customer_email(request, token):
    customer = get_object_or_404(Customer, verification_token=token)
    customer.email_verified = True
    customer.verification_token = None
    customer.save(update_fields=["email_verified", "verification_token"])
    messages.success(request, "Your email address has been verified successfully.")
    return redirect("portal_login")


def portal_login(request):
    # Customer login view.
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()

            # Make sure this user has a customer profile.
            customer = getattr(user, "customer_profile", None)
            if customer is None:
                messages.error(
                    request, "❌ This account is not linked to a customer profile."
                )
                return redirect("portal_login")

            if not customer.email_verified and customer.verification_token:
                messages.error(
                    request,
                    "Please verify your email address before signing in.",
                )
                return redirect("portal_login")

            login(request, user)
            return redirect("portal_dashboard")

        messages.error(request, "❌ Invalid username or password.")

    else:
        form = AuthenticationForm()

    return render(request, "portal/portal_login.html", {"form": form})


def portal_logout(request):
    # Customer logout view.
    logout(request)
    return redirect("portal_login")


@login_required
def portal_dashboard(request):
    customer = get_object_or_404(Customer, user=request.user)

    bookings = Booking.objects.filter(customer=customer).order_by(
        "-booking_date", "-booking_time"
    )[:10]

    invoices = Invoice.objects.filter(booking__customer=customer).order_by(
        "-issue_date"
    )[:10]

    upcoming_bookings = (
        Booking.objects.filter(
            customer=customer, booking_date__gte=timezone.now().date()
        )
        .exclude(status="cancelled")
        .count()
    )

    completed_jobs = Booking.objects.filter(
        customer=customer, status="completed"
    ).count()

    paid_invoices = Invoice.objects.filter(
        booking__customer=customer, status="paid"
    ).count()

    unpaid_invoices = (
        Invoice.objects.filter(booking__customer=customer)
        .exclude(status="paid")
        .count()
    )

    outstanding_balance = (
        Invoice.objects.filter(booking__customer=customer)
        .exclude(status="paid")
        .aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    total_paid = (
        Invoice.objects.filter(booking__customer=customer, status="paid").aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    last_cleaning = (
        Booking.objects.filter(customer=customer, status="completed")
        .order_by("-booking_date")
        .first()
    )

    active_contracts = CleaningContract.objects.filter(
        customer=customer, status="active"
    ).count()

    expiring_contracts = CleaningContract.objects.filter(
        customer=customer, status="active"
    ).count()

    notifications = Notification.objects.filter(user=request.user)[:10]

    unread_notifications = Notification.objects.filter(
        user=request.user, is_read=False
    ).count()

    reports = CleaningReport.objects.filter(booking__customer=customer).order_by(
        "-generated_at"
    )[:10]

    return render(
        request,
        "portal/portal_dashboard.html",
        {
            "customer": customer,
            "bookings": bookings,
            "invoices": invoices,
            "paid_invoices": paid_invoices,
            "unpaid_invoices": unpaid_invoices,
            "upcoming_bookings": upcoming_bookings,
            "completed_jobs": completed_jobs,
            "outstanding_balance": outstanding_balance,
            "total_paid": total_paid,
            "last_cleaning": last_cleaning,
            "active_contracts": active_contracts,
            "expiring_contracts": expiring_contracts,
            "notifications": notifications,
            "unread_notifications": unread_notifications,
            "reports": reports,
        },
    )


@login_required
def portal_bookings(request):
    # Customer bookings list.
    customer = get_object_or_404(Customer, user=request.user)

    bookings = Booking.objects.filter(customer=customer).order_by(
        "-booking_date", "-booking_time"
    )

    return render(
        request,
        "portal_bookings.html",
        {
            "customer": customer,
            "bookings": bookings,
        },
    )


@login_required
def booking_detail(request, booking_id):
    # Customer booking detail page.
    customer = get_object_or_404(Customer, user=request.user)

    booking = get_object_or_404(Booking, id=booking_id, customer=customer)

    # Before photos uploaded by employee.
    before_photos = booking.job_photos.filter(photo_type="before").order_by(
        "-uploaded_at"
    )

    # After photos uploaded by employee.
    after_photos = booking.job_photos.filter(photo_type="after").order_by(
        "-uploaded_at"
    )

    # Attendance record for this booking.
    attendance = AttendanceLog.objects.filter(booking=booking).first()

    return render(
        request,
        "portal/portal_booking_detail_new.html",
        {
            "customer": customer,
            "booking": booking,
            "before_photos": before_photos,
            "after_photos": after_photos,
            "attendance": attendance,
        },
    )


@login_required
def portal_invoices(request):
    # Customer invoices list.
    customer = get_object_or_404(Customer, user=request.user)

    invoices = Invoice.objects.filter(booking__customer=customer).order_by(
        "-issue_date"
    )

    return render(
        request,
        "portal/portal_invoices.html",
        {
            "customer": customer,
            "invoices": invoices,
        },
    )


@login_required
def portal_invoice_detail(request, invoice_id):
    # Customer invoice detail page.
    customer = get_object_or_404(Customer, user=request.user)

    invoice = get_object_or_404(Invoice, id=invoice_id, booking__customer=customer)

    return render(
        request,
        "portal_invoice_detail.html",
        {
            "customer": customer,
            "invoice": invoice,
        },
    )


@login_required
def portal_profile(request):
    # Customer profile and password management page.
    customer = get_object_or_404(Customer, user=request.user)

    # Load profile form with current customer data.
    profile_form = CustomerProfileForm(instance=customer)

    # Load password form for current user.
    password_form = CustomerPasswordForm(user=request.user)

    if request.method == "POST":
        # This identifies which form was submitted.
        form_type = request.POST.get("form_type")

        # Update customer profile.
        if form_type == "profile":
            profile_form = CustomerProfileForm(request.POST, instance=customer)

            if profile_form.is_valid():
                updated_customer = profile_form.save()

                # Keep Django user email in sync with customer email.
                request.user.email = updated_customer.email
                request.user.save()

                messages.success(request, "✅ Profile updated successfully.")

                return redirect("portal_profile")

        # Change customer password.
        if form_type == "password":
            password_form = CustomerPasswordForm(user=request.user, data=request.POST)

            if password_form.is_valid():
                user = password_form.save()

                # Keep customer logged in after password change.
                update_session_auth_hash(request, user)

                messages.success(request, "✅ Password updated successfully.")

                return redirect("portal_profile")

    return render(
        request,
        "portal/portal_profile.html",
        {
            "customer": customer,
            "profile_form": profile_form,
            "password_form": password_form,
        },
    )


@login_required
def portal_documents(request):

    customer = get_object_or_404(Customer, user=request.user)

    invoices = Invoice.objects.filter(booking__customer=customer).order_by(
        "-issue_date"
    )

    bookings = Booking.objects.filter(customer=customer)

    contracts = CleaningContract.objects.filter(customer=customer).order_by(
        "-created_at"
    )

    return render(
        request,
        "portal/portal_documents.html",
        {
            "customer": customer,
            "invoices": invoices,
            "bookings": bookings,
            "contracts": contracts,
        },
    )
