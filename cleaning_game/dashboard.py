from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import render
from django.utils import timezone

from .models import CleaningGameEvent
from .services import MAX_SCORE


STAGE_LABELS = {
    1: "Site handover",
    2: "Occupied office",
    3: "Washroom hygiene",
    4: "Chemical safety",
    5: "Final inspection",
}


@login_required
def cleaning_game_analytics(request):
    """Show verified challenge activity from the last 30 days."""

    period_start = timezone.now() - timedelta(days=30)
    events = CleaningGameEvent.objects.filter(
        created_at__gte=period_start
    )

    view_events = events.filter(
        event_type=CleaningGameEvent.EVENT_GAME_VIEWED
    )
    start_events = events.filter(
        event_type=CleaningGameEvent.EVENT_GAME_STARTED
    )
    completion_events = events.filter(
        event_type=CleaningGameEvent.EVENT_GAME_COMPLETED
    )
    quote_events = events.filter(
        event_type=CleaningGameEvent.EVENT_QUOTE_CLICKED
    )

    total_views = view_events.count()
    started_visits = (
        start_events.exclude(visit_id__isnull=True)
        .values("visit_id")
        .distinct()
        .count()
    )
    started_rounds = start_events.exclude(
        round_id__isnull=True
    ).values("round_id")
    total_starts = started_rounds.distinct().count()

    total_completions = completion_events.count()
    completed_rounds = completion_events.exclude(
        round_id__isnull=True
    ).values("round_id")
    identified_completions = completed_rounds.distinct().count()

    completed_started_rounds = (
        completion_events.filter(round_id__in=started_rounds)
        .values("round_id")
        .distinct()
        .count()
    )
    quote_rounds = quote_events.exclude(
        round_id__isnull=True
    ).values("round_id")
    quote_clicks = (
        completion_events.filter(round_id__in=quote_rounds)
        .values("round_id")
        .distinct()
        .count()
    )

    completion_summary = completion_events.aggregate(
        average_score=Avg("score"),
        perfect_rounds=Count(
            "id",
            filter=Q(score=MAX_SCORE),
        ),
        correct_answers=Sum("correct_answers"),
        total_questions=Sum("total_questions"),
    )
    answer_events = events.filter(
        event_type=CleaningGameEvent.EVENT_QUESTION_ANSWERED,
        is_correct__isnull=False,
    )
    question_stats = list(
        answer_events.values("question_number")
        .annotate(
            answer_count=Count("id"),
            correct_count=Count(
                "id",
                filter=Q(is_correct=True),
            ),
        )
        .order_by("question_number")
    )

    for item in question_stats:
        item["stage_name"] = STAGE_LABELS.get(
            item["question_number"],
            f"Shift stage {item['question_number']}",
        )
        item["percentage"] = round(
            item["correct_count"] / item["answer_count"] * 100,
            1,
        ) if item["answer_count"] else 0

    total_questions_answered = (
        completion_summary["total_questions"] or 0
    )
    total_correct_answers = completion_summary["correct_answers"] or 0
    recent_events = (
        events.filter(
            event_type__in=[
                CleaningGameEvent.EVENT_GAME_STARTED,
                CleaningGameEvent.EVENT_GAME_COMPLETED,
                CleaningGameEvent.EVENT_QUOTE_CLICKED,
            ]
        )
        .order_by("-created_at")[:20]
    )

    context = {
        "total_views": total_views,
        "total_starts": total_starts,
        "total_completions": total_completions,
        "quote_clicks": quote_clicks,
        "start_rate": round(started_visits / total_views * 100, 1)
        if total_views
        else 0,
        "completion_rate": round(
            completed_started_rounds / total_starts * 100,
            1,
        ) if total_starts else 0,
        "quote_conversion_rate": round(
            quote_clicks / identified_completions * 100,
            1,
        ) if identified_completions else 0,
        "perfect_rounds": completion_summary["perfect_rounds"] or 0,
        "average_score": round(
            completion_summary["average_score"] or 0,
            1,
        ),
        "average_accuracy": round(
            total_correct_answers / total_questions_answered * 100,
            1,
        ) if total_questions_answered else 0,
        "total_questions_answered": total_questions_answered,
        "question_stats": question_stats,
        "recent_events": recent_events,
        "period_days": 30,
    }

    return render(
        request,
        "dashboard/cleaning_game/cleaning_game_analytics.html",
        context,
    )
