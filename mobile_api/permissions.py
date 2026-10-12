
from rest_framework.permissions import BasePermission

from customers.models import Customer
from employees.models import Employee


class IsCustomer(BasePermission):
    message = "A linked customer account is required."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and Customer.objects.filter(user=request.user).exists()
        )


class IsEmployee(BasePermission):
    message = "An active employee account is required."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and Employee.objects.filter(
                user=request.user,
                active=True,
            ).exists()
        )


class IsCompanyAdmin(BasePermission):
    message = "Company administrator access is required."

    def has_permission(self, request, view):
        user = request.user

        return (
            user.is_authenticated
            and user.is_active
            and (
                user.is_superuser
                or user.has_perm("bookings.view_booking")
            )
        )
