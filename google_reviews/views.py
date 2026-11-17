import base64
import hashlib
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build


from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from .business_profile import (
    GoogleBusinessProfileError,
    GoogleBusinessProfileService,
    parse_google_datetime as _parse_google_datetime,
)
from .models import GoogleAccount
from .review_utils import (
    get_public_google_reviews,
    get_public_google_review_stats,
)

logger = logging.getLogger(__name__)


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

    operation = "OAuth token exchange"
    try:
        flow = get_flow()
        flow.oauth2session.state = state

        flow.fetch_token(
            authorization_response=request.build_absolute_uri(),
            code_verifier=code_verifier,
        )

        credentials = flow.credentials

        operation = "OAuth account persistence"
        google_account = GoogleAccount.objects.order_by(
            "-updated_at", "-id"
        ).first()
        if google_account is None:
            google_account = GoogleAccount()
        google_account.access_token = credentials.token
        if credentials.refresh_token:
            google_account.refresh_token = credentials.refresh_token
        id_token = credentials.id_token
        if isinstance(id_token, dict):
            google_account.email = id_token.get("email", "")
        google_account.save()

    except Exception:
        logger.exception(
            "Google OAuth callback failed during %s.",
            operation,
            extra={"operation": operation},
        )
        return HttpResponse(
            """
            <h2>Google connection failed</h2>
            <p>Google could not be connected. Please try again.</p>
            """,
            status=500,
        )

    operation = "Google Calendar backfill"
    try:
        from .calendar_utils import sync_existing_bookings_to_company_calendar

        synced_count, failed_count = sync_existing_bookings_to_company_calendar()
    except Exception:
        logger.exception(
            "Google OAuth succeeded, but %s failed.",
            operation,
            extra={"operation": operation},
        )
        return HttpResponse(
            """
            <h2>Google connected successfully</h2>
            <p>Your Google account is connected and the credentials were saved.</p>
            <p>Calendar synchronisation needs attention. Check the application
            logs and retry the calendar sync; you do not need to reconnect Google.</p>
            <a href="/google/reviews/">Check Reviews</a>
            """
        )

    return HttpResponse(
        f"""
        <h2>✅ Google connected successfully</h2>
        <p>Your Google account is connected.</p>
        <p>{synced_count} existing job(s) synced to the company calendar.</p>
        <p>{failed_count} job(s) could not be synced. Check the application logs
        and retry the calendar sync if needed.</p>
        <a href="/google/reviews/">Check Reviews</a>
        """
    )


def public_google_reviews(request):
    reviews = get_public_google_reviews(limit=100)
    stats = get_public_google_review_stats()

    return render(
        request,
        "google_reviews/public_reviews.html",
        {
            "reviews": reviews,
            "review_count": stats["review_count"],
            "average_rating": stats["average_rating"],
            "reviews_last_synced_at": stats["last_synced_at"],
        },
    )


def google_reviews(request):
    try:
        reviews = GoogleBusinessProfileService().get_selected_reviews()
    except GoogleBusinessProfileError as exc:
        return HttpResponse(exc.user_message, status=exc.status_code)
    except Exception:
        logger.exception("Could not retrieve selected Google Business Profile reviews.")
        return HttpResponse(
            "Google Business Profile reviews could not be retrieved.",
            status=500,
        )
    return JsonResponse({"reviews": reviews})


def _sync_google_reviews_response():
    """Run the Google Reviews sync and return its result."""
    try:
        saved, retrieved = GoogleBusinessProfileService().sync_selected_reviews()
    except GoogleBusinessProfileError as exc:
        return HttpResponse(exc.user_message, status=exc.status_code)
    except Exception:
        logger.exception("Could not sync selected Google Business Profile reviews.")
        return HttpResponse(
            "Google Business Profile reviews could not be synced. Check server logs.",
            status=500,
        )

    if retrieved == 0:
        return HttpResponse(
            "Google returned zero reviews for the selected listing. "
            "Existing saved reviews were left unchanged.",
            status=204,
        )

    return HttpResponse(
        f"Google reviews synced successfully. Retrieved {retrieved} review(s) "
        f"and saved {saved}."
    )


@require_POST
@staff_member_required
def sync_google_reviews(request):
    return _sync_google_reviews_response()



def get_google_reviews(request):
    return google_reviews(request)

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

    start_time = timezone.now() + timedelta(days=1)

    end_time = start_time + timedelta(hours=1)

    event = {
        "summary": "YD Commercial Cleaning Test Event",
        "description": "Calendar integration test.",
        "start": {
            "dateTime": start_time.isoformat(),
        },
        "end": {
            "dateTime": end_time.isoformat(),
        },
    }

    created_event = service.events().insert(calendarId="primary", body=event).execute()

    return HttpResponse(f"✅ Event created: {created_event.get('htmlLink')}")
