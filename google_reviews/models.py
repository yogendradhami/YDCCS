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



class GoogleReview(models.Model):

    review_id = models.CharField(
        max_length=255,
        unique=True
    )

    reviewer_name = models.CharField(
        max_length=255,
        blank=True
    )

    reviewer_photo = models.URLField(
        blank=True,
        null=True
    )

    rating = models.CharField(
        max_length=20,
        blank=True
    )

    comment = models.TextField(
        blank=True
    )

    review_date = models.DateTimeField(
        blank=True,
        null=True
    )

    reply = models.TextField(
        blank=True
    )

    reply_date = models.DateTimeField(
        blank=True,
        null=True
    )

    review_url = models.URLField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )


    def __str__(self):
        return f"{self.reviewer_name} - {self.rating}"