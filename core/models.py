from django.conf import settings
from django.db import models
from .storage import CloudinaryVideoStorage


class FAQQuestion(models.Model):
    """Publicly submitted FAQ question."""

    name = models.CharField(max_length=120)
    email = models.EmailField()
    question = models.TextField()

    page_key = models.CharField(
        max_length=100,
        blank=True,
        help_text=(
            "Optional key to associate the question "
            "with a page/service/suburb"
        ),
    )

    answer = models.TextField(blank=True)

    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    answered_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_published = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"FAQ #{self.id} - {self.question[:60]}"


class TestimonialVideo(models.Model):
    """Customer testimonial videos displayed on the testimonials page."""

    title = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    video = models.FileField(
        storage=CloudinaryVideoStorage(),
        upload_to="testimonial-videos/",
    )

    thumbnail = models.ImageField(
        upload_to="testimonial-video-thumbnails/",
        blank=True,
        null=True,
    )

    active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

class TeamMember(models.Model):
    """Team members displayed on the public Team page."""

    name = models.CharField(
        max_length=150,
        help_text="Team member's full name."
    )

    role = models.CharField(
        max_length=150,
        help_text="Job title or role."
    )

    short_bio = models.TextField(
        blank=True,
        help_text="Short professional biography."
    )

    image = models.ImageField(
        upload_to="team/",
        blank=True,
        null=True,
        help_text="Upload a professional team member photo."
    )

    email = models.EmailField(
        blank=True
    )

    phone = models.CharField(
        max_length=30,
        blank=True
    )

    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers appear first."
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = "Team Member"
        verbose_name_plural = "Team Members"

    def __str__(self):
        return f"{self.name} - {self.role}"