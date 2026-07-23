from django import forms

from .models import CleaningContract


class CleaningContractForm(forms.ModelForm):
    class Meta:
        model = CleaningContract

        fields = [
            "customer",
            "service_type",
            "frequency",
            "start_date",
            "end_date",
            "preferred_time",
            "address",
            "suburb_postcode",
            "assigned_employee",
            "price_per_visit",
            "status",
            "notes",
        ]

        widgets = {
            "customer": forms.Select(attrs={"class": "form-control"}),
            "service_type": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Office Cleaning / Commercial Cleaning",
                }
            ),
            "frequency": forms.Select(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "end_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "preferred_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "suburb_postcode": forms.TextInput(attrs={"class": "form-control"}),
            "assigned_employee": forms.Select(attrs={"class": "form-control"}),
            "price_per_visit": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "status": forms.Select(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }
