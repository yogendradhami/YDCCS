from django.contrib.auth.models import User
from django.db import models


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ("quote", "Quote"),
        ("booking", "Booking"),
        ("invoice", "Invoice"),
        ("customer", "Customer"),
        ("employee", "Employee"),
        ("gallery", "Gallery"),
        ("review", "Review"),
        ("report", "Report"),
        ("contract", "Contract"),
        ("attendance", "Attendance"),
        ("payroll", "Payroll"),
        ("leave", "Leave"),
        ("roster", "Roster"),
        ("system", "System"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=30, choices=NOTIFICATION_TYPES, default="system"
    )
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class ReminderCenterReadState(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="reminder_center_read_state",
    )
    seen_reminder_keys = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Reminder center read state for {self.user}"
