from django.core.management.base import BaseCommand

from employees.models import Employee
from induction.models import EmployeeOnboardingProfile


class Command(BaseCommand):

    help = (
        "Create missing onboarding profiles for existing employees."
    )

    def handle(self, *args, **options):

        created = 0

        for employee in Employee.objects.all():

            profile, was_created = (
                EmployeeOnboardingProfile.objects.get_or_create(
                    employee=employee,
                )
            )

            if was_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Onboarding profile setup complete. "
                f"Created: {created}"
            )
        )