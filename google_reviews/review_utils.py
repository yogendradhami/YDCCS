import requests
from django.conf import settings
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .models import GoogleAccount


def get_google_mybusiness_service():
    """Build and return Google My Business API service."""
    google_account = GoogleAccount.objects.first()

    if not google_account:
        return None

    creds = Credentials(
        token=google_account.access_token,
        refresh_token=google_account.refresh_token or None,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleAuthRequest())
        google_account.access_token = creds.token
        google_account.save(update_fields=["access_token"])

    return build("mybusinessaccountmanagement", "v1", credentials=creds)


def _normalize_star_rating(star_rating):
    if isinstance(star_rating, str):
        star_rating = star_rating.upper()
        mapping = {
            "ONE": 1,
            "TWO": 2,
            "THREE": 3,
            "FOUR": 4,
            "FIVE": 5,
        }
        return mapping.get(star_rating, 5)

    try:
        return max(1, min(int(star_rating), 5))
    except (TypeError, ValueError):
        return 5


def get_google_reviews_api():
    """
    Fetch live reviews from Google My Business API.
    Returns list of review dicts with reviewer_name, comment, rating.
    Falls back to empty list if API unavailable.
    """
    try:
        google_account = GoogleAccount.objects.first()
        if not google_account:
            return []

        creds = Credentials(
            token=google_account.access_token,
            refresh_token=google_account.refresh_token or None,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )

        if creds.expired and creds.refresh_token:
            creds.refresh(GoogleAuthRequest())
            google_account.access_token = creds.token
            google_account.save(update_fields=["access_token"])

        access_token = creds.token
        if not access_token:
            return []

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        accounts_response = requests.get(
            "https://mybusinessaccountmanagement.googleapis.com/v1/accounts",
            headers=headers,
            timeout=10,
        )

        if accounts_response.status_code != 200:
            return []

        accounts = accounts_response.json().get("accounts", [])
        if not accounts:
            return []

        account_name = accounts[0].get("name")
        if not account_name:
            return []

        locations_response = requests.get(
            f"https://mybusinessbusinessinformation.googleapis.com/v1/{account_name}/locations",
            headers=headers,
            timeout=10,
        )

        if locations_response.status_code != 200:
            return []

        locations = locations_response.json().get("locations", [])
        if not locations:
            return []

        location_name = locations[0].get("name")
        if not location_name:
            return []

        reviews_response = requests.get(
            f"https://mybusiness.googleapis.com/v4/{location_name}/reviews",
            headers=headers,
            timeout=10,
        )

        if reviews_response.status_code != 200:
            return []

        reviews_data = reviews_response.json().get("reviews", [])

        google_reviews = []
        for review in reviews_data[:6]:
            star_count = _normalize_star_rating(review.get("starRating", 5))
            google_reviews.append(
                {
                    "reviewer_name": review.get("reviewer", {}).get("displayName", "Anonymous"),
                    "comment": review.get("reviewReply", {}).get("comment", review.get("comment", "")),
                    "rating": "⭐" * star_count,
                    "created_at": review.get("createTime", ""),
                }
            )

        return google_reviews

    except Exception as e:
        print(f"Error fetching Google reviews: {e}")
        return []
