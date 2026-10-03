# ====================================================
# YD Commercial Cleaning Services
# File: invoices/views.py
# Purpose:
# - Invoice list
# - Invoice creation
# - Invoice editing
# - Invoice deletion
# - Invoice detail page
# - PDF invoice download
# - Stripe Checkout payment flow
# ====================================================

import logging

logger = logging.getLogger(__name__)

from io import BytesIO

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .forms import InvoiceForm
from .models import Invoice

from django.db.models import Q, Sum

from dashboard.decorators import admin_required
from dashboard.models import ActivityLog
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.db import transaction
from django.db.models import Sum, Q
from dashboard.models import ActivityLog, EmailLog
from customers.models import Customer



def get_accessible_invoice(request, invoice_id):
    invoice = get_object_or_404(
        Invoice.objects.select_related(
            "booking__customer"
        ),
        id=invoice_id,
    )

    if request.user.is_staff or request.user.is_superuser:
        return invoice

    if invoice.booking.customer.user_id == request.user.id:
        return invoice

    raise PermissionDenied(
        "You do not have permission to access this invoice."
    )


def invoice_detail_redirect_name(user):
    return (
        "portal_invoice_detail"
        if hasattr(user, "customer_profile")
        else "invoice_detail"
    )


@login_required
def invoice_list(request):
    today = timezone.localdate()

    base_invoices = (
        Invoice.objects
        .select_related("booking__customer")
        .all()
    )

    # ==========================================================
    # FINANCIAL KPIs
    # ==========================================================

    total_invoiced = (
        base_invoices
        .exclude(status="cancelled")
        .aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    paid_total = (
        base_invoices
        .filter(status="paid")
        .aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    outstanding_total = (
        base_invoices
        .filter(status__in=["draft", "sent", "overdue"])
        .aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    overdue_total = (
        base_invoices
        .filter(due_date__lt=today)
        .exclude(status__in=["paid", "cancelled"])
        .aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    # ==========================================================
    # SEARCH / FILTERS
    # ==========================================================

    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    invoices = base_invoices

    if query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=query)
            | Q(booking__customer__full_name__icontains=query)
            | Q(booking__customer__email__icontains=query)
            | Q(booking__service_type__icontains=query)
        )

    valid_statuses = {
        value for value, label in Invoice.STATUS_CHOICES
    }

    if status in valid_statuses:
        invoices = invoices.filter(status=status)

    if date_from:
        invoices = invoices.filter(issue_date__gte=date_from)

    if date_to:
        invoices = invoices.filter(issue_date__lte=date_to)

    invoices = invoices.order_by(
        "-issue_date",
        "-created_at",
    )

    # ==========================================================
    # CONTEXT
    # ==========================================================

    context = {
        "invoices": invoices,

        "today": today,

        "query": query,

        "selected_status": status,

        "date_from": date_from,

        "date_to": date_to,

        "status_choices": Invoice.STATUS_CHOICES,

        "stats": {
            "total_invoiced": total_invoiced,
            "paid_total": paid_total,
            "outstanding_total": outstanding_total,
            "overdue_total": overdue_total,

            "invoice_count": (
                base_invoices
                .exclude(status="cancelled")
                .count()
            ),

            "paid_count": (
                base_invoices
                .filter(status="paid")
                .count()
            ),

            "outstanding_count": (
                base_invoices
                .filter(
                    status__in=[
                        "draft",
                        "sent",
                        "overdue",
                    ]
                )
                .count()
            ),

            "overdue_count": (
                base_invoices
                .filter(due_date__lt=today)
                .exclude(
                    status__in=[
                        "paid",
                        "cancelled",
                    ]
                )
                .count()
            ),
        },
    }

    return render(
        request,
        "invoices/invoice_list.html",
        context,
    )

@login_required
def create_invoice(request):

    if request.method == "POST":

        form = InvoiceForm(request.POST)

        if form.is_valid():

            invoice = form.save()

            messages.success(
                request,
                f"✅ Invoice {invoice.invoice_number} created successfully.",
            )

            return redirect(
                "invoice_detail",
                invoice_id=invoice.id,
            )

        messages.error(
            request,
            "❌ Please check the invoice form and try again.",
        )

    else:

        form = InvoiceForm()

    return render(
        request,
        "invoices/invoice_form.html",
        {
            "form": form,
            "is_edit": False,
        },
    )


@login_required
def edit_invoice(request, invoice_id):

    invoice = get_object_or_404(
        Invoice.objects.select_related(
            "booking",
            "booking__customer",
        ),
        id=invoice_id,
    )

    # --------------------------------------------------
    # Paid invoices are protected from financial editing.
    # --------------------------------------------------
    if invoice.status == "paid":

        messages.warning(
            request,
            (
                f"Invoice {invoice.invoice_number} has already been paid "
                "and cannot be edited."
            ),
        )

        return redirect(
            "invoice_detail",
            invoice_id=invoice.id,
        )

    if request.method == "POST":

        form = InvoiceForm(
            request.POST,
            instance=invoice,
        )

        if form.is_valid():

            updated_invoice = form.save()

            messages.success(
                request,
                (
                    f"✅ Invoice "
                    f"{updated_invoice.invoice_number} "
                    "updated successfully."
                ),
            )

            return redirect(
                "invoice_detail",
                invoice_id=updated_invoice.id,
            )

        messages.error(
            request,
            "❌ Please check the invoice form and try again.",

        )

    else:

        form = InvoiceForm(
            instance=invoice,
        )

    return render(
        request,
        "invoices/invoice_form.html",
        {
            "form": form,
            "invoice": invoice,
            "is_edit": True,
        },
    )


@login_required
@require_POST
def delete_invoice(request, invoice_id):

    invoice = get_object_or_404(
        Invoice.objects.select_related(
            "booking",
            "booking__customer",
        ),
        id=invoice_id,
    )

    # --------------------------------------------------
    # Never hard-delete paid invoices.
    # --------------------------------------------------
    if invoice.status == "paid":

        messages.error(
            request,
            (
                f"Invoice {invoice.invoice_number} is paid and "
                "cannot be deleted."
            ),
        )

        return redirect("invoice_list")

    # --------------------------------------------------
    # Allow deletion of draft/cancelled invoices.
    # Sent/overdue invoices should be preserved for audit.
    # --------------------------------------------------
    if invoice.status not in ["draft", "cancelled"]:

        messages.warning(
            request,
            (
                f"Invoice {invoice.invoice_number} cannot be deleted "
                "because it has already been issued."
            ),
        )

        return redirect("invoice_list")

    invoice_number = invoice.invoice_number

    invoice.delete()

    messages.success(
        request,
        f"Invoice {invoice_number} deleted successfully.",
    )

    return redirect("invoice_list")

# ==========================================================
# EDIT INVOICE
# ==========================================================

@login_required
@admin_required
def edit_invoice(request, invoice_id):

    invoice = get_object_or_404(
        Invoice.objects.select_related(
            "booking__customer"
        ),
        id=invoice_id,
    )

    # Paid invoices should not be edited.
    if invoice.status == "paid":

        messages.error(
            request,
            (
                f"Invoice {invoice.invoice_number} is already paid "
                "and is locked from editing."
            ),
        )

        return redirect(
            "invoice_detail",
            invoice_id=invoice.id,
        )

    if request.method == "POST":

        form = InvoiceForm(
            request.POST,
            instance=invoice,
        )

        if form.is_valid():

            updated_invoice = form.save()

            try:

                ActivityLog.objects.create(
                    user=request.user,
                    action_type="invoice",
                    title="Invoice Updated",
                    description=(
                        f"{updated_invoice.invoice_number} "
                        f"was updated by "
                        f"{request.user.get_username()}."
                    ),
                )

            except Exception:
                pass

            messages.success(
                request,
                (
                    f"Invoice "
                    f"{updated_invoice.invoice_number} "
                    "updated successfully."
                ),
            )

            return redirect(
                "invoice_detail",
                invoice_id=updated_invoice.id,
            )

        messages.error(
            request,
            "Please correct the highlighted invoice fields.",
        )

    else:

        form = InvoiceForm(
            instance=invoice
        )

    return render(
        request,
        "invoices/invoice_form.html",
        {
            "form": form,
            "invoice": invoice,
            "is_edit": True,
        },
    )


# ==========================================================
# MARK INVOICE AS PAID
# ==========================================================

@login_required
@admin_required
@require_POST
def mark_invoice_paid(request, invoice_id):
    invoice = get_object_or_404(
        Invoice.objects.select_related("booking__customer"),
        id=invoice_id,
    )

    # Prevent duplicate payment events/emails.
    if invoice.status == "paid":
        messages.info(
            request,
            f"Invoice {invoice.invoice_number} is already marked as paid.",
        )
        return redirect("invoice_detail", invoice_id=invoice.id)

    # Record the payment.
    invoice.status = "paid"
    invoice.paid_at = timezone.now()
    invoice.save()

    # Send payment confirmation to the customer.
    email_sent = send_payment_received_email(invoice)

    if email_sent:
        messages.success(
            request,
            f"Invoice {invoice.invoice_number} marked as paid. "
            "Payment confirmation email sent to the customer.",
        )
    else:
        messages.warning(
            request,
            f"Invoice {invoice.invoice_number} was marked as paid, "
            "but the payment confirmation email could not be sent.",
        )

    return redirect("invoice_detail", invoice_id=invoice.id)
# ==========================================================
# CANCEL INVOICE
# ==========================================================

@login_required
@require_POST
@admin_required
def cancel_invoice(request, invoice_id):

    invoice = get_object_or_404(
        Invoice,
        id=invoice_id,
    )

    if invoice.status == "paid":

        messages.error(
            request,
            "Paid invoices cannot be cancelled.",
        )

        return redirect(
            "invoice_detail",
            invoice_id=invoice.id,
        )

    if invoice.status == "cancelled":

        messages.info(
            request,
            "This invoice is already cancelled.",
        )

        return redirect(
            "invoice_detail",
            invoice_id=invoice.id,
        )

    invoice.status = "cancelled"

    invoice.save()

    try:

        ActivityLog.objects.create(
            user=request.user,
            action_type="invoice",
            title="Invoice Cancelled",
            description=(
                f"{invoice.invoice_number} "
                "was cancelled."
            ),
        )

    except Exception:
        pass

    messages.success(
        request,
        f"{invoice.invoice_number} cancelled.",
    )

    return redirect("invoice_list")


# ==========================================================
# DELETE INVOICE
# ==========================================================

@login_required
@require_POST
@admin_required
def delete_invoice(request, invoice_id):

    invoice = get_object_or_404(
        Invoice,
        id=invoice_id,
    )

    # Financial protection:
    # Only draft/cancelled invoices may be permanently deleted.

    if invoice.status not in [
        "draft",
        "cancelled",
    ]:

        messages.error(
            request,
            (
                "Only draft or cancelled invoices can be "
                "permanently deleted. Issued financial records "
                "should be cancelled instead."
            ),
        )

        return redirect(
            "invoice_detail",
            invoice_id=invoice.id,
        )

    invoice_number = invoice.invoice_number

    try:

        ActivityLog.objects.create(
            user=request.user,
            action_type="invoice",
            title="Invoice Deleted",
            description=(
                f"{invoice_number} "
                "was permanently deleted."
            ),
        )

    except Exception:
        pass

    invoice.delete()

    messages.success(
        request,
        f"Invoice {invoice_number} deleted successfully.",
    )

    return redirect("invoice_list")



@login_required
def invoice_detail(request, invoice_id):

    invoice = get_accessible_invoice(
        request,
        invoice_id,
    )

    return render(
        request,
        "invoice_detail.html",
        {
            "invoice": invoice,
            "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        },
    )


@login_required
@require_POST
def create_stripe_checkout_session(request, invoice_id):

    invoice = get_accessible_invoice(
        request,
        invoice_id,
    )

    if invoice.status == "paid":

        messages.info(
            request,
            "This invoice has already been paid.",
        )

        return redirect(
            invoice_detail_redirect_name(request.user),
            invoice_id=invoice.id,
        )

    stripe.api_key = settings.STRIPE_SECRET_KEY

    domain = request.build_absolute_uri("/").rstrip("/")

    success_url = (
        domain
        + reverse(
            (
                "portal_stripe_payment_success"
                if hasattr(request.user, "customer_profile")
                else "stripe_payment_success"
            ),
            kwargs={
                "invoice_id": invoice.id,
            },
        )
        + "?session_id={CHECKOUT_SESSION_ID}"
    )

    cancel_url = (
        domain
        + reverse(
            invoice_detail_redirect_name(request.user),
            kwargs={
                "invoice_id": invoice.id,
            },
        )
    )

    amount_in_cents = int(
        invoice.total_amount * 100
    )

    checkout_session = stripe.checkout.Session.create(

        payment_method_types=["card"],

        mode="payment",

        customer_email=(
            invoice.booking.customer.email
            or None
        ),

        line_items=[
            {
                "price_data": {
                    "currency": settings.STRIPE_CURRENCY,

                    "product_data": {
                        "name": (
                            f"Invoice "
                            f"{invoice.invoice_number}"
                        ),
                        "description": invoice.description,
                    },

                    "unit_amount": amount_in_cents,
                },

                "quantity": 1,
            }
        ],

        metadata={
            "invoice_id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "customer": invoice.booking.customer.full_name,
        },

        success_url=success_url,

        cancel_url=cancel_url,
    )

    invoice.stripe_checkout_session_id = (
        checkout_session.id
    )

    invoice.status = "sent"

    invoice.save()

    return redirect(
        checkout_session.url
    )


@login_required
def stripe_payment_success(request, invoice_id):

    invoice = get_accessible_invoice(
        request,
        invoice_id,
    )

    session_id = request.GET.get(
        "session_id"
    )

    if session_id:

        stripe.api_key = settings.STRIPE_SECRET_KEY

        session = stripe.checkout.Session.retrieve(
            session_id
        )

        metadata = session.metadata or {}

        session_invoice_id = str(
            metadata.get("invoice_id", "")
        )

        is_expected_session = (
            session.id
            == invoice.stripe_checkout_session_id
        )

        if (
            is_expected_session
            and session_invoice_id
            == str(invoice.id)
            and session.payment_status == "paid"
        ):

            invoice.status = "paid"

            invoice.stripe_checkout_session_id = (
                session.id
            )

            invoice.stripe_payment_intent_id = (
                session.payment_intent or ""
            )

            invoice.paid_at = timezone.now()

            invoice.save()

            messages.success(
                request,
                "✅ Payment successful. Invoice marked as paid.",
            )

        else:

            messages.error(
                request,
                (
                    "The payment session does not match "
                    "this invoice or is incomplete."
                ),
            )

    return redirect(
        invoice_detail_redirect_name(request.user),
        invoice_id=invoice.id,
    )


@login_required
def stripe_payment_cancel(request, invoice_id):

    invoice = get_accessible_invoice(
        request,
        invoice_id,
    )

    messages.error(
        request,
        "❌ Payment cancelled.",
    )

    return redirect(
        invoice_detail_redirect_name(request.user),
        invoice_id=invoice.id,
    )


@login_required
def download_invoice_pdf(request, invoice_id):

    import os

    invoice = get_accessible_invoice(
        request,
        invoice_id,
    )

    booking = invoice.booking
    customer = booking.customer

    buffer = BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=A4,
    )

    width, height = A4

    # --------------------------------------------------
    # Logo
    # --------------------------------------------------

    logo_path = os.path.join(
        settings.BASE_DIR,
        "static",
        "images",
        "logo.jpeg",
    )

    if os.path.exists(logo_path):

        pdf.drawImage(
            logo_path,
            45,
            height - 120,
            width=85,
            height=85,
            preserveAspectRatio=True,
            mask="auto",
        )

    # --------------------------------------------------
    # Company details
    # --------------------------------------------------

    pdf.setFont(
        "Helvetica-Bold",
        20,
    )

    pdf.drawString(
        145,
        height - 55,
        "YD Commercial Cleaning Services",
    )

    pdf.setFont(
        "Helvetica",
        9,
    )

    pdf.drawString(
        145,
        height - 75,
        "ABN: 95 916 203 175",
    )

    pdf.drawString(
        145,
        height - 90,
        "2/10 Da Costa Avenue, Prospect SA 5082",
    )

    pdf.drawString(
        145,
        height - 105,
        "Phone: 0430 049 865",
    )

    pdf.drawString(
        145,
        height - 120,
        "Email: info@ydcleaning.com.au",
    )

    # --------------------------------------------------
    # Invoice details
    # --------------------------------------------------

    pdf.setFont(
        "Helvetica-Bold",
        18,
    )

    pdf.drawRightString(
        width - 45,
        height - 95,
        invoice.invoice_number,
    )

    pdf.setFont(
        "Helvetica",
        10,
    )

    pdf.drawRightString(
        width - 45,
        height - 115,
        f"Issue Date: {invoice.issue_date}",
    )

    if invoice.due_date:

        pdf.drawRightString(
            width - 45,
            height - 133,
            f"Due Date: {invoice.due_date}",
        )

    else:

        pdf.drawRightString(
            width - 45,
            height - 133,
            "Due Date: Not set",
        )

    pdf.drawRightString(
        width - 45,
        height - 151,
        f"Status: {invoice.get_status_display()}",
    )

    pdf.line(
        45,
        height - 170,
        width - 45,
        height - 170,
    )

    # --------------------------------------------------
    # Client information
    # --------------------------------------------------

    pdf.setFont(
        "Helvetica-Bold",
        13,
    )

    pdf.drawString(
        45,
        height - 185,
        "CLIENT INFORMATION",
    )

    pdf.setFont(
        "Helvetica",
        10,
    )

    y = height - 205

    pdf.drawString(
        45,
        y,
        f"Name: {customer.full_name}",
    )

    y -= 16

    pdf.drawString(
        45,
        y,
        f"Phone: {customer.phone}",
    )

    y -= 16

    if customer.email:

        pdf.drawString(
            45,
            y,
            f"Email: {customer.email}",
        )

        y -= 16

    if customer.address:

        pdf.drawString(
            45,
            y,
            f"Address: {customer.address}",
        )

    # --------------------------------------------------
    # Job details
    # --------------------------------------------------

    pdf.setFont(
        "Helvetica-Bold",
        13,
    )

    pdf.drawString(
        330,
        height - 185,
        "JOB DETAILS",
    )

    pdf.setFont(
        "Helvetica",
        10,
    )

    y2 = height - 205

    pdf.drawString(
        330,
        y2,
        f"Service: {booking.service_type}",
    )

    y2 -= 16

    pdf.drawString(
        330,
        y2,
        f"Date: {booking.booking_date}",
    )

    y2 -= 16

    pdf.drawString(
        330,
        y2,
        f"Time: {booking.booking_time}",
    )

    y2 -= 16

    pdf.drawString(
        330,
        y2,
        f"Suburb: {booking.suburb_postcode}",
    )

    y2 -= 16

    pdf.drawString(
        330,
        y2,
        f"Address: {booking.address[:38]}",
    )

    # --------------------------------------------------
    # Invoice table
    # --------------------------------------------------

    table_top = height - 330

    pdf.setFillColorRGB(
        0.94,
        0.96,
        0.98,
    )

    pdf.rect(
        45,
        table_top,
        width - 90,
        28,
        fill=True,
        stroke=False,
    )

    pdf.setFillColorRGB(
        0,
        0,
        0,
    )

    pdf.setFont(
        "Helvetica-Bold",
        10,
    )

    pdf.drawString(
        55,
        table_top + 9,
        "Description",
    )

    pdf.drawRightString(
        385,
        table_top + 9,
        "Qty",
    )

    pdf.drawRightString(
        470,
        table_top + 9,
        "Price",
    )

    pdf.drawRightString(
        width - 55,
        table_top + 9,
        "Total",
    )

    row_y = table_top - 32

    pdf.setFont(
        "Helvetica",
        10,
    )

    pdf.drawString(
        55,
        row_y,
        booking.service_type[:45],
    )

    pdf.drawRightString(
        385,
        row_y,
        "1",
    )

    pdf.drawRightString(
        470,
        row_y,
        f"${invoice.amount}",
    )

    pdf.drawRightString(
        width - 55,
        row_y,
        f"${invoice.amount}",
    )

    pdf.line(
        45,
        row_y - 18,
        width - 45,
        row_y - 18,
    )

    # --------------------------------------------------
    # Description
    # --------------------------------------------------

    pdf.setFont(
        "Helvetica-Bold",
        12,
    )

    pdf.drawString(
        45,
        row_y - 55,
        "Description",
    )

    pdf.setFont(
        "Helvetica",
        10,
    )

    desc_y = row_y - 75

    description = (
        invoice.description
        or "Cleaning service"
    )

    for line in description.split("\n"):

        pdf.drawString(
            45,
            desc_y,
            line[:80],
        )

        desc_y -= 14

        if desc_y < 180:
            break

    buffer.seek(0)

    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f"{invoice.invoice_number}.pdf",
    )



def send_payment_received_email(invoice):
    """
    Send a single payment-received email to the invoice customer.

    Returns True when the email is sent successfully.
    Returns False when the customer has no email or sending fails.
    """

    try:
        customer = invoice.booking.customer

        customer_email = getattr(customer, "email", None)

        if not customer_email:
            logger.warning(
                "Payment received email skipped: customer has no email. "
                "Invoice=%s",
                invoice.invoice_number,
            )
            return False

        customer_name = (
            getattr(customer, "full_name", None)
            or getattr(customer, "name", None)
            or "Customer"
        )

        context = {
            "invoice": invoice,
            "customer": customer,
            "customer_name": customer_name,
        }

        subject = (
            f"Payment Received - Invoice {invoice.invoice_number} "
            f"| YD Commercial Cleaning Services"
        )

        text_content = render_to_string(
            "emails/invoices/payment_received.txt",
            context,
        )

        html_content = render_to_string(
            "emails/invoices/payment_received.html",
            context,
        )

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[customer_email],
        )

        email.attach_alternative(
            html_content,
            "text/html",
        )

        email.send(fail_silently=False)

        logger.info(
            "Payment received email sent successfully. "
            "Invoice=%s Customer=%s",
            invoice.invoice_number,
            customer_email,
        )

        return True

    except Exception:
        logger.exception(
            "Failed to send payment received email. Invoice=%s",
            invoice.invoice_number,
        )
        return False
    
@login_required
@require_POST
def delete_invoice(request, invoice_id):
    """
    Permanently delete an invoice while keeping the related
    booking and customer history intact.

    Financial cleanup:
    - Deletes the invoice.
    - Deletes invoice-related email logs.
    - Deletes invoice-related activity logs where identifiable.
    - Recalculates the customer's stored revenue from remaining
      paid invoices.
    - Does NOT delete the booking.
    - Does NOT delete the customer.
    """

    with transaction.atomic():

        invoice = get_object_or_404(
            Invoice.objects.select_related("booking__customer"),
            id=invoice_id,
        )

        invoice_number = invoice.invoice_number
        customer = invoice.booking.customer
        customer_id = customer.id

        # -----------------------------------------------------
        # 1. Remove invoice-related email records
        # -----------------------------------------------------

        EmailLog.objects.filter(
            related_object=invoice_number
        ).delete()

        # -----------------------------------------------------
        # 2. Remove identifiable invoice activity records
        #
        # Existing ActivityLog does not have a ForeignKey to
        # Invoice, so we only remove records that explicitly
        # contain this invoice number.
        # -----------------------------------------------------

        ActivityLog.objects.filter(
            action_type="invoice"
        ).filter(
            Q(title__icontains=invoice_number)
            | Q(description__icontains=invoice_number)
        ).delete()

        # -----------------------------------------------------
        # 3. Delete the invoice itself
        # -----------------------------------------------------

        invoice.delete()

        # -----------------------------------------------------
        # 4. Recalculate customer revenue
        #
        # Only remaining PAID invoices count as revenue.
        # -----------------------------------------------------

        remaining_paid_revenue = (
            Invoice.objects.filter(
                booking__customer_id=customer_id,
                status="paid",
            ).aggregate(
                total=Sum("total_amount")
            )["total"]
            or 0
        )

        Customer.objects.filter(
            id=customer_id
        ).update(
            total_revenue=remaining_paid_revenue
        )

    messages.success(
        request,
        f"Invoice {invoice_number} was permanently deleted. "
        "Financial records have been recalculated.",
    )

    return redirect("invoice_list")