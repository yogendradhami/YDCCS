from io import BytesIO
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders
from django.core.mail import EmailMessage
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from bookings.models import Booking
from reports.models import CleaningReport
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from reports.pdf_utils import generate_cleaning_report_pdf

logger = logging.getLogger(__name__)
MAX_REPORT_EMAIL_ATTACHMENT_BYTES = 25 * 1024 * 1024

def _stored_image_reader(image_field):
    """Read an image through its storage backend, including remote storage."""
    if not image_field:
        return None

    try:
        with image_field.open("rb") as image_file:
            return ImageReader(BytesIO(image_file.read()))
    except Exception:
        return None


def user_can_view_booking_report(user, booking):
    if user.is_staff or user.is_superuser:
        return True

    if hasattr(user, "employee_profile"):
        return booking.assigned_employee == user.employee_profile

    if hasattr(user, "customer_profile"):
        return booking.customer == user.customer_profile

    return False


@login_required
def report_list(request):
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponseForbidden("Only admin/staff can view all reports.")

    bookings = (
        Booking.objects.select_related(
            "cleaning_report", "customer", "assigned_employee"
        )
        .prefetch_related("job_photos")
        .all()
        .order_by("-booking_date", "-booking_time")
    )
    emailed_reports = bookings.filter(
        cleaning_report__emailed_to_customer=True
    ).count()
    pending_reports = bookings.filter(
        cleaning_report__emailed_to_customer=False
    ).count() + bookings.filter(cleaning_report__isnull=True).count()
    return render(
        request,
        "reports/report_list.html",
        {
            "bookings": bookings,
            "emailed_reports": emailed_reports,
            "pending_reports": pending_reports,
        },
    )


@login_required
def cleaning_report_detail(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if not user_can_view_booking_report(request.user, booking):
        return HttpResponseForbidden("You do not have permission to view this report.")

    before_photos = booking.job_photos.filter(photo_type="before").order_by(
        "uploaded_at"
    )
    after_photos = booking.job_photos.filter(photo_type="after").order_by("uploaded_at")

    return render(
        request,
        "reports/cleaning_report_detail.html",
        {
            "booking": booking,
            "before_photos": before_photos,
            "after_photos": after_photos,
        },
    )



@login_required
def download_cleaning_report_pdf(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if not user_can_view_booking_report(request.user, booking):
        return HttpResponseForbidden(
            "You do not have permission to download this report."
        )

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    green = (0.08, 0.25, 0.18)
    grey = (0.35, 0.38, 0.36)
    page_number = 1

    def draw_footer():
        pdf.setStrokeColorRGB(*green)
        pdf.setLineWidth(0.8)
        pdf.line(50, 42, width - 50, 42)

        pdf.setFont("Helvetica", 8)
        pdf.setFillColorRGB(*grey)
        pdf.drawString(50, 28, "YD Commercial Cleaning Services")
        pdf.drawRightString(width - 50, 28, f"Page {page_number}")
        pdf.setFillColorRGB(0, 0, 0)

    def new_page():
        nonlocal page_number
        draw_footer()
        pdf.showPage()
        page_number += 1
        return height - 60

    def draw_section_heading(title, y):
        pdf.setFillColorRGB(*green)
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(50, y, title)
        pdf.setFillColorRGB(0, 0, 0)
        return y - 24

    def draw_wrapped_text(text, x, y, max_width, font_size=10, line_height=14):
        """Draw long text without allowing it to run off the page."""
        from reportlab.pdfbase.pdfmetrics import stringWidth

        pdf.setFont("Helvetica", font_size)

        paragraphs = str(text or "").splitlines() or [""]
        for paragraph in paragraphs:
            words = paragraph.split()
            line = ""

            for word in words:
                candidate = f"{line} {word}".strip()

                if stringWidth(candidate, "Helvetica", font_size) <= max_width:
                    line = candidate
                else:
                    if y < 65:
                        y = new_page()

                    if line:
                        pdf.drawString(x, y, line)
                        y -= line_height

                    line = word

            if y < 65:
                y = new_page()

            pdf.drawString(x, y, line)
            y -= line_height

        return y

    # ---------------------------------------------------------
    # Company header and branding
    # ---------------------------------------------------------
    y = height - 50
    logo_path = finders.find("images/logo.jpeg")

    if logo_path:
        try:
            pdf.drawImage(
                logo_path,
                50,
                y - 35,
                width=105,
                height=45,
                preserveAspectRatio=True,
                anchor="c",
                mask="auto",
            )
        except Exception:
            pass

    pdf.setFillColorRGB(*green)
    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawRightString(
        width - 50, y, "YD Commercial Cleaning Services"
    )

    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(width - 50, y - 19, "ABN: 95 916 203 175")
    pdf.drawRightString(width - 50, y - 33, "Phone: 0430 049 865")
    pdf.drawRightString(width - 50, y - 47, "Email: info@ydcleaning.com.au")

    y -= 85
    pdf.setStrokeColorRGB(*green)
    pdf.setLineWidth(1.5)
    pdf.line(50, y, width - 50, y)
    y -= 35

    pdf.setFillColorRGB(*green)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawCentredString(
        width / 2, y, "CLEANING COMPLETION REPORT"
    )
    pdf.setFillColorRGB(0, 0, 0)
    y -= 35

    pdf.setFont("Helvetica", 9)
    pdf.setFillColorRGB(*grey)
    pdf.drawString(
        50,
        y,
        f"Report generated: {timezone.localtime().strftime('%d %B %Y, %I:%M %p')}",
    )
    pdf.setFillColorRGB(0, 0, 0)
    y -= 30

    # ---------------------------------------------------------
    # Job details
    # ---------------------------------------------------------
    y = draw_section_heading("Job Details", y)

    job_details = [
        ("Service", booking.get_service_type_display()),
        ("Booking reference", str(booking.id)),
        ("Date", str(booking.booking_date or "Not specified")),
        ("Time", str(booking.booking_time or "Not specified")),
        ("Status", booking.get_status_display()),
        ("Address", booking.address or "Not provided"),
        ("Suburb/Postcode", booking.suburb_postcode or "Not provided"),
    ]

    pdf.setFont("Helvetica", 10)

    for label, value in job_details:
        if y < 65:
            y = new_page()

        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(50, y, f"{label}:")
        pdf.setFont("Helvetica", 10)

        y = draw_wrapped_text(
            value,
            160,
            y,
            width - 210,
            font_size=10,
            line_height=13,
        )
        y -= 3

    y -= 12

    # ---------------------------------------------------------
    # Customer details
    # ---------------------------------------------------------
    y = draw_section_heading("Customer Details", y)
    customer = booking.customer

    if customer:
        customer_details = [
            ("Name", customer.full_name or "Not provided"),
            ("Phone", customer.phone or "Not provided"),
            ("Email", customer.email or "Not provided"),
        ]
    else:
        customer_details = [
            ("Name", "Not assigned"),
            ("Phone", "Not provided"),
            ("Email", "Not provided"),
        ]

    for label, value in customer_details:
        if y < 65:
            y = new_page()

        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(50, y, f"{label}:")
        pdf.setFont("Helvetica", 10)
        y = draw_wrapped_text(
            value, 160, y, width - 210, font_size=10
        )
        y -= 3

    y -= 12

    # ---------------------------------------------------------
    # Cleaner / employee details
    # ---------------------------------------------------------
    y = draw_section_heading("Cleaner / Employee", y)

    employee = booking.assigned_employee

    if employee:
        employee_details = [
            ("Name", employee.full_name or "Not provided"),
            ("Phone", employee.phone or "Not provided"),
        ]
    else:
        employee_details = [("Assignment", "No employee assigned")]

    for label, value in employee_details:
        if y < 65:
            y = new_page()

        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(50, y, f"{label}:")
        pdf.setFont("Helvetica", 10)
        y = draw_wrapped_text(
            value, 160, y, width - 210, font_size=10
        )
        y -= 3

    y -= 12

    # ---------------------------------------------------------
    # Completion notes
    # ---------------------------------------------------------
    y = draw_section_heading("Completion Notes", y)

    notes = booking.notes or "No completion notes provided."
    y = draw_wrapped_text(
        notes,
        50,
        y,
        width - 100,
        font_size=10,
        line_height=15,
    )

    draw_footer()
    pdf.showPage()
    page_number += 1

    # ---------------------------------------------------------
    # Before and after photo pages
    # ---------------------------------------------------------
    photo_sections = [
        ("Before Photos", booking.job_photos.filter(photo_type="before")),
        ("After Photos", booking.job_photos.filter(photo_type="after")),
    ]

    for section_title, photos in photo_sections:
        y = height - 60

        pdf.setFillColorRGB(*green)
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(50, y, section_title)
        pdf.setFillColorRGB(0, 0, 0)
        y -= 35

        if not photos.exists():
            pdf.setFont("Helvetica", 11)
            pdf.drawString(
                50, y, f"No {section_title.lower()} uploaded."
            )
            draw_footer()
            pdf.showPage()
            page_number += 1
            continue

        x_positions = [50, 315]
        image_width = 220
        image_height = 150

        for index, photo in enumerate(photos):
            # Two photos per row, four per page.
            if index > 0 and index % 4 == 0:
                draw_footer()
                pdf.showPage()
                page_number += 1

                y = height - 60
                pdf.setFillColorRGB(*green)
                pdf.setFont("Helvetica-Bold", 18)
                pdf.drawString(50, y, section_title)
                pdf.setFillColorRGB(0, 0, 0)
                y -= 35

            col = index % 2
            row = (index % 4) // 2
            x = x_positions[col]
            image_y = y - (row * 225)

            try:
                image_reader = _stored_image_reader(photo.image)

                if image_reader:
                    pdf.drawImage(
                        image_reader,
                        x,
                        image_y - image_height,
                        width=image_width,
                        height=image_height,
                        preserveAspectRatio=True,
                        anchor="c",
                        mask="auto",
                    )

                    pdf.setFont("Helvetica-Bold", 10)
                    pdf.drawString(
                        x,
                        image_y - image_height - 17,
                        photo.get_photo_type_display(),
                    )

                    pdf.setFont("Helvetica", 9)
                    photo_notes = photo.notes or "No notes provided."
                    pdf.drawString(
                        x,
                        image_y - image_height - 32,
                        photo_notes[:45],
                    )
                else:
                    pdf.setFont("Helvetica", 10)
                    pdf.drawString(
                        x, image_y - 20, "Image unavailable."
                    )

            except Exception:
                pdf.setFont("Helvetica", 10)
                pdf.drawString(
                    x, image_y - 20, "Image unavailable."
                )

        draw_footer()
        pdf.showPage()
        page_number += 1

    # ---------------------------------------------------------
    # Verification and signatures
    # ---------------------------------------------------------
    y = height - 70

    pdf.setFillColorRGB(*green)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, y, "Verification & Signatures")
    pdf.setFillColorRGB(0, 0, 0)

    y -= 45
    latest_photo = booking.job_photos.order_by("-uploaded_at").first()

    if latest_photo:
        signatures = [
            ("Employee Signature", latest_photo.employee_signature),
            ("Customer Signature", latest_photo.customer_signature),
        ]

        for title, signature in signatures:
            if not signature:
                continue

            if y < 150:
                y = new_page()

            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(50, y, title)
            y -= 15

            try:
                signature_reader = _stored_image_reader(signature)

                if signature_reader:
                    pdf.drawImage(
                        signature_reader,
                        50,
                        y - 65,
                        width=180,
                        height=60,
                        preserveAspectRatio=True,
                        anchor="c",
                        mask="auto",
                    )
                else:
                    pdf.setFont("Helvetica", 9)
                    pdf.drawString(
                        50, y - 15, "Signature image unavailable."
                    )

            except Exception:
                pdf.setFont("Helvetica", 9)
                pdf.drawString(
                    50, y - 15, "Signature image unavailable."
                )

            y -= 95

    else:
        pdf.setFont("Helvetica", 10)
        pdf.drawString(
            50, y, "No verification photos or signatures are available."
        )
        y -= 25

    if y < 80:
        y = new_page()

    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        50,
        y - 10,
        "This report records the cleaning service details and available verification.",
    )

    draw_footer()
    pdf.showPage()
    page_number += 1

    # ---------------------------------------------------------
    # Final page
    # ---------------------------------------------------------
    pdf.setFillColorRGB(*green)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawCentredString(
        width / 2, height - 100, "Report Completed"
    )

    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica", 11)
    pdf.drawCentredString(
        width / 2,
        height - 135,
        "Thank you for choosing YD Commercial Cleaning Services.",
    )
    pdf.drawCentredString(
        width / 2,
        height - 155,
        "Professional Cleaning. Reliable Service. Spotless Results.",
    )

    pdf.setFillColorRGB(*green)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawCentredString(
        width / 2, height - 195, "www.ydcleaning.com.au"
    )

    pdf.setFillColorRGB(0, 0, 0)
    draw_footer()

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f"cleaning-report-booking-{booking.id}.pdf",
        content_type="application/pdf",
    )



@login_required
def email_cleaning_report(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponseForbidden(
            "Only admin/staff can email reports."
        )

    customer = booking.customer

    if not customer or not customer.email:
        messages.error(
            request,
            "Customer does not have an email address.",
        )
        return redirect(
            "cleaning_report_detail",
            booking_id=booking.id,
        )

    report, created = CleaningReport.objects.get_or_create(
        booking=booking
    )

    # Generate the same branded PDF used by the download view.
    pdf_buffer = generate_cleaning_report_pdf(booking)
    pdf_attachment = pdf_buffer.getvalue()
    if len(pdf_attachment) > MAX_REPORT_EMAIL_ATTACHMENT_BYTES:
        messages.error(
            request,
            "The report PDF is too large to email. Download it and send it "
            "using a file-sharing link instead.",
        )
        return redirect("cleaning_report_detail", booking_id=booking.id)

    context = {
        "customer_name": customer.full_name,
        "booking": booking,
        "report_date": timezone.localtime(),
    }

    text_message = render_to_string(
        "emails/reviews/reports/cleaning_report_email.txt",
        context,
    )

    html_message = render_to_string(
        "emails/reviews/reports/cleaning_report_email.html",
        context,
    )

    email = EmailMultiAlternatives(
        subject="Your Cleaning Completion Report",
        body=text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[customer.email],
        reply_to=["info@ydcleaning.com.au"],
    )

    email.attach_alternative(
        html_message,
        "text/html",
    )

    email.attach(
        f"cleaning-report-booking-{booking.id}.pdf",
        pdf_attachment,
        "application/pdf",
    )

    try:
        email.send(fail_silently=False)
    except Exception:
        logger.exception(
            "Failed to email cleaning report for booking %s.", booking.id
        )
        messages.error(
            request,
            "The report was prepared, but the email service timed out or was "
            "unavailable. The report is still available to download; please "
            "retry sending it shortly.",
        )
        return redirect("cleaning_report_detail", booking_id=booking.id)

    report.emailed_to_customer = True
    report.save(update_fields=["emailed_to_customer"])

    messages.success(
        request,
        "Cleaning report PDF emailed to customer successfully.",
    )

    return redirect(
        "cleaning_report_detail",
        booking_id=booking.id,
    )
