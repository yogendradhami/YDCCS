from unittest.mock import MagicMock, patch

from django.test import TestCase

from .review_utils import get_google_reviews_api


class GoogleReviewsUtilsTests(TestCase):
    def test_get_google_reviews_api_returns_empty_without_account(self):
        with patch("google_reviews.review_utils.GoogleAccount.objects") as objects_mock:
            objects_mock.first.return_value = None
            self.assertEqual(get_google_reviews_api(), [])

    def test_get_google_reviews_api_parses_reviews_successfully(self):
        account = MagicMock(
            access_token="test_token",
            refresh_token="refresh_token",
            save=MagicMock(),
        )

        def request_side_effect(url, headers, timeout):
            response = MagicMock()
            if url.endswith("/accounts"):
                response.status_code = 200
                response.json.return_value = {"accounts": [{"name": "accounts/123"}]}
            elif "/reviews" in url:
                response.status_code = 200
                response.json.return_value = {
                    "reviews": [
                        {
                            "reviewer": {"displayName": "Sam"},
                            "comment": "Great job",
                            "starRating": "FIVE",
                            "createTime": "2026-07-23T12:00:00Z",
                        }
                    ]
                }
            elif "/locations" in url:
                response.status_code = 200
                response.json.return_value = {
                    "locations": [{"name": "accounts/123/locations/456"}]
                }
            else:
                response.status_code = 404
                response.json.return_value = {}
            return response

        with patch("google_reviews.review_utils.GoogleAccount.objects") as objects_mock:
            objects_mock.first.return_value = account
            with patch("google_reviews.review_utils.requests.get", side_effect=request_side_effect):
                reviews = get_google_reviews_api()

        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["reviewer_name"], "Sam")
        self.assertEqual(reviews[0]["comment"], "Great job")
        self.assertEqual(reviews[0]["rating"], "⭐⭐⭐⭐⭐")
