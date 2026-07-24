from django.db import models

from customers.models import Customer
from employees.models import Employee


class Booking(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("assigned", "Assigned"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    SERVICE_CHOICES = [
        ("Commercial Cleaning", "Commercial Cleaning"),
        ("Office Cleaning", "Office Cleaning"),
        ("House Cleaning", "House Cleaning"),
        ("End of Lease Cleaning", "End of Lease Cleaning"),
        ("Window Cleaning", "Window Cleaning"),
        ("Deep Cleaning", "Deep Cleaning"),
        ("Post Construction Cleaning", "Post Construction Cleaning"),
    ]

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="bookings"
    )

    service_type = models.CharField(max_length=100, choices=SERVICE_CHOICES)

    booking_date = models.DateField()
    booking_time = models.TimeField()

    address = models.CharField(max_length=255)
    suburb_postcode = models.CharField(max_length=150)

    quoted_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    assigned_employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_bookings",
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.full_name} - {self.service_type} - {self.booking_date}"


class JobPhoto(models.Model):
    PHOTO_TYPES = [
        ("before", "Before"),
        ("after", "After"),
    ]

    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="job_photos"
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_job_photos",
    )

    photo_type = models.CharField(max_length=20, choices=PHOTO_TYPES)

    image = models.FileField(upload_to="job_photos/")

    employee_signature = models.ImageField(
        upload_to="signatures/employees/", blank=True, null=True
    )

    customer_signature = models.ImageField(
        upload_to="signatures/customers/", blank=True, null=True
    )

    customer_signed_at = models.DateTimeField(blank=True, null=True)

    employee_signed_at = models.DateTimeField(blank=True, null=True)

    notes = models.TextField(blank=True)

    google_calendar_event_id = models.CharField(max_length=255, blank=True, null=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking.customer.full_name} - {self.get_photo_type_display()}"
