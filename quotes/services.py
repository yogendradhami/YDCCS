from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from pathlib import Path
import uuid

from django.db import IntegrityError, transaction

from bookings.models import Booking
from bookings.services import create_booking
from .models import QuoteImage, QuoteRequest
from .upload_service import MAX_QUOTE_IMAGES, destroy_quote_image_assets

logger = logging.getLogger(__name__)


def calculate_quote_estimate(quote):
    base_price = 120
    base_price += int(quote.bedrooms or 0) * 30
    base_price += int(quote.bathrooms or 0) * 20

    if quote.property_type == "Office":
        base_price += 150
    elif quote.property_type == "Commercial Property":
        base_price += 250
    elif quote.property_type == "End of Lease Property":
        base_price += 300

    if quote.window_cleaning:
        base_price += 50
    if quote.carpet_shampooing:
        base_price += 100
    if quote.grout_cleaning:
        base_price += 75
    if quote.upholstery_cleaning:
        base_price += 60
    if quote.laundry_service:
        base_price += 60

    return Decimal(base_price)


def create_quote_request(
    *, form, images=None, workflow_key=None, uploaded_image_ids=None
):
    if not getattr(form, "cleaned_data", None) and not form.is_valid():
        raise ValueError("Quote form is invalid.")

    if workflow_key:
        existing = QuoteRequest.objects.filter(idempotency_key=workflow_key).first()
        if existing:
            return existing, False

    image_files = list(images or [])
    direct_image_ids = list(uploaded_image_ids or [])
    if image_files and direct_image_ids:
        raise ValueError("Use either uploaded files or verified direct image uploads.")
    if len(direct_image_ids) > MAX_QUOTE_IMAGES or any(
        not isinstance(public_id, str)
        or not public_id.startswith("quote_images/")
        for public_id in direct_image_ids
    ):
        raise ValueError("The verified property photo list is invalid.")
    if len(set(direct_image_ids)) != len(direct_image_ids):
        raise ValueError("The verified property photo list is invalid.")
    image_storage = QuoteImage._meta.get_field("image").storage
    stored_names = [None] * len(image_files)

    def store_image(image):
        suffix = Path(image.name).suffix.lower()
        filename = f"quote_images/{uuid.uuid4().hex}{suffix}"
        image.seek(0)
        return image_storage.save(filename, image)

    if image_files:
        failures = []
        with ThreadPoolExecutor(max_workers=min(3, len(image_files))) as executor:
            futures = {
                executor.submit(store_image, image): index
                for index, image in enumerate(image_files)
            }
            for future in as_completed(futures):
                try:
                    stored_names[futures[future]] = future.result()
                except Exception as exc:
                    failures.append(exc)

        if failures:
            for name in filter(None, stored_names):
                try:
                    image_storage.delete(name)
                except Exception:
                    logger.exception("Could not clean up quote image %s", name)
            raise failures[0]

    quote = form.save(commit=False)
    quote.estimated_price = calculate_quote_estimate(quote)
    try:
        with transaction.atomic():
            if workflow_key:
                quote.idempotency_key = workflow_key
            quote.save()
            QuoteImage.objects.bulk_create(
                [
                    QuoteImage(quote=quote, image=name)
                    for name in [*stored_names, *direct_image_ids]
                ],
                batch_size=6,
            )
    except Exception as exc:
        if isinstance(exc, IntegrityError) and workflow_key:
            existing = QuoteRequest.objects.filter(
                idempotency_key=workflow_key
            ).first()
            if existing:
                linked_names = set(
                    existing.images.values_list("image", flat=True)
                )
                destroy_quote_image_assets(
                    [
                        public_id
                        for public_id in direct_image_ids
                        if public_id not in linked_names
                    ]
                )
                return existing, False
        for name in filter(None, stored_names):
            try:
                image_storage.delete(name)
            except Exception:
                logger.exception("Could not clean up quote image %s", name)
        destroy_quote_image_assets(direct_image_ids)
        raise

    return quote, True


def create_quote_from_workflow(*, data, workflow_key=None):
    required = ("name", "email", "phone", "property_type", "suburb_postcode")
    if any(not data.get(field) for field in required):
        raise ValueError("Quote details are incomplete.")

    if data["property_type"] not in dict(QuoteRequest.PROPERTY_TYPES):
        raise ValueError("Unsupported quote property type.")

    if workflow_key:
        existing = QuoteRequest.objects.filter(idempotency_key=workflow_key).first()
        if existing:
            return existing, False

    quote = QuoteRequest(
        name=data["name"],
        email=data["email"],
        phone=data["phone"],
        property_type=data["property_type"],
        suburb_postcode=data["suburb_postcode"],
        message=data.get("message", ""),
        lead_source="website",
        estimated_price=0,
        idempotency_key=workflow_key,
    )
    with transaction.atomic():
        quote.save()
    return quote, True


def convert_quote_to_booking(*, quote_id, booking_date, booking_time, workflow_key=None):
    from customers.services import resolve_customer

    with transaction.atomic():
        quote = QuoteRequest.objects.select_for_update().get(id=quote_id)

        # ------------------------------------------------------
        # IDEMPOTENCY / RECOVERY
        # ------------------------------------------------------
        # A quote may already be marked "booked" because of a
        # previous failed conversion. If a booking already exists,
        # return it instead of creating a duplicate.
        # If no booking exists, continue and repair the quote by
        # creating the missing booking.
        # ------------------------------------------------------
        workflow_key = workflow_key or f"quote:{quote.id}"

        existing = Booking.objects.filter(
            idempotency_key=workflow_key
        ).first()

        if existing:
            if quote.status != "booked":
                quote.status = "booked"
                quote.save(update_fields=["status"])

            return existing, False

        # ------------------------------------------------------
        # SERVICE TYPE
        # ------------------------------------------------------
        service_type = {
            "House": "House Cleaning",
            "Apartment": "House Cleaning",
            "Office": "Office Cleaning",
            "Commercial Property": "Commercial Cleaning",
            "End of Lease Property": "End of Lease Cleaning",
        }.get(quote.property_type)

        if not service_type:
            raise ValueError(
                f"Unsupported quote property type: {quote.property_type}"
            )

        if not booking_date:
            raise ValueError("A booking date is required.")

        if not booking_time:
            raise ValueError("A booking time is required.")

        # ------------------------------------------------------
        # CUSTOMER
        # ------------------------------------------------------
        customer, _ = resolve_customer(
            email=quote.email,
            name=quote.name,
            phone=quote.phone,
            property_type=quote.property_type,
            suburb_postcode=quote.suburb_postcode,
            create=True,
        )

        # ------------------------------------------------------
        # CREATE BOOKING
        # ------------------------------------------------------
        booking, created = create_booking(
            customer=customer,
            service_type=service_type,
            booking_date=booking_date,
            booking_time=booking_time,
            address=customer.address or "Address not provided",
            suburb_postcode=quote.suburb_postcode,
            quoted_price=quote.estimated_price,
            notes=quote.message,
            workflow_key=workflow_key,
        )

        # ------------------------------------------------------
        # MARK QUOTE AS BOOKED ONLY AFTER BOOKING EXISTS
        # ------------------------------------------------------
        if quote.status != "booked":
            quote.status = "booked"
            quote.save(update_fields=["status"])

        return booking, created
