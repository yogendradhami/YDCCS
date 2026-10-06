import re
from datetime import datetime


DATE_PATTERNS = [
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
    r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b",
]


def extract_dates(text):
    """
    Find likely dates in document text.

    Returns dates as ISO strings.
    """

    if not text:
        return []

    found = []

    for pattern in DATE_PATTERNS:
        found.extend(
            re.findall(
                pattern,
                text,
                flags=re.IGNORECASE,
            )
        )

    results = []

    for value in found:
        parsed = parse_date(value)

        if parsed:
            results.append(parsed)

    return list(dict.fromkeys(results))


def parse_date(value):
    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d/%m/%y",
        "%d-%m-%y",
        "%Y/%m/%d",
        "%Y-%m-%d",
        "%d %B %Y",
        "%d %b %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(
                value.strip(),
                fmt,
            ).date().isoformat()

        except ValueError:
            continue

    return None

def extract_reference(text):
    if not text:
        return ""

    patterns = [
        r"\b(?:Document|Doc|Reference|Ref|Record|Form)\s*(?:ID|No|Number|#)?\s*[:\-]?\s*([A-Z]{2,10}[-_/][A-Z0-9_-]+)\b",
        r"\b(?:HR|WHS|OPS|CLI|LEG|SUP|CHEM|AST|FLEET|FIN|TRN|MKT|BCP|QMS|PRIV|CORP|INS)[-_][A-Z0-9_-]+\b",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return (
                match.group(1)
                if match.lastindex
                else match.group(0)
            )

    return ""


def extract_version(text):
    if not text:
        return ""

    patterns = [
        r"\bVersion\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)*)",
        r"\bVer\.?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)*)",
        r"\bv([0-9]+(?:\.[0-9]+)*)\b",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1)

    return ""