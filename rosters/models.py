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

    google_calendar_event_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["shift_date", "start_time"]

    @property
    def time_status(self):
        """
        Dynamically determine the current time state of the roster.

        This does not change the database status.
        """

        from datetime import datetime
        from django.utils import timezone

        if self.status == "completed":
            return "completed"

        if self.status == "cancelled":
            return "cancelled"

        now = timezone.localtime()

        start_datetime = timezone.make_aware(
            datetime.combine(
                self.shift_date,
                self.start_time,
            ),
            timezone.get_current_timezone(),
        )

        end_datetime = timezone.make_aware(
            datetime.combine(
                self.shift_date,
                self.end_time,
            ),
            timezone.get_current_timezone(),
        )

        if now < start_datetime:
            return "upcoming"

        if start_datetime <= now <= end_datetime:
            return "in_progress"

        return "time_passed"

    @property
    def time_status_display(self):
        labels = {
            "completed": "Completed",
            "cancelled": "Cancelled",
            "upcoming": "Upcoming",
            "in_progress": "In Progress",
            "time_passed": "Time Passed",
        }

        return labels.get(
            self.time_status,
            "Unknown",
        )

    def __str__(self):
        return f"{self.employee.full_name} - {self.shift_date}"