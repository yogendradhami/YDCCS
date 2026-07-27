from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .seo_data import LOCATION_ALIASES
from services.models import Service


def service_page_slugs():
    active_services = Service.objects.filter(is_active=True)
    slugs = []

    for service in active_services:
        for location_slug in LOCATION_ALIASES:

            # Avoid duplicate adelaide-adelaide URLs
            if service.slug.endswith(location_slug):
                continue

            slugs.append(f"{service.slug}-{location_slug}")

    return sorted(set(slugs))

class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return ["home", "contact", "booking"]

    def location(self, item):
        return reverse(item)


class LocalServiceSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return service_page_slugs()

    def location(self, item):
        return reverse(
            "service_page",
            kwargs={"service_slug": item}
        )


class ServicesIndexSitemap(Sitemap):
    changefreq = "weekly"
    priority = 1.0

    def items(self):
        return ["services_home"]

    def location(self, item):
        return reverse(item)


class ServiceDetailSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Service.objects.filter(is_active=True)

    def location(self, obj):
        return reverse(
            "service_page",
            kwargs={"service_slug": obj.slug},
        )


# KEEP THIS AT THE VERY END
sitemaps = {
    "static": StaticViewSitemap,
    "services_index": ServicesIndexSitemap,
    "service_details": ServiceDetailSitemap,
    "local_services": LocalServiceSitemap,
}