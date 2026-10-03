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
                    "placeholder": (
                        "Describe the cleaning service or work "
                        "included in this invoice."
                    ),
                }
            ),

            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0.01",
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
                    "placeholder": (
                        "Internal invoice notes."
                    ),
                }
            ),
        }


    def clean_amount(self):

        amount = self.cleaned_data.get("amount")

        if amount is None:
            raise forms.ValidationError(
                "Invoice amount is required."
            )

        if amount <= 0:
            raise forms.ValidationError(
                "Invoice amount must be greater than $0."
            )

        return amount


    def clean(self):

        cleaned_data = super().clean()

        issue_date = cleaned_data.get("issue_date")
        due_date = cleaned_data.get("due_date")

        if issue_date and due_date:

            if due_date < issue_date:

                self.add_error(
                    "due_date",
                    "Due date cannot be before the issue date.",
                )

        return cleaned_data