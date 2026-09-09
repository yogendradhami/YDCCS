# ====================================================
# YD Commercial Cleaning Services
# File: core/context_processors.py
# Purpose: Provide default FAQ section data for templates.
# ====================================================

from .faq_data import FAQ_PAGE_CONFIG
from .views import _build_why_choose_section


def faq_section(request):
    section = FAQ_PAGE_CONFIG.get("generic", {}).copy()
    section["page_key"] = "generic"
    return {"faq_section": section}





def global_why_choose(request):
    """
    Provides a global Why Choose Us section to every template.

    Individual views can override why_choose_section with
    service-specific or page-specific content.
    """

    global_why_choose_context = {
        "heading": "Why Choose YD Commercial Cleaning?",
        "intro": (
            "Customers across Adelaide choose YD Commercial Cleaning "
            "for dependable service, professional standards and cleaning "
            "solutions tailored to the needs of their property."
        ),
        "cards": [
            {
                "icon": "✓",
                "title": "Fully Insured Cleaning",
                "description": (
                    "Our cleaning services are delivered with professional "
                    "standards and appropriate insurance coverage, giving "
                    "customers greater confidence when inviting our team "
                    "into their property."
                ),
            },
            {
                "icon": "★",
                "title": "Professional Local Team",
                "description": (
                    "We are an Adelaide-based cleaning service focused on "
                    "reliable communication, punctual service and consistent "
                    "cleaning results."
                ),
            },
            {
                "icon": "◈",
                "title": "Tailored Cleaning Solutions",
                "description": (
                    "Every property has different requirements. We can "
                    "adapt the cleaning scope around your property, "
                    "priorities, schedule and service type."
                ),
            },
            {
                "icon": "⏱",
                "title": "Flexible Scheduling",
                "description": (
                    "We work with residential and commercial customers to "
                    "arrange cleaning at practical times that fit around "
                    "your household, workplace or property requirements."
                ),
            },
            {
                "icon": "✓",
                "title": "Clear Communication",
                "description": (
                    "From the initial enquiry through to completion, we "
                    "aim to keep the cleaning scope, expectations and "
                    "service arrangements clear."
                ),
            },
            {
                "icon": "◆",
                "title": "Quality-Focused Results",
                "description": (
                    "Our approach focuses on detailed cleaning, careful "
                    "attention to high-use areas and results that help "
                    "keep your property clean, presentable and comfortable."
                ),
            },
        ],
    }

    return {
        "why_choose_section": _build_why_choose_section(
            global_why_choose_context
        )
    }