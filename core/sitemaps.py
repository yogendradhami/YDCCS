from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .seo_data import LOCATION_ALIASES
from services.models import Service


def service_page_slugs():
    active_services = Service.objects.filter(is_active=True)
    slugs = []
    for service in active_services:
        for location_slug in LOCATION_ALIASES:
            slugs.append(f"{service.slug}-{location_slug}")
    return sorted(set(slugs))


class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return ["home", "contact"]

    def location(self, item):
        return reverse(item)


class ServicePageSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return service_page_slugs()

    def location(self, item):
        return reverse("service_page", kwargs={"service_slug": item})


sitemaps = {
    "static": StaticViewSitemap,
    "services": ServicePageSitemap,
}
