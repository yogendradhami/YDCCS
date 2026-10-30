import os
from html import escape
from io import BytesIO

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


NAVY = colors.HexColor("#0f172a")
BLUE = colors.HexColor("#0759c9")
SLATE = colors.HexColor("#475569")
MUTED = colors.HexColor("#64748b")
PALE = colors.HexColor("#f8fafc")
BORDER = colors.HexColor("#e2e8f0")
WHITE = colors.white


def _safe_paragraph(value, style):
    text = escape(str(value or "")).replace("\n", "<br/>")
    return Paragraph(text or " ", style)


def _format_money(value):
    return f"${value:,.2f}"


def _footer(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(BORDER)
    canvas.line(18 * mm, 16 * mm, A4[0] - 18 * mm, 16 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(
        A4[0] / 2,
        10 * mm,
        "YD Commercial Cleaning Services  |  Professional Cleaning. Reliable Service.",
    )
    canvas.restoreState()


def generate_invoice_pdf(invoice):
    booking = invoice.booking
    customer = booking.customer
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=22 * mm,
        title=f"Invoice {invoice.invoice_number}",
        author="YD Commercial Cleaning Services",
    )
    content_width = A4[0] - 36 * mm
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CompanyName",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=20,
            textColor=NAVY,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CompanyDetails",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=MUTED,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="InvoiceTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=23,
            leading=27,
            textColor=NAVY,
            alignment=TA_RIGHT,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="InvoiceMeta",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=13,
            textColor=SLATE,
            alignment=TA_RIGHT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=BLUE,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            name="PartyTitle",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=NAVY,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="PartyDetail",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=SLATE,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableHeader",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=NAVY,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableCell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=SLATE,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableCellRight",
            parent=styles["TableCell"],
            alignment=TA_RIGHT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TotalLabel",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=SLATE,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TotalValue",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=13,
            textColor=NAVY,
            alignment=TA_RIGHT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="GrandTotal",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=BLUE,
        )
    )
    styles.add(
        ParagraphStyle(
            name="GrandTotalRight",
            parent=styles["GrandTotal"],
            alignment=TA_RIGHT,
        )
    )

    company_lines = [
        _safe_paragraph("YD Commercial Cleaning Services", styles["CompanyName"]),
        _safe_paragraph("ABN 95 916 203 175", styles["CompanyDetails"]),
        _safe_paragraph(
            "2/10 Da Costa Avenue, Prospect SA 5082", styles["CompanyDetails"]
        ),
        _safe_paragraph(
            "0430 049 865  |  info@ydcleaning.com.au", styles["CompanyDetails"]
        ),
    ]
    logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logo.jpeg")
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=22 * mm, height=22 * mm, kind="proportional")
        company_block = Table(
            [[logo, company_lines]],
            colWidths=[25 * mm, 84 * mm],
            hAlign="LEFT",
        )
        company_block.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
    else:
        company_block = company_lines

    due_date = invoice.due_date.strftime("%d %b %Y") if invoice.due_date else "Not set"
    issued_date = invoice.issue_date.strftime("%d %b %Y")
    invoice_meta = [
        Paragraph("INVOICE", styles["InvoiceTitle"]),
        Paragraph(escape(invoice.invoice_number), styles["InvoiceMeta"]),
        Paragraph(f"Issued {issued_date}", styles["InvoiceMeta"]),
        Paragraph(f"Due {due_date}", styles["InvoiceMeta"]),
        Paragraph(escape(invoice.get_status_display().upper()), styles["InvoiceMeta"]),
    ]
    header = Table(
        [[company_block, invoice_meta]],
        colWidths=[content_width * 0.62, content_width * 0.38],
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LINEBELOW", (0, 0), (-1, -1), 0.8, BORDER),
            ]
        )
    )

    bill_to = [
        Paragraph("BILL TO", styles["SectionHeading"]),
        _safe_paragraph(
            customer.full_name if customer else "No customer",
            styles["PartyTitle"],
        ),
        _safe_paragraph(
            customer.email if customer and customer.email else "Email not provided",
            styles["PartyDetail"],
        ),
        _safe_paragraph(
            customer.phone if customer and customer.phone else "Phone not provided",
            styles["PartyDetail"],
        ),
        _safe_paragraph(
            customer.address if customer and customer.address else "Address not provided",
            styles["PartyDetail"],
        ),
    ]
    booking_date = booking.booking_date.strftime("%d %b %Y")
    booking_time = booking.booking_time.strftime("%I:%M %p").lstrip("0")
    service_details = [
        Paragraph("SERVICE DETAILS", styles["SectionHeading"]),
        _safe_paragraph(booking.service_type, styles["PartyTitle"]),
        _safe_paragraph(f"Date: {booking_date}", styles["PartyDetail"]),
        _safe_paragraph(f"Time: {booking_time}", styles["PartyDetail"]),
        _safe_paragraph(
            f"Property: {booking.address}, {booking.suburb_postcode}",
            styles["PartyDetail"],
        ),
    ]
    parties = Table(
        [[bill_to, service_details]],
        colWidths=[content_width / 2 - 4 * mm, content_width / 2 - 4 * mm],
        hAlign="LEFT",
    )
    parties.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.7, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 11),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )

    work_orders = list(invoice.work_orders.all())
    item_rows = [[
        Paragraph("DESCRIPTION", styles["TableHeader"]),
        Paragraph("QTY", styles["TableHeader"]),
        Paragraph("UNIT PRICE", styles["TableHeader"]),
        Paragraph("TOTAL", styles["TableHeader"]),
    ]]
    if work_orders:
        for position, work_order in enumerate(work_orders, start=1):
            title = _safe_paragraph(
                f"{position}. {work_order.description}",
                styles["TableCell"],
            )
            if position == 1 and invoice.description:
                title = [
                    title,
                    _safe_paragraph(invoice.description, styles["PartyDetail"]),
                ]
            item_rows.append(
                [
                    title,
                    Paragraph("1", styles["TableCell"]),
                    Paragraph(_format_money(work_order.price), styles["TableCellRight"]),
                    Paragraph(_format_money(work_order.price), styles["TableCellRight"]),
                ]
            )
    else:
        item_rows.append(
            [
                [
                    _safe_paragraph(
                        f"1. {booking.service_type}",
                        styles["TableCell"],
                    ),
                    _safe_paragraph(invoice.description, styles["PartyDetail"]),
                ],
                Paragraph("1", styles["TableCell"]),
                Paragraph(_format_money(invoice.amount), styles["TableCellRight"]),
                Paragraph(_format_money(invoice.amount), styles["TableCellRight"]),
            ]
        )
    item_table = Table(
        item_rows,
        colWidths=[
            content_width * 0.52,
            content_width * 0.10,
            content_width * 0.19,
            content_width * 0.19,
        ],
        repeatRows=1,
        hAlign="LEFT",
    )
    item_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("TEXTCOLOR", (0, 0), (-1, 0), NAVY),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, BORDER),
                ("LINEBELOW", (0, 1), (-1, -1), 0.5, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )

    notes = [
        Paragraph("NOTES", styles["SectionHeading"]),
        _safe_paragraph(
            invoice.notes or "Thank you for choosing YD Commercial Cleaning Services.",
            styles["PartyDetail"],
        ),
    ]
    totals = [
        [Paragraph("Subtotal", styles["TotalLabel"]), Paragraph(_format_money(invoice.amount), styles["TotalValue"])],
        [Paragraph("Discount", styles["TotalLabel"]), Paragraph(_format_money(invoice.discount_amount), styles["TotalValue"])],
        [Paragraph("GST", styles["TotalLabel"]), Paragraph(_format_money(invoice.gst_amount), styles["TotalValue"])],
        [Paragraph("Total", styles["GrandTotal"]), Paragraph(_format_money(invoice.total_amount), styles["GrandTotalRight"])],
    ]
    totals_table = Table(totals, colWidths=[40 * mm, 40 * mm])
    totals_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LINEABOVE", (0, 3), (-1, 3), 0.8, BORDER),
            ]
        )
    )
    summary = Table(
        [[notes, totals_table]],
        colWidths=[content_width - 86 * mm, 86 * mm],
        hAlign="LEFT",
    )
    summary.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    story = [
        header,
        Spacer(1, 8 * mm),
        parties,
        Spacer(1, 8 * mm),
        item_table,
        Spacer(1, 9 * mm),
        summary,
    ]
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buffer.seek(0)
    return buffer
