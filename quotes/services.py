from decimal import Decimal

from django.db import transaction

from bookings.models import Booking
from bookings.services import create_booking
from .models import QuoteImage, QuoteRequest


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


def create_quote_request(*, form, images=None, workflow_key=None):
    if not getattr(form, "cleaned_data", None) and not form.is_valid():
        raise ValueError("Quote form is invalid.")

    if workflow_key:
        existing = QuoteRequest.objects.filter(idempotency_key=workflow_key).first()
        if existing:
            return existing, False

    quote = form.save(commit=False)
    quote.estimated_price = calculate_quote_estimate(quote)

    with transaction.atomic():
        if workflow_key:
            quote.idempotency_key = workflow_key
        quote.save()
        for image in images or []:
            QuoteImage.objects.create(quote=quote, image=image)

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
        if quote.status == "booked":
            existing = Booking.objects.filter(idempotency_key=workflow_key or f"quote:{quote.id}").first()
            if existing:
                return existing, False
            raise ValueError("Quote is already marked as booked without a linked booking.")

        service_type = {
            "House": "House Cleaning",
            "Apartment": "House Cleaning",
            "Office": "Office Cleaning",
            "Commercial Property": "Commercial Cleaning",
            "End of Lease Property": "End of Lease Cleaning",
        }.get(quote.property_type)
        if not service_type or not booking_date or not booking_time:
            raise ValueError("A supported service, date, and time are required.")

        customer, _ = resolve_customer(
            email=quote.email,
            name=quote.name,
            phone=quote.phone,
            property_type=quote.property_type,
            suburb_postcode=quote.suburb_postcode,
            create=True,
        )
        booking, created = create_booking(
            customer=customer,
            service_type=service_type,
            booking_date=booking_date,
            booking_time=booking_time,
            address=customer.address or "Address not provided",
            suburb_postcode=quote.suburb_postcode,
            quoted_price=quote.estimated_price,
            notes=quote.message,
            workflow_key=workflow_key or f"quote:{quote.id}",
        )
        if quote.status != "booked":
            quote.status = "booked"
            quote.save(update_fields=["status"])
        return booking, created
