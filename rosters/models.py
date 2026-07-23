# Create your models here.
from django.db import models

from bookings.models import Booking
from employees.models import Employee


class Roster(models.Model):

    STATUS_CHOICES = (
        ("scheduled", "Scheduled"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    )

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="rosters"
    )

    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="rosters"
    )

    shift_date = models.DateField()

    start_time = models.TimeField()

    end_time = models.TimeField()

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="scheduled"
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["shift_date", "start_time"]

    def __str__(self):
        return f"{self.employee.full_name} - {self.shift_date}"
