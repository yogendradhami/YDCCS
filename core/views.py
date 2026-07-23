# ====================================================
# YD Commercial Cleaning Services
# File: core/views.py
# Purpose: Handles homepage, contact, services, SEO files
# ====================================================

import os
import string
from django.conf import settings

from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.template import TemplateDoesNotExist
from django.utils.text import slugify

from .suburbs_data import ADELAIDE_SUBURBS
from .seo_data import SERVICE_DEFINITIONS
from blog.models import BlogPost
from gallery.models import GalleryItem
from quotes.email_service import (
    send_admin_quote_email,
    send_customer_quote_email,
)
from quotes.forms import QuoteRequestForm
from quotes.models import QuoteImage
from reviews.models import Review
from services.models import Service
from google_reviews.review_utils import get_google_reviews_api


def _slugify_area(area):
    return slugify(f"{area['name']} {area['postcode']}")


def _get_adelaide_services():
    return [
        {
            "slug": "commercial-cleaning-adelaide",
            "name": "Commercial Cleaning",
            "service_name": "Commercial Cleaning",
            "description": "Reliable commercial cleaning for offices, shops, warehouses and business premises across Adelaide.",
            "url": "/services/commercial-cleaning-adelaide/",
            "included": ["Office cleaning", "Retail cleaning", "Warehouse cleaning"],
        },
        {
            "slug": "office-cleaning-adelaide",
            "name": "Office Cleaning",
            "service_name": "Office Cleaning",
            "description": "Keep your workplace clean, fresh and professional with regular office cleaning services tailored to your business needs.",
            "url": "/services/office-cleaning-adelaide/",
            "included": ["Reception areas", "Shared workspaces", "Desks and meeting rooms"],
        },
        {
            "slug": "end-of-lease-cleaning-adelaide",
            "name": "End of Lease Cleaning",
            "service_name": "End of Lease Cleaning",
            "description": "Detailed end-of-lease cleaning for tenants, landlords and property managers across Adelaide.",
            "url": "/services/end-of-lease-cleaning-adelaide/",
            "included": ["Bond cleaning", "Kitchen deep clean", "Carpet steam cleaning"],
        },
        {
            "slug": "house-cleaning-adelaide",
            "name": "House Cleaning",
            "service_name": "House Cleaning",
            "description": "Affordable and reliable house cleaning for Adelaide homes, including regular cleans, one-off cleans and deep cleaning.",
            "url": "/services/house-cleaning-adelaide/",
            "included": ["Living rooms", "Bedrooms", "Bathrooms"],
        },
        {
            "slug": "window-cleaning-adelaide",
            "name": "Window Cleaning",
            "service_name": "Window Cleaning",
            "description": "Interior and exterior window cleaning for homes, offices and commercial spaces across Adelaide.",
            "url": "/services/window-cleaning-adelaide/",
            "included": ["Interior glass", "Exterior glass", "Frame and sill cleaning"],
        },
    ]


def _get_letter_areas(letter):
    return [
        {"name": area["name"], "postcode": area["postcode"], "slug": _slugify_area(area)}
        for area in ADELAIDE_SUBURBS.get(letter.lower(), [])
    ]


def _get_suburb_by_slug(area_slug):
    for areas in ADELAIDE_SUBURBS.values():
        for area in areas:
            if _slugify_area(area) == area_slug:
                return area
    return None


# ====================================================
# Homepage View
# ====================================================
def home(request):
    gallery_items = GalleryItem.objects.filter(featured=True).order_by("-created_at")[:6]
    featured_reviews = Review.objects.filter(featured=True).order_by("-created_at")[:3]

    google_reviews = get_google_reviews_api()
    if not google_reviews:
        google_reviews = [
            {
                "reviewer_name": review.customer_name,
                "comment": review.review_text,
                "rating": review.stars(),
                "suburb": review.suburb,
                "created_at": review.created_at,
            }
            for review in featured_reviews
        ]

    rating_values = []
    for review in google_reviews:
        rating = review.get("rating")
        if isinstance(rating, str):
            rating_values.append(rating.count("★") or rating.count("⭐"))
        elif isinstance(rating, int):
            rating_values.append(rating)

    average_rating = round(sum(rating_values) / len(rating_values), 1) if rating_values else 5.0
    google_review_count = len(google_reviews)

    if request.method == "POST":
        form = QuoteRequestForm(request.POST, request.FILES)

        if form.is_valid():

            quote = form.save(commit=False)

            base_price = 120

            base_price += int(quote.bedrooms or 0) * 30
            base_price += int(quote.bathrooms or 0) * 20

            if quote.property_type == "Office":
                base_price += 150

            elif quote.property_type == "Commercial Property":
                base_price += 250

            elif quote.property_type == "End of Lease Property":
                base_price += 300

            if quote.window_cleaning:
                base_price += 50

            if quote.carpet_shampooing:
                base_price += 100

            if quote.grout_cleaning:
                base_price += 75

            if quote.upholstery_cleaning:
                base_price += 60

            if quote.laundry_service:
                base_price += 60

            quote.estimated_price = base_price
            quote.save(update_fields=None)

            uploaded_images = request.FILES.getlist("property_images")

            for image in uploaded_images:
                QuoteImage.objects.create(quote=quote, image=image)

            try:
                send_customer_quote_email(quote)
                send_admin_quote_email(quote)
            except Exception as error:
                print("Email sending failed:", error)

            messages.success(
                request,
                f"✅ Thank you! Your quote request has been submitted successfully. Estimated price: ${quote.estimated_price}. Our team will confirm the final price shortly.",
            )

            return redirect("/#quote")

        messages.error(request, "❌ Please check the form and try again.")

    else:
        form = QuoteRequestForm()

    return render(
        request,
        "home.html",
        {
            "form": form,
            "gallery_items": gallery_items,
            "reviews": featured_reviews,
            "google_reviews": google_reviews,
            "average_rating": average_rating,
            "google_review_count": google_review_count,
        },
    )


# ====================================================
# Contact Page View
# ====================================================


def contact(request):
    return render(request, "contact.html")


# ====================================================
# Services List Page View
# ====================================================


def services_list(request):
    services = [
        {
            "slug": "commercial-cleaning-adelaide",
            "service_name": "Commercial Cleaning",
            "description": "Reliable commercial cleaning for offices, shops, warehouses and business premises across Adelaide.",
            "url": "/services/commercial-cleaning-adelaide/",
        },
        {
            "slug": "office-cleaning-adelaide",
            "service_name": "Office Cleaning",
            "description": "Keep your workplace clean, fresh and professional with regular office cleaning services tailored to your business needs.",
            "url": "/services/office-cleaning-adelaide/",
        },
        {
            "slug": "end-of-lease-cleaning-adelaide",
            "service_name": "End of Lease Cleaning",
            "description": "Detailed end-of-lease cleaning for tenants, landlords and property managers across Adelaide.",
            "url": "/services/end-of-lease-cleaning-adelaide/",
        },
        {
            "slug": "house-cleaning-adelaide",
            "service_name": "House Cleaning",
            "description": "Affordable and reliable house cleaning for Adelaide homes, including regular cleans, one-off cleans and deep cleaning.",
            "url": "/services/house-cleaning-adelaide/",
        },
        {
            "slug": "window-cleaning-adelaide",
            "service_name": "Window Cleaning",
            "description": "Interior and exterior window cleaning for homes, offices and commercial spaces across Adelaide.",
            "url": "/services/window-cleaning-adelaide/",
        },
    ]
    
    db_reviews = Review.objects.filter(featured=True).order_by("-created_at")[:3]
    google_reviews = []
    for r in db_reviews:
        google_reviews.append({
            "reviewer_name": r.customer_name,
            "review_text": r.review_text,
        })
        
    context = {
        "services": services,
        "google_reviews": google_reviews,
        "page_description": "Professional cleaning services for homes, offices and commercial properties across Adelaide.",
    }
    return render(request, "services/services_list.html", context)


def resources(request):
    resources_list = [
        {
            "title": "Local Services",
            "description": "Find Adelaide suburbs, service areas and local cleaning options.",
            "url": "/local/",
            "icon": "🧭",
        },
        {
            "title": "Cleaning Guides",
            "description": "Free PDF guides, checklists and expert cleaning tips.",
            "url": "/guides/",
            "icon": "📘",
        },
        {
            "title": "Blog & Tips",
            "description": "Practical cleaning advice, seasonal tips and professional insights.",
            "url": "/blog/",
            "icon": "📝",
        },
        {
            "title": "Case Studies",
            "description": "Real Adelaide results from our commercial and residential cleaning work.",
            "url": "/case-studies/",
            "icon": "📊",
        },
        {
            "title": "Testimonials",
            "description": "Read trusted client reviews and evidence of our premium Adelaide cleaning service.",
            "url": "/testimonials/",
            "icon": "🌟",
        },
        {
            "title": "FAQ",
            "description": "Answers to common questions about booking, pricing and services.",
            "url": "/faq/",
            "icon": "❓",
        },
        {
            "title": "Insurance & Guarantees",
            "description": "Learn about our coverage, guarantees and risk-free service promise.",
            "url": "/insurance/",
            "icon": "🛡️",
        },
        {
            "title": "Corporate Partnerships",
            "description": "Cleaning solutions for businesses, property managers and commercial partners.",
            "url": "/corporate/",
            "icon": "🤝",
        },
        {
            "title": "Eco-Friendly Cleaning",
            "description": "Sustainable cleaning practices that are safe for people and the planet.",
            "url": "/eco-friendly-cleaning/",
            "icon": "🌿",
        },
        {
            "title": "Emergency Cleaning",
            "description": "Fast response cleaning for urgent jobs, events and unexpected messes.",
            "url": "/emergency-cleaning/",
            "icon": "🚨",
        },
    ]
    return render(request, "pages/resources.html", {"resources_list": resources_list})


def testimonials(request):
    from google_reviews.review_utils import get_google_reviews_api
    
    # Fetch live Google reviews from API
    google_reviews = get_google_reviews_api()
    
    # Fall back to featured DB reviews if no API reviews
    featured_reviews = Review.objects.filter(featured=True).order_by("-created_at")[:6]
    if not google_reviews:
        google_reviews = [
            {
                "reviewer_name": review.customer_name,
                "comment": review.review_text,
                "rating": review.stars(),
            }
            for review in featured_reviews
        ]
    
    testimonials = [
        {
            "reviewer_name": review.customer_name,
            "review_text": review.review_text,
            "rating": review.stars(),
            "suburb": review.suburb,
        }
        for review in featured_reviews
    ]

    google_review_count = len(google_reviews)

    return render(
        request,
        "pages/testimonials.html",
        {
            "testimonials": testimonials,
            "google_reviews": google_reviews,
            "google_review_count": google_review_count,
        },
    )


def guides(request):
    return render(request, "pages/guides.html")


def guide_detail(request, guide_slug):
    template_name = f"pages/guides/{guide_slug}.html"
    try:
        return render(request, template_name)
    except TemplateDoesNotExist:
        raise Http404("Guide not found")


def case_studies(request):
    return render(request, "pages/case-studies.html")


def faq(request):
    return render(request, "pages/faq.html")


def blog(request):
    posts = BlogPost.objects.filter(published=True).order_by("-published_at")
    return render(request, "pages/blog.html", {"posts": posts})


def about(request):
    return render(request, "pages/about.html")


def pricing(request):
    return render(request, "pages/pricing.html")


def team(request):
    return render(request, "pages/team.html")


def corporate(request):
    return render(request, "pages/corporate.html")


def insurance(request):
    return render(request, "pages/insurance.html")


def referral_program(request):
    return render(request, "pages/referral_program.html")


def eco_friendly_cleaning(request):
    return render(request, "pages/eco_friendly_cleaning.html")


def emergency_cleaning(request):
    return render(request, "pages/emergency_cleaning.html")


def rss_xml(request):
    posts = BlogPost.objects.filter(published=True).order_by("-published_at")[:20]
    feed_items = []
    for post in posts:
        url = request.build_absolute_uri(f"/blog/{post.slug}/")
        feed_items.append(
            f"""
            <item>
                <title>{post.title}</title>
                <link>{url}</link>
                <description>{post.excerpt}</description>
                <pubDate>{post.published_at.strftime('%a, %d %b %Y %H:%M:%S %z') if post.published_at else ''}</pubDate>
                <guid>{url}</guid>
            </item>
            """
        )

    rss_content = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
    <rss version=\"2.0\">
        <channel>
            <title>YD Commercial Cleaning Blog</title>
            <link>{request.build_absolute_uri('/blog/')}</link>
            <description>Latest blog posts and cleaning advice from YD Commercial Cleaning.</description>
            {''.join(feed_items)}
        </channel>
    </rss>
    """

    return HttpResponse(rss_content, content_type="application/rss+xml")


def local_services(request):
    return redirect("local_area_index_default")


def local_area_index(request, letter="a"):
    location_name = "Adelaide"
    current_letter = letter.upper()
    letters = [chr(code) for code in range(ord("A"), ord("Z") + 1)]
    matching_areas = _get_letter_areas(letter)

    services = _get_adelaide_services()
    page_title = f"Adelaide Local Services - {current_letter}"
    page_description = f"Explore cleaning services and suburbs in Adelaide that start with {current_letter}."

    context = {
        "location_name": location_name,
        "page_title": page_title,
        "page_description": page_description,
        "letters": letters,
        "current_letter": current_letter,
        "matching_areas": matching_areas,
        "services": services,
    }
    return render(request, "services/location_index.html", context)


def local_suburb_detail(request, area_slug):
    location_name = "Adelaide"
    suburb = _get_suburb_by_slug(area_slug)
    if not suburb:
        return redirect("local_services")

    services = _get_adelaide_services()
    db_reviews = Review.objects.filter(featured=True).order_by("-created_at")[:3]
    google_reviews = [
        {"reviewer_name": r.customer_name, "review_text": r.review_text}
        for r in db_reviews
    ]

    page_title = f"{suburb['name']} Cleaning Services"
    page_description = f"Professional cleaning services for {suburb['name']}, {location_name}."

    context = {
        "location_name": location_name,
        "suburb_name": suburb["name"],
        "page_title": page_title,
        "page_description": page_description,
        "services": services,
        "google_reviews": google_reviews,
    }
    return render(request, "services/suburb_detail.html", context)


# ====================================================
# SEO Service Page View
# ====================================================


def _normalize_service_slug(service_slug):
    if service_slug.endswith("-adelaide"):
        return service_slug[: -len("-adelaide")]
    return service_slug


def _service_context_from_model(service_obj):
    return {
        "title": service_obj.name,
        "heading": service_obj.name,
        "description": service_obj.description,
        "overview": service_obj.overview,
        "included": service_obj.included or [],
        "packages": service_obj.packages or [],
        "hero_image": service_obj.hero_image.url if service_obj.hero_image else "/static/images/logo.jpeg",
    }


def _service_context_from_definition(service_slug, location_name="Adelaide"):
    definition = SERVICE_DEFINITIONS.get(service_slug)
    if not definition:
        return None
    # Prefer SVG, then WEBP, then JPG static files if they exist under static/images/services
    static_dir = os.path.join(settings.BASE_DIR, "static", "images", "services")
    candidates = [
        f"{service_slug}.svg",
        f"{service_slug}.webp",
        f"{service_slug}.jpg",
    ]

    chosen = None
    for fname in candidates:
        if os.path.exists(os.path.join(static_dir, fname)):
            chosen = fname
            break

    hero_path = f"/static/images/services/{chosen}" if chosen else "/static/images/logo.jpeg"

    return {
        "title": definition["service_name"],
        "heading": definition["service_name"],
        "description": definition["description"].format(location=location_name),
        "overview": definition["overview"].format(location=location_name),
        "included": definition["included"],
        "packages": definition["packages"],
        "hero_image": hero_path,
    }


def service_page(request, service_slug):
    normalized_slug = _normalize_service_slug(service_slug)
    service_obj = Service.objects.filter(slug__iexact=normalized_slug).first()

    if service_obj:
        service = _service_context_from_model(service_obj)
    else:
        service = _service_context_from_definition(normalized_slug)

    if not service:
        return redirect("home")

    service_url = request.build_absolute_uri()
    return render(request, "services/service_detail.html", {"service": service, "service_url": service_url})


# ====================================================
# robots.txt
# Tells search engines what they can crawl
# ====================================================


def robots_txt(request):
    content = """User-agent: *
Allow: /

Sitemap: https://www.ydcleaning.com/sitemap.xml
"""
    return HttpResponse(content, content_type="text/plain")



# ====================================================
# Careers page & application handler
# ====================================================
from django.contrib.auth import get_user_model
from dashboard.models import CareerApplication
from notifications.models import Notification
from .forms import CareerApplicationForm


def careers(request):
    """Render careers page and accept applications."""
    if request.method == "POST":
        form = CareerApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save()

            # notify first admin user if present
            User = get_user_model()
            admin_user = User.objects.filter(is_superuser=True).first()
            if admin_user:
                try:
                    Notification.objects.create(
                        user=admin_user,
                        title=f"New career application: {application.full_name}",
                        message=f"Applicant {application.full_name} submitted an application.",
                        notification_type="system",
                        link="/dashboard/careers/",
                    )
                except Exception:
                    pass

            from django.contrib import messages

            messages.success(request, "✅ Thank you — your application has been received.")
            return redirect("/careers/#applied")
    else:
        form = CareerApplicationForm()

    return render(request, "pages/careers.html", {"form": form})


def terms(request):
    return render(request, "pages/terms.html")


def privacy(request):
    return render(request, "pages/privacy.html")


def legal(request):
    return render(request, "pages/legal.html")


def booking_terms(request):

    return render(
        request,
        "pages/booking_terms.html"
    )