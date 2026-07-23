from django.contrib import admin

from .models import Review, ReviewRequest


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


@admin.register(ReviewRequest)
class ReviewRequestAdmin(admin.ModelAdmin):

    list_display = (
        "customer_name",
        "customer_email",
        "request_sent",
        "review_received",
        "created_at",
    )
