from django import forms

from employees.models import Employee

from .models import PayrollRecord


class PayrollRecordForm(forms.ModelForm):
    class Meta:
        model = PayrollRecord
        fields = [
            "employee",
            "period_start",
            "period_end",
            "total_hours",
            "hourly_rate",
            "gross_pay",
            "notes",
        ]
        widgets = {
            "employee": forms.Select(attrs={"class": "form-control"}),
            "period_start": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "period_end": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "total_hours": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "step": "0.01"}
            ),
            "hourly_rate": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "step": "0.01"}
            ),
            "gross_pay": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "step": "0.01"}
            ),
            "notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employee"].queryset = Employee.objects.order_by("full_name")

    def clean(self):
        cleaned_data = super().clean()
        for field_name in ("total_hours", "hourly_rate", "gross_pay"):
            value = cleaned_data.get(field_name)
            if value is not None and value < 0:
                self.add_error(field_name, "Enter a value greater than or equal to zero.")
        period_start = cleaned_data.get("period_start")
        period_end = cleaned_data.get("period_end")
        if period_start and period_end and period_end < period_start:
            self.add_error(
                "period_end",
                "Pay period end must be on or after its start.",
            )
        return cleaned_data
