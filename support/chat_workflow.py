import re
from copy import deepcopy
from datetime import date, time

from bookings.services import create_booking, map_service
from customers.services import resolve_customer
from quotes.services import create_quote_from_workflow


QUOTE_FIELDS = (
    "property_type",
    "approximate_size",
    "frequency",
    "suburb",
)

BOOKING_FIELDS = (
    "service",
    "preferred_date",
    "preferred_time",
    "address",
    "suburb",
    "email",
    "phone",
)


CONFIRMATIONS = {
    "yes",
    "y",
    "confirm",
    "confirmed",
    "go ahead",
    "that is correct",
    "that's correct",
    "correct",
    "submit",
    "submit it",
}


CANCELLATIONS = {
    "no",
    "n",
    "cancel",
    "stop",
    "not correct",
    "change",
    "start over",
    "restart",
}


# =========================================================
# NORMAL CONVERSATIONAL MESSAGES
# =========================================================

GREETINGS = {
    "hi",
    "hello",
    "hey",
    "hiya",
    "good morning",
    "good afternoon",
    "good evening",
    "morning",
    "afternoon",
    "evening",
}


def _is_greeting(message):
    """
    Detect a standalone greeting.

    Greetings are handled before an active quote/booking
    confirmation workflow so stale workflow state cannot make
    a simple 'hi' appear to be a booking correction.
    """

    normalized = (
        str(message or "")
        .strip()
        .lower()
    )

    return normalized in GREETINGS


def _state(conversation):
    """
    Return a safe, independent workflow state for this conversation.

    The existing conversation state is deep-copied so workflow
    processing cannot accidentally mutate the database-backed
    state before the consumer explicitly persists the result.
    """

    state = deepcopy(
        conversation.conversation_state or {}
    )

    state.setdefault(
        "schema_version",
        1,
    )

    state.setdefault(
        "workflow",
        {},
    )

    state.setdefault(
        "quote",
        {},
    )

    state.setdefault(
        "booking",
        {},
    )

    state.setdefault(
        "customer",
        {},
    )

    customer = state["customer"]

    customer.setdefault(
        "name",
        conversation.name or "",
    )

    customer.setdefault(
        "email",
        conversation.email or "",
    )

    customer.setdefault(
        "phone",
        conversation.phone or "",
    )

    return state


def _property_type(value):
    """
    Normalize common property-type phrases.
    """

    mapping = {
        "house": "House",
        "home": "House",
        "apartment": "Apartment",
        "unit": "Apartment",
        "office": "Office",
        "commercial": "Commercial Property",
        "commercial property": "Commercial Property",
        "warehouse": "Commercial Property",
        "retail": "Commercial Property",
        "shop": "Commercial Property",
        "end of lease": "End of Lease Property",
        "end-of-lease": "End of Lease Property",
        "end of lease property": "End of Lease Property",
    }

    normalized = (
        str(value or "")
        .strip()
        .lower()
    )

    return mapping.get(
        normalized
    )


def _confirmation(message):
    normalized = (
        str(message or "")
        .strip()
        .lower()
    )

    return normalized in CONFIRMATIONS


def _cancellation(message):
    normalized = (
        str(message or "")
        .strip()
        .lower()
    )

    return normalized in CANCELLATIONS


def _summary(values):
    labels = {
        "property_type": "Property",
        "approximate_size": "Approximate size",
        "frequency": "Frequency",
        "service": "Service",
        "preferred_date": "Preferred date",
        "preferred_time": "Preferred time",
        "address": "Address",
        "suburb": "Suburb",
        "email": "Email",
        "phone": "Phone",
        "name": "Name",
    }

    return "\n".join(
        f"{labels[key]}: {values[key]}"
        for key in labels
        if values.get(key)
    )


def _persist(conversation, state):
    """
    Compatibility helper retained for existing callers.
    """

    conversation.conversation_state = state
    return conversation


def _set_customer_from_entities(
    state,
    entities,
):
    customer = state["customer"]

    for key in (
        "email",
        "phone",
    ):
        if entities.get(key):
            customer[key] = entities[key]

    return customer


def _merge_entities_into_workflow(
    state,
    entities,
    service=None,
):
    """
    Merge analyzer entities into the appropriate workflow state.

    This is intentionally centralized so normal AI messages can
    update quote/booking state even when the user provides several
    details in one message.
    """

    quote = state["quote"]
    booking = state["booking"]
    customer = state["customer"]

    # ---------------------------------------------------------
    # Customer contact details
    # ---------------------------------------------------------

    for key in (
        "email",
        "phone",
    ):
        if entities.get(key):
            customer[key] = entities[key]

    # ---------------------------------------------------------
    # Quote-related information
    # ---------------------------------------------------------

    for key in (
        "property_type",
        "approximate_size",
        "frequency",
        "suburb",
    ):
        if entities.get(key):

            value = entities[key]

            if key == "property_type":
                value = (
                    _property_type(value)
                    or value
                )

            quote[key] = value

    # ---------------------------------------------------------
    # Booking-related information
    # ---------------------------------------------------------

    for key in (
        "preferred_date",
        "preferred_time",
        "address",
        "suburb",
    ):
        if entities.get(key):
            booking[key] = entities[key]

    # ---------------------------------------------------------
    # Preserve detected service.
    # ---------------------------------------------------------

    if service:

        quote.setdefault(
            "service",
            service,
        )

        booking.setdefault(
            "service",
            service,
        )

    return state


def _quote_reply(state):
    quote = state["quote"]
    customer = state["customer"]

    required = {
        **quote,
        **customer,
    }

    missing = [
        field
        for field in QUOTE_FIELDS
        if not required.get(field)
    ]

    if not customer.get("email"):
        missing.append("email")

    if not customer.get("phone"):
        missing.append("phone")

    if not customer.get("name"):
        missing.insert(
            0,
            "name",
        )

    prompts = {
        "name": (
            "What name should we put on the quote request?"
        ),
        "property_type": (
            "What type of property is it, such as a house, "
            "apartment, office or commercial property?"
        ),
        "approximate_size": (
            "Approximately how large is the property?"
        ),
        "frequency": (
            "Would you like a one-off, weekly, fortnightly, "
            "monthly or daily clean?"
        ),
        "suburb": (
            "Which suburb is the property in?"
        ),
        "email": (
            "What email address should our team use "
            "to contact you?"
        ),
        "phone": (
            "What phone number should our team use "
            "to contact you?"
        ),
    }

    if missing:

        state["workflow"] = {
            "type": "quote",
            "step": missing[0],
            "awaiting_confirmation": False,
        }

        return (
            prompts[missing[0]],
            False,
        )

    state["workflow"] = {
        "type": "quote",
        "step": "confirmation",
        "awaiting_confirmation": True,
    }

    return (
        "Please confirm these quote details:\n"
        f"{_summary(required)}\n\n"
        "Reply 'yes' to submit the request, or tell me "
        "what to change.",
        False,
    )


def _booking_reply(state):
    booking = state["booking"]
    customer = state["customer"]

    missing = [
        field
        for field in BOOKING_FIELDS
        if field not in {
            "email",
            "phone",
        }
        and not booking.get(field)
    ]

    if not customer.get("name"):
        missing.insert(
            0,
            "name",
        )

    if not customer.get("email"):
        missing.append("email")

    if not customer.get("phone"):
        missing.append("phone")

    prompts = {
        "name": (
            "What name should we use for the booking?"
        ),
        "service": (
            "Which cleaning service would you like to book?"
        ),
        "preferred_date": (
            "What date would you prefer? For example, "
            "15 September or next Friday."
        ),
        "preferred_time": (
            "What time would you prefer? For example, "
            "10am or 2:30pm."
        ),
        "address": (
            "What is the property address?"
        ),
        "suburb": (
            "Which suburb is the property in?"
        ),
        "email": (
            "What email address should our team use "
            "to contact you?"
        ),
        "phone": (
            "What phone number should our team use "
            "to contact you?"
        ),
    }

    if missing:

        state["workflow"] = {
            "type": "booking",
            "step": missing[0],
            "awaiting_confirmation": False,
        }

        return (
            prompts[missing[0]],
            False,
        )

    state["workflow"] = {
        "type": "booking",
        "step": "confirmation",
        "awaiting_confirmation": True,
    }

    combined = {
        **booking,
        **customer,
    }

    return (
        "Please confirm these booking details:\n"
        f"{_summary(combined)}\n\n"
        "Reply 'yes' to submit the booking request, "
        "or tell me what to change.",
        False,
    )


def _accept_step_value(
    state,
    message,
    analysis,
):
    workflow = state["workflow"]

    step = workflow.get(
        "step"
    )

    entities = (
        analysis.get("entities")
        or {}
    )

    customer = state["customer"]

    # ---------------------------------------------------------
    # Name
    # ---------------------------------------------------------

    if (
        step == "name"
        and not customer.get("name")
    ):

        value = (
            str(message or "")
            .strip()
        )

        if value and not _cancellation(value):

            customer["name"] = value[:150]

            return True

        return False

    # ---------------------------------------------------------
    # Email / phone
    # ---------------------------------------------------------

    if step in {
        "email",
        "phone",
    }:

        value = entities.get(
            step
        )

        if value:

            customer[step] = value

            return True

        return False

    workflow_type = workflow.get(
        "type"
    )

    target = state.get(
        workflow_type,
        {},
    )

    # ---------------------------------------------------------
    # Property type
    # ---------------------------------------------------------

    if step == "property_type":

        value = _property_type(
            entities.get(
                "property_type"
            )
        )

        if not value:

            value = _property_type(
                message
            )

        if value:

            target[step] = value

            return True

        return False

    # ---------------------------------------------------------
    # Standard entity-based fields
    # ---------------------------------------------------------

    if step in {
        "approximate_size",
        "frequency",
        "suburb",
        "preferred_date",
        "preferred_time",
        "address",
    }:

        value = entities.get(
            step
        )

        if value:

            target[step] = value

            return True

        # -----------------------------------------------------
        # Suburb fallback
        # -----------------------------------------------------

        if step == "suburb":

            value = (
                str(message or "")
                .strip()
            )

            if (
                2 <= len(value) <= 100
                and not _cancellation(value)
            ):

                target[step] = value.title()

                return True

        # -----------------------------------------------------
        # Address fallback
        # -----------------------------------------------------

        if step == "address":

            value = (
                str(message or "")
                .strip()
            )

            if (
                5 <= len(value) <= 255
                and not _cancellation(value)
            ):

                # Accept normal street addresses such as:
                # "123 King Street"
                # "12 Main Road"
                # "Unit 4, 25 Smith Street"
                # "5/18 Prospect Road"
                #
                # Do not treat a general enquiry sentence such as
                # "Hi, I need a quote for office cleaning in Prospect."
                # as an address.

                address_pattern = re.compile(
                    r"""
                    ^
                    (?:
                        (?:unit|suite|apt|apartment)\s*[\w-]+[,\s]+
                    )?
                    \d+[A-Za-z]?
                    (?:[/-]\d+[A-Za-z]?)?
                    [,\s]+
                    [A-Za-z0-9][A-Za-z0-9 .'-]*
                    \b
                    (?:street|st|road|rd|avenue|ave|drive|dr|lane|ln|
                    court|ct|close|cl|crescent|cres|place|pl|
                    terrace|tce|parade|pde|boulevard|blvd|
                    highway|hwy|way|circuit|circ|square|sq)
                    \b
                    .*$
                    """,
                    re.IGNORECASE | re.VERBOSE,
                )

                if address_pattern.match(value):
                    target[step] = value

                    return True

    # ---------------------------------------------------------
    # Service
    # ---------------------------------------------------------

    if step == "service":

        service = analysis.get(
            "service"
        )

        if service:

            target[step] = service

            return True

    return False


def create_confirmed_quote(
    conversation,
    state,
):
    customer = state["customer"]
    quote = state["quote"]

    data = {
        "name": (
            customer.get("name")
            or conversation.name
            or "Website Visitor"
        ),
        "email": customer.get(
            "email",
            "",
        ),
        "phone": customer.get(
            "phone",
            "",
        ),
        "property_type": quote.get(
            "property_type"
        ),
        "suburb_postcode": quote.get(
            "suburb"
        ),
        "message": (
            "Chat quote request. Approximate size: "
            f"{quote.get('approximate_size', 'Not provided')}. "
            "Frequency: "
            f"{quote.get('frequency', 'Not provided')}."
        ),
    }

    return create_quote_from_workflow(
        data=data,
        workflow_key=f"quote:{conversation.id}",
    )


def create_confirmed_booking(
    conversation,
    state,
):
    customer_data = state["customer"]
    booking_data = state["booking"]

    service_type = map_service(
        booking_data.get("service")
    )

    if not service_type:
        raise ValueError(
            "This service requires staff assistance before booking."
        )

    booking_date = date.fromisoformat(
        booking_data["preferred_date"]
    )

    booking_time = time.fromisoformat(
        booking_data["preferred_time"]
    )

    customer, _ = resolve_customer(
        email=customer_data.get(
            "email"
        ),
        name=(
            customer_data.get("name")
            or conversation.name
            or "Website Visitor"
        ),
        phone=customer_data.get(
            "phone",
            "",
        ),
        address=booking_data.get(
            "address",
            "",
        ),
        suburb_postcode=booking_data.get(
            "suburb",
            "",
        ),
        create=True,
    )

    return create_booking(
        customer=customer,
        service_type=service_type,
        booking_date=booking_date,
        booking_time=booking_time,
        address=booking_data["address"],
        suburb_postcode=booking_data["suburb"],
        notes=(
            "Booking request submitted through website live chat."
        ),
        workflow_key=f"booking:{conversation.id}",
    )


def handle_message(
    conversation,
    message,
    analysis,
    faq_response=None,
):
    """
    Main workflow owner for customer messages.

    Returns a structured result consumed by the WebSocket
    consumer. Database persistence is intentionally performed
    by the consumer after this function returns.
    """

    state = _state(
        conversation
    )

    intent = analysis.get(
        "intent",
        "unknown",
    )

    entities = (
        analysis.get("entities")
        or {}
    )

    service = analysis.get(
        "service"
    )

    # ---------------------------------------------------------
    # Human-controlled conversations.
    # ---------------------------------------------------------

    if conversation.mode in {
        "human",
        "waiting_for_human",
    }:

        return {
            "reply": None,
            "action": "none",
            "state": state,
            "state_updated": False,
            "needs_human": False,
        }

    # ---------------------------------------------------------
    # Explicit human request / complaint.
    # ---------------------------------------------------------

    if intent in {
        "human_agent",
        "complaint",
    }:

        state["workflow"] = {
            "type": "human",
            "step": "handoff",
            "awaiting_confirmation": False,
        }

        return {
            "reply": (
                "I’ll connect you with a team member "
                "to help with this."
            ),
            "action": "request_human",
            "state": state,
            "state_updated": True,
            "needs_human": True,
        }

    # ---------------------------------------------------------
    # Merge detected information before workflow handling.
    # ---------------------------------------------------------

    _set_customer_from_entities(
        state,
        entities,
    )

    _merge_entities_into_workflow(
        state,
        entities,
        service=service,
    )

    if (
        service
        and not conversation.service
    ):

        conversation.service = service

    workflow = (
        state.get("workflow")
        or {}
    )

    workflow_type = workflow.get(
        "type"
    )

    # =========================================================
    # GREETING
    #
    # IMPORTANT:
    # Handle a standalone greeting before an active quote or
    # booking workflow. This prevents stale workflow state from
    # interpreting "hi" as a correction/confirmation response.
    #
    # We intentionally DO NOT clear the workflow state here.
    # Existing quote/booking information remains available if
    # the customer continues the conversation.
    # =========================================================

    if _is_greeting(message):

        return {
            "reply": (
                faq_response
                or (
                    "Hi! 👋 Welcome to YD Commercial Cleaning. "
                    "How can we help you today? You can ask me "
                    "about our cleaning services, quotes, bookings, "
                    "or service areas."
                )
            ),
            "action": "faq",
            "state": state,
            "state_updated": False,
            "needs_human": False,
        }

    # =========================================================
    # WORKFLOW SWITCH
    #
    # Allow an explicit request for the other workflow to
    # override an existing quote/booking workflow.
    #
    # Examples:
    #   active quote + booking enquiry -> booking
    #   active booking + quote request -> quote
    #
    # Ordinary messages and greetings continue using the
    # existing workflow.
    # =========================================================

    if (
        workflow_type == "quote"
        and intent == "booking_enquiry"
    ):

        state["workflow"] = {
            "type": "booking",
            "step": "start",
            "awaiting_confirmation": False,
        }

        state["booking"] = {}

        if service:

            state["booking"]["service"] = (
                service
            )

        for key in (
            "preferred_date",
            "preferred_time",
            "suburb",
            "address",
        ):

            if entities.get(key):

                state["booking"][key] = (
                    entities[key]
                )

        reply, _ = _booking_reply(
            state
        )

        return {
            "reply": reply,
            "action": "collect_booking",
            "state": state,
            "state_updated": True,
            "needs_human": False,
        }

    if (
        workflow_type == "booking"
        and intent == "quote_request"
    ):

        state["workflow"] = {
            "type": "quote",
            "step": "start",
            "awaiting_confirmation": False,
        }

        state["quote"] = {}

        for key in QUOTE_FIELDS:

            if entities.get(key):

                state["quote"][key] = (
                    _property_type(
                        entities[key]
                    )
                    if key == "property_type"
                    else entities[key]
                )

        reply, _ = _quote_reply(
            state
        )

        return {
            "reply": reply,
            "action": "collect_quote",
            "state": state,
            "state_updated": True,
            "needs_human": False,
        }

    # =========================================================
    # ACTIVE QUOTE / BOOKING WORKFLOW
    # =========================================================

    if workflow_type in {
        "quote",
        "booking",
    }:

        # -----------------------------------------------------
        # Confirmation
        # -----------------------------------------------------

        if workflow.get(
            "awaiting_confirmation"
        ):

            if _confirmation(message):

                return {
                    "reply": (
                        "Your quote request is being submitted."
                        if workflow_type == "quote"
                        else
                        "Your booking request is being submitted."
                    ),
                    "action": (
                        "create_quote"
                        if workflow_type == "quote"
                        else "create_booking"
                    ),
                    "state": state,
                    "state_updated": True,
                    "needs_human": False,
                }

            # -------------------------------------------------
            # User wants to cancel/restart.
            # -------------------------------------------------

            if _cancellation(message):

                state["workflow"] = {
                    "type": workflow_type,
                    "step": "restart",
                    "awaiting_confirmation": False,
                }

                return {
                    "reply": (
                        "No problem. Let's start again. "
                        + (
                            "What type of property is it?"
                            if workflow_type == "quote"
                            else
                            "Which cleaning service would you "
                            "like to book?"
                        )
                    ),
                    "action": (
                        "collect_quote"
                        if workflow_type == "quote"
                        else "collect_booking"
                    ),
                    "state": state,
                    "state_updated": True,
                    "needs_human": False,
                }

            # -------------------------------------------------
            # User supplied a correction while confirming.
            # -------------------------------------------------

            if workflow_type == "quote":

                changed = False

                for key in QUOTE_FIELDS:

                    if entities.get(key):

                        state["quote"][key] = (
                            _property_type(
                                entities[key]
                            )
                            if key == "property_type"
                            else entities[key]
                        )

                        changed = True

                if entities.get("email"):
                    state["customer"]["email"] = (
                        entities["email"]
                    )
                    changed = True

                if entities.get("phone"):
                    state["customer"]["phone"] = (
                        entities["phone"]
                    )
                    changed = True

                if changed:

                    reply, _ = _quote_reply(
                        state
                    )

                    return {
                        "reply": reply,
                        "action": "collect_quote",
                        "state": state,
                        "state_updated": True,
                        "needs_human": False,
                    }

                return {
                    "reply": (
                        "Tell me which detail you would "
                        "like to change."
                    ),
                    "action": "collect_quote",
                    "state": state,
                    "state_updated": True,
                    "needs_human": False,
                }

            changed = False

            for key in (
                "service",
                "preferred_date",
                "preferred_time",
                "suburb",
                "address",
            ):

                if entities.get(key):

                    state["booking"][key] = (
                        entities[key]
                    )

                    changed = True

            if entities.get("email"):

                state["customer"]["email"] = (
                    entities["email"]
                )

                changed = True

            if entities.get("phone"):

                state["customer"]["phone"] = (
                    entities["phone"]
                )

                changed = True

            if changed:

                reply, _ = _booking_reply(
                    state
                )

                return {
                    "reply": reply,
                    "action": "collect_booking",
                    "state": state,
                    "state_updated": True,
                    "needs_human": False,
                }

            return {
                "reply": (
                    "Tell me which booking detail you "
                    "would like to change."
                ),
                "action": "collect_booking",
                "state": state,
                "state_updated": True,
                "needs_human": False,
            }

        # -----------------------------------------------------
        # Collect current workflow step.
        # -----------------------------------------------------

        _accept_step_value(
            state,
            message,
            analysis,
        )

        if workflow_type == "quote":

            reply, _ = _quote_reply(
                state
            )

            return {
                "reply": reply,
                "action": "collect_quote",
                "state": state,
                "state_updated": True,
                "needs_human": False,
            }

        reply, _ = _booking_reply(
            state
        )

        return {
            "reply": reply,
            "action": "collect_booking",
            "state": state,
            "state_updated": True,
            "needs_human": False,
        }

    # =========================================================
    # START QUOTE WORKFLOW
    # =========================================================

    if intent == "quote_request":

        state["workflow"] = {
            "type": "quote",
            "step": "start",
            "awaiting_confirmation": False,
        }

        for key in QUOTE_FIELDS:

            if entities.get(key):

                state["quote"][key] = (
                    _property_type(
                        entities[key]
                    )
                    if key == "property_type"
                    else entities[key]
                )

        reply, _ = _quote_reply(
            state
        )

        return {
            "reply": reply,
            "action": "collect_quote",
            "state": state,
            "state_updated": True,
            "needs_human": False,
        }

    # =========================================================
    # START BOOKING WORKFLOW
    # =========================================================

    if intent == "booking_enquiry":

        state["workflow"] = {
            "type": "booking",
            "step": "start",
            "awaiting_confirmation": False,
        }

        if service:

            state["booking"]["service"] = (
                service
            )

        for key in (
            "preferred_date",
            "preferred_time",
            "suburb",
            "address",
        ):

            if entities.get(key):

                state["booking"][key] = (
                    entities[key]
                )

        # -----------------------------------------------------
        # Unsupported direct-booking services must go to staff.
        # -----------------------------------------------------

        if (
            state["booking"].get("service")
            and not map_service(
                state["booking"]["service"]
            )
        ):

            state["workflow"] = {
                "type": "human",
                "step": "handoff",
                "awaiting_confirmation": False,
            }

            return {
                "reply": (
                    "I can collect the details, but this "
                    "service needs our team to arrange the "
                    "booking. I’ll connect you with them."
                ),
                "action": "request_human",
                "state": state,
                "state_updated": True,
                "needs_human": True,
            }

        reply, _ = _booking_reply(
            state
        )

        return {
            "reply": reply,
            "action": "collect_booking",
            "state": state,
            "state_updated": True,
            "needs_human": False,
        }

    # =========================================================
    # FAQ / NORMAL MESSAGE
    # =========================================================

    return {
        "reply": faq_response,
        "action": (
            "faq"
            if faq_response
            else "none"
        ),
        "state": state,
        "state_updated": bool(
            service
            or entities
        ),
        "needs_human": False,
    }