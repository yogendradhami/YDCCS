# ==========================================================
# File: payroll/models.py
# Purpose:
# Store employee payroll records generated from attendance.
# ==========================================================

from django.db import models

from employees.models import Employee


class PayrollRecord(models.Model):
    # Employee linked to this payroll record.
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="payroll_records"
    )

    # Payroll period.
    period_start = models.DateField()
    period_end = models.DateField()

    # Payroll calculation values.
    total_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    gross_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Payroll status.
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("approved", "Approved"),
        ("paid", "Paid"),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-period_end", "employee__full_name"]

    def __str__(self):
        return f"{self.employee.full_name} - {self.period_start} to {self.period_end}"
