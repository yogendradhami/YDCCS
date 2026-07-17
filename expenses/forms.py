from django import forms
<<<<<<< HEAD

=======
>>>>>>> 5815f15 (Initial project commit)
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
<<<<<<< HEAD
            field.widget.attrs.update({"class": "form-control"})
=======
            field.widget.attrs.update({
                "class": "form-control"
            })
>>>>>>> 5815f15 (Initial project commit)
