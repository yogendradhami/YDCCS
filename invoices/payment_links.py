from django.conf import settings
from django.core import signing
from django.urls import reverse


STRIPE_PAYMENT_LINK_SALT = "invoices.stripe-payment"


def get_invoice_payment_token(invoice):
    return signing.Signer(salt=STRIPE_PAYMENT_LINK_SALT).sign(str(invoice.pk))


def get_invoice_id_from_payment_token(token):
    try:
        invoice_id = signing.loads(token, salt=STRIPE_PAYMENT_LINK_SALT)
    except (signing.BadSignature, ValueError):
        try:
            invoice_id = signing.Signer(salt=STRIPE_PAYMENT_LINK_SALT).unsign(token)
        except signing.BadSignature as exc:
            raise ValueError("Invalid invoice payment link.") from exc

    invoice_id = str(invoice_id)
    if not invoice_id.isdecimal():
        raise ValueError("Invalid invoice payment link.")
    return invoice_id


def get_invoice_payment_url(invoice):
    token = get_invoice_payment_token(invoice)
    return (
        f"{settings.SITE_URL.rstrip('/')}"
        f"{reverse('invoice_stripe_pay_link', kwargs={'token': token})}"
    )
