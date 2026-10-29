import os
from io import BytesIO

from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def generate_invoice_pdf(invoice):
    booking = invoice.booking
    customer = booking.customer

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4

    logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logo.jpeg")

    if os.path.exists(logo_path):
        pdf.drawImage(
            logo_path,
            45,
            height - 120,
            width=85,
            height=85,
            preserveAspectRatio=True,
            mask="auto",
        )

    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(145, height - 55, "YD Commercial Cleaning Services")

    pdf.setFont("Helvetica", 9)
    pdf.drawString(145, height - 75, "ABN: 95 916 203 175")
    pdf.drawString(145, height - 90, "2/10 Da Costa Avenue, Prospect SA 5082")
    pdf.drawString(145, height - 105, "Phone: 0430 049 865")
    pdf.drawString(145, height - 120, "Email: info@ydcleaning.com.au")

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawRightString(width - 45, height - 95, invoice.invoice_number)

    pdf.setFont("Helvetica", 10)
    pdf.drawRightString(width - 45, height - 115, f"Issue Date: {invoice.issue_date}")
    pdf.drawRightString(width - 45, height - 133, f"Due Date: {invoice.due_date}")
    pdf.drawRightString(
        width - 45, height - 151, f"Status: {invoice.get_status_display()}"
    )

    pdf.line(45, height - 170, width - 45, height - 170)

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(45, height - 200, "CLIENT INFORMATION")

    pdf.setFont("Helvetica", 10)
    y = height - 220
    pdf.drawString(45, y, f"Name: {customer.full_name if customer else 'No customer'}")
    y -= 16
    pdf.drawString(45, y, f"Phone: {customer.phone if customer else 'Not provided'}")
    y -= 16
    pdf.drawString(45, y, f"Email: {customer.email if customer else 'Not provided'}")
    y -= 16
    pdf.drawString(45, y, f"Address: {customer.address if customer else 'Not provided'}")

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(330, height - 200, "JOB DETAILS")

    pdf.setFont("Helvetica", 10)
    y2 = height - 220
    pdf.drawString(330, y2, f"Service: {booking.service_type}")
    y2 -= 16
    pdf.drawString(330, y2, f"Date: {booking.booking_date}")
    y2 -= 16
    pdf.drawString(330, y2, f"Time: {booking.booking_time}")
    y2 -= 16
    pdf.drawString(330, y2, f"Suburb: {booking.suburb_postcode}")
    y2 -= 16
    pdf.drawString(330, y2, f"Address: {booking.address[:38]}")

    work_orders = list(invoice.work_orders.all())
    if work_orders:
        line_items = [
            (item.description, item.price)
            for item in work_orders
        ]
    else:
        line_items = [(booking.service_type, invoice.amount)]

    def draw_table_header(y):
        pdf.setFillColorRGB(0.94, 0.96, 0.98)
        pdf.rect(45, y, width - 90, 28, fill=True, stroke=False)
        pdf.setFillColorRGB(0, 0, 0)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(55, y + 9, "Work order")
        pdf.drawRightString(385, y + 9, "Qty")
        pdf.drawRightString(470, y + 9, "Price")
        pdf.drawRightString(width - 55, y + 9, "Total")

    table_top = height - 330
    draw_table_header(table_top)
    row_y = table_top - 32
    for position, (description, price) in enumerate(line_items, start=1):
        if row_y < 245:
            pdf.showPage()
            draw_table_header(height - 55)
            row_y = height - 100
        pdf.setFont("Helvetica", 10)
        pdf.drawString(55, row_y, f"{position}. {description[:48]}")
        pdf.drawRightString(385, row_y, "1")
        pdf.drawRightString(470, row_y, f"${price:.2f}")
        pdf.drawRightString(width - 55, row_y, f"${price:.2f}")
        pdf.line(45, row_y - 12, width - 45, row_y - 12)
        row_y -= 24

    description_lines = (invoice.description or "").splitlines()
    if description_lines:
        if row_y - (len(description_lines) + 1) * 14 < 220:
            pdf.showPage()
            row_y = height - 80
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(45, row_y, "Invoice description")
        pdf.setFont("Helvetica", 9)
        for line in description_lines:
            row_y -= 14
            pdf.drawString(45, row_y, line[:95])

    discount_value = getattr(invoice, "discount_amount", 0)

    pdf.setFont("Helvetica", 11)
    pdf.drawString(360, 190, "Subtotal:")
    pdf.drawRightString(width - 55, 190, f"${invoice.amount:.2f}")

    pdf.drawString(360, 168, "Discount:")
    pdf.drawRightString(width - 55, 168, f"-${discount_value:.2f}")

    pdf.drawString(360, 146, "GST 10%:")
    pdf.drawRightString(width - 55, 146, f"${invoice.gst_amount:.2f}")

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(360, 112, "Total:")
    pdf.drawRightString(width - 55, 112, f"${invoice.total_amount:.2f}")

    pdf.line(45, 85, width - 45, 85)

    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(
        width / 2, 65, "Thank you for choosing YD Commercial Cleaning Services."
    )
    pdf.drawCentredString(
        width / 2, 50, "Professional Cleaning. Reliable Service. Spotless Results."
    )

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    return buffer
