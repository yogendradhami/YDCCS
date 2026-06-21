import os
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from bookings.models import Booking
from reports.models import CleaningReport


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
        .all()
        .order_by("-booking_date", "-booking_time")
    )
    return render(request, "report_list.html", {"bookings": bookings})


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
        "cleaning_report_detail.html",
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
    y = height - 50

    logo_path = os.path.join(settings.MEDIA_ROOT, "company/logo.jpeg")

    if os.path.exists(logo_path):
        pdf.drawImage(
            logo_path,
            50,
            y - 40,
            width=120,
            height=50,
            preserveAspectRatio=True,
            mask="auto",
        )

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(190, y, "YD Commercial Cleaning Services")
    y -= 22

    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, y, "ABN: 95 916 203 175")
    y -= 15
    pdf.drawString(50, y, "Phone: 0430 049 865")
    y -= 15
    pdf.drawString(50, y, "Email: ydcommercialcleaning@gmail.com")
    y -= 15
    pdf.drawString(50, y, "Address: 2/10 Da Costa Avenue, Prospect SA 5082")
    y -= 35

    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(50, y, "CLEANING COMPLETION REPORT")
    y -= 35

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "Job Details")
    y -= 22

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, f"Service: {booking.service_type}")
    y -= 16
    pdf.drawString(50, y, f"Date: {booking.booking_date}")
    y -= 16
    pdf.drawString(50, y, f"Time: {booking.booking_time}")
    y -= 16
    pdf.drawString(50, y, f"Status: {booking.get_status_display()}")
    y -= 16

    pdf.drawString(50, y, f"Generated: {timezone.now().strftime('%d %B %Y %I:%M %p')}")

    y -= 16
    pdf.drawString(50, y, f"Address: {booking.address}")
    y -= 16
    pdf.drawString(50, y, f"Suburb/Postcode: {booking.suburb_postcode}")
    y -= 30

    customer = booking.customer

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "Customer Details")
    y -= 22

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, f"Name: {customer.full_name}")
    y -= 16
    pdf.drawString(50, y, f"Phone: {customer.phone}")
    y -= 16

    if customer.email:
        pdf.drawString(50, y, f"Email: {customer.email}")
        y -= 16

    y -= 15

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "Cleaner / Employee")
    y -= 22

    pdf.setFont("Helvetica", 11)

    if booking.assigned_employee:
        pdf.drawString(50, y, f"Name: {booking.assigned_employee.full_name}")
        y -= 16
        pdf.drawString(50, y, f"Phone: {booking.assigned_employee.phone}")
        y -= 16
    else:
        pdf.drawString(50, y, "Not assigned")
        y -= 16

    y -= 15

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "Completion Notes")
    y -= 22

    pdf.setFont("Helvetica", 11)

    notes = booking.notes or "No completion notes provided."

    for line in notes.split("\n"):
        if y < 100:
            pdf.showPage()
            y = height - 50

        pdf.drawString(50, y, line[:95])
        y -= 16

    photo_sections = [
        ("Before Photos", booking.job_photos.filter(photo_type="before")),
        ("After Photos", booking.job_photos.filter(photo_type="after")),
    ]

    for section_title, photos in photo_sections:
        pdf.showPage()
        y = height - 50

        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(50, y, section_title)
        y -= 30

        if not photos.exists():
            pdf.setFont("Helvetica", 11)
            pdf.drawString(50, y, f"No {section_title.lower()} uploaded.")
            continue

        x_positions = [50, 315]
        image_width = 220
        image_height = 160
        index = 0

        for photo in photos:
            if index > 0 and index % 4 == 0:
                pdf.showPage()
                y = height - 50
                pdf.setFont("Helvetica-Bold", 18)
                pdf.drawString(50, y, section_title)
                y -= 30

            col = index % 2
            row = (index % 4) // 2
            x = x_positions[col]
            image_y = y - (row * 230)

            if os.path.exists(photo.image.path):
                try:
                    pdf.drawImage(
                        ImageReader(photo.image.path),
                        x,
                        image_y - image_height,
                        width=image_width,
                        height=image_height,
                        preserveAspectRatio=True,
                        mask="auto",
                    )

                    pdf.setFont("Helvetica-Bold", 10)
                    pdf.drawString(
                        x, image_y - image_height - 18, photo.get_photo_type_display()
                    )

                    pdf.setFont("Helvetica", 9)
                    pdf.drawString(
                        x, image_y - image_height - 34, (photo.notes or "No notes")[:40]
                    )

                except Exception:
                    pdf.setFont("Helvetica", 10)
                    pdf.drawString(x, image_y, "Could not load image.")

            index += 1

    pdf.showPage()

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, height - 70, "Verification & Signatures")

    y = height - 120

    latest_photo = booking.job_photos.order_by("-uploaded_at").first()

    if latest_photo:

        if latest_photo.employee_signature:

            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(50, y, "Employee Signature")

            if os.path.exists(latest_photo.employee_signature.path):
                pdf.drawImage(
                    latest_photo.employee_signature.path,
                    50,
                    y - 90,
                    width=180,
                    height=70,
                    preserveAspectRatio=True,
                    mask="auto",
                )

            y -= 120

        if latest_photo.customer_signature:

            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(50, y, "Customer Signature")

            if os.path.exists(latest_photo.customer_signature.path):
                pdf.drawImage(
                    latest_photo.customer_signature.path,
                    50,
                    y - 90,
                    width=180,
                    height=70,
                    preserveAspectRatio=True,
                    mask="auto",
                )

            y -= 120

    pdf.setFont("Helvetica", 11)

    pdf.drawString(50, y, "This cleaning service has been completed and verified.")

    pdf.showPage()
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, height - 80, "Report Completed")

    pdf.setFont("Helvetica", 11)
    pdf.drawString(
        50, height - 110, "Thank you for choosing YD Commercial Cleaning Services."
    )
    pdf.drawString(
        50, height - 130, "Professional Cleaning. Reliable Service. Spotless Results."
    )

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    return FileResponse(
        buffer, as_attachment=True, filename=f"cleaning-report-booking-{booking.id}.pdf"
    )


@login_required
def email_cleaning_report(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponseForbidden("Only admin/staff can email reports.")

    customer = booking.customer

    if not customer.email:
        messages.error(request, "Customer does not have an email address.")
        return redirect("cleaning_report_detail", booking_id=booking.id)

    report, created = CleaningReport.objects.get_or_create(booking=booking)

    # Generate PDF in memory
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    y = height - 50

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, y, "YD Commercial Cleaning Services")
    y -= 35

    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(50, y, "CLEANING COMPLETION REPORT")
    y -= 35

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, f"Customer: {customer.full_name}")
    y -= 16
    pdf.drawString(50, y, f"Service: {booking.service_type}")
    y -= 16
    pdf.drawString(50, y, f"Date: {booking.booking_date}")
    y -= 16
    pdf.drawString(50, y, f"Time: {booking.booking_time}")
    y -= 16
    pdf.drawString(50, y, f"Address: {booking.address}")
    y -= 16
    pdf.drawString(50, y, f"Suburb/Postcode: {booking.suburb_postcode}")
    y -= 30

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "Completion Notes")
    y -= 20

    pdf.setFont("Helvetica", 11)
    notes = booking.notes or "No completion notes provided."

    for line in notes.split("\n"):
        pdf.drawString(50, y, line[:90])
        y -= 16

    pdf.showPage()
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, height - 80, "Report Completed")

    pdf.setFont("Helvetica", 11)
    pdf.drawString(
        50, height - 110, "Thank you for choosing YD Commercial Cleaning Services."
    )

    pdf.save()
    buffer.seek(0)

    subject = "Your Cleaning Completion Report"

    message = f"""
Hi {customer.full_name},

Your cleaning completion report is attached as a PDF.

Thank you for choosing YD Commercial Cleaning Services.

Kind regards,
YD Commercial Cleaning Services
"""

    email = EmailMessage(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [customer.email],
    )

    email.attach(
        f"cleaning-report-booking-{booking.id}.pdf",
        buffer.getvalue(),
        "application/pdf",
    )

    email.send(fail_silently=False)

    report.emailed_to_customer = True
    report.save(update_fields=["emailed_to_customer"])

    messages.success(
        request, "✅ Cleaning report PDF emailed to customer successfully."
    )

    return redirect("cleaning_report_detail", booking_id=booking.id)
