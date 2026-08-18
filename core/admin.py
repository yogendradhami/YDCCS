from django.contrib import admin

from .models import FAQQuestion, TestimonialVideo


@admin.register(FAQQuestion)
class FAQQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "question",
        "name",
        "email",
        "is_published",
        "created_at",
    )

    list_filter = (
        "is_published",
        "created_at",
    )

    search_fields = (
        "question",
        "answer",
        "name",
        "email",
    )

    readonly_fields = (
        "created_at",
        "answered_at",
    )


@admin.register(TestimonialVideo)
class TestimonialVideoAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "active",
        "created_at",
    )

    list_filter = (
        "active",
    )

    search_fields = (
        "title",
        "description",
    )