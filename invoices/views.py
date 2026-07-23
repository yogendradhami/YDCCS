# ====================================================
# YD Commercial Cleaning Services
# File: invoices/views.py
# Purpose:
# - Invoice list
# - Invoice creation
# - Invoice detail page
# - PDF invoice download
# - Stripe Checkout payment flow
# ====================================================

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


def get_accessible_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice.objects.select_related("booking__customer"), id=invoice_id)
    if request.user.is_staff or request.user.is_superuser:
        return invoice
    if invoice.booking.customer.user_id == request.user.id:
        return invoice
    raise PermissionDenied("You do not have permission to access this invoice.")


def invoice_detail_redirect_name(user):
    return "portal_invoice_detail" if hasattr(user, "customer_profile") else "invoice_detail"


@login_required
def invoice_list(request):
    invoices = Invoice.objects.all().order_by("-created_at")

    return render(request, "invoices/invoice_list.html", {"invoices": invoices})


@login_required
def create_invoice(request):
    if request.method == "POST":
        form = InvoiceForm(request.POST)

        if form.is_valid():
            invoice = form.save()
            messages.success(request, "✅ Invoice created successfully.")
            return redirect("invoice_detail", invoice_id=invoice.id)

        messages.error(request, "❌ Please check the invoice form and try again.")

    else:
        form = InvoiceForm()

    return render(request, "invoices/invoice_form.html", {"form": form})


@login_required
def invoice_detail(request, invoice_id):
    invoice = get_accessible_invoice(request, invoice_id)

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
    invoice = get_accessible_invoice(request, invoice_id)

    if invoice.status == "paid":
        messages.info(request, "This invoice has already been paid.")
        return redirect(invoice_detail_redirect_name(request.user), invoice_id=invoice.id)

    stripe.api_key = settings.STRIPE_SECRET_KEY

    domain = request.build_absolute_uri("/").rstrip("/")

    success_url = (
        domain
        + reverse(
            "portal_stripe_payment_success"
            if hasattr(request.user, "customer_profile")
            else "stripe_payment_success",
            kwargs={"invoice_id": invoice.id},
        )
        + "?session_id={CHECKOUT_SESSION_ID}"
    )

    cancel_url = domain + reverse(
        invoice_detail_redirect_name(request.user), kwargs={"invoice_id": invoice.id}
    )

    amount_in_cents = int(invoice.total_amount * 100)

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        customer_email=invoice.booking.customer.email or None,
        line_items=[
            {
                "price_data": {
                    "currency": settings.STRIPE_CURRENCY,
                    "product_data": {
                        "name": f"Invoice {invoice.invoice_number}",
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

    invoice.stripe_checkout_session_id = checkout_session.id
    invoice.status = "sent"
    invoice.save()

    return redirect(checkout_session.url)


@login_required
def stripe_payment_success(request, invoice_id):
    invoice = get_accessible_invoice(request, invoice_id)

    session_id = request.GET.get("session_id")

    if session_id:
        stripe.api_key = settings.STRIPE_SECRET_KEY

        session = stripe.checkout.Session.retrieve(session_id)

        # The success URL is user-controlled.  Only accept the session created
        # for this exact invoice; otherwise a paid session for another invoice
        # could mark this invoice as paid.
        metadata = session.metadata or {}
        session_invoice_id = str(metadata.get("invoice_id", ""))
        is_expected_session = session.id == invoice.stripe_checkout_session_id

        if (
            is_expected_session
            and session_invoice_id == str(invoice.id)
            and session.payment_status == "paid"
        ):
            invoice.status = "paid"
            invoice.stripe_checkout_session_id = session.id
            invoice.stripe_payment_intent_id = session.payment_intent or ""
            invoice.paid_at = timezone.now()
            invoice.save()

            messages.success(request, "✅ Payment successful. Invoice marked as paid.")
        else:
            messages.error(request, "The payment session does not match this invoice or is incomplete.")

    return redirect(invoice_detail_redirect_name(request.user), invoice_id=invoice.id)


@login_required
def stripe_payment_cancel(request, invoice_id):
    invoice = get_accessible_invoice(request, invoice_id)

    messages.error(request, "❌ Payment cancelled.")

    return redirect(invoice_detail_redirect_name(request.user), invoice_id=invoice.id)


@login_required
def download_invoice_pdf(request, invoice_id):
    import os

    invoice = get_accessible_invoice(request, invoice_id)
    booking = invoice.booking
    customer = booking.customer

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4

    # Logo
    logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logo.jpeg")

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

    # Company details
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(145, height - 55, "YD Commercial Cleaning Services")

    pdf.setFont("Helvetica", 9)
    pdf.drawString(145, height - 75, "ABN: 95 916 203 175")
    pdf.drawString(145, height - 90, "2/10 Da Costa Avenue, Prospect SA 5082")
    pdf.drawString(145, height - 105, "Phone: 0430 049 865")
    pdf.drawString(145, height - 120, "Email: ydcommercialcleaning@gmail.com")

    # Invoice details - top right
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawRightString(width - 45, height - 95, invoice.invoice_number)

    pdf.setFont("Helvetica", 10)
    pdf.drawRightString(width - 45, height - 115, f"Issue Date: {invoice.issue_date}")

    if invoice.due_date:
        pdf.drawRightString(width - 45, height - 133, f"Due Date: {invoice.due_date}")
    else:
        pdf.drawRightString(width - 45, height - 133, "Due Date: Not set")

    pdf.drawRightString(
        width - 45, height - 151, f"Status: {invoice.get_status_display()}"
    )

    # Divider
    pdf.line(45, height - 170, width - 45, height - 170)

    # Client information
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(45, height - 185, "CLIENT INFORMATION")

    pdf.setFont("Helvetica", 10)
    y = height - 205
    pdf.drawString(45, y, f"Name: {customer.full_name}")
    y -= 16
    pdf.drawString(45, y, f"Phone: {customer.phone}")
    y -= 16

    if customer.email:
        pdf.drawString(45, y, f"Email: {customer.email}")
        y -= 16

    if customer.address:
        pdf.drawString(45, y, f"Address: {customer.address}")

    # Job details
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(330, height - 185, "JOB DETAILS")

    pdf.setFont("Helvetica", 10)
    y2 = height - 205
    pdf.drawString(330, y2, f"Service: {booking.service_type}")
    y2 -= 16
    pdf.drawString(330, y2, f"Date: {booking.booking_date}")
    y2 -= 16
    pdf.drawString(330, y2, f"Time: {booking.booking_time}")
    y2 -= 16
    pdf.drawString(330, y2, f"Suburb: {booking.suburb_postcode}")
    y2 -= 16
    pdf.drawString(330, y2, f"Address: {booking.address[:38]}")

    # Table header
    table_top = height - 330

    pdf.setFillColorRGB(0.94, 0.96, 0.98)
    pdf.rect(45, table_top, width - 90, 28, fill=True, stroke=False)

    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(55, table_top + 9, "Description")
    pdf.drawRightString(385, table_top + 9, "Qty")
    pdf.drawRightString(470, table_top + 9, "Price")
    pdf.drawRightString(width - 55, table_top + 9, "Total")

    # Table row
    row_y = table_top - 32

    pdf.setFont("Helvetica", 10)
    pdf.drawString(55, row_y, booking.service_type[:45])
    pdf.drawRightString(385, row_y, "1")
    pdf.drawRightString(470, row_y, f"${invoice.amount}")
    pdf.drawRightString(width - 55, row_y, f"${invoice.amount}")

    pdf.line(45, row_y - 18, width - 45, row_y - 18)

    # Description
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(45, row_y - 55, "Description")

    pdf.setFont("Helvetica", 10)
    desc_y = row_y - 75

    description = invoice.description or "Cleaning service"

    for line in description.split("\n"):
        pdf.drawString(45, desc_y, line[:80])
        desc_y -= 14

        if desc_y < 180:
            break

    # Notes
    if invoice.notes:
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(45, 185, "Notes")

        pdf.setFont("Helvetica", 10)
        pdf.drawString(45, 168, invoice.notes[:85])

    # Totals
    totals_x_label = 360
    totals_x_value = width - 55

    discount_value = getattr(invoice, "discount_amount", 0)

    pdf.setFont("Helvetica", 11)
    pdf.drawString(totals_x_label, 190, "Subtotal:")
    pdf.drawRightString(totals_x_value, 190, f"${invoice.amount}")

    pdf.drawString(totals_x_label, 168, "Discount:")
    pdf.drawRightString(totals_x_value, 168, f"-${discount_value}")

    pdf.drawString(totals_x_label, 146, "GST 10%:")
    pdf.drawRightString(totals_x_value, 146, f"${invoice.gst_amount}")

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(totals_x_label, 112, "Total:")
    pdf.drawRightString(totals_x_value, 112, f"${invoice.total_amount}")

    # Footer
    pdf.line(45, 85, width - 45, 85)

    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(
        width / 2, 65, "Thank you for choosing YD Commercial Cleaning Services."
    )
    pdf.drawCentredString(
        width / 2, 50, "Professional Cleaning. Reliable Service. Spotless Results."
    )

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    return FileResponse(
        buffer, as_attachment=True, filename=f"{invoice.invoice_number}.pdf"
    )
