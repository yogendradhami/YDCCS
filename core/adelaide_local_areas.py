"""
Controlled Adelaide local-area content registry.

This module is intentionally separate from:
- core/suburbs_data.py
- core/seo_data.py

Do not use the full statewide suburb dataset as the source
for public Adelaide local SEO pages.
"""

ADELAIDE_LOCAL_AREAS = {
    "aberfoyle-park-5159": {
        "name": "Aberfoyle Park",
        "postcode": "5159",
        "letter": "A",

        "seo_title": "Aberfoyle Park Cleaning Services | YD Commercial Cleaning",
        "meta_description": (
            "Professional cleaning services in Aberfoyle Park, Adelaide "
            "for homes, offices, rental properties and businesses. "
            "Request a free quote from YD Commercial Cleaning."
        ),

        "intro": (
            "YD Commercial Cleaning provides professional cleaning services "
            "for homes, rental properties, offices and businesses in "
            "Aberfoyle Park and surrounding Adelaide areas. Whether you need "
            "regular cleaning, a one-off deep clean, end-of-lease cleaning "
            "or help maintaining a workplace, we tailor the service to the "
            "property and the cleaning requirements."
        ),

        "local_overview": (
            "Aberfoyle Park includes a mix of established residential "
            "properties and local businesses, so cleaning requirements can "
            "vary considerably from one property to another. Our approach "
            "starts with understanding the size, condition and purpose of "
            "the property before recommending a suitable cleaning service."
        ),

        "residential_content": (
            "For homes in Aberfoyle Park, cleaning can be arranged around "
            "your household routine and the condition of the property. "
            "Regular cleaning can help maintain kitchens, bathrooms, living "
            "areas and floors, while deep cleaning can provide additional "
            "attention when a property needs a more thorough refresh."
        ),

        "commercial_content": (
            "Local businesses and workplaces can require consistent cleaning "
            "to maintain presentation, hygiene and a comfortable environment "
            "for staff and visitors. Commercial cleaning schedules can be "
            "planned around operating hours and the specific requirements "
            "of the workplace."
        ),

        "why_local": (
            "Choosing a cleaning provider familiar with Adelaide's "
            "residential and commercial requirements makes it easier to "
            "plan the right scope of work, communicate clearly and arrange "
            "a practical cleaning schedule."
        ),

        "nearby_areas": [
            "Happy Valley",
            "Flagstaff Hill",
            "Woodcroft",
            "Hallett Cove",
            "Morphett Vale",
        ],

        "faqs": [
            {
                "question": "Do you provide cleaning services in Aberfoyle Park?",
                "answer": (
                    "Yes. YD Commercial Cleaning provides residential and "
                    "commercial cleaning services in Aberfoyle Park and "
                    "surrounding Adelaide areas."
                ),
            },
            {
                "question": "What cleaning services are available in Aberfoyle Park?",
                "answer": (
                    "Depending on your property and requirements, services "
                    "can include house cleaning, office cleaning, commercial "
                    "cleaning, end-of-lease cleaning and window cleaning."
                ),
            },
            {
                "question": "Can I request a cleaning quote for my Aberfoyle Park property?",
                "answer": (
                    "Yes. Contact YD Commercial Cleaning with your property "
                    "type, location and cleaning requirements and we can "
                    "provide a tailored quote."
                ),
            },
        ],
    },
}
