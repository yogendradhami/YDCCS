import uuid
from decimal import Decimal

import stripe
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Invoice


class CheckoutSessionConflict(Exception):
    pass


def _retrieve_checkout_session(session_id):
    try:
        return stripe.checkout.Session.retrieve(session_id)
    except stripe.error.InvalidRequestError as exc:
        if exc.code == "resource_missing":
            return None
        raise


def create_checkout_session(invoice, success_url, cancel_url):
    if not settings.STRIPE_SECRET_KEY:
        raise ValidationError("Stripe payments are not configured.")
    if invoice.status in {"paid", "cancelled"}:
        raise ValidationError("This invoice is not eligible for payment.")
    if invoice.total_amount <= Decimal("0.00"):
        raise ValidationError("The invoice total must be greater than zero.")

    currency = settings.STRIPE_CURRENCY.lower()
    if currency != "aud":
        raise ValidationError("Invoice payments must be configured in AUD.")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    with transaction.atomic():
        locked_invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
        if locked_invoice.status in {"paid", "cancelled"}:
            raise ValidationError("This invoice is not eligible for payment.")

        if locked_invoice.stripe_checkout_session_id:
            existing = _retrieve_checkout_session(
                locked_invoice.stripe_checkout_session_id,
            )
            if existing and existing.status == "open":
                return existing
            if existing and existing.status != "expired":
                raise CheckoutSessionConflict(
                    "This invoice already has a completed or active payment session."
                )
            locked_invoice.stripe_checkout_session_id = ""
            locked_invoice.stripe_checkout_idempotency_key = ""

        if not locked_invoice.stripe_checkout_idempotency_key:
            locked_invoice.stripe_checkout_idempotency_key = str(uuid.uuid4())
            Invoice.objects.filter(pk=locked_invoice.pk).update(
                stripe_checkout_session_id="",
                stripe_checkout_idempotency_key=(
                    locked_invoice.stripe_checkout_idempotency_key
                )
            )

        invoice_id = locked_invoice.pk
        idempotency_key = locked_invoice.stripe_checkout_idempotency_key

    with transaction.atomic():
        locked_invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
        if locked_invoice.status in {"paid", "cancelled"}:
            raise ValidationError("This invoice is not eligible for payment.")
        if locked_invoice.stripe_checkout_idempotency_key != idempotency_key:
            raise CheckoutSessionConflict(
                "The invoice payment session changed while Checkout was starting."
            )
        if locked_invoice.stripe_checkout_session_id:
            existing = _retrieve_checkout_session(
                locked_invoice.stripe_checkout_session_id,
            )
            if existing and existing.status == "open":
                return existing
            if existing and existing.status != "expired":
                raise CheckoutSessionConflict(
                    "This invoice already has a completed or active payment session."
                )
            locked_invoice.stripe_checkout_session_id = ""
            locked_invoice.stripe_checkout_idempotency_key = str(uuid.uuid4())
            idempotency_key = locked_invoice.stripe_checkout_idempotency_key
            Invoice.objects.filter(pk=locked_invoice.pk).update(
                stripe_checkout_session_id="",
                stripe_checkout_idempotency_key=idempotency_key,
            )

        customer = locked_invoice.booking.customer
        session = stripe.checkout.Session.create(
            mode="payment",
            customer_email=(customer.email or None) if customer else None,
            line_items=[
                {
                    "price_data": {
                        "currency": currency,
                        "product_data": {
                            "name": f"Invoice {locked_invoice.invoice_number}",
                            "description": locked_invoice.description,
                        },
                        "unit_amount": int(locked_invoice.total_amount * 100),
                    },
                    "quantity": 1,
                }
            ],
            metadata={
                "invoice_id": str(invoice_id),
                "invoice_number": locked_invoice.invoice_number,
            },
            client_reference_id=str(invoice_id),
            success_url=success_url,
            cancel_url=cancel_url,
            idempotency_key=f"invoice-{invoice_id}-{idempotency_key}",
        )
        Invoice.objects.filter(pk=locked_invoice.pk).update(
            stripe_checkout_session_id=session.id,
            status=(
                "pending"
                if locked_invoice.status in {"draft", "sent", "overdue"}
                else locked_invoice.status
            ),
        )
        invoice.stripe_checkout_session_id = session.id
        invoice.stripe_checkout_idempotency_key = (
            locked_invoice.stripe_checkout_idempotency_key
        )
        if locked_invoice.status in {"draft", "sent", "overdue"}:
            invoice.status = "pending"
        return session


def verify_webhook(payload, signature):
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise ValidationError("Stripe webhook signing is not configured.")
    return stripe.Webhook.construct_event(
        payload=payload,
        sig_header=signature,
        secret=settings.STRIPE_WEBHOOK_SECRET,
    )
