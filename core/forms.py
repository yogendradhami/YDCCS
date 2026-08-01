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
        fields = ["full_name", "email", "phone", "cover_letter", "resume"]
        widgets = {
            "cover_letter": forms.Textarea(attrs={"rows": 5}),
        }
