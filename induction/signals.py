from django.db.models.signals import post_save
from django.dispatch import receiver

from employees.models import Employee

from .models import (
    EmployeeInduction,
    InductionProgramme,
    EmployeeOnboardingProfile,
)


@receiver(
    post_save,
    sender=Employee,
)
def create_employee_induction(
    sender,
    instance,
    created,
    **kwargs,
):

    if not created:
        return

    programme = (
        InductionProgramme.objects
        .filter(
            active=True,
        )
        .order_by(
            "-version",
        )
        .first()
    )

    if not programme:
        return

    EmployeeInduction.objects.get_or_create(
        employee=instance,
        defaults={
            "programme": programme,
        },
    )


@receiver(post_save, sender=Employee)
def create_employee_onboarding_profile(
    sender,
    instance,
    created,
    **kwargs,
):
    if not created:
        return

    EmployeeOnboardingProfile.objects.get_or_create(
        employee=instance,
    )