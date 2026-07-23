# ==========================================================
# File: payroll/views.py
# Purpose:
# Payroll dashboard, payroll generation, approval workflow,
# paid workflow and payslip PDF download.
# ==========================================================

from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from attendance.models import AttendanceLog
from dashboard.models import ActivityLog
from employees.models import Employee

from .models import PayrollRecord

# ==========================================================
# Activity Log Helper
# ==========================================================


def create_activity_log(user, action_type, title, description=""):
    ActivityLog.objects.create(
        user=user, action_type=action_type, title=title, description=description
    )


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
def generate_payroll(request):
    # Generate payroll for the last 7 days.
    today = timezone.now().date()
    period_end = today
    period_start = today - timedelta(days=6)

    employees = Employee.objects.filter(active=True)

    created_count = 0
    updated_count = 0

    for employee in employees:
        # Get completed attendance logs only.
        logs = AttendanceLog.objects.filter(
            employee=employee,
            check_in_time__date__gte=period_start,
            check_in_time__date__lte=period_end,
            check_out_time__isnull=False,
        )

        total_hours = Decimal("0.00")

        for log in logs:
            # Use total_hours saved in attendance log.
            if log.total_hours:
                total_hours += Decimal(str(log.total_hours))

        hourly_rate = Decimal(str(employee.hourly_rate or 0))
        gross_pay = total_hours * hourly_rate

        # Create or update payroll for same employee and period.
        payroll, created = PayrollRecord.objects.update_or_create(
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
        else:
            updated_count += 1

    # ==================================================
    # Activity Log
    # ==================================================

    create_activity_log(
        request.user,
        "payroll",
        "Payroll Generated",
        f"Created {created_count} payroll records and updated {updated_count} records.",
    )

    messages.success(
        request,
        f"✅ Payroll generated. Created: {created_count}, Updated: {updated_count}.",
    )

    return redirect("payroll_list")


@login_required
def approve_payroll(request, payroll_id):
    # Move payroll from Draft to Approved.
    payroll = get_object_or_404(PayrollRecord, id=payroll_id)

    payroll.status = "approved"
    payroll.save()

    # Activity Log
    # ==================================================

    create_activity_log(
        request.user,
        "payroll",
        "Payroll Approved",
        f"{payroll.employee.full_name} payroll approved for period ending {payroll.period_end}",
    )

    messages.success(request, "✅ Payroll approved successfully.")

    return redirect("payroll_list")


@login_required
def mark_payroll_paid(request, payroll_id):
    # Move payroll from Approved to Paid.
    payroll = get_object_or_404(PayrollRecord, id=payroll_id)

    payroll.status = "paid"
    payroll.save()

    # Activity Log
    # ==================================================

    create_activity_log(
        request.user,
        "payroll",
        "Payroll Approved",
        f"{payroll.employee.full_name} payroll approved for period ending {payroll.period_end}",
    )

    messages.success(request, "✅ Payroll marked as paid.")

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
