# ====================================================
# YD Commercial Cleaning Services
# File: invoices/forms.py
# Purpose:
# - Custom invoice creation form
# ====================================================

from django import forms

from .models import Invoice


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice

        fields = [
            "booking",
            "issue_date",
            "due_date",
            "description",
            "amount",
            "status",
            "notes",
        ]

        widgets = {
<<<<<<< HEAD
            "booking": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "issue_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "due_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe the cleaning work completed",
                }
            ),
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "placeholder": "Amount before GST",
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Internal invoice notes",
                }
            ),
        }
=======
            "booking": forms.Select(attrs={
                "class": "form-control",
            }),

            "issue_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),

            "due_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),

            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Describe the cleaning work completed",
            }),

            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "placeholder": "Amount before GST",
            }),

            "status": forms.Select(attrs={
                "class": "form-control",
            }),

            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Internal invoice notes",
            }),
        }
>>>>>>> 5815f15 (Initial project commit)
