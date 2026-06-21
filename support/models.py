from django.db import models

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
        Customer, on_delete=models.CASCADE, related_name="support_tickets"
    )

    subject = models.CharField(max_length=255)

    message = models.TextField()

    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default="medium"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.subject
