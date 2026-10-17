# ==========================================================
# File: employees/profile_forms.py
# Purpose:
# Employee profile update form
# Password change form
# ==========================================================

from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError

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
            "image",
            "notes",
        ]

        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "availability": forms.Select(attrs={"class": "form-control"}),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if not image or not hasattr(image, "image"):
            return image
        if image.size > 5 * 1024 * 1024:
            raise ValidationError("Choose a profile image smaller than 5 MB.")
        if image.image.format not in {"JPEG", "PNG", "WEBP"}:
            raise ValidationError("Use a JPEG, PNG, or WebP profile image.")
        return image


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
