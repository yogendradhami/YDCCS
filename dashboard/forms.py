# ==========================================================
# File: dashboard/forms.py
# Purpose:
# Forms used inside the admin/business dashboard.
# Includes company settings form.
# ==========================================================

from django import forms
from django.core.files.uploadedfile import UploadedFile
from core.models import TestimonialVideo
from core.testimonial_uploads import (
    MAX_TESTIMONIAL_UPLOAD_COUNT,
    validate_testimonial_video_file,
)
from customers.models import MarketingSubscriber
from .models import (
    CampaignLog,
    CleaningSupply,
    CompanySettings,
    Equipment,
    MaintenanceHistory,
    PurchaseOrder,
    Supplier,
    Vehicle,
)


class MultipleVideoInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleVideoField(forms.FileField):
    widget = MultipleVideoInput

    def clean(self, data, initial=None):
        if not data:
            if self.required:
                raise forms.ValidationError(self.error_messages["required"], code="required")
            return []
        files = data if isinstance(data, (list, tuple)) else [data]
        return [forms.FileField.clean(self, upload, initial) for upload in files]


class TestimonialVideoUploadForm(forms.Form):
    videos = MultipleVideoField(
        label="Video files",
        help_text="Select up to 10 videos. Each video can be up to 100 MB.",
        widget=MultipleVideoInput(attrs={"accept": "video/*"}),
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="This description will be applied to each uploaded video.",
    )
    active = forms.BooleanField(required=False, initial=True, label="Show on website")

    def clean_videos(self):
        videos = self.cleaned_data["videos"]
        if len(videos) > MAX_TESTIMONIAL_UPLOAD_COUNT:
            raise forms.ValidationError(
                f"Upload no more than {MAX_TESTIMONIAL_UPLOAD_COUNT} videos at a time."
            )
        for video in videos:
            try:
                validate_testimonial_video_file(video)
            except ValueError as exc:
                raise forms.ValidationError(f"{video.name}: {exc}") from exc
        return videos


class TestimonialVideoEditForm(forms.ModelForm):
    replacement_video = forms.FileField(
        required=False,
        label="Replace video",
        help_text="Optional. Upload a new video to replace the current one.",
        widget=forms.ClearableFileInput(attrs={"accept": "video/*"}),
    )

    class Meta:
        model = TestimonialVideo
        fields = ["title", "description", "active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_replacement_video(self):
        video = self.cleaned_data.get("replacement_video")
        if video:
            try:
                validate_testimonial_video_file(video)
            except ValueError as exc:
                raise forms.ValidationError(str(exc)) from exc
        return video


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

    def _clean_brand_image(self, field_name):
        image = self.cleaned_data.get(field_name)
        if isinstance(image, UploadedFile) and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Branding images must be 5 MB or smaller.")
        return image

    def clean_logo(self):
        return self._clean_brand_image("logo")

    def clean_favicon(self):
        return self._clean_brand_image("favicon")


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


class MarketingSubscriberForm(forms.ModelForm):
    class Meta:
        model = MarketingSubscriber

        fields = [
            "email",
            "consent_given",
            "source",
            "is_active",
        ]

        widgets = {
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "customer@example.com",
                }
            ),
            "consent_given": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
            "source": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }


class CampaignLogForm(forms.ModelForm):
    class Meta:
        model = CampaignLog

        fields = [
            "campaign_type",
            "title",
            "recipients_count",
        ]

        widgets = {
            "campaign_type": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "recipients_count": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                }
            ),
        }
