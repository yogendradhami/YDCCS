from django.db import models
<<<<<<< HEAD

=======
>>>>>>> 5815f15 (Initial project commit)
from customers.models import Customer
from employees.models import Employee


class CleaningContract(models.Model):
    FREQUENCY_CHOICES = [
        ("weekly", "Weekly"),
        ("fortnightly", "Fortnightly"),
        ("monthly", "Monthly"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("paused", "Paused"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

<<<<<<< HEAD
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="contracts"
    )
=======
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="contracts")
>>>>>>> 5815f15 (Initial project commit)
    service_type = models.CharField(max_length=100)
    frequency = models.CharField(max_length=30, choices=FREQUENCY_CHOICES)

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    preferred_time = models.TimeField()

    address = models.CharField(max_length=255)
    suburb_postcode = models.CharField(max_length=150)

    assigned_employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
<<<<<<< HEAD
        related_name="contracts",
=======
        related_name="contracts"
>>>>>>> 5815f15 (Initial project commit)
    )

    price_per_visit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="active")
    notes = models.TextField(blank=True)

    bookings_generated_until = models.DateField(null=True, blank=True)

    renewal_30_sent = models.BooleanField(default=False)

    renewal_14_sent = models.BooleanField(default=False)

    renewal_7_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
<<<<<<< HEAD
        return f"{self.customer.full_name} - {self.service_type} - {self.frequency}"
=======
        return f"{self.customer.full_name} - {self.service_type} - {self.frequency}"
>>>>>>> 5815f15 (Initial project commit)
