# ====================================================
# YD Commercial Cleaning Services
# File: portal/forms.py
# Purpose:
# - Customer registration form
# - Customer login form
# - Customer profile update form
# - Customer password change form
# ====================================================

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from customers.models import Customer


class CustomerRegisterForm(forms.Form):
    # Customer full name field
    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your full name",
            }
        ),
    )

    # Customer email field
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your email address",
            }
        )
    )

    # Customer phone field
    phone = forms.CharField(
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your phone number",
            }
        ),
    )

    # Customer address field
    address = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your address",
            }
        ),
    )

    # Customer suburb/postcode field
    suburb_postcode = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g., Prospect 5082",
            }
        ),
    )

    # Customer password field
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Create a strong password",
            }
        )
    )

    # Customer password confirmation field
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Confirm password",
            }
        )
    )

    def clean_email(self):
        # Prevent duplicate customer account email.
        email = self.cleaned_data.get("email")

        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("An account with this email already exists.")

        return email

    def clean_password(self):
        # Use Django's built-in password strength validators.
        password = self.cleaned_data.get("password")
        validate_password(password)
        return password

    def clean(self):
        # Confirm both passwords match.
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data


class CustomerLoginForm(AuthenticationForm):
    # Customer login username/email field.
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Email address",
            }
        )
    )

    # Customer login password field.
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Password",
            }
        )
    )


class CustomerProfileForm(forms.ModelForm):
    # Customer profile update form.
    class Meta:
        model = Customer

        fields = [
            "full_name",
            "email",
            "phone",
            "address",
            "property_type",
            "suburb_postcode",
            "notes",
        ]

        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "property_type": forms.TextInput(attrs={"class": "form-control"}),
            "suburb_postcode": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
        }


class CustomerPasswordForm(PasswordChangeForm):
    # Customer password change form.
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )

    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )

    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )
