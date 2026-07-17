import os
import requests

from django.shortcuts import redirect
from django.http import HttpResponse
from django.conf import settings
from google_auth_oauthlib.flow import Flow
from .models import GoogleAccount
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta


os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

SCOPES = [
    "https://www.googleapis.com/auth/business.manage",
    "https://www.googleapis.com/auth/calendar",
]


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
        autogenerate_code_verifier=True,
    )

    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI

    return flow


def google_connect(request):
    """
    Start Google OAuth flow.
    """

    flow = get_flow()

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    # Save OAuth state
    request.session["google_oauth_state"] = state

    # Save generated PKCE verifier
    request.session["google_code_verifier"] = flow.code_verifier

    request.session.save()

    return redirect(authorization_url)


def google_callback(request):
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
    )

    credentials = flow.credentials

    # Store in session
    request.session["google_access_token"] = credentials.token

    if credentials.refresh_token:
        request.session["google_refresh_token"] = credentials.refresh_token

    # Store in database
    GoogleAccount.objects.all().delete()

    GoogleAccount.objects.create(
        access_token=credentials.token,
        refresh_token=credentials.refresh_token or ""
    )

    return HttpResponse(
        "✅ Google connected successfully and saved to database."
    )



def google_reviews(request):
# --------------------------------------------------
# Load token from database
# --------------------------------------------------

    google_account = GoogleAccount.objects.first()

    if not google_account:
        return HttpResponse(
            "No Google account connected."
        )

    access_token = google_account.access_token

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = requests.get(
        "https://mybusinessaccountmanagement.googleapis.com/v1/accounts",
        headers=headers,
    )

    return HttpResponse(response.text, content_type="application/json")

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

    created_event = service.events().insert(
        calendarId="primary",
        body=event
    ).execute()

    return HttpResponse(
        f"✅ Event created: {created_event.get('htmlLink')}"
    )