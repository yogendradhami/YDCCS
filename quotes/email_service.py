from django.conf import settings
from django.core.mail import send_mail


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


def send_customer_quote_email(quote):
    subject = "Thank you for your quote request - YD Commercial Cleaning"

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
Website: www.ydcleaning.com
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [quote.email],
        fail_silently=False,
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

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [settings.ADMIN_EMAIL],
        fail_silently=False,
<<<<<<< HEAD
    )
=======
    )
>>>>>>> 5815f15 (Initial project commit)
