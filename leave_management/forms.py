from django import forms
<<<<<<< HEAD

=======
>>>>>>> 5815f15 (Initial project commit)
from .models import LeaveRequest


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = [
            "employee",
            "leave_type",
            "start_date",
            "end_date",
            "reason",
        ]

        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
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


class EmployeeLeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = [
            "leave_type",
            "start_date",
            "end_date",
            "reason",
        ]

        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
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
