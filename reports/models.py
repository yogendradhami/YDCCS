from django.db import models

from bookings.models import Booking


class CleaningReport(models.Model):

    booking = models.OneToOneField(
        Booking, on_delete=models.CASCADE, related_name="cleaning_report"
    )

    pdf_file = models.FileField(upload_to="cleaning_reports/", blank=True, null=True)

    emailed_to_customer = models.BooleanField(default=False)

    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report - Booking #{self.booking.id}"
