import resend
from django.conf import settings

resend.api_key = settings.RESEND_API_KEY


def send_customer_email(quote):

    resend.Emails.send(
        {
            "from": "YD Commercial Cleaning <quotes@ydcleaning.com>",
            "to": [quote.email],
            "subject": "Quote Request Received",
            "html": f"""
        <h2>Thank you for contacting YD Cleaning</h2>

        <p>Hi {quote.name},</p>

        <p>
        We have received your quote request and our team
        will contact you shortly.
        </p>

        <p>
        Thank you for choosing
        <strong>YD Commercial Cleaning Services</strong>.
        </p>
        """,
        }
    )


def send_admin_email(quote):

    resend.Emails.send(
        {
            "from": "YD Commercial Cleaning <quotes@ydcleaning.com>",
            "to": ["yogendradhami6@gmail.com"],
            "subject": f"New Quote Request - {quote.name}",
            "html": f"""
        <h2>New Website Lead</h2>

        <ul>
            <li>Name: {quote.name}</li>
            <li>Email: {quote.email}</li>
            <li>Phone: {quote.phone}</li>
            <li>Property Type: {quote.property_type}</li>
            <li>Suburb: {quote.suburb_postcode}</li>
        </ul>

        <p>{quote.message}</p>
        """,
        }
    )
