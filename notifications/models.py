<<<<<<< HEAD
from django.contrib.auth.models import User
from django.db import models
=======
from django.db import models
from django.contrib.auth.models import User
>>>>>>> 5815f15 (Initial project commit)


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

<<<<<<< HEAD
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=30, choices=NOTIFICATION_TYPES, default="system"
    )
=======
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES, default="system")
>>>>>>> 5815f15 (Initial project commit)
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
<<<<<<< HEAD
        return self.title
=======
        return self.title
>>>>>>> 5815f15 (Initial project commit)
