from django import forms

from dashboard.models import CareerApplication


class CareerApplicationForm(forms.ModelForm):
    class Meta:
        model = CareerApplication
        fields = ["full_name", "email", "phone", "cover_letter", "resume"]
        widgets = {
            "cover_letter": forms.Textarea(attrs={"rows": 5}),
        }
