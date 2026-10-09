import json
import uuid
from random import shuffle

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .models import CleaningGameEvent
from .services import (
    MAX_QUESTIONS,
    MAX_SCORE,
    calculate_score,
    get_challenge_questions,
    get_performance_level,
    get_performance_profile,
    record_game_event,
)


@ensure_csrf_cookie
def challenge(request):
    """
    Customer-facing Cleaning Challenge.

    The correct answers are kept server-side and are not exposed
    in the public JavaScript payload.
    """

    questions = get_challenge_questions(
        number=MAX_QUESTIONS
    )

    safe_questions = []

    round_answers = {}
    question_ids = []
    visit_id = uuid.uuid4()
    round_id = uuid.uuid4()

    for question in questions:
        question_id = str(question["id"])
        question_ids.append(question_id)
        shuffled_answers = question["answers"].copy()
        shuffle(shuffled_answers)

        round_answers[question_id] = {
            "correct_answer": question["correct_answer"],
            "answers": question["answers"],
            "category": question.get("category", ""),
        }

        safe_questions.append(
            {
                "id": question["id"],
                "surface": question["surface"],
                "icon": question["icon"],
                "category": question.get("category", ""),
                "scenario": question["scenario"],
                "question": question["question"],
                "answers": shuffled_answers,
                "explanation": question["explanation"],
                "tip": question.get("tip", ""),
            }
        )

    # Store only the current round's answer key in the session.
    request.session["cleaning_game_round"] = round_answers
    request.session["cleaning_game_question_ids"] = question_ids
    request.session["cleaning_game_visit_id"] = str(visit_id)
    request.session["cleaning_game_round_id"] = str(round_id)
    request.session["cleaning_game_round_started"] = False

    # Prevent an old result from being reused.
    request.session["cleaning_game_round_completed"] = False

    quote_url = getattr(
        settings,
        "CLEANING_GAME_QUOTE_URL",
        "/contact/",
    )

    context = {
        "game_questions": safe_questions,
        "game_questions_json": json.dumps(
            safe_questions
        ),
        "game_question_count": len(safe_questions),
        "game_max_score": MAX_SCORE,
        "quote_url": quote_url,
    }

    record_game_event(
        CleaningGameEvent.EVENT_GAME_VIEWED,
        visit_id=visit_id,
    )

    return render(
        request,
        "cleaning_game/challenge.html",
        context,
    )


def calculate_result(request):
    """
    Secure server-side result calculation.

    The browser submits the answers selected by the customer.
    Django compares them against the answer key stored in
    the current anonymous session.
    """

    if request.method != "POST":
        return JsonResponse(
            {
                "success": False,
                "error": "POST required.",
            },
            status=405,
        )

    if request.session.get(
        "cleaning_game_round_completed",
        False,
    ):
        return JsonResponse(
            {
                "success": False,
                "error": "This round has already been completed.",
            },
            status=400,
        )

    round_answers = request.session.get(
        "cleaning_game_round"
    )
    question_ids = request.session.get(
        "cleaning_game_question_ids"
    )

    if not round_answers or not question_ids:
        return JsonResponse(
            {
                "success": False,
                "error": "Game round expired. Please start a new round.",
            },
            status=400,
        )

    try:
        payload = json.loads(
            request.body.decode("utf-8")
        )
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid request.",
            },
            status=400,
        )

    if not isinstance(payload, dict):
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid request.",
            },
            status=400,
        )

    submitted_answers = payload.get(
        "answers",
        {}
    )

    if not isinstance(submitted_answers, dict):
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid answers.",
            },
            status=400,
        )

    expected_question_ids = set(
        round_answers.keys()
    )

    submitted_question_ids = {
        str(question_id)
        for question_id in submitted_answers.keys()
    }

    if submitted_question_ids != expected_question_ids:
        return JsonResponse(
            {
                "success": False,
                "error": "Incomplete or invalid game round.",
            },
            status=400,
        )

    for question_id, round_data in round_answers.items():
        selected_answer = submitted_answers.get(question_id)
        if (
            not isinstance(selected_answer, str)
            or selected_answer not in round_data["answers"]
        ):
            return JsonResponse(
                {
                    "success": False,
                    "error": "One or more selected actions are invalid.",
                },
                status=400,
            )

    correct_answers = 0
    question_results = []

    for question_number, question_id in enumerate(
        question_ids,
        start=1,
    ):
        round_data = round_answers[question_id]
        selected_answer = submitted_answers.get(
            question_id
        )
        is_correct = selected_answer == round_data["correct_answer"]
        question_results.append((question_number, is_correct))
        if is_correct:
            correct_answers += 1

    total_questions = len(round_answers)

    result = calculate_score(
        correct_answers,
        total_questions,
    )

    performance = get_performance_level(
        result["score"]
    )

    profile = get_performance_profile(
        result["score"],
        correct_answers,
        total_questions,
    )

    # Mark this anonymous round as completed.
    request.session[
        "cleaning_game_round_completed"
    ] = True

    visit_id = request.session.get("cleaning_game_visit_id")
    round_id = request.session.get("cleaning_game_round_id")

    for question_number, is_correct in question_results:
        record_game_event(
            CleaningGameEvent.EVENT_QUESTION_ANSWERED,
            visit_id=visit_id,
            round_id=round_id,
            question_number=question_number,
            is_correct=is_correct,
        )

    record_game_event(
        CleaningGameEvent.EVENT_GAME_COMPLETED,
        visit_id=visit_id,
        round_id=round_id,
        score=result["score"],
        correct_answers=correct_answers,
        total_questions=total_questions,
        performance_level=performance,
    )

    return JsonResponse(
        {
            "success": True,
            "result": {
                **result,
                "performance": performance,
                "profile": profile,
                "correct_answers": correct_answers,
                "total_questions": total_questions,
                "max_score": MAX_SCORE,
            },
        }
    )


@require_POST
def track_event(request):
    """
    Record an anonymous Cleaning Challenge event.

    Only whitelisted event types are accepted.
    """

    try:
        payload = json.loads(
            request.body.decode("utf-8")
        )
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid request.",
            },
            status=400,
        )

    if not isinstance(payload, dict):
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid request.",
            },
            status=400,
        )

    event_type = payload.get("event")

    if event_type not in {
        CleaningGameEvent.EVENT_GAME_STARTED,
        CleaningGameEvent.EVENT_QUOTE_CLICKED,
    }:
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid event.",
            },
            status=400,
        )

    if event_type == CleaningGameEvent.EVENT_GAME_STARTED:
        request.session["cleaning_game_round_id"] = str(uuid.uuid4())
        request.session["cleaning_game_round_started"] = True
        request.session["cleaning_game_round_completed"] = False
        record_game_event(
            event_type,
            visit_id=request.session.get("cleaning_game_visit_id"),
            round_id=request.session.get("cleaning_game_round_id"),
        )
    else:
        if not request.session.get("cleaning_game_round_completed"):
            return JsonResponse(
                {
                    "success": False,
                    "error": "Complete the shift before requesting a quote.",
                },
                status=400,
            )

        round_id = request.session.get("cleaning_game_round_id")
        if not CleaningGameEvent.objects.filter(
            event_type=CleaningGameEvent.EVENT_QUOTE_CLICKED,
            round_id=round_id,
        ).exists():
            record_game_event(
                event_type,
                visit_id=request.session.get("cleaning_game_visit_id"),
                round_id=round_id,
            )

    return JsonResponse(
        {
            "success": True,
        }
    )