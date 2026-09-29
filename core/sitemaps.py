from django.contrib.sitemaps import Sitemap
from django.conf import settings
from django.urls import reverse

from .adelaide_local_areas import ADELAIDE_LOCAL_AREAS
from services.models import Service
from django.utils import timezone



class BaseSitemap(Sitemap):
    protocol = "https"

    def get_domain(self, site=None):
        return "ydcleaning.com.au"

class StaticViewSitemap(BaseSitemap):


    def items(self):
        return ["home", "contact", "booking"]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        if item in ["home", "booking"]:
            return 1.0
        return 0.8

    def lastmod(self, item):
        return timezone.now()


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
        return Service.objects.filter(is_active=True)

    def priority(self, obj):
        return 0.8

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse(
            "service_page",
            kwargs={"service_slug": obj.slug},
        )


class AdelaideLocalAreaSitemap(BaseSitemap):

    def items(self):
        return sorted(ADELAIDE_LOCAL_AREAS.keys())

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


sitemaps = {
    "static": StaticViewSitemap,
    "services_index": ServicesIndexSitemap,
    "service_details": ServiceDetailSitemap,
    "adelaide_local_areas": AdelaideLocalAreaSitemap,
    "adelaide_local_index": AdelaideLocalIndexSitemap,
    "adelaide_local_letters": AdelaideLocalLetterSitemap,
}