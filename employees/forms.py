# ====================================================
# YD Commercial Cleaning Services
# File: employees/forms.py
# Purpose:
# - Dashboard employee form
# - Employee portal login form
# - Employee job status form
# ====================================================

import json
import uuid

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Q

from bookings.models import Booking

from dashboard.models import CleaningSupply, Equipment

from .models import (
    Employee,
    PropertyDamageReport,
    PropertyDamageReportReply,
    SupplyRequest,
    SupplyRequestItem,
)

MAX_DAMAGE_REPORT_IMAGES = 12
MAX_DAMAGE_REPORT_IMAGE_SIZE = 25 * 1024 * 1024
ALLOWED_DAMAGE_REPORT_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_SUPPLY_REQUEST_ATTACHMENTS = 5
MAX_SUPPLY_REQUEST_ATTACHMENT_SIZE = 15 * 1024 * 1024


class SupplyRequestMultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class SupplyRequestAttachmentField(forms.FileField):
    widget = SupplyRequestMultipleFileInput

    def clean(self, data, initial=None):
        uploaded = data if isinstance(data, (list, tuple)) else ([data] if data else [])
        if len(uploaded) > MAX_SUPPLY_REQUEST_ATTACHMENTS:
            raise ValidationError(
                f"Upload no more than {MAX_SUPPLY_REQUEST_ATTACHMENTS} files."
            )
        valid_signatures = (
            lambda content: content.startswith(b"%PDF-"),
            lambda content: content.startswith(b"\xff\xd8\xff"),
            lambda content: content.startswith(b"\x89PNG\r\n\x1a\n"),
            lambda content: (
                len(content) >= 12
                and content[:4] == b"RIFF"
                and content[8:12] == b"WEBP"
            ),
        )
        files = []
        for item in uploaded:
            if item.size > MAX_SUPPLY_REQUEST_ATTACHMENT_SIZE:
                raise ValidationError("Each attachment must be 15 MB or smaller.")
            content = item.read(16)
            item.seek(0)
            if not any(signature(content) for signature in valid_signatures):
                raise ValidationError(
                    "Attachments must be a PDF, JPEG, PNG, or WebP file."
                )
            files.append(item)
        return files


class SupplyRequestForm(forms.Form):
    idempotency_key = forms.UUIDField(widget=forms.HiddenInput)
    job_location = forms.CharField(max_length=255)
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}))
    urgency = forms.ChoiceField(choices=SupplyRequest.Urgency.choices)
    request_items = forms.CharField(widget=forms.HiddenInput)
    attachments = SupplyRequestAttachmentField(required=False)

    def clean_request_items(self):
        raw_items = self.cleaned_data["request_items"]
        try:
            values = json.loads(raw_items)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Choose at least one valid item.") from exc
        if not isinstance(values, list) or not values:
            raise ValidationError("Choose at least one supply or equipment item.")
        if len(values) > 30:
            raise ValidationError("A request can contain no more than 30 items.")

        parsed = []
        seen = set()
        for value in values:
            if not isinstance(value, dict) or value.get("kind") not in {
                "supply",
                "equipment",
            }:
                raise ValidationError("The selected request item is invalid.")
            try:
                item_id = int(value["id"])
                quantity = int(value["quantity"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValidationError("Enter a valid item and quantity.") from exc
            if item_id <= 0 or quantity <= 0 or quantity > 10000:
                raise ValidationError("Item quantities must be between 1 and 10,000.")
            if value["kind"] == "equipment" and quantity != 1:
                raise ValidationError("Equipment is individually tracked; request one unit.")
            unique_item = (value["kind"], item_id)
            if unique_item in seen:
                raise ValidationError("Each item may only appear once per request.")
            seen.add(unique_item)

            model = CleaningSupply if value["kind"] == "supply" else Equipment
            try:
                item = model.objects.get(pk=item_id)
            except model.DoesNotExist as exc:
                raise ValidationError("One of the selected items no longer exists.") from exc
            if value["kind"] == "equipment" and (
                item.assigned_employee_id or item.condition in {"repair", "retired"}
            ):
                raise ValidationError("One of the selected equipment items is unavailable.")
            parsed.append((value["kind"], item, quantity))
        return parsed


class SupplyRequestApprovalForm(forms.Form):
    comments = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, request_record, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_record = request_record
        self.request_items = list(request_record.items.select_related("supply", "equipment"))
        for item in self.request_items:
            self.fields[f"quantity_{item.pk}"] = forms.IntegerField(
                min_value=0,
                max_value=item.requested_quantity,
                initial=item.requested_quantity,
                label=f"{item.item_name} (requested {item.requested_quantity})",
            )

    def clean(self):
        cleaned = super().clean()
        quantities = [
            cleaned.get(f"quantity_{item.pk}") or 0
            for item in self.request_items
        ]
        if not any(quantities):
            raise ValidationError("Approve at least one positive item quantity.")
        if any(
            quantity < item.requested_quantity
            for item, quantity in zip(self.request_items, quantities)
        ) and not cleaned.get("comments", "").strip():
            raise ValidationError("Explain any reduced or declined quantities.")
        return cleaned


class SupplyRequestRejectForm(forms.Form):
    comments = forms.CharField(
        min_length=3,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Reason for rejection",
    )


class SupplyRequestIssueForm(forms.Form):
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    idempotency_key = forms.UUIDField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, request_record, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_items = list(request_record.items.select_related("supply", "equipment"))
        for item in self.request_items:
            remaining = item.remaining_to_issue
            if remaining:
                self.fields[f"quantity_{item.pk}"] = forms.IntegerField(
                    min_value=0,
                    max_value=remaining,
                    initial=remaining,
                    label=f"{item.item_name} (remaining {remaining})",
                )

    def clean(self):
        cleaned = super().clean()
        if not any(
            cleaned.get(f"quantity_{item.pk}", 0)
            for item in self.request_items
        ):
            raise ValidationError("Enter at least one quantity to hand over.")
        return cleaned

    def clean_idempotency_key(self):
        return self.cleaned_data.get("idempotency_key") or uuid.uuid4()


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return []

        files = data if isinstance(data, (list, tuple)) else [data]
        if len(files) > MAX_DAMAGE_REPORT_IMAGES:
            raise ValidationError(
                f"Choose no more than {MAX_DAMAGE_REPORT_IMAGES} images."
            )

        image_field = forms.ImageField()
        cleaned_images = []
        for image in files:
            cleaned_image = image_field.clean(image, initial)
            if cleaned_image.size > MAX_DAMAGE_REPORT_IMAGE_SIZE:
                raise ValidationError("Each image must be 25 MB or smaller.")
            if cleaned_image.image.format not in ALLOWED_DAMAGE_REPORT_IMAGE_FORMATS:
                raise ValidationError("Use JPEG, PNG, or WebP images.")
            cleaned_images.append(cleaned_image)
        return cleaned_images


class PropertyDamageReportForm(forms.ModelForm):
    images = MultipleImageField(
        required=False,
        label="Damage photos",
        help_text="Upload up to 12 JPEG, PNG, or WebP images (25 MB max each).",
        widget=MultipleFileInput(
            attrs={
                "accept": "image/jpeg,image/png,image/webp",
                "class": "damage-report-file-input",
            }
        ),
    )

    class Meta:
        model = PropertyDamageReport
        fields = ["booking", "description", "images"]
        widgets = {
            "booking": forms.Select(attrs={"class": "damage-report-control"}),
            "description": forms.Textarea(
                attrs={
                    "class": "damage-report-control",
                    "rows": 6,
                    "placeholder": "Describe what happened, where the damage is, and any immediate action taken.",
                }
            ),
        }
        labels = {
            "booking": "Assigned job",
            "description": "What happened?",
        }

    def __init__(self, *args, employee, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["booking"].required = True
        self.fields["booking"].queryset = (
            Booking.objects.filter(assigned_employee=employee)
            .select_related("customer")
            .order_by("-booking_date", "-booking_time")
        )
        self.fields["booking"].label_from_instance = (
            lambda booking: (
                f"{booking.booking_date:%d %b %Y} — {booking.get_service_type_display()} — "
                f"{booking.address}, {booking.suburb_postcode}"
            )
        )


class PropertyDamageReportReplyForm(forms.ModelForm):
    class Meta:
        model = PropertyDamageReportReply
        fields = ["message"]
        widgets = {
            "message": forms.Textarea(
                attrs={
                    "class": "damage-report-control",
                    "rows": 3,
                    "placeholder": "Write an update or follow-up for the employee.",
                }
            ),
        }
        labels = {"message": "Reply to employee"}


class EmployeePropertyDamageReportReplyForm(PropertyDamageReportReplyForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["message"].label = "Your response"
        self.fields["message"].widget.attrs["placeholder"] = (
            "Write a response or follow-up for the dashboard team."
        )


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

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if not image or not hasattr(image, "image"):
            return image
        if image.size > 5 * 1024 * 1024:
            raise ValidationError("Choose an employee image smaller than 5 MB.")
        if image.image.format not in {"JPEG", "PNG", "WEBP"}:
            raise ValidationError("Use a JPEG, PNG, or WebP employee image.")
        return image

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
            .filter(
                Q(customer_profile__isnull=True)
                | Q(customer_profile__email_verified=True)
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
                if user_model._default_manager.filter(
                    **{f"{user_model.USERNAME_FIELD}__iexact": login_email}
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
