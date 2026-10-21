from django import forms
from django.contrib.auth.models import Group, Permission, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .signals import SAFE_PERMISSION_APPS


class ManagedUserCreateForm(forms.Form):
    email = forms.EmailField()
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)
    position = forms.ModelChoiceField(queryset=Group.objects.none())

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        groups = Group.objects.order_by("name")
        if user and not user.is_superuser:
            groups = groups.exclude(name="Administrator").exclude(
                permissions__content_type__app_label="security",
                permissions__codename="manage_security_roles",
            ).distinct()
        self.fields["position"].queryset = groups

    def clean_email(self):
        email = self.cleaned_data["email"].strip().casefold()
        if User.objects.filter(email__iexact=email).exists() or User.objects.filter(
            username__iexact=email
        ).exists():
            raise ValidationError("An account already uses this email address.")
        return email

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The passwords do not match.")
        if password1:
            try:
                validate_password(password1)
            except ValidationError as error:
                self.add_error("password1", error)
        return cleaned


class ManagedUserUpdateForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)
    position = forms.ModelChoiceField(queryset=Group.objects.none())

    def __init__(self, *args, user=None, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        groups = Group.objects.order_by("name")
        if user and not user.is_superuser:
            groups = groups.exclude(name="Administrator").exclude(
                permissions__content_type__app_label="security",
                permissions__codename="manage_security_roles",
            ).distinct()
        self.fields["position"].queryset = groups
        if instance is not None and not self.is_bound:
            self.initial.update(
                {
                    "first_name": instance.first_name,
                    "last_name": instance.last_name,
                    "position": instance.groups.first(),
                }
            )


class PositionForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Group
        fields = ["name", "permissions"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        permissions = (
            Permission.objects.select_related("content_type")
            .filter(content_type__app_label__in=SAFE_PERMISSION_APPS)
            .exclude(content_type__app_label__in=["auth", "admin"])
            .order_by("content_type__app_label", "codename")
        )
        if user and not user.is_superuser:
            permissions = permissions.exclude(codename="manage_security_roles")
        self.fields["permissions"].queryset = permissions


def position_has_dashboard_access(group):
    return group.permissions.filter(
        content_type__app_label="security",
        codename="access_dashboard",
    ).exists()

