import re
from datetime import date, timedelta


_MONTHS = {
    name: number
    for number, name in enumerate(
        (
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december",
        ),
        1,
    )
}
_WEEKDAYS = {
    name: number
    for number, name in enumerate(
        ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
    )
}
_DATE_PATTERNS = (
    re.compile(r"\b(?P<day>\d{1,2})[/-](?P<month>\d{1,2})(?:[/-](?P<year>\d{2,4}))?\b"),
    re.compile(
        r"\b(?P<month>january|february|march|april|may|june|july|august|"
        r"september|october|november|december)\s+(?P<day>\d{1,2})"
        r"(?:st|nd|rd|th)?(?:,?\s+(?P<year>\d{4}))?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?P<day>\d{1,2})(?:st|nd|rd|th)?\s+"
        r"(?P<month>january|february|march|april|may|june|july|august|"
        r"september|october|november|december)"
        r"(?:\s+(?P<year>\d{4}))?\b",
        re.IGNORECASE,
    ),
)
_TIME_PATTERN = re.compile(
    r"\b(?P<hour>1[0-2]|0?[1-9])(?:[:.](?P<minute>[0-5]\d))?\s*"
    r"(?P<ampm>a\.?m\.?|p\.?m\.?)\b",
    re.IGNORECASE,
)

INTENTS = {
    "general_question",
    "service_enquiry",
    "pricing_enquiry",
    "quote_request",
    "booking_enquiry",
    "existing_booking",
    "complaint",
    "invoice_question",
    "payment_question",
    "human_agent",
    "other",
    "unknown",
}

SERVICES = {
    "commercial_cleaning",
    "office_cleaning",
    "window_cleaning",
    "oven_cleaning",
    "carpet_cleaning",
    "spring_cleaning",
    "deep_cleaning",
    "end_of_lease_cleaning",
    "other",
}

_EMAIL_PATTERN = re.compile(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+61|0)[\d ()-]{7,14}\d(?!\w)")
_SIZE_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(sqm|m2|square\s+met(?:re|er)s?)\b",
    re.IGNORECASE,
)
_SUBURB_PATTERN = re.compile(
    r"\b(?:suburb|in|located\s+in|based\s+in|property\s+in)\s*(?:is|:)?\s*"
    r"([A-Za-z][A-Za-z -]{2,40}?)(?=[,.!?]|$)",
    re.IGNORECASE,
)


def normalize_message(message):
    return " ".join(str(message or "").lower().split())


def detect_intent(message):
    text = normalize_message(message)

    if not text:
        return "unknown"

    if any(
        phrase in text
        for phrase in (
            "talk to someone",
            "speak to someone",
            "speak to an agent",
            "real person",
            "human",
            "customer service",
            "staff member",
        )
    ):
        return "human_agent"

    if any(
        phrase in text
        for phrase in (
            "complaint",
            "unhappy",
            "bad service",
            "problem with cleaner",
            "issue with cleaner",
        )
    ):
        return "complaint"

    if any(phrase in text for phrase in ("existing booking", "my booking", "current booking")):
        return "existing_booking"

    if any(word in text.split() for word in ("invoice", "invoices")):
        return "invoice_question"

    if any(word in text.split() for word in ("payment", "payments", "paid")):
        return "payment_question"

    if any(word in text.split() for word in ("quote", "quotation", "estimate")):
        return "quote_request"

    if any(word in text.split() for word in ("price", "pricing", "cost")) or "how much" in text:
        return "pricing_enquiry"

    if any(word in text.split() for word in ("book", "booking", "schedule", "appointment")):
        return "booking_enquiry"

    if detect_service(text):
        return "service_enquiry"

    if any(
        phrase in text
        for phrase in (
            "cleaning service",
            "cleaning services",
            "what do you clean",
            "what services",
            "services do you provide",
        )
    ):
        return "service_enquiry"

    if re.match(r"^(hi|hello|hey)\b", text) or text in {
        "thanks",
        "thank you",
        "bye",
        "goodbye",
    }:
        return "general_question"

    return "unknown"


def detect_service(message):
    text = normalize_message(message)
    service_patterns = (
        ("end_of_lease_cleaning", ("end of lease", "end-of-lease", "bond cleaning")),
        ("commercial_cleaning", ("commercial cleaning", "commercial cleaners")),
        ("office_cleaning", ("office cleaning", "office cleaners")),
        ("window_cleaning", ("window cleaning", "clean my windows", "clean windows")),
        ("oven_cleaning", ("oven cleaning", "oven needs cleaning")),
        ("carpet_cleaning", ("carpet cleaning", "clean my carpet")),
        ("spring_cleaning", ("spring clean", "spring cleaning")),
        ("deep_cleaning", ("deep clean", "deep cleaning")),
    )

    for service, phrases in service_patterns:
        if any(phrase in text for phrase in phrases):
            return service

    return None


def _extract_email(text):
    match = _EMAIL_PATTERN.search(text)
    return match.group(0) if match else None


def _extract_phone(text):
    match = _PHONE_PATTERN.search(text)
    if not match:
        return None
    value = match.group(0).strip()
    digits = re.sub(r"\D", "", value)
    return value if 8 <= len(digits) <= 15 else None


def _extract_size(text):
    match = _SIZE_PATTERN.search(text)
    if not match:
        return None
    return f"{match.group(1)} {re.sub(r'\s+', ' ', match.group(2).lower())}"


def _extract_frequency(text):
    for frequency in ("one-off", "one off", "fortnightly", "weekly", "daily", "monthly"):
        if frequency in text:
            return "one-off" if frequency == "one off" else frequency
    return None


def _extract_property_type(text):
    property_types = (
        ("office", "office"),
        ("commercial", "commercial property"),
        ("warehouse", "warehouse"),
        ("apartment", "apartment"),
        ("house", "house"),
        ("home", "house"),
        ("retail", "retail"),
        ("shop", "retail"),
    )
    for phrase, value in property_types:
        if re.search(rf"\b{re.escape(phrase)}\b", text):
            return value
    return None


def _extract_suburb(text):
    match = _SUBURB_PATTERN.search(text)
    return match.group(1).strip().title() if match else None


def _safe_date(year, month, day):
    try:
        if year is not None and year < 100:
            year += 2000
        return date(year or date.today().year, month, day)
    except ValueError:
        return None


def _extract_preferred_date(text):
    today = date.today()
    lowered = text.lower()

    if re.search(r"\bday after tomorrow\b", lowered):
        return (today + timedelta(days=2)).isoformat()
    if re.search(r"\btomorrow\b", lowered):
        return (today + timedelta(days=1)).isoformat()
    if re.search(r"\btoday\b", lowered):
        return today.isoformat()

    for weekday_name, weekday_number in _WEEKDAYS.items():
        if re.search(rf"\bnext\s+{weekday_name}\b", lowered):
            days_ahead = (weekday_number - today.weekday()) % 7
            days_ahead = days_ahead or 7
            return (today + timedelta(days=days_ahead)).isoformat()
        if re.search(rf"\b{weekday_name}\b", lowered):
            days_ahead = (weekday_number - today.weekday()) % 7
            return (today + timedelta(days=days_ahead)).isoformat()

    for pattern in _DATE_PATTERNS:
        match = pattern.search(lowered)
        if not match:
            continue
        month_value = match.group("month")
        month = (
            _MONTHS.get(month_value.lower())
            if isinstance(month_value, str)
            else int(month_value)
        )
        value = _safe_date(
            int(match.group("year")) if match.group("year") else None,
            month,
            int(match.group("day")),
        )
        if value:
            if not match.group("year") and value < today:
                try:
                    value = value.replace(year=today.year + 1)
                except ValueError:
                    return None
            return value.isoformat()
    return None


def _extract_preferred_time(text):
    match = _TIME_PATTERN.search(text)
    if not match:
        return None
    hour = int(match.group("hour"))
    minute = int(match.group("minute") or 0)
    ampm = match.group("ampm").lower().replace(".", "")
    if ampm == "pm" and hour != 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute:02d}"


def _extract_address(text):
    match = re.search(
        r"\b(?:address|at|property address)\s*(?:is|:)?\s*(.+)$",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None
    value = match.group(1).strip(" ,.")
    if len(value) < 5:
        return None
    return value


def detect_entities(message):
    text = normalize_message(message)
    entities = {}
    for key, value in (
        ("email", _extract_email(text)),
        ("phone", _extract_phone(text)),
        ("approximate_size", _extract_size(text)),
        ("frequency", _extract_frequency(text)),
        ("property_type", _extract_property_type(text)),
        ("suburb", _extract_suburb(text)),
        ("preferred_date", _extract_preferred_date(text)),
        ("preferred_time", _extract_preferred_time(text)),
        ("address", _extract_address(text)),
    ):
        if value:
            entities[key] = value
    return entities


def analyze_message(message):
    return {
        "intent": detect_intent(message),
        "service": detect_service(message),
        "entities": detect_entities(message),
    }
