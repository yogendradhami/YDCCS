from django.contrib import admin

from .models import GoogleAccount, GoogleReview


@admin.register(GoogleAccount)
class GoogleAccountAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "connected_at",
        "updated_at",
    )


@admin.register(GoogleReview)
class GoogleReviewAdmin(admin.ModelAdmin):

    list_display = (
        "reviewer_name",
        "rating",
        "review_date",
    )

    search_fields = (
        "reviewer_name",
        "comment",
    )

    readonly_fields = (
        "review_id",
        "created_at",
        "updated_at",
    )