# ====================================================
# YD Commercial Cleaning Services
# File: core/context_processors.py
# Purpose: Provide default FAQ section data for templates.
# ====================================================

from .faq_data import FAQ_PAGE_CONFIG


def faq_section(request):
    section = FAQ_PAGE_CONFIG.get("generic", {}).copy()
    section["page_key"] = "generic"
    return {"faq_section": section}
