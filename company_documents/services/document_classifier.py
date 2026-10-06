import os
import re

from .document_metadata import (
    extract_reference,
    extract_version,
    extract_dates,
)


# ==========================================================
# GENERIC CATEGORY CLASSIFICATION RULES
# ==========================================================
#
# These rules are the FALLBACK classifier.
#
# Specific document identities are evaluated first below.
#
# ==========================================================

CLASSIFICATION_RULES = {
    "company": {
        "keywords": [
            "company policy",
            "business policy",
            "corporate",
            "company register",
            "business register",
            "company information",
            "business information",
            "annual business plan",
            "business plan",
            "corporate details",
            "abn",
        ],
        "document_types": [
            "Company Record",
        ],
    },

    "insurance": {
        "keywords": [
            "insurance",
            "certificate of currency",
            "public liability",
            "workers compensation",
            "professional indemnity",
            "policy number",
            "insured",
            "premium",
            "certificate of insurance",
        ],
        "document_types": [
            "Insurance Certificate",
        ],
    },

    "employee": {
        "keywords": [
            "employee",
            "employment agreement",
            "employment contract",
            "position description",
            "working rights",
            "identity document",
            "employee record",
            "emergency contact",
            "commencement date",
            "salary",
            "hourly rate",
        ],
        "document_types": [
            "Employment Agreement",
            "Position Description",
            "Working Rights Evidence",
            "Identity Document Record",
            "Employee Record",
        ],
    },

    "whs": {
        "keywords": [
            "whs",
            "work health and safety",
            "workplace health",
            "risk assessment",
            "hazard",
            "incident",
            "accident",
            "near miss",
            "safe work",
            "swms",
            "first aid",
        ],
        "document_types": [
            "WHS / Safety Record",
        ],
    },

    "operations": {
        "keywords": [
            "cleaning checklist",
            "cleaning schedule",
            "cleaning scope",
            "site checklist",
            "cleaning inspection",
            "cleaning procedure",
            "cleaning standard",
            "service checklist",
        ],
        "document_types": [
            "Cleaning Operations Record",
        ],
    },

    "customer": {
        "keywords": [
            "customer",
            "client",
            "client agreement",
            "service agreement",
            "site handover",
            "customer record",
            "client feedback",
            "customer feedback",
        ],
        "document_types": [
            "Client / Customer Record",
        ],
    },

    "contract": {
        "keywords": [
            "contract",
            "agreement",
            "terms and conditions",
            "service contract",
            "subcontractor agreement",
            "supplier agreement",
            "confidentiality agreement",
            "nda",
        ],
        "document_types": [
            "Contract / Agreement",
        ],
    },

    "supplier": {
        "keywords": [
            "supplier",
            "vendor",
            "purchase order",
            "supplier onboarding",
            "supplier register",
            "supplier agreement",
            "vendor agreement",
        ],
        "document_types": [
            "Supplier Record",
        ],
    },

    "chemicals": {
        "keywords": [
            "sds",
            "safety data sheet",
            "chemical",
            "cleaning chemical",
            "hazardous substance",
            "dilution",
            "chemical register",
            "spill",
        ],
        "document_types": [
            "Chemical / SDS Record",
        ],
    },

    "equipment": {
        "keywords": [
            "equipment",
            "asset register",
            "asset",
            "machine",
            "vacuum",
            "polisher",
            "equipment register",
            "equipment inspection",
        ],
        "document_types": [
            "Equipment / Asset Record",
        ],
    },

    "vehicle": {
        "keywords": [
            "vehicle",
            "registration",
            "rego",
            "odometer",
            "vehicle inspection",
            "vehicle insurance",
            "fleet",
            "driver",
            "make",
            "model",
        ],
        "document_types": [
            "Vehicle / Fleet Record",
        ],
    },

    "finance": {
        "keywords": [
            "invoice",
            "receipt",
            "payment",
            "financial",
            "accounting",
            "expense",
            "purchase",
            "gst",
            "tax invoice",
        ],
        "document_types": [
            "Finance / Accounting Record",
        ],
    },

    "training": {
        "keywords": [
            "training",
            "certificate",
            "competency",
            "competent",
            "course",
            "qualification",
            "induction",
            "training record",
        ],
        "document_types": [
            "Training / Competency Record",
        ],
    },

    "marketing": {
        "keywords": [
            "marketing",
            "brand",
            "campaign",
            "advertisement",
            "brochure",
            "social media",
            "marketing asset",
        ],
        "document_types": [
            "Marketing / Brand Record",
        ],
    },

    "business_continuity": {
        "keywords": [
            "business continuity",
            "continuity plan",
            "disaster recovery",
            "emergency response",
            "business interruption",
            "recovery plan",
        ],
        "document_types": [
            "Business Continuity Record",
        ],
    },

    "quality": {
        "keywords": [
            "quality",
            "quality inspection",
            "quality assurance",
            "quality management",
            "non-conformance",
            "corrective action",
            "audit",
            "inspection",
        ],
        "document_types": [
            "Quality Management Record",
        ],
    },

    "privacy": {
        "keywords": [
            "privacy",
            "personal information",
            "personal data",
            "confidential",
            "data protection",
            "privacy breach",
            "information security",
            "data retention",
        ],
        "document_types": [
            "Privacy / Data Protection Record",
        ],
    },
}


# ==========================================================
# SPECIFIC DOCUMENT IDENTIFICATION
# ==========================================================
#
# Specific document identity ALWAYS beats generic category
# keywords.
#
# Higher priority = stronger identity.
#
# IMPORTANT:
# Filename matches and exact document names are intentionally
# handled before broad content classification.
#
# ==========================================================

SPECIFIC_RULES = [

    # ======================================================
    # COMPANY & CORPORATE
    # ======================================================

    {
        "category": "company",
        "document_type": "Annual Business Plan",
        "keywords": [
            "annual business plan",
            "company business plan",
        ],
        "priority": 120,
    },

    {
        "category": "company",
        "document_type": "ABN / Corporate Details Record",
        "keywords": [
            "abn and corporate details record",
            "abn corporate details",
            "corporate details record",
            "abn record",
            "abn details",
            "australian business number",
            "company abn",
        ],
        "priority": 120,
    },

    {
        "category": "company",
        "document_type": "Company Record",
        "keywords": [
            "company record",
            "company information",
            "company register",
            "business register",
            "corporate record",
        ],
        "priority": 110,
    },

    {
        "category": "company",
        "document_type": "Company Policy",
        "keywords": [
            "company policy",
            "business policy",
            "corporate policy",
        ],
        "priority": 105,
    },

    {
        "category": "company",
        "document_type": "Annual Compliance Calendar",
        "keywords": [
            "annual compliance calendar",
            "compliance calendar",
            "annual compliance schedule",
        ],
        "priority": 125,
    },


    # ======================================================
    # INSURANCE
    # ======================================================

    {
        "category": "insurance",
        "document_type": "Insurance Certificate",
        "keywords": [
            "insurance certificate",
            "certificate of insurance",
            "certificate of currency",
            "public liability insurance",
            "workers compensation insurance",
            "professional indemnity insurance",
        ],
        "priority": 120,
    },


    # ======================================================
    # EMPLOYEE / HR
    # ======================================================

    {
        "category": "employee",
        "document_type": "Working Rights Evidence",
        "keywords": [
            "working rights evidence",
            "working rights",
            "work rights evidence",
            "right to work",
            "rights to work",
            "work entitlement",
            "vevo",
            "visa evidence",
            "work rights verified",
            "permitted to work",
        ],
        "priority": 120,
    },

    {
        "category": "employee",
        "document_type": "Identity Document Record",
        "keywords": [
            "identity document record",
            "identity document",
            "identity verification",
            "passport record",
            "driver licence record",
            "driver license record",
            "document was sighted",
        ],
        "priority": 115,
    },

    {
        "category": "employee",
        "document_type": "Employment Agreement",
        "keywords": [
            "employment agreement",
            "employment contract",
            "contract of employment",
            "terms of employment",
            "employment terms",
        ],
        "priority": 110,
    },

    {
        "category": "employee",
        "document_type": "Position Description",
        "keywords": [
            "position description",
            "job description",
            "position profile",
            "role description",
        ],
        "priority": 110,
    },

    {
        "category": "employee",
        "document_type": "Employee Record",
        "keywords": [
            "employee record",
            "employee information record",
            "employee file",
            "employee details",
            "employee profile",
        ],
        "priority": 105,
    },

    {
        "category": "employee",
        "document_type": "Confidentiality Acknowledgement",
        "keywords": [
            "confidentiality acknowledgement",
            "confidentiality acknowledgment",
            "confidentiality acknowledgement form",
            "confidentiality acknowledgment form",
            "employee confidentiality acknowledgement",
            "employee confidentiality acknowledgment",
            "confidentiality undertaking",
        ],
        "priority": 125,
    },


    # ======================================================
    # WHS / SAFETY
    # ======================================================

    {
        "category": "whs",
        "document_type": "WHS / Safety Record",
        "keywords": [
            "whs record",
            "whs safety record",
            "work health and safety record",
            "safety record",
            "risk assessment",
            "hazard assessment",
            "incident report",
            "accident report",
            "incident accident report",
            "incident / accident report",
            "near miss report",
            "safe work method statement",
            "swms",
        ],
        "priority": 125,
    },

    {
        "category": "whs",
        "document_type": "WHS / Safety Record",
        "keywords": [
            "whs induction checklist",
            "whs induction",
            "work health and safety induction",
            "safety induction checklist",
            "workplace safety induction",
        ],
        "priority": 130,
    },


    # ======================================================
    # OPERATIONS
    # ======================================================

    {
        "category": "operations",
        "document_type": "Cleaning Operations Record",
        "keywords": [
            "cleaning checklist",
            "cleaning schedule",
            "cleaning scope",
            "site checklist",
            "cleaning inspection",
            "cleaning procedure",
            "cleaning standard",
            "service checklist",
        ],
        "priority": 110,
    },

    {
        "category": "operations",
        "document_type": "Cleaning Operations Record",
        "keywords": [
            "site handover record",
            "client site handover",
            "site handover checklist",
            "cleaning site handover",
        ],
        "priority": 115,
    },


    # ======================================================
    # CUSTOMER
    # ======================================================

    {
        "category": "customer",
        "document_type": "Client / Customer Record",
        "keywords": [
            "client / customer record",
            "client customer record",
            "customer record",
            "client record",
            "customer information",
            "client information",
            "client feedback",
            "customer feedback",
        ],
        "priority": 110,
    },


    # ======================================================
    # CONTRACTS & LEGAL
    # ======================================================

    {
        "category": "contract",
        "document_type": "Contract / Agreement",
        "keywords": [
            "client service agreement",
            "client service contract",
            "service agreement",
            "service contract",
            "subcontractor agreement",
            "subcontractor contract",
            "supplier agreement",
            "supplier contract",
            "confidentiality agreement",
            "non disclosure agreement",
            "non-disclosure agreement",
            "nda",
            "contract / agreement",
            "contract agreement",
        ],
        "priority": 120,
    },


    # ======================================================
    # SUPPLIERS
    # ======================================================

    {
        "category": "supplier",
        "document_type": "Supplier Record",
        "keywords": [
            "supplier onboarding record",
            "supplier onboarding form",
            "supplier onboarding",
            "supplier record",
            "supplier register",
            "supplier information",
            "vendor record",
            "vendor information",
            "supplier details",
        ],
        "priority": 125,
    },


    # ======================================================
    # CHEMICALS / SDS
    # ======================================================

    {
        "category": "chemicals",
        "document_type": "Chemical / SDS Record",
        "keywords": [
            "safety data sheet",
            "sds",
            "chemical safety data",
            "chemical register",
            "cleaning chemical",
            "hazardous substance",
            "chemical dilution",
        ],
        "priority": 115,
    },


    # ======================================================
    # EQUIPMENT / ASSETS
    # ======================================================

    {
        "category": "equipment",
        "document_type": "Equipment / Asset Record",
        "keywords": [
            "equipment record",
            "equipment register",
            "asset register",
            "asset record",
            "equipment inspection",
            "equipment maintenance",
        ],
        "priority": 110,
    },


    # ======================================================
    # VEHICLE / FLEET
    # ======================================================

    {
        "category": "vehicle",
        "document_type": "Vehicle / Fleet Record",
        "keywords": [
            "vehicle record",
            "vehicle register",
            "fleet record",
            "fleet register",
            "vehicle inspection",
            "vehicle insurance",
            "registration record",
        ],
        "priority": 110,
    },


    # ======================================================
    # FINANCE
    # ======================================================

    {
        "category": "finance",
        "document_type": "Finance / Accounting Record",
        "keywords": [
            "finance record",
            "accounting record",
            "financial record",
            "tax invoice",
            "expense record",
            "payment record",
            "receipt",
            "invoice",
        ],
        "priority": 105,
    },


    # ======================================================
    # TRAINING
    # ======================================================

    {
        "category": "training",
        "document_type": "Training / Competency Record",
        "keywords": [
            "training record",
            "training certificate",
            "competency record",
            "competency certificate",
            "qualification record",
            "induction record",
        ],
        "priority": 110,
    },


    # ======================================================
    # MARKETING
    # ======================================================

    {
        "category": "marketing",
        "document_type": "Marketing / Brand Record",
        "keywords": [
            "marketing record",
            "marketing asset",
            "brand asset",
            "marketing campaign",
            "advertising campaign",
            "social media",
            "brochure",
        ],
        "priority": 105,
    },


    # ======================================================
    # BUSINESS CONTINUITY
    # ======================================================

    {
        "category": "business_continuity",
        "document_type": "Business Continuity Record",
        "keywords": [
            "business continuity plan",
            "business continuity record",
            "continuity plan",
            "disaster recovery plan",
            "business interruption plan",
            "recovery plan",
        ],
        "priority": 115,
    },


    # ======================================================
    # QUALITY
    # ======================================================

    {
        "category": "quality",
        "document_type": "Quality Management Record",
        "keywords": [
            "quality management record",
            "quality inspection",
            "quality assurance record",
            "quality management",
            "non-conformance",
            "corrective action",
        ],
        "priority": 110,
    },


    # ======================================================
    # PRIVACY
    # ======================================================

    {
        "category": "privacy",
        "document_type": "Privacy / Data Protection Record",
        "keywords": [
            "privacy record",
            "privacy policy",
            "privacy breach",
            "data protection record",
            "personal data protection",
            "information security record",
            "data retention",
        ],
        "priority": 110,
    },
]


def classify_document(filename, text=""):
    """
    Classify a document using filename/content rules.

    Classification order:

    1. Specific document identity.
    2. Generic category keywords.
    3. Unknown / manual review.

    Specific document identities always take priority over
    broad category words.
    """

    filename_text = os.path.splitext(
        filename or ""
    )[0].lower().strip()

    content = (text or "").lower()

    combined = f"{filename_text}\n{content}"

    # ==========================================================
    # SPECIFIC DOCUMENT-TYPE DETECTION
    # ==========================================================

    specific_matches = []

    for rule in SPECIFIC_RULES:

        matched_keywords = []

        for keyword in rule["keywords"]:

            keyword = keyword.lower().strip()

            if keyword in filename_text:

                matched_keywords.append(
                    f"Filename contains '{keyword}'"
                )

            elif keyword in content:

                matched_keywords.append(
                    f"Content contains '{keyword}'"
                )

        if matched_keywords:

            specific_matches.append(
                {
                    "rule": rule,
                    "matches": matched_keywords,
                }
            )

    if specific_matches:

        def specific_sort_key(entry):

            rule = entry["rule"]

            matched_keyword_lengths = []

            for keyword in rule["keywords"]:

                keyword = keyword.lower()

                if any(
                    keyword in match.lower()
                    for match in entry["matches"]
                ):
                    matched_keyword_lengths.append(
                        len(keyword)
                    )

            longest_match = (
                max(matched_keyword_lengths)
                if matched_keyword_lengths
                else 0
            )

            return (
                rule["priority"],
                len(entry["matches"]),
                longest_match,
            )

        specific_matches.sort(
            key=specific_sort_key,
            reverse=True,
        )

        selected = specific_matches[0]

        rule = selected["rule"]

        reasons = selected["matches"]

        confidence = min(
            99,
            88 + min(
                len(reasons) * 3,
                11,
            ),
        )

        reference = extract_reference(text)

        version = extract_version(text)

        dates = extract_dates(text)

        sensitive = detect_sensitive(
            filename,
            text,
            rule["category"],
        )

        return {
            "category": rule["category"],
            "document_type": rule["document_type"],
            "confidence_score": confidence,
            "confidence_label": (
                "Very High"
                if confidence >= 95
                else "High"
            ),
            "reasons": reasons[:10],
            "reference": reference,
            "version": version,
            "dates": dates,
            "sensitive": sensitive,
        }

    # ==========================================================
    # GENERIC CATEGORY CLASSIFICATION
    # ==========================================================

    scores = {}

    reasons = {}

    for category, rule in CLASSIFICATION_RULES.items():

        score = 0

        category_reasons = []

        for keyword in rule["keywords"]:

            keyword = keyword.lower().strip()

            if keyword in filename_text:

                score += 12

                category_reasons.append(
                    f"Filename contains '{keyword}'"
                )

            elif keyword in content:

                score += 5

                category_reasons.append(
                    f"Content contains '{keyword}'"
                )

        scores[category] = score

        reasons[category] = category_reasons

    if not scores:

        return _unknown_result()

    category = max(
        scores,
        key=scores.get,
    )

    score = scores[category]

    if score <= 0:

        return _unknown_result()

    confidence = min(
        99,
        max(
            35,
            50 + score,
        ),
    )

    rule = CLASSIFICATION_RULES[category]

    document_type = rule["document_types"][0]

    reference = extract_reference(text)

    version = extract_version(text)

    dates = extract_dates(text)

    sensitive = detect_sensitive(
        filename,
        text,
        category,
    )

    if confidence >= 90:

        confidence_label = "High"

    elif confidence >= 70:

        confidence_label = "Medium"

    else:

        confidence_label = "Low"

    return {
        "category": category,
        "document_type": document_type,
        "confidence_score": confidence,
        "confidence_label": confidence_label,
        "reasons": reasons[category][:10],
        "reference": reference,
        "version": version,
        "dates": dates,
        "sensitive": sensitive,
    }


def detect_sensitive(filename, text, category):
    """
    Determine whether a document should be treated as sensitive.

    Employee documents are always considered sensitive.

    Other categories are marked sensitive when the document
    contains clearly sensitive identity, financial, credential,
    medical, or private-information indicators.
    """

    value = (
        f"{filename}\n{text}"
    ).lower()

    sensitive_terms = [
        "passport",
        "driver licence",
        "driver license",
        "identity document",
        "working rights",
        "bank account",
        "tax file number",
        "tfn",
        "tfns",
        "password",
        "medical",
        "employee personal",
        "confidential",
        "private information",
    ]

    if category == "employee":

        return True

    return any(
        term in value
        for term in sensitive_terms
    )


def _unknown_result():
    """
    Return a conservative result when no classification
    rule produces meaningful evidence.

    Low-confidence documents should remain reviewable
    rather than being automatically imported.
    """

    return {
        "category": "other",
        "document_type": "Unclassified Document",
        "confidence_score": 25,
        "confidence_label": "Low",
        "reasons": [
            "No strong classification rule matched."
        ],
        "reference": "",
        "version": "",
        "dates": [],
        "sensitive": False,
    }