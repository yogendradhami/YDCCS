# ==========================================================
# File: employees/profile_forms.py
# Purpose:
# Employee profile update form
# Password change form
# ==========================================================

from django import forms
from django.contrib.auth.forms import PasswordChangeForm

from .models import Employee


class EmployeeProfileForm(forms.ModelForm):
    """
    Employee profile update form.
    """

    class Meta:
        model = Employee

        fields = [
            "full_name",
            "email",
            "phone",
            "address",
            "availability",
            "notes",
        ]

        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "availability": forms.Select(attrs={"class": "form-control"}),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
        }


class EmployeePasswordForm(PasswordChangeForm):
    """
    Employee password change form.
    """

    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )

    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )

    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )
