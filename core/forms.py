from django import forms

from .models import FAQQuestion


class FAQSubmissionForm(forms.ModelForm):
    class Meta:
        model = FAQQuestion
        fields = ["name", "email", "question", "page_key"]
        widgets = {
            "question": forms.Textarea(attrs={"rows": 4}),
            "page_key": forms.HiddenInput(),
        }
from django import forms

from dashboard.models import CareerApplication


class CareerApplicationForm(forms.ModelForm):
    class Meta:
        model = CareerApplication
        fields = [
            "full_name",
            "email",
            "phone",
            "address",
            "suburb",
            "date_of_birth",

            "position",
            "employment_type",

            "work_rights",
            "work_rights_details",

            "years_cleaning_experience",
            "previous_cleaning_experience",
            "skills",

            "has_drivers_license",
            "has_vehicle",
            "availability_days",
            "availability_hours",
            "preferred_start_date",

            "cover_letter",
            "resume",

            "reference_name",
            "reference_phone",
            "reference_relationship",
        ]

        widgets = {
            "cover_letter": forms.Textarea(attrs={"rows": 5}),
            "previous_cleaning_experience": forms.Textarea(attrs={"rows": 4}),
            "skills": forms.Textarea(attrs={"rows": 3}),
            "availability_days": forms.Textarea(attrs={"rows": 2}),
            "availability_hours": forms.Textarea(attrs={"rows": 2}),
            "work_rights_details": forms.TextInput(attrs={"placeholder": "If 'Other' or visa type, please specify"}),
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "preferred_start_date": forms.DateInput(attrs={"type": "date"}),
            "position": forms.Select(attrs={"class": "form-control"}),
            "employment_type": forms.Select(attrs={"class": "form-control"}),
            "has_drivers_license": forms.CheckboxInput(),
            "has_vehicle": forms.CheckboxInput(),
        }

    def clean_resume(self):
        resume = self.cleaned_data.get("resume")
        if resume:
            allowed = ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
            if resume.content_type not in allowed:
                raise forms.ValidationError("Resume must be a PDF or Word document (.pdf, .doc, .docx).")
            if resume.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Resume file size must be under 5MB.")
        return resume
