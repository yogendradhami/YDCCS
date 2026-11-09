from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import AttendanceLogForm
from .models import AttendanceLog


@login_required
@permission_required("attendance.view_attendancelog", raise_exception=True)
def attendance_log_detail(request, attendance_id):
    attendance = get_object_or_404(
        AttendanceLog.objects.select_related(
            "employee",
            "booking",
            "booking__customer",
            "roster",
        ),
        pk=attendance_id,
    )
    return render(
        request,
        "attendance/attendance_log_detail.html",
        {"attendance": attendance},
    )


@login_required
@permission_required("attendance.add_attendancelog", raise_exception=True)
@require_http_methods(["GET", "POST"])
def attendance_log_create(request):
    form = AttendanceLogForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        attendance = form.save()
        messages.success(
            request,
            f"Attendance for {attendance.employee.full_name} was added.",
        )
        return redirect("attendance_report")

    return render(
        request,
        "attendance/attendance_log_form.html",
        {"form": form, "editing": False},
    )


@login_required
@permission_required("attendance.change_attendancelog", raise_exception=True)
@require_http_methods(["GET", "POST"])
def attendance_log_edit(request, attendance_id):
    attendance = get_object_or_404(
        AttendanceLog.objects.select_related("employee", "booking"),
        pk=attendance_id,
        source=AttendanceLog.Source.PORTAL,
    )
    form = AttendanceLogForm(request.POST or None, instance=attendance)
    if request.method == "POST" and form.is_valid():
        attendance = form.save()
        messages.success(
            request,
            f"Attendance for {attendance.employee.full_name} was updated.",
        )
        return redirect("attendance_report")

    return render(
        request,
        "attendance/attendance_log_form.html",
        {"form": form, "editing": True, "attendance": attendance},
    )


@login_required
@permission_required("attendance.delete_attendancelog", raise_exception=True)
@require_http_methods(["GET", "POST"])
def attendance_log_delete(request, attendance_id):
    attendance = get_object_or_404(
        AttendanceLog.objects.select_related("employee", "booking"),
        pk=attendance_id,
        source=AttendanceLog.Source.PORTAL,
    )
    if request.method == "POST":
        employee_name = attendance.employee.full_name
        attendance.delete()
        messages.success(request, f"Attendance for {employee_name} was deleted.")
        return redirect("attendance_report")

    return render(
        request,
        "attendance/attendance_log_confirm_delete.html",
        {"attendance": attendance},
    )
