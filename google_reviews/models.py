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


class GoogleBusinessProfileAccount(models.Model):
    resource_name = models.CharField(max_length=255, unique=True)
    account_name = models.CharField(max_length=255, blank=True)
    account_type = models.CharField(max_length=40, blank=True)
    verification_state = models.CharField(max_length=40, blank=True)
    is_available = models.BooleanField(default=True)
    last_discovered_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("account_name", "resource_name")
        verbose_name = "Google Business Profile account"
        verbose_name_plural = "Google Business Profile accounts"

    def __str__(self):
        return f"{self.account_name or self.resource_name} ({self.resource_name})"


class GoogleBusinessProfileLocation(models.Model):
    account = models.ForeignKey(
        GoogleBusinessProfileAccount,
        on_delete=models.CASCADE,
        related_name="locations",
    )
    resource_name = models.CharField(max_length=255)
    title = models.CharField(max_length=255, blank=True)
    storefront_address = models.JSONField(default=dict, blank=True)
    has_voice_of_merchant = models.BooleanField(null=True, blank=True)
    is_available = models.BooleanField(default=True)
    is_selected = models.BooleanField(default=False)
    google_total_review_count = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    google_average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
    )

    reviews_last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    last_discovered_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("title", "resource_name")
        constraints = [
            models.UniqueConstraint(
                fields=("account", "resource_name"),
                name="unique_google_profile_location",
            ),
            models.UniqueConstraint(
                fields=("is_selected",),
                condition=models.Q(is_selected=True),
                name="one_selected_google_profile_location",
            ),
        ]

    def __str__(self):
        return f"{self.title or self.resource_name} ({self.account.resource_name})"



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

    review_updated_at = models.DateTimeField(
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