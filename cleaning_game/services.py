"""
Cleaning Challenge business logic.

This module intentionally contains no database logic.
The Phase 2 challenge is completely anonymous and
customer-facing.
"""

MAX_QUESTIONS = 5
POINTS_PER_CORRECT = 10
PERFECT_ROUND_BONUS = 25
MAX_SCORE = 75


QUESTION_BANK = [
    {
        "id": "site-handover",
        "surface": "STAGE 1 · SITE HANDOVER",
        "icon": "commercial",
        "category": "Site Safety",
        "scenario": (
            "You arrive for the morning office clean. The site "
            "contact points out a wet patch by reception and says "
            "staff will start arriving shortly."
        ),
        "question": "What is your safest first move?",
        "answers": [
            "Secure and sign the area, assess the hazard, then follow the site procedure",
            "Mop it immediately without closing the walkway",
            "Put a chair over it and begin cleaning somewhere else",
            "Leave it for the next scheduled clean",
        ],
        "correct_answer": (
            "Secure and sign the area, assess the hazard, then follow the site procedure"
        ),
        "explanation": (
            "A real shift starts with the handover and a hazard "
            "check. Keep people away from the wet area and use the "
            "site's procedure before resuming work."
        ),
        "tip": (
            "Never leave a wet floor unmarked in an occupied building."
        ),
    },
    {
        "id": "occupied-workstation",
        "surface": "STAGE 2 · OPEN OFFICE",
        "icon": "cloth",
        "category": "Workstation Care",
        "scenario": (
            "The office is occupied. A desk has papers and a laptop "
            "on it, while dust is visible on the clear monitor stand "
            "and nearby ledge."
        ),
        "question": "How do you clean this workstation professionally?",
        "answers": [
            "Leave personal items in place, clean agreed clear surfaces with a clean cloth, and work high to low",
            "Move the papers and laptop so you can wipe every part of the desk",
            "Dust the ledge after vacuuming so debris falls onto the finished floor",
            "Spray cleaner directly across the desk and equipment",
        ],
        "correct_answer": (
            "Leave personal items in place, clean agreed clear surfaces with a clean cloth, and work high to low"
        ),
        "explanation": (
            "Respect personal property and the agreed scope. "
            "Cleaning high-to-low keeps loosened dust off areas "
            "you have already finished."
        ),
        "tip": (
            "Use a suitable cloth and product; do not spray near "
            "electronics or documents."
        ),
    },
    {
        "id": "washroom-cross-contamination",
        "surface": "STAGE 3 · WASHROOM",
        "icon": "bathroom",
        "category": "Hygiene Control",
        "scenario": (
            "You move from the office into the washroom. Your kit "
            "has a designated washroom cloth set and a general-use "
            "cloth set."
        ),
        "question": "Which workflow best controls cross-contamination?",
        "answers": [
            "Use the washroom-only cloths, follow the site's clean-to-dirty sequence, and keep them separate from office cloths",
            "Use the same cloth throughout so no area is missed",
            "Use the general-use cloth first, then finish with the washroom cloth on the office desk",
            "Rinse a used cloth quickly and treat it as clean",
        ],
        "correct_answer": (
            "Use the washroom-only cloths, follow the site's clean-to-dirty sequence, and keep them separate from office cloths"
        ),
        "explanation": (
            "Dedicated, clearly separated equipment and a "
            "consistent sequence reduce the chance of carrying "
            "contamination between areas."
        ),
        "tip": (
            "Follow the site's colour-coding and cloth-change "
            "procedures rather than relying on a quick rinse."
        ),
    },
    {
        "id": "chemical-identification",
        "surface": "STAGE 4 · STAFF KITCHEN",
        "icon": "chemical",
        "category": "Chemical Safety",
        "scenario": (
            "There is a sticky mark on the kitchen counter. A spray "
            "bottle nearby has no readable product label."
        ),
        "question": "What do you do before treating the mark?",
        "answers": [
            "Do not use the unidentified bottle; check the approved product and instructions with the site contact",
            "Test the bottle on a small part of the counter",
            "Mix it with another cleaner to make it stronger",
            "Use extra product and wipe it away quickly",
        ],
        "correct_answer": (
            "Do not use the unidentified bottle; check the approved product and instructions with the site contact"
        ),
        "explanation": (
            "Never use an unidentified chemical. Confirm the "
            "approved, labelled product and follow its directions "
            "and the workplace safety procedure."
        ),
        "tip": (
            "Never mix cleaning chemicals or decant them into "
            "unlabelled containers."
        ),
    },
    {
        "id": "handover-quality-check",
        "surface": "STAGE 5 · FINAL WALK-THROUGH",
        "icon": "order",
        "category": "Quality and Handover",
        "scenario": (
            "The agreed areas are clean. A washroom floor is still "
            "damp and the office is about to reopen."
        ),
        "question": "What is the right way to finish the shift?",
        "answers": [
            "Keep the area signed and controlled until safe, complete the checklist, and hand over any outstanding issue",
            "Remove the sign as soon as mopping is finished",
            "Leave without checking the agreed areas because the schedule is tight",
            "Put the sign away and ask the first staff member to watch the floor",
        ],
        "correct_answer": (
            "Keep the area signed and controlled until safe, complete the checklist, and hand over any outstanding issue"
        ),
        "explanation": (
            "A professional clean includes a safe reopening, a "
            "quality check against the agreed scope, and a clear "
            "handover of anything that could not be completed."
        ),
        "tip": (
            "Do not claim a floor is dry or an area is complete "
            "until it has been checked."
        ),
    },
]


def get_challenge_questions(number=MAX_QUESTIONS):
    """
    Return the ordered stages for one realistic cleaning shift.

    The function never returns more stages than a complete shift contains.
    """

    try:
        number = int(number)
    except (TypeError, ValueError):
        number = MAX_QUESTIONS

    number = max(
        1,
        min(
            number,
            MAX_QUESTIONS,
        ),
    )

    return QUESTION_BANK[:number]


def calculate_score(
    correct_answers,
    total_questions,
):
    """
    Calculate the challenge score.

    Scoring:
    - 10 points per correct answer
    - 25 point perfect-round bonus
    - maximum 75 points for five questions
    """

    try:
        correct_answers = int(correct_answers)
    except (TypeError, ValueError):
        correct_answers = 0

    try:
        total_questions = int(total_questions)
    except (TypeError, ValueError):
        total_questions = 0

    total_questions = max(
        0,
        min(
            total_questions,
            MAX_QUESTIONS,
        ),
    )

    correct_answers = max(
        0,
        min(
            correct_answers,
            total_questions,
        ),
    )

    base_score = (
        correct_answers *
        POINTS_PER_CORRECT
    )

    perfect_round = (
        total_questions > 0
        and correct_answers == total_questions
    )

    perfect_bonus = (
        PERFECT_ROUND_BONUS
        if perfect_round
        else 0
    )

    score = min(
        base_score + perfect_bonus,
        MAX_SCORE,
    )

    accuracy = (
        round(
            (
                correct_answers /
                total_questions
            ) * 100
        )
        if total_questions
        else 0
    )

    return {
        "score": score,
        "correct_answers": correct_answers,
        "total_questions": total_questions,
        "accuracy": accuracy,
        "perfect_round": perfect_round,
        "perfect_bonus": perfect_bonus,
    }


def get_performance_level(score):
    """Return a concise performance level for the completed shift."""

    try:
        score = int(score)
    except (TypeError, ValueError):
        score = 0

    if score >= 60:
        return "Outstanding Shift"

    if score >= 40:
        return "Shift Ready"

    if score >= 20:
        return "Developing Operative"

    return "Coaching Recommended"


def get_performance_profile(
    score,
    correct_answers=0,
    total_questions=MAX_QUESTIONS,
):
    """
    Return personalised result messaging.

    No personal data is used or stored.
    """

    level = get_performance_level(score)

    profiles = {
        "Outstanding Shift": {
            "eyebrow": "EXCELLENT RESULT",
            "headline": (
                "You ran a safe, high-quality shift."
            ),
            "message": (
                "Excellent decisions across the site. You "
                "followed a safe sequence and protected the "
                "quality of the handover."
            ),
            "tip": (
                "Keep using the site scope, area-specific "
                "equipment and final inspection on every shift."
            ),
            "cta": (
                "See how our team maintains that standard."
            ),
        },
        "Shift Ready": {
            "eyebrow": "STRONG RESULT",
            "headline": (
                "A solid shift with a few things to refine."
            ),
            "message": (
                "You made several sound site decisions. A "
                "couple of process improvements can help you "
                "deliver a more consistent handover."
            ),
            "tip": (
                "Keep checking product labels, separating "
                "area equipment and working to the site checklist."
            ),
            "cta": (
                "Our professional team can take care of the work."
            ),
        },
        "Developing Operative": {
            "eyebrow": "GOOD START",
            "headline": (
                "Your shift is underway; keep building consistency."
            ),
            "message": (
                "Some of your decisions could affect safety or "
                "the finish. Reviewing the site process will "
                "help you improve."
            ),
            "tip": (
                "Use a written checklist and ask the site contact "
                "when the scope or product is unclear."
            ),
            "cta": (
                "A trained team can handle the details for you."
            ),
        },
        "Coaching Recommended": {
            "eyebrow": "KEEP LEARNING",
            "headline": (
                "A safe process comes before a fast clean."
            ),
            "message": (
                "This shift exposed some important safety and "
                "quality steps. The right site procedure protects "
                "both people and surfaces."
            ),
            "tip": (
                "Pause when a hazard or unidentified chemical is "
                "present, and confirm the safe procedure before "
                "continuing."
            ),
            "cta": (
                "Prefer to leave the cleaning to a trained team?"
            ),
        },
    }

    profile = profiles[level].copy()

    profile.update(
        {
            "level": level,
            "correct_answers": max(
                0,
                int(correct_answers or 0),
            ),
            "total_questions": max(
                0,
                int(total_questions or 0),
            ),
        }
    )

    return profile


from .models import CleaningGameEvent


ALLOWED_ANALYTICS_EVENTS = {
    CleaningGameEvent.EVENT_GAME_VIEWED,
    CleaningGameEvent.EVENT_GAME_STARTED,
    CleaningGameEvent.EVENT_QUESTION_ANSWERED,
    CleaningGameEvent.EVENT_GAME_COMPLETED,
    CleaningGameEvent.EVENT_QUOTE_CLICKED,
}


def record_game_event(
    event_type,
    *,
    visit_id=None,
    round_id=None,
    question_number=None,
    is_correct=None,
    score=None,
    correct_answers=None,
    total_questions=None,
    performance_level="",
):
    """
    Record one anonymous Cleaning Challenge event.
    """

    if event_type not in ALLOWED_ANALYTICS_EVENTS:
        return None

    return CleaningGameEvent.objects.create(
        event_type=event_type,
        visit_id=visit_id,
        round_id=round_id,
        question_number=question_number,
        is_correct=is_correct,
        score=score,
        correct_answers=correct_answers,
        total_questions=total_questions,
        performance_level=performance_level or "",
    )