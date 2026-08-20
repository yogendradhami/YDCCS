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
from django.db import transaction
from django.shortcuts import redirect, render
from django.core.mail import send_mail
from django.conf import settings
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils.text import slugify
from .models import FAQQuestion, TeamMember

# Local app imports
from .faq_data import FAQ_PAGE_CONFIG
from .suburbs_data import ADELAIDE_SUBURBS
from .seo_data import (
    LOCATION_ALIASES,
    SERVICE_DEFINITIONS,
    SERVICE_SLUG_ALIASES,
    get_location_definition,
)
from .forms import (
    FAQSubmissionForm,
    CareerApplicationForm,
)
from .models import FAQQuestion
from django.core.cache import cache
from django.shortcuts import render

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
from .models import TestimonialVideo

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
        form = QuoteRequestForm(request.POST, request.FILES, request=request)

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

            uploaded_images = form.cleaned_data.get("property_images", [])

            try:
                with transaction.atomic():
                    quote.save()

                    for image in uploaded_images:
                        QuoteImage.objects.create(quote=quote, image=image)

                customer_email_sent = send_customer_quote_email(quote)
                admin_email_sent = send_admin_quote_email(quote)

                if not customer_email_sent:
                    print("WARNING: Customer quote email was not sent.")

                if not admin_email_sent:
                    print("WARNING: Admin quote email was not sent.")

                messages.success(
                    request,
                    f"✅ Thank you! Your quote request has been submitted successfully. Estimated price: ${quote.estimated_price}. Our team will confirm the final price shortly.",
                )

                return redirect("/#quote")

            except Exception as error:
                form.add_error(
                    "property_images",
                    "One or more uploaded images could not be processed. Please try again with a valid image file.",
                )

        messages.error(request, "❌ Please check the form and try again.")

    else:
        form = QuoteRequestForm(request=request)

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
    """
    Testimonials page.

    Google reviews stored in the database are used as the
    primary public source. The live Google API is used as
    a fallback when no database reviews are available.
    """

    # ---------------------------------------------------------
    # GOOGLE REVIEWS
    # ---------------------------------------------------------

    google_reviews = get_public_google_reviews(limit=100)

    # If there are no stored reviews, try the live Google API.
    if not google_reviews:
        google_reviews = get_google_reviews_api()

    # ---------------------------------------------------------
    # FEATURED TESTIMONIALS
    # ---------------------------------------------------------

    featured_reviews = (
        Review.objects
        .filter(featured=True)
        .order_by("-created_at")
    )

    testimonials = [
        {
            "reviewer_name": review.customer_name,
            "review_text": review.review_text,
            "rating": review.stars(),
            "suburb": review.suburb,
        }
        for review in featured_reviews
    ]

    # ---------------------------------------------------------
    # TESTIMONIAL VIDEOS
    # ---------------------------------------------------------

    testimonial_videos = (
        TestimonialVideo.objects
        .filter(active=True)
        .order_by("-created_at")
    )

    # ---------------------------------------------------------
    # GOOGLE RATING CALCULATION
    # ---------------------------------------------------------

    rating_values = []

    for review in google_reviews:
        rating = review.get("rating", "")

        if isinstance(rating, str):
            numeric_rating = (
                rating.count("⭐")
                or rating.count("★")
            )

            if numeric_rating:
                rating_values.append(numeric_rating)

        elif isinstance(rating, (int, float)):
            rating_values.append(float(rating))

    average_rating = (
        round(
            sum(rating_values) / len(rating_values),
            1
        )
        if rating_values
        else 5.0
    )

    google_review_count = len(google_reviews)

    # ---------------------------------------------------------
    # RENDER PAGE
    # ---------------------------------------------------------

    return render(
        request,
        "pages/testimonials.html",
        {
            "testimonials": testimonials,
            "google_reviews": google_reviews,
            "google_review_count": google_review_count,
            "average_rating": average_rating,
            "testimonial_videos": testimonial_videos,
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
    team_members = (
        TeamMember.objects
        .filter(is_active=True)
        .order_by("display_order", "name")
    )

    return render(
        request,
        "pages/team.html",
        {
            "team_members": team_members,
        },
    )


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

def _get_canonical_service_redirect_path(service_slug):
    """
    Redirect legacy /services/<service>-<location>/ URLs to the canonical
    /services/<service>-adelaide-<location>/ form.
    """
    slug = (service_slug or "").lower().strip("-")
    if not slug:
        return None

    if slug.endswith("-adelaide"):
        return None

    for location_slug in sorted(LOCATION_ALIASES, key=len, reverse=True):
        if slug.endswith(f"-adelaide-{location_slug}"):
            return None

    for location_slug in sorted(LOCATION_ALIASES, key=len, reverse=True):
        suffix = f"-{location_slug}"
        if slug.endswith(suffix) and not slug.endswith(f"-adelaide-{location_slug}"):
            base_slug = slug[: -len(suffix)]
            canonical_slug = f"{base_slug}-adelaide-{location_slug}"
            if canonical_slug:
                return f"/services/{canonical_slug}/"

    return None


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
        f"{service_slug}.webp",
        f"{service_slug}.jpg",
        f"{service_slug}.svg",
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
        "location_content": definition.get("location_content", {}).get(
            location_name.lower().replace(" ", "-"),
            ""
        ),
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

def legacy_service_redirect(request, service_slug):
    canonical_path = _get_canonical_service_redirect_path(service_slug)
    if canonical_path:
        return redirect(canonical_path, permanent=True)
    return redirect(
        f"/services/{service_slug}/",
        permanent=True
    )


def _get_why_choose_context(request, service=None, location=None, suburb_name=None):
    """
    Build page-specific content for the globally rendered
    'Why Choose YD Commercial Cleaning?' section.

    The section remains reusable across the site while its
    messaging changes according to the current page/service.
    """

    path = request.path.lower()

    # ----------------------------------------------------
    # Service-specific content
    # ----------------------------------------------------
    if service:
        service_title = service.get("title") or service.get("heading") or ""
        service_name = service_title.replace(" Adelaide", "").strip()
        service_key = service_name.lower()

        service_profiles = {
            "commercial cleaning": {
                "heading": "Why Choose YD for Commercial Cleaning?",
                "intro": (
                    "Reliable commercial cleaning for Adelaide businesses, "
                    "with professional teams, flexible scheduling and "
                    "consistent cleaning standards."
                ),
                "cards": [
                    {
                        "icon": "🏢",
                        "title": "Business-Focused Cleaning",
                        "text": (
                            "Cleaning plans designed for offices, retail spaces, "
                            "warehouses and other commercial properties across Adelaide."
                        ),
                    },
                    {
                        "icon": "🛡️",
                        "title": "Fully Insured Teams",
                        "text": (
                            "Work with a professional cleaning team backed by "
                            "appropriate insurance and clear service standards."
                        ),
                    },
                    {
                        "icon": "📅",
                        "title": "Flexible Scheduling",
                        "text": (
                            "Daily, weekly or scheduled commercial cleaning "
                            "arranged around your business operations."
                        ),
                    },
                    {
                        "icon": "✅",
                        "title": "Consistent Quality",
                        "text": (
                            "A structured cleaning process with quality checks "
                            "to help maintain a consistently professional workplace."
                        ),
                    },
                    {
                        "icon": "💬",
                        "title": "Clear Communication",
                        "text": (
                            "Straightforward quotes, responsive communication "
                            "and clear expectations before cleaning begins."
                        ),
                    },
                    {
                        "icon": "📍",
                        "title": "Local Adelaide Service",
                        "text": (
                            "A local cleaning team serving businesses across "
                            "Adelaide and surrounding areas."
                        ),
                    },
                ],
            },

            "office cleaning": {
                "heading": "Why Choose YD for Office Cleaning?",
                "intro": (
                    "Keep your Adelaide workplace clean, hygienic and professional "
                    "with dependable office cleaning tailored around your team."
                ),
                "cards": [
                    {
                        "icon": "🧑‍💼",
                        "title": "Professional Workplaces",
                        "text": (
                            "Detailed cleaning for workstations, meeting rooms, "
                            "shared areas, kitchens and staff spaces."
                        ),
                    },
                    {
                        "icon": "🧼",
                        "title": "Hygiene-Focused Cleaning",
                        "text": (
                            "Regular cleaning and sanitisation of high-touch "
                            "and shared workplace areas."
                        ),
                    },
                    {
                        "icon": "🌙",
                        "title": "After-Hours Options",
                        "text": (
                            "Flexible scheduling can help minimise disruption "
                            "to your staff, customers and daily operations."
                        ),
                    },
                    {
                        "icon": "📋",
                        "title": "Structured Service",
                        "text": (
                            "Consistent cleaning routines and quality checks "
                            "help maintain your workplace to a professional standard."
                        ),
                    },
                    {
                        "icon": "🛡️",
                        "title": "Fully Insured",
                        "text": (
                            "Choose a professional cleaning provider with "
                            "appropriate insurance and service standards."
                        ),
                    },
                    {
                        "icon": "📍",
                        "title": "Adelaide Local Team",
                        "text": (
                            "Reliable office cleaning services for workplaces "
                            "across Adelaide and surrounding suburbs."
                        ),
                    },
                ],
            },

            "end of lease cleaning": {
                "heading": "Why Choose YD for End of Lease Cleaning?",
                "intro": (
                    "Move out with confidence with detailed end of lease cleaning "
                    "for Adelaide tenants, landlords and property managers."
                ),
                "cards": [
                    {
                        "icon": "🏠",
                        "title": "Inspection-Focused Cleaning",
                        "text": (
                            "Detailed cleaning of kitchens, bathrooms, floors, "
                            "surfaces and other areas commonly checked during inspections."
                        ),
                    },
                    {
                        "icon": "🧽",
                        "title": "Deep Kitchen & Bathroom Cleaning",
                        "text": (
                            "Targeted cleaning for grease, grime, bathrooms, "
                            "fixtures, tiles and other high-use areas."
                        ),
                    },
                    {
                        "icon": "🧹",
                        "title": "Detailed Property Cleaning",
                        "text": (
                            "Attention to floors, skirting, walls, windows and "
                            "other areas that can affect the final presentation."
                        ),
                    },
                    {
                        "icon": "📋",
                        "title": "Clear Cleaning Process",
                        "text": (
                            "A structured approach helps make sure important "
                            "areas are covered before your property handover."
                        ),
                    },
                    {
                        "icon": "⏱️",
                        "title": "Flexible Scheduling",
                        "text": (
                            "Cleaning appointments organised around your moving "
                            "date and property handover requirements."
                        ),
                    },
                    {
                        "icon": "💬",
                        "title": "Transparent Quotes",
                        "text": (
                            "Clear pricing and service expectations before the "
                            "cleaning team starts work."
                        ),
                    },
                ],
            },

            "bond cleaning": {
                "heading": "Why Choose YD for Bond Cleaning?",
                "intro": (
                    "Detailed Adelaide bond cleaning designed to help tenants "
                    "prepare their rental property for inspection and handover."
                ),
                "cards": [
                    {
                        "icon": "🔎",
                        "title": "Inspection Ready",
                        "text": (
                            "Focused cleaning of the areas landlords and property "
                            "managers commonly inspect."
                        ),
                    },
                    {
                        "icon": "🍳",
                        "title": "Kitchen Deep Cleaning",
                        "text": (
                            "Detailed cleaning for ovens, appliances, benches, "
                            "cupboards and kitchen surfaces."
                        ),
                    },
                    {
                        "icon": "🚿",
                        "title": "Bathroom Detail",
                        "text": (
                            "Bathrooms receive focused attention to surfaces, "
                            "fixtures, tiles and grout."
                        ),
                    },
                    {
                        "icon": "🧹",
                        "title": "Whole-Property Cleaning",
                        "text": (
                            "Floors, walls, skirting, windows and other key areas "
                            "are included according to your cleaning requirements."
                        ),
                    },
                    {
                        "icon": "📅",
                        "title": "Move-Out Scheduling",
                        "text": (
                            "Flexible appointments to work around your moving "
                            "and property handover timeline."
                        ),
                    },
                    {
                        "icon": "🛡️",
                        "title": "Professional Service",
                        "text": (
                            "A reliable local cleaning team focused on detailed "
                            "results and clear communication."
                        ),
                    },
                ],
            },
        }

        profile = service_profiles.get(service_key)

        if profile:
            return profile

        # ------------------------------------------------
        # Generic service fallback
        # Uses existing SEO/service data where possible.
        # ------------------------------------------------
        benefits = service.get("benefits") or []
        included = service.get("included") or []

        cards = [
            {
                "icon": "🛡️",
                "title": "Fully Insured Cleaning",
                "text": (
                    "Professional cleaning delivered with appropriate insurance "
                    "and clear service standards."
                ),
            },
            {
                "icon": "📍",
                "title": f"Local {location or 'Adelaide'} Service",
                "text": (
                    f"Reliable {service_name.lower()} delivered by a local team "
                    f"serving {location or 'Adelaide'} and surrounding areas."
                ),
            },
            {
                "icon": "🧹",
                "title": "Detailed Cleaning Process",
                "text": (
                    "A structured approach focused on the cleaning requirements "
                    "of your property and service."
                ),
            },
            {
                "icon": "📅",
                "title": "Flexible Scheduling",
                "text": (
                    "Appointments arranged around your property, business, "
                    "rental or project requirements."
                ),
            },
            {
                "icon": "💬",
                "title": "Transparent Communication",
                "text": (
                    "Clear quotes and straightforward communication before "
                    "your cleaning service begins."
                ),
            },
            {
                "icon": "⭐",
                "title": "Quality-Focused Results",
                "text": (
                    "We focus on delivering a thorough, professional result "
                    "suited to your cleaning requirements."
                ),
            },
        ]

        # If the service has meaningful benefits, use one as a subtle
        # service-specific supporting card.
        if benefits:
            cards[-1]["text"] = (
                f"{benefits[0]}. Our team combines this service requirement "
                "with a professional, detail-focused cleaning approach."
            )

        return {
            "heading": f"Why Choose YD for {service_name}?",
            "intro": (
                f"Professional {service_name.lower()} for "
                f"{location or 'Adelaide'}, delivered by a reliable local "
                "cleaning team with a focus on quality and service."
            ),
            "cards": cards,
        }

    # ----------------------------------------------------
    # Suburb/local page
    # ----------------------------------------------------
    if suburb_name:
        return {
            "heading": f"Why Choose YD Cleaning in {suburb_name}?",
            "intro": (
                f"Looking for reliable cleaning services in {suburb_name}, Adelaide? "
                "YD Commercial Cleaning provides professional, locally focused "
                "cleaning for homes, businesses and rental properties."
            ),
            "cards": [
                {
                    "icon": "📍",
                    "title": f"Local {suburb_name} Service",
                    "text": (
                        f"Professional cleaning services for homes and businesses "
                        f"in {suburb_name} and nearby Adelaide suburbs."
                    ),
                },
                {
                    "icon": "🛡️",
                    "title": "Fully Insured Team",
                    "text": (
                        "Book with confidence with a professional cleaning team "
                        "committed to safe and reliable service."
                    ),
                },
                {
                    "icon": "🧹",
                    "title": "Professional Cleaning",
                    "text": (
                        "Detailed cleaning options for residential, commercial "
                        "and rental properties."
                    ),
                },
                {
                    "icon": "⏱️",
                    "title": "Flexible Scheduling",
                    "text": (
                        "Convenient cleaning appointments arranged around your "
                        "home, workplace or property requirements."
                    ),
                },
                {
                    "icon": "💬",
                    "title": "Clear Quotes",
                    "text": (
                        "Straightforward communication and transparent service "
                        "expectations before work begins."
                    ),
                },
                {
                    "icon": "⭐",
                    "title": "Quality-Focused Service",
                    "text": (
                        "We focus on reliable results and a professional customer "
                        "experience from booking through completion."
                    ),
                },
            ],
        }

    # ----------------------------------------------------
    # Special site pages
    # ----------------------------------------------------
    page_profiles = {
        "/insurance/": {
            "heading": "Why Choose YD for Safe & Reliable Cleaning?",
            "intro": (
                "Professional cleaning backed by clear service standards, "
                "insurance and a strong commitment to customer confidence."
            ),
        },
        "/emergency-cleaning/": {
            "heading": "Why Choose YD for Emergency Cleaning?",
            "intro": (
                "When unexpected cleaning problems need attention, our Adelaide "
                "team focuses on responsive communication and practical solutions."
            ),
        },
        "/eco-friendly-cleaning/": {
            "heading": "Why Choose YD for Eco-Friendly Cleaning?",
            "intro": (
                "Thoughtful cleaning practices designed to maintain a high "
                "standard of cleanliness while considering people and the environment."
            ),
        },
    }

    profile = next(
        (
            profile
            for page_path, profile in page_profiles.items()
            if path.startswith(page_path)
        ),
        None,
    )

    if profile:
        return {
            **profile,
            "cards": [
                {
                    "icon": "🛡️",
                    "title": "Professional Standards",
                    "text": "Reliable cleaning delivered with clear processes and professional service standards.",
                },
                {
                    "icon": "📍",
                    "title": "Local Adelaide Team",
                    "text": "A local cleaning provider serving Adelaide homes, businesses and properties.",
                },
                {
                    "icon": "🧹",
                    "title": "Detailed Results",
                    "text": "Cleaning focused on the specific requirements of your property and service.",
                },
                {
                    "icon": "💬",
                    "title": "Clear Communication",
                    "text": "Straightforward quotes, booking information and communication throughout your service.",
                },
                {
                    "icon": "📅",
                    "title": "Flexible Scheduling",
                    "text": "Cleaning appointments arranged around your property and scheduling requirements.",
                },
                {
                    "icon": "⭐",
                    "title": "Customer Focused",
                    "text": "We aim to provide a dependable experience and professional cleaning results.",
                },
            ],
        }

    # ----------------------------------------------------
    # Default global fallback
    # ----------------------------------------------------
    return {
        "heading": "Why Choose YD Commercial Cleaning?",
        "intro": (
            "Trusted Adelaide cleaning specialists providing professional, "
            "reliable and detail-focused cleaning for homes, businesses and properties."
        ),
        "cards": [
            {
                "icon": "🛡️",
                "title": "Fully Insured Cleaning",
                "text": "Professional cleaning backed by appropriate insurance and clear service standards.",
            },
            {
                "icon": "📍",
                "title": "Reliable Local Team",
                "text": "A local Adelaide cleaning team focused on dependable service and professional results.",
            },
            {
                "icon": "⭐",
                "title": "Quality-Focused Results",
                "text": "A detail-focused approach designed around the requirements of your property.",
            },
            {
                "icon": "⏱️",
                "title": "Flexible Scheduling",
                "text": "Convenient booking options for homes, businesses, rental properties and commercial sites.",
            },
            {
                "icon": "💬",
                "title": "Transparent Communication",
                "text": "Clear quotes and straightforward communication so you know what to expect.",
            },
            {
                "icon": "🧹",
                "title": "Tailored Cleaning Plans",
                "text": "Cleaning services adapted to your property, schedule and specific requirements.",
            },
        ],
    }





def service_page(request, service_slug):

    canonical_redirect = _get_canonical_service_redirect_path(service_slug)
    if canonical_redirect and request.path.rstrip("/") != canonical_redirect.rstrip("/"):
        return redirect(canonical_redirect, permanent=True)

    normalized_slug = _normalize_service_slug(service_slug)
    path_slug = service_slug.lower().strip("-")
    location = _get_location_from_slug(path_slug)
    location_slug = None

    for slug, name in sorted(
        LOCATION_ALIASES.items(),
        key=lambda x: len(x[0]),
        reverse=True
    ):
        if path_slug.endswith(slug):
            location_slug = slug
            break

    location_definition = (
        get_location_definition(location_slug)
        if location_slug
        else get_location_definition("adelaide")
    )

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
            "location_definition": location_definition,
            "why_choose": _get_why_choose_context(
                request,
                service=service,
                location=location,
            ),

            "google_reviews": google_reviews,
            "service_review_count": service_review_count,
            "service_average_rating": service_average_rating,
            "hide_default_faq": True,
            "faq_section": _get_faq_section(
                "service_detail",
                service_title=service["title"].replace(" Adelaide", ""),
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
        # Translate incoming public form fields to match the internal ModelForm
        post = request.POST.copy()

        pos_map = {
            "residential-cleaner": "residential_cleaner",
            "commercial-cleaner": "commercial_cleaner",
            "specialist-cleaner": "specialist_cleaner",
            "cleaning-team-leader": "team_leader",
            "other": "general_application",
        }
        if "position" in post:
            post["position"] = pos_map.get(post.get("position", ""), post.get("position", ""))

        emp_map = {"part-time": "part_time", "full-time": "full_time", "contract": "contractor"}
        if "employment_type" in post:
            post["employment_type"] = emp_map.get(post.get("employment_type", ""), post.get("employment_type", ""))

        exp_map = {"none": "0", "less-than-1": "0", "1-2": "1", "3-5": "3", "5-plus": "5"}
        if "experience_years" in post:
            post["years_cleaning_experience"] = exp_map.get(post.get("experience_years", ""), "")

        if "availability" in post:
            post["availability_days"] = post.get("availability", "")
        if "preferred_hours" in post:
            post["availability_hours"] = post.get("preferred_hours", "")

        working_days = request.POST.getlist("working_days")
        if working_days:
            existing = post.get("availability_days", "")
            joined = ", ".join(working_days)
            post["availability_days"] = (existing + ", " + joined).strip(", ") if existing else joined

        dl = post.get("drivers_license") or post.get("drivers_license", "")
        if dl:
            post["has_drivers_license"] = "yes" == dl
        veh = post.get("vehicle") or post.get("vehicle", "")
        if veh:
            post["has_vehicle"] = "yes" == veh

        wr_map = {"permanent-resident": "permanent_resident", "visa": "visa_holder"}
        if "work_rights" in post:
            post["work_rights"] = wr_map.get(post.get("work_rights", ""), post.get("work_rights", ""))

        if "experience" in post:
            post["previous_cleaning_experience"] = post.get("experience")

        form = CareerApplicationForm(post, request.FILES)
        if form.is_valid():
            application = form.save()

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

            # Send templated confirmation email
            try:
                subject = "YD Commercial Cleaning — Application Received"
                context = {"application": application}
                text = render_to_string("emails/application_received.txt", context)
                html = render_to_string("emails/application_received.html", context)
                send_mail(subject, text, settings.DEFAULT_FROM_EMAIL, [application.email], html_message=html)
            except Exception:
                pass

            messages.success(request, "✅ Thank you — your application has been received.")
            return redirect("/careers/#applied")
        else:
            # surface validation errors to the user via messages (template already shows messages)
            try:
                err_items = []
                for k, v in form.errors.items():
                    err_items.append(f"{k}: {', '.join(v)}")
                messages.error(request, "There were errors with your submission: " + "; ".join(err_items))
            except Exception:
                messages.error(request, "There were errors with your submission. Please check the form fields.")
            # fall through to re-render form with posted data (form contains errors)
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

def cleaning_services_video(request):
    return render(
        request,
        "videos/cleaning_services_adelaide.html"
    )