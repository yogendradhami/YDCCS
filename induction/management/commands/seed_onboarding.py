from django.core.management.base import BaseCommand

from induction.models import OnboardingRequirement


class Command(BaseCommand):

    help = (
        "Create default YD Commercial Cleaning "
        "employee onboarding requirements."
    )

    REQUIREMENTS = [
        {
            "code": "employment-agreement",
            "title": "Employment Agreement",
            "category": "employment",
            "role": "all",
            "description": (
                "Signed employment agreement or contract."
            ),
            "required": True,
            "employee_upload_allowed": True,
            "expiry_days": None,
            "sort_order": 10,
        },
        {
            "code": "position-description",
            "title": "Position Description",
            "category": "employment",
            "role": "all",
            "description": (
                "Current position description acknowledged "
                "by the employee."
            ),
            "required": True,
            "employee_upload_allowed": True,
            "expiry_days": None,
            "sort_order": 20,
        },
        {
            "code": "working-rights",
            "title": "Working Rights Evidence",
            "category": "right_to_work",
            "role": "all",
            "description": (
                "Evidence required to verify the employee's "
                "right to work."
            ),
            "required": True,
            "employee_upload_allowed": True,
            "expiry_days": None,
            "sort_order": 30,
        },
        {
            "code": "identity-document",
            "title": "Identity Document",
            "category": "identity",
            "role": "all",
            "description": (
                "Approved identity document."
            ),
            "required": True,
            "employee_upload_allowed": True,
            "expiry_days": None,
            "sort_order": 40,
        },
        {
            "code": "whs-training-record",
            "title": "WHS Training Record",
            "category": "training",
            "role": "all",
            "description": (
                "Additional WHS training evidence where "
                "required for the role."
            ),
            "required": False,
            "employee_upload_allowed": True,
            "expiry_days": 365,
            "sort_order": 50,
        },
        {
            "code": "licence-certificate",
            "title": "Licence / Certificate",
            "category": "licence",
            "role": "all",
            "description": (
                "Relevant licence or certificate for the role."
            ),
            "required": False,
            "employee_upload_allowed": True,
            "expiry_days": 365,
            "sort_order": 60,
        },
        {
            "code": "police-check",
            "title": "Police Check",
            "category": "compliance",
            "role": "all",
            "description": (
                "Police check where required by company "
                "policy, customer contract or role."
            ),
            "required": False,
            "employee_upload_allowed": True,
            "expiry_days": None,
            "sort_order": 70,
        },
        {
            "code": "driver-licence",
            "title": "Driver Licence",
            "category": "licence",
            "role": "supervisor",
            "description": (
                "Current driver's licence where driving "
                "is required for the position."
            ),
            "required": False,
            "employee_upload_allowed": True,
            "expiry_days": 365,
            "sort_order": 80,
        },
        {
            "code": "privacy-policy",
            "title": "Privacy & Confidentiality Policy",
            "category": "policy",
            "role": "all",
            "description": "Employee acknowledgement of privacy and confidentiality obligations.",
            "required": False,
            "employee_upload_allowed": False,
            "expiry_days": None,
            "sort_order": 90,
        },
        {
            "code": "code-of-conduct",
            "title": "Code of Conduct",
            "category": "policy",
            "role": "all",
            "description": "Employee acknowledgement of workplace conduct requirements.",
            "required": False,
            "employee_upload_allowed": False,
            "expiry_days": None,
            "sort_order": 100,
        },
    ]

    def handle(self, *args, **options):

        created = 0
        updated = 0

        for data in self.REQUIREMENTS:

            requirement, was_created = (
                OnboardingRequirement.objects.update_or_create(
                    code=data["code"],
                    defaults={
                        **data,
                        "active": True,
                        "version": 1,
                    },
                )
            )

            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                "YD onboarding requirements seeded successfully."
            )
        )

        self.stdout.write(
            f"Created: {created}"
        )

        self.stdout.write(
            f"Updated: {updated}"
        )