import logging



from django.contrib import admin, messages

from django.db import transaction

from django.urls import path

from django.shortcuts import redirect

from django.urls import reverse

from django.views.decorators.http import require_POST

from .business_profile import (

    GoogleBusinessProfileError,

    refresh_discovered_profiles,

)

from .models import (

    GoogleAccount,

    GoogleBusinessProfileAccount,

    GoogleBusinessProfileLocation,

    GoogleReview,

)



logger = logging.getLogger(__name__)





@admin.register(GoogleAccount)

class GoogleAccountAdmin(admin.ModelAdmin):

    list_display = (

        "email",

        "connected_at",

        "updated_at",

    )

    change_list_template = (

        "admin/google_reviews/googleaccount/change_list.html"

    )





class GoogleBusinessProfileDiscoveryAdmin(admin.ModelAdmin):

    def get_urls(self):

        custom_urls = [

            path(

                "discover-profiles/",

                self.admin_site.admin_view(self.discover_profiles),

                name=f"discover_{self.model._meta.model_name}_profiles",

            ),

        ]

        return custom_urls + super().get_urls()



    def discover_profiles(self, request):

        try:

            accounts = refresh_discovered_profiles()

        except GoogleBusinessProfileError as exc:

            self.message_user(request, exc.user_message, level=messages.ERROR)

        except Exception:

            logger.exception(

                "Google Business Profile administrator discovery failed."

            )

            self.message_user(

                request,

                "Google Business Profile discovery failed. Check server logs.",

                level=messages.ERROR,

            )

        else:

            account_report = ", ".join(

                f"{item.get('accountName') or item.get('name')} "

                f"({item.get('name')}; verification "

                f"{item.get('verificationState') or 'not provided'})"

                for item in accounts

            ) or "No accessible accounts"

            self.message_user(

                request,

                f"Discovered {len(accounts)} account(s): {account_report}. "

                "Select the correct YDCCS business location on the next page.",

                level=messages.SUCCESS,

            )

        return redirect(

            reverse("admin:google_reviews_googlebusinessprofilelocation_changelist")

        )





@admin.register(GoogleBusinessProfileAccount)

class GoogleBusinessProfileAccountAdmin(GoogleBusinessProfileDiscoveryAdmin):

    change_list_template = (

        "admin/google_reviews/googlebusinessprofileaccount/change_list.html"

    )

    list_display = (

        "account_name",

        "resource_name",

        "account_type",

        "verification_state",

        "is_available",

        "last_discovered_at",

    )

    search_fields = ("account_name", "resource_name")

    readonly_fields = (

        "resource_name",

        "account_name",

        "account_type",

        "verification_state",

        "is_available",

        "last_discovered_at",

    )



    def has_add_permission(self, request):

        return False



    def has_change_permission(self, request, obj=None):

        return False



    def has_delete_permission(self, request, obj=None):

        return False





@admin.register(GoogleBusinessProfileLocation)

class GoogleBusinessProfileLocationAdmin(GoogleBusinessProfileDiscoveryAdmin):

    change_list_template = (

        "admin/google_reviews/googlebusinessprofilelocation/change_list.html"

    )

    list_display = (

        "title",

        "account",

        "resource_name",

        "account_verification_state",

        "voice_of_merchant_status",

        "address_summary",

        "is_available",

        "is_selected",

        "last_discovered_at",

    )

    list_filter = ("is_available", "is_selected", "has_voice_of_merchant")

    search_fields = (

        "title",

        "resource_name",

        "account__account_name",

        "account__resource_name",

    )

    actions = ("select_as_reviews_location",)

    readonly_fields = (

        "account",

        "resource_name",

        "title",

        "storefront_address",

        "has_voice_of_merchant",

        "is_available",

        "is_selected",

        "last_discovered_at",

    )



    def has_add_permission(self, request):

        return False



    def has_delete_permission(self, request, obj=None):

        return False



    def get_urls(self):

        custom_urls = [

            path(

                "check-selected-verification/",

                self.admin_site.admin_view(

                    self.check_selected_verification

                ),

                name="check_google_business_profile_verification",

            ),

        ]

        return custom_urls + super().get_urls()



    def check_selected_verification(self, request):

        location = GoogleBusinessProfileLocation.objects.filter(

            is_selected=True

        ).first()

        if location is None:

            self.message_user(

                request,

                "Select a Google Business Profile location before checking its status.",

                level=messages.ERROR,

            )

            return redirect(

                reverse(

                    "admin:google_reviews_googlebusinessprofilelocation_changelist"

                )

            )



        from .business_profile import GoogleBusinessProfileService



        try:

            state = GoogleBusinessProfileService().get_location_voice_of_merchant_state(

                location.resource_name

            )

        except GoogleBusinessProfileError as exc:

            self.message_user(request, exc.user_message, level=messages.ERROR)

        except Exception:

            logger.exception(

                "Google Business Profile verification-state check failed."

            )

            self.message_user(

                request,

                "Could not check this location's Google verification state. "

                "Check server logs.",

                level=messages.ERROR,

            )

        else:

            has_voice_of_merchant = state.get("hasVoiceOfMerchant")

            recommendation = next(

                (

                    key

                    for key in (

                        "verify",

                        "resolveOwnershipConflict",

                        "complyWithGuidelines",

                        "waitForVoiceOfMerchant",

                    )

                    if state.get(key) is not None

                ),

                None,

            )

            logger.info(

                "Google location verification state received: resource=%s "

                "has_voice_of_merchant=%s has_business_authority=%s "

                "recommendation=%s",

                location.resource_name,

                has_voice_of_merchant,

                state.get("hasBusinessAuthority"),

                recommendation,

                extra={

                    "google_resource": location.resource_name,

                    "has_voice_of_merchant": has_voice_of_merchant,

                    "has_business_authority": state.get("hasBusinessAuthority"),

                    "verification_recommendation": recommendation,

                },

            )

            if isinstance(has_voice_of_merchant, bool):

                location.has_voice_of_merchant = has_voice_of_merchant

                location.save(update_fields=("has_voice_of_merchant",))



            if state.get("verify") is not None:

                pending = state["verify"].get("hasPendingVerification")

                detail = (

                    "A verification is already pending; complete it in Google "

                    "Business Profile."

                    if pending

                    else "Complete the requested verification in Google "

                    "Business Profile before syncing reviews."

                )

                self.message_user(

                    request,

                    f"Google reports that {location.title or location.resource_name} "

                    f"requires verification. {detail}",

                    level=messages.ERROR,

                )

            elif state.get("resolveOwnershipConflict") is not None:

                self.message_user(

                    request,

                    "Google's Voice of Merchant response explicitly reports "

                    "resolveOwnershipConflict for this location, which Google "

                    "defines as a duplicate of another location in good standing. "

                    "This is not inferred from the account verification status or "

                    "a Reviews API error. Confirm the affected resource in Google "

                    "Business Profile before taking action.",

                    level=messages.ERROR,

                )

            elif state.get("complyWithGuidelines") is not None:

                self.message_user(

                    request,

                    "Google requires this listing to address a Business Profile "

                    "guidelines issue before it can be used.",

                    level=messages.ERROR,

                )

            elif state.get("waitForVoiceOfMerchant") is not None:

                self.message_user(

                    request,

                    "Google reports that this listing is under review. Wait for "

                    "Google to grant Voice of Merchant, then retry review sync.",

                    level=messages.WARNING,

                )

            elif has_voice_of_merchant is True:

                self.message_user(

                    request,

                    "Google reports that this location has Voice of Merchant "

                    "and is in good standing. If review sync still fails, refresh "

                    "the selected account/location resources.",

                    level=messages.SUCCESS,

                )

            else:

                self.message_user(

                    request,

                    "Google did not confirm this location's Voice of Merchant "

                    "state. Its verification status remains unknown.",

                    level=messages.WARNING,

                )



        return redirect(

            reverse(

                "admin:google_reviews_googlebusinessprofilelocation_changelist"

            )

        )



    @admin.display(description="Voice of Merchant")

    def voice_of_merchant_status(self, location):

        if location.has_voice_of_merchant is None:

            return "Not provided by Google"

        return "Available" if location.has_voice_of_merchant else "Unavailable"



    @admin.display(description="Account verification (not location)")

    def account_verification_state(self, location):

        return location.account.verification_state or "Not provided by Google"



    @admin.display(description="Address")

    def address_summary(self, location):

        address = location.storefront_address or {}

        return ", ".join(

            part

            for part in (

                " ".join(address.get("addressLines", [])),

                address.get("locality"),

                address.get("administrativeArea"),

                address.get("postalCode"),

            )

            if part

        )



    @admin.action(description="Select as Google Reviews location")

    def select_as_reviews_location(self, request, queryset):

        if queryset.count() != 1:

            self.message_user(

                request,

                "Select exactly one Google Business Profile location.",

                level=messages.ERROR,

            )

            return



        location = queryset.select_related("account").get()

        if not location.is_available:

            self.message_user(

                request,

                "This location is no longer available. Discover locations again first.",

                level=messages.ERROR,

            )

            return

        with transaction.atomic():

            GoogleBusinessProfileLocation.objects.filter(

                is_selected=True

            ).update(is_selected=False)

            GoogleBusinessProfileLocation.objects.filter(

                pk=location.pk

            ).update(is_selected=True)



        if location.has_voice_of_merchant is False:

            verification_message = (

                " Google reports this location does not currently have Voice of "

                "Merchant. Check its verification or ownership status before syncing."

            )

            level = messages.WARNING

        elif location.has_voice_of_merchant is None:

            verification_message = (

                " Google did not provide Voice of Merchant metadata; the location "

                "verification state is unknown."

            )

            level = messages.WARNING

        else:

            verification_message = ""

            level = messages.SUCCESS

        self.message_user(

            request,

            f"Selected {location.title or location.resource_name} under "

            f"{location.account.account_name or location.account.resource_name}."

            f"{verification_message}",

            level=level,

        )





@admin.register(GoogleReview)

class GoogleReviewAdmin(admin.ModelAdmin):



    list_display = (

        "reviewer_name",

        "rating",

        "review_date",

    )



    search_fields = (

        "reviewer_name",

        "comment",

    )



    readonly_fields = (

        "review_id",

        "review_updated_at",

        "created_at",

        "updated_at",

    )





    change_list_template = "reviews/google_review_change_list.html"

    def get_urls(self):

        custom_urls = [

            path(

                "sync/",

                self.admin_site.admin_view(

                    require_POST(self.sync_reviews)

                ),

                name="sync_google_reviews",

            ),

        ]



        return custom_urls + super().get_urls()











    def sync_reviews(self, request):

        from .views import _sync_google_reviews_response



        response = _sync_google_reviews_response()



        if response.status_code == 204:

            messages.warning(

                request,

                response.content.decode()

                or "Google returned zero reviews. Existing saved reviews were left unchanged.",

            )

        elif response.status_code == 200:

            messages.success(request, response.content.decode())

        else:

            messages.error(request, response.content.decode())



        return redirect("../")
