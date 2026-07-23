# ==========================================================
# File: dashboard/forms.py
# Purpose:
# Forms used inside the admin/business dashboard.
# Includes company settings form.
# ==========================================================

from django import forms

from .models import (
    CleaningSupply,
    CompanySettings,
    Equipment,
    MaintenanceHistory,
    PurchaseOrder,
    Supplier,
    Vehicle,
)


class CompanySettingsForm(forms.ModelForm):
    """
    Form used by admin to update company/business settings.
    These settings can later be used in header, footer,
    invoices, reports and emails.
    """

    class Meta:
        model = CompanySettings

        fields = [
            "business_name",
            "abn",
            "phone",
            "email",
            "website",
            "address",
            "logo",
            "favicon",
            "facebook_url",
            "instagram_url",
            "linkedin_url",
            "tiktok_url",
            "invoice_prefix",
            "gst_percentage",
            "payment_terms_days",
        ]

        widgets = {
            # Business information fields
            "business_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "YD Commercial Cleaning Services",
                }
            ),
            "abn": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter ABN",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0430 049 865",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "business@email.com",
                }
            ),
            "website": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://www.ydcleaning.com",
                }
            ),
            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Business address",
                }
            ),
            # Branding upload fields
            "logo": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "favicon": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                }
            ),
            # Social media fields
            "facebook_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Facebook URL",
                }
            ),
            "instagram_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Instagram URL",
                }
            ),
            "linkedin_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "LinkedIn URL",
                }
            ),
            "tiktok_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "TikTok URL",
                }
            ),
            # Invoice settings fields
            "invoice_prefix": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "YD",
                }
            ),
            "gst_percentage": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                }
            ),
            "payment_terms_days": forms.NumberInput(
                attrs={
                    "class": "form-control",
                }
            ),
        }


class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment

        fields = "__all__"

        widgets = {
            "purchase_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "next_service_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "notes": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
        }


class CleaningSupplyForm(forms.ModelForm):

    class Meta:
        model = CleaningSupply

        fields = "__all__"

        widgets = {
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
        }


class PurchaseOrderForm(forms.ModelForm):

    class Meta:
        model = PurchaseOrder
        fields = "__all__"


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = "__all__"


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = "__all__"


class MaintenanceHistoryForm(forms.ModelForm):

    class Meta:
        model = MaintenanceHistory
        fields = "__all__"
