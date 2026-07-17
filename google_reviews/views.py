<<<<<<< HEAD
import base64
import hashlib
import os
import secrets
from datetime import datetime, timedelta

import requests
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from .models import GoogleAccount
=======
import os
import requests

from django.shortcuts import redirect
from django.http import HttpResponse
from django.conf import settings
from google_auth_oauthlib.flow import Flow
from .models import GoogleAccount
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from .models import GoogleReview
from .models import (
    GoogleReview,
    GoogleReviewStats
)
>>>>>>> 5815f15 (Initial project commit)

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

SCOPES = [
    "https://www.googleapis.com/auth/business.manage",
    "https://www.googleapis.com/auth/calendar",
]


<<<<<<< HEAD
def create_code_challenge(code_verifier):
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


=======
>>>>>>> 5815f15 (Initial project commit)
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
<<<<<<< HEAD
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
=======
        autogenerate_code_verifier=True,
    )

    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI

>>>>>>> 5815f15 (Initial project commit)
    return flow


def google_connect(request):
<<<<<<< HEAD
    flow = get_flow()

    code_verifier = secrets.token_urlsafe(64)
    code_challenge = create_code_challenge(code_verifier)
=======
    """
    Start Google OAuth flow.
    """

    flow = get_flow()
>>>>>>> 5815f15 (Initial project commit)

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
<<<<<<< HEAD
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )

    request.session["google_oauth_state"] = state
    request.session["google_code_verifier"] = code_verifier
=======
    )

    # Save OAuth state
    request.session["google_oauth_state"] = state

    # Save generated PKCE verifier
    request.session["google_code_verifier"] = flow.code_verifier

>>>>>>> 5815f15 (Initial project commit)
    request.session.save()

    return redirect(authorization_url)


def google_callback(request):
<<<<<<< HEAD
    state = request.session.get("google_oauth_state")
    code_verifier = request.session.get("google_code_verifier")

    if not state or not code_verifier:
        return HttpResponse(
            "OAuth session expired. Please open /google/connect/ again."
        )

    flow = get_flow()
    flow.oauth2session.state = state

    flow.fetch_token(
        authorization_response=request.build_absolute_uri(),
        code_verifier=code_verifier,
=======
    """
    Handle Google OAuth callback.
    """

    state = request.session.get("google_oauth_state")

    if not state:
        return HttpResponse(
            "OAuth session expired. Open /google/connect/ again."
        )

    flow = get_flow()
    # Restore PKCE verifier from session
    flow.code_verifier = request.session.get(
        "google_code_verifier"
    )
    flow.oauth2session.state = state

    # Exchange authorization code
    flow.fetch_token(
        authorization_response=request.build_absolute_uri()
>>>>>>> 5815f15 (Initial project commit)
    )

    credentials = flow.credentials

<<<<<<< HEAD
=======
    # Store in session
>>>>>>> 5815f15 (Initial project commit)
    request.session["google_access_token"] = credentials.token

    if credentials.refresh_token:
        request.session["google_refresh_token"] = credentials.refresh_token

<<<<<<< HEAD
    GoogleAccount.objects.all().delete()

    GoogleAccount.objects.create(
        access_token=credentials.token, refresh_token=credentials.refresh_token or ""
    )

    return HttpResponse("✅ Google connected successfully and saved to database.")


def google_reviews(request):
    access_token = request.session.get("google_access_token")

    if not access_token:
        return HttpResponse("Google not connected. Open /google/connect/ first.")

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = requests.get(
        "https://mybusinessaccountmanagement.googleapis.com/v1/accounts",
        headers=headers,
    )

    return HttpResponse(response.text, content_type="application/json")


def test_calendar_event(request):
=======
    # Store in database
    GoogleAccount.objects.all().delete()

    GoogleAccount.objects.create(
        access_token=credentials.token,
        refresh_token=credentials.refresh_token or ""
    )

    return HttpResponse(
        "✅ Google connected successfully and saved to database."
    )



# def google_reviews(request):
# # --------------------------------------------------
# # Load token from database
# # --------------------------------------------------

#     google_account = GoogleAccount.objects.first()

#     if not google_account:
#         return HttpResponse(
#             "No Google account connected."
#         )

#     access_token = google_account.access_token

#     headers = {
#         "Authorization": f"Bearer {access_token}",
#     }

#     response = requests.get(
#         "https://mybusinessaccountmanagement.googleapis.com/v1/accounts",
#         headers=headers,
#     )
#     # Convert account response to JSON
#     data = response.json()

#     print("GOOGLE ACCOUNT DATA =", data)

#     # Get first account name
#     account_name = data["accounts"][0]["name"]

#     print("ACCOUNT NAME =", account_name)

#     # --------------------------------------------------
#     # Fetch Business Locations
#     # --------------------------------------------------

#     # --------------------------------------------------
# # Fetch Business Locations
# # --------------------------------------------------

#     location_response = requests.get(
#         f"https://mybusinessbusinessinformation.googleapis.com/v1/{account_name}/locations",
#         headers=headers,
#         params={
#             "readMask": (
#                 "name,title,storeCode,websiteUri,"
#                 "primaryPhone,metadata"
#             )
#         }
#     )

#     print(
#         "LOCATION STATUS =",
#         location_response.status_code
#     )

#     return HttpResponse(
#         location_response.text,
#         content_type="application/json"
#     )


# =====================================================
# Refresh Google Token Automatically
# =====================================================

def get_valid_google_token():
>>>>>>> 5815f15 (Initial project commit)

    google_account = GoogleAccount.objects.first()

    if not google_account:
<<<<<<< HEAD
        return HttpResponse("No Google account connected.")
=======
        return None
>>>>>>> 5815f15 (Initial project commit)

    creds = Credentials(
        token=google_account.access_token,
        refresh_token=google_account.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )

<<<<<<< HEAD
    service = build("calendar", "v3", credentials=creds)
=======
    if creds.expired and creds.refresh_token:

        creds.refresh(Request())

        google_account.access_token = creds.token
        google_account.save()

    return creds.token

def google_reviews(request):

    google_account = GoogleAccount.objects.first()

    if not google_account:
        return HttpResponse(
            "No Google account connected."
        )

    access_token = get_valid_google_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = requests.get(
        "https://mybusinessaccountmanagement.googleapis.com/v1/accounts",
        headers=headers,
    )

    # Convert Google account response to Python dictionary
    data = response.json()

    print("GOOGLE ACCOUNT DATA =", data)

    import json

    # Get Google account name
    account_name = data["accounts"][0]["name"]

    # Get Business Profile locations
# --------------------------------------------------
# Get Google Reviews
# --------------------------------------------------

    review_response = requests.get(
        "https://mybusiness.googleapis.com/v4/accounts/"
        "103743515012926700887"
        "/locations/1982958555522724329/reviews",
        headers=headers,
    )

    print(
        "REVIEW STATUS =",
        review_response.status_code
    )

    return HttpResponse(
        review_response.text,
        content_type="application/json"
    )



def test_calendar_event(request):

    google_account = GoogleAccount.objects.first()

    if not google_account:
        return HttpResponse(
            "No Google account connected."
        )

    creds = Credentials(
        token=google_account.access_token,
        refresh_token=google_account.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )

    service = build(
        "calendar",
        "v3",
        credentials=creds
    )
>>>>>>> 5815f15 (Initial project commit)

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

<<<<<<< HEAD
    created_event = service.events().insert(calendarId="primary", body=event).execute()

    return HttpResponse(f"✅ Event created: {created_event.get('htmlLink')}")
=======
    created_event = service.events().insert(
        calendarId="primary",
        body=event
    ).execute()

    return HttpResponse(
        f"✅ Event created: {created_event.get('htmlLink')}"
    )


def sync_google_reviews(request):
    """
    Sync Google reviews into database.
    """

    google_account = GoogleAccount.objects.first()

    # Refresh expired Google token automatically
    creds = Credentials(
        token=google_account.access_token,
        refresh_token=google_account.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

        google_account.access_token = creds.token
        google_account.save()

    if not google_account:
        return HttpResponse(
            "No Google account connected."
        )

    headers = {
        "Authorization":
        f"Bearer {get_valid_google_token()}"
    }

    response = requests.get(
        "https://mybusiness.googleapis.com/v4/"
        "accounts/103743515012926700887/"
        "locations/1982958555522724329/reviews",
        headers=headers,
    )

    data = response.json()
    # Debug Google response
   
    GoogleReviewStats.objects.update_or_create(
        id=1,
        defaults={
            "average_rating":
                data.get(
                    "averageRating",
                    0
                ),

            "total_reviews":
                data.get(
                    "totalReviewCount",
                    0
                )
        }
    )

    reviews = data.get("reviews", [])

    count = 0

    for review in reviews:

        GoogleReview.objects.update_or_create(
            review_id=review["reviewId"],
            defaults={
                "reviewer_name":
                    review["reviewer"]["displayName"],

                "reviewer_photo":
                    review["reviewer"].get(
                        "profilePhotoUrl", ""
                    ),

                "rating":
                    5 if review["starRating"] == "FIVE"
                    else 4,

                "comment":
                    review.get("comment", ""),

                "review_date":
                    review["createTime"],
            }
        )

        count += 1

    return HttpResponse(
        f"✅ {count} reviews synced successfully."
    )
>>>>>>> 5815f15 (Initial project commit)
