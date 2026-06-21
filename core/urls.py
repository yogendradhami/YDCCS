# ====================================================
# YD Commercial Cleaning Services
# File: core/urls.py
# Purpose: Main website URL routing
# ====================================================

from django.urls import path

from .views import (
    contact,
    home,
    robots_txt,
    service_page,
    sitemap_xml,
)

urlpatterns = [
    # Main pages
    path("", home, name="home"),
    path("contact/", contact, name="contact"),
    # SEO files
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap_xml, name="sitemap_xml"),
    # SEO service pages
    path("<slug:service_slug>/", service_page, name="service_page"),
]
