# ====================================================
# YD Commercial Cleaning Services
# File: core/views.py
# Purpose: Handles homepage, contact, services, SEO files
# ====================================================

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


# ====================================================
# Homepage View
# ====================================================
def home(request):
    gallery_items = GalleryItem.objects.filter(featured=True).order_by("-created_at")[
        :6
    ]
    reviews = Review.objects.filter(featured=True).order_by("-created_at")[:3]

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
            "reviews": reviews,
        },
    )


# ====================================================
# Contact Page View
# ====================================================


def contact(request):
    return render(request, "contact.html")


# ====================================================
# SEO Service Page View
# ====================================================


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
