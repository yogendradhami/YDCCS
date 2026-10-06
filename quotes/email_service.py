from datetime import datetime

import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.utils.html import escape
from django.utils.timezone import localtime, now


logger = logging.getLogger(__name__)


# ============================================================
# YD COMMERCIAL CLEANING
# EMAIL BRAND CONFIGURATION
# ============================================================

BUSINESS_NAME = "YD Commercial Cleaning Services"
BUSINESS_SHORT_NAME = "YD Commercial Cleaning"

BUSINESS_PHONE = "0430 049 865"
BUSINESS_PHONE_TEL = "+61430049865"

BUSINESS_WEBSITE = "https://www.ydcleaning.com.au"

BUSINESS_LOGO_URL = (
    "https://www.ydcleaning.com.au/static/"
    "images/branding/yd-email-logo.jpeg"
)

BUSINESS_EMAIL = getattr(
    settings,
    "DEFAULT_FROM_EMAIL",
    "info@ydcleaning.com.au",
)


# ============================================================
# BRAND COLOURS
# ============================================================

PRIMARY_GREEN = "#174b3d"
DARK_GREEN = "#0b2c24"
LIGHT_GREEN = "#e8f2ed"

TEXT_DARK = "#14211d"
TEXT_MUTED = "#5f6f68"

BACKGROUND = "#f3f6f4"
CARD_BACKGROUND = "#ffffff"
SOFT_BACKGROUND = "#f7faf8"

BORDER = "#e3ebe6"
WHITE = "#ffffff"


# ============================================================
# ADD-ONS
# ============================================================

ADDON_PRICES = {
    "window_cleaning": 50,
    "carpet_shampooing": 100,
    "grout_cleaning": 75,
    "upholstery_cleaning": 60,
    "laundry_service": 60,
}


ADDON_LABELS = {
    "window_cleaning": "Window Cleaning",
    "carpet_shampooing": "Carpet Shampooing",
    "grout_cleaning": "Grout Cleaning",
    "upholstery_cleaning": "Upholstery Cleaning",
    "laundry_service": "Laundry Service",
}


# ============================================================
# BASIC HELPERS
# ============================================================

def _safe(value, fallback="—"):
    """
    Convert a value to safe readable text.
    """

    if value is None:
        return fallback

    value = str(value).strip()

    return value if value else fallback


def _escape(value, fallback="—"):
    """
    HTML-escape customer/database values.
    """

    return escape(
        _safe(
            value,
            fallback=fallback,
        )
    )


def _is_valid_email(email):
    """
    Validate an email address.
    """

    if not email:
        return False

    try:
        validate_email(str(email).strip())
        return True

    except ValidationError:
        return False


# ============================================================
# DATE FORMATTING
# ============================================================

def _format_date(value):
    """
    Format dates for customer-facing emails.
    """

    if not value:
        return "Not specified"

    try:

        if isinstance(value, datetime):

            value = localtime(value)

            return value.strftime(
                "%A, %d %B %Y at %I:%M %p"
            )

        return value.strftime(
            "%A, %d %B %Y"
        )

    except (
        AttributeError,
        TypeError,
        ValueError,
    ):

        return str(value)


def _format_submission_time(value):
    """
    Format lead submission timestamp.
    """

    if not value:
        value = now()

    try:

        value = localtime(value)

        return value.strftime(
            "%d %B %Y at %I:%M %p"
        )

    except (
        AttributeError,
        TypeError,
        ValueError,
    ):

        return str(value)


# ============================================================
# QUOTE REFERENCE
# ============================================================

def _get_quote_reference(quote):
    """
    Generate a readable quote reference.

    Example:

        YD-Q-20260930-00025
    """

    quote_id = getattr(
        quote,
        "pk",
        None,
    )

    created_at = getattr(
        quote,
        "created_at",
        None,
    )

    if created_at:

        try:
            date_part = localtime(
                created_at
            ).strftime("%Y%m%d")

        except (
            AttributeError,
            TypeError,
            ValueError,
        ):
            date_part = now().strftime(
                "%Y%m%d"
            )

    else:
        date_part = now().strftime(
            "%Y%m%d"
        )

    if quote_id:

        try:
            return (
                f"YD-Q-{date_part}-"
                f"{int(quote_id):05d}"
            )

        except (
            TypeError,
            ValueError,
        ):
            pass

    return (
        f"YD-Q-{now().strftime('%Y%m%d%H%M%S')}"
    )


# ============================================================
# SERVICE NAME
# ============================================================

def _get_service_name(
    quote,
    service_name=None,
):
    """
    Resolve service name.

    Priority:

    1. Explicit service_name
    2. quote.service_name
    3. quote.service
    4. Cleaning service
    """

    if service_name:

        return str(
            service_name
        ).strip()

    for field_name in (
        "service_name",
        "service",
    ):

        value = getattr(
            quote,
            field_name,
            None,
        )

        if value:

            return str(
                value
            ).strip()

    return "Cleaning service"


# ============================================================
# ADD-ON FUNCTIONS
# ============================================================

def get_addons(quote):
    """
    Return selected add-ons.
    """

    addons = []

    for (
        field_name,
        price,
    ) in ADDON_PRICES.items():

        if getattr(
            quote,
            field_name,
            False,
        ):

            addons.append(
                {
                    "key": field_name,
                    "name": ADDON_LABELS[
                        field_name
                    ],
                    "price": price,
                }
            )

    return addons


def get_addons_text(quote):
    """
    Plain-text add-on list.
    """

    addons = get_addons(quote)

    if not addons:
        return "No add-ons selected"

    return "\n".join(
        f"- {addon['name']} (+${addon['price']})"
        for addon in addons
    )


def get_addons_total(quote):
    """
    Calculate selected add-on total.
    """

    return sum(
        addon["price"]
        for addon in get_addons(quote)
    )


# ============================================================
# CENTRAL EMAIL SENDER
# ============================================================

def _send_email(
    subject,
    message,
    recipient,
    html_message=None,
    *,
    reply_to=None,
):
    """
    Central email sending helper.

    Returns:

        True
            Email accepted by Django backend.

        False
            Email failed.
    """

    if not recipient:

        logger.error(
            "Email not sent: recipient is empty. "
            "subject=%s",
            subject,
        )

        return False

    recipient = str(
        recipient
    ).strip()

    if not _is_valid_email(
        recipient
    ):

        logger.error(
            "Email not sent: invalid recipient=%s "
            "subject=%s",
            recipient,
            subject,
        )

        return False

    try:

        email_kwargs = {
            "subject": subject,
            "body": message,
            "from_email": BUSINESS_EMAIL,
            "to": [recipient],
        }

        if (
            reply_to
            and _is_valid_email(reply_to)
        ):

            email_kwargs[
                "reply_to"
            ] = [
                str(
                    reply_to
                ).strip()
            ]

        email = EmailMultiAlternatives(
            **email_kwargs
        )

        if html_message:

            email.attach_alternative(
                html_message,
                "text/html",
            )

        sent = email.send(
            fail_silently=False
        )

        if sent:

            logger.info(
                "Email sent successfully. "
                "recipient=%s subject=%s",
                recipient,
                subject,
            )

            return True

        logger.warning(
            "Email backend returned 0. "
            "recipient=%s subject=%s",
            recipient,
            subject,
        )

        return False

    except Exception:

        logger.exception(
            "Email delivery failed. "
            "recipient=%s subject=%s",
            recipient,
            subject,
        )

        return False


# ============================================================
# CUSTOMER QUOTE EMAIL
# ============================================================

def send_customer_quote_email(
    quote,
    *,
    service_name=None,
    source_page=None,
    submitted_at=None,
):
    """
    Send quote confirmation to customer.
    """

    customer_name = _safe(
        getattr(
            quote,
            "name",
            None,
        ),
        fallback="there",
    )

    customer_email = getattr(
        quote,
        "email",
        None,
    )

    resolved_service = _get_service_name(
        quote,
        service_name,
    )

    reference = _get_quote_reference(
        quote
    )

    preferred_date = _format_date(
        getattr(
            quote,
            "preferred_date",
            None,
        )
    )

    property_type = _safe(
        getattr(
            quote,
            "property_type",
            None,
        )
    )

    suburb_postcode = _safe(
        getattr(
            quote,
            "suburb_postcode",
            None,
        )
    )

    customer_message = _safe(
        getattr(
            quote,
            "message",
            None,
        ),
        fallback="No additional message provided.",
    )

    subject = (
        "Quote Request Received — "
        f"{BUSINESS_SHORT_NAME} "
        f"({reference})"
    )

    # --------------------------------------------------------
    # PLAIN TEXT
    # --------------------------------------------------------

    text_message = f"""
Hi {customer_name},

Thank you for contacting {BUSINESS_NAME}.

We have successfully received your cleaning quote request.

QUOTE REFERENCE
{reference}

YOUR REQUEST
----------------------------------------
Service: {resolved_service}
Property Type: {property_type}
Suburb / Postcode: {suburb_postcode}
Preferred Date: {preferred_date}

ADDITIONAL SERVICES
----------------------------------------
{get_addons_text(quote)}

YOUR MESSAGE
----------------------------------------
{customer_message}

WHAT HAPPENS NEXT
----------------------------------------
1. Our team will review your request.
2. We will contact you to confirm the details.
3. We will discuss availability and pricing with you.

If your request is urgent, please call:

{BUSINESS_PHONE}

{BUSINESS_NAME}
{BUSINESS_PHONE}
{BUSINESS_WEBSITE}

Thank you for choosing YD Commercial Cleaning Services.
""".strip()

    # --------------------------------------------------------
    # HTML
    # --------------------------------------------------------

    html_message = _customer_quote_email_html(
        quote=quote,
        customer_name=customer_name,
        service_name=resolved_service,
        reference=reference,
        preferred_date=preferred_date,
        property_type=property_type,
        suburb_postcode=suburb_postcode,
        customer_message=customer_message,
    )

    return _send_email(
        subject=subject,
        message=text_message,
        recipient=customer_email,
        html_message=html_message,
    )


# ============================================================
# CUSTOMER EMAIL HTML
# ============================================================

def _customer_quote_email_html(
    *,
    quote,
    customer_name,
    service_name,
    reference,
    preferred_date,
    property_type,
    suburb_postcode,
    customer_message,
):
    """
    Premium customer-facing quote email.
    """

    addons = get_addons(
        quote
    )

    if addons:

        addon_rows = ""

        for addon in addons:

            addon_rows += f"""
            <tr>

                <td style="
                    padding:10px 0;
                    border-bottom:1px solid {BORDER};
                    color:{TEXT_DARK};
                    font-size:14px;
                ">
                    {_escape(addon["name"])}
                </td>

                <td
                    align="right"
                    style="
                        padding:10px 0;
                        border-bottom:1px solid {BORDER};
                        color:{TEXT_DARK};
                        font-size:14px;
                        font-weight:600;
                    "
                >
                    +${addon["price"]}
                </td>

            </tr>
            """

    else:

        addon_rows = f"""
        <tr>
            <td
                colspan="2"
                style="
                    padding:10px 0;
                    color:{TEXT_MUTED};
                    font-size:14px;
                "
            >
                No additional services selected.
            </td>
        </tr>
        """

    safe_customer_message = (
        _escape(
            customer_message
        )
        .replace(
            "\n",
            "<br>",
        )
    )

    return f"""
<!doctype html>

<html lang="en">

<head>

<meta charset="utf-8">

<meta
    name="viewport"
    content="width=device-width,
             initial-scale=1.0"
>

<title>
    Quote Request Received
</title>

</head>


<body style="
    margin:0;
    padding:0;
    background:{BACKGROUND};
    font-family:
        Arial,
        Helvetica,
        sans-serif;
    color:{TEXT_DARK};
">


<table
    role="presentation"
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
    style="
        background:{BACKGROUND};
    "
>

<tr>

<td
    align="center"
    style="
        padding:30px 15px;
    "
>


<table
    role="presentation"
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
    style="
        max-width:620px;
        background:{CARD_BACKGROUND};
        border:1px solid {BORDER};
        border-radius:12px;
        overflow:hidden;
    "
>


<!-- ======================================================
     BRAND HEADER
     Logo + visible company name
======================================================= -->

<tr>

<td
    align="center"
    style="
        background:{PRIMARY_GREEN};
        padding:28px 25px;
    "
>

<table
    role="presentation"
    cellpadding="0"
    cellspacing="0"
    border="0"
    style="margin:0 auto;"
>

<tr>

<!-- LOGO -->

<td
    valign="middle"
    style="padding-right:14px;"
>

<a
    href="{BUSINESS_WEBSITE}"
    target="_blank"
    style="display:inline-block;text-decoration:none;"
>

<img
    src="{BUSINESS_LOGO_URL}"
    alt=""
    width="72"
    style="
        display:block;
        width:72px;
        max-width:72px;
        height:auto;
        border:0;
        outline:none;
        text-decoration:none;
    "
>

</a>

</td>

<!-- COMPANY NAME -->

<td
    valign="middle"
    style="text-align:left;"
>

<div
    style="
        color:#ffffff;
        font-family:Arial,Helvetica,sans-serif;
        font-size:20px;
        line-height:1.2;
        font-weight:700;
        white-space:nowrap;
    "
>
YD Commercial Cleaning
</div>

<div
    style="
        margin-top:5px;
        color:#dcebe5;
        font-family:Arial,Helvetica,sans-serif;
        font-size:10px;
        line-height:1.3;
        letter-spacing:1.2px;
        font-weight:600;
    "
>
PROFESSIONAL CLEANING SERVICES
</div>

</td>

</tr>

</table>

</td>

</tr>


<!-- ======================================================
     HERO
======================================================= -->

<tr>

<td
    style="
        padding:35px 30px 20px;
    "
>


<div style="
    display:inline-block;
    padding:6px 10px;
    background:{LIGHT_GREEN};
    color:{PRIMARY_GREEN};
    border-radius:20px;
    font-size:11px;
    font-weight:700;
    letter-spacing:.5px;
">

REQUEST RECEIVED

</div>


<h1 style="
    margin:16px 0 10px;
    color:{DARK_GREEN};
    font-size:27px;
    line-height:1.25;
">

Thank you, {_escape(customer_name)}

</h1>


<p style="
    margin:0;
    color:{TEXT_MUTED};
    font-size:15px;
    line-height:1.7;
">

We've successfully received your
cleaning quote request. Our team will
review your details and contact you shortly.

</p>


</td>

</tr>


<!-- ======================================================
     REFERENCE
======================================================= -->

<tr>

<td
    style="
        padding:0 30px 25px;
    "
>


<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    style="
        background:{SOFT_BACKGROUND};
        border:1px solid {BORDER};
        border-radius:8px;
    "
>

<tr>

<td style="
    padding:16px 18px;
">

<div style="
    color:{TEXT_MUTED};
    font-size:11px;
    text-transform:uppercase;
    letter-spacing:.7px;
    margin-bottom:5px;
">

Quote Reference

</div>


<div style="
    color:{DARK_GREEN};
    font-size:18px;
    font-weight:700;
">

{_escape(reference)}

</div>

</td>

</tr>

</table>

</td>

</tr>


<!-- ======================================================
     REQUEST DETAILS
======================================================= -->

<tr>

<td
    style="
        padding:0 30px 30px;
    "
>

<h2 style="
    margin:0 0 15px;
    color:{DARK_GREEN};
    font-size:18px;
">

Your Request

</h2>


<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    style="
        border-collapse:collapse;
    "
>


<tr>

<td style="
    padding:11px 0;
    border-bottom:1px solid {BORDER};
    color:{TEXT_MUTED};
    font-size:13px;
">

Service

</td>


<td
    align="right"
    style="
        padding:11px 0;
        border-bottom:1px solid {BORDER};
        color:{TEXT_DARK};
        font-size:14px;
        font-weight:600;
    "
>

{_escape(service_name)}

</td>

</tr>


<tr>

<td style="
    padding:11px 0;
    border-bottom:1px solid {BORDER};
    color:{TEXT_MUTED};
    font-size:13px;
">

Property Type

</td>


<td
    align="right"
    style="
        padding:11px 0;
        border-bottom:1px solid {BORDER};
        color:{TEXT_DARK};
        font-size:14px;
    "
>

{_escape(property_type)}

</td>

</tr>


<tr>

<td style="
    padding:11px 0;
    border-bottom:1px solid {BORDER};
    color:{TEXT_MUTED};
    font-size:13px;
">

Location

</td>


<td
    align="right"
    style="
        padding:11px 0;
        border-bottom:1px solid {BORDER};
        color:{TEXT_DARK};
        font-size:14px;
    "
>

{_escape(suburb_postcode)}

</td>

</tr>


<tr>

<td style="
    padding:11px 0;
    color:{TEXT_MUTED};
    font-size:13px;
">

Preferred Date

</td>


<td
    align="right"
    style="
        padding:11px 0;
        color:{TEXT_DARK};
        font-size:14px;
        font-weight:600;
    "
>

{_escape(preferred_date)}

</td>

</tr>


</table>

</td>

</tr>


<!-- ======================================================
     ADDITIONAL SERVICES
======================================================= -->

<tr>

<td
    style="
        padding:0 30px 30px;
    "
>

<h2 style="
    margin:0 0 15px;
    color:{DARK_GREEN};
    font-size:18px;
">

Additional Services

</h2>


<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    style="
        border-collapse:collapse;
    "
>

{addon_rows}

</table>

</td>

</tr>


<!-- ======================================================
     CUSTOMER MESSAGE
======================================================= -->

<tr>

<td
    style="
        padding:0 30px 30px;
    "
>

<h2 style="
    margin:0 0 12px;
    color:{DARK_GREEN};
    font-size:18px;
">

Your Message

</h2>


<div style="
    padding:15px;
    background:{SOFT_BACKGROUND};
    border-left:3px solid {PRIMARY_GREEN};
    border-radius:4px;
    color:{TEXT_MUTED};
    font-size:14px;
    line-height:1.7;
">

{safe_customer_message}

</div>

</td>

</tr>


<!-- ======================================================
     WHAT HAPPENS NEXT
======================================================= -->

<tr>

<td style="
    padding:25px 30px;
    background:{SOFT_BACKGROUND};
    border-top:1px solid {BORDER};
    border-bottom:1px solid {BORDER};
">


<h2 style="
    margin:0 0 18px;
    color:{DARK_GREEN};
    font-size:18px;
">

What happens next?

</h2>


<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
>


<tr>

<td
    valign="top"
    style="
        width:32px;
        color:{PRIMARY_GREEN};
        font-weight:700;
        font-size:16px;
    "
>

1

</td>

<td style="
    padding-bottom:14px;
    color:{TEXT_MUTED};
    font-size:14px;
    line-height:1.5;
">

Our team reviews your request.

</td>

</tr>


<tr>

<td
    valign="top"
    style="
        width:32px;
        color:{PRIMARY_GREEN};
        font-weight:700;
        font-size:16px;
    "
>

2

</td>

<td style="
    padding-bottom:14px;
    color:{TEXT_MUTED};
    font-size:14px;
    line-height:1.5;
">

We'll contact you to confirm the details.

</td>

</tr>


<tr>

<td
    valign="top"
    style="
        width:32px;
        color:{PRIMARY_GREEN};
        font-weight:700;
        font-size:16px;
    "
>

3

</td>

<td style="
    color:{TEXT_MUTED};
    font-size:14px;
    line-height:1.5;
">

We'll discuss availability and pricing with you.

</td>

</tr>


</table>

</td>

</tr>


<!-- ======================================================
     CALL TO ACTION
======================================================= -->

<tr>

<td
    align="center"
    style="
        padding:30px;
    "
>

<p style="
    margin:0 0 18px;
    color:{TEXT_MUTED};
    font-size:14px;
">

Need to speak with us sooner?

</p>


<a
    href="tel:{BUSINESS_PHONE_TEL}"
    style="
        display:inline-block;
        padding:13px 24px;
        background:{PRIMARY_GREEN};
        color:#ffffff;
        text-decoration:none;
        border-radius:6px;
        font-size:14px;
        font-weight:700;
    "
>

Call {BUSINESS_PHONE}

</a>


&nbsp;&nbsp;


<a
    href="{BUSINESS_WEBSITE}"
    target="_blank"
    style="
        display:inline-block;
        padding:13px 24px;
        background:#ffffff;
        color:{PRIMARY_GREEN};
        text-decoration:none;
        border:1px solid {PRIMARY_GREEN};
        border-radius:6px;
        font-size:14px;
        font-weight:700;
    "
>

Visit Website

</a>


</td>

</tr>


<!-- ======================================================
     FOOTER
======================================================= -->

<tr>

<td
    style="
        padding:25px 30px;
        background:{PRIMARY_GREEN};
        text-align:center;
    "
>


<div style="
    color:#ffffff;
    font-size:15px;
    font-weight:700;
    margin-bottom:8px;
">

{BUSINESS_NAME}

</div>


<div style="
    color:#dcebe5;
    font-size:12px;
    line-height:1.8;
">

{BUSINESS_PHONE}

<br>

<a
    href="{BUSINESS_WEBSITE}"
    target="_blank"
    style="
        color:#ffffff;
        text-decoration:none;
    "
>

www.ydcleaning.com.au

</a>

</div>


</td>

</tr>


</table>

</td>

</tr>

</table>


</body>

</html>
""".strip()


# ============================================================
# ADMIN QUOTE EMAIL
# ============================================================

def send_admin_quote_email(
    quote,
    *,
    service_name=None,
    source_page=None,
    submitted_at=None,
):
    """
    Send new lead notification to the business.
    """

    customer_name = _safe(
        getattr(
            quote,
            "name",
            None,
        ),
        fallback="Unknown customer",
    )

    customer_email = getattr(
        quote,
        "email",
        None,
    )

    customer_phone = _safe(
        getattr(
            quote,
            "phone",
            None,
        ),
        fallback="Not provided",
    )

    resolved_service = _get_service_name(
        quote,
        service_name,
    )

    reference = _get_quote_reference(
        quote
    )

    preferred_date = _format_date(
        getattr(
            quote,
            "preferred_date",
            None,
        )
    )

    property_type = _safe(
        getattr(
            quote,
            "property_type",
            None,
        )
    )

    suburb_postcode = _safe(
        getattr(
            quote,
            "suburb_postcode",
            None,
        )
    )

    customer_message = _safe(
        getattr(
            quote,
            "message",
            None,
        ),
        fallback="No additional message provided.",
    )

    submission_value = (
        submitted_at
        or getattr(
            quote,
            "created_at",
            None,
        )
        or now()
    )

    submission_time = _format_submission_time(
        submission_value
    )

    source = _safe(
        source_page,
        fallback="Website",
    )

    subject = (
        f"NEW QUOTE LEAD — "
        f"{customer_name} "
        f"({reference})"
    )

    # --------------------------------------------------------
    # PLAIN TEXT
    # --------------------------------------------------------

    text_message = f"""
NEW QUICK QUOTE REQUEST
========================================

REFERENCE
{reference}

CUSTOMER
----------------------------------------
Name: {customer_name}
Phone: {customer_phone}
Email: {customer_email or "Not provided"}

JOB DETAILS
----------------------------------------
Service: {resolved_service}
Property Type: {property_type}
Suburb / Postcode: {suburb_postcode}
Preferred Date: {preferred_date}

ADDITIONAL SERVICES
----------------------------------------
{get_addons_text(quote)}

CUSTOMER MESSAGE
----------------------------------------
{customer_message}

LEAD SOURCE
----------------------------------------
Page: {source}
Submitted: {submission_time}

ACTION
----------------------------------------
Contact the customer and update the lead
status in the YD Commercial Cleaning dashboard.

YD Commercial Cleaning Services
{BUSINESS_PHONE}
{BUSINESS_WEBSITE}
""".strip()

    # --------------------------------------------------------
    # HTML
    # --------------------------------------------------------

    html_message = _admin_quote_email_html(
        quote=quote,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        service_name=resolved_service,
        reference=reference,
        preferred_date=preferred_date,
        property_type=property_type,
        suburb_postcode=suburb_postcode,
        customer_message=customer_message,
        source=source,
        submission_time=submission_time,
    )

    return _send_email(
        subject=subject,
        message=text_message,
        recipient=settings.ADMIN_EMAIL,
        html_message=html_message,
        reply_to=customer_email,
    )


# ============================================================
# ADMIN EMAIL HTML
# ============================================================

def _admin_quote_email_html(
    *,
    quote,
    customer_name,
    customer_email,
    customer_phone,
    service_name,
    reference,
    preferred_date,
    property_type,
    suburb_postcode,
    customer_message,
    source,
    submission_time,
):
    """
    Premium internal lead notification.
    """

    addons = get_addons(
        quote
    )

    if addons:

        addon_rows = ""

        for addon in addons:

            addon_rows += f"""
            <tr>

                <td style="
                    padding:10px 12px;
                    border-bottom:1px solid {BORDER};
                    font-size:14px;
                    color:{TEXT_DARK};
                ">
                    {_escape(addon["name"])}
                </td>

                <td
                    align="right"
                    style="
                        padding:10px 12px;
                        border-bottom:1px solid {BORDER};
                        font-size:14px;
                        font-weight:600;
                        color:{TEXT_DARK};
                    "
                >
                    +${addon["price"]}
                </td>

            </tr>
            """

    else:

        addon_rows = f"""
        <tr>

            <td
                colspan="2"
                style="
                    padding:12px;
                    color:{TEXT_MUTED};
                    font-size:14px;
                "
            >

                No additional services selected.

            </td>

        </tr>
        """

    safe_customer_message = (
        _escape(
            customer_message
        )
        .replace(
            "\n",
            "<br>",
        )
    )

    safe_email = (
        _escape(
            customer_email
        )
        if customer_email
        else "Not provided"
    )

    safe_phone = _escape(
        customer_phone
    )

    return f"""
<!doctype html>

<html lang="en">

<head>

<meta charset="utf-8">

<meta
    name="viewport"
    content="width=device-width,
             initial-scale=1.0"
>

<title>
    New Quote Lead
</title>

</head>


<body style="
    margin:0;
    padding:25px 12px;
    background:{BACKGROUND};
    font-family:
        Arial,
        Helvetica,
        sans-serif;
    color:{TEXT_DARK};
">


<table
    role="presentation"
    width="100%"
    cellpadding="0"
    cellspacing="0"
>


<tr>

<td align="center">


<table
    role="presentation"
    width="100%"
    cellpadding="0"
    cellspacing="0"
    style="
        max-width:650px;
        background:#ffffff;
        border:1px solid {BORDER};
        border-radius:12px;
        overflow:hidden;
    "
>


<!-- ======================================================
     HEADER WITH LOGO + COMPANY NAME
======================================================= -->

<tr>

<td
    style="
        padding:24px 26px;
        background:{PRIMARY_GREEN};
    "
>

<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
>

<tr>

<!-- BRAND -->

<td
    valign="middle"
>

<table
    cellpadding="0"
    cellspacing="0"
    border="0"
>

<tr>

<td
    valign="middle"
    style="padding-right:12px;"
>

<a
    href="{BUSINESS_WEBSITE}"
    target="_blank"
    style="display:inline-block;text-decoration:none;"
>

<img
    src="{BUSINESS_LOGO_URL}"
    alt=""
    width="58"
    style="
        display:block;
        width:58px;
        max-width:58px;
        height:auto;
        border:0;
    "
>

</a>

</td>

<td
    valign="middle"
>

<div
    style="
        color:#ffffff;
        font-family:Arial,Helvetica,sans-serif;
        font-size:17px;
        line-height:1.2;
        font-weight:700;
    "
>
YD Commercial Cleaning
</div>

<div
    style="
        margin-top:4px;
        color:#dcebe5;
        font-family:Arial,Helvetica,sans-serif;
        font-size:9px;
        line-height:1.3;
        letter-spacing:1px;
        font-weight:600;
    "
>
PROFESSIONAL CLEANING SERVICES
</div>

</td>

</tr>

</table>

</td>

<!-- NEW LEAD -->

<td
    align="right"
    valign="middle"
    style="
        color:#dcebe5;
        font-family:Arial,Helvetica,sans-serif;
        font-size:11px;
        font-weight:600;
        white-space:nowrap;
    "
>
NEW LEAD
</td>

</tr>

</table>

</td>

</tr>

</table>

</td>

</tr>


<!-- ======================================================
     TITLE
======================================================= -->

<tr>

<td
    style="
        padding:28px 26px 20px;
    "
>


<div style="
    display:inline-block;
    background:{LIGHT_GREEN};
    color:{PRIMARY_GREEN};
    padding:6px 10px;
    border-radius:20px;
    font-size:11px;
    font-weight:700;
">

NEW QUOTE REQUEST

</div>


<h1 style="
    margin:14px 0 8px;
    color:{DARK_GREEN};
    font-size:25px;
">

{_escape(customer_name)}

</h1>


<p style="
    margin:0;
    color:{TEXT_MUTED};
    font-size:14px;
    line-height:1.6;
">

A new customer has submitted a quote request
through the website.

</p>


</td>

</tr>


<!-- ======================================================
     REFERENCE
======================================================= -->

<tr>

<td
    style="
        padding:0 26px 25px;
    "
>


<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    style="
        background:{SOFT_BACKGROUND};
        border:1px solid {BORDER};
        border-radius:8px;
    "
>

<tr>

<td style="
    padding:15px;
">

<div style="
    color:{TEXT_MUTED};
    font-size:11px;
    text-transform:uppercase;
    letter-spacing:.6px;
    margin-bottom:4px;
">

Quote Reference

</div>


<strong style="
    color:{DARK_GREEN};
    font-size:17px;
">

{_escape(reference)}

</strong>

</td>

</tr>

</table>

</td>

</tr>


<!-- ======================================================
     CUSTOMER DETAILS
======================================================= -->

<tr>

<td
    style="
        padding:0 26px 25px;
    "
>


<h2 style="
    margin:0 0 14px;
    color:{DARK_GREEN};
    font-size:17px;
">

Customer Details

</h2>


<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    style="
        border:1px solid {BORDER};
        border-radius:8px;
        border-collapse:separate;
        overflow:hidden;
    "
>


<tr>

<td style="
    padding:11px 12px;
    background:{SOFT_BACKGROUND};
    color:{TEXT_MUTED};
    font-size:13px;
">

Name

</td>

<td style="
    padding:11px 12px;
    font-size:14px;
    font-weight:600;
">

{_escape(customer_name)}

</td>

</tr>


<tr>

<td style="
    padding:11px 12px;
    background:{SOFT_BACKGROUND};
    color:{TEXT_MUTED};
    font-size:13px;
">

Phone

</td>

<td style="
    padding:11px 12px;
    font-size:14px;
    font-weight:600;
">

<a
    href="tel:{BUSINESS_PHONE_TEL}"
    style="
        color:{PRIMARY_GREEN};
        text-decoration:none;
    "
>

{safe_phone}

</a>

</td>

</tr>


<tr>

<td style="
    padding:11px 12px;
    background:{SOFT_BACKGROUND};
    color:{TEXT_MUTED};
    font-size:13px;
">

Email

</td>

<td style="
    padding:11px 12px;
    font-size:14px;
">

{safe_email}

</td>

</tr>


</table>

</td>

</tr>


<!-- ======================================================
     JOB DETAILS
======================================================= -->

<tr>

<td
    style="
        padding:0 26px 25px;
    "
>


<h2 style="
    margin:0 0 14px;
    color:{DARK_GREEN};
    font-size:17px;
">

Job Details

</h2>


<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    style="
        border-collapse:collapse;
    "
>


<tr>

<td style="
    padding:10px 0;
    border-bottom:1px solid {BORDER};
    color:{TEXT_MUTED};
    font-size:13px;
">

Service

</td>


<td
    align="right"
    style="
        padding:10px 0;
        border-bottom:1px solid {BORDER};
        font-size:14px;
        font-weight:600;
    "
>

{_escape(service_name)}

</td>

</tr>


<tr>

<td style="
    padding:10px 0;
    border-bottom:1px solid {BORDER};
    color:{TEXT_MUTED};
    font-size:13px;
">

Property Type

</td>


<td
    align="right"
    style="
        padding:10px 0;
        border-bottom:1px solid {BORDER};
        font-size:14px;
    "
>

{_escape(property_type)}

</td>

</tr>


<tr>

<td style="
    padding:10px 0;
    border-bottom:1px solid {BORDER};
    color:{TEXT_MUTED};
    font-size:13px;
">

Location

</td>


<td
    align="right"
    style="
        padding:10px 0;
        border-bottom:1px solid {BORDER};
        font-size:14px;
    "
>

{_escape(suburb_postcode)}

</td>

</tr>


<tr>

<td style="
    padding:10px 0;
    color:{TEXT_MUTED};
    font-size:13px;
">

Preferred Date

</td>


<td
    align="right"
    style="
        padding:10px 0;
        font-size:14px;
        font-weight:600;
    "
>

{_escape(preferred_date)}

</td>

</tr>


</table>

</td>

</tr>


<!-- ======================================================
     ADDITIONAL SERVICES
======================================================= -->

<tr>

<td
    style="
        padding:0 26px 25px;
    "
>


<h2 style="
    margin:0 0 14px;
    color:{DARK_GREEN};
    font-size:17px;
">

Additional Services

</h2>


<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    style="
        border-collapse:collapse;
    "
>

{addon_rows}

</table>

</td>

</tr>


<!-- ======================================================
     CUSTOMER MESSAGE
======================================================= -->

<tr>

<td
    style="
        padding:0 26px 25px;
    "
>


<h2 style="
    margin:0 0 12px;
    color:{DARK_GREEN};
    font-size:17px;
">

Customer Message

</h2>


<div style="
    padding:15px;
    background:{SOFT_BACKGROUND};
    border-left:3px solid {PRIMARY_GREEN};
    border-radius:4px;
    color:{TEXT_MUTED};
    font-size:14px;
    line-height:1.7;
">

{safe_customer_message}

</div>

</td>

</tr>


<!-- ======================================================
     LEAD SOURCE
======================================================= -->

<tr>

<td style="
    padding:20px 26px;
    background:{SOFT_BACKGROUND};
    border-top:1px solid {BORDER};
    border-bottom:1px solid {BORDER};
">


<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
>

<tr>

<td>

<div style="
    color:{TEXT_MUTED};
    font-size:11px;
    text-transform:uppercase;
    margin-bottom:5px;
">

Lead Source

</div>


<div style="
    color:{TEXT_DARK};
    font-size:13px;
">

{_escape(source)}

</div>

</td>


<td align="right">

<div style="
    color:{TEXT_MUTED};
    font-size:11px;
    text-transform:uppercase;
    margin-bottom:5px;
">

Submitted

</div>


<div style="
    color:{TEXT_DARK};
    font-size:13px;
">

{_escape(submission_time)}

</div>

</td>

</tr>

</table>

</td>

</tr>


<!-- ======================================================
     ADMIN ACTION
======================================================= -->

<tr>

<td
    align="center"
    style="
        padding:30px 26px;
    "
>


<p style="
    margin:0 0 18px;
    color:{TEXT_MUTED};
    font-size:13px;
">

Follow up with the customer and update the lead
status in your YD Commercial Cleaning dashboard.

</p>


<a
    href="tel:{BUSINESS_PHONE_TEL}"
    style="
        display:inline-block;
        padding:13px 24px;
        background:{PRIMARY_GREEN};
        color:#ffffff;
        text-decoration:none;
        border-radius:6px;
        font-size:14px;
        font-weight:700;
    "
>

Call Business

</a>


</td>

</tr>


<!-- ======================================================
     FOOTER
======================================================= -->

<tr>

<td
    style="
        padding:20px 26px;
        text-align:center;
        background:{DARK_GREEN};
        color:#dcebe5;
        font-size:11px;
        line-height:1.7;
    "
>

{BUSINESS_NAME}

<br>

{BUSINESS_PHONE}

<br>

<a
    href="{BUSINESS_WEBSITE}"
    target="_blank"
    style="
        color:#ffffff;
        text-decoration:none;
    "
>

www.ydcleaning.com.au

</a>

</td>

</tr>


</table>

</td>

</tr>

</table>


</body>

</html>
""".strip()