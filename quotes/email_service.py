from django.conf import settings
from django.core.mail import send_mail
import logging

logger = logging.getLogger(__name__)


def get_addons_text(quote):
    addons = []

    if quote.window_cleaning:
        addons.append("Window Cleaning (+$50)")

    if quote.carpet_shampooing:
        addons.append("Carpet Shampooing (+$100)")

    if quote.grout_cleaning:
        addons.append("Grout Cleaning (+$75)")

    if quote.upholstery_cleaning:
        addons.append("Upholstery Cleaning (+$60)")

    if quote.laundry_service:
        addons.append("Laundry Service (+$60)")

    if not addons:
        return "No add-ons selected"

    return "\n".join(addons)


def _send_email(subject, message, recipient):
    """
    Central email helper.

    Returns True when the email is accepted by the configured
    Django email backend, otherwise logs the error and returns False.
    """

    if not recipient:
        logger.error(
            "Email not sent: recipient address is empty."
        )
        return False

    try:
        sent = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )

        if sent:
            logger.info(
                "Email sent successfully to %s",
                recipient,
            )
            return True

        logger.warning(
            "Email backend returned 0 for %s",
            recipient,
        )
        return False

    except Exception:
        logger.exception(
            "Email delivery failed to %s",
            recipient,
        )
        return False


def send_customer_quote_email(quote):
    subject = (
        "Thank you for your quote request - "
        "YD Commercial Cleaning"
    )

    message = f"""
Hi {quote.name},

Thank you for contacting YD Commercial Cleaning Services.

We have received your quote request and our team will contact you shortly.

Your request details:

Name: {quote.name}
Phone: {quote.phone}
Email: {quote.email}
Property Type: {quote.property_type}
Suburb/Postcode: {quote.suburb_postcode}
Preferred Date: {quote.preferred_date}

Add-ons:
{get_addons_text(quote)}

Message:
{quote.message}

Thank you,
YD Commercial Cleaning Services
Phone: 0430 049 865
Website: https://ydcleaning.com.au
"""

    return _send_email(
        subject,
        message,
        quote.email,
    )


def send_admin_quote_email(quote):
    subject = f"New Quote Request - {quote.name}"

    message = f"""
New quote request received from the website.

Customer Details:

Name: {quote.name}
Phone: {quote.phone}
Email: {quote.email}
Property Type: {quote.property_type}
Suburb/Postcode: {quote.suburb_postcode}
Preferred Date: {quote.preferred_date}

Add-ons:
{get_addons_text(quote)}

Message:
{quote.message}

Login to Django Admin to view full details and uploaded images.
"""

    return _send_email(
        subject,
        message,
        settings.ADMIN_EMAIL,
    )