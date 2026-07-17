from django.contrib import admin
<<<<<<< HEAD

from .models import Review, ReviewRequest
=======
from .models import Review
from .models import ReviewRequest
>>>>>>> 5815f15 (Initial project commit)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "customer_name",
        "suburb",
        "rating",
        "featured",
        "created_at",
    )

    list_filter = (
        "rating",
        "featured",
        "created_at",
    )

    search_fields = (
        "customer_name",
        "suburb",
        "review_text",
    )

<<<<<<< HEAD

=======
>>>>>>> 5815f15 (Initial project commit)
@admin.register(ReviewRequest)
class ReviewRequestAdmin(admin.ModelAdmin):

    list_display = (
        "customer_name",
        "customer_email",
        "request_sent",
        "review_received",
        "created_at",
<<<<<<< HEAD
    )
=======
    )
>>>>>>> 5815f15 (Initial project commit)
