from django.core.management.base import BaseCommand

from company_documents.models import ComplianceRequirement


REQUIREMENTS = [

    # =========================================================
    # COMPANY
    # =========================================================

    {
        "scope": "company",
        "name": "Insurance Certificate",
        "category": "insurance",
        "document_type": "Insurance Certificate",
        "description": "Current company insurance evidence.",
        "sort_order": 10,
    },

    {
        "scope": "company",
        "name": "ABN / Corporate Details",
        "category": "company",
        "document_type": "ABN / Corporate Details Record",
        "description": "Current company registration and ABN evidence.",
        "sort_order": 20,
    },

    {
        "scope": "company",
        "name": "Annual Business Plan",
        "category": "company",
        "document_type": "Annual Business Plan",
        "description": "Current business planning documentation.",
        "sort_order": 30,
    },

    {
        "scope": "company",
        "name": "WHS Induction Checklist",
        "category": "whs",
        "document_type": "WHS / Safety Record",
        "description": "Core WHS compliance documentation.",
        "sort_order": 40,
    },

    {
        "scope": "company",
        "name": "Privacy / Data Protection",
        "category": "company",
        "document_type": "Privacy / Data Protection Record",
        "description": "Privacy and data protection documentation.",
        "sort_order": 50,
    },


    # =========================================================
    # EMPLOYEE
    # =========================================================

    {
        "scope": "employee",
        "name": "Employment Agreement",
        "category": "employee",
        "document_type": "Employment Agreement",
        "description": "Current employment agreement.",
        "sort_order": 10,
    },

    {
        "scope": "employee",
        "name": "Identity Document",
        "category": "employee",
        "document_type": "Identity Document Record",
        "description": "Identity evidence for the employee.",
        "sort_order": 20,
        "sensitive": True,
    },

    {
        "scope": "employee",
        "name": "Working Rights Evidence",
        "category": "employee",
        "document_type": "Working Rights Evidence",
        "description": "Evidence of working rights.",
        "sort_order": 30,
        "sensitive": True,
    },

    {
        "scope": "employee",
        "name": "Position Description",
        "category": "employee",
        "document_type": "Position Description",
        "description": "Current position description.",
        "sort_order": 40,
    },

    {
        "scope": "employee",
        "name": "Confidentiality Acknowledgement",
        "category": "employee",
        "document_type": "Confidentiality Acknowledgement",
        "description": "Employee confidentiality acknowledgement.",
        "sort_order": 50,
        "sensitive": True,
    },

    {
        "scope": "employee",
        "name": "WHS Induction",
        "category": "whs",
        "document_type": "WHS / Safety Record",
        "description": "Employee WHS induction evidence.",
        "sort_order": 60,
    },


    # =========================================================
    # VEHICLE
    # =========================================================

    {
        "scope": "vehicle",
        "name": "Vehicle Registration",
        "category": "vehicle",
        "document_type": "Vehicle / Fleet Record",
        "description": "Current vehicle registration evidence.",
        "sort_order": 10,
    },

    {
        "scope": "vehicle",
        "name": "Vehicle Insurance",
        "category": "vehicle",
        "document_type": "Vehicle / Fleet Record",
        "description": "Current vehicle insurance evidence.",
        "sort_order": 20,
    },

    {
        "scope": "vehicle",
        "name": "Vehicle Inspection",
        "category": "vehicle",
        "document_type": "Vehicle / Fleet Record",
        "description": "Current vehicle inspection evidence.",
        "sort_order": 30,
    },


    # =========================================================
    # CUSTOMER
    # =========================================================

    {
        "scope": "customer",
        "name": "Client Service Agreement",
        "category": "contract",
        "document_type": "Contract / Agreement",
        "description": "Customer service agreement.",
        "sort_order": 10,
    },

    {
        "scope": "customer",
        "name": "Site Handover Record",
        "category": "operations",
        "document_type": "Cleaning Operations Record",
        "description": "Site handover documentation where required.",
        "sort_order": 20,
        "required": False,
    },


    # =========================================================
    # SUPPLIER
    # =========================================================

    {
        "scope": "supplier",
        "name": "Supplier Onboarding Record",
        "category": "supplier",
        "document_type": "Supplier Record",
        "description": "Supplier onboarding and verification.",
        "sort_order": 10,
    },

    {
        "scope": "supplier",
        "name": "Supplier Agreement",
        "category": "contract",
        "document_type": "Contract / Agreement",
        "description": "Supplier agreement where applicable.",
        "sort_order": 20,
        "required": False,
    },


    # =========================================================
    # CONTRACT
    # =========================================================

    {
        "scope": "contract",
        "name": "Cleaning Service Agreement",
        "category": "contract",
        "document_type": "Contract / Agreement",
        "description": "Contract documentation for the service arrangement.",
        "sort_order": 10,
    },

    {
        "scope": "contract",
        "name": "Site Handover Record",
        "category": "operations",
        "document_type": "Cleaning Operations Record",
        "description": "Site handover record where applicable.",
        "sort_order": 20,
        "required": False,
    },
]


class Command(BaseCommand):

    help = (
        "Create or update the default YD Cleaning "
        "compliance requirements."
    )

    def handle(self, *args, **options):

        created = 0
        updated = 0

        for data in REQUIREMENTS:

            lookup = {
                "scope": data["scope"],
                "name": data["name"],
            }

            defaults = {
                "category": data.get(
                    "category",
                    "",
                ),
                "document_type": data.get(
                    "document_type",
                    "",
                ),
                "description": data.get(
                    "description",
                    "",
                ),
                "required": data.get(
                    "required",
                    True,
                ),
                "active": True,
                "sensitive": data.get(
                    "sensitive",
                    False,
                ),
                "sort_order": data.get(
                    "sort_order",
                    100,
                ),
            }

            obj, was_created = (
                ComplianceRequirement.objects.update_or_create(
                    **lookup,
                    defaults=defaults,
                )
            )

            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                (
                    "Compliance requirements seeded successfully. "
                    f"Created: {created}. "
                    f"Updated: {updated}."
                )
            )
        )