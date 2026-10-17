from django.contrib import admin
from django import forms
from django.core.files.uploadedfile import UploadedFile
from pathlib import Path

from .models import FAQQuestion, TestimonialVideo


class TestimonialVideoAdminForm(forms.ModelForm):
    class Meta:
        model = TestimonialVideo
        fields = "__all__"

    def clean_video(self):
        video = self.cleaned_data.get("video")
        if not isinstance(video, UploadedFile):
            return video
        if video.size > 100 * 1024 * 1024:
            raise forms.ValidationError("Testimonial videos must be 100 MB or smaller.")
        allowed = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv", ".mpeg", ".mpg", ".ogv", ".3gp"}
        if Path(video.name).suffix.lower() not in allowed:
            raise forms.ValidationError("Upload a supported video file such as MP4, MOV, or WebM.")
        return video

    def clean_thumbnail(self):
        thumbnail = self.cleaned_data.get("thumbnail")
        if isinstance(thumbnail, UploadedFile) and thumbnail.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Video thumbnails must be 10 MB or smaller.")
        return thumbnail


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
    form = TestimonialVideoAdminForm
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
