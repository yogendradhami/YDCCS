from django import forms
<<<<<<< HEAD

=======
>>>>>>> 5815f15 (Initial project commit)
from .models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer

        fields = [
            "user",
            "full_name",
            "email",
            "phone",
            "address",
            "property_type",
            "suburb_postcode",
            "notes",
            "jobs_completed",
            "total_revenue",
        ]

        widgets = {
            "user": forms.Select(attrs={"class": "form-control"}),
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "property_type": forms.TextInput(attrs={"class": "form-control"}),
            "suburb_postcode": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "jobs_completed": forms.NumberInput(attrs={"class": "form-control"}),
<<<<<<< HEAD
            "total_revenue": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
        }
=======
            "total_revenue": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }
>>>>>>> 5815f15 (Initial project commit)
