from django.db import IntegrityError, transaction

from .models import Customer


def normalize_email(email):
    return (email or "").strip().lower()


def resolve_customer(*, user=None, email="", name="", phone="", address="", property_type="", suburb_postcode="", create=False):
    if user is not None and getattr(user, "is_authenticated", False):
        with transaction.atomic():
            customer = Customer.objects.select_for_update().get(user=user)
            return customer, False

    normalized_email = normalize_email(email)
    if not normalized_email:
        if create:
            raise ValueError("A validated email is required to create a customer.")
        return None, False

    with transaction.atomic():
        customer = (
            Customer.objects.select_for_update()
            .filter(email__iexact=normalized_email)
            .first()
        )
        if customer:
            return customer, False

        if not create:
            return None, False

        try:
            customer = Customer.objects.create(
                full_name=(name or "Website Customer").strip(),
                email=normalized_email,
                phone=(phone or "").strip(),
                address=(address or "").strip(),
                property_type=(property_type or "").strip(),
                suburb_postcode=(suburb_postcode or "").strip(),
            )
        except IntegrityError:
            customer = Customer.objects.select_for_update().get(
                email__iexact=normalized_email
            )
            return customer, False

        return customer, True
