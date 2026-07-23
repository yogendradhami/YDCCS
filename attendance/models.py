from django.db import models

from bookings.models import Booking


class AttendanceLog(models.Model):
    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="attendance_logs"
    )

    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="attendance_logs"
    )

    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)

    check_in_latitude = models.DecimalField(
        max_digits=12, decimal_places=8, null=True, blank=True
    )

    check_in_longitude = models.DecimalField(
        max_digits=12, decimal_places=8, null=True, blank=True
    )

    check_out_latitude = models.DecimalField(
        max_digits=12, decimal_places=8, null=True, blank=True
    )

    check_out_longitude = models.DecimalField(
        max_digits=12, decimal_places=8, null=True, blank=True
    )

    total_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.employee.full_name} - {self.booking.id}"
