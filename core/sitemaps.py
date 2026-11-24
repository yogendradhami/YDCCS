from functools import lru_cache
from urllib.parse import urlsplit

from django.contrib.sitemaps import Sitemap
from django.conf import settings
from django.urls import reverse

from .seo_data import (
    LOCATION_ALIASES,
    SERVICE_DEFINITIONS,
    get_curated_service_location_slugs,
)
from .adelaide_local_areas import ADELAIDE_LOCAL_AREAS
from .adelaide_local_content import ADELAIDE_LOCAL_CONTENT
from blog.models import BlogPost
from services.models import Service
from .models import TestimonialVideo


class BaseSitemap(Sitemap):
    protocol = "https"

    def get_domain(self, site=None):
        return urlsplit(settings.SITE_URL).netloc


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
        canonical_service_slug = (
            service_slug
            if service_slug.endswith("-adelaide")
            else f"{service_slug}-adelaide"
        )
        base_service_slug = canonical_service_slug.removesuffix("-adelaide")

        for location_slug in get_curated_service_location_slugs(base_service_slug):
            slugs.append(f"{canonical_service_slug}-{location_slug}")

    return sorted(set(slugs))


class StaticViewSitemap(BaseSitemap):

    def items(self):
        return [
            "home",
            "about",
            "pricing",
            "team",
            "contact",
            "resources",
            "testimonials",
            "guides",
            "case_studies",
            "faq",
            "insurance",
            "eco_friendly_cleaning",
            "emergency_cleaning",
            "blog",
            "cleaning_services_video",
            "customer_testimonial_video",
            "booking",
        ]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        if item == "home":
            return 1.0
        if item in {"services_home", "guides", "blog"}:
            return 0.9
        if item == "booking":
            return 0.8
        return 0.8


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
        return self._service_lastmod_by_slug.get(service_slug)


class ServicesIndexSitemap(BaseSitemap):

    def items(self):
        return ["services_home"]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return 0.9

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
        return obj.updated_at if isinstance(obj, Service) else None

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

class AdelaideLocalIndexSitemap(BaseSitemap):
    """Main Adelaide local SEO hub."""

    def items(self):
        return ["local_area_index_default"]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return 0.9

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


class BlogPostSitemap(BaseSitemap):
    def items(self):
        return BlogPost.objects.filter(published=True).order_by("slug")

    def location(self, post):
        return reverse("blog_detail", kwargs={"blog_slug": post.slug})

    def lastmod(self, post):
        return post.updated_at

    def priority(self, post):
        return 0.7


class GuideSitemap(BaseSitemap):
    def items(self):
        return (
            "end-of-lease-checklist",
            "office-checklist",
            "maintenance-schedule",
            "post-construction-checklist",
            "residential-checklist",
            "window-glass-guide",
        )

    def location(self, item):
        return reverse("guide_detail", kwargs={"guide_slug": item})

    def priority(self, item):
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
    "blog_posts": BlogPostSitemap,
    "guides": GuideSitemap,
}
