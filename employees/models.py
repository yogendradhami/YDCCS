# ====================================================
# YD Commercial Cleaning Services
# File: employees/models.py
# Purpose:
# - Store cleaner/employee records
# - Link employees to login accounts
# - Track availability and performance
# ====================================================

from django.contrib.auth.models import User
from django.db import models


class Employee(models.Model):
    ROLE_CHOICES = [
        ("cleaner", "Cleaner"),
        ("supervisor", "Supervisor"),
        ("manager", "Manager"),
        ("admin", "Admin"),
    ]

    AVAILABILITY_CHOICES = [
        ("available", "Available"),
        ("unavailable", "Unavailable"),
        ("on_leave", "On Leave"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_profile",
    )

    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    image = models.ImageField(
        upload_to="employees/",
        blank=True,
        null=True,
        help_text="Professional employee photo displayed on the public Team page.",
    )

    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default="cleaner")

    availability = models.CharField(
        max_length=30, choices=AVAILABILITY_CHOICES, default="available"
    )

    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=35)

    jobs_completed = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name


class EmployeeGoogleAccount(models.Model):
    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name="google_calendar_account",
    )

    email = models.EmailField(blank=True)

    access_token = models.TextField()

    refresh_token = models.TextField(blank=True, null=True)

    connected_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.email:
            return f"{self.employee.full_name} - {self.email}"

        return f"{self.employee.full_name} - Google Calendar"