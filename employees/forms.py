# ====================================================
# YD Commercial Cleaning Services
# File: employees/forms.py
# Purpose:
# - Dashboard employee form
# - Employee portal login form
# - Employee job status form
# ====================================================

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Q

from bookings.models import Booking

from .models import Employee


class EmployeeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_model = get_user_model()
        current_user = getattr(self.instance, "user", None)
        self.fields["user"].required = False
        self.fields["user"].empty_label = "No portal login linked"
        self.fields["user"].queryset = user_model._default_manager.filter(
            Q(employee_profile__isnull=True) | Q(pk=current_user.pk if current_user else None)
        ).order_by(user_model.USERNAME_FIELD)

    def clean_user(self):
        user = self.cleaned_data.get("user")
        if user is None:
            return None

        related_employee = getattr(user, "employee_profile", None)
        if related_employee is not None and related_employee.pk != self.instance.pk:
            raise ValidationError("This account is already linked to another employee.")

        return user

    class Meta:
        model = Employee

        fields = [
            "user",
            "full_name",
            "phone",
            "email",
            "image",
            "address",
            "role",
            "availability",
            "hourly_rate",
            "jobs_completed",
            "notes",
            "active",
        ]

        widgets = {
            "user": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "full_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Employee full name",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Phone number",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Email address",
                }
            ),

            "image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),
            "address": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Address",
                }
            ),
            "role": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "availability": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "hourly_rate": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                }
            ),
            "jobs_completed": forms.NumberInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
            "active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }


class EmployeeCreateForm(forms.ModelForm):
    ACCESS_CHOICES = (
        ("none", "No login access"),
        ("create", "Create new login account"),
        ("link", "Link existing user"),
    )

    access_mode = forms.ChoiceField(
        choices=ACCESS_CHOICES,
        initial="none",
        widget=forms.RadioSelect,
    )
    login_email = forms.EmailField(required=False)
    username = forms.CharField(required=False, max_length=150)
    password1 = forms.CharField(
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    existing_user = forms.ModelChoiceField(
        queryset=get_user_model()._default_manager.none(),
        required=False,
        empty_label="Select an account",
    )

    class Meta:
        model = Employee
        fields = [
            "full_name",
            "phone",
            "email",
            "image",
            "address",
            "role",
            "availability",
            "hourly_rate",
            "jobs_completed",
            "notes",
            "active",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "phone": forms.TelInput(attrs={"autocomplete": "tel"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "image": forms.ClearableFileInput(
                attrs={"accept": "image/jpeg,image/png,image/webp"}
            ),
            "address": forms.TextInput(attrs={"autocomplete": "street-address"}),
            "hourly_rate": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "jobs_completed": forms.NumberInput(attrs={"min": "0", "step": "1"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_model = get_user_model()
        username_field = user_model._meta.get_field(user_model.USERNAME_FIELD)
        self.fields["username"].required = False
        self.fields["username"].label = username_field.verbose_name.capitalize()
        self.fields["existing_user"].queryset = (
            user_model._default_manager.filter(
                is_active=True,
                is_staff=False,
                is_superuser=False,
                employee_profile__isnull=True,
            )
            .order_by(user_model.USERNAME_FIELD)
        )
        self.fields["existing_user"].label_from_instance = self._user_label

    @staticmethod
    def _user_label(user):
        email = getattr(user, "email", "")
        return f"{user.get_username()} ({email})" if email else user.get_username()

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if not image or not hasattr(image, "image"):
            return image

        if image.size > 5 * 1024 * 1024:
            raise ValidationError("Choose an image smaller than 5 MB.")
        if image.image.format not in {"JPEG", "PNG", "WEBP"}:
            raise ValidationError("Use a JPEG, PNG, or WebP image.")
        return image

    def clean_hourly_rate(self):
        hourly_rate = self.cleaned_data["hourly_rate"]
        if hourly_rate < 0:
            raise ValidationError("Hourly rate cannot be negative.")
        return hourly_rate

    def clean(self):
        cleaned_data = super().clean()
        access_mode = cleaned_data.get("access_mode")
        user_model = get_user_model()

        if access_mode == "create":
            login_email = (cleaned_data.get("login_email") or "").strip().lower()
            username = (cleaned_data.get("username") or "").strip()
            password1 = cleaned_data.get("password1") or ""
            password2 = cleaned_data.get("password2") or ""

            if not login_email:
                self.add_error("login_email", "Enter an email for dashboard access.")
            else:
                email_field = getattr(user_model, "EMAIL_FIELD", "email")
                if any(field.name == email_field for field in user_model._meta.fields):
                    if user_model._default_manager.filter(
                        **{f"{email_field}__iexact": login_email}
                    ).exists():
                        self.add_error("login_email", "An account already uses this email.")

            username_value = username or login_email
            if not username_value:
                self.add_error("username", "Enter a username for dashboard access.")
            else:
                username_field = user_model.USERNAME_FIELD
                lookup = {f"{username_field}__iexact": username_value}
                if user_model._default_manager.filter(**lookup).exists():
                    self.add_error("username", "This username is already in use.")
                cleaned_data["username"] = username_value

            if not password1:
                self.add_error("password1", "Enter a temporary password.")
            elif password1 != password2:
                self.add_error("password2", "The passwords do not match.")
            else:
                user = user_model(**{user_model.USERNAME_FIELD: username_value})
                if hasattr(user, "email"):
                    user.email = login_email
                try:
                    validate_password(password1, user=user)
                except ValidationError as error:
                    self.add_error("password1", error)

        elif access_mode == "link":
            existing_user = cleaned_data.get("existing_user")
            if not existing_user:
                self.add_error("existing_user", "Select an active, unlinked account.")

        return cleaned_data


class EmployeeLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Employee email or username",
            }
        )
    )

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Password",
            }
        )
    )


class EmployeeJobStatusForm(forms.ModelForm):
    class Meta:
        model = Booking

        fields = [
            "status",
            "notes",
        ]

        widgets = {
            "status": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Add job update notes",
                }
            ),
        }
