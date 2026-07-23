from django import forms

from .models import Roster


class RosterForm(forms.ModelForm):
    class Meta:
        model = Roster

        fields = [
            "employee",
            "booking",
            "shift_date",
            "start_time",
            "end_time",
            "status",
            "notes",
        ]

        widgets = {
            "employee": forms.Select(attrs={"class": "form-control"}),
            "booking": forms.Select(attrs={"class": "form-control"}),
            "shift_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "start_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "end_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "status": forms.Select(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }
