import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import CleaningGameEvent
from .services import QUESTION_BANK, calculate_score, get_challenge_questions


class CleaningGameServiceTests(TestCase):
    def test_shift_stages_are_ordered_and_limited(self):
        questions = get_challenge_questions(99)

        self.assertEqual(len(questions), 5)
        self.assertEqual(
            [question["id"] for question in questions],
            [
                "site-handover",
                "occupied-workstation",
                "washroom-cross-contamination",
                "chemical-identification",
                "handover-quality-check",
            ],
        )
        self.assertEqual(len(QUESTION_BANK), 5)

    def test_score_is_bounded_and_perfect_bonus_is_applied(self):
        self.assertEqual(calculate_score(5, 5)["score"], 75)
        self.assertEqual(calculate_score(3, 5)["score"], 30)
        self.assertEqual(calculate_score(99, 5)["score"], 75)


class CleaningGameFlowTests(TestCase):
    def start_shift(self):
        page = self.client.get(reverse("cleaning_game:challenge"))
        self.assertEqual(page.status_code, 200)
        self.assertIn("csrftoken", page.cookies)

        started = self.client.post(
            reverse("cleaning_game:track_event"),
            data=json.dumps({"event": CleaningGameEvent.EVENT_GAME_STARTED}),
            content_type="application/json",
        )
        self.assertEqual(started.status_code, 200)
        return self.client.session["cleaning_game_round"]

    def submit_answers(self, round_answers, correct_count=5):
        answers = {}
        for index, (question_id, question) in enumerate(
            round_answers.items()
        ):
            if index < correct_count:
                answers[question_id] = question["correct_answer"]
            else:
                answers[question_id] = next(
                    choice
                    for choice in question["answers"]
                    if choice != question["correct_answer"]
                )

        return self.client.post(
            reverse("cleaning_game:calculate_result"),
            data=json.dumps({"answers": answers, "score": 75}),
            content_type="application/json",
        )

    def test_server_validates_answers_and_records_verified_results(self):
        round_answers = self.start_shift()

        response = self.submit_answers(round_answers, correct_count=3)

        self.assertEqual(response.status_code, 200)
        result = response.json()["result"]
        self.assertEqual(result["correct_answers"], 3)
        self.assertEqual(result["total_questions"], 5)
        self.assertEqual(result["score"], 30)

        question_events = CleaningGameEvent.objects.filter(
            event_type=CleaningGameEvent.EVENT_QUESTION_ANSWERED
        )
        self.assertEqual(question_events.count(), 5)
        self.assertEqual(
            question_events.filter(is_correct=True).count(),
            3,
        )
        completion = CleaningGameEvent.objects.get(
            event_type=CleaningGameEvent.EVENT_GAME_COMPLETED
        )
        self.assertEqual(completion.score, 30)
        self.assertEqual(completion.correct_answers, 3)
        self.assertEqual(completion.total_questions, 5)
        self.assertIsNotNone(completion.round_id)
        self.assertIsNotNone(completion.visit_id)

        duplicate = self.submit_answers(round_answers)
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(
            CleaningGameEvent.objects.filter(
                event_type=CleaningGameEvent.EVENT_GAME_COMPLETED
            ).count(),
            1,
        )

    def test_result_rejects_choices_not_offered_by_the_server(self):
        round_answers = self.start_shift()
        answers = {
            question_id: "An action that was not offered"
            for question_id in round_answers
        }

        response = self.client.post(
            reverse("cleaning_game:calculate_result"),
            data=json.dumps({"answers": answers}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            CleaningGameEvent.objects.filter(
                event_type=CleaningGameEvent.EVENT_GAME_COMPLETED
            ).exists()
        )

    def test_verified_result_does_not_depend_on_start_tracking(self):
        page = self.client.get(reverse("cleaning_game:challenge"))
        self.assertEqual(page.status_code, 200)
        round_answers = self.client.session["cleaning_game_round"]

        response = self.submit_answers(round_answers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"]["score"], 75)

    def test_analytics_rates_use_linked_verified_rounds(self):
        first_round = self.start_shift()
        completed = self.submit_answers(first_round, correct_count=3)
        self.assertEqual(completed.status_code, 200)

        quote_click = self.client.post(
            reverse("cleaning_game:track_event"),
            data=json.dumps({"event": CleaningGameEvent.EVENT_QUOTE_CLICKED}),
            content_type="application/json",
        )
        self.assertEqual(quote_click.status_code, 200)

        duplicate_quote_click = self.client.post(
            reverse("cleaning_game:track_event"),
            data=json.dumps({"event": CleaningGameEvent.EVENT_QUOTE_CLICKED}),
            content_type="application/json",
        )
        self.assertEqual(duplicate_quote_click.status_code, 200)
        self.assertEqual(
            CleaningGameEvent.objects.filter(
                event_type=CleaningGameEvent.EVENT_QUOTE_CLICKED
            ).count(),
            1,
        )

        self.start_shift()

        user = get_user_model().objects.create_user(
            username="analytics-reviewer",
            password="test-password",
        )
        self.client.force_login(user)
        response = self.client.get(
            reverse("cleaning_game:cleaning_game_analytics")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_views"], 2)
        self.assertEqual(response.context["total_starts"], 2)
        self.assertEqual(response.context["total_completions"], 1)
        self.assertEqual(response.context["start_rate"], 100)
        self.assertEqual(response.context["completion_rate"], 50)
        self.assertEqual(response.context["quote_clicks"], 1)
        self.assertEqual(response.context["quote_conversion_rate"], 100)
        self.assertEqual(response.context["average_accuracy"], 60)
        self.assertEqual(response.context["total_questions_answered"], 5)
        self.assertEqual(len(response.context["question_stats"]), 5)
        self.assertEqual(
            response.context["question_stats"][0]["stage_name"],
            "Site handover",
        )
