# ====================================================
# YD Commercial Cleaning Services
# File: employees/models.py
# Purpose:
# - Store cleaner/employee records
# - Link employees to login accounts
# - Track availability and performance
# ====================================================

<<<<<<< HEAD
from django.contrib.auth.models import User
from django.db import models
=======
from django.db import models
from django.contrib.auth.models import User
>>>>>>> 5815f15 (Initial project commit)


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
<<<<<<< HEAD
        related_name="employee_profile",
=======
        related_name="employee_profile"
>>>>>>> 5815f15 (Initial project commit)
    )

    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)

<<<<<<< HEAD
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default="cleaner")

    availability = models.CharField(
        max_length=30, choices=AVAILABILITY_CHOICES, default="available"
    )

    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=35)
=======
    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default="cleaner"
    )

    availability = models.CharField(
        max_length=30,
        choices=AVAILABILITY_CHOICES,
        default="available"
    )

    hourly_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=35
    )
>>>>>>> 5815f15 (Initial project commit)

    jobs_completed = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
<<<<<<< HEAD
        return self.full_name
=======
        return self.full_name
>>>>>>> 5815f15 (Initial project commit)
