from django.contrib.sitemaps import Sitemap
from django.conf import settings
from django.urls import reverse

from .seo_data import LOCATION_ALIASES
from services.models import Service


class BaseSitemap(Sitemap):
    protocol = "https"

    def get_domain(self, site=None):
        return "ydcleaning.com.au"

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

    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return ["home", "contact", "booking"]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        if item in ["home", "booking"]:
            return 1.0
        return 0.8


class LocalServiceSitemap(BaseSitemap):

    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return service_page_slugs()

    def location(self, item):
        return reverse(
            "service_page",
            kwargs={"service_slug": item}
        )


class ServicesIndexSitemap(BaseSitemap):

    changefreq = "weekly"
    priority = 1.0

    def items(self):
        return ["services_home"]

    def location(self, item):
        return reverse(item)


class ServiceDetailSitemap(BaseSitemap):

    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Service.objects.filter(is_active=True)

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