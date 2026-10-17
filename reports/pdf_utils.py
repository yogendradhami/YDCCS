
import os
from io import BytesIO
from xml.sax.saxutils import escape

from django.conf import settings
from django.utils import timezone
from PIL import Image as PILImage
from PIL import ImageOps

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle,
)
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


DARK_GREEN = colors.HexColor("#0B2C24")
GREEN = colors.HexColor("#174B3D")
MID_GREEN = colors.HexColor("#39745D")
LIGHT_GREEN = colors.HexColor("#F0F6F2")
BORDER = colors.HexColor("#DCE9E0")
MUTED = colors.HexColor("#66736E")


def _image_from_field(field, max_width, max_height):
    """Load and compress an image before embedding it in the report PDF."""
    try:
        if not field or not field.name:
            return None

        try:
            from pillow_heif import register_heif_opener

            register_heif_opener()
        except ImportError:
            pass

        with field.open("rb") as source:
            with PILImage.open(source) as original:
                image = ImageOps.exif_transpose(original)
                image.thumbnail((1600, 1400), PILImage.Resampling.LANCZOS)

                if "A" in image.getbands():
                    rgba = image.convert("RGBA")
                    image = PILImage.new("RGB", rgba.size, "white")
                    image.paste(rgba, mask=rgba.getchannel("A"))
                else:
                    image = image.convert("RGB")

                compressed = BytesIO()
                image.save(
                    compressed,
                    format="JPEG",
                    quality=76,
                    optimize=True,
                    progressive=True,
                )

        compressed.seek(0)
        flowable = Image(compressed, width=max_width, height=max_height)
        flowable._restrictSize(max_width, max_height)
        return flowable

    except Exception:
        return None


def generate_cleaning_report_pdf(booking):
    """Generate a branded cleaning completion PDF in memory."""
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title=f"Cleaning Completion Report - Booking {booking.pk}",
        author="YD Commercial Cleaning Services",
        subject="Cleaning service completion report",
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="YDTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=21,
        leading=26,
        textColor=DARK_GREEN,
        alignment=TA_CENTER,
        spaceAfter=5,
    ))

    styles.add(ParagraphStyle(
        name="YDSubtitle",
        parent=styles["Normal"],
        fontSize=9,
        leading=14,
        textColor=MUTED,
        alignment=TA_CENTER,
        spaceAfter=12,
    ))

    styles.add(ParagraphStyle(
        name="YDSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=GREEN,
        spaceBefore=12,
        spaceAfter=7,
        keepWithNext=True,
    ))

    styles.add(ParagraphStyle(
        name="YDBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#34483E"),
        wordWrap="CJK",
    ))

    styles.add(ParagraphStyle(
        name="YDLabel",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=MUTED,
        wordWrap="CJK",
    ))

    styles.add(ParagraphStyle(
        name="YDPhotoCaption",
        parent=styles["BodyText"],
        fontSize=8,
        leading=11,
        textColor=DARK_GREEN,
        alignment=TA_CENTER,
        wordWrap="CJK",
    ))

    styles.add(ParagraphStyle(
        name="YDClosing",
        parent=styles["BodyText"],
        fontSize=10,
        leading=15,
        textColor=DARK_GREEN,
        alignment=TA_CENTER,
    ))

    story = []

    # Brand header and logo
    logo_path = os.path.join(
        settings.BASE_DIR,
        "static",
        "images",
        "branding",
        "yd-email-logo.jpeg",
    )

    logo = None
    if os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=27 * mm, height=27 * mm)
            logo._restrictSize(27 * mm, 27 * mm)
        except (OSError, ValueError):
            logo = None

    brand = [
        Paragraph(
            "YD COMMERCIAL CLEANING SERVICES",
            styles["YDTitle"],
        ),
        Paragraph(
            "PROFESSIONAL CLEANING SOLUTIONS",
            styles["YDSubtitle"],
        ),
        Paragraph(
            "0430 049 865 | info@ydcleaning.com.au<br/>"
            "www.ydcleaning.com.au",
            styles["YDSubtitle"],
        ),
    ]

    if logo:
        header = Table(
            [[logo, brand]],
            colWidths=[32 * mm, 142 * mm],
        )
        header.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(header)
    else:
        story.extend(brand)

    story.append(Spacer(1, 5 * mm))

    divider = Table([[""]], colWidths=[174 * mm], rowHeights=[2])
    divider.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GREEN),
    ]))
    story.append(divider)
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph(
        "CLEANING COMPLETION REPORT",
        styles["YDTitle"],
    ))

    story.append(Paragraph(
        f"Report reference: YD-{booking.pk:06d}<br/>"
        f"Generated: {timezone.localtime().strftime('%d %B %Y, %I:%M %p')}",
        styles["YDSubtitle"],
    ))

    def add_section(title, fields):
        story.append(Paragraph(title, styles["YDSection"]))

        rows = []

        for label, value in fields:
            safe_label = escape(str(label))
            safe_value = escape(
                str(value if value not in (None, "") else "Not provided")
            ).replace("\n", "<br/>")

            rows.append([
                Paragraph(safe_label, styles["YDLabel"]),
                Paragraph(safe_value, styles["YDBody"]),
            ])

        table = Table(
            rows,
            colWidths=[43 * mm, 131 * mm],
            repeatRows=0,
            hAlign="LEFT",
        )

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), LIGHT_GREEN),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))

        story.append(table)

    customer = booking.customer
    employee = booking.assigned_employee

    add_section("SERVICE DETAILS", [
        ("Report reference", f"YD-{booking.pk:06d}"),
        ("Service", booking.get_service_type_display()),
        (
            "Booking date",
            booking.booking_date.strftime("%d %B %Y")
            if booking.booking_date else "Not provided",
        ),
        (
            "Scheduled time",
            booking.booking_time.strftime("%I:%M %p")
            if booking.booking_time else "Not provided",
        ),
        ("Status", booking.get_status_display()),
        ("Service address", booking.address),
        ("Suburb / postcode", booking.suburb_postcode),
        ("Quoted price", f"${booking.quoted_price}"),
    ])

    add_section("CUSTOMER DETAILS", [
        ("Customer", customer.full_name if customer else "Not provided"),
        ("Phone", getattr(customer, "phone", "") if customer else ""),
        ("Email", getattr(customer, "email", "") if customer else ""),
    ])

    add_section("SERVICE TEAM", [
        ("Assigned cleaner", employee.full_name if employee else "Not assigned"),
        ("Cleaner phone", getattr(employee, "phone", "") if employee else ""),
    ])

    story.append(Paragraph("COMPLETION NOTES", styles["YDSection"]))
    notes = booking.notes or "No completion notes were recorded."
    story.append(Paragraph(
        escape(notes).replace("\n", "<br/>"),
        styles["YDBody"],
    ))

    photos = list(booking.job_photos.order_by("uploaded_at"))

    for photo_type, title in (
        ("before", "BEFORE SERVICE PHOTOS"),
        ("after", "AFTER SERVICE PHOTOS"),
    ):
        matching = [
            photo for photo in photos
            if photo.photo_type == photo_type
        ]

        story.append(PageBreak())
        story.append(Paragraph(title, styles["YDTitle"]))
        story.append(Paragraph(
            "Photographic evidence recorded for this service.",
            styles["YDSubtitle"],
        ))

        if not matching:
            story.append(Paragraph(
                "No photographs were uploaded for this section.",
                styles["YDBody"],
            ))
            continue

        for index in range(0, len(matching), 2):
            cells = []

            for photo in matching[index:index + 2]:
                image = _image_from_field(
                    photo.image,
                    75 * mm,
                    65 * mm,
                )

                caption = Paragraph(
                    f"<b>{escape(photo.get_photo_type_display())}</b><br/>"
                    f"{photo.uploaded_at.strftime('%d %b %Y, %I:%M %p')}<br/>"
                    f"{escape(photo.notes or 'No photo notes')}",
                    styles["YDPhotoCaption"],
                )

                if image:
                    cells.append([image, caption])
                else:
                    cells.append([
                        Paragraph("Photo unavailable", styles["YDBody"]),
                        caption,
                    ])

            if len(cells) == 1:
                cells.append([
                    Paragraph("", styles["YDBody"]),
                    Paragraph("", styles["YDBody"]),
                ])

            photo_table = Table(
                [[cells[0], cells[1]]],
                colWidths=[87 * mm, 87 * mm],
                hAlign="LEFT",
            )

            photo_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]))

            story.append(KeepTogether([
                photo_table,
                Spacer(1, 5 * mm),
            ]))

    story.append(PageBreak())
    story.append(Paragraph(
        "VERIFICATION &amp; SIGNATURES",
        styles["YDTitle"],
    ))
    story.append(Spacer(1, 8 * mm))

    latest_photo = booking.job_photos.order_by("-uploaded_at").first()

    if latest_photo:
        for label, field, signed_at in (
            (
                "Employee signature",
                latest_photo.employee_signature,
                latest_photo.employee_signed_at,
            ),
            (
                "Customer signature",
                latest_photo.customer_signature,
                latest_photo.customer_signed_at,
            ),
        ):
            story.append(Paragraph(label, styles["YDSection"]))
            signature = _image_from_field(field, 75 * mm, 35 * mm)

            if signature:
                story.append(signature)
            else:
                story.append(Paragraph(
                    "No signature recorded.",
                    styles["YDBody"],
                ))

            if signed_at:
                story.append(Paragraph(
                    f"Signed: {signed_at.strftime('%d %B %Y, %I:%M %p')}",
                    styles["YDLabel"],
                ))
    else:
        story.append(Paragraph(
            "No job photos or signatures were recorded.",
            styles["YDBody"],
        ))

    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph(
        "Thank you for choosing YD Commercial Cleaning Services.<br/>"
        "Professional Cleaning Solutions",
        styles["YDClosing"],
    ))

    def draw_page(pdf_canvas, doc):
        pdf_canvas.saveState()
        pdf_canvas.setStrokeColor(BORDER)
        pdf_canvas.setLineWidth(0.5)
        pdf_canvas.line(
            18 * mm, 14 * mm,
            A4[0] - 18 * mm, 14 * mm,
        )
        pdf_canvas.setFont("Helvetica", 8)
        pdf_canvas.setFillColor(MUTED)
        pdf_canvas.drawString(
            18 * mm, 9 * mm,
            "YD Commercial Cleaning Services | Adelaide, South Australia",
        )
        pdf_canvas.drawRightString(
            A4[0] - 18 * mm, 9 * mm,
            f"Page {doc.page}",
        )
        pdf_canvas.restoreState()

    document.build(
        story,
        onFirstPage=draw_page,
        onLaterPages=draw_page,
    )

    buffer.seek(0)
    return buffer
