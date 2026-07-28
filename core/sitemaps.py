from functools import lru_cache
from django.contrib.sitemaps import Sitemap
from django.conf import settings
from django.urls import reverse

from .seo_data import LOCATION_ALIASES
from services.models import Service


class BaseSitemap(Sitemap):
    protocol = "https"

    def get_domain(self, site=None):
        return "ydcleaning.com.au"

@lru_cache(maxsize=1)
def service_page_slugs():
    active_services = Service.objects.filter(is_active=True)
    slugs = []

    for service in active_services:
        for location_slug in LOCATION_ALIASES:

            if service.slug.endswith(location_slug):
                continue

            slugs.append(f"{service.slug}-{location_slug}")

    return sorted(set(slugs))


class StaticViewSitemap(BaseSitemap):


    def items(self):
        return ["home", "contact", "booking"]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        if item in ["home", "booking"]:
            return 1.0
        return 0.8


class LocalServiceSitemap(BaseSitemap):

    def items(self):
        return service_page_slugs()

    def location(self, item):
        return reverse(
            "service_page",
            kwargs={"service_slug": item}
        )

    def lastmod(self, item):

        service_slug = item

        for location in LOCATION_ALIASES:
            suffix = f"-{location}"

            if service_slug.endswith(suffix):
                service_slug = service_slug[:-len(suffix)]
                break

        service = Service.objects.filter(
            slug=service_slug
        ).first()

        return service.updated_at if service else None


class ServicesIndexSitemap(BaseSitemap):


    def items(self):
        return ["services_home"]

    def location(self, item):
        return reverse(item)


class ServiceDetailSitemap(BaseSitemap):

    def items(self):
        return Service.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse(
            "service_page",
            kwargs={"service_slug": obj.slug},
        )


sitemaps = {
    "static": StaticViewSitemap,
    "services_index": ServicesIndexSitemap,
    "service_details": ServiceDetailSitemap,
    "local_services": LocalServiceSitemap,
}