from decimal import Decimal

from django import forms

from .models import AttendanceLog


class AttendanceLogForm(forms.ModelForm):
    check_in_time = forms.DateTimeField(
        required=False,
        input_formats=("%Y-%m-%dT%H:%M",),
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
    )
    check_out_time = forms.DateTimeField(
        required=False,
        input_formats=("%Y-%m-%dT%H:%M",),
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
    )

    class Meta:
        model = AttendanceLog
        fields = (
            "employee",
            "booking",
            "check_in_time",
            "check_out_time",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "workforce-form-control"

    def clean(self):
        cleaned_data = super().clean()
        check_in = cleaned_data.get("check_in_time")
        check_out = cleaned_data.get("check_out_time")

        if check_out and not check_in:
            self.add_error("check_in_time", "Add a check-in time before check-out.")
        elif check_in and check_out and check_out < check_in:
            self.add_error("check_out_time", "Check-out cannot be before check-in.")

        employee = cleaned_data.get("employee")
        booking = cleaned_data.get("booking")
        if employee and booking and AttendanceLog.objects.filter(
            employee=employee,
            booking=booking,
            source=AttendanceLog.Source.PORTAL,
        ).exclude(pk=self.instance.pk).exists():
            self.add_error(
                "booking",
                "This employee already has portal attendance for this booking.",
            )

        return cleaned_data

    def save(self, commit=True):
        attendance = super().save(commit=False)
        attendance.source = AttendanceLog.Source.PORTAL
        attendance.roster = None

        if attendance.check_in_time and attendance.check_out_time:
            elapsed = (
                attendance.check_out_time - attendance.check_in_time
            ).total_seconds() / 3600
            attendance.total_hours = Decimal(str(elapsed)).quantize(
                Decimal("0.01")
            )
        else:
            attendance.total_hours = Decimal("0.00")

        if commit:
            attendance.save()
            self.save_m2m()
        return attendance
