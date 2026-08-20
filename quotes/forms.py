from django import forms
from django.conf import settings
import requests

from .models import QuoteRequest


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return []

        if isinstance(data, (list, tuple)):
            return [
                super(MultipleImageField, self).clean(file, initial) for file in data
            ]

        return [super().clean(data, initial)]


class QuoteRequestForm(forms.ModelForm):
    g_recaptcha_response = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    property_images = MultipleImageField(
        required=False,
        widget=MultipleFileInput(
            attrs={
                "class": "form-control",
                "multiple": True,
                "accept": "image/*",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        self.recaptcha_site_key = getattr(settings, "RECAPTCHA_SITE_KEY", "")

    class Meta:
        model = QuoteRequest
        fields = [
            "name",
            "email",
            "phone",
            "property_type",
            "suburb_postcode",
            "preferred_date",
            "message",
            "window_cleaning",
            "carpet_shampooing",
            "grout_cleaning",
            "upholstery_cleaning",
            "laundry_service",
            "bedrooms",
            "bathrooms",
            "lead_source",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Your name",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "your@email.com",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0233 222 333",
                }
            ),
            "property_type": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "suburb_postcode": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., Adelaide 5000",
                }
            ),
            "preferred_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Tell us more about your cleaning needs...",
                    "rows": 4,
                }
            ),
            "window_cleaning": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
            "carpet_shampooing": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
            "grout_cleaning": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
            "upholstery_cleaning": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
            "laundry_service": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def clean_property_type(self):
        value = self.cleaned_data.get("property_type")
        if not value:
            raise forms.ValidationError("Please select a property type.")
        return value

    def clean(self):
        cleaned_data = super().clean()

        secret_key = getattr(settings, "RECAPTCHA_SECRET_KEY", "")
        site_key = getattr(settings, "RECAPTCHA_SITE_KEY", "")

        # If reCAPTCHA is not configured, skip validation
        if not secret_key or not site_key:
            return cleaned_data

        token = None

        if self.request is not None:
            token = (
                self.request.POST.get("g-recaptcha-response")
                or self.request.POST.get("g_recaptcha_response")
            )

        if not token:
            token = (
                self.data.get("g-recaptcha-response")
                or self.data.get("g_recaptcha_response")
            )

        # If no token provided, raise validation error
        if not token:
            raise forms.ValidationError(
                "Security verification failed. Please complete the form and try again."
            )

        # For localhost testing, allow localhost-test-token to bypass reCAPTCHA verification
        if token == "localhost-test-token":
            return cleaned_data

        try:
            response = requests.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={
                    "secret": secret_key,
                    "response": token,
                    "remoteip": (
                        self.request.META.get("REMOTE_ADDR")
                        if self.request
                        else None
                    ),
                },
                timeout=10,
            )

            response.raise_for_status()
            result = response.json()

        except requests.RequestException as e:
            raise forms.ValidationError(
                "Security verification service unavailable. Please try again."
            )

        if not result.get("success"):
            raise forms.ValidationError(
                "Security verification failed. Please try again."
            )

        score = result.get("score", 0)

        # Accept score of 0.3 or higher for quote submissions
        if score < 0.3:
            raise forms.ValidationError(
                "Your submission was flagged as suspicious. Please try again."
            )

        action = result.get("action")

        if action != "quote_submit":
            raise forms.ValidationError(
                "Security verification failed. Please try again."
            )

        return cleaned_data