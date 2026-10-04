from django.shortcuts import redirect

from employees.models import Employee
from induction.models import EmployeeInduction


class EmployeeInductionMiddleware:
    """
    Prevent active employees from accessing protected employee
    functionality until their mandatory induction is completed.

    Important:
    - Only applies to authenticated users.
    - Only applies to /employee/ URLs.
    - Allows the induction page itself.
    - Allows logout/login-related URLs.
    - Does not interfere with static/media/admin/dashboard URLs.
    """

    EXCLUDED_PATHS = (
        "/employee/induction/",
        "/employee/logout/",
        "/employee/login/",
        "/accounts/",
        "/admin/",
        "/static/",
        "/media/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Anonymous users are not affected.
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Only protect employee portal URLs.
        if not request.path.startswith("/employee/"):
            return self.get_response(request)

        # Don't interfere with allowed URLs.
        if any(
            request.path.startswith(path)
            for path in self.EXCLUDED_PATHS
        ):
            return self.get_response(request)

        # Find the employee account associated with this user.
        try:
            employee = (
                Employee.objects
                .select_related("induction")
                .get(
                    user=request.user,
                    active=True,
                )
            )

        except Employee.DoesNotExist:
            # User is authenticated but isn't an active employee.
            return self.get_response(request)

        except EmployeeInduction.DoesNotExist:
            # Employee has no induction record.
            return redirect("employee_induction")

        induction = employee.induction

        # If induction is incomplete, redirect to induction.
        if induction.status != "completed":
            return redirect("employee_induction")

        return self.get_response(request)