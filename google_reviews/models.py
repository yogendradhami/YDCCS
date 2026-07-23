from django.db import models


class GoogleAccount(models.Model):
    email = models.EmailField(blank=True)

    access_token = models.TextField()

    refresh_token = models.TextField(blank=True, null=True)

    connected_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.email:
            return self.email

        return "Google Account"
