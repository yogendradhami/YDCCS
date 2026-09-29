from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.mail import send_mail
from django.utils.html import escape
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


def _send_email(subject, message, recipient, html_message=None):
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
        if html_message:
            email = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient],
            )
            email.attach_alternative(html_message, "text/html")
            sent = email.send(fail_silently=False)
        else:
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


def send_customer_quote_email(
    quote, *, service_name=None, source_page=None, submitted_at=None
):
    quick_quote = service_name is not None or source_page is not None
    subject = (
        "Your YD Commercial Cleaning quote request"
        if quick_quote
        else "Thank you for your quote request - YD Commercial Cleaning"
    )
    service_name = service_name or quote.message.partition(": ")[2] or "Cleaning service"

    message = f"""
Hi {quote.name},

Thank you for contacting YD Commercial Cleaning Services.

We have received your quote request and our team will contact you shortly.

Your request details:

Name: {quote.name}
Phone: {quote.phone}
Email: {quote.email}
Service: {service_name}
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

    html_message = _quote_email_html(
        "We have your request",
        "Thanks for contacting YD Commercial Cleaning. Our Adelaide team will review your details and contact you shortly.",
        quote,
        service_name,
    )

    return _send_email(
        subject,
        message,
        quote.email,
        html_message=html_message,
    )


def send_admin_quote_email(
    quote, *, service_name=None, source_page=None, submitted_at=None
):
    quick_quote = service_name is not None or source_page is not None
    subject = (
        f"New Quick Quote Request - {quote.name}"
        if quick_quote
        else f"New Quote Request - {quote.name}"
    )
    service_name = service_name or quote.message.partition(": ")[2] or "Cleaning service"

    message = f"""
{"NEW QUICK QUOTE REQUEST" if quick_quote else "New quote request received from the website."}

Customer Details:

Name: {quote.name}
Phone: {quote.phone}
Email: {quote.email}
Service: {service_name}
Property Type: {quote.property_type}
Suburb/Postcode: {quote.suburb_postcode}
Page submitted from: {source_page or 'Website'}
Submission time: {submitted_at or quote.created_at}
Preferred Date: {quote.preferred_date}

Add-ons:
{get_addons_text(quote)}

Message:
{quote.message}

Login to Django Admin to view full details and uploaded images.
"""

    html_message = _quote_email_html(
        "New Quick Quote Request",
        "A customer has submitted a quote request from the website.",
        quote,
        service_name,
        source_page=source_page,
        submitted_at=submitted_at,
        admin_notice=quick_quote,
    )

    return _send_email(
        subject,
        message,
        settings.ADMIN_EMAIL,
        html_message=html_message,
    )


def _quote_email_html(
    heading,
    introduction,
    quote,
    service_name,
    *,
    source_page=None,
    submitted_at=None,
    admin_notice=False,
):
    rows = [
        ("Name", quote.name),
        ("Phone", quote.phone),
        ("Email", quote.email),
        ("Service", service_name),
        ("Property type", quote.property_type),
        ("Suburb / postcode", quote.suburb_postcode),
    ]
    if admin_notice:
        rows.extend(
            [
                ("Page submitted from", source_page or "Website"),
                ("Submission time", submitted_at or quote.created_at),
            ]
        )

    table_rows = "".join(
        "<tr>"
        '<th align="left" style="padding:10px 12px;color:#53655e;border-bottom:1px solid #e6ebe8;font-size:13px">'
        f"{escape(label)}</th>"
        '<td style="padding:10px 12px;color:#14211d;border-bottom:1px solid #e6ebe8;font-size:14px">'
        f"{escape(value)}</td></tr>"
        for label, value in rows
    )
    admin_footer = (
        "<p style=\"margin:20px 0 0;color:#65716c;font-size:12px\">"
        "Open Django Admin to review and follow up on this request.</p>"
        if admin_notice
        else "<p style=\"margin:20px 0 0;color:#65716c;font-size:13px\">"
        "YD Commercial Cleaning Services<br>0430 049 865<br>"
        "<a href=\"https://ydcleaning.com.au\" style=\"color:#174b3d\">ydcleaning.com.au</a></p>"
    )
    return (
        '<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta charset="utf-8"></head>'
        '<body style="margin:0;padding:24px 12px;background:#f3f6f3;font-family:Arial,sans-serif;color:#14211d">'
        '<main style="max-width:600px;margin:0 auto;background:#fff;border:1px solid #e2e9e4;border-radius:8px;overflow:hidden">'
        '<header style="padding:22px 26px;background:#174b3d;color:#fff;font-size:15px;font-weight:700">'
        "YD Commercial Cleaning</header>"
        '<section style="padding:26px">'
        f'<h1 style="margin:0 0 12px;color:#0b2c24;font-size:23px;line-height:1.25">{escape(heading)}</h1>'
        f'<p style="margin:0 0 20px;color:#53655e;font-size:14px;line-height:1.6">{escape(introduction)}</p>'
        '<table role="presentation" style="width:100%;border-collapse:collapse">'
        f"{table_rows}</table>{admin_footer}</section></main></body></html>"
    )