# ====================================================
# YD Commercial Cleaning Services
# File: core/views.py
# Purpose: Handles homepage, contact, services, SEO files
# ====================================================

import copy
import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils.text import slugify

# Local app imports
from .faq_data import FAQ_PAGE_CONFIG
from .suburbs_data import ADELAIDE_SUBURBS
from .seo_data import (
    LOCATION_ALIASES,
    SERVICE_DEFINITIONS,
    SERVICE_SLUG_ALIASES,
)
from .forms import (
    FAQSubmissionForm,
    CareerApplicationForm,
)
from .models import FAQQuestion
from django.core.cache import cache

# External app imports
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

from google_reviews.review_utils import (
    get_google_reviews_api,
    get_public_google_reviews,
)

from bookings.forms import BookingForm
from notifications.models import Notification

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


def _format_faq_value(value, **format_kwargs):
    if isinstance(value, str):
        return value.format(**format_kwargs)
    if isinstance(value, list):
        return [_format_faq_value(item, **format_kwargs) for item in value]
    if isinstance(value, dict):
        return {key: _format_faq_value(item, **format_kwargs) for key, item in value.items()}
    return value


def _get_faq_section(faq_key="generic", **format_kwargs):
    config = FAQ_PAGE_CONFIG.get(faq_key, FAQ_PAGE_CONFIG["generic"])
    section = _format_faq_value(copy.deepcopy(config), **format_kwargs)
    # expose the key so templates can set the submission page_key
    try:
        section["page_key"] = faq_key
    except Exception:
        pass

    return section


def _get_faq_submissions(faq_key="generic"):
    try:
        return FAQQuestion.objects.filter(page_key=faq_key).order_by("-created_at")
    except Exception:
        return FAQQuestion.objects.none()


# ====================================================
# Homepage View
# ====================================================
def home(request):
    gallery_items = GalleryItem.objects.filter(featured=True).order_by("-created_at")[:6]
    featured_reviews = Review.objects.filter(featured=True).order_by("-created_at")[:3]
    featured_services = list(Service.objects.filter(is_active=True).order_by("name")[:6])

    google_reviews = cache.get("homepage_google_reviews")

    if not google_reviews:
        google_reviews = get_public_google_reviews(limit=6)
        cache.set(
            "homepage_google_reviews",
            google_reviews,
            3600
        )
    if not google_reviews:
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
            "services": featured_services,
            "reviews": featured_reviews,
            "google_reviews": google_reviews,
            "average_rating": average_rating,
            "google_review_count": google_review_count,
            "faq_section": _get_faq_section("home"),
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
    services = Service.objects.filter(is_active=True).order_by("name")

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

    rating_values = []
    for review in google_reviews:
        rating = review.get("rating")
        if isinstance(rating, str):
            rating_values.append(rating.count("★") or rating.count("⭐"))
        elif isinstance(rating, (int, float)):
            rating_values.append(float(rating))

    average_rating = round(sum(rating_values) / len(rating_values), 1) if rating_values else 5.0
    google_review_count = len(google_reviews)

    return render(
        request,
        "pages/testimonials.html",
        {
            "testimonials": testimonials,
            "google_reviews": google_reviews,
            "google_review_count": google_review_count,
            "average_rating": average_rating,
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


from .forms import FAQSubmissionForm


def faq(request):
    faq_section = _get_faq_section("faq")
    customer_submissions = _get_faq_submissions("faq")

    if request.method == "POST":
        form = FAQSubmissionForm(request.POST)
        if form.is_valid():
            faq_q = form.save(commit=False)
            faq_q.save()

            # notify admin/staff users
            from django.contrib.auth import get_user_model

            User = get_user_model()
            staff_users = User.objects.filter(is_staff=True, is_active=True)
            for u in staff_users:
                Notification.objects.create(
                    user=u,
                    title="New FAQ submission",
                    message=f"New question submitted: {faq_q.question[:140]}",
                    notification_type="system",
                    link=f"/dashboard/faq-questions/",
                )

            messages.success(request, "✅ Thank you! Your question has been submitted.")
            return redirect("/faq/#community")
        else:
            messages.error(request, "❌ Please check the FAQ form and try again.")
    else:
        form = FAQSubmissionForm(initial={"page_key": "faq"})

    return render(
        request,
        "pages/faq.html",
        {
            "faq_section": faq_section,
            "form": form,
            "customer_submissions": customer_submissions,
        },
    )


def blog(request):
    posts = BlogPost.objects.filter(published=True).order_by("-published_at")
    return render(request, "pages/blog.html", {"posts": posts})


def about(request):
    return render(request, "pages/about.html", {"faq_section": _get_faq_section("about")})


def pricing(request):
    return render(request, "pages/pricing.html")


def team(request):
    return render(request, "pages/team.html")


def corporate(request):
    return render(request, "pages/corporate.html", {"faq_section": _get_faq_section("corporate")})


def insurance(request):
    return render(request, "pages/insurance.html", {"faq_section": _get_faq_section("insurance")})


def referral_program(request):
    return render(request, "pages/referral_program.html", {"faq_section": _get_faq_section("referral_program")})


def eco_friendly_cleaning(request):
    return render(request, "pages/eco_friendly_cleaning.html", {"faq_section": _get_faq_section("eco_friendly_cleaning")})


def emergency_cleaning(request):
    return render(request, "pages/emergency_cleaning.html", {"faq_section": _get_faq_section("emergency_cleaning")})


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
        "faq_section": _get_faq_section(
            "suburb_detail",
            suburb_name=suburb["name"],
            location_name=location_name,
        ),
    }
    return render(request, "services/suburb_detail.html", context)


# ====================================================
# SEO Service Page View
# ====================================================

def _normalize_service_slug(service_slug):
    """
    Convert SEO location service URLs into base service slugs.

    Examples:
    end-of-lease-cleaning-north-adelaide
        -> end-of-lease-cleaning

    carpet-steam-cleaning-norwood
        -> carpet-steam-cleaning
    """

    slug = service_slug.lower().strip("-")

    # Remove full suburb names first (north-adelaide, glenelg, etc.)
    location_slugs = set(LOCATION_ALIASES.keys())


    for areas in ADELAIDE_SUBURBS.values():
        for area in areas:
            location_slugs.add(_slugify_area(area))


    location_slugs = sorted(
        location_slugs,
        key=len,
        reverse=True
    )

    for location_slug in location_slugs:
        if slug.endswith(f"-{location_slug}"):
            slug = slug[:-(len(location_slug) + 1)]
            break

    # Remove Adelaide suffix if still present
    if slug.endswith("-adelaide"):
        slug = slug[:-len("-adelaide")]

    normalized = SERVICE_SLUG_ALIASES.get(slug, slug)

    # Match existing service database slugs
    if Service.objects.filter(slug=normalized).exists():
        return normalized


    # Try Adelaide suffix
    adelaide_slug = f"{normalized}-adelaide"

    if Service.objects.filter(slug=adelaide_slug).exists():
        return adelaide_slug


    return normalized


def _get_location_from_slug(slug):
    """
    Extract suburb/location from SEO URL slug.

    Example:
    carpet-steam-cleaning-north-adelaide
    -> North Adelaide
    """

    slug = slug.lower().strip("-")


    # 1. Check SEO aliases first
    for location_slug, location_name in sorted(
        LOCATION_ALIASES.items(),
        key=lambda x: len(x[0]),
        reverse=True
    ):
        if slug.endswith(location_slug):
            return location_name


    # 2. Fallback: check ADELAIDE_SUBURBS database
    for areas in ADELAIDE_SUBURBS.values():

        for area in areas:

            suburb_slug = _slugify_area(area)

            if slug.endswith(suburb_slug):
                return area["name"]


    # 3. Remove Adelaide suffix
    if slug.endswith("-adelaide"):
        return "Adelaide"


    return "Adelaide"


def _normalize_related_services(related_services):
    normalized = []
    for item in related_services or []:
        if isinstance(item, dict):
            slug = item.get("slug") or item.get("service_slug") or item.get("name") or ""
            label = item.get("label") or item.get("title") or item.get("name") or slug.replace("-", " ").title()
        else:
            slug = str(item).strip()
            label = slug.replace("-", " ").title()
        if slug:
            normalized.append({"slug": slug, "label": label})
    return normalized


def _service_context_from_model(service_obj):
    return {
        "title": service_obj.name,
        "heading": service_obj.name,
        "description": service_obj.description,
        "overview": service_obj.overview,
        "included": service_obj.included or [],
        "packages": service_obj.packages or [],
        "hero_image": service_obj.hero_image.url if getattr(service_obj, 'hero_image', None) else "/static/images/logo.jpeg",
        # Rich optional fields — provide safe defaults so templates can render consistently
        "gallery": getattr(service_obj, "gallery_images", []) or [],
        "problems": getattr(service_obj, "problems", []) or [],
        "process": getattr(service_obj, "process_steps", []) or [],
        "benefits": getattr(service_obj, "benefits", []) or [],
        "ideal_for": getattr(service_obj, "ideal_for", []) or [],
        "industries": getattr(service_obj, "industries", []) or [],
        "faqs": getattr(service_obj, "faqs", []) or [],
        "related_services": _normalize_related_services(getattr(service_obj, "related_services", []) or []),
        "locations": getattr(service_obj, "locations", []) or [],
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

    # Build a rich context merging available definition fields and sensible defaults
    return {
        "title": definition.get("title", definition.get("service_name", "Cleaning Service")),
        "heading": definition.get("heading", definition.get("service_name", "Cleaning Service")),
        "description": definition.get("description", definition.get("overview", "")).format(location=location_name, suburb=location_name) if definition.get("description") else "",
        "overview": definition.get("overview", "").format(location=location_name) if definition.get("overview") else "",
        "meta_description": definition.get("meta_description", definition.get("description", "")).format(location=location_name) if definition.get("meta_description") or definition.get("description") else "",
        "introduction": definition.get("introduction", definition.get("overview", "")).format(location=location_name) if definition.get("introduction") or definition.get("overview") else "",
        "included": definition.get("included", []),
        "packages": definition.get("packages", []),
        "hero_image": definition.get("hero_image", hero_path),
        "image_alt": definition.get("image_alt", f"{definition.get('title', definition.get('service_name', 'Cleaning Service'))} in {location_name}, Adelaide"),
        "gallery": definition.get("gallery", []),
        "problems": definition.get("problems", []),
        "process": definition.get("process", []),
        "benefits": definition.get("benefits", []),
        "ideal_for": definition.get("ideal_for", []),
        "industries": definition.get("industries", []),
        "faqs": definition.get("faqs", []),
        "related_services": _normalize_related_services(definition.get("related_services", [])),
        "locations": definition.get("locations", [location_name]),
    }


def _get_service_google_reviews(limit=6):
    google_reviews = get_public_google_reviews(limit=limit)
    if not google_reviews:
        google_reviews = get_google_reviews_api()
    if not google_reviews:
        recent_reviews = Review.objects.order_by("-created_at")[:limit]
        google_reviews = [
            {
                "reviewer_name": review.customer_name,
                "review_text": review.review_text,
                "rating": getattr(review, "stars", lambda: None)(),
            }
            for review in recent_reviews
        ]
    return google_reviews


def service_page(request, service_slug):

    normalized_slug = _normalize_service_slug(service_slug)
    path_slug = service_slug.lower().strip("-")
    location = _get_location_from_slug(path_slug)

    slug_candidates = [normalized_slug]
    if path_slug != normalized_slug:
        slug_candidates.append(path_slug)
    if not normalized_slug.endswith("-adelaide"):
        slug_candidates.append(f"{normalized_slug}-adelaide")

    service_obj = Service.objects.filter(
        slug__in=slug_candidates
    ).first()

    if service_obj:
        service = _service_context_from_model(service_obj)
    else:
        service = _service_context_from_definition(normalized_slug)

    if not service:
        raise Http404("Service not found")

    service_url = f"{settings.SITE_URL}{request.path}"
    google_reviews = _get_service_google_reviews(limit=6)

    rating_values = []
    for review in google_reviews:
        rating = review.get("rating")
        if isinstance(rating, int):
            rating_values.append(rating)
        elif isinstance(rating, str):
            rating_values.append(rating.count("★") or rating.count("⭐"))

    service_review_count = len(google_reviews)
    service_average_rating = round(sum(rating_values) / len(rating_values), 1) if rating_values else 5.0

    return render(
        request,
        "services/service_detail.html",
        {
            "service": service,
            "service_url": service_url,
            "location": location,
            "google_reviews": google_reviews,
            "service_review_count": service_review_count,
            "service_average_rating": service_average_rating,
            "faq_section": _get_faq_section(
                "service_detail",
                service_title=service["title"],
                location_name=location,
            ),
        }
    )

# ====================================================
# robots.txt
# Tells search engines what they can crawl
# ====================================================


def robots_txt(request):
    content = render_to_string("robots.txt", {"site_url": settings.SITE_URL})
    return HttpResponse(content, content_type="text/plain; charset=utf-8")

# ====================================================
# Careers page & application handler
# ====================================================


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

    return render(request, "pages/careers.html", {"form": form, "faq_section": _get_faq_section("careers")})


def terms(request):
    return render(request, "pages/terms.html", {"faq_section": _get_faq_section("terms")})


def privacy(request):
    return render(request, "pages/privacy.html", {"faq_section": _get_faq_section("privacy")})


def legal(request):
    return render(request, "pages/legal.html")


def booking_terms(request):

    return render(
        request,
        "pages/booking_terms.html",
        {"faq_section": _get_faq_section("booking_terms")},
    )






def booking(request):
    if request.method == "POST":
        form = BookingForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Your booking request has been submitted successfully."
            )

            return redirect("home")

    else:
        form = BookingForm()

    return render(
        request,
        "bookings/public_booking.html",
        {
            "form": form
        }
    )

