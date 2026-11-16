import logging
import re
from urllib.parse import urlsplit

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials

from .models import (
    GoogleAccount,
    GoogleBusinessProfileAccount,
    GoogleBusinessProfileLocation,
    GoogleReview,
)


logger = logging.getLogger(__name__)

ACCOUNT_API = "https://mybusinessaccountmanagement.googleapis.com/v1"
LOCATION_API = "https://mybusinessbusinessinformation.googleapis.com/v1"
VERIFICATION_API = "https://mybusinessverifications.googleapis.com/v1"
REVIEWS_API = "https://mybusiness.googleapis.com/v4"
LOCATION_READ_MASK = "name,title,storefrontAddress,metadata"
ACCOUNT_PAGE_SIZE = 20
LOCATION_PAGE_SIZE = 100
REVIEW_PAGE_SIZE = 50
REQUEST_TIMEOUT = 20
ACCOUNT_RESOURCE_RE = re.compile(r"accounts/\d+\Z")
LOCATION_RESOURCE_RE = re.compile(r"locations/\d+\Z")


class GoogleBusinessProfileError(RuntimeError):
    status_code = 502
    category = "business_profile_api"
    user_message = "Google Business Profile could not complete the request."


class GoogleAuthenticationError(GoogleBusinessProfileError):
    status_code = 401
    category = "authentication"
    user_message = (
        "Google authentication failed. Check the saved connection and reconnect "
        "Google only if the credentials have expired or been revoked."
    )


class GooglePermissionError(GoogleBusinessProfileError):
    status_code = 403
    category = "permission"
    user_message = (
        "Google denied access to the Business Profile API. Check the Google "
        "account's Business Profile access and API permissions."
    )


class GoogleBusinessProfileApiDisabled(GoogleBusinessProfileError):
    status_code = 403
    category = "api_disabled"
    user_message = (
        "The Google My Business Verifications API is disabled for this Google "
        "Cloud project. Enable it for the project used by this app, wait for "
        "Google's change to propagate, then check location verification again."
    )


class GoogleAccountNotFound(GoogleBusinessProfileError):
    status_code = 404
    category = "account_not_found"
    user_message = (
        "The selected Google Business Profile account is no longer accessible. "
        "Run the administrator discovery action and select the correct account."
    )


class GoogleLocationNotFound(GoogleBusinessProfileError):
    status_code = 404
    category = "location_not_found"
    user_message = (
        "Google could not find the selected Business Profile account/location "
        "resource. This does not by itself prove the location is unverified. "
        "Refresh profiles and locations, then select the matching YDCCS listing."
    )


class GoogleReviewsResponseIncomplete(GoogleBusinessProfileError):
    status_code = 502
    category = "reviews_response_incomplete"
    user_message = (
        "Google returned no review records or total count. No reviews were "
        "changed. Use “Check selected location verification” in the Business "
        "Profile locations admin to retrieve Google's verification or ownership "
        "state. An empty Reviews API response alone does not prove that the "
        "location is unverified or that API access is missing. Reconnecting Google "
        "will not resolve this response."
    )


class GoogleRateLimitError(GoogleBusinessProfileError):
    status_code = 429
    category = "rate_limit"
    user_message = "Google is rate-limiting Business Profile requests. Retry later."


class GoogleServiceUnavailable(GoogleBusinessProfileError):
    status_code = 503
    category = "google_service"
    user_message = "Google Business Profile is temporarily unavailable. Retry later."


class GoogleNetworkError(GoogleBusinessProfileError):
    status_code = 502
    category = "network"
    user_message = "Could not reach Google Business Profile. Check network access and retry."


class GoogleSelectionRequired(GoogleBusinessProfileError):
    status_code = 400
    category = "selection_required"
    user_message = (
        "No Google Business Profile location is selected. Use the administrator "
        "discovery action, verify the YDCCS listing, and select it."
    )


class GoogleBusinessProfileService:
    def __init__(self, google_account=None):
        self.google_account = google_account or GoogleAccount.objects.order_by(
            "-updated_at", "-id"
        ).first()
        if not self.google_account or not self.google_account.access_token:
            raise GoogleAuthenticationError(
                "No saved Google OAuth account is available."
            )

        self.credentials = Credentials(
            token=self.google_account.access_token,
            refresh_token=self.google_account.refresh_token or None,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )

    def _refresh_credentials(self):
        if not self.credentials.refresh_token:
            raise GoogleAuthenticationError(
                "The saved Google connection has no refresh token."
            )
        try:
            self.credentials.refresh(GoogleAuthRequest())
        except RefreshError as exc:
            logger.exception(
                "Google Business Profile access-token refresh failed."
            )
            raise GoogleAuthenticationError(
                "Google Business Profile authentication needs attention."
            ) from exc

        self.google_account.access_token = self.credentials.token
        fields = ["access_token", "updated_at"]
        if (
            self.credentials.refresh_token
            and self.credentials.refresh_token != self.google_account.refresh_token
        ):
            self.google_account.refresh_token = self.credentials.refresh_token
            fields.append("refresh_token")
        self.google_account.save(update_fields=fields)

    def _get_json(self, url, *, params=None, operation):
        refreshed = False
        endpoint = urlsplit(url).path
        resources = re.findall(r"(?:accounts|locations)/[^/]+", endpoint)
        while True:
            try:
                response = requests.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.credentials.token}",
                        "Accept": "application/json",
                    },
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                )
            except requests.RequestException as exc:
                logger.exception(
                    "Google Business Profile network request failed: "
                    "operation=%s endpoint=%s resources=%s",
                    operation,
                    endpoint,
                    resources,
                )
                raise GoogleNetworkError from exc

            if response.status_code == 401 and not refreshed:
                self._refresh_credentials()
                refreshed = True
                continue
            if response.status_code != 200:
                try:
                    response_payload = response.json()
                except (ValueError, AttributeError):
                    response_payload = {}
                error = (
                    response_payload.get("error", {})
                    if isinstance(response_payload, dict)
                    else {}
                )
                if not isinstance(error, dict):
                    error = {}
                error_details = {
                    key: error.get(key)
                    for key in ("code", "status", "message", "details")
                    if key in error
                }
                logger.error(
                    "Google Business Profile request failed: operation=%s "
                    "endpoint=%s resources=%s http_status=%s google_error=%s",
                    operation,
                    endpoint,
                    resources,
                    response.status_code,
                    error_details,
                    extra={
                        "operation": operation,
                        "google_endpoint": endpoint,
                        "google_resources": resources,
                        "http_status": response.status_code,
                        "google_error": error_details,
                    },
                )
                if response.status_code == 401:
                    raise GoogleAuthenticationError
                if response.status_code == 403:
                    if any(
                        detail.get("reason") == "SERVICE_DISABLED"
                        and (detail.get("metadata") or {}).get("service")
                        == "mybusinessverifications.googleapis.com"
                        for detail in error.get("details", [])
                        if isinstance(detail, dict)
                    ):
                        raise GoogleBusinessProfileApiDisabled
                    raise GooglePermissionError
                if response.status_code == 404:
                    if operation == "account discovery":
                        raise GoogleAccountNotFound
                    if operation.startswith("locations for "):
                        raise GoogleAccountNotFound
                    raise GoogleLocationNotFound
                if response.status_code == 429:
                    raise GoogleRateLimitError
                if response.status_code >= 500:
                    raise GoogleServiceUnavailable
                raise GoogleBusinessProfileError
            try:
                payload = response.json()
            except ValueError as exc:
                logger.exception(
                    "Google Business Profile returned invalid JSON during %s.",
                    operation,
                )
                raise GoogleBusinessProfileError from exc
            if not isinstance(payload, dict):
                logger.error(
                    "Google Business Profile returned an unexpected JSON type "
                    "during %s: endpoint=%s resources=%s type=%s",
                    operation,
                    endpoint,
                    resources,
                    type(payload).__name__,
                )
                raise GoogleBusinessProfileError
            logger.info(
                "Google Business Profile request succeeded: operation=%s "
                "endpoint=%s resources=%s http_status=%s response_fields=%s",
                operation,
                endpoint,
                resources,
                response.status_code,
                sorted(payload),
                extra={
                    "operation": operation,
                    "google_endpoint": endpoint,
                    "google_resources": resources,
                    "http_status": response.status_code,
                    "response_fields": sorted(payload),
                },
            )
            return payload

    def discover_accounts(self):
        accounts = []
        page_token = None
        while True:
            params = {"pageSize": ACCOUNT_PAGE_SIZE}
            if page_token:
                params["pageToken"] = page_token
            payload = self._get_json(
                f"{ACCOUNT_API}/accounts",
                params=params,
                operation="account discovery",
            )
            accounts.extend(payload.get("accounts", []))
            page_token = payload.get("nextPageToken")
            if not page_token:
                return accounts

    def discover_locations(self, account_resource_name):
        if not ACCOUNT_RESOURCE_RE.fullmatch(account_resource_name or ""):
            raise GoogleAccountNotFound

        locations = []
        page_token = None
        while True:
            params = {
                "readMask": LOCATION_READ_MASK,
                "pageSize": LOCATION_PAGE_SIZE,
            }
            if page_token:
                params["pageToken"] = page_token
            payload = self._get_json(
                f"{LOCATION_API}/{account_resource_name}/locations",
                params=params,
                operation=f"locations for {account_resource_name}",
            )
            locations.extend(payload.get("locations", []))
            page_token = payload.get("nextPageToken")
            if not page_token:
                return locations

    def get_location_voice_of_merchant_state(self, location_resource_name):
        if not LOCATION_RESOURCE_RE.fullmatch(location_resource_name or ""):
            raise GoogleLocationNotFound
        return self._get_json(
            f"{VERIFICATION_API}/{location_resource_name}/VoiceOfMerchantState",
            operation=f"verification state for {location_resource_name}",
        )

    @staticmethod
    def _get_selected_location():
        try:
            return (
                GoogleBusinessProfileLocation.objects.select_related("account")
                .get(is_selected=True)
            )
        except GoogleBusinessProfileLocation.DoesNotExist as exc:
            raise GoogleSelectionRequired from exc

    def _verify_selected_location(self):
        selected = self._get_selected_location()
        if not ACCOUNT_RESOURCE_RE.fullmatch(selected.account.resource_name or ""):
            raise GoogleAccountNotFound
        if not LOCATION_RESOURCE_RE.fullmatch(selected.resource_name or ""):
            raise GoogleLocationNotFound

        accounts = self.discover_accounts()
        account = next(
            (
                resource for resource in accounts
                if resource.get("name") == selected.account.resource_name
            ),
            None,
        )
        if account is None:
            raise GoogleAccountNotFound

        locations = self.discover_locations(selected.account.resource_name)
        location = next(
            (
                resource for resource in locations
                if resource.get("name") == selected.resource_name
            ),
            None,
        )
        if location is None:
            raise GoogleLocationNotFound

        return selected

    def get_selected_reviews(self):
        selected = self._verify_selected_location()
        account_id = selected.account.resource_name.split("/", 1)[1]
        location_id = selected.resource_name.split("/", 1)[1]
        url = f"{REVIEWS_API}/accounts/{account_id}/locations/{location_id}/reviews"
        reviews = []
        page_token = None
        page_number = 0
        while True:
            page_number += 1
            params = {
                "pageSize": REVIEW_PAGE_SIZE,
                "orderBy": "updateTime desc",
            }
            if page_token:
                params["pageToken"] = page_token
            payload = self._get_json(
                url,
                params=params,
                operation=f"reviews for {selected.resource_name}",
            )
            page_reviews = payload.get("reviews")
            if page_reviews is None:
                total_review_count = payload.get("totalReviewCount")
                if total_review_count is None:
                    logger.error(
                        "Google Reviews API returned no review fields: "
                        "endpoint=%s account=%s location=%s response_fields=%s",
                        urlsplit(url).path,
                        selected.account.resource_name,
                        selected.resource_name,
                        sorted(payload),
                        extra={
                            "google_endpoint": urlsplit(url).path,
                            "google_resources": [
                                selected.account.resource_name,
                                selected.resource_name,
                            ],
                            "response_fields": sorted(payload),
                        },
                    )
                    raise GoogleReviewsResponseIncomplete
                page_reviews = []
            if not isinstance(page_reviews, list):
                logger.error(
                    "Google Reviews API returned an invalid reviews field for "
                    "endpoint=%s account=%s location=%s",
                    urlsplit(url).path,
                    selected.account.resource_name,
                    selected.resource_name,
                )
                raise GoogleReviewsResponseIncomplete
            logger.info(
                "Google Reviews API page received: endpoint=%s account=%s "
                "location=%s page=%s review_records=%s total_reviews=%s "
                "has_next_page=%s",
                urlsplit(url).path,
                selected.account.resource_name,
                selected.resource_name,
                page_number,
                len(page_reviews),
                payload.get("totalReviewCount"),
                bool(payload.get("nextPageToken")),
                extra={
                    "google_endpoint": urlsplit(url).path,
                    "google_resources": [
                        selected.account.resource_name,
                        selected.resource_name,
                    ],
                    "page": page_number,
                    "review_records": len(page_reviews),
                    "total_reviews": payload.get("totalReviewCount"),
                    "has_next_page": bool(payload.get("nextPageToken")),
                },
            )
            reviews.extend(page_reviews)
            page_token = payload.get("nextPageToken")
            if not page_token:
                return reviews

    def sync_selected_reviews(self):
        reviews = self.get_selected_reviews()
        saved = 0
        for review in reviews:
            review_id = review.get("reviewId")
            if not review_id:
                logger.warning(
                    "Skipping Google review without a review ID."
                )
                continue

            reviewer = review.get("reviewer") or {}
            reply = review.get("reviewReply") or {}
            GoogleReview.objects.update_or_create(
                review_id=review_id,
                defaults={
                    "reviewer_name": reviewer.get("displayName", ""),
                    "reviewer_photo": reviewer.get("profilePhotoUrl") or None,
                    "rating": review.get("starRating", ""),
                    "comment": review.get("comment", ""),
                    "review_date": parse_google_datetime(
                        review.get("createTime")
                    ),
                    "review_updated_at": parse_google_datetime(
                        review.get("updateTime")
                    ),
                    "reply": reply.get("comment", ""),
                    "reply_date": parse_google_datetime(
                        reply.get("updateTime")
                    ),
                    "review_url": review.get("reviewUrl") or None,
                },
            )
            saved += 1
        return saved, len(reviews)


def refresh_discovered_profiles():
    service = GoogleBusinessProfileService()
    accounts = service.discover_accounts()
    discovered_at = timezone.now()
    discovered_resources = []
    for resource in accounts:
        account_resource_name = resource.get("name")
        if not ACCOUNT_RESOURCE_RE.fullmatch(account_resource_name or ""):
            logger.warning(
                "Skipping Google Business Profile account with invalid resource name."
            )
            continue
        discovered_resources.append(
            (
                resource,
                service.discover_locations(account_resource_name),
            )
        )

    with transaction.atomic():
        GoogleBusinessProfileAccount.objects.update(is_available=False)
        GoogleBusinessProfileLocation.objects.update(is_available=False)

        for resource, locations in discovered_resources:
            account_resource_name = resource.get("name")
            account, _ = GoogleBusinessProfileAccount.objects.update_or_create(
                resource_name=account_resource_name,
                defaults={
                    "account_name": resource.get("accountName", ""),
                    "account_type": resource.get("type", ""),
                    "verification_state": resource.get("verificationState", ""),
                    "is_available": True,
                    "last_discovered_at": discovered_at,
                },
            )
            for location_resource in locations:
                location_name = location_resource.get("name")
                if not LOCATION_RESOURCE_RE.fullmatch(location_name or ""):
                    logger.warning(
                        "Skipping Google Business Profile location with invalid resource name."
                    )
                    continue
                metadata = location_resource.get("metadata") or {}
                GoogleBusinessProfileLocation.objects.update_or_create(
                    account=account,
                    resource_name=location_name,
                    defaults={
                        "title": location_resource.get("title", ""),
                        "storefront_address": (
                            location_resource.get("storefrontAddress") or {}
                        ),
                        "has_voice_of_merchant": metadata.get(
                            "hasVoiceOfMerchant"
                        ),
                        "is_available": True,
                        "last_discovered_at": discovered_at,
                    },
                )

    return accounts


def parse_google_datetime(value):
    if not isinstance(value, str):
        return None

    parsed = parse_datetime(value)
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.get_default_timezone())
    return parsed
