<<<<<<< HEAD
# Create your models here.
from django.db import models

from bookings.models import Booking
from employees.models import Employee
=======
from django.db import models

# Create your models here.
from django.db import models
from employees.models import Employee
from bookings.models import Booking
>>>>>>> 5815f15 (Initial project commit)


class Roster(models.Model):

    STATUS_CHOICES = (
        ("scheduled", "Scheduled"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    )

    employee = models.ForeignKey(
<<<<<<< HEAD
        Employee, on_delete=models.CASCADE, related_name="rosters"
    )

    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="rosters"
=======
        Employee,
        on_delete=models.CASCADE,
        related_name="rosters"
    )

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="rosters"
>>>>>>> 5815f15 (Initial project commit)
    )

    shift_date = models.DateField()

    start_time = models.TimeField()

    end_time = models.TimeField()

    status = models.CharField(
<<<<<<< HEAD
        max_length=20, choices=STATUS_CHOICES, default="scheduled"
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
=======
        max_length=20,
        choices=STATUS_CHOICES,
        default="scheduled"
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )
>>>>>>> 5815f15 (Initial project commit)

    class Meta:
        ordering = ["shift_date", "start_time"]

    def __str__(self):
<<<<<<< HEAD
        return f"{self.employee.full_name} - {self.shift_date}"
=======
        return f"{self.employee.full_name} - {self.shift_date}"
>>>>>>> 5815f15 (Initial project commit)
