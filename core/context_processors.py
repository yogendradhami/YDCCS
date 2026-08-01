# ====================================================
# YD Commercial Cleaning Services
# File: core/context_processors.py
# Purpose: Provide default FAQ section data for templates.
# ====================================================

from .faq_data import FAQ_PAGE_CONFIG


def faq_section(request):
    return {"faq_section": FAQ_PAGE_CONFIG.get("generic", {})}
