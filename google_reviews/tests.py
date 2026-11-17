from datetime import datetime, timedelta, timezone as datetime_timezone

from unittest.mock import MagicMock, patch

from zoneinfo import ZoneInfo



from django.contrib import admin

from django.contrib.auth import get_user_model

from django.contrib.messages.storage.fallback import FallbackStorage

from django.core.cache import cache

from django.test import RequestFactory, TestCase

from django.urls import reverse

from django.utils import timezone

from google.auth.exceptions import RefreshError

from google.oauth2.credentials import Credentials



from bookings.models import Booking

from employees.models import Employee, EmployeeGoogleAccount

from rosters.models import Roster



from .models import GoogleAccount, GoogleReview

from .calendar_utils import (

    _google_credentials_expiry,

    delete_booking_event,

    delete_roster_event,

)

from .business_profile import (

    GoogleAccountNotFound,

    GoogleAuthenticationError,

    GoogleBusinessProfileApiDisabled,

    GoogleBusinessProfileService,

    GoogleLocationNotFound,

    GooglePermissionError,

    GoogleReviewsResponseIncomplete,

    LOCATION_READ_MASK,

    refresh_discovered_profiles,

)

from .admin import (

    GoogleAccountAdmin,

    GoogleBusinessProfileLocationAdmin,

    GoogleReviewAdmin,

)

from .review_utils import get_google_reviews_api, get_public_google_reviews

from googleapiclient.errors import HttpError



from google_reviews.calendar_utils import (

    CalendarNotConfigured,

    CalendarServiceUnavailable,

    create_or_update_booking_event,

    create_or_update_roster_event,

    sync_existing_bookings_to_company_calendar,

)

from google_reviews.views import _parse_google_datetime

from .models import GoogleBusinessProfileAccount, GoogleBusinessProfileLocation





class GoogleReviewsUtilsTests(TestCase):

    def _set_oauth_session(self):

        session = self.client.session

        session["google_oauth_state"] = "oauth-state"

        session["google_code_verifier"] = "oauth-verifier"

        session.save()



    def test_get_public_google_reviews_returns_db_reviews(self):

        GoogleReview.objects.create(

            review_id="review-1",

            reviewer_name="Alicia",

            comment="Excellent service and attention to detail.",

            rating="5",

            review_date=timezone.now(),

        )



        reviews = get_public_google_reviews(limit=3)



        self.assertEqual(len(reviews), 1)

        self.assertEqual(reviews[0]["reviewer_name"], "Alicia")

        self.assertEqual(reviews[0]["comment"], "Excellent service and attention to detail.")

        self.assertEqual(reviews[0]["rating"], "⭐⭐⭐⭐⭐")



    def test_numeric_string_ratings_keep_their_actual_star_count(self):

        GoogleReview.objects.create(

            review_id="review-2",

            reviewer_name="Four-star customer",

            rating="4",

        )

        GoogleReview.objects.create(

            review_id="review-3",

            reviewer_name="Two-star customer",

            rating="2",

        )



        reviews = {

            review["reviewer_name"]: review

            for review in get_public_google_reviews()

        }



        self.assertEqual(reviews["Four-star customer"]["rating"], "⭐⭐⭐⭐")

        self.assertEqual(reviews["Two-star customer"]["rating"], "⭐⭐")



    def test_homepage_uses_selected_google_profile_statistics(self):

        account = GoogleBusinessProfileAccount.objects.create(

            resource_name="accounts/100",

            account_name="YD Commercial Cleaning Services",

        )

        GoogleBusinessProfileLocation.objects.create(

            account=account,

            resource_name="locations/200",

            title="YD Commercial Cleaning Services",

            is_selected=True,

            google_total_review_count=234,

            google_average_rating="4.80",

        )

        GoogleReview.objects.create(

            review_id="homepage-stats-review",

            reviewer_name="Homepage customer",

            rating="1",

        )

        cache.delete("homepage_google_reviews")

        self.addCleanup(cache.delete, "homepage_google_reviews")



        response = self.client.get("/")



        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context["google_review_count"], 234)

        self.assertEqual(response.context["average_rating"], 4.8)

        self.assertContains(response, "Based on 234 reviews")



    def test_google_account_admin_has_oauth_reconnect_action(self):

        user = get_user_model().objects.create_superuser(

            username="google-admin",

            email="google-admin@example.com",

            password="test-password",

        )

        self.client.force_login(user)



        response = self.client.get(

            reverse("admin:google_reviews_googleaccount_changelist")

        )



        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "Reconnect Google account")

        self.assertContains(response, 'href="/google/connect/"')

        self.assertContains(response, "Add Google Account")



    def test_google_account_admin_connect_starts_existing_oauth_flow(self):

        user = get_user_model().objects.create_superuser(

            username="google-admin",

            email="google-admin@example.com",

            password="test-password",

        )

        self.client.force_login(user)

        flow = MagicMock()

        flow.authorization_url.return_value = (

            "https://accounts.google.com/oauth",

            "oauth-state",

        )



        with patch("google_reviews.views.get_flow", return_value=flow):

            response = self.client.get("/google/connect/")



        self.assertRedirects(

            response,

            "https://accounts.google.com/oauth",

            fetch_redirect_response=False,

        )

        session = self.client.session

        self.assertEqual(session["google_oauth_state"], "oauth-state")

        self.assertTrue(session.get("google_code_verifier"))

        flow.authorization_url.assert_called_once()



    def test_existing_oauth_start_remains_available_without_admin_login(self):

        flow = MagicMock()

        flow.authorization_url.return_value = (

            "https://accounts.google.com/oauth",

            "oauth-state",

        )

        with patch("google_reviews.views.get_flow", return_value=flow):

            response = self.client.get("/google/connect/")



        self.assertEqual(response.status_code, 302)

        self.assertEqual(response["Location"], "https://accounts.google.com/oauth")

        self.assertEqual(GoogleAccount.objects.count(), 0)



    def test_company_google_callback_backfills_bookings_and_keeps_refresh_token(self):

        account = GoogleAccount.objects.create(

            access_token="old-access-token",

            refresh_token="existing-refresh-token",

        )

        flow = MagicMock()

        flow.credentials.token = "new-access-token"

        flow.credentials.refresh_token = None

        flow.credentials.id_token = {"email": "company@example.com"}



        self._set_oauth_session()



        with (

            patch("google_reviews.views.get_flow", return_value=flow),

            patch(

                "google_reviews.calendar_utils.sync_existing_bookings_to_company_calendar",

                return_value=(3, 1),

            ) as sync_bookings,

        ):

            response = self.client.get("/google/oauth/callback/")



        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "3 existing job(s) synced")

        self.assertContains(response, "1 job(s) could not be synced")

        sync_bookings.assert_called_once_with()

        account.refresh_from_db()

        self.assertEqual(account.access_token, "new-access-token")

        self.assertEqual(account.refresh_token, "existing-refresh-token")

        self.assertEqual(account.email, "company@example.com")

        self.assertEqual(

            flow.fetch_token.call_args.kwargs["code_verifier"],

            "oauth-verifier",

        )



    def test_company_google_callback_saves_new_refresh_token_without_duplicate(self):

        account = GoogleAccount.objects.create(

            access_token="old-access-token",

            refresh_token="old-refresh-token",

        )

        flow = MagicMock()

        flow.credentials.token = "new-access-token"

        flow.credentials.refresh_token = "new-refresh-token"

        flow.credentials.id_token = {"email": "company@example.com"}

        self._set_oauth_session()



        with (

            patch("google_reviews.views.get_flow", return_value=flow),

            patch(

                "google_reviews.calendar_utils.sync_existing_bookings_to_company_calendar",

                return_value=(0, 0),

            ),

        ):

            response = self.client.get("/google/oauth/callback/")



        self.assertEqual(response.status_code, 200)

        account.refresh_from_db()

        self.assertEqual(account.access_token, "new-access-token")

        self.assertEqual(account.refresh_token, "new-refresh-token")

        self.assertEqual(GoogleAccount.objects.count(), 1)



    def test_calendar_backfill_failure_does_not_fail_oauth_or_discard_tokens(self):

        flow = MagicMock()

        flow.credentials.token = "saved-access-token"

        flow.credentials.refresh_token = "saved-refresh-token"

        flow.credentials.id_token = {"email": "company@example.com"}

        self._set_oauth_session()



        with (

            patch("google_reviews.views.get_flow", return_value=flow),

            patch(

                "google_reviews.calendar_utils.sync_existing_bookings_to_company_calendar",

                side_effect=RuntimeError("sensitive-refresh-token-value"),

            ),

            self.assertLogs("google_reviews.views", level="ERROR") as log_output,

        ):

            response = self.client.get("/google/oauth/callback/")



        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "Google connected successfully")

        self.assertContains(response, "Calendar synchronisation needs attention")

        self.assertContains(response, "do not need to reconnect Google")

        self.assertNotContains(response, "sensitive-refresh-token-value")

        self.assertIn("Google Calendar backfill", log_output.output[0])



        account = GoogleAccount.objects.get()

        self.assertEqual(account.access_token, "saved-access-token")

        self.assertEqual(account.refresh_token, "saved-refresh-token")





class GoogleDatetimeNormalizationTests(TestCase):

    def test_naive_google_credential_timestamp_normalizes_to_naive_utc(self):

        updated_at = timezone.make_naive(

            timezone.now(),

            timezone.get_default_timezone(),

        )

        expiry = _google_credentials_expiry(updated_at)

        expected = (

            timezone.make_aware(updated_at, timezone.get_default_timezone())

            .astimezone(datetime_timezone.utc)

            .replace(tzinfo=None)

            + timedelta(minutes=55)

        )



        self.assertEqual(expiry, expected)

        self.assertTrue(timezone.is_naive(expiry))

        self.assertFalse(Credentials(token="test", expiry=expiry).expired)



    def test_aware_google_credential_timestamp_preserves_its_instant(self):

        updated_at = timezone.now().astimezone(

            ZoneInfo("Australia/Adelaide")

        )

        expiry = _google_credentials_expiry(updated_at)

        expected = (

            updated_at.astimezone(datetime_timezone.utc)

            .replace(tzinfo=None)

            + timedelta(minutes=55)

        )



        self.assertEqual(expiry, expected)

        self.assertTrue(timezone.is_naive(expiry))

        self.assertFalse(Credentials(token="test", expiry=expiry).expired)



    def test_naive_google_api_timestamp_is_assumed_in_configured_timezone(self):

        parsed = _parse_google_datetime("2026-06-01T12:00:00")



        self.assertTrue(timezone.is_aware(parsed))

        self.assertEqual(

            parsed,

            timezone.make_aware(

                datetime(2026, 6, 1, 12, 0),

                timezone.get_default_timezone(),

            ),

        )



    def test_aware_google_api_timestamp_preserves_its_offset(self):

        parsed = _parse_google_datetime("2026-06-01T12:00:00+09:00")



        self.assertTrue(timezone.is_aware(parsed))

        self.assertEqual(parsed.utcoffset(), timedelta(hours=9))





class GoogleBusinessProfileServiceTests(TestCase):

    def setUp(self):

        self.google_account = GoogleAccount.objects.create(

            access_token="stored-access-token",

            refresh_token="stored-refresh-token",

        )

        self.profile_account = GoogleBusinessProfileAccount.objects.create(

            resource_name="accounts/100",

            account_name="YD Commercial Cleaning Services",

            account_type="PERSONAL",

            verification_state="VERIFIED",

        )

        self.location = GoogleBusinessProfileLocation.objects.create(

            account=self.profile_account,

            resource_name="locations/200",

            title="YD Commercial Cleaning Services",

            is_selected=True,

        )



    def test_profile_admin_pages_expose_discovery_and_selection_instructions(self):

        user_model = get_user_model()

        user = user_model.objects.create_superuser(

            username="profile-admin",

            email="profile-admin@example.com",

            password="test-password",

        )

        self.client.force_login(user)



        account_response = self.client.get(

            reverse("admin:google_reviews_googlebusinessprofileaccount_changelist")

        )

        location_response = self.client.get(

            reverse("admin:google_reviews_googlebusinessprofilelocation_changelist")

        )



        self.assertEqual(account_response.status_code, 200)

        self.assertContains(account_response, "Discover Google Business Profiles")

        self.assertEqual(location_response.status_code, 200)

        self.assertContains(

            location_response,

            "Select as Google Reviews location",

        )

        self.assertContains(

            location_response,

            "Check selected location verification",

        )

        self.assertContains(

            location_response,

            "Refresh available profiles and locations",

        )



    def test_admin_verification_check_reports_verified_and_unverified_states(self):

        user = get_user_model().objects.create_superuser(

            username="verification-admin",

            email="verification-admin@example.com",

            password="test-password",

        )

        model_admin = GoogleBusinessProfileLocationAdmin(

            GoogleBusinessProfileLocation,

            admin.site,

        )



        for state, expected_level, expected_message in (

            (

                {

                    "hasVoiceOfMerchant": True,

                    "hasBusinessAuthority": True,

                },

                "success",

                "has Voice of Merchant and is in good standing",

            ),

            (

                {

                    "hasVoiceOfMerchant": False,

                    "hasBusinessAuthority": True,

                    "verify": {"hasPendingVerification": False},

                },

                "error",

                "requires verification",

            ),

            (

                {

                    "hasVoiceOfMerchant": False,

                    "hasBusinessAuthority": False,

                    "resolveOwnershipConflict": {},

                },

                "error",

                "explicitly reports resolveOwnershipConflict",

            ),

        ):

            request = RequestFactory().get(

                "/admin/google_reviews/googlebusinessprofilelocation/"

                "check-selected-verification/"

            )

            request.user = user

            request.session = self.client.session

            request._messages = FallbackStorage(request)

            with self.subTest(state=state), patch(

                "google_reviews.business_profile.GoogleBusinessProfileService."

                "get_location_voice_of_merchant_state",

                return_value=state,

            ):

                response = model_admin.check_selected_verification(request)



            self.assertEqual(response.status_code, 302)

            message = list(request._messages)[0]

            self.assertEqual(message.level_tag, expected_level)

            self.assertIn(expected_message, str(message))

            self.location.refresh_from_db()

            self.assertIs(

                self.location.has_voice_of_merchant,

                state["hasVoiceOfMerchant"],

            )

            self.assertTrue(self.location.is_selected)



    def test_verification_permission_failure_is_not_reported_as_ownership_conflict(self):

        user = get_user_model().objects.create_superuser(

            username="permission-admin",

            email="permission-admin@example.com",

            password="test-password",

        )

        request = RequestFactory().get(

            "/admin/google_reviews/googlebusinessprofilelocation/"

            "check-selected-verification/"

        )

        request.user = user

        request.session = self.client.session

        setattr(request, "_messages", FallbackStorage(request))

        model_admin = GoogleBusinessProfileLocationAdmin(

            GoogleBusinessProfileLocation,

            admin.site,

        )



        with patch(

            "google_reviews.business_profile.GoogleBusinessProfileService."

            "get_location_voice_of_merchant_state",

            side_effect=GooglePermissionError(),

        ):

            model_admin.check_selected_verification(request)



        message = list(request._messages)[0]

        self.assertIn("Google denied access", str(message))

        self.assertNotIn("ownership conflict", str(message).lower())



    @staticmethod

    def response(payload=None, status=200):

        result = MagicMock(status_code=status)

        result.json.return_value = payload or {}

        return result



    def discovery_responses(self, locations=None, reviews=None):

        return [

            self.response({"accounts": [{"name": "accounts/100"}]}),

            self.response({"locations": locations or []}),

            self.response(

                {"reviews": []} if reviews is None else reviews

            ),

        ]



    def test_successful_account_discovery(self):

        with patch(

            "google_reviews.business_profile.requests.get",

            return_value=self.response(

                {"accounts": [{"name": "accounts/100", "accountName": "YDCCS"}]}

            ),

        ):

            accounts = GoogleBusinessProfileService().discover_accounts()



        self.assertEqual(accounts[0]["name"], "accounts/100")

        self.assertEqual(accounts[0]["accountName"], "YDCCS")



    def test_multiple_accessible_accounts_are_all_returned(self):

        with patch(

            "google_reviews.business_profile.requests.get",

            return_value=self.response(

                {"accounts": [

                    {"name": "accounts/100"},

                    {"name": "accounts/101"},

                ]}

            ),

        ):

            accounts = GoogleBusinessProfileService().discover_accounts()



        self.assertEqual(

            [item["name"] for item in accounts],

            ["accounts/100", "accounts/101"],

        )



    def test_multiple_locations_and_location_pagination_are_returned(self):

        responses = [

            self.response({

                "locations": [{"name": "locations/200"}],

                "nextPageToken": "next-location-page",

            }),

            self.response({"locations": [{"name": "locations/201"}]}),

        ]

        with patch(

            "google_reviews.business_profile.requests.get",

            side_effect=responses,

        ) as api_get:

            locations = GoogleBusinessProfileService().discover_locations(

                "accounts/100"

            )



        self.assertEqual(

            [item["name"] for item in locations],

            ["locations/200", "locations/201"],

        )

        self.assertEqual(

            api_get.call_args_list[0].args[0],

            "https://mybusinessbusinessinformation.googleapis.com/v1/"

            "accounts/100/locations",

        )

        self.assertEqual(

            api_get.call_args_list[0].kwargs["params"]["readMask"],

            LOCATION_READ_MASK,

        )

        self.assertEqual(

            api_get.call_args_list[1].kwargs["params"]["readMask"],

            LOCATION_READ_MASK,

        )

        self.assertEqual(

            api_get.call_args_list[1].kwargs["params"]["pageToken"],

            "next-location-page",

        )



    def test_correct_ydccs_location_is_selected_not_first_discovered(self):

        GoogleBusinessProfileLocation.objects.create(

            account=self.profile_account,

            resource_name="locations/199",

            title="Different Business",

        )

        responses = self.discovery_responses(

            locations=[

                {"name": "locations/199", "title": "Different Business"},

                {

                    "name": "locations/200",

                    "title": "YD Commercial Cleaning Services",

                    "metadata": {"hasVoiceOfMerchant": True},

                },

            ],

            reviews={"reviews": []},

        )

        with patch(

            "google_reviews.business_profile.requests.get",

            side_effect=responses,

        ) as api_get:

            self.assertEqual(

                GoogleBusinessProfileService().get_selected_reviews(), []

            )



        review_request = api_get.call_args_list[-1]

        self.assertEqual(

            review_request.args[0],

            "https://mybusiness.googleapis.com/v4/"

            "accounts/100/locations/200/reviews",

        )

        self.assertEqual(

            review_request.kwargs["params"]["orderBy"],

            "updateTime desc",

        )



    def test_admin_can_select_verified_ydccs_location(self):

        self.location.is_selected = False

        self.location.has_voice_of_merchant = True

        self.location.save(update_fields=["is_selected", "has_voice_of_merchant"])

        other_location = GoogleBusinessProfileLocation.objects.create(

            account=self.profile_account,

            resource_name="locations/199",

            title="Different Business",

            is_selected=True,

        )

        model_admin = GoogleBusinessProfileLocationAdmin(

            GoogleBusinessProfileLocation,

            admin.site,

        )



        with patch.object(model_admin, "message_user"):

            model_admin.select_as_reviews_location(

                MagicMock(),

                GoogleBusinessProfileLocation.objects.filter(

                    pk=self.location.pk

                ),

            )



        self.location.refresh_from_db()

        other_location.refresh_from_db()

        self.assertTrue(self.location.is_selected)

        self.assertFalse(other_location.is_selected)



    def test_profile_discovery_persists_all_candidates_without_selecting_one(self):

        accounts = [

            {

                "name": "accounts/100",

                "accountName": "YDCCS",

                "type": "PERSONAL",

                "verificationState": "UNVERIFIED",

            },

            {

                "name": "accounts/101",

                "accountName": "Other account",

                "type": "BUSINESS",

            },

        ]

        locations_by_account = {

            "accounts/100": [

                {

                    "name": "locations/200",

                    "title": "YD Commercial Cleaning Services",

                    "storefrontAddress": {"locality": "Prospect"},

                    "metadata": {},

                }

            ],

            "accounts/101": [

                {

                    "name": "locations/201",

                    "title": "Other Business",

                    "metadata": {"hasVoiceOfMerchant": True},

                }

            ],

        }

        with (

            patch(

                "google_reviews.business_profile.GoogleBusinessProfileService.discover_accounts",

                return_value=accounts,

            ),

            patch(

                "google_reviews.business_profile.GoogleBusinessProfileService.discover_locations",

                side_effect=lambda account_name: locations_by_account[account_name],

            ),

        ):

            refresh_discovered_profiles()



        self.assertEqual(GoogleBusinessProfileAccount.objects.count(), 2)

        self.assertEqual(GoogleBusinessProfileLocation.objects.count(), 2)

        self.assertEqual(

            GoogleBusinessProfileLocation.objects.filter(is_selected=True).count(),

            1,

        )

        self.assertEqual(

            GoogleBusinessProfileLocation.objects.get(

                resource_name="locations/201"

            ).has_voice_of_merchant,

            True,

        )



    def test_profile_discovery_persists_unverified_voice_of_merchant_state(self):

        accounts = [{"name": "accounts/100", "accountName": "YDCCS"}]

        with (

            patch(

                "google_reviews.business_profile.GoogleBusinessProfileService.discover_accounts",

                return_value=accounts,

            ),

            patch(

                "google_reviews.business_profile.GoogleBusinessProfileService.discover_locations",

                return_value=[

                    {

                        "name": "locations/200",

                        "title": "YD Commercial Cleaning Services",

                        "metadata": {"hasVoiceOfMerchant": False},

                    }

                ],

            ),

        ):

            refresh_discovered_profiles()



        self.location.refresh_from_db()

        self.assertIs(self.location.has_voice_of_merchant, False)



    def test_missing_account_is_reported(self):

        with patch(

            "google_reviews.business_profile.requests.get",

            return_value=self.response({"accounts": []}),

        ), self.assertRaises(GoogleAccountNotFound):

            GoogleBusinessProfileService().get_selected_reviews()



    def test_missing_location_is_reported(self):

        responses = [

            self.response({"accounts": [{"name": "accounts/100"}]}),

            self.response({"locations": [{"name": "locations/201"}]}),

        ]

        with patch(

            "google_reviews.business_profile.requests.get",

            side_effect=responses,

        ), self.assertRaises(GoogleLocationNotFound):

            GoogleBusinessProfileService().get_selected_reviews()



    def test_reviews_404_does_not_assume_location_is_unverified(self):

        responses = [

            self.response({"accounts": [{"name": "accounts/100"}]}),

            self.response({

                "locations": [{

                    "name": "locations/200",

                    "metadata": {"hasVoiceOfMerchant": False},

                }]

            }),

            self.response(

                {"error": {"status": "NOT_FOUND"}},

                status=404,

            ),

        ]

        with patch(

            "google_reviews.business_profile.requests.get",

            side_effect=responses,

        ), self.assertRaises(GoogleLocationNotFound) as raised:

            GoogleBusinessProfileService().get_selected_reviews()

        self.assertIn("does not by itself prove", raised.exception.user_message)



    def test_get_location_voice_of_merchant_state_uses_verifications_api(self):

        state = {"hasVoiceOfMerchant": True, "hasBusinessAuthority": True}

        with patch(

            "google_reviews.business_profile.requests.get",

            return_value=self.response(state),

        ) as api_get:

            result = GoogleBusinessProfileService().get_location_voice_of_merchant_state(

                "locations/200"

            )



        self.assertEqual(result, state)

        self.assertEqual(

            api_get.call_args.args[0],

            "https://mybusinessverifications.googleapis.com/v1/"

            "locations/200/VoiceOfMerchantState",

        )



    def test_disabled_verifications_api_has_specific_admin_diagnostic(self):

        response = self.response(

            {

                "error": {

                    "status": "PERMISSION_DENIED",

                    "details": [{

                        "reason": "SERVICE_DISABLED",

                        "metadata": {

                            "service": "mybusinessverifications.googleapis.com",

                        },

                    }],

                }

            },

            status=403,

        )

        with patch(

            "google_reviews.business_profile.requests.get",

            return_value=response,

        ), self.assertRaises(GoogleBusinessProfileApiDisabled):

            GoogleBusinessProfileService().get_location_voice_of_merchant_state(

                "locations/200"

            )



    def test_incorrect_stored_account_resource_is_rejected(self):

        self.profile_account.resource_name = "accounts/not-an-id"

        self.profile_account.save(update_fields=["resource_name"])



        with patch("google_reviews.business_profile.requests.get") as api_get:

            with self.assertRaises(GoogleAccountNotFound):

                GoogleBusinessProfileService().get_selected_reviews()

        api_get.assert_not_called()



    def test_incorrect_stored_location_resource_is_rejected(self):

        self.location.resource_name = "locations/not-an-id"

        self.location.save(update_fields=["resource_name"])



        with patch("google_reviews.business_profile.requests.get") as api_get:

            with self.assertRaises(GoogleLocationNotFound):

                GoogleBusinessProfileService().get_selected_reviews()

        api_get.assert_not_called()



    def test_location_discovery_always_sends_read_mask(self):

        with patch(

            "google_reviews.business_profile.requests.get",

            return_value=self.response({"locations": []}),

        ) as api_get:

            GoogleBusinessProfileService().discover_locations("accounts/100")



        self.assertEqual(

            api_get.call_args.kwargs["params"]["readMask"],

            "name,title,storefrontAddress,metadata",

        )



    def test_successful_review_retrieval_uses_original_review_fields(self):

        review = {

            "reviewId": "review-1",

            "comment": "Customer comment",

            "reviewReply": {"comment": "Business reply"},

        }

        with patch(

            "google_reviews.business_profile.requests.get",

            side_effect=self.discovery_responses(

                locations=[{"name": "locations/200"}],

                reviews={"reviews": [review]},

            ),

        ):

            result = GoogleBusinessProfileService().get_selected_reviews()



        self.assertEqual(result, [review])



    def test_empty_reviews_object_is_not_reported_as_success_or_delete_saved_reviews(self):

        existing = GoogleReview.objects.create(

            review_id="existing-review",

            reviewer_name="Existing reviewer",

            comment="Existing review",

        )

        responses = self.discovery_responses(

            locations=[{"name": "locations/200"}],

            reviews={},

        )

        with (

            patch(

                "google_reviews.business_profile.requests.get",

                side_effect=responses,

            ),

            self.assertLogs(

                "google_reviews.business_profile",

                level="ERROR",

            ) as log_output,

            self.assertRaises(GoogleReviewsResponseIncomplete),

        ):

            GoogleBusinessProfileService().sync_selected_reviews()



        self.assertIn(

            "/accounts/100/locations/200/reviews",

            log_output.output[0],

        )

        self.assertIn("response_fields=[]", log_output.output[0])

        self.assertEqual(GoogleReview.objects.count(), 1)

        existing.refresh_from_db()

        self.assertEqual(existing.comment, "Existing review")



    def test_incomplete_reviews_response_gives_actionable_admin_diagnostic(self):

        error = GoogleReviewsResponseIncomplete()



        self.assertIn("Check selected location verification", error.user_message)

        self.assertIn("does not prove that the location is unverified", error.user_message)

        self.assertIn("API access is missing", error.user_message)

        self.assertIn("Reconnecting Google will not resolve", error.user_message)



    def test_explicit_zero_review_response_is_a_valid_empty_result(self):

        responses = self.discovery_responses(

            locations=[{"name": "locations/200"}],

            reviews={"reviews": [], "totalReviewCount": 0},

        )

        with patch(

            "google_reviews.business_profile.requests.get",

            side_effect=responses,

        ):

            result = GoogleBusinessProfileService().get_selected_reviews()



        self.assertEqual(result, [])







    def test_empty_sync_result_is_staff_only_post_and_preserves_existing_reviews(self):

        existing = GoogleReview.objects.create(

            review_id="existing-review",

            reviewer_name="Existing reviewer",

            comment="Existing review",

        )



        user = get_user_model().objects.create_superuser(

            username="review-admin",

            email="review-admin@example.com",

            password="test-password",

        )



        with patch(

            "google_reviews.business_profile.GoogleBusinessProfileService.sync_selected_reviews",

            return_value=(0, 0),

        ) as sync_mock:

            # GET must not trigger a sync.

            response = self.client.get("/google/sync-reviews/")

            self.assertEqual(response.status_code, 405)

            sync_mock.assert_not_called()



            # Anonymous POST must not trigger a sync.

            response = self.client.post("/google/sync-reviews/")

            self.assertEqual(response.status_code, 302)

            sync_mock.assert_not_called()



            # Authenticated staff POST may trigger a sync.

            self.client.force_login(user)

            response = self.client.post("/google/sync-reviews/")



        self.assertEqual(response.status_code, 204)

        self.assertEqual(response.content, b"")

        sync_mock.assert_called_once()



        existing.refresh_from_db()

        self.assertEqual(existing.comment, "Existing review")



        # Verify the admin action preserves its warning message.

        request = RequestFactory().post(

            "/admin/google_reviews/googlereview/sync/"

        )

        request.user = user

        request.session = self.client.session

        message_storage = FallbackStorage(request)

        setattr(request, "_messages", message_storage)



        with patch(

            "google_reviews.business_profile.GoogleBusinessProfileService.sync_selected_reviews",

            return_value=(0, 0),

        ):

            admin_response = GoogleReviewAdmin(

                GoogleReview, admin.site

            ).sync_reviews(request)



        self.assertEqual(admin_response.status_code, 302)

        warning = list(message_storage)[0]

        self.assertEqual(warning.level_tag, "warning")

        self.assertEqual(

            str(warning),

            "Google returned zero reviews for the selected listing. "

            "Existing saved reviews were left unchanged.",

        )







    def test_review_pagination_follows_every_next_page_token(self):

        responses = self.discovery_responses(

            locations=[{"name": "locations/200"}],

            reviews={"reviews": [{"reviewId": "first"}], "nextPageToken": "page-2"},

        )

        responses.append(self.response({"reviews": [{"reviewId": "second"}]}))

        with patch(

            "google_reviews.business_profile.requests.get",

            side_effect=responses,

        ) as api_get:

            result = GoogleBusinessProfileService().get_selected_reviews()



        self.assertEqual([item["reviewId"] for item in result], ["first", "second"])

        review_calls = api_get.call_args_list[-2:]

        for call in review_calls:

            self.assertEqual(call.kwargs["params"]["pageSize"], 50)

            self.assertEqual(call.kwargs["params"]["orderBy"], "updateTime desc")

        self.assertEqual(review_calls[1].kwargs["params"]["pageToken"], "page-2")



    def test_successful_paginated_review_sync_saves_every_returned_review(self):

        first_review = {

            "reviewId": "first",

            "reviewer": {"displayName": "First"},

            "comment": "First customer review",

            "starRating": "FIVE",

            "createTime": "2026-11-01T10:00:00Z",

        }

        second_review = {

            "reviewId": "second",

            "reviewer": {"displayName": "Second"},

            "comment": "Second customer review",

            "starRating": "FOUR",

            "createTime": "2026-11-02T10:00:00Z",

        }

        responses = self.discovery_responses(

            locations=[{"name": "locations/200"}],

            reviews={

                "reviews": [first_review],

                "totalReviewCount": 2,

                "averageRating": 4.5,

                "nextPageToken": "page-2",

            },

        )

        responses.append(

            self.response({

                "reviews": [second_review],

                "totalReviewCount": 2,

                "averageRating": 4.5,

            })

        )



        with patch(

            "google_reviews.business_profile.requests.get",

            side_effect=responses,

        ) as api_get:

            saved, retrieved = GoogleBusinessProfileService().sync_selected_reviews()



        self.assertEqual((saved, retrieved), (2, 2))

        self.assertEqual(GoogleReview.objects.count(), 2)

        self.assertEqual(

            set(GoogleReview.objects.values_list("review_id", flat=True)),

            {"first", "second"},

        )

        selected_location = GoogleBusinessProfileLocation.objects.get(

            is_selected=True

        )

        self.assertEqual(selected_location.google_total_review_count, 2)

        self.assertEqual(selected_location.google_average_rating, 4.5)

        self.assertEqual(api_get.call_args_list[-1].kwargs["params"]["pageToken"], "page-2")



    def test_reviews_404_is_reported_as_missing_resource_not_unverified(self):

        response = self.response(

            {

                "error": {

                    "code": 404,

                    "status": "NOT_FOUND",

                    "message": "Requested entity was not found.",

                }

            },

            status=404,

        )

        with patch(

            "google_reviews.business_profile.requests.get",

            return_value=response,

        ), self.assertLogs("google_reviews.business_profile", level="ERROR") as log_output, self.assertRaises(

            GoogleLocationNotFound

        ) as raised:

            GoogleBusinessProfileService()._get_json(

                "https://mybusiness.googleapis.com/v4/"

                "accounts/100/locations/200/reviews",

                operation="reviews for locations/200",

            )

        self.assertIn("does not by itself prove", raised.exception.user_message)

        self.assertIn("http_status=404", log_output.output[0])

        self.assertIn("Requested entity was not found", log_output.output[0])

        self.assertIn("/accounts/100/locations/200/reviews", log_output.output[0])

        self.assertNotIn("stored-access-token", log_output.output[0])



    def test_403_is_reported_as_permission_denied(self):

        with patch(

            "google_reviews.business_profile.requests.get",

            return_value=self.response(

                {"error": {"status": "PERMISSION_DENIED"}},

                status=403,

            ),

        ), self.assertRaises(GooglePermissionError):

            GoogleBusinessProfileService()._get_json(

                "https://example.test/reviews",

                operation="reviews for locations/200",

            )



    @patch("google_reviews.business_profile.GoogleAuthRequest")

    @patch("google_reviews.business_profile.Credentials")

    def test_401_refreshes_and_persists_access_and_replacement_refresh_tokens(

        self,

        credentials_factory,

        google_request,

    ):

        credentials = credentials_factory.return_value

        credentials.token = "rotated-access-token"

        credentials.refresh_token = "rotated-refresh-token"

        responses = [

            self.response(status=401),

            self.response({"accounts": [{"name": "accounts/100"}]}),

        ]

        with patch(

            "google_reviews.business_profile.requests.get",

            side_effect=responses,

        ) as api_get:

            result = GoogleBusinessProfileService().discover_accounts()



        self.assertEqual(result[0]["name"], "accounts/100")

        credentials.refresh.assert_called_once_with(google_request.return_value)

        self.assertEqual(

            api_get.call_args_list[1].kwargs["headers"]["Authorization"],

            "Bearer rotated-access-token",

        )

        self.google_account.refresh_from_db()

        self.assertEqual(self.google_account.access_token, "rotated-access-token")

        self.assertEqual(self.google_account.refresh_token, "rotated-refresh-token")



    def test_duplicate_reviews_are_not_created_and_business_reply_is_separate(self):

        item = {

            "reviewId": "review-duplicate",

            "reviewer": {"displayName": "Sam", "profilePhotoUrl": "https://example.test/sam.jpg"},

            "starRating": "FIVE",

            "comment": "Original customer comment",

            "createTime": "2026-01-01T10:00:00Z",

            "updateTime": "2026-01-02T10:00:00Z",

            "reviewReply": {

                "comment": "Business response",

                "updateTime": "2026-01-03T10:00:00Z",

            },

            "reviewUrl": "https://example.test/review",

        }

        responses = self.discovery_responses(

            locations=[{"name": "locations/200"}],

            reviews={"reviews": [item], "nextPageToken": "page-2"},

        )

        responses.append(self.response({"reviews": [item]}))

        with patch(

            "google_reviews.business_profile.requests.get",

            side_effect=responses,

        ):

            saved, retrieved = GoogleBusinessProfileService().sync_selected_reviews()



        self.assertEqual((saved, retrieved), (2, 2))

        self.assertEqual(GoogleReview.objects.count(), 1)

        review = GoogleReview.objects.get(review_id="review-duplicate")

        self.assertEqual(review.comment, "Original customer comment")

        self.assertEqual(review.reply, "Business response")

        self.assertEqual(review.reviewer_name, "Sam")

        self.assertEqual(review.review_url, "https://example.test/review")

        self.assertTrue(timezone.is_aware(review.review_updated_at))

        self.assertTrue(timezone.is_aware(review.reply_date))



    def test_existing_review_is_updated(self):

        existing = GoogleReview.objects.create(

            review_id="review-update",

            reviewer_name="Old name",

            comment="Old comment",

        )

        updated = {

            "reviewId": "review-update",

            "reviewer": {"displayName": "New name"},

            "comment": "Updated original comment",

            "starRating": "FOUR",

        }

        with patch(

            "google_reviews.business_profile.requests.get",

            side_effect=self.discovery_responses(

                locations=[{"name": "locations/200"}],

                reviews={"reviews": [updated]},

            ),

        ):

            saved, retrieved = GoogleBusinessProfileService().sync_selected_reviews()



        existing.refresh_from_db()

        self.assertEqual((saved, retrieved), (1, 1))

        self.assertEqual(GoogleReview.objects.count(), 1)

        self.assertEqual(existing.reviewer_name, "New name")

        self.assertEqual(existing.comment, "Updated original comment")

        self.assertEqual(existing.rating, "FOUR")





class CalendarDeleteRetryTests(TestCase):

    def setUp(self):

        self.employee = Employee.objects.create(

            full_name="Calendar Employee",

            phone="0400000000",

        )

        self.booking = Booking.objects.create(

            service_type="Office Cleaning",

            booking_date=timezone.localdate(),

            booking_time=timezone.localtime().time().replace(second=0, microsecond=0),

            address="1 King Street",

            suburb_postcode="Adelaide 5000",

            assigned_employee=self.employee,

            google_calendar_event_id="booking-event-1",

        )

        self.roster = Roster.objects.create(

            employee=self.employee,

            booking=self.booking,

            shift_date=self.booking.booking_date,

            start_time=self.booking.booking_time,

            end_time=self.booking.booking_time,

            google_calendar_event_id="roster-event-1",

        )



    def test_booking_sync_reports_missing_company_calendar_configuration(self):

        with patch(

            "google_reviews.calendar_utils.get_company_google_calendar_service",

            return_value=None,

        ):

            with self.assertRaises(CalendarNotConfigured):

                create_or_update_booking_event(self.booking)



    @patch("google_reviews.calendar_utils.Request")

    @patch("google_reviews.calendar_utils.build")

    @patch("google_reviews.calendar_utils.Credentials")

    def test_employee_calendar_refreshes_expired_access_token(

        self,

        credentials_factory,

        build_calendar,

        google_request,

    ):

        account = EmployeeGoogleAccount.objects.create(

            employee=self.employee,

            access_token="expired-access-token",

            refresh_token="existing-refresh-token",

        )

        credentials = MagicMock()

        credentials.expired = True

        credentials.refresh_token = "rotated-refresh-token"

        credentials.token = "new-access-token"

        credentials_factory.return_value = credentials



        from google_reviews.calendar_utils import get_employee_google_calendar_service



        result = get_employee_google_calendar_service(self.employee)



        self.assertEqual(result, build_calendar.return_value)

        credentials_factory.assert_called_once()

        self.assertEqual(

            credentials_factory.call_args.kwargs["expiry"],

            _google_credentials_expiry(account.updated_at),

        )

        credentials.refresh.assert_called_once_with(google_request.return_value)

        build_calendar.assert_called_once()

        account.refresh_from_db()

        self.assertEqual(account.access_token, "new-access-token")

        self.assertEqual(account.refresh_token, "rotated-refresh-token")



    def test_company_calendar_sync_creates_event_for_unassigned_booking(self):

        self.booking.status = "cancelled"

        self.booking.save(update_fields=["status"])

        booking = Booking.objects.create(

            service_type="Office Cleaning",

            booking_date=timezone.localdate(),

            booking_time=timezone.localtime().time().replace(second=0, microsecond=0),

            address="1 King Street",

            suburb_postcode="Adelaide 5000",

        )

        service = MagicMock()

        service.events.return_value.insert.return_value.execute.return_value = {

            "id": "company-calendar-event",

        }



        with patch(

            "google_reviews.calendar_utils.get_company_google_calendar_service",

            return_value=service,

        ):

            synced_count, failed_count = sync_existing_bookings_to_company_calendar()



        self.assertEqual((synced_count, failed_count), (1, 0))

        booking.refresh_from_db()

        self.assertEqual(

            booking.google_calendar_event_id,

            "company-calendar-event",

        )

        service.events.return_value.insert.assert_called_once()

        insert_call = service.events.return_value.insert.call_args

        self.assertEqual(insert_call.kwargs["calendarId"], "primary")

        self.assertIn("Employee: Unassigned", insert_call.kwargs["body"]["description"])



    def test_booking_delete_failure_preserves_event_id_for_retry(self):

        service = MagicMock()

        service.events.return_value.delete.return_value.execute.side_effect = RuntimeError(

            "calendar unavailable"

        )

        with patch(

            "google_reviews.calendar_utils.get_company_google_calendar_service",

            return_value=service,

        ), self.assertLogs("google_reviews.calendar_utils", level="ERROR"):

            result = delete_booking_event(self.booking)



        self.assertFalse(result)

        self.booking.refresh_from_db()

        self.assertEqual(self.booking.google_calendar_event_id, "booking-event-1")



    def test_roster_delete_failure_preserves_event_id_for_retry(self):

        service = MagicMock()

        service.events.return_value.delete.return_value.execute.side_effect = RuntimeError(

            "calendar unavailable"

        )

        with patch(

            "google_reviews.calendar_utils.get_employee_google_calendar_service",

            return_value=service,

        ), self.assertLogs("google_reviews.calendar_utils", level="ERROR"):

            result = delete_roster_event(self.roster)



        self.assertFalse(result)

        self.roster.refresh_from_db()

        self.assertEqual(self.roster.google_calendar_event_id, "roster-event-1")



    def test_get_google_reviews_api_requires_a_selected_location(self):

        with self.assertRaises(GoogleAuthenticationError):

            get_google_reviews_api()



    def test_get_google_reviews_api_preserves_original_comment(self):

        reviews = [

            {

                "reviewId": "review-1",

                "reviewer": {"displayName": "Sam"},

                "comment": "Original customer comment",

                "starRating": "FIVE",

                "reviewReply": {"comment": "Business response"},

            }

        ]

        with patch(

            "google_reviews.business_profile.GoogleBusinessProfileService"

        ) as service_factory:

            service_factory.return_value.get_selected_reviews.return_value = reviews

            result = get_google_reviews_api()



        self.assertEqual(len(result), 1)

        self.assertEqual(result[0]["reviewer_name"], "Sam")

        self.assertEqual(result[0]["comment"], "Original customer comment")

        self.assertEqual(result[0]["rating"], "⭐⭐⭐⭐⭐")





    def test_booking_delete_404_clears_stale_event_id(self):

        service = MagicMock()

        service.events.return_value.delete.return_value.execute.side_effect = (

            HttpError(

                MagicMock(status=404),

                b'{"error": {"message": "Not Found"}}',

            )

        )



        with patch(

            "google_reviews.calendar_utils.get_company_google_calendar_service",

            return_value=service,

        ):

            result = delete_booking_event(self.booking)



        self.assertTrue(result)

        self.booking.refresh_from_db()

        self.assertIsNone(self.booking.google_calendar_event_id)



    def test_roster_delete_404_clears_stale_event_id(self):

        service = MagicMock()

        service.events.return_value.delete.return_value.execute.side_effect = (

            HttpError(

                MagicMock(status=404),

                b'{"error": {"message": "Not Found"}}',

            )

        )



        with patch(

            "google_reviews.calendar_utils.get_employee_google_calendar_service",

            return_value=service,

        ):

            result = delete_roster_event(self.roster)



        self.assertTrue(result)

        self.roster.refresh_from_db()

        self.assertIsNone(self.roster.google_calendar_event_id)









class CalendarEventRecoveryTests(CalendarDeleteRetryTests):

    """Regression tests for stale Google Calendar event IDs."""



    def _not_found_error(self):

        return HttpError(

            MagicMock(status=404),

            b'{"error": {"message": "Not Found"}}',

        )



    def _make_calendar_service(self, update_error=None):

        service = MagicMock()



        if update_error is not None:

            service.events.return_value.update.return_value.execute.side_effect = (

                update_error

            )



        service.events.return_value.insert.return_value.execute.return_value = {

            "id": "replacement-event-123"

        }



        return service



    def test_booking_update_404_creates_replacement_event(self):

        service = self._make_calendar_service(self._not_found_error())



        with patch(

            "google_reviews.calendar_utils.get_company_google_calendar_service",

            return_value=service,

        ):

            create_or_update_booking_event(self.booking)



        service.events.return_value.insert.assert_called_once()

        self.booking.refresh_from_db()

        self.assertEqual(

            self.booking.google_calendar_event_id,

            "replacement-event-123",

        )



    def test_roster_update_404_creates_replacement_event(self):

        service = self._make_calendar_service(self._not_found_error())



        with patch(

            "google_reviews.calendar_utils.get_employee_google_calendar_service",

            return_value=service,

        ):

            create_or_update_roster_event(self.roster)



        service.events.return_value.insert.assert_called_once()

        self.roster.refresh_from_db()

        self.assertEqual(

            self.roster.google_calendar_event_id,

            "replacement-event-123",

        )



    def test_roster_create_retry_reuses_stable_event_id(self):

        service = MagicMock()

        update_attempts = 0



        def update_event():

            nonlocal update_attempts

            update_attempts += 1

            if update_attempts == 1:

                raise self._not_found_error()

            return {"id": self.roster.google_calendar_event_id}



        service.events.return_value.update.return_value.execute.side_effect = (

            update_event

        )

        service.events.return_value.insert.return_value.execute.side_effect = (

            RuntimeError("Calendar response unavailable")

        )

        self.roster.google_calendar_event_id = None

        self.roster.save(update_fields=["google_calendar_event_id"])



        with patch(

            "google_reviews.calendar_utils.get_employee_google_calendar_service",

            return_value=service,

        ):

            with self.assertRaises(RuntimeError):

                create_or_update_roster_event(self.roster)



            self.roster.refresh_from_db()

            stable_event_id = self.roster.google_calendar_event_id

            self.assertRegex(stable_event_id, r"^r[0-9a-v]{52}$")

            self.assertEqual(

                service.events.return_value.insert.call_args.kwargs["body"]["id"],

                stable_event_id,

            )



            create_or_update_roster_event(self.roster)



        self.roster.refresh_from_db()

        self.assertEqual(self.roster.google_calendar_event_id, stable_event_id)

        service.events.return_value.insert.assert_called_once()

        self.assertEqual(service.events.return_value.update.call_count, 2)



    def test_missing_roster_calendar_service_is_explicit(self):

        with patch(

            "google_reviews.calendar_utils.get_employee_google_calendar_service",

            return_value=None,

        ):

            with self.assertRaises(CalendarNotConfigured):

                create_or_update_roster_event(self.roster)



        self.roster.refresh_from_db()

        self.assertEqual(self.roster.google_calendar_event_id, "roster-event-1")



    def test_booking_update_non_404_error_does_not_insert(self):

        service = self._make_calendar_service(

            HttpError(

                MagicMock(status=403),

                b'{"error": {"message": "Forbidden"}}',

            )

        )



        with patch(

            "google_reviews.calendar_utils.get_company_google_calendar_service",

            return_value=service,

        ):

            with self.assertRaises(HttpError):

                create_or_update_booking_event(self.booking)



        service.events.return_value.insert.assert_not_called()

        self.booking.refresh_from_db()

        self.assertEqual(

            self.booking.google_calendar_event_id,

            "booking-event-1",

        )
