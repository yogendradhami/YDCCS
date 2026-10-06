from django.db.models import Q


# ============================================================
# RELATIONSHIP MATCHING
# ============================================================

def match_related_record(
    category,
    filename,
    text,
):
    """
    Attempt to identify an existing related database record.

    Supported relationship types:
        employee
        customer
        vehicle
        supplier
        contract

    Company-level categories deliberately do NOT attempt
    relationship matching.

    This prevents generic words such as:
        contract
        agreement
        renewal
        expiry
        service
        customer

    from incorrectly attaching a company document to a
    CleaningContract or another business record.
    """

    category = (category or "").strip().lower()

    haystack = (
        f"{filename or ''}\n{text or ''}"
    ).lower()

    # --------------------------------------------------------
    # COMPANY-LEVEL CATEGORIES
    # --------------------------------------------------------
    #
    # These categories must remain company-level even if the
    # document contains words such as "contract", "customer",
    # "employee", "renewal", etc.
    #
    company_categories = {
        "company",
        "insurance",
        "whs",
        "finance",
        "licence",
        "operations",
        "training",
        "marketing",
        "business_continuity",
        "quality",
        "privacy",
        "chemicals",
        "equipment",
        "other",
    }

    if category in company_categories:
        return {
            "related_type": "company",
            "object": None,
            "score": 0,
            "reason": (
                "Company-level document. "
                "No individual database relationship required."
            ),
        }

    # --------------------------------------------------------
    # EMPLOYEE
    # --------------------------------------------------------

    if category == "employee":
        return _match_employee(haystack)

    # --------------------------------------------------------
    # CUSTOMER
    # --------------------------------------------------------

    if category == "customer":
        return _match_customer(haystack)

    # --------------------------------------------------------
    # VEHICLE
    # --------------------------------------------------------

    if category == "vehicle":
        return _match_vehicle(haystack)

    # --------------------------------------------------------
    # SUPPLIER
    # --------------------------------------------------------

    if category == "supplier":
        return _match_supplier(haystack)

    # --------------------------------------------------------
    # CONTRACT
    # --------------------------------------------------------

    if category == "contract":
        return _match_contract(
            haystack,
            filename=filename,
        )

    # --------------------------------------------------------
    # UNKNOWN CATEGORY
    # --------------------------------------------------------

    return {
        "related_type": "company",
        "object": None,
        "score": 0,
        "reason": (
            f"No relationship matcher configured for "
            f"category '{category}'. Treated as company-level."
        ),
    }


# ============================================================
# EMPLOYEE MATCHING
# ============================================================

def _match_employee(haystack):
    from employees.models import Employee

    best = None
    best_score = 0
    best_reasons = []

    for employee in Employee.objects.all():
        name = (
            employee.full_name or ""
        ).strip()

        email = (
            employee.email or ""
        ).strip()

        phone = (
            employee.phone or ""
        ).strip()

        if not name:
            continue

        score = 0
        reasons = []

        # ----------------------------------------------------
        # Exact full-name match
        # ----------------------------------------------------

        if name.lower() in haystack:
            score += 90
            reasons.append(
                f"Employee name matched: {name}."
            )

        # ----------------------------------------------------
        # Email match
        # ----------------------------------------------------

        if email and email.lower() in haystack:
            score += 100
            reasons.append(
                f"Employee email matched: {email}."
            )

        # ----------------------------------------------------
        # Phone match
        # ----------------------------------------------------

        if phone:
            normalized_phone = _normalize_phone(phone)
            normalized_haystack = _normalize_phone(
                haystack
            )

            if (
                normalized_phone
                and normalized_phone in normalized_haystack
            ):
                score += 70
                reasons.append(
                    "Employee phone number matched."
                )

        if score > best_score:
            best = employee
            best_score = score
            best_reasons = reasons

    return {
        "related_type": "employee",
        "object": best,
        "score": min(best_score, 100),
        "reason": (
            " ".join(best_reasons)
            if best
            else "No employee match found."
        ),
    }


# ============================================================
# CUSTOMER MATCHING
# ============================================================

def _match_customer(haystack):
    from customers.models import Customer

    best = None
    best_score = 0
    best_reasons = []

    for customer in Customer.objects.all():
        name = (
            customer.full_name or ""
        ).strip()

        email = (
            customer.email or ""
        ).strip()

        phone = (
            customer.phone or ""
        ).strip()

        if not name:
            continue

        score = 0
        reasons = []

        # ----------------------------------------------------
        # Exact full-name match
        # ----------------------------------------------------

        if name.lower() in haystack:
            score += 90
            reasons.append(
                f"Customer name matched: {name}."
            )

        # ----------------------------------------------------
        # Email match
        # ----------------------------------------------------

        if email and email.lower() in haystack:
            score += 100
            reasons.append(
                f"Customer email matched: {email}."
            )

        # ----------------------------------------------------
        # Phone match
        # ----------------------------------------------------

        if phone:
            normalized_phone = _normalize_phone(phone)
            normalized_haystack = _normalize_phone(
                haystack
            )

            if (
                normalized_phone
                and normalized_phone in normalized_haystack
            ):
                score += 70
                reasons.append(
                    "Customer phone number matched."
                )

        if score > best_score:
            best = customer
            best_score = score
            best_reasons = reasons

    return {
        "related_type": "customer",
        "object": best,
        "score": min(best_score, 100),
        "reason": (
            " ".join(best_reasons)
            if best
            else "No customer match found."
        ),
    }


# ============================================================
# VEHICLE MATCHING
# ============================================================

def _match_vehicle(haystack):
    from dashboard.models import Vehicle

    best = None
    best_score = 0
    best_reasons = []

    normalized_haystack = _normalize_vehicle_text(
        haystack
    )

    for vehicle in Vehicle.objects.all():
        registration = (
            vehicle.registration_number or ""
        ).strip()

        vehicle_name = (
            vehicle.vehicle_name or ""
        ).strip()

        make = (
            vehicle.make or ""
        ).strip()

        model = (
            vehicle.model or ""
        ).strip()

        score = 0
        reasons = []

        # ----------------------------------------------------
        # Registration is strongest vehicle identifier
        # ----------------------------------------------------

        if registration:
            normalized_registration = (
                _normalize_vehicle_text(
                    registration
                )
            )

            if (
                normalized_registration
                and normalized_registration
                in normalized_haystack
            ):
                score += 100
                reasons.append(
                    "Vehicle registration matched."
                )

        # ----------------------------------------------------
        # Vehicle name
        # ----------------------------------------------------

        if (
            vehicle_name
            and vehicle_name.lower() in haystack
        ):
            score += 80
            reasons.append(
                f"Vehicle name matched: {vehicle_name}."
            )

        # ----------------------------------------------------
        # Make
        # ----------------------------------------------------

        if make and make.lower() in haystack:
            score += 20
            reasons.append(
                f"Vehicle make matched: {make}."
            )

        # ----------------------------------------------------
        # Model
        # ----------------------------------------------------

        if model and model.lower() in haystack:
            score += 15
            reasons.append(
                f"Vehicle model matched: {model}."
            )

        if score > best_score:
            best = vehicle
            best_score = score
            best_reasons = reasons

    return {
        "related_type": "vehicle",
        "object": best,
        "score": min(best_score, 100),
        "reason": (
            " ".join(best_reasons)
            if best
            else "No vehicle match found."
        ),
    }


# ============================================================
# SUPPLIER MATCHING
# ============================================================

def _match_supplier(haystack):
    from dashboard.models import Supplier

    best = None
    best_score = 0
    best_reasons = []

    for supplier in Supplier.objects.all():
        name = (
            supplier.name or ""
        ).strip()

        email = (
            supplier.email or ""
        ).strip()

        abn = (
            supplier.abn or ""
        ).strip()

        if not name and not email and not abn:
            continue

        score = 0
        reasons = []

        # ----------------------------------------------------
        # Supplier name
        # ----------------------------------------------------

        if name and name.lower() in haystack:
            score += 90
            reasons.append(
                f"Supplier name matched: {name}."
            )

        # ----------------------------------------------------
        # Supplier email
        # ----------------------------------------------------

        if email and email.lower() in haystack:
            score += 100
            reasons.append(
                "Supplier email matched."
            )

        # ----------------------------------------------------
        # ABN
        # ----------------------------------------------------

        if abn:
            normalized_abn = _normalize_digits(abn)
            normalized_haystack = _normalize_digits(
                haystack
            )

            if (
                normalized_abn
                and normalized_abn in normalized_haystack
            ):
                score += 100
                reasons.append(
                    "Supplier ABN matched."
                )

        if score > best_score:
            best = supplier
            best_score = score
            best_reasons = reasons

    return {
        "related_type": "supplier",
        "object": best,
        "score": min(best_score, 100),
        "reason": (
            " ".join(best_reasons)
            if best
            else "No supplier match found."
        ),
    }


# ============================================================
# CONTRACT MATCHING
# ============================================================

def _match_contract(
    haystack,
    filename="",
):
    """
    Match a document to an existing CleaningContract.

    Contract matching is deliberately conservative.

    A generic word such as:
        contract
        agreement
        renewal
        service
        expiry

    is NOT enough to identify a database contract.

    A contract should have meaningful customer/service evidence.
    """

    from contracts.models import CleaningContract

    best = None
    best_score = 0
    best_reasons = []

    # --------------------------------------------------------
    # Strong contract indicators
    # --------------------------------------------------------

    contract_indicators = {
        "cleaning contract",
        "cleaning agreement",
        "service agreement",
        "service contract",
        "contract agreement",
        "contract for cleaning",
    }

    has_strong_contract_indicator = any(
        indicator in haystack
        for indicator in contract_indicators
    )

    # --------------------------------------------------------
    # Generic terms are intentionally NOT sufficient.
    # --------------------------------------------------------

    generic_contract_terms = {
        "contract",
        "agreement",
        "renewal",
        "renewal date",
        "expiry",
        "expiry date",
        "service",
    }

    has_generic_contract_term = any(
        term in haystack
        for term in generic_contract_terms
    )

    for contract in CleaningContract.objects.select_related(
        "customer"
    ):
        score = 0
        reasons = []

        customer = contract.customer

        # ----------------------------------------------------
        # Customer name is the strongest contract relationship
        # ----------------------------------------------------

        if (
            customer
            and customer.full_name
            and customer.full_name.strip().lower()
            in haystack
        ):
            score += 80
            reasons.append(
                f"Contract customer matched: "
                f"{customer.full_name}."
            )

        # ----------------------------------------------------
        # Customer email
        # ----------------------------------------------------

        if (
            customer
            and customer.email
            and customer.email.strip().lower()
            in haystack
        ):
            score += 100
            reasons.append(
                "Contract customer email matched."
            )

        # ----------------------------------------------------
        # Customer phone
        # ----------------------------------------------------

        if customer and customer.phone:
            normalized_phone = _normalize_phone(
                customer.phone
            )

            normalized_haystack = _normalize_phone(
                haystack
            )

            if (
                normalized_phone
                and normalized_phone in normalized_haystack
            ):
                score += 70
                reasons.append(
                    "Contract customer phone matched."
                )

        # ----------------------------------------------------
        # Contract service type
        # ----------------------------------------------------

        if (
            contract.service_type
            and contract.service_type.strip().lower()
            in haystack
        ):
            score += 30
            reasons.append(
                f"Contract service matched: "
                f"{contract.service_type}."
            )

        # ----------------------------------------------------
        # Address/suburb matching
        #
        # Only use this as supporting evidence.
        # ----------------------------------------------------

        address = ""

        if customer:
            address = (
                getattr(customer, "address", "")
                or ""
            )

            suburb_postcode = (
                getattr(
                    customer,
                    "suburb_postcode",
                    "",
                )
                or ""
            )

            if (
                address
                and address.strip().lower()
                in haystack
            ):
                score += 25
                reasons.append(
                    "Customer address matched."
                )

            if (
                suburb_postcode
                and suburb_postcode.strip().lower()
                in haystack
            ):
                score += 15
                reasons.append(
                    "Customer suburb/postcode matched."
                )

        # ----------------------------------------------------
        # Contract-specific terminology
        #
        # This provides supporting evidence only.
        # It can NEVER create a relationship by itself.
        # ----------------------------------------------------

        if has_strong_contract_indicator:
            score += 15
            reasons.append(
                "Strong cleaning-contract terminology detected."
            )

        # Generic terms deliberately contribute nothing.
        #
        # This prevents a document such as:
        #
        # Annual Compliance Calendar
        #
        # containing "contract", "agreement" or "renewal"
        # from automatically being attached to a contract.
        #
        _ = has_generic_contract_term
        _ = generic_contract_terms

        if score > best_score:
            best = contract
            best_score = score
            best_reasons = reasons

    # --------------------------------------------------------
    # Conservative contract threshold
    # --------------------------------------------------------
    #
    # A contract relationship should require real database
    # evidence. A service-type-only match is not enough.
    #
    # 60+ means there is meaningful customer/contract evidence.
    # --------------------------------------------------------

    if best is None or best_score < 60:
        return {
            "related_type": "contract",
            "object": None,
            "score": 0,
            "reason": (
                "No sufficiently strong contract match found. "
                "Generic contract terminology is not enough "
                "to identify a database contract."
            ),
        }

    return {
        "related_type": "contract",
        "object": best,
        "score": min(best_score, 100),
        "reason": " ".join(best_reasons),
    }


# ============================================================
# NORMALISATION HELPERS
# ============================================================

def _normalize_phone(value):
    """
    Remove formatting from a phone number.

    Example:
        0412 345 678
        +61 412 345 678

    are normalised as digit strings.

    This improves matching when documents contain
    different phone formatting.
    """

    return _normalize_digits(value)


def _normalize_digits(value):
    """
    Return only numeric characters.
    """

    if not value:
        return ""

    return "".join(
        character
        for character in str(value)
        if character.isdigit()
    )


def _normalize_vehicle_text(value):
    """
    Normalise vehicle identifiers while preserving
    useful alphanumeric characters.
    """

    if not value:
        return ""

    return "".join(
        character.lower()
        for character in str(value)
        if character.isalnum()
    )