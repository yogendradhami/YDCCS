# ====================================================
# YD Commercial Cleaning Services
# File: core/urls.py
# Purpose: Main website URL routing
# ====================================================

from django.contrib.sitemaps.views import sitemap
from django.urls import path
from django.views.generic import RedirectView

from .sitemaps import sitemaps
from .views import (
    about,
    booking_terms,
    blog,
    careers,
    case_studies,
    contact,
    corporate,
    eco_friendly_cleaning,
    emergency_cleaning,
    faq,
    guide_detail,
    guides,
    home,
    insurance,
    local_area_index,
    local_services,
    pricing,
    referral_program,
    resources,
    testimonials,
    robots_txt,
    rss_xml,
    service_page,
    services_list,
    team,
    terms,
    privacy,
    legal,
    local_suburb_detail,
)
from .views_append import blog_detail

urlpatterns = [
    # Login redirect for convenience
    path("login/", RedirectView.as_view(url="/dashboard/login/", permanent=False), name="login_redirect"),
    
    # Main pages
    path("", home, name="home"),
    path("about/", about, name="about"),
    path("pricing/", pricing, name="pricing"),
    path("team/", team, name="team"),
    path("contact/", contact, name="contact"),
    path("careers/", careers, name="careers"),
    path("terms/", terms, name="terms"),
    path("privacy/", privacy, name="privacy"),
    path("booking-terms/", booking_terms, name="booking_terms"),
    path("legal/", legal, name="legal"),
    path("resources/", resources, name="resources"),
    path("testimonials/", testimonials, name="testimonials"),
    path("guides/", guides, name="guides"),
    path("guides/<slug:guide_slug>/", guide_detail, name="guide_detail"),
    path("case-studies/", case_studies, name="case_studies"),
    path("faq/", faq, name="faq"),
    path("blog/", blog, name="blog"),
    path("blog/<slug:blog_slug>/", blog_detail, name="blog_detail"),
    path("corporate/", corporate, name="corporate"),
    path("insurance/", insurance, name="insurance"),
    path("referral-program/", referral_program, name="referral_program"),
    path("eco-friendly-cleaning/", eco_friendly_cleaning, name="eco_friendly_cleaning"),
    path("emergency-cleaning/", emergency_cleaning, name="emergency_cleaning"),
    path("rss.xml", rss_xml, name="rss_xml"),

    # SEO files
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap_xml"),
    # SEO service pages
    path("services/", services_list, name="services_home"),
    path("local/", local_services, name="local_services"),
    path(
        "local/index/adelaide/",
        local_area_index,
        {"letter": "a"},
        name="local_area_index_default",
    ),
    path(
        "local/index/adelaide/<slug:letter>/",
        local_area_index,
        name="local_area_index",
    ),
    path(
        "local/adelaide/<slug:area_slug>/",
        local_suburb_detail,
        name="local_suburb_detail",
    ),
    path("services/<slug:service_slug>/", service_page, name="service_page"),
    path("<slug:service_slug>/", service_page, name="service_page"),
]
