# ==========================================================
# File: payroll/views.py
# Purpose:
# Payroll dashboard, payroll generation, approval workflow,
# paid workflow and payslip PDF download.
# ==========================================================

import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from attendance.models import AttendanceLog
from dashboard.models import ActivityLog
from employees.models import Employee

import os
from io import BytesIO
from xml.sax.saxutils import escape

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)

from .models import PayrollRecord

logger = logging.getLogger(__name__)

# ==========================================================
# Activity Log Helper
# ==========================================================


def create_activity_log(user, action_type, title, description=""):
    ActivityLog.objects.create(
        user=user, action_type=action_type, title=title, description=description
    )


def send_payroll_email(payroll, stage):
    employee = payroll.employee
    recipient = (employee.email or "").strip()
    if not recipient and employee.user:
        recipient = (employee.user.email or "").strip()
    if not recipient:
        logger.warning(
            "Payroll email not sent: employee %s has no email address.", employee.pk
        )
        return False

    stage_copy = {
        "generated": "Your payroll has been generated and is pending approval.",
        "updated": "Your draft payroll was updated and is pending approval.",
        "approved": "Your payroll has been approved and is pending payment.",
        "paid": "Your payroll has been marked as paid.",
    }
    subject_copy = {
        "generated": "Payroll generated",
        "updated": "Payroll updated",
        "approved": "Payroll approved",
        "paid": "Payroll paid",
    }
    period = f"{payroll.period_start:%d %b %Y} to {payroll.period_end:%d %b %Y}"
    message = (
        f"Hi {employee.full_name},\n\n"
        f"{stage_copy[stage]}\n\n"
        f"Pay period: {period}\n"
        f"Hours worked: {payroll.total_hours}\n"
        f"Hourly rate: ${payroll.hourly_rate}\n"
        f"Gross pay before deductions: ${payroll.gross_pay}\n\n"
        "Please contact your manager if any details look incorrect.\n\n"
        "YD Commercial Cleaning Services"
    )

    try:
        sent = send_mail(
            f"{subject_copy[stage]}: {period}",
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            "Could not send %s payroll email for payroll record %s.",
            stage,
            payroll.pk,
        )
        return False
    return sent == 1


@login_required
def payroll_list(request):

    payroll_records = PayrollRecord.objects.select_related("employee").order_by(
        "-period_end"
    )

    total_payroll = sum(record.gross_pay for record in payroll_records)

    total_hours = sum(record.total_hours for record in payroll_records)

    total_employees = payroll_records.values("employee").distinct().count()

    draft_count = payroll_records.filter(status="draft").count()

    approved_count = payroll_records.filter(status="approved").count()

    paid_count = payroll_records.filter(status="paid").count()

    return render(
        request,
        "payroll/payroll_list.html",
        {
            "payroll_records": payroll_records,
            "total_payroll": total_payroll,
            "total_hours": total_hours,
            "total_employees": total_employees,
            "draft_count": draft_count,
            "approved_count": approved_count,
            "paid_count": paid_count,
        },
    )


@login_required
@require_POST
def generate_payroll(request):
    # Generate payroll for the last 7 days.
    today = timezone.localdate()
    period_end = today
    period_start = today - timedelta(days=6)

    employees = Employee.objects.filter(active=True)

    created_count = 0
    updated_count = 0
    unchanged_count = 0
    protected_count = 0
    payroll_emails_sent = 0
    payroll_emails_failed = 0

    for employee in employees:
        # Get completed attendance logs only.
        logs = AttendanceLog.objects.filter(
            employee=employee,
            check_in_time__date__gte=period_start,
            check_in_time__date__lte=period_end,
        ).filter(Q(check_out_time__isnull=False) | Q(total_hours__gt=0))

        total_hours = Decimal("0.00")

        for log in logs:
            # Attendance records are the source of payroll hours. Older logs
            # may have punches but no saved total, so derive those hours from
            # the recorded check-in/check-out times.
            recorded_hours = Decimal(str(log.total_hours or 0))
            if recorded_hours > 0:
                total_hours += recorded_hours
            elif log.check_in_time and log.check_out_time:
                elapsed_seconds = Decimal(
                    str((log.check_out_time - log.check_in_time).total_seconds())
                )
                total_hours += (elapsed_seconds / Decimal("3600")).quantize(
                    Decimal("0.01")
                )

        hourly_rate = Decimal(str(employee.hourly_rate or 0))
        gross_pay = total_hours * hourly_rate

        # Generate a new draft or refresh an existing draft for this period.
        # Approved and paid records remain unchanged when payroll is regenerated.
        payroll, created = PayrollRecord.objects.get_or_create(
            employee=employee,
            period_start=period_start,
            period_end=period_end,
            defaults={
                "total_hours": total_hours,
                "hourly_rate": hourly_rate,
                "gross_pay": gross_pay,
                "status": "draft",
            },
        )

        if created:
            created_count += 1
            email_stage = "generated"
        elif payroll.status == "draft":
            changed = any(
                getattr(payroll, field) != value
                for field, value in (
                    ("total_hours", total_hours),
                    ("hourly_rate", hourly_rate),
                    ("gross_pay", gross_pay),
                )
            )
            if changed:
                payroll.total_hours = total_hours
                payroll.hourly_rate = hourly_rate
                payroll.gross_pay = gross_pay
                payroll.save(
                    update_fields=[
                        "total_hours",
                        "hourly_rate",
                        "gross_pay",
                        "updated_at",
                    ]
                )
                updated_count += 1
                email_stage = "updated"
            else:
                unchanged_count += 1
                email_stage = "generated"
        else:
            protected_count += 1
            continue

        if send_payroll_email(payroll, email_stage):
            payroll_emails_sent += 1
        else:
            payroll_emails_failed += 1

    # ==================================================
    # Activity Log
    # ==================================================

    create_activity_log(
        request.user,
        "payroll",
        "Payroll Generated",
        (
            f"Created {created_count} payroll records, updated {updated_count}, "
            f"reused {unchanged_count} unchanged drafts, "
            f"preserved {protected_count} approved or paid records, and sent "
            f"{payroll_emails_sent} payroll emails."
        ),
    )

    messages.info(
        request,
        (
            f"Payroll generated. Created: {created_count}, updated: {updated_count}, "
            f"unchanged drafts: {unchanged_count}, "
            f"approved/paid preserved: {protected_count}. "
            f"Employee emails sent: {payroll_emails_sent}; "
            f"not sent: {payroll_emails_failed}."
        ),
    )

    return redirect("payroll_list")


@login_required
@require_POST
def approve_payroll(request, payroll_id):
    # Move payroll from Draft to Approved.
    payroll = get_object_or_404(PayrollRecord, id=payroll_id)

    if payroll.status != "draft":
        messages.warning(request, "Only draft payroll can be approved.")
        return redirect("payroll_list")

    payroll.status = "approved"
    payroll.save()
    email_sent = send_payroll_email(payroll, "approved")

    # Activity Log
    # ==================================================

    create_activity_log(
        request.user,
        "payroll",
        "Payroll Approved",
        f"{payroll.employee.full_name} payroll approved for period ending {payroll.period_end}",
    )

    if email_sent:
        messages.success(request, "Payroll approved and employee emailed.")
    else:
        messages.warning(
            request,
            "Payroll approved, but the employee email could not be sent. "
            "Check their email address and the mail service settings.",
        )

    return redirect("payroll_list")



def generate_payroll_pdf(payroll):
    """Generate a professional, branded employee payslip PDF."""

    employee = payroll.employee
    buffer = BytesIO()

    green = colors.HexColor("#0B2C24")
    light_green = colors.HexColor("#EAF3EE")
    muted = colors.HexColor("#65736C")
    border = colors.HexColor("#DCE5DF")

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=20 * mm,
        title=f"Employee Payslip - {employee.full_name}",
        author="YD Commercial Cleaning Services",
    )

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="CompanyTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=19,
            leading=24,
            textColor=green,
            alignment=TA_CENTER,
            spaceAfter=4,
        )
    )

    styles.add(
        ParagraphStyle(
            name="DocumentTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=20,
            textColor=green,
            alignment=TA_CENTER,
            spaceBefore=12,
            spaceAfter=6,
        )
    )

    styles.add(
        ParagraphStyle(
            name="MutedText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=muted,
            alignment=TA_CENTER,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=green,
            spaceBefore=12,
            spaceAfter=7,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TotalLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=green,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TotalValue",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=green,
            alignment=TA_CENTER,
        )
    )

    def paragraph(value, style="TableText"):
        return Paragraph(
            escape(str(value if value not in (None, "") else "Not provided")),
            styles[style],
        )

    def draw_footer(canvas, document):
        canvas.saveState()

        canvas.setStrokeColor(border)
        canvas.setLineWidth(0.6)
        canvas.line(
            18 * mm,
            14 * mm,
            A4[0] - 18 * mm,
            14 * mm,
        )

        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(muted)
        canvas.drawString(
            18 * mm,
            9 * mm,
            "YD Commercial Cleaning Services | Confidential Employee Payslip",
        )
        canvas.drawRightString(
            A4[0] - 18 * mm,
            9 * mm,
            f"Page {document.page}",
        )

        canvas.restoreState()

    story = []

    # Company logo, if available.
    logo_path = os.path.join(
        settings.BASE_DIR,
        "static",
        "images",
        "branding",
        "yd-email-logo.jpeg",
    )

    if os.path.isfile(logo_path):
        logo = Image(logo_path, width=25 * mm, height=25 * mm)
        logo.hAlign = "CENTER"
        logo._restrictSize(25 * mm, 25 * mm)
        story.extend([logo, Spacer(1, 4 * mm)])

    story.append(
        Paragraph(
            "YD Commercial Cleaning Services",
            styles["CompanyTitle"],
        )
    )
    story.append(
        Paragraph(
            "PROFESSIONAL CLEANING SOLUTIONS",
            styles["MutedText"],
        )
    )
    story.append(Spacer(1, 3 * mm))
    story.append(
        Paragraph("EMPLOYEE PAYSLIP", styles["DocumentTitle"])
    )
    story.append(
        Paragraph(
            "ABN: 95 916 203 175<br/>"
            "2/10 Da Costa Avenue, Prospect SA 5082<br/>"
            "0430 049 865 | info@ydcleaning.com.au<br/>"
            "www.ydcleaning.com.au",
            styles["MutedText"],
        )
    )
    story.append(Spacer(1, 8 * mm))

    # Payroll status and reference.
    status_data = [
        [
            paragraph("PAYROLL REFERENCE"),
            paragraph("PAYMENT STATUS"),
        ],
        [
            paragraph(f"PAY-{payroll.pk:06d}"),
            paragraph(payroll.get_status_display()),
        ],
    ]

    status_table = Table(
        status_data,
        colWidths=[doc.width / 2, doc.width / 2],
    )
    status_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), light_green),
                ("TEXTCOLOR", (0, 0), (-1, 0), green),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, border),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(status_table)

    # Employee details.
    story.append(
        Paragraph("EMPLOYEE DETAILS", styles["SectionTitle"])
    )

    employee_data = [
        [paragraph("Employee name"), paragraph(employee.full_name)],
        [paragraph("Employee email"), paragraph(employee.email)],
        [paragraph("Employee phone"), paragraph(employee.phone)],
        [paragraph("Position"), paragraph(employee.get_role_display())],
    ]

    employee_table = Table(
        employee_data,
        colWidths=[doc.width * 0.32, doc.width * 0.68],
    )
    employee_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), light_green),
                ("GRID", (0, 0), (-1, -1), 0.5, border),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(employee_table)

    # Pay period details.
    story.append(
        Paragraph("PAY PERIOD DETAILS", styles["SectionTitle"])
    )

    paid_at = timezone.localtime()

    period_data = [
        [paragraph("Pay period start"), paragraph(payroll.period_start.strftime("%d %B %Y"))],
        [paragraph("Pay period end"), paragraph(payroll.period_end.strftime("%d %B %Y"))],
        [paragraph("Payment recorded"), paragraph(paid_at.strftime("%d %B %Y, %I:%M %p") if payroll.status == "paid" else "Not marked as paid")],
    ]

    period_table = Table(
        period_data,
        colWidths=[doc.width * 0.32, doc.width * 0.68],
    )
    period_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), light_green),
                ("GRID", (0, 0), (-1, -1), 0.5, border),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(period_table)

    # Earnings breakdown.
    story.append(
        Paragraph("EARNINGS SUMMARY", styles["SectionTitle"])
    )

    total_hours = payroll.total_hours or 0
    hourly_rate = payroll.hourly_rate or 0
    gross_pay = payroll.gross_pay or 0

    earnings_data = [
        [
            paragraph("Description"),
            paragraph("Quantity / Rate"),
            paragraph("Amount (AUD)"),
        ],
        [
            paragraph("Ordinary hours"),
            paragraph(f"{total_hours} hours"),
            paragraph(f"${gross_pay:,.2f}"),
        ],
        [
            paragraph("Hourly rate"),
            paragraph(f"${hourly_rate:,.2f} per hour"),
            paragraph("-"),
        ],
    ]

    earnings_table = Table(
        earnings_data,
        colWidths=[
            doc.width * 0.40,
            doc.width * 0.30,
            doc.width * 0.30,
        ],
    )
    earnings_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), green),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, border),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(earnings_table)
    story.append(Spacer(1, 5 * mm))

    total_table = Table(
        [
            [
                Paragraph(
                    "GROSS EARNINGS",
                    styles["TotalLabel"],
                ),
                Paragraph(
                    f"${gross_pay:,.2f} AUD",
                    styles["TotalValue"],
                ),
            ]
        ],
        colWidths=[doc.width * 0.45, doc.width * 0.55],
    )
    total_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), light_green),
                ("BOX", (0, 0), (-1, -1), 0.8, green),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    story.append(total_table)
    story.append(Spacer(1, 5 * mm))

    story.append(
        Paragraph(
            "<b>Important payroll information</b><br/>"
            "This document reports the gross earnings recorded in the "
            "company payroll system. Tax, superannuation, deductions and "
            "net pay are not itemised in this report because they are not "
            "currently recorded in this payroll calculation. Please contact "
            "your manager if you believe any recorded details are incorrect.",
            styles["TableText"],
        )
    )

    story.append(Spacer(1, 8 * mm))
    story.append(
        Paragraph(
            "Thank you for your contribution to YD Commercial Cleaning Services.",
            styles["MutedText"],
        )
    )

    doc.build(
        story,
        onFirstPage=draw_footer,
        onLaterPages=draw_footer,
    )

    buffer.seek(0)
    return buffer





@login_required
def mark_payroll_paid(request, payroll_id):
    payroll = get_object_or_404(
        PayrollRecord.objects.select_related("employee"),
        id=payroll_id,
    )

    # Preserve the current workflow: mark the payroll as paid.
    payroll.status = "paid"
    payroll.save(update_fields=["status", "updated_at"])

    create_activity_log(
        request.user,
        "payroll",
        "Payroll Marked as Paid",
        (
            f"{payroll.employee.full_name} payroll marked as paid "
            f"for {payroll.period_start} to {payroll.period_end}."
        ),
    )

    employee = payroll.employee

    if not employee.email:
        messages.warning(
            request,
            "Payroll was marked as paid, but the employee has no email address. "
            "Add an email address to send the payslip.",
        )
        return redirect("payroll_list")

    try:
        paid_at = timezone.localtime()

        pdf_buffer = generate_payroll_pdf(payroll)

        context = {
            "employee": employee,
            "payroll": payroll,
            "paid_at": paid_at,
            "payroll_reference": f"PAY-{payroll.pk:06d}",
        }

        text_body = render_to_string(
            "emails/payroll/payroll_paid.txt",
            context,
        )
        html_body = render_to_string(
            "emails/payroll/payroll_paid.html",
            context,
        )

        email = EmailMultiAlternatives(
            subject=(
                f"Payroll paid: "
                f"{payroll.period_start:%d %b %Y} to "
                f"{payroll.period_end:%d %b %Y}"
            ),
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[employee.email],
            reply_to=["info@ydcleaning.com.au"],
        )

        email.attach_alternative(html_body, "text/html")

        email.attach(
            filename=(
                f"payslip-{payroll.pk}-"
                f"{payroll.period_start}-to-{payroll.period_end}.pdf"
            ),
            content=pdf_buffer.getvalue(),
            mimetype="application/pdf",
        )

        email.send(fail_silently=False)

    except Exception:
        # Do not revert the paid status just because email delivery failed.
        messages.warning(
            request,
            "Payroll was marked as paid, but the email or PDF attachment "
            "could not be sent. Check your email configuration and logs.",
        )
        return redirect("payroll_list")

    messages.success(
        request,
        f"Payroll marked as paid. The PDF payslip was emailed to {employee.email}.",
    )

    return redirect("payroll_list")


@login_required
def download_payslip_pdf(request, payroll_id):
    # Download one payroll record as a simple PDF payslip.
    payroll = get_object_or_404(
        PayrollRecord.objects.select_related("employee"), id=payroll_id
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="payslip-{payroll.employee.full_name}-{payroll.period_end}.pdf"'
    )

    pdf = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    y = height - 60

    # Header
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, y, "YD Commercial Cleaning Services")
    y -= 30

    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, y, "Employee Payslip")
    y -= 40

    # Employee information
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Employee Details")
    y -= 22

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, f"Employee: {payroll.employee.full_name}")
    y -= 18
    pdf.drawString(50, y, f"Email: {payroll.employee.email or 'N/A'}")
    y -= 18
    pdf.drawString(50, y, f"Phone: {payroll.employee.phone or 'N/A'}")
    y -= 35

    # Payroll period
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Pay Period")
    y -= 22

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, f"Period Start: {payroll.period_start}")
    y -= 18
    pdf.drawString(50, y, f"Period End: {payroll.period_end}")
    y -= 18
    pdf.drawString(50, y, f"Status: {payroll.get_status_display()}")
    y -= 35

    # Payroll calculation
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Earnings")
    y -= 22

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, f"Total Hours: {payroll.total_hours}")
    y -= 18
    pdf.drawString(50, y, f"Hourly Rate: ${payroll.hourly_rate}")
    y -= 18
    pdf.drawString(50, y, f"Gross Pay: ${payroll.gross_pay}")
    y -= 40

    # Footer note
    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(50, y, "This payslip was generated by YD Commercial Cleaning CRM.")

    pdf.showPage()
    pdf.save()

    return response


# ==========================================================
# Employee Payslips
# ==========================================================


@login_required
def employee_payslips(request):
    # Get the logged-in employee profile.
    employee = get_object_or_404(Employee, user=request.user)

    # Only show payslips belonging to this employee.
    payroll_records = PayrollRecord.objects.filter(employee=employee).order_by(
        "-period_end"
    )

    return render(
        request,
        "employees/employee_payslips.html",
        {
            "employee": employee,
            "payroll_records": payroll_records,
        },
    )
