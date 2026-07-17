# ====================================================
# YD Commercial Cleaning Services
# File: core/views.py
# Purpose: Handles homepage, contact, services, SEO files
# ====================================================

<<<<<<< HEAD
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render

from gallery.models import GalleryItem
from quotes.email_service import (
    send_admin_quote_email,
    send_customer_quote_email,
)
from quotes.forms import QuoteRequestForm
from quotes.models import QuoteImage
from reviews.models import Review
=======
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponse
from django.utils.feedgenerator import Rss201rev2Feed
from django.utils.text import slugify

from quotes.forms import QuoteRequestForm
from quotes.models import QuoteImage
from quotes.email_service import (
    send_customer_quote_email,
    send_admin_quote_email,
)
from gallery.models import GalleryItem
from reviews.models import Review
from google_reviews.models import GoogleReview
from services.models import Service
from blog.models import BlogPost
from .seo_data import LOCATION_ALIASES
from .suburbs_data import ADELAIDE_SUBURBS


def get_location_from_slug(service_slug):
    for location_slug, location_name in LOCATION_ALIASES.items():
        if service_slug.endswith(f"-{location_slug}"):
            return location_slug, location_name
    return "adelaide", "Adelaide"


def get_base_slug(service_slug, location_slug):
    if service_slug.endswith(f"-{location_slug}"):
        return service_slug[: -len(location_slug) - 1]
    return service_slug


def get_active_service_by_slug(base_slug):
    return Service.objects.filter(slug=base_slug, is_active=True).first()


def build_service_dict_from_model(service_obj, location_name="Adelaide"):
    if not service_obj:
        return None

    service_slug = f"{service_obj.slug}-{location_name.lower().replace(' ', '-') }"
    return {
        "name": service_obj.name,
        "description": service_obj.description,
        "overview": service_obj.overview,
        "url": reverse('service_page_services', kwargs={'service_slug': service_slug}),
        "slug": service_slug,
        "service_name": service_obj.name,
        "icon": "🧼",
        "popular_package": service_obj.packages[0] if service_obj.packages else None,
        "hero_image": service_obj.hero_image.url if service_obj.hero_image else None,
        "included": service_obj.included,
        "packages": service_obj.packages,
    }


def get_service_listing(location_name="Adelaide", description_location=None):
    if description_location is None:
        description_location = location_name

    active_services = Service.objects.filter(is_active=True).order_by("name")
    return [build_service_dict_from_model(service, location_name) for service in active_services]


def service_page_redirect(request, service_slug):
    location_slug, location_name = get_location_from_slug(service_slug)
    base_slug = get_base_slug(service_slug, location_slug)

    service_obj = get_active_service_by_slug(base_slug)
    if not service_obj:
        return redirect("home")

    return redirect(
        "service_page_services",
        service_slug=service_slug,
        permanent=True,
    )
>>>>>>> 5815f15 (Initial project commit)


# ====================================================
# Homepage View
# ====================================================
def home(request):
<<<<<<< HEAD
    gallery_items = GalleryItem.objects.filter(featured=True).order_by("-created_at")[
        :6
    ]
    reviews = Review.objects.filter(featured=True).order_by("-created_at")[:3]
=======
    gallery_items = GalleryItem.objects.filter(featured=True).order_by("-created_at")[:6]
    reviews = Review.objects.filter(featured=True).order_by("-created_at")[:3]
    # Google reviews synced from Google Business Profile
    google_reviews = GoogleReview.objects.order_by(
        "-review_date"
    )[:6]
    google_review_count = GoogleReview.objects.count()


>>>>>>> 5815f15 (Initial project commit)

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
<<<<<<< HEAD
                QuoteImage.objects.create(quote=quote, image=image)
=======
                QuoteImage.objects.create(
                    quote=quote,
                    image=image
                )
>>>>>>> 5815f15 (Initial project commit)

            try:
                send_customer_quote_email(quote)
                send_admin_quote_email(quote)
            except Exception as error:
                print("Email sending failed:", error)

            messages.success(
                request,
<<<<<<< HEAD
                f"✅ Thank you! Your quote request has been submitted successfully. Estimated price: ${quote.estimated_price}. Our team will confirm the final price shortly.",
=======
                f"✅ Thank you! Your quote request has been submitted successfully. Estimated price: ${quote.estimated_price}. Our team will confirm the final price shortly."
>>>>>>> 5815f15 (Initial project commit)
            )

            return redirect("/#quote")

        messages.error(request, "❌ Please check the form and try again.")

    else:
        form = QuoteRequestForm()

    return render(
        request,
<<<<<<< HEAD
        "home.html",
=======
        "core/home.html",
>>>>>>> 5815f15 (Initial project commit)
        {
            "form": form,
            "gallery_items": gallery_items,
            "reviews": reviews,
<<<<<<< HEAD
        },
    )

=======
            "page_title": "YD Commercial Cleaning Services Adelaide",
            "page_description": "Professional commercial and residential cleaning services across Adelaide and South Australia. Fast quotes, reliable teams and fully insured cleaners.",
            "page_keywords": "Adelaide cleaning service, commercial cleaning Adelaide, office cleaning Adelaide, end of lease cleaning Adelaide, window cleaning Adelaide, house cleaning Adelaide",
            # Google Reviews
            "google_reviews": google_reviews,
            "google_review_count": google_review_count,
        },
    )

# ====================================================
# Services Listing Page View
# ====================================================

def services_page(request):
    default_location = "Adelaide"
    services = []
    icon_map = {
        "commercial-cleaning": "🏢",
        "office-cleaning": "🧹",
        "end-of-lease-cleaning": "🔑",
        "bond-cleaning": "🔒",
        "house-cleaning": "🏠",
        "regular-house-cleaning": "🏡",
        "window-cleaning": "🪟",
        "carpet-steam-cleaning": "🧼",
        "builders-cleaning": "🚧",
        "post-construction-cleaning": "🧱",
        "pressure-washing": "💦",
        "bathroom-cleaning": "🚿",
        "kitchen-cleaning": "🍳",
        "deep-cleaning": "🧽",
        "move-in-cleaning": "📦",
        "move-out-cleaning": "🚚",
        "spring-cleaning": "🌸",
    }

    service_queryset = Service.objects.filter(is_active=True).order_by("name")
    for service_obj in service_queryset:
        base_slug = service_obj.slug
        service_slug = f"{base_slug}-{default_location.lower()}"
        services.append({
            "name": service_obj.name,
            "description": service_obj.description,
            "overview": service_obj.overview,
            "url": reverse('service_page_services', kwargs={'service_slug': service_slug}),
            "slug": service_slug,
            "service_name": service_obj.name,
            "icon": icon_map.get(base_slug, "🧼"),
            "popular_package": service_obj.packages[0] if service_obj.packages else None,
            "hero_image": service_obj.hero_image.url if service_obj.hero_image else None,
        })

    google_reviews = GoogleReview.objects.order_by("-review_date")[:4]

    return render(request, "services/services_list.html", {
        "services": services,
        "page_title": "Adelaide Cleaning Services | YD Commercial Cleaning Services",
        "page_description": "Explore our Adelaide cleaning services, including residential, commercial, bond and office cleaning. Find the right service for your needs.",
        "page_keywords": "Adelaide cleaning services, residential cleaning Adelaide, commercial cleaning Adelaide, bond cleaning Adelaide, office cleaning Adelaide, window cleaning Adelaide",
        "page_image": "/static/images/logo.jpeg",
        "google_reviews": google_reviews,
    })


def custom_page_not_found(request, exception=None):
    return render(request, "404.html", {
        "page_title": "Page Not Found | YD Commercial Cleaning Services",
        "page_description": "The requested page doesn’t exist. Explore our Adelaide cleaning services or get in touch for quick support.",
        "page_keywords": "404 Adelaide cleaning, page not found, YD Commercial Cleaning services",
        "page_image": "/static/images/logo.jpeg",
    }, status=404)
>>>>>>> 5815f15 (Initial project commit)

# ====================================================
# Contact Page View
# ====================================================

<<<<<<< HEAD

def contact(request):
    return render(request, "contact.html")


=======
def contact(request):
    return render(request, "pages/contact.html", {
        "page_title": "Contact YD Commercial Cleaning Services",
        "page_description": "Contact YD Commercial Cleaning Services for Adelaide commercial, office and home cleaning. Book a free quote, call our local team or send a message.",
        "page_keywords": "contact Adelaide cleaning, YD Commercial Cleaning contact, Adelaide cleaning quote, local cleaning service enquiries",
    })


def login_hub(request):
    return render(request, "core/login_hub.html")

>>>>>>> 5815f15 (Initial project commit)
# ====================================================
# SEO Service Page View
# ====================================================

<<<<<<< HEAD

def service_page(request, service_slug):
    services = {
        "commercial-cleaning-adelaide": {
            "title": "Commercial Cleaning Adelaide",
            "heading": "Professional Commercial Cleaning Services in Adelaide",
            "description": "Reliable commercial cleaning for offices, shops, warehouses and business premises across Adelaide.",
        },
        "office-cleaning-adelaide": {
            "title": "Office Cleaning Adelaide",
            "heading": "Reliable Office Cleaning Services in Adelaide",
            "description": "Keep your workplace clean, fresh and professional with regular office cleaning services tailored to your business needs.",
        },
        "end-of-lease-cleaning-adelaide": {
            "title": "End of Lease Cleaning Adelaide",
            "heading": "End of Lease Cleaning Services in Adelaide",
            "description": "Detailed end-of-lease cleaning for tenants, landlords and property managers across Adelaide.",
        },
        "house-cleaning-adelaide": {
            "title": "House Cleaning Adelaide",
            "heading": "Professional House Cleaning Services in Adelaide",
            "description": "Affordable and reliable house cleaning for Adelaide homes, including regular cleans, one-off cleans and deep cleaning.",
        },
        "window-cleaning-adelaide": {
            "title": "Window Cleaning Adelaide",
            "heading": "Professional Window Cleaning Services in Adelaide",
            "description": "Interior and exterior window cleaning for homes, offices and commercial spaces across Adelaide.",
        },
    }

    service = services.get(service_slug)

    if not service:
        return redirect("home")

    return render(request, "service_detail.html", {"service": service})
=======
def service_page(request, service_slug):
    location_slug, location_name = get_location_from_slug(service_slug)
    base_slug = get_base_slug(service_slug, location_slug)

    service_obj = get_active_service_by_slug(base_slug)
    if not service_obj:
        return redirect("home")

    service_title = f"{service_obj.name} {location_name}"
    service_description = service_obj.description
    service_overview = service_obj.overview
    page_keywords = f"{service_obj.name} {location_name}, Adelaide {service_obj.name.lower()}, local cleaning service, {location_name} cleaning"
    page_title = f"{service_obj.name} {location_name} | Adelaide Cleaning"

    service = {
        "title": service_title,
        "heading": f"Professional {service_obj.name} in {location_name}",
        "description": service_description,
        "overview": service_overview,
        "included": service_obj.included,
        "packages": service_obj.packages,
        "hero_image": service_obj.hero_image.url if service_obj.hero_image else "/static/images/logo.jpeg",
        "slug": service_slug,
        "location": location_name,
        "keywords": page_keywords,
    }

    service_reviews = GoogleReview.objects.order_by("-review_date")[:5]
    service_review_count = service_reviews.count()
    service_average_rating = None
    if service_review_count:
        service_average_rating = round(
            sum(review.rating for review in service_reviews) / service_review_count,
            1,
        )

    service_url = request.build_absolute_uri()

    return render(request, "services/service_detail.html", {
        "service": service,
        "page_title": page_title,
        "page_description": service_description,
        "page_keywords": page_keywords,
        "page_image": "/static/images/logo.jpeg",
        "service_reviews": service_reviews,
        "service_review_count": service_review_count,
        "service_average_rating": service_average_rating,
        "service_url": service_url,
    })
>>>>>>> 5815f15 (Initial project commit)


# ====================================================
# robots.txt
# Tells search engines what they can crawl
# ====================================================

<<<<<<< HEAD

def robots_txt(request):
    content = """User-agent: *
Allow: /

Sitemap: https://www.ydcleaning.com/sitemap.xml
=======
def robots_txt(request):
    site_url = request.build_absolute_uri("/").rstrip("/")
    content = f"""User-agent: *
Allow: /

Sitemap: {site_url}/sitemap.xml
>>>>>>> 5815f15 (Initial project commit)
"""
    return HttpResponse(content, content_type="text/plain")


<<<<<<< HEAD
# ====================================================
# sitemap.xml
# Lists important website pages for Google indexing
# ====================================================


def sitemap_xml(request):
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">

    <url>
        <loc>https://www.ydcleaning.com/</loc>
        <priority>1.0</priority>
    </url>

    <url>
        <loc>https://www.ydcleaning.com/contact/</loc>
        <priority>0.8</priority>
    </url>

    <url>
        <loc>https://www.ydcleaning.com/gallery/</loc>
        <priority>0.7</priority>
    </url>

    <url>
        <loc>https://www.ydcleaning.com/reviews/</loc>
        <priority>0.7</priority>
    </url>

    <url>
        <loc>https://www.ydcleaning.com/commercial-cleaning-adelaide/</loc>
        <priority>0.9</priority>
    </url>

    <url>
        <loc>https://www.ydcleaning.com/office-cleaning-adelaide/</loc>
        <priority>0.9</priority>
    </url>

    <url>
        <loc>https://www.ydcleaning.com/end-of-lease-cleaning-adelaide/</loc>
        <priority>0.9</priority>
    </url>

    <url>
        <loc>https://www.ydcleaning.com/house-cleaning-adelaide/</loc>
        <priority>0.9</priority>
    </url>

    <url>
        <loc>https://www.ydcleaning.com/window-cleaning-adelaide/</loc>
        <priority>0.9</priority>
    </url>

</urlset>
"""
    return HttpResponse(content, content_type="application/xml")
=======
def location_landing_page(request):
    """
    Landing page showing all services by location (similar to Jim's SA page).
    Displays:
    - Services overview for Adelaide
    - Service list with links
    - Location highlights
    - Why Choose Us content
    - Related blog articles
    """
    location_name = "Adelaide"
    location_slug = "adelaide"

    # Build comprehensive service list for this location
    services = get_service_listing(location_name)

    # Build service categories
    service_categories = {}
    for service in services:
        category = service["service_name"].split()[0]  # First word as category
        if category not in service_categories:
            service_categories[category] = []
        service_categories[category].append(service)

    # Get featured areas/suburbs
    featured_locations = [
        {"name": "Prospect", "slug": "prospect"},
        {"name": "Mawson Lakes", "slug": "mawson-lakes"},
        {"name": "Salisbury", "slug": "salisbury"},
        {"name": "North Adelaide", "slug": "north-adelaide"},
        {"name": "Glenelg", "slug": "glenelg"},
        {"name": "Norwood", "slug": "norwood"},
        {"name": "Unley", "slug": "unley"},
        {"name": "Burnside", "slug": "burnside"},
        {"name": "Modbury", "slug": "modbury"},
    ]

    google_reviews = GoogleReview.objects.order_by("-review_date")[:6]

    return render(request, "services/location_landing.html", {
        "location_name": location_name,
        "location_slug": location_slug,
        "services": services,
        "service_categories": service_categories,
        "featured_locations": featured_locations,
        "page_title": f"Cleaning Services {location_name} | Adelaide Local Services | YD Commercial Cleaning",
        "page_description": f"Discover all YD Commercial Cleaning services in {location_name} and suburbs.",
        "page_keywords": f"cleaning services {location_name}, Adelaide cleaning, residential cleaning, commercial cleaning",
        "page_image": "/static/images/logo.jpeg",
        "google_reviews": google_reviews,
    })


def location_index_page(request, letter="a"):
    location_name = "Adelaide"
    location_slug = "adelaide"
    current_letter = letter.lower()[:1]
    if current_letter not in "abcdefghijklmnopqrstuvwxyz":
        current_letter = "a"

    alphabet_letters = [chr(code) for code in range(ord("A"), ord("Z") + 1)]

    suburb_entries = ADELAIDE_SUBURBS.get(current_letter, [])

    matching_areas = [
        {
            "name": suburb["name"],
            "postcode": suburb.get("postcode", ""),
            "slug": slugify(suburb["name"]),
        }
        for suburb in suburb_entries
    ]

    services = get_service_listing(location_name)

    return render(request, "services/location_index.html", {
        "location_name": location_name,
        "location_slug": location_slug,
        "current_letter": current_letter.upper(),
        "letters": alphabet_letters,
        "matching_areas": matching_areas,
        "services": services,
        "page_title": f"{location_name} Cleaning Areas Starting with {current_letter.upper()} | YD Commercial Cleaning",
        "page_description": f"Explore Adelaide cleaning services and suburbs starting with {current_letter.upper()}. Find the right local cleaning area and service today.",
        "page_keywords": f"{location_name} cleaning {current_letter.upper()}, Adelaide cleaning areas, local cleaning suburbs",
        "page_image": "/static/images/logo.jpeg",
    })


def suburb_detail_page(request, suburb_slug):
    """Detail page for a specific Adelaide suburb."""
    location_name = "Adelaide"
    location_slug = "adelaide"

    suburb_name = suburb_slug.replace('-', ' ').title()

    services = get_service_listing(location_name, description_location=suburb_name)

    google_reviews = GoogleReview.objects.order_by("-review_date")[:4]

    return render(request, "services/suburb_detail.html", {
        "suburb_name": suburb_name,
        "suburb_slug": suburb_slug,
        "location_name": location_name,
        "location_slug": location_slug,
        "services": services,
        "google_reviews": google_reviews,
        "page_title": f"Cleaning Services in {suburb_name}, {location_name} | YD Commercial Cleaning",
        "page_description": f"Professional cleaning services for {suburb_name} and surrounding areas. Residential, commercial, office and specialist cleaning available.",
        "page_keywords": f"{suburb_name} cleaning, cleaning services {suburb_name}, {suburb_name} Adelaide cleaning",
        "page_image": "/static/images/logo.jpeg",
    })


def rss_feed(request):
    feed = Rss201rev2Feed(
        title="YD Commercial Cleaning Reviews",
        link=request.build_absolute_uri("/"),
        description="Latest Adelaide customer reviews and service updates from YD Commercial Cleaning Services.",
        language="en-AU",
    )

    reviews = Review.objects.filter(featured=True).order_by("-created_at")[:20]
    for review in reviews:
        feed.add_item(
            title=f"{review.customer_name} ⭐{review.rating} Review",
            link=request.build_absolute_uri("/reviews/"),
            description=review.review_text,
            unique_id=f"review-{review.id}",
            pubdate=review.created_at,
        )

    return HttpResponse(feed.writeString("utf-8"), content_type="application/rss+xml")


# ====================================================
# New Page Views
# ====================================================

def about(request):
    """About page showing company information and story."""
    return render(request, "pages/about.html", {})


def pricing(request):
    """Pricing page showing service packages and rates."""
    return render(request, "pages/pricing.html", {})


def team(request):
    """Team page showcasing company team members."""
    return render(request, "pages/team.html", {})


def faq(request):
    """Frequently Asked Questions page."""
    return render(request, "pages/faq.html", {})


def blog(request):
    """Blog listing page."""
    posts = BlogPost.objects.filter(published=True).order_by('-published_at')
    return render(request, "pages/blog.html", {"posts": posts})


def guides(request):
    """Free cleaning guides and resources page."""
    return render(request, "pages/guides.html", {})


def resources(request):
    """Resources hub page linking guides, blog, case studies and FAQs."""
    resources_list = [
        {
            "title": "Cleaning Guides",
            "description": "Download our professional cleaning checklists, maintenance guides and printable resources.",
            "url": "/guides/",
            "icon": "📘",
        },
        {
            "title": "Blog Articles",
            "description": "Read cleaning tips, maintenance advice and expert service recommendations.",
            "url": "/blog/",
            "icon": "📝",
        },
        {
            "title": "Case Studies",
            "description": "See real Adelaide cleaning projects and before-and-after service results.",
            "url": "/case-studies/",
            "icon": "📂",
        },
        {
            "title": "FAQs",
            "description": "Find quick answers about cleaning services, pricing and booking options.",
            "url": "/faq/",
            "icon": "❓",
        },
        {
            "title": "Local Services",
            "description": "Explore our Adelaide cleaning services and choose the right solution for your property.",
            "url": "/services/",
            "icon": "📍",
        },
        {
            "title": "Request a Quote",
            "description": "Get a free, no-obligation cleaning quote from our Adelaide team today.",
            "url": "/contact/",
            "icon": "📞",
        },
    ]
    return render(request, "pages/resources.html", {
        "page_title": "Cleaning Resources | YD Commercial Cleaning Services",
        "page_description": "Explore free cleaning resources, guides, blog posts, case studies and FAQs from YD Commercial Cleaning Services.",
        "page_keywords": "cleaning resources Adelaide, cleaning guides, blog, case studies, FAQ, YD Commercial Cleaning",
        "page_image": "/static/images/logo.jpeg",
        "resources_list": resources_list,
    })


def case_studies(request):
    """Case studies showcasing real project results."""
    return render(request, "pages/case-studies.html", {})


def guide_detail(request, guide_slug):
    """Render a single guide detail page (shows checklist and download link).

    Expects template at `pages/guides/<guide_slug>.html`.
    """
    from django.template import TemplateDoesNotExist
    from django.http import Http404

    template_name = f"pages/guides/{guide_slug}.html"
    try:
        return render(request, template_name, {})
    except TemplateDoesNotExist:
        raise Http404("Guide not found")


def blog_detail(request, blog_slug):
    """Render a single blog post page.

    Prefer BlogPost model instance when available, otherwise fall back to static template.
    """
    from django.template import TemplateDoesNotExist

    post = BlogPost.objects.filter(slug=blog_slug, published=True).first()
    if post:
        # pass a list of recent posts for the sidebar (exclude current)
        recent_posts = BlogPost.objects.filter(published=True).order_by('-published_at')[:8]
        return render(request, "pages/blog_post_detail.html", {"post": post, "posts": recent_posts})

    # Fallback - attempt static template
    template_name = f"pages/blog_posts/{blog_slug}.html"
    try:
        return render(request, template_name, {})
    except TemplateDoesNotExist:
        raise Http404("Blog post not found")
>>>>>>> 5815f15 (Initial project commit)
