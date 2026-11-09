from functools import lru_cache
from django.contrib.sitemaps import Sitemap
from django.conf import settings
from django.urls import reverse

from .seo_data import LOCATION_ALIASES
from .seo_data import SERVICE_DEFINITIONS
from .adelaide_local_areas import ADELAIDE_LOCAL_AREAS
from .adelaide_local_content import ADELAIDE_LOCAL_CONTENT
from services.models import Service
from django.utils import timezone
from .models import TestimonialVideo



class BaseSitemap(Sitemap):
    protocol = "https"

    def get_domain(self, site=None):
        return "ydcleaning.com.au"

    def get_latest_lastmod(self):
        # Child sitemap URLs include lastmod; avoid scanning every item to
        # calculate a timestamp for the sitemap index.
        return None


@lru_cache(maxsize=1)
def service_page_slugs():
    active_service_slugs = list(
        Service.objects.filter(is_active=True).values_list("slug", flat=True)
    )
    active_base_slugs = {
        slug.removesuffix("-adelaide")
        for slug in active_service_slugs
    }
    service_slugs = list(active_service_slugs)
    service_slugs.extend(
        f"{slug}-adelaide"
        for slug in SERVICE_DEFINITIONS
        if slug not in active_base_slugs
    )
    slugs = []

    for service_slug in service_slugs:
        for location_slug in LOCATION_ALIASES:
            if service_slug.endswith(location_slug):
                continue

            # Adelaide CBD is represented by the existing service slug
            # ending in "-adelaide" plus the CBD suffix. Avoid the old
            # duplicated form "...-adelaide-adelaide-cbd".
            if location_slug == "adelaide-cbd" and service_slug.endswith("-adelaide"):
                slugs.append(f"{service_slug}-adelaide-cbd")
            else:
                slugs.append(f"{service_slug}-{location_slug}")

    return sorted(set(slugs))


class StaticViewSitemap(BaseSitemap):


    def items(self):
        return [
            "home",
            "contact",
            "booking",
            "testimonials",
            "cleaning_services_video",
            "customer_testimonial_video",
        ]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        if item in ["home", "booking"]:
            return 1.0
        return 0.8

    def lastmod(self, item):
        return timezone.now()


def _base_service_slug_for_local_page(service_slug):
    """Remove the final local-area suffix from a generated service-page slug."""
    for location in LOCATION_ALIASES:
        suffix = f"-{location}"
        if service_slug.endswith(suffix):
            return service_slug[:-len(suffix)]
    return service_slug


class LocalServiceSitemap(BaseSitemap):
    def items(self):
        # Load modification dates once per sitemap request. Calling
        # Service.objects.filter(...).first() from lastmod() caused one
        # database query for every generated local-service URL.
        self._service_lastmod_by_slug = dict(
            Service.objects.values_list("slug", "updated_at")
        )
        self._fallback_lastmod = timezone.now()
        return service_page_slugs()

    def priority(self, item):
        return 0.7

    def location(self, item):
        return reverse(
            "service_page",
            kwargs={"service_slug": item},
        )

    def lastmod(self, item):
        service_slug = _base_service_slug_for_local_page(item)
        return self._service_lastmod_by_slug.get(
            service_slug,
            self._fallback_lastmod,
        )


class ServicesIndexSitemap(BaseSitemap):

    def items(self):
        return ["services_home"]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return 0.9

    def lastmod(self, item):
        return timezone.now()


class ServiceDetailSitemap(BaseSitemap):

    def items(self):
        active_services = list(Service.objects.filter(is_active=True).order_by("slug"))
        active_base_slugs = {
            service.slug.removesuffix("-adelaide")
            for service in active_services
        }
        definition_slugs = [
            f"{slug}-adelaide"
            for slug in SERVICE_DEFINITIONS
            if slug not in active_base_slugs
        ]
        return [*active_services, *definition_slugs]

    def priority(self, obj):
        return 0.8

    def lastmod(self, obj):
        return obj.updated_at if isinstance(obj, Service) else timezone.now()

    def location(self, obj):
        service_slug = obj.slug if isinstance(obj, Service) else obj
        return reverse(
            "service_page",
            kwargs={"service_slug": service_slug},
        )


class AdelaideLocalAreaSitemap(BaseSitemap):

    def items(self):
        return sorted(set(ADELAIDE_LOCAL_AREAS) | set(ADELAIDE_LOCAL_CONTENT))

    def priority(self, item):
        return 0.75

    def location(self, item):
        return reverse(
            "local_suburb_detail",
            kwargs={"area_slug": item},
        )

    def lastmod(self, item):
        return timezone.now()


class AdelaideLocalIndexSitemap(BaseSitemap):
    """Main Adelaide local SEO hub."""

    def items(self):
        return ["local_area_index_default"]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return 0.9

    def lastmod(self, item):
        return timezone.now()


class AdelaideLocalLetterSitemap(BaseSitemap):
    """A-Z Adelaide local-area index pages with actual suburb data."""

    def items(self):
        # Only expose letters that currently have local-area entries.
        # Existing local pages and the underlying suburb dataset are untouched.
        from .views import _get_letter_areas

        return [
            letter
            for letter in "abcdefghijklmnopqrstuvwxyz"
            if _get_letter_areas(letter)
        ]

    def location(self, item):
        return reverse(
            "local_area_index",
            kwargs={"letter": item},
        )

    def priority(self, item):
        return 0.75

    def lastmod(self, item):
        return timezone.now()


class TestimonialVideoSitemap(BaseSitemap):
    """Dedicated watch pages for active customer testimonial videos."""

    def items(self):
        return TestimonialVideo.objects.filter(active=True)

    def location(self, video):
        return reverse(
            "testimonial_video_watch",
            kwargs={"video_id": video.pk},
        )

    def lastmod(self, video):
        return video.updated_at

    def priority(self, video):
        return 0.7


sitemaps = {
    "static": StaticViewSitemap,
    "services_index": ServicesIndexSitemap,
    "service_details": ServiceDetailSitemap,
    "local_services": LocalServiceSitemap,
    "adelaide_local_areas": AdelaideLocalAreaSitemap,
    "adelaide_local_index": AdelaideLocalIndexSitemap,
    "adelaide_local_letters": AdelaideLocalLetterSitemap,
    "testimonial_videos": TestimonialVideoSitemap,
}
