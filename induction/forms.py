from django import forms

from .models import (
    EmployeeInduction,
    InductionModuleCompletion,
)


class InductionSetupForm(forms.ModelForm):

    class Meta:

        model = EmployeeInduction

        fields = [
            "programme",
            "employment_type",
            "start_date",
            "supervisor_name",
            "primary_work_location",
            "induction_duration_minutes",
            "notes",
        ]

        widgets = {

            "programme": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "employment_type": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "start_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "supervisor_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "primary_work_location": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "induction_duration_minutes": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
        }


class ModuleCompletionForm(forms.ModelForm):

    acknowledgement = forms.BooleanField(
        required=True,
    )

    class Meta:

        model = InductionModuleCompletion

        fields = [
            "acknowledgement",
            "notes",
        ]

        widgets = {

            "acknowledgement": forms.CheckboxInput(
                attrs={
                    "class": "induction-check",
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": (
                        "Optional notes"
                    ),
                }
            ),
        }


class InductionDeclarationForm(forms.Form):

    declaration_name = forms.CharField(
        max_length=150,
        label="Full name / electronic signature",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "name",
            }
        ),
    )

    declaration = forms.BooleanField(
        required=True,
        label=(
            "I confirm that I completed the required "
            "induction material, understood the "
            "instructions provided, and will follow "
            "YD Commercial Cleaning's workplace, "
            "safety and operational requirements."
        ),
    )

from django import forms
from django.core.exceptions import ValidationError

from .models import (
    EmployeeOnboardingDocument,
)


class OnboardingDocumentUploadForm(forms.ModelForm):
    class Meta:
        model = EmployeeOnboardingDocument
        fields = ["file"]

    def clean_file(self):
        uploaded_file = self.cleaned_data.get("file")

        if not uploaded_file:
            raise ValidationError("Please select a file.")

        max_size = 10 * 1024 * 1024  # 10 MB

        if uploaded_file.size > max_size:
            raise ValidationError(
                "File size cannot exceed 10 MB."
            )

        allowed_extensions = {
            ".pdf",
            ".jpg",
            ".jpeg",
            ".png",
            ".doc",
            ".docx",
        }

        filename = uploaded_file.name.lower()

        if "." not in filename:
            raise ValidationError(
                "This file type is not supported."
            )

        extension = "." + filename.rsplit(".", 1)[1]

        if extension not in allowed_extensions:
            raise ValidationError(
                "Allowed file types: PDF, JPG, JPEG, PNG, DOC and DOCX."
            )

        return uploaded_file


class OnboardingReviewForm(forms.ModelForm):
    class Meta:
        model = EmployeeOnboardingDocument
        fields = [
            "status",
            "review_notes",
            "expires_at",
        ]

        widgets = {
            "status": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "review_notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter HR review notes...",
                }
            ),
            "expires_at": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
        }