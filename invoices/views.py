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
import json
from datetime import datetime, timezone as datetime_timezone
from decimal import Decimal

logger = logging.getLogger(__name__)

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import EmailMultiAlternatives
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .forms import InvoiceForm
from .forms import InvoiceWorkOrderFormSet
from .models import Invoice, StripeWebhookEvent
from .pdf_utils import generate_invoice_pdf
from .payment_links import (
    STRIPE_PAYMENT_LINK_SALT,
    get_invoice_payment_token,
    get_invoice_payment_url,
)

from django.db.models import Q, Sum

from bookings.models import Booking
from dashboard.decorators import admin_required
from dashboard.models import ActivityLog
from django.db import transaction
from django.db.models import Sum, Q
from dashboard.models import ActivityLog
from bookings.models import Booking
from customers.models import Customer
from google_reviews.calendar_utils import delete_booking_event, delete_roster_event
from .services import (
    create_booking_for_invoice,
    get_booking_work_order_initial,
    replace_invoice_work_orders,
)
from .stripe_service import (
    CheckoutSessionConflict,
    create_checkout_session,
    verify_webhook,
)

def get_accessible_invoice(request, invoice_id):
    invoice = get_object_or_404(
        Invoice.objects.select_related(
            "booking__customer"
        ),
        id=invoice_id,
    )

    if request.user.is_staff or request.user.is_superuser:
        return invoice

    if (
        invoice.booking.customer
        and invoice.booking.customer.user_id == request.user.id
    ):
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
        .prefetch_related("work_orders")
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
        .filter(status__in=["draft", "sent", "pending", "overdue"])
        .aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    overdue_invoices = (
        base_invoices
        .filter(Q(status="overdue") | Q(due_date__lt=today))
        .exclude(status__in=["paid", "cancelled"])
    )
    overdue_total = (
        overdue_invoices.aggregate(total=Sum("total_amount"))["total"] or 0
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
        "booking__customer__full_name",
        "booking__customer_id",
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
                        "pending",
                        "overdue",
                    ]
                )
                .count()
            ),

            "overdue_count": (
                overdue_invoices.count()
            ),
        },
    }

    return render(
        request,
        "invoices/invoice_list.html",
        context,
    )

def _booking_work_orders_json():
    bookings = Booking.objects.prefetch_related("work_orders").order_by(
        "-booking_date", "-booking_time"
    )
    return json.dumps(
        {
            str(booking.pk): [
                {
                    "description": item["description"],
                    "price": str(item["price"]),
                }
                for item in get_booking_work_order_initial(booking)
            ]
            for booking in bookings
        }
    )


def _invoice_work_order_initial(invoice):
    line_items = list(invoice.work_orders.all())
    if line_items:
        return [
            {"description": item.description, "price": item.price}
            for item in line_items
        ]
    return [
        {
            "description": invoice.booking.service_type,
            "price": invoice.amount,
        }
    ]


@login_required
def create_invoice(request):
    work_order_prefix = "work_orders"
    if request.method == "POST":
        form = InvoiceForm(request.POST)
        work_order_formset = (
            InvoiceWorkOrderFormSet(request.POST, prefix=work_order_prefix)
            if f"{work_order_prefix}-TOTAL_FORMS" in request.POST
            else None
        )

        if form.is_valid():
            booking = form.cleaned_data["booking"]
            if work_order_formset is None:
                work_orders = get_booking_work_order_initial(booking)
                if not booking.work_orders.exists():
                    work_orders = [
                        {
                            "description": (
                                form.cleaned_data["description"]
                                or booking.service_type
                            ),
                            "price": form.cleaned_data["amount"],
                        }
                    ]
            elif work_order_formset.is_valid():
                work_orders = [
                    {
                        "description": item["description"],
                        "price": item["price"],
                    }
                    for item in work_order_formset.cleaned_data
                    if item and item.get("description") and not item.get("DELETE")
                ]
            else:
                work_orders = []

            if work_orders:
                with transaction.atomic():
                    source_booking = Booking.objects.select_for_update().get(
                        pk=booking.pk
                    )
                    invoice = form.save(commit=False)
                    invoice.amount = sum(
                        (item["price"] for item in work_orders),
                        Decimal("0.00"),
                    )
                    quoted_price = max(
                        invoice.amount - invoice.discount_amount,
                        Decimal("0.00"),
                    )
                    invoice.booking = create_booking_for_invoice(
                        source_booking,
                        work_orders,
                        quoted_price,
                    )
                    invoice.save()
                    replace_invoice_work_orders(invoice, work_orders)

                if request.POST.get("send_invoice_email") == "on":
                    from dashboard.views import send_invoice_email

                    if send_invoice_email(request, invoice):
                        messages.success(
                            request,
                            (
                                f"Invoice {invoice.invoice_number} created and emailed "
                                f"to {invoice.booking.customer.email}."
                            ),
                        )
                    else:
                        messages.warning(
                            request,
                            (
                                f"Invoice {invoice.invoice_number} was created, but the "
                                "customer email could not be sent. Check the customer's "
                                "email address and mail service settings."
                            ),
                        )
                else:
                    messages.success(
                        request,
                        (
                            f"Invoice {invoice.invoice_number} was created. "
                            "No email was sent. You can choose email delivery when "
                            "creating another invoice."
                        ),
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
        selected_booking = None
        booking_id = request.GET.get("booking") or request.GET.get("booking_id")
        if booking_id:
            selected_booking = get_object_or_404(Booking, pk=booking_id)
        initial = {}
        if selected_booking:
            initial_work_orders = get_booking_work_order_initial(selected_booking)
            initial.update(
                booking=selected_booking.pk,
                amount=sum(
                    (item["price"] for item in initial_work_orders),
                    Decimal("0.00"),
                ),
                description=selected_booking.service_type,
            )
            work_order_formset = InvoiceWorkOrderFormSet(
                prefix=work_order_prefix,
                initial=initial_work_orders,
            )
        else:
            work_order_formset = InvoiceWorkOrderFormSet(
                prefix=work_order_prefix,
                initial=[{"description": "", "price": Decimal("0.00")}],
            )
        form = InvoiceForm(initial=initial)

    if work_order_formset is None:
        work_order_formset = InvoiceWorkOrderFormSet(
            prefix=work_order_prefix,
            initial=[
                {
                    "description": request.POST.get("description", ""),
                    "price": request.POST.get("amount", ""),
                }
            ],
        )

    return render(
        request,
        "invoices/invoice_form.html",
        {
            "form": form,
            "work_order_formset": work_order_formset,
            "booking_work_orders_json": _booking_work_orders_json(),
            "is_edit": False,
            "send_invoice_email_requested": (
                request.method == "POST"
                and request.POST.get("send_invoice_email") == "on"
            ),
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
    original_status = invoice.status

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
        work_order_formset = (
            InvoiceWorkOrderFormSet(request.POST, prefix="work_orders")
            if "work_orders-TOTAL_FORMS" in request.POST
            else None
        )

        if form.is_valid():
            if work_order_formset is None:
                work_orders = _invoice_work_order_initial(invoice)
            elif work_order_formset.is_valid():
                work_orders = [
                    {
                        "description": item["description"],
                        "price": item["price"],
                    }
                    for item in work_order_formset.cleaned_data
                    if item and item.get("description") and not item.get("DELETE")
                ]
            else:
                work_orders = []

            if work_orders:
                with transaction.atomic():
                    updated_invoice = form.save(commit=False)
                    updated_invoice.amount = sum(
                        (item["price"] for item in work_orders),
                        Decimal("0.00"),
                    )
                    updated_invoice.save()
                    replace_invoice_work_orders(updated_invoice, work_orders)
            else:
                form.add_error(None, "Add at least one invoice work order.")
                updated_invoice = None

            if updated_invoice:
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
                    logger.exception(
                        "Could not log changes to invoice %s.",
                        updated_invoice.pk,
                    )

                messages.success(
                    request,
                    (
                        f"Invoice "
                        f"{updated_invoice.invoice_number} "
                        "updated successfully."
                    ),
                )

                if updated_invoice.status != original_status:
                    return redirect("invoice_list")
                return redirect("invoice_detail", invoice_id=updated_invoice.id)

        messages.error(
            request,
            "Please correct the highlighted invoice fields.",
        )

    else:
        form = InvoiceForm(
            instance=invoice
        )
        work_order_formset = InvoiceWorkOrderFormSet(
            prefix="work_orders",
            initial=_invoice_work_order_initial(invoice),
        )

    if work_order_formset is None:
        work_order_formset = InvoiceWorkOrderFormSet(
            prefix="work_orders",
            initial=_invoice_work_order_initial(invoice),
        )

    return render(
        request,
        "invoices/invoice_form.html",
        {
            "form": form,
            "work_order_formset": work_order_formset,
            "booking_work_orders_json": _booking_work_orders_json(),
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
        invoice.save()
        messages.info(
            request,
            f"Invoice {invoice.invoice_number} is already marked as paid. "
            "Booking completion has been synchronised.",
        )
        return redirect("invoice_list")

    invoice.status = "paid"
    invoice.paid_at = timezone.now()
    invoice.save()

    messages.success(
        request,
        f"Invoice {invoice.invoice_number} marked as paid. No email was sent.",
    )

    return redirect("invoice_list")


@login_required
@admin_required
@require_POST
def mark_invoice_unpaid(request, invoice_id):
    invoice = get_object_or_404(
        Invoice.objects.select_related("booking__customer"),
        id=invoice_id,
    )

    if invoice.status != "paid":
        messages.info(
            request,
            f"Invoice {invoice.invoice_number} is not marked as paid.",
        )
        return redirect("invoice_list")

    invoice.status = (
        "overdue"
        if invoice.due_date and invoice.due_date < timezone.localdate()
        else "sent"
    )
    invoice.paid_at = None
    invoice.save()

    try:
        ActivityLog.objects.create(
            user=request.user,
            action_type="invoice",
            title="Invoice Marked Unpaid",
            description=(
                f"{invoice.invoice_number} was marked unpaid by "
                f"{request.user.get_username()}."
            ),
        )
    except Exception:
        logger.exception(
            "Could not log invoice %s being marked unpaid.",
            invoice.invoice_number,
        )

    messages.success(
        request,
        f"Invoice {invoice.invoice_number} marked as {invoice.get_status_display()}. "
        "This does not refund or reverse a Stripe payment.",
    )
    return redirect("invoice_list")


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

        return redirect("invoice_list")

    if invoice.status == "cancelled":

        messages.info(
            request,
            "This invoice is already cancelled.",
        )

        return redirect("invoice_list")

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
    invoice = get_object_or_404(Invoice, id=invoice_id)

    if invoice.status not in {"draft", "cancelled"}:
        messages.error(
            request,
            (
                "Only draft or cancelled invoices can be permanently deleted. "
                "Issued financial records should be cancelled instead."
            ),
        )
        return redirect("invoice_detail", invoice_id=invoice.id)

    invoice_number = invoice.invoice_number
    invoice.delete()

    ActivityLog.objects.create(
        user=request.user,
        action_type="invoice",
        title="Invoice Deleted",
        description=f"{invoice_number} was permanently deleted.",
    )
    messages.success(request, f"Invoice {invoice_number} deleted successfully.")
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
            "payment_url": get_invoice_payment_url(invoice),
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
        messages.info(request, "This invoice has already been paid.")
        return redirect(invoice_detail_redirect_name(request.user), invoice_id=invoice.id)
    if invoice.status == "cancelled":
        messages.error(request, "Cancelled invoices cannot be paid.")
        return redirect(invoice_detail_redirect_name(request.user), invoice_id=invoice.id)

    is_portal = hasattr(request.user, "customer_profile")
    cancel_name = (
        "portal_stripe_payment_cancel" if is_portal else "stripe_payment_cancel"
    )
    base_url = settings.SITE_URL.rstrip("/")
    return_token = get_invoice_payment_token(invoice)
    success_url = (
        f"{base_url}"
        f"{reverse('stripe_payment_return', kwargs={'token': return_token})}"
        "?session_id={CHECKOUT_SESSION_ID}"
    )
    cancel_url = (
        f"{base_url}{reverse(cancel_name, kwargs={'invoice_id': invoice.id})}"
    )

    try:
        checkout_session = create_checkout_session(invoice, success_url, cancel_url)
    except (CheckoutSessionConflict, ValidationError) as exc:
        messages.error(request, str(exc))
        return redirect(invoice_detail_redirect_name(request.user), invoice_id=invoice.id)
    except stripe.error.StripeError:
        logger.exception("Stripe Checkout creation failed for invoice=%s", invoice.pk)
        messages.error(request, "Payment could not be started. Please try again later.")
        return redirect(invoice_detail_redirect_name(request.user), invoice_id=invoice.id)

    return redirect(checkout_session.url)


def stripe_pay_invoice_link(request, token):
    try:
        invoice_id = signing.Signer(salt=STRIPE_PAYMENT_LINK_SALT).unsign(token)
    except signing.BadSignature:
        return HttpResponse("This payment link is invalid.", status=400)
    invoice = get_object_or_404(
        Invoice.objects.select_related("booking__customer"),
        pk=invoice_id,
    )
    if invoice.status == "paid":
        return HttpResponse("This invoice has already been paid.", status=200)
    if invoice.status == "cancelled":
        return HttpResponse("Cancelled invoices cannot be paid.", status=400)

    success_url = (
        f"{settings.SITE_URL.rstrip('/')}"
        f"{reverse('stripe_payment_return', kwargs={'token': get_invoice_payment_token(invoice)})}"
        "?session_id={CHECKOUT_SESSION_ID}"
    )
    cancel_url = (
        f"{settings.SITE_URL.rstrip('/')}"
        f"{reverse('stripe_payment_cancel_return', kwargs={'token': token})}"
    )
    try:
        session = create_checkout_session(invoice, success_url, cancel_url)
    except (CheckoutSessionConflict, ValidationError) as exc:
        return HttpResponse(str(exc), status=409)
    except stripe.error.StripeError:
        logger.exception("Stripe Checkout creation failed for invoice=%s", invoice.pk)
        return HttpResponse(
            "Payment could not be started. Please contact YD Commercial Cleaning Services.",
            status=502,
        )
    return redirect(session.url)


@login_required
def stripe_payment_success(request, invoice_id):
    invoice = get_accessible_invoice(
        request,
        invoice_id,
    )
    if invoice.status == "paid":
        messages.success(request, "Payment confirmed. Thank you.")
    else:
        messages.info(
            request,
            "Thank you. Your payment is being verified; the invoice will update once confirmed.",
        )
    return redirect(
        invoice_detail_redirect_name(request.user),
        invoice_id=invoice.id,
    )


def stripe_payment_return(request, token):
    try:
        signing.Signer(salt=STRIPE_PAYMENT_LINK_SALT).unsign(token)
    except signing.BadSignature:
        return HttpResponse("This payment link is invalid.", status=400)
    return HttpResponse(
        "Thank you. Your payment is being verified. "
        "The invoice will update after Stripe confirms payment."
    )


def stripe_payment_cancel_return(request, token):
    try:
        signing.Signer(salt=STRIPE_PAYMENT_LINK_SALT).unsign(token)
    except signing.BadSignature:
        return HttpResponse("This payment link is invalid.", status=400)
    return HttpResponse(
        "Payment was cancelled and has not been recorded. "
        "You can return to your invoice payment link to try again."
    )


def _send_stripe_payment_confirmation(invoice):
    customer = invoice.booking.customer
    if not customer or not customer.email:
        logger.warning(
            "Payment confirmation not emailed: invoice=%s has no customer email",
            invoice.invoice_number,
        )
        invoice.payment_confirmation_email_sent = True
        invoice.save(update_fields=["payment_confirmation_email_sent"])
        return

    invoice_url = get_invoice_payment_url(invoice)
    context = {
        "invoice": invoice,
        "customer": customer,
        "invoice_url": invoice_url,
    }
    html_body = render_to_string("emails/invoices/payment_received.html", context)
    email = EmailMultiAlternatives(
        subject=f"Payment received for invoice {invoice.invoice_number}",
        body=(
            f"Hi {customer.full_name}, payment for invoice "
            f"{invoice.invoice_number} has been received. Thank you."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[customer.email],
    )
    email.attach_alternative(html_body, "text/html")
    pdf_buffer = generate_invoice_pdf(invoice, payment_url=invoice_url)
    email.attach(
        f"{invoice.invoice_number}.pdf",
        pdf_buffer.getvalue(),
        "application/pdf",
    )
    email.send(fail_silently=False)
    invoice.payment_confirmation_email_sent = True
    invoice.save(update_fields=["payment_confirmation_email_sent"])


@csrf_exempt
@require_POST
def stripe_webhook(request):
    try:
        event = verify_webhook(
            request.body,
            request.headers.get("Stripe-Signature", ""),
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        logger.warning("Rejected Stripe webhook with invalid signature")
        return HttpResponse(status=400)
    except ValidationError:
        logger.exception("Stripe webhook signing is not configured")
        return HttpResponse(status=503)

    event_id = event.get("id")
    event_type = event.get("type")
    if not event_id or not event_type:
        logger.warning("Rejected verified Stripe webhook without event identity")
        return HttpResponse(status=400)

    try:
        with transaction.atomic():
            webhook_event, created = StripeWebhookEvent.objects.get_or_create(
                event_id=event_id,
                defaults={"event_type": event_type},
            )
            if not created:
                return HttpResponse(status=200)

            if event_type in {
                "checkout.session.completed",
                "checkout.session.async_payment_succeeded",
                "checkout.session.async_payment_failed",
                "checkout.session.expired",
            }:
                session = event.get("data", {}).get("object", {})
                metadata = session.get("metadata") or {}
                invoice_id = metadata.get("invoice_id")
                invoice = (
                    Invoice.objects.select_for_update()
                    .select_related("booking__customer")
                    .filter(pk=invoice_id)
                    .first()
                    if isinstance(invoice_id, str) and invoice_id.isdigit()
                    else None
                )
                if invoice is None:
                    logger.error(
                        "Stripe event=%s references unknown invoice id=%s",
                        event_id,
                        invoice_id,
                    )
                elif event_type in {
                    "checkout.session.async_payment_failed",
                    "checkout.session.expired",
                }:
                    session_id = session.get("id")
                    valid_session = (
                        session_id == invoice.stripe_checkout_session_id
                        and metadata.get("invoice_number") == invoice.invoice_number
                        and session.get("client_reference_id") == str(invoice.pk)
                    )
                    if valid_session and invoice.status == "pending":
                        retry_status = (
                            "overdue"
                            if invoice.due_date
                            and invoice.due_date < timezone.localdate()
                            else "sent"
                        )
                        Invoice.objects.filter(
                            pk=invoice.pk,
                            status="pending",
                            stripe_checkout_session_id=session_id,
                        ).update(
                            status=retry_status,
                            stripe_checkout_session_id="",
                            stripe_checkout_idempotency_key="",
                        )
                        logger.info(
                            "Stripe Checkout %s for invoice=%s; invoice is available for retry",
                            event_type.rsplit(".", 1)[-1],
                            invoice.pk,
                        )
                    elif not valid_session:
                        logger.error(
                            "Stripe event=%s failed invoice/session validation: "
                            "invoice=%s session=%s",
                            event_id,
                            invoice.pk,
                            session_id,
                        )
                else:
                    amount_total = session.get("amount_total")
                    expected_amount = int(invoice.total_amount * 100)
                    payment_intent = session.get("payment_intent")
                    if not isinstance(payment_intent, str):
                        payment_intent = getattr(payment_intent, "id", "") or ""
                    valid_session = (
                        session.get("id") == invoice.stripe_checkout_session_id
                        and metadata.get("invoice_number") == invoice.invoice_number
                        and session.get("client_reference_id") == str(invoice.pk)
                        and session.get("mode") == "payment"
                        and (session.get("currency") or "").lower() == "aud"
                        and amount_total == expected_amount
                    )
                    if not valid_session:
                        logger.error(
                            "Stripe event=%s failed invoice/session validation: "
                            "invoice=%s session=%s",
                            event_id,
                            invoice.pk,
                            session.get("id"),
                        )
                    elif session.get("payment_status") == "paid":
                        if invoice.status == "cancelled":
                            logger.error(
                                "Paid Stripe session received for cancelled invoice=%s",
                                invoice.pk,
                            )
                        else:
                            if invoice.status != "paid":
                                invoice.status = "paid"
                            if not invoice.paid_at:
                                invoice.paid_at = datetime.fromtimestamp(
                                    event.get("created", timezone.now().timestamp()),
                                    tz=datetime_timezone.utc,
                                )
                            invoice.stripe_payment_intent_id = payment_intent
                            methods = session.get("payment_method_types") or []
                            invoice.payment_method = (
                                f"Stripe ({methods[0]})" if methods else "Stripe"
                            )[:50]
                            invoice.save(
                                update_fields=[
                                    "status",
                                    "paid_at",
                                    "stripe_payment_intent_id",
                                    "payment_method",
                                ]
                            )
                            if not invoice.payment_confirmation_email_sent:
                                _send_stripe_payment_confirmation(invoice)
                    else:
                        logger.info(
                            "Stripe event=%s not paid; invoice=%s remains unpaid",
                            event_id,
                            invoice.pk,
                        )

            webhook_event.processed_at = timezone.now()
            webhook_event.save(update_fields=["processed_at"])
    except Exception:
        logger.exception("Stripe webhook processing failed: event=%s", event_id)
        return HttpResponse(status=500)

    return HttpResponse(status=200)


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
    invoice = get_accessible_invoice(request, invoice_id)
    pdf_buffer = generate_invoice_pdf(invoice)
    return FileResponse(
        pdf_buffer,
        as_attachment=True,
        filename=f"{invoice.invoice_number}.pdf",
        content_type="application/pdf",
    )

@login_required
@require_POST
@admin_required
def delete_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)

    if invoice.status not in {"draft", "cancelled"}:
        messages.error(
            request,
            (
                "Only draft or cancelled invoices can be permanently deleted. "
                "Issued financial records should be cancelled instead."
            ),
        )
        return redirect("invoice_detail", invoice_id=invoice.id)

    invoice_number = invoice.invoice_number
    invoice.delete()

    ActivityLog.objects.create(
        user=request.user,
        action_type="invoice",
        title="Invoice Deleted",
        description=f"{invoice_number} was permanently deleted.",
    )
    messages.success(request, f"Invoice {invoice_number} deleted successfully.")
    return redirect("invoice_list")
