# ====================================================
# YD Commercial Cleaning Services
# File: core/urls.py
# Purpose: Main website URL routing
# ====================================================

<<<<<<< HEAD
from django.urls import path

from .views import (
    contact,
    home,
    robots_txt,
    service_page,
    sitemap_xml,
)
=======
import re

from django.urls import path, re_path
from django.contrib.sitemaps.views import sitemap
from .views import (
    home,
    contact,
    login_hub,
    services_page,
    resources,
    service_page,
    service_page_redirect,
    location_landing_page,
    location_index_page,
    suburb_detail_page,
    robots_txt,
    rss_feed,
    about,
    pricing,
    team,
    faq,
    blog,
    guides,
    case_studies,
    guide_detail,
    blog_detail,
)
from .seo_data import LOCATION_ALIASES
from .sitemaps import sitemaps
>>>>>>> 5815f15 (Initial project commit)

urlpatterns = [
    # Main pages
    path("", home, name="home"),
<<<<<<< HEAD
    path("contact/", contact, name="contact"),
    # SEO files
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap_xml, name="sitemap_xml"),
    # SEO service pages
    path("<slug:service_slug>/", service_page, name="service_page"),
]
=======
    path("about/", about, name="about"),
    path("pricing/", pricing, name="pricing"),
    path("team/", team, name="team"),
    path("faq/", faq, name="faq"),
    path("blog/", blog, name="blog"),
    path("blog/<slug:blog_slug>/", blog_detail, name="blog_detail"),
    path("guides/", guides, name="guides"),
    path("case-studies/", case_studies, name="case_studies"),
    path("contact/", contact, name="contact"),
    path("login/", login_hub, name="login_hub"),

    # SEO files
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap_xml"),
    path("rss.xml", rss_feed, name="rss_feed"),

    # SEO service pages
    path("services/", services_page, name="services_home"),
    path("resources/", resources, name="resources"),
    path("local/", location_landing_page, name="location_landing"),
    path("local/adelaide/", location_landing_page, name="location_landing_adelaide"),
    path("local/index/adelaide/", location_index_page, name="location_index_root"),
    path("local/index/adelaide/<slug:letter>/", location_index_page, name="location_index_letter"),
    path("local/adelaide/<slug:suburb_slug>/", suburb_detail_page, name="suburb_detail"),
    path("services/<slug:service_slug>/", service_page, name="service_page_services"),
    path("guides/<slug:guide_slug>/", guide_detail, name="guide_detail"),
]
>>>>>>> 5815f15 (Initial project commit)
