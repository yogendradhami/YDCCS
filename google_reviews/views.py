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

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

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
            "OAuth session expired. Please open /google/connect/ again."
        )

    flow = get_flow()
    flow.oauth2session.state = state

    flow.fetch_token(
        authorization_response=request.build_absolute_uri(),
        code_verifier=code_verifier,
    )

    credentials = flow.credentials

    request.session["google_access_token"] = credentials.token

    if credentials.refresh_token:
        request.session["google_refresh_token"] = credentials.refresh_token

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
