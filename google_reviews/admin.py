from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import redirect

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


    change_list_template = "reviews/google_review_change_list.html"
    def get_urls(self):
        urls = super().get_urls()

        custom_urls = [
            path(
                "sync/",
                self.admin_site.admin_view(self.sync_reviews),
                name="sync_google_reviews",
            ),
        ]

        return custom_urls + urls


    def sync_reviews(self, request):

        from .views import sync_google_reviews

        response = sync_google_reviews(request)

        if response.status_code == 200:
            messages.success(
                request,
                response.content.decode()
            )
        else:
            messages.error(
                request,
                response.content.decode()
            )

        return redirect("../")