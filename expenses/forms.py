from django import forms
from pathlib import Path

from .models import Expense


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = [
            "date",
            "category",
            "description",
            "amount",
            "receipt",
            "notes",
        ]

        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_receipt(self):
        receipt = self.cleaned_data.get("receipt")
        if not receipt or not hasattr(receipt, "size"):
            return receipt
        if receipt.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Receipts must be 10 MB or smaller.")
        if Path(receipt.name).suffix.lower() not in {
            ".pdf", ".jpg", ".jpeg", ".png", ".webp",
        }:
            raise forms.ValidationError("Upload a PDF, JPG, PNG, or WebP receipt.")
        return receipt

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})
