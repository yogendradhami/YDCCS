import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import redirect, render

from core.views import _get_faq_section, _get_page_why_choose

from .forms import (
    CorporateMultiSiteForm,
    CorporateProposalForm,
    CorporateTeamContactForm,
)

logger = logging.getLogger(__name__)


def _send_corporate_lead_emails(lead):
    """
    Send internal notification and customer confirmation emails
    for a successfully saved corporate lead.

    Email failures are logged but do not prevent the lead from
    being saved or the customer from reaching the success page.
    """

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "")
    admin_email = getattr(settings, "ADMIN_EMAIL", "")

    if not from_email:
        logger.error(
            "Corporate lead email not sent: DEFAULT_FROM_EMAIL is not configured."
        )
        return

    if not admin_email:
        logger.error(
            "Corporate lead email not sent: ADMIN_EMAIL is not configured."
        )
        return

    lead_type = lead.lead_type_display_name

    company = lead.company_name or "Not provided"
    job_title = lead.job_title or "Not provided"
    phone = lead.phone or "Not provided"
    industry = lead.get_industry_display() if lead.industry else "Not provided"
    number_of_sites = (
        str(lead.number_of_sites)
        if lead.number_of_sites is not None
        else "Not provided"
    )
    service_locations = lead.service_locations or "Not provided"
    facility_size = lead.facility_size or "Not provided"
    services_required = lead.services_required or "Not provided"
    frequency = (
        lead.get_frequency_display()
        if lead.frequency
        else "Not provided"
    )
    preferred_start_date = (
        lead.preferred_start_date.strftime("%d %B %Y")
        if lead.preferred_start_date
        else "Not provided"
    )
    current_provider = (
        lead.current_cleaning_provider
        or "Not provided"
    )
    location_coverage = (
        lead.location_coverage
        or "Not provided"
    )
    centralised_invoicing = (
        "Yes"
        if lead.centralised_invoicing
        else "No"
    )
    reporting_requirements = (
        lead.reporting_requirements
        or "Not provided"
    )
    access_requirements = (
        lead.access_requirements
        or "Not provided"
    )
    customer_message = lead.message or "Not provided"
    landing_page = lead.landing_page or "Not recorded"
    referrer = lead.referrer or "Not recorded"

    # ---------------------------------------------------------
    # INTERNAL ADMIN NOTIFICATION
    # ---------------------------------------------------------

    admin_subject = (
        f"New Corporate Lead — {lead_type} — "
        f"{company} — {lead.full_name}"
    )

    admin_text = f"""
A new corporate enquiry has been submitted through the YD Commercial Cleaning website.

LEAD TYPE
{lead_type}

CONTACT DETAILS
Name: {lead.full_name}
Job title: {job_title}
Company / Organisation: {company}
Business email: {lead.email}
Business phone: {phone}

BUSINESS DETAILS
Industry: {industry}
Number of sites: {number_of_sites}
Service locations: {service_locations}
Facility size: {facility_size}
Services required: {services_required}
Cleaning frequency: {frequency}
Preferred start date: {preferred_start_date}
Current cleaning provider: {current_provider}

MULTI-SITE / OPERATIONAL REQUIREMENTS
Location coverage: {location_coverage}
Centralised invoicing: {centralised_invoicing}
Reporting requirements: {reporting_requirements}
Access requirements: {access_requirements}

CUSTOMER MESSAGE
{customer_message}

LEAD INFORMATION
Lead ID: {lead.pk}
Lead source: {lead.lead_source}
Landing page: {landing_page}
Referrer: {referrer}
Status: {lead.get_status_display()}
Submitted: {lead.created_at.strftime("%d %B %Y %I:%M %p")}

Please follow up with the customer through the CRM.
""".strip()

    admin_html = f"""
    <html>
    <body>
        <h2>New Corporate Lead</h2>

        <p>
            A new corporate enquiry has been submitted through the
            YD Commercial Cleaning website.
        </p>

        <h3>Lead Type</h3>
        <p>{lead_type}</p>

        <h3>Contact Details</h3>
        <table cellpadding="6" cellspacing="0" border="0">
            <tr><td><strong>Name</strong></td><td>{lead.full_name}</td></tr>
            <tr><td><strong>Job title</strong></td><td>{job_title}</td></tr>
            <tr><td><strong>Company</strong></td><td>{company}</td></tr>
            <tr><td><strong>Email</strong></td><td>{lead.email}</td></tr>
            <tr><td><strong>Phone</strong></td><td>{phone}</td></tr>
        </table>

        <h3>Business Details</h3>
        <table cellpadding="6" cellspacing="0" border="0">
            <tr><td><strong>Industry</strong></td><td>{industry}</td></tr>
            <tr><td><strong>Number of sites</strong></td><td>{number_of_sites}</td></tr>
            <tr><td><strong>Service locations</strong></td><td>{service_locations}</td></tr>
            <tr><td><strong>Facility size</strong></td><td>{facility_size}</td></tr>
            <tr><td><strong>Services required</strong></td><td>{services_required}</td></tr>
            <tr><td><strong>Frequency</strong></td><td>{frequency}</td></tr>
            <tr><td><strong>Preferred start date</strong></td><td>{preferred_start_date}</td></tr>
            <tr><td><strong>Current provider</strong></td><td>{current_provider}</td></tr>
        </table>

        <h3>Operational Requirements</h3>
        <table cellpadding="6" cellspacing="0" border="0">
            <tr><td><strong>Location coverage</strong></td><td>{location_coverage}</td></tr>
            <tr><td><strong>Centralised invoicing</strong></td><td>{centralised_invoicing}</td></tr>
            <tr><td><strong>Reporting requirements</strong></td><td>{reporting_requirements}</td></tr>
            <tr><td><strong>Access requirements</strong></td><td>{access_requirements}</td></tr>
        </table>

        <h3>Customer Message</h3>
        <p>{customer_message}</p>

        <h3>Lead Information</h3>
        <table cellpadding="6" cellspacing="0" border="0">
            <tr><td><strong>Lead ID</strong></td><td>{lead.pk}</td></tr>
            <tr><td><strong>Lead source</strong></td><td>{lead.lead_source}</td></tr>
            <tr><td><strong>Landing page</strong></td><td>{landing_page}</td></tr>
            <tr><td><strong>Referrer</strong></td><td>{referrer}</td></tr>
            <tr><td><strong>Status</strong></td><td>{lead.get_status_display()}</td></tr>
            <tr>
                <td><strong>Submitted</strong></td>
                <td>{lead.created_at.strftime("%d %B %Y %I:%M %p")}</td>
            </tr>
        </table>

        <p>
            <strong>Please follow up with the customer through the CRM.</strong>
        </p>
    </body>
    </html>
    """

    try:
        admin_email_message = EmailMultiAlternatives(
            subject=admin_subject,
            body=admin_text,
            from_email=from_email,
            to=[admin_email],
            reply_to=[lead.email],
        )

        admin_email_message.attach_alternative(
            admin_html,
            "text/html",
        )

        admin_email_message.send(
            fail_silently=False,
        )

        logger.info(
            "Corporate admin notification sent successfully for lead %s.",
            lead.pk,
        )

    except Exception:
        logger.exception(
            "Failed to send corporate admin notification for lead %s.",
            lead.pk,
        )

    # ---------------------------------------------------------
    # CUSTOMER CONFIRMATION
    # ---------------------------------------------------------

    customer_subject = (
        "We have received your corporate cleaning enquiry | "
        "YD Commercial Cleaning"
    )

    customer_text = f"""
Hi {lead.full_name},

Thank you for contacting YD Commercial Cleaning regarding your corporate cleaning requirements.

We have received your enquiry and our team will review the information you provided.

Enquiry type:
{lead_type}

Company / Organisation:
{company}

Our team will contact you shortly to discuss your requirements and the next steps.

If you need to provide additional information, you can reply directly to this email.

Kind regards,

YD Commercial Cleaning Services
Phone: 0430 049 865
Email: info@ydcleaning.com.au
Website: https://ydcleaning.com.au
""".strip()

    customer_html = f"""
    <html>
    <body>
        <p>Hi {lead.full_name},</p>

        <p>
            Thank you for contacting
            <strong>YD Commercial Cleaning Services</strong>
            regarding your corporate cleaning requirements.
        </p>

        <p>
            We have received your enquiry and our team will review
            the information you provided.
        </p>

        <h3>Enquiry Details</h3>

        <p>
            <strong>Enquiry type:</strong><br>
            {lead_type}
        </p>

        <p>
            <strong>Company / Organisation:</strong><br>
            {company}
        </p>

        <p>
            Our team will contact you shortly to discuss your
            requirements and the next steps.
        </p>

        <p>
            If you need to provide additional information,
            you can reply directly to this email.
        </p>

        <p>
            Kind regards,<br>
            <strong>YD Commercial Cleaning Services</strong><br>
            Phone: 0430 049 865<br>
            Email: info@ydcleaning.com.au<br>
            Website: https://ydcleaning.com.au
        </p>
    </body>
    </html>
    """

    try:
        customer_email_message = EmailMultiAlternatives(
            subject=customer_subject,
            body=customer_text,
            from_email=from_email,
            to=[lead.email],
        )

        customer_email_message.attach_alternative(
            customer_html,
            "text/html",
        )

        customer_email_message.send(
            fail_silently=False,
        )

        logger.info(
            "Corporate customer confirmation sent successfully for lead %s.",
            lead.pk,
        )

    except Exception:
        logger.exception(
            "Failed to send corporate customer confirmation for lead %s.",
            lead.pk,
        )


def _prepare_corporate_lead(lead, request):
    """
    Store attribution information after the lead has been saved.
    """

    lead.landing_page = request.build_absolute_uri(request.path)

    referrer = request.META.get("HTTP_REFERER", "").strip()

    if referrer:
        lead.referrer = referrer

    update_fields = ["landing_page"]

    if referrer:
        update_fields.append("referrer")

    lead.save(update_fields=update_fields)

    return lead


def _process_corporate_form(
    request,
    form_class,
    template_name,
    page_title,
    form_type,
    success_message,
):
    """
    Shared processing for all corporate enquiry forms.
    """

    if request.method == "POST":
        form = form_class(request.POST)

        if form.is_valid():
            lead = form.save()

            _prepare_corporate_lead(
                lead,
                request,
            )

            # Email is deliberately sent after the lead has been saved.
            # If email delivery fails, the lead remains safely stored.
            _send_corporate_lead_emails(lead)

            messages.success(
                request,
                success_message,
            )

            return redirect("corporate:success")

    else:
        form = form_class()

    return render(
        request,
        template_name,
        {
            "form": form,
            "page_title": page_title,
            "form_type": form_type,
        },
    )


def corporate(request):
    return render(
        request,
        "pages/corporate/corporate.html",
        {
            "faq_section": _get_faq_section("corporate"),
            "why_choose_section": _get_page_why_choose("corporate"),
        },
    )


def corporate_proposal(request):
    """
    Corporate Proposal enquiry.
    """

    return _process_corporate_form(
        request=request,
        form_class=CorporateProposalForm,
        template_name="pages/corporate/proposal.html",
        page_title="Request a Corporate Proposal",
        form_type="proposal",
        success_message=(
            "Thank you. Your corporate proposal enquiry has been "
            "received. Our team will contact you shortly."
        ),
    )


def corporate_team_contact(request):
    """
    Speak With Our Team enquiry.
    """

    return _process_corporate_form(
        request=request,
        form_class=CorporateTeamContactForm,
        template_name="pages/corporate/team_contact.html",
        page_title="Speak With Our Team",
        form_type="team_contact",
        success_message=(
            "Thank you. Your enquiry has been received. "
            "A member of our team will be in touch shortly."
        ),
    )


def corporate_multi_site(request):
    """
    Multi-Site Cleaning enquiry.
    """

    return _process_corporate_form(
        request=request,
        form_class=CorporateMultiSiteForm,
        template_name="pages/corporate/multi_site.html",
        page_title="Discuss Multi-Site Cleaning",
        form_type="multi_site",
        success_message=(
            "Thank you. Your multi-site cleaning enquiry has "
            "been received. Our corporate team will contact you "
            "shortly."
        ),
    )


def corporate_success(request):
    """
    Confirmation page shown after a successful corporate enquiry.
    """

    return render(
        request,
        "pages/corporate/success.html",
    )

