from django.db import models


class GoogleAccount(models.Model):
    email = models.EmailField(blank=True)

    access_token = models.TextField()

<<<<<<< HEAD
    refresh_token = models.TextField(blank=True, null=True)

    connected_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)
=======
    refresh_token = models.TextField(
        blank=True,
        null=True
    )

    connected_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )
>>>>>>> 5815f15 (Initial project commit)

    def __str__(self):
        if self.email:
            return self.email

        return "Google Account"
<<<<<<< HEAD
=======
    


from django.db import models


class GoogleReview(models.Model):
    # Google Review ID
    review_id = models.CharField(
        max_length=255,
        unique=True
    )

    reviewer_name = models.CharField(
        max_length=255
    )

    reviewer_photo = models.URLField(
        blank=True
    )

    rating = models.IntegerField()

    comment = models.TextField()

    review_date = models.DateTimeField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.reviewer_name
    

class GoogleReviewStats(models.Model):

    average_rating = models.FloatField(
        default=0
    )

    total_reviews = models.IntegerField(
        default=0
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return "Google Review Stats"
>>>>>>> 5815f15 (Initial project commit)
