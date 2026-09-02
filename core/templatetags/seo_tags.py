from urllib.parse import urljoin
import json

from django import template
from django.utils.html import escape
from django.conf import settings
import os

register = template.Library()

@register.simple_tag(takes_context=True)
def canonical_url(context):
    request = context.get("request")
    if not request:
        return ""
    return request.build_absolute_uri(request.path)

@register.simple_tag(takes_context=True)
def current_page_url(context):
    request = context.get("request")
    if not request:
        return ""
    return request.build_absolute_uri()

@register.simple_tag(takes_context=True)
def open_graph_title(context):
    return context.get("page_title") or context.get("company_settings").business_name if context.get("company_settings") else "YD Commercial Cleaning Services"

@register.simple_tag(takes_context=True)
def open_graph_description(context):
    return context.get("page_description") or context.get("default_seo_description") or "Professional commercial and residential cleaning services in Adelaide, South Australia."

@register.simple_tag(takes_context=True)
def open_graph_image(context):
    company_settings = context.get("company_settings")
    # Prefer a pre-generated optimized static WebP if present to avoid loading large media uploads
    static_opt = os.path.join(settings.BASE_DIR, 'static', 'images', 'company', 'logoo.webp')
    if os.path.exists(static_opt):
        return urljoin(context.get("site_url", ""), "/static/images/company/logoo.webp")

    if company_settings and getattr(company_settings, "logo", None):
        return context.get("site_url", "") + company_settings.logo.url
    return urljoin(context.get("site_url", ""), "/static/images/logo.jpeg")

@register.simple_tag(takes_context=True)
def twitter_title(context):
    return open_graph_title(context)

@register.simple_tag(takes_context=True)
def twitter_description(context):
    return open_graph_description(context)

@register.simple_tag(takes_context=True)
def twitter_image(context):
    return open_graph_image(context)

@register.simple_tag()
def organization_schema():
    """Return Organization JSON-LD schema for YD Commercial Cleaning."""
    schema = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": "YD Commercial Cleaning Services",
        "alternateName": "YD Cleaning",
        "url": "https://ydcleaning.com.au",
        "logo": "https://ydcleaning.com.au/static/images/logo.jpeg",
        "description": "Professional cleaning services in Adelaide for homes, offices, end-of-lease and commercial spaces.",
        "address": {
            "@type": "PostalAddress",
            "addressLocality": "Adelaide",
            "addressRegion": "SA",
            "postalCode": "5000",
            "addressCountry": "AU"
        },
        "telephone": "0430049865",
        "email": "info@ydcleaning.com.au",
        "sameAs": [
            "https://www.facebook.com/ydcommercialcleaning",
            "https://www.instagram.com/ydcommercialcleaning",
            "https://www.tiktok.com/@yd_cleaning3"
        ],
        "areaServed": [
            {
                "@type": "City",
                "name": "Adelaide",
                "addressCountry": "AU"
            },
            {
                "@type": "State",
                "name": "South Australia",
                "addressCountry": "AU"
            }
        ],
        "priceRange": "$$"
    }
    return json.dumps(schema)

@register.simple_tag()
def website_schema():
    """Return WebSite JSON-LD schema."""
    schema = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "YD Commercial Cleaning Services",
        "url": "https://ydcleaning.com.au",
        "potentialAction": {
            "@type": "SearchAction",
            "target": "https://ydcleaning.com.au/?q={search_term_string}",
            "query-input": "required name=search_term_string"
        }
    }
    return json.dumps(schema)

@register.simple_tag()
def breadcrumb_schema(items):
    """Return BreadcrumbList JSON-LD schema.
    
    items should be a list of dicts: [
        {'name': 'Home', 'url': 'https://...'},
        {'name': 'Services', 'url': 'https://...'},
    ]
    """
    if not items or len(items) < 2:
        return ""
    
    breadcrumb_items = []
    for idx, item in enumerate(items, 1):
        breadcrumb_items.append({
            "@type": "ListItem",
            "position": idx,
            "name": item.get("name", ""),
            "item": item.get("url", "")
        })
    
    schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": breadcrumb_items
    }
    return json.dumps(schema)

@register.filter
def cloudinary_optimize(image_url, width=None):
    """Optimize Cloudinary image URL with f_auto, q_auto, and optional width.
    
    Usage: {{ item.image.url|cloudinary_optimize:"400" }}
    Applies: format=auto, quality=auto, and width transformation for better performance.
    """
    if not image_url or "res.cloudinary.com" not in str(image_url):
        return image_url
    
    try:
        # Split the URL at /upload/ to inject transformation params
        url_str = str(image_url)
        if "/upload/" in url_str:
            parts = url_str.split("/upload/")
            if len(parts) == 2:
                base_url = parts[0]
                resource_path = parts[1]
                
                # Build transformations: format=auto, quality=auto, width=X (if specified)
                transforms = ["f_auto", "q_auto"]
                if width:
                    try:
                        transforms.append(f"w_{int(width)}")
                        transforms.append("c_scale")  # Scale to fit width
                    except (ValueError, TypeError):
                        pass
                
                # Combine transformations
                transform_string = ",".join(transforms)
                return f"{base_url}/upload/{transform_string}/{resource_path}"
    except Exception:
        pass
    
    return image_url
