from django.db import models


class Review(models.Model):
    RATING_CHOICES = [
        (5, "5 Stars"),
        (4, "4 Stars"),
        (3, "3 Stars"),
        (2, "2 Stars"),
        (1, "1 Star"),
    ]

    customer_name = models.CharField(max_length=100)
    suburb = models.CharField(max_length=100, blank=True)
    rating = models.IntegerField(choices=RATING_CHOICES, default=5)
    review_text = models.TextField()
    featured = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def stars(self):
        return "★" * self.rating

    def __str__(self):
        return f"{self.customer_name} - {self.rating} Stars"
<<<<<<< HEAD


class ReviewRequest(models.Model):

    booking = models.ForeignKey("bookings.Booking", on_delete=models.CASCADE)

    customer_name = models.CharField(max_length=150)

    customer_email = models.EmailField()

    request_sent = models.BooleanField(default=False)

    review_received = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.customer_name
=======
    

class ReviewRequest(models.Model):

    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.CASCADE
    )

    customer_name = models.CharField(
        max_length=150
    )

    customer_email = models.EmailField()

    request_sent = models.BooleanField(
        default=False
    )

    review_received = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.customer_name
>>>>>>> 5815f15 (Initial project commit)
