import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from dashboard.models import PurchaseOrder, Supplier

from company_documents.services.document_extractor import extract_text
from company_documents.models import (
    CompanyDocument,
    CompanyDocumentAudit,
    InvoiceDocumentReview,
)


INVOICE_FILE_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
MONEY_PATTERN = r"(?:AUD\s*)?\$?\s*([0-9][0-9,]*(?:\.\d{1,2})?)"
DATE_FORMATS = (
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d",
    "%d %b %Y",
    "%d %B %Y",
    "%d-%b-%Y",
    "%d-%B-%Y",
)


def is_invoice_document(document):
    if document.category == CompanyDocument.Category.FINANCE:
        return True
    document_labels = f"{document.name} {document.document_type}".casefold()
    return (
        document.related_type == CompanyDocument.RelatedType.SUPPLIER
        and any(word in document_labels for word in ("invoice", "receipt", "bill"))
    )


def validate_invoice_document_file(uploaded_file):
    if uploaded_file.size > settings.COMPANY_DOCUMENT_MAX_SIZE:
        raise ValueError("Invoice documents cannot exceed 50 MB.")
    extension = Path(uploaded_file.name.replace("\\", "/")).suffix.lower()
    if extension not in INVOICE_FILE_EXTENSIONS:
        raise ValueError("Invoice documents must be PDF, JPEG, PNG, or WebP files.")

    uploaded_file.seek(0)
    signature = uploaded_file.read(16)
    uploaded_file.seek(0)
    valid = (
        signature.startswith(b"%PDF-")
        if extension == ".pdf"
        else signature.startswith(b"\xff\xd8\xff")
        if extension in {".jpg", ".jpeg"}
        else signature.startswith(b"\x89PNG\r\n\x1a\n")
        if extension == ".png"
        else (
            len(signature) >= 12
            and signature[:4] == b"RIFF"
            and signature[8:12] == b"WEBP"
        )
    )
    if not valid:
        raise ValueError(
            "The invoice file content does not match its PDF or image extension."
        )


def normalize_invoice_number(value):
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())[:150]


def extract_invoice_fields(text, *, method="", extraction_error=""):
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    source = "\n".join(lines)
    values = {}
    confidence = {}
    validation_errors = []

    values["supplier_name"], confidence["supplier_name"] = _label_value(
        source,
        r"(?:supplier|vendor|issued\s+by|from)\s*(?:name)?",
    )
    if not values["supplier_name"]:
        values["supplier_name"] = _first_supplier_candidate(lines)
        confidence["supplier_name"] = 0.35 if values["supplier_name"] else 0.0

    raw_abn = _label_value(
        source,
        r"(?:australian\s+business\s+number|ABN)",
    )[0]
    abn = re.sub(r"\D", "", raw_abn)
    values["abn"] = abn if len(abn) == 11 else ""
    confidence["abn"] = 0.95 if values["abn"] and is_valid_abn(abn) else (
        0.4 if values["abn"] else 0.0
    )
    if values["abn"] and not is_valid_abn(abn):
        validation_errors.append("The extracted ABN does not pass its checksum.")

    values["invoice_number"], confidence["invoice_number"] = _label_value(
        source,
        r"(?:invoice\s*(?:number|no\.?|#|id|ref(?:erence)?)|tax\s+invoice\s*(?:number|no\.?|#))",
    )
    invoice_number_parts = values["invoice_number"].split()
    values["invoice_number"] = (
        invoice_number_parts[0].strip("#:;")[:150]
        if invoice_number_parts
        else ""
    )

    values["invoice_date"], confidence["invoice_date"] = _label_date(
        source,
        r"(?:invoice|issue|issued)\s*date",
    )
    values["due_date"], confidence["due_date"] = _label_date(
        source,
        r"(?:payment\s*)?due\s*date|due\s*by",
    )
    if (
        values["invoice_date"]
        and values["due_date"]
        and values["due_date"] < values["invoice_date"]
    ):
        validation_errors.append("The due date is earlier than the invoice date.")

    values["subtotal"], confidence["subtotal"] = _label_money(
        source,
        r"(?:sub\s*total|subtotal|net\s*amount|net\s*total)",
    )
    values["gst"], confidence["gst"] = _label_money(
        source,
        r"(?:GST|goods\s+and\s+services\s+tax|tax\s+amount)",
    )
    values["total"], confidence["total"] = _label_money(
        source,
        r"(?:grand\s*total|invoice\s*total|total\s*amount|amount\s*due|total)",
    )

    line_items = _extract_line_items(lines)
    values["line_items"] = line_items
    confidence["line_items"] = 0.75 if line_items else 0.0

    values["description"], confidence["description"] = _label_value(
        source,
        r"(?:description|details|goods\s+or\s+services)",
    )
    if not values["description"] and line_items:
        values["description"] = "; ".join(
            item["description"] for item in line_items[:3]
        )
        confidence["description"] = 0.6

    values["payment_status"] = _extract_payment_claim(source)
    confidence["payment_status"] = 0.65 if values["payment_status"] != "unknown" else 0.0
    if "ocr" in method:
        confidence = {
            field: round(value * 0.85, 2)
            for field, value in confidence.items()
        }

    subtotal = _decimal_or_none(values["subtotal"])
    gst = _decimal_or_none(values["gst"])
    total = _decimal_or_none(values["total"])
    if subtotal is not None and gst is not None and total is not None:
        if abs(subtotal + gst - total) > Decimal("0.02"):
            validation_errors.append(
                "Subtotal plus GST does not match the extracted total."
            )
    elif gst is not None and total is not None and gst > total:
        validation_errors.append("The extracted GST is greater than the total.")
    if extraction_error:
        validation_errors.append(extraction_error)

    return {
        "data": values,
        "confidence": confidence,
        "validation_errors": validation_errors,
        "method": method,
        "error": extraction_error,
    }


def create_invoice_review(document, uploaded_file):
    if not is_invoice_document(document):
        return None

    existing = InvoiceDocumentReview.objects.filter(document=document).first()
    if existing:
        return existing, False

    if uploaded_file:
        validate_invoice_document_file(uploaded_file)
        extraction = extract_text(uploaded_file)
    else:
        extraction = {
            "text": "",
            "method": "unavailable",
            "error": "The original upload was not available for extraction.",
        }

    parsed = extract_invoice_fields(
        extraction.get("text", ""),
        method=extraction.get("method", ""),
        extraction_error=extraction.get("error", ""),
    )
    supplier = document.supplier
    if supplier is None:
        supplier = _suggest_supplier(
            parsed["data"].get("supplier_name", ""),
            parsed["data"].get("abn", ""),
        )
    purchase_order = _suggest_purchase_order(
        supplier=supplier,
        data=parsed["data"],
    )
    suggested_expense_category = _suggest_expense_category(
        document=document,
        data=parsed["data"],
        has_purchase_order=bool(purchase_order),
    )
    normalized_number = normalize_invoice_number(
        parsed["data"].get("invoice_number")
    )
    duplicate = None
    if normalized_number:
        duplicate_query = InvoiceDocumentReview.objects.filter(
            normalized_invoice_number=normalized_number,
        ).exclude(status=InvoiceDocumentReview.Status.REJECTED)
        if supplier:
            duplicate_query = duplicate_query.filter(
                Q(supplier=supplier) | Q(suggested_supplier=supplier)
            )
            duplicate = duplicate_query.select_related("document").first()
        else:
            supplier_name = _normalize_name(parsed["data"].get("supplier_name", ""))
            candidates = duplicate_query.select_related(
                "document",
                "supplier",
                "suggested_supplier",
            ).order_by("pk")
            for candidate in candidates:
                candidate_name = (
                    candidate.supplier.name
                    if candidate.supplier_id
                    else (
                        candidate.suggested_supplier.name
                        if candidate.suggested_supplier_id
                        else candidate.extracted_data.get("supplier_name", "")
                    )
                )
                if supplier_name and _normalize_name(candidate_name) == supplier_name:
                    duplicate = candidate
                    break
        if duplicate:
            parsed["validation_errors"].append(
                f"Possible duplicate invoice of document #{duplicate.document_id}."
            )

    review, created = InvoiceDocumentReview.objects.get_or_create(
        document=document,
        defaults={
            "extracted_data": parsed["data"],
            "confidence": parsed["confidence"],
            "validation_errors": parsed["validation_errors"],
            "extraction_method": parsed["method"],
            "extraction_error": parsed["error"],
            "suggested_expense_category": suggested_expense_category,
            "normalized_invoice_number": normalized_number,
            "suggested_supplier": supplier,
            "supplier": document.supplier,
            "suggested_purchase_order": purchase_order,
            "duplicate_of": duplicate,
        },
    )
    if created:
        from dashboard.operations_automation import record_operations_event

        record_operations_event(
            module="Finance",
            event=f"Supplier invoice {document.name} needs review",
            trigger="A supplier invoice was added to Company Documents.",
            action_taken="Extracted invoice fields and prepared a review record.",
            result="Invoice remains pending verification; no expense or stock was changed.",
            actor=document.uploaded_by,
            metadata={
                "invoice_review_id": review.pk,
                "document_id": document.pk,
                "supplier_id": supplier.pk if supplier else None,
            },
            idempotency_key=f"invoice-review-created:{review.pk}",
            link=reverse(
                "company_documents:invoice_review_detail",
                kwargs={"review_id": review.pk},
            ),
        )
    return review, created


def _suggest_expense_category(*, document, data, has_purchase_order):
    if has_purchase_order:
        return "cleaning_supplies"
    text = " ".join(
        [
            document.name,
            document.document_type,
            data.get("description", ""),
            *(item.get("description", "") for item in data.get("line_items", [])),
        ]
    ).casefold()
    categories = (
        ("fuel", ("fuel", "petrol", "diesel", "unleaded")),
        ("vehicle", ("vehicle", "registration", "rego", "toll")),
        ("equipment", ("equipment", "vacuum", "machine", "tool")),
        ("cleaning_supplies", ("cleaning", "detergent", "chemical", "disinfectant")),
        ("insurance", ("insurance", "premium", "policy")),
        ("software", ("software", "subscription", "hosting", "licence")),
        ("marketing", ("marketing", "advertising", "campaign")),
        ("office", ("office", "stationery", "printer")),
    )
    return next(
        (
            category
            for category, keywords in categories
            if any(keyword in text for keyword in keywords)
        ),
        "other",
    )


@transaction.atomic
def verify_invoice_review(*, review_id, actor, verified_data):
    review = (
        InvoiceDocumentReview.objects.select_for_update()
        .select_related("document")
        .get(pk=review_id)
    )
    if review.status not in {
        InvoiceDocumentReview.Status.PENDING,
        InvoiceDocumentReview.Status.VERIFIED,
    }:
        raise ValidationError("Only pending or verified invoice reviews can be updated.")

    supplier = verified_data["supplier"]
    invoice_number = verified_data["invoice_number"].strip()
    normalized_number = normalize_invoice_number(invoice_number)
    if not normalized_number:
        raise ValidationError("Enter an invoice number containing letters or digits.")
    duplicate = InvoiceDocumentReview.objects.filter(
        supplier=supplier,
        normalized_invoice_number=normalized_number,
        status__in=(
            InvoiceDocumentReview.Status.VERIFIED,
            InvoiceDocumentReview.Status.APPROVED,
        ),
    ).exclude(pk=review.pk)
    if duplicate.exists():
        existing = duplicate.order_by("pk").first()
        raise ValidationError(
            f"This supplier invoice number is already verified in review #{existing.pk}."
        )

    verified_values = {
        key: value
        for key, value in verified_data.items()
        if key != "supplier"
    }
    verified_values["line_items"] = verified_values.pop(
        "line_items_json",
        verified_values.get("line_items", []),
    )
    for field in ("invoice_date", "due_date"):
        if verified_values.get(field):
            verified_values[field] = verified_values[field].isoformat()
    for field in ("subtotal", "gst", "total"):
        value = verified_values.get(field)
        if value is not None:
            verified_values[field] = format(value, ".2f")
    verified_values["payment_status"] = "unconfirmed"

    review.supplier = supplier
    review.normalized_invoice_number = normalized_number
    review.verified_data = verified_values
    review.status = InvoiceDocumentReview.Status.VERIFIED
    review.reviewed_by = actor
    review.reviewed_at = timezone.now()
    review.review_notes = ""
    review.save(
        update_fields=[
            "supplier",
            "normalized_invoice_number",
            "verified_data",
            "status",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
            "updated_at",
        ]
    )
    CompanyDocumentAudit.objects.create(
        document=review.document,
        user=actor,
        action=CompanyDocumentAudit.Action.UPDATED,
        metadata={
            "event": "invoice_document_verified",
            "invoice_review_id": review.pk,
            "supplier_id": supplier.pk,
            "invoice_number": invoice_number,
        },
    )
    from dashboard.operations_automation import record_operations_event

    record_operations_event(
        module="Finance",
        event=f"Supplier invoice {invoice_number} verified",
        trigger="Authorised manager verified extracted invoice details.",
        action_taken="Invoice data was verified for review.",
        result="No expense was posted and payment status remains unconfirmed.",
        actor=actor,
        metadata={"invoice_review_id": review.pk, "supplier_id": supplier.pk},
        idempotency_key=f"invoice-review-verified:{review.pk}",
        link=reverse(
            "company_documents:invoice_review_detail",
            kwargs={"review_id": review.pk},
        ),
    )
    return review


@transaction.atomic
def reject_invoice_review(*, review_id, actor, review_notes):
    review = (
        InvoiceDocumentReview.objects.select_for_update()
        .select_related("document")
        .get(pk=review_id)
    )
    review_notes = review_notes.strip()
    if len(review_notes) < 3:
        raise ValidationError("Provide a reason for rejecting the invoice review.")
    if review.status in {
        InvoiceDocumentReview.Status.APPROVED,
        InvoiceDocumentReview.Status.REJECTED,
    }:
        raise ValidationError("This invoice review can no longer be rejected.")

    review.status = InvoiceDocumentReview.Status.REJECTED
    review.review_notes = review_notes
    review.reviewed_by = actor
    review.reviewed_at = timezone.now()
    review.save(
        update_fields=[
            "status",
            "review_notes",
            "reviewed_by",
            "reviewed_at",
            "updated_at",
        ]
    )
    CompanyDocumentAudit.objects.create(
        document=review.document,
        user=actor,
        action=CompanyDocumentAudit.Action.UPDATED,
        metadata={
            "event": "invoice_document_rejected",
            "invoice_review_id": review.pk,
            "reason": review_notes,
        },
    )
    from dashboard.operations_automation import record_operations_event

    record_operations_event(
        module="Finance",
        event=f"Supplier invoice review #{review.pk} rejected",
        trigger="Authorised manager rejected an invoice document.",
        action_taken=f"Recorded rejection reason: {review_notes}",
        result="No expense or stock was changed.",
        actor=actor,
        metadata={"invoice_review_id": review.pk},
        idempotency_key=f"invoice-review-rejected:{review.pk}",
        link=reverse(
            "company_documents:invoice_review_detail",
            kwargs={"review_id": review.pk},
        ),
    )
    return review


@transaction.atomic
def post_verified_invoice_review(
    *,
    review_id,
    actor,
    expense_category,
    purchase_order_id=None,
):
    from expenses.models import Expense

    review = (
        InvoiceDocumentReview.objects.select_for_update(of=("self",))
        .select_related("document", "supplier")
        .get(pk=review_id)
    )
    existing_expense = Expense.objects.filter(invoice_review=review).first()
    if review.status == InvoiceDocumentReview.Status.APPROVED:
        if existing_expense:
            return existing_expense, False
        raise ValidationError(
            "This invoice is marked approved but its expense record is missing."
        )
    if review.status != InvoiceDocumentReview.Status.VERIFIED:
        raise ValidationError("Only verified invoices can be approved for posting.")
    if expense_category not in dict(Expense.CATEGORY_CHOICES):
        raise ValidationError("Select a valid expense category.")
    if existing_expense:
        raise ValidationError(
            "An expense already references this invoice; contact an administrator."
        )

    purchase_order = None
    if purchase_order_id:
        purchase_order = PurchaseOrder.objects.select_for_update().get(
            pk=purchase_order_id
        )
        if purchase_order.status == "cancelled":
            raise ValidationError("A cancelled purchase order cannot be linked.")
        if purchase_order.supplier_name.strip().casefold() != review.supplier.name.strip().casefold():
            raise ValidationError(
                "The purchase order supplier does not match the verified invoice supplier."
            )

    verified = review.verified_data
    try:
        invoice_date = datetime.fromisoformat(verified["invoice_date"]).date()
        due_date = (
            datetime.fromisoformat(verified["due_date"]).date()
            if verified.get("due_date")
            else None
        )
        amount = Decimal(verified["total"])
        gst_amount = (
            Decimal(verified["gst"])
            if verified.get("gst") not in (None, "")
            else None
        )
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise ValidationError(
            "The verified invoice is missing a valid date, GST, or total."
        ) from exc
    if amount < 0 or (gst_amount is not None and gst_amount < 0):
        raise ValidationError("Verified invoice amounts cannot be negative.")

    expense = Expense.objects.create(
        invoice_review=review,
        supplier=review.supplier,
        purchase_order=purchase_order,
        invoice_number=verified["invoice_number"],
        date=invoice_date,
        due_date=due_date,
        category=expense_category,
        description=verified["description"][:255],
        amount=amount,
        gst_amount=gst_amount,
        payment_status=Expense.PaymentStatus.UNCONFIRMED,
        recorded_by=actor,
        notes=(
            f"Posted from verified Company Documents invoice "
            f"#{review.document_id}. Payment status remains unconfirmed."
        ),
    )
    review.status = InvoiceDocumentReview.Status.APPROVED
    review.suggested_purchase_order = purchase_order
    review.reviewed_by = actor
    review.reviewed_at = timezone.now()
    review.save(
        update_fields=[
            "status",
            "suggested_purchase_order",
            "reviewed_by",
            "reviewed_at",
            "updated_at",
        ]
    )
    CompanyDocumentAudit.objects.create(
        document=review.document,
        user=actor,
        action=CompanyDocumentAudit.Action.UPDATED,
        metadata={
            "event": "invoice_document_posted_to_expenses",
            "invoice_review_id": review.pk,
            "expense_id": expense.pk,
            "supplier_id": review.supplier_id,
            "purchase_order_id": purchase_order.pk if purchase_order else None,
            "invoice_number": review.verified_data["invoice_number"],
        },
    )
    from dashboard.operations_automation import record_operations_event

    record_operations_event(
        module="Finance",
        event=f"Supplier invoice {review.verified_data['invoice_number']} posted",
        trigger="Authorised manager approved a verified supplier invoice.",
        action_taken=f"Created expense #{expense.pk}.",
        result="Expense recorded; payment remains unconfirmed and stock is unchanged.",
        actor=actor,
        metadata={
            "invoice_review_id": review.pk,
            "expense_id": expense.pk,
            "supplier_id": review.supplier_id,
            "purchase_order_id": purchase_order.pk if purchase_order else None,
        },
        idempotency_key=f"invoice-expense-post:{review.pk}",
    )
    return expense, True


def _label_value(source, label_pattern):
    pattern = re.compile(
        rf"^[ \t]*(?:{label_pattern})[ \t]*[:#\-]?[ \t]*(?P<value>.+?)[ \t]*$",
        re.IGNORECASE,
    )
    for line in source.splitlines():
        match = pattern.match(line)
        if match:
            value = re.split(r"\s{2,}", match.group("value").strip())[0]
            return value[:255], 0.9 if value else 0.0
    return "", 0.0


def _label_date(source, label_pattern):
    value, confidence = _label_value(source, label_pattern)
    if not value:
        return None, 0.0
    value = re.sub(r"^[A-Za-z ]+:\s*", "", value).strip()
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(value[:20], date_format).date().isoformat(), confidence
        except ValueError:
            continue
    match = re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", value)
    if match:
        for date_format in ("%d/%m/%y", "%d-%m-%y"):
            try:
                return datetime.strptime(match.group(), date_format).date().isoformat(), 0.7
            except ValueError:
                continue
    return None, 0.0


def _label_money(source, label_pattern):
    pattern = re.compile(
        rf"^[ \t]*(?:{label_pattern})[ \t]*[:\-]?[ \t]*"
        rf"(?:(?:\d{{1,2}}(?:\.\d+)?[ \t]*%)[ \t]*)?{MONEY_PATTERN}",
        re.IGNORECASE,
    )
    for line in source.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        try:
            return str(
                Decimal(match.group(1).replace(",", "")).quantize(Decimal("0.01"))
            ), 0.88
        except InvalidOperation:
            return "", 0.0
    return "", 0.0


def _extract_line_items(lines):
    parsed = []
    money = r"\$?\d[\d,]*(?:\.\d{1,2})?"
    pattern = re.compile(
        rf"^(?P<description>.+?)\s+(?P<quantity>\d+(?:\.\d+)?)\s+"
        rf"(?:x\s*)?(?P<unit_price>{money})"
        rf"(?:\s+(?P<line_total>{money}))?$",
        re.IGNORECASE,
    )
    for line in lines:
        match = pattern.match(line)
        if not match:
            continue
        try:
            quantity = Decimal(match.group("quantity"))
            unit_price = Decimal(
                match.group("unit_price").replace("$", "").replace(",", "")
            )
            if quantity <= 0 or unit_price < 0:
                continue
            line_total = match.group("line_total")
            parsed.append(
                {
                    "description": match.group("description").strip()[:255],
                    "quantity": str(quantity),
                    "unit_price": str(unit_price.quantize(Decimal("0.01"))),
                    "line_total": (
                        str(
                            Decimal(line_total.replace("$", "").replace(",", "")).quantize(
                                Decimal("0.01")
                            )
                        )
                        if line_total
                        else ""
                    ),
                }
            )
        except InvalidOperation:
            continue
    return parsed[:100]


def _extract_payment_claim(source):
    lowered = source.casefold()
    if re.search(r"\bpartially\s+paid\b", lowered):
        return "partial_claimed"
    if re.search(r"\bpaid\s+in\s+full\b|\bpayment\s+received\b|\bpaid\b", lowered):
        return "paid_claimed"
    if re.search(r"\bunpaid\b|\boutstanding\b|\bamount\s+due\b", lowered):
        return "unpaid_claimed"
    return "unknown"


def _first_supplier_candidate(lines):
    ignored = re.compile(
        r"invoice|tax invoice|abn|gst|date|total|amount|due|page\s+\d+",
        re.IGNORECASE,
    )
    for line in lines[:8]:
        if len(line) > 2 and not ignored.search(line) and not re.fullmatch(r"[\d\s./-]+", line):
            return line[:255]
    return ""


def is_valid_abn(value):
    if len(value) != 11 or not value.isdigit():
        return False
    digits = [int(digit) for digit in value]
    digits[0] -= 1
    weights = (10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19)
    return sum(digit * weight for digit, weight in zip(digits, weights)) % 89 == 0


def _decimal_or_none(value):
    try:
        return Decimal(str(value)) if value not in (None, "") else None
    except InvalidOperation:
        return None


def _suggest_supplier(supplier_name, abn):
    suppliers = Supplier.objects.filter(active=True)
    if abn and is_valid_abn(abn):
        exact_abn = re.sub(r"\D", "", abn)
        for supplier in suppliers:
            if re.sub(r"\D", "", supplier.abn) == exact_abn:
                return supplier
    normalized_name = _normalize_name(supplier_name)
    if not normalized_name:
        return None
    candidates = [
        (SequenceMatcher(None, normalized_name, _normalize_name(supplier.name)).ratio(), supplier)
        for supplier in suppliers
    ]
    score, supplier = max(candidates, default=(0, None), key=lambda candidate: candidate[0])
    return supplier if score >= 0.68 else None


def _suggest_purchase_order(*, supplier, data):
    supplier_name = supplier.name if supplier else data.get("supplier_name", "")
    if not supplier_name:
        return None
    orders = PurchaseOrder.objects.filter(
        status__in=("draft", "ordered", "received"),
        supplier_name__iexact=supplier_name,
    ).select_related("supply")
    descriptions = [
        _normalize_name(item.get("description", ""))
        for item in data.get("line_items", [])
    ]
    if descriptions:
        ranked = []
        for order in orders:
            supply_name = _normalize_name(order.supply.name)
            score = max(
                (SequenceMatcher(None, supply_name, description).ratio() for description in descriptions),
                default=0,
            )
            ranked.append((score, order))
        score, order = max(ranked, default=(0, None), key=lambda value: value[0])
        if score >= 0.55:
            return order
    return orders.order_by("-order_date", "-pk").first()


def build_purchase_order_reconciliation(review):
    order = review.suggested_purchase_order
    if not order:
        return None

    data = review.verified_data or review.extracted_data
    supply_name = _normalize_name(order.supply.name)
    invoice_quantity = Decimal("0")
    matched_items = 0
    for item in data.get("line_items") or data.get("line_items_json", []):
        description = _normalize_name(item.get("description", ""))
        if not description or SequenceMatcher(None, supply_name, description).ratio() < 0.6:
            continue
        try:
            quantity = Decimal(str(item.get("quantity", "")))
        except InvalidOperation:
            continue
        if quantity > 0:
            invoice_quantity += quantity
            matched_items += 1

    return {
        "purchase_order": order,
        "ordered_quantity": order.quantity,
        "invoice_quantity": invoice_quantity if matched_items else None,
        "received_quantity": order.quantity_received,
        "invoice_vs_order": (
            invoice_quantity - Decimal(order.quantity) if matched_items else None
        ),
        "invoice_vs_received": (
            invoice_quantity - Decimal(order.quantity_received)
            if matched_items
            else None
        ),
    }


def _normalize_name(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").casefold())
