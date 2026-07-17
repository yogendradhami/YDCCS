from urllib.parse import urljoin

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
