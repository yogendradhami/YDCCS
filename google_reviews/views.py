import base64
import hashlib
import secrets
from datetime import datetime, timedelta

import requests
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect, render
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from .models import GoogleAccount, GoogleReview
from .review_utils import get_public_google_reviews
from django.utils.dateparse import parse_datetime
SCOPES = [
    "https://www.googleapis.com/auth/business.manage",
    "https://www.googleapis.com/auth/calendar",
]


def create_code_challenge(code_verifier):
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def get_flow():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    return flow


def google_connect(request):
    flow = get_flow()

    code_verifier = secrets.token_urlsafe(64)
    code_challenge = create_code_challenge(code_verifier)

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )

    request.session["google_oauth_state"] = state
    request.session["google_code_verifier"] = code_verifier
    request.session.save()

    return redirect(authorization_url)


def google_callback(request):

    state = request.session.get("google_oauth_state")
    code_verifier = request.session.get("google_code_verifier")

    if not state or not code_verifier:
        return HttpResponse(
            """
            <h2>OAuth session expired</h2>
            <p>Please start again:</p>
            <a href="/google/connect/">Connect Google</a>
            """
        )

    try:

        flow = get_flow()
        flow.oauth2session.state = state

        flow.fetch_token(
            authorization_response=request.build_absolute_uri(),
            code_verifier=code_verifier,
        )

        credentials = flow.credentials


        # Save Google token in database
        GoogleAccount.objects.all().delete()

        GoogleAccount.objects.create(
            access_token=credentials.token,
            refresh_token=credentials.refresh_token or ""
        )


        return HttpResponse(
            """
            <h2>✅ Google connected successfully</h2>
            <p>Your Google account is connected.</p>
            <a href="/google/reviews/">Check Reviews</a>
            """
        )


    except Exception as e:

        return HttpResponse(
            f"""
            <h2>Google OAuth Error</h2>
            <pre>{e}</pre>
            """
        )

def public_google_reviews(request):
    reviews = get_public_google_reviews(limit=12)
    review_count = len(reviews)
    average_rating = 5.0

    if reviews:
        rating_values = []
        for review in reviews:
            rating_text = review.get("rating", "")
            rating_values.append(len(rating_text.replace("☆", "").replace("★", "")) or 5)
        average_rating = round(sum(rating_values) / len(rating_values), 1) if rating_values else 5.0

    return render(
        request,
        "google_reviews/public_reviews.html",
        {
            "reviews": reviews,
            "review_count": review_count,
            "average_rating": average_rating,
        },
    )


def google_reviews(request):

    google_account = GoogleAccount.objects.first()

    if not google_account:
        return HttpResponse(
            "Google not connected. Open /google/connect/ first."
        )


    headers = {
        "Authorization": f"Bearer {google_account.access_token}",
        "Accept": "application/json",
    }


    account_id = "103743515012926700887"
    location_id = "1982958555522724329"


    url = (
        f"https://mybusiness.googleapis.com/v4/"
        f"accounts/{account_id}/locations/{location_id}/reviews"
    )


    response = requests.get(
        url,
        headers=headers
    )


    if response.status_code != 200:
        return HttpResponse(
            response.text,
            status=response.status_code,
            content_type="application/json"
        )


    return HttpResponse(
        response.text,
        content_type="application/json"
    )

def sync_google_reviews(request):

    google_account = GoogleAccount.objects.first()

    if not google_account:
        return HttpResponse(
            "Google not connected"
        )


    headers = {
        "Authorization": f"Bearer {google_account.access_token}",
        "Accept": "application/json",
    }


    account_id = "103743515012926700887"
    location_id = "1982958555522724329"


    url = (
        f"https://mybusiness.googleapis.com/v4/"
        f"accounts/{account_id}/locations/{location_id}/reviews"
    )


    response = requests.get(
        url,
        headers=headers
    )


    data = response.json()


    for review in data.get("reviews", []):

        reviewer = review.get("reviewer", {})

        review_reply = review.get(
            "reviewReply",
            {}
        )


        GoogleReview.objects.update_or_create(

            review_id=review.get("reviewId"),

            defaults={

                "reviewer_name":
                    reviewer.get(
                        "displayName",
                        ""
                    ),

                "reviewer_photo":
                    reviewer.get(
                        "profilePhotoUrl",
                        ""
                    ),

                "rating":
                    review.get(
                        "starRating",
                        ""
                    ),

                "comment":
                    review.get(
                        "comment",
                        ""
                    ),

                "review_date":
                    parse_datetime(
                        review.get(
                            "createTime"
                        )
                    ),

                "reply":
                    review_reply.get(
                        "comment",
                        ""
                    ),

                "reply_date":
                    parse_datetime(
                        review_reply.get(
                            "updateTime"
                        )
                    ),

                "review_url":
                    review.get(
                        "reviewReplyUrl",
                        ""
                    ),
            }
        )


    return HttpResponse(
        "✅ Google reviews synced successfully"
    )



def get_google_reviews(request):

    google_account = GoogleAccount.objects.first()

    if not google_account:
        return HttpResponse(
            "Google not connected."
        )

    headers = {
        "Authorization": f"Bearer {google_account.access_token}",
        "Accept": "application/json",
    }


    account_id = "103743515012926700887"
    location_id = "1982958555522724329"


    url = (
        f"https://mybusiness.googleapis.com/v4/"
        f"accounts/{account_id}/locations/{location_id}/reviews"
    )


    response = requests.get(
        url,
        headers=headers
    )


    return HttpResponse(
        response.text,
        content_type="application/json"
    )

def test_calendar_event(request):

    google_account = GoogleAccount.objects.first()

    if not google_account:
        return HttpResponse("No Google account connected.")

    creds = Credentials(
        token=google_account.access_token,
        refresh_token=google_account.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )

    service = build("calendar", "v3", credentials=creds)

    start_time = datetime.utcnow() + timedelta(days=1)

    end_time = start_time + timedelta(hours=1)

    event = {
        "summary": "YD Commercial Cleaning Test Event",
        "description": "Calendar integration test.",
        "start": {
            "dateTime": start_time.isoformat() + "Z",
        },
        "end": {
            "dateTime": end_time.isoformat() + "Z",
        },
    }

    created_event = service.events().insert(calendarId="primary", body=event).execute()

    return HttpResponse(f"✅ Event created: {created_event.get('htmlLink')}")
