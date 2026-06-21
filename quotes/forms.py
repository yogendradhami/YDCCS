from django import forms

from .models import QuoteRequest


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.FileField):
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
            "is_not_robot",
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
            "is_not_robot": forms.CheckboxInput(
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

    def clean_is_not_robot(self):
        value = self.cleaned_data.get("is_not_robot")
        if not value:
            raise forms.ValidationError("Please confirm that you are not a robot.")
        return value
