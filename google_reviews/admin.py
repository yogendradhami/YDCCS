import logging

from django.contrib import admin, messages
from django.db import transaction
from django.urls import path
from django.shortcuts import redirect
from django.urls import reverse

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

    @admin.display(description="Voice of Merchant")
    def voice_of_merchant_status(self, location):
        if location.has_voice_of_merchant is None:
            return "Not provided by Google"
        return "Available" if location.has_voice_of_merchant else "Unavailable"

    @admin.display(description="Account verification")
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

        verification_message = ""
        if location.has_voice_of_merchant is not True:
            verification_message = (
                " Google's Voice of Merchant metadata does not confirm listing "
                "verification; the reviews API will validate access during sync."
            )
        self.message_user(
            request,
            f"Selected {location.title or location.resource_name} under "
            f"{location.account.account_name or location.account.resource_name}."
            f"{verification_message}",
            level=(
                messages.WARNING
                if verification_message
                else messages.SUCCESS
            ),
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
                self.admin_site.admin_view(self.sync_reviews),
                name="sync_google_reviews",
            ),
        ]

        return custom_urls + super().get_urls()

    def sync_reviews(self, request):

        from .views import sync_google_reviews

        response = sync_google_reviews(request)

        if response.status_code == 204:
            messages.warning(
                request,
                response.content.decode()
                or "Google returned zero reviews. Existing saved reviews were left unchanged.",
            )
        elif response.status_code == 200:
            messages.success(
                request,
                response.content.decode()
            )
        else:
            messages.error(
                request,
                response.content.decode()
            )

        return redirect("../")