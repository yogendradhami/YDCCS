from django.db import models
<<<<<<< HEAD

=======
>>>>>>> 5815f15 (Initial project commit)
from customers.models import Customer


class SupportTicket(models.Model):

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]

    customer = models.ForeignKey(
<<<<<<< HEAD
        Customer, on_delete=models.CASCADE, related_name="support_tickets"
    )

    subject = models.CharField(max_length=255)
=======
        Customer,
        on_delete=models.CASCADE,
        related_name="support_tickets"
    )

    subject = models.CharField(
        max_length=255
    )
>>>>>>> 5815f15 (Initial project commit)

    message = models.TextField()

    priority = models.CharField(
<<<<<<< HEAD
        max_length=20, choices=PRIORITY_CHOICES, default="medium"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)
=======
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="medium"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="open"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )
>>>>>>> 5815f15 (Initial project commit)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
<<<<<<< HEAD
        return self.subject
=======
        return self.subject
>>>>>>> 5815f15 (Initial project commit)
