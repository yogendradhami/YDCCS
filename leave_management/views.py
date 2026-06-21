from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from employees.models import Employee

from .forms import EmployeeLeaveRequestForm, LeaveRequestForm
from .models import LeaveRequest


def get_logged_in_employee(request):
    try:
        return request.user.employee_profile
    except Exception:
        return Employee.objects.filter(user=request.user).first()


@login_required
def leave_list(request):
    today = timezone.now().date()

    leave_requests = LeaveRequest.objects.select_related("employee").all()

    return render(
        request,
        "leave_list.html",
        {
            "leave_requests": leave_requests,
            "pending_count": leave_requests.filter(status="pending").count(),
            "approved_count": leave_requests.filter(status="approved").count(),
            "rejected_count": leave_requests.filter(status="rejected").count(),
            "currently_on_leave": leave_requests.filter(
                status="approved", start_date__lte=today, end_date__gte=today
            ).count(),
        },
    )


@login_required
def add_leave_request(request):
    if request.method == "POST":
        form = LeaveRequestForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "✅ Leave request added successfully.")
            return redirect("leave_list")
    else:
        form = LeaveRequestForm()

    return render(
        request,
        "leave_form.html",
        {
            "form": form,
            "page_title": "Add Leave Request",
            "button_text": "Save Leave Request",
        },
    )


@login_required
def employee_leave_history(request):
    employee = get_logged_in_employee(request)

    leave_requests = (
        LeaveRequest.objects.filter(employee=employee).order_by("-created_at")
        if employee
        else []
    )

    return render(
        request,
        "employee_leave_history.html",
        {
            "employee": employee,
            "leave_requests": leave_requests,
        },
    )


@login_required
def employee_apply_leave(request):
    employee = get_logged_in_employee(request)

    if not employee:
        messages.error(request, "❌ Employee profile not found.")
        return redirect("/employee/dashboard/")

    if request.method == "POST":
        form = EmployeeLeaveRequestForm(request.POST)

        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.employee = employee
            leave_request.status = "pending"
            leave_request.save()

            messages.success(
                request,
                "✅ Leave request submitted successfully. It is now waiting for approval.",
            )

            return redirect("/employee/leave/")
        else:
            messages.error(request, "❌ Please check the leave form and try again.")

    else:
        form = EmployeeLeaveRequestForm()

    return render(
        request,
        "leave_request_form.html",
        {
            "form": form,
            "employee": employee,
        },
    )


@login_required
def approve_leave_request(request, leave_id):
    leave_request = get_object_or_404(LeaveRequest, id=leave_id)

    if request.method == "POST":
        leave_request.status = "approved"
        leave_request.save()
        messages.success(request, "✅ Leave request approved.")

    return redirect("leave_list")


@login_required
def reject_leave_request(request, leave_id):
    leave_request = get_object_or_404(LeaveRequest, id=leave_id)

    if request.method == "POST":
        leave_request.status = "rejected"
        leave_request.save()
        messages.success(request, "❌ Leave request rejected.")

    return redirect("leave_list")
