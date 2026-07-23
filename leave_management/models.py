from django.db import models

from employees.models import Employee


class LeaveRequest(models.Model):
    LEAVE_TYPES = [
        ("annual", "Annual Leave"),
        ("sick", "Sick Leave"),
        ("personal", "Personal Leave"),
        ("unpaid", "Unpaid Leave"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="leave_requests"
    )

    leave_type = models.CharField(max_length=30, choices=LEAVE_TYPES)

    start_date = models.DateField()
    end_date = models.DateField()

    reason = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    admin_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.employee.full_name} - {self.get_leave_type_display()}"
