from django.db import models


class CleaningGameEvent(models.Model):
    """
    Anonymous analytics events for the Cleaning Challenge.

    No customer identity, email, phone number, or booking
    information is stored here.
    """

    EVENT_GAME_VIEWED = "game_viewed"
    EVENT_GAME_STARTED = "game_started"
    EVENT_QUESTION_ANSWERED = "question_answered"
    EVENT_GAME_COMPLETED = "game_completed"
    EVENT_QUOTE_CLICKED = "quote_clicked"

    EVENT_CHOICES = [
        (
            EVENT_GAME_VIEWED,
            "Game Viewed",
        ),
        (
            EVENT_GAME_STARTED,
            "Game Started",
        ),
        (
            EVENT_QUESTION_ANSWERED,
            "Question Answered",
        ),
        (
            EVENT_GAME_COMPLETED,
            "Game Completed",
        ),
        (
            EVENT_QUOTE_CLICKED,
            "Quote Clicked",
        ),
    ]

    event_type = models.CharField(
        max_length=40,
        choices=EVENT_CHOICES,
        db_index=True,
    )

    visit_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
    )

    round_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
    )

    question_number = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    is_correct = models.BooleanField(
        null=True,
        blank=True,
    )

    score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    correct_answers = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    total_questions = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    performance_level = models.CharField(
        max_length=40,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=[
                    "event_type",
                    "created_at",
                ]
            ),
            models.Index(
                fields=[
                    "question_number",
                    "created_at",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"{self.get_event_type_display()} "
            f"— {self.created_at:%Y-%m-%d %H:%M}"
        )