from django.shortcuts import redirect
from django.contrib import messages


def employee_required(view_func):
    def wrapper(request, *args, **kwargs):

        if not request.user.is_authenticated:
            return redirect("employee_login")

        if not hasattr(request.user, "employee_profile"):
            messages.error(request, "Employee access only.")
            return redirect("employee_login")

        if not request.user.employee_profile.active:
            messages.error(request, "Your employee account is not active.")
            return redirect("employee_login")

        return view_func(request, *args, **kwargs)

    return wrapper