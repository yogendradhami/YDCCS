from __future__ import annotations

from io import BytesIO

import re

from employees.models import Employee

import requests

import cloudinary

from cloudinary.utils import cloudinary_url

import hashlib

import os

import secrets

from datetime import datetime



from django.db import transaction

from django.utils import timezone



from company_documents.models import (

    BulkImportBatch,

    BulkImportItem,

    CompanyDocument,

    CompanyDocumentAudit,

)







from .document_classifier import classify_document

from .document_extractor import extract_text

from .document_matcher import match_related_record





# ==========================================================

# CONFIGURATION

# ==========================================================



ANALYSIS_READY_THRESHOLD = 85





# ==========================================================

# FILE HASH

# ==========================================================



def calculate_hash(uploaded_file):

    """

    Calculate SHA-256 using chunks so large files are not

    loaded completely into memory.



    The file pointer is reset to the beginning before and

    after hashing whenever the object supports seek().

    """



    sha256 = hashlib.sha256()



    try:

        uploaded_file.seek(0)

    except (AttributeError, OSError):

        pass



    while True:

        chunk = uploaded_file.read(1024 * 1024)



        if not chunk:

            break



        sha256.update(chunk)



    try:

        uploaded_file.seek(0)

    except (AttributeError, OSError):

        pass



    return sha256.hexdigest()





# ==========================================================

# BATCH REFERENCE

# ==========================================================



def generate_batch_reference():

    """

    Generate a unique human-readable batch reference.



    Example:



        IMP-20261005-A81F3C

    """



    date_part = timezone.localdate().strftime("%Y%m%d")

    random_part = secrets.token_hex(3).upper()



    return f"IMP-{date_part}-{random_part}"





# ==========================================================

# SAFE FILENAME

# ==========================================================



def get_safe_filename(uploaded_file):

    """

    Return only the basename of an uploaded filename.



    This is important because Django's FileField rejects

    absolute paths such as:



        /tmp/example.pdf



    when saving a file.



    The database still keeps the original filename separately

    in BulkImportItem.original_filename.

    """



    original_name = getattr(

        uploaded_file,

        "name",

        "",

    ) or "unnamed-file"



    safe_filename = os.path.basename(

        str(original_name)

    )



    safe_filename = safe_filename.strip()



    if not safe_filename:

        safe_filename = "unnamed-file"



    return safe_filename[:500]





# ==========================================================

# CREATE BATCH

# ==========================================================



@transaction.atomic

def create_batch(user, files):

    """

    Create a bulk import batch and persist uploaded files

    directly into Cloudinary RAW staging storage.



    IMPORTANT:



    This function does NOT create permanent CompanyDocument

    records.



    Files are first stored as temporary RAW Cloudinary

    resources attached to BulkImportItem records.



    Workflow:



        upload

        -> staging

        -> analysis

        -> review

        -> approval

        -> permanent CompanyDocument

    """



    files = list(files)



    batch = BulkImportBatch.objects.create(

        batch_reference=generate_batch_reference(),

        status=BulkImportBatch.Status.UPLOADED,

        uploaded_by=user,

        total_files=len(files),

    )



    staging_folder = timezone.now().strftime(

        "company_document_staging/%Y/%m"

    )



    for uploaded_file in files:



        # --------------------------------------------------

        # FILE HASH

        # --------------------------------------------------



        file_hash = calculate_hash(

            uploaded_file

        )



        # --------------------------------------------------

        # ORIGINAL METADATA

        # --------------------------------------------------



        original_filename = (

            getattr(

                uploaded_file,

                "name",

                "",

            )

            or "unnamed-file"

        )



        original_filename = str(

            original_filename

        )[:500]



        file_size = (

            getattr(

                uploaded_file,

                "size",

                0,

            )

            or 0

        )



        mime_type = (

            getattr(

                uploaded_file,

                "content_type",

                "",

            )

            or ""

        )



        # --------------------------------------------------

        # CREATE STAGING ITEM

        # --------------------------------------------------



        item = BulkImportItem.objects.create(

            batch=batch,

            original_filename=original_filename,

            file_size=file_size,

            mime_type=mime_type,

            file_hash=file_hash,

            status=BulkImportItem.Status.PENDING,

        )



        # --------------------------------------------------

        # RESET FILE POINTER

        # --------------------------------------------------



        try:

            uploaded_file.seek(0)

        except (AttributeError, OSError):

            pass



        # --------------------------------------------------

        # SAFE FILENAME

        # --------------------------------------------------



        safe_filename = get_safe_filename(

            uploaded_file

        )



        # --------------------------------------------------

        # CLOUDINARY RAW STAGING

        # --------------------------------------------------



        try:



            result = cloudinary.uploader.upload(

                uploaded_file,

                resource_type="raw",

                folder=staging_folder,

                use_filename=True,

                unique_filename=True,

                overwrite=False,

            )



        except Exception as exc:



            item.status = (

                BulkImportItem.Status.FAILED

            )



            item.error_message = (

                "Cloudinary staging upload failed: "

                f"{exc}"

            )[:5000]



            item.save(

                update_fields=[

                    "status",

                    "error_message",

                ]

            )



            raise



        # --------------------------------------------------

        # GET CLOUDINARY PUBLIC ID

        # --------------------------------------------------



        public_id = (

            result.get("public_id")

            if isinstance(result, dict)

            else None

        )



        if not public_id:



            item.status = (

                BulkImportItem.Status.FAILED

            )



            item.error_message = (

                "Cloudinary staging upload succeeded "

                "but did not return a public_id."

            )



            item.save(

                update_fields=[

                    "status",

                    "error_message",

                ]

            )



            raise ValueError(

                "Cloudinary staging upload did not "

                "return a public_id."

            )



        # --------------------------------------------------

        # STORE THE ACTUAL CLOUDINARY PUBLIC ID

        # --------------------------------------------------

        #

        # IMPORTANT:

        #

        # staging_file.name must contain the actual

        # Cloudinary RAW public ID.

        #

        # Example:

        #

        # company_document_staging/2026/10/

        # Annual_Compliance_Calendar_t9gdtr.docx

        #

        # NOT merely:

        #

        # Annual_Compliance_Calendar_t9gdtr.docx

        #

        # This allows get_staged_file_for_extraction()

        # to generate the correct RAW Cloudinary URL.

        # --------------------------------------------------



        item.staging_file.name = public_id



        item.save(

            update_fields=[

                "staging_file",

            ]

        )



    return batch







# ==========================================================

# DUPLICATE CHECK — SAME BATCH

# ==========================================================



# ==========================================================

# DUPLICATE CHECK — EXISTING DOCUMENT

# ==========================================================



def find_existing_duplicate(item):

    """

    Find an existing CompanyDocument with the same SHA-256 hash.



    This checks permanent CompanyDocument records only.



    Returns:

        CompanyDocument instance or None

    """



    if not item.file_hash:

        return None



    return (

        CompanyDocument.objects

        .filter(file_hash=item.file_hash)

        .order_by("-id")

        .first()

    )





# ==========================================================

# DUPLICATE CHECK — SAME BATCH

# ==========================================================



def find_batch_duplicate(item):

    """

    Find another BulkImportItem in the same import batch

    with the same SHA-256 hash.



    This deliberately checks staged bulk-import items rather

    than CompanyDocument records.



    The current item is excluded from the search.



    Only meaningful staged items are considered. Failed,

    skipped and cancelled-style items are ignored because

    they should not cause another file to be treated as a

    duplicate.



    Returns:

        BulkImportItem instance or None

    """



    if not item.file_hash:

        return None



    return (

        BulkImportItem.objects

        .filter(

            batch=item.batch,

            file_hash=item.file_hash,

        )

        .exclude(pk=item.pk)

        .exclude(

            status__in=[

                BulkImportItem.Status.FAILED,

                BulkImportItem.Status.SKIPPED,

            ]

        )

        .order_by("id")

        .first()

    )







# ==========================================================

# CONFIDENCE

# ==========================================================



def confidence_label(score):

    """

    Convert numerical confidence into a human-readable label.

    """



    if score >= 95:

        return "Very High"



    if score >= 85:

        return "High"



    if score >= 70:

        return "Medium"



    if score >= 50:

        return "Low"



    return "Very Low"





# ==========================================================

# DATE MAPPING

# ==========================================================



def map_extracted_dates(dates):

    """

    Map extracted dates into the three available metadata

    fields.



    Current implementation:



        first date  -> issue date

        second date -> expiry date

        third date  -> review date



    NOTE:



    This is intentionally conservative.



    The classifier currently returns dates without enough

    contextual information to reliably determine whether a

    date is an issue, expiry, renewal, review, or other date.



    Contextual date intelligence can be added later.

    """



    if not dates:

        return None, None, None



    parsed_dates = []



    for value in dates:



        if not value:

            continue



        parsed_dates.append(value)



    if not parsed_dates:

        return None, None, None



    issue_date = parsed_dates[0]



    expiry_date = (

        parsed_dates[1]

        if len(parsed_dates) >= 2

        else None

    )



    review_date = (

        parsed_dates[2]

        if len(parsed_dates) >= 3

        else None

    )



    return (

        issue_date,

        expiry_date,

        review_date,

    )





def find_labelled_employee(text):

    """

    Find an employee explicitly identified in the document.



    Supports labels such as:



        Employee: John Smith

        Employee Name: John Smith

        Employee Full Name: John Smith

        Full Name: John Smith

    """



    if not text:

        return None, 0, ""



    patterns = [

        r"employee\s+full\s+name\s\*:\s\*(.+)",

        r"employee\s+name\s\*:\s\*(.+)",

        r"employee\s\*:\s\*(.+)",

        r"full\s+legal\s+name\s\*:\s\*(.+)",

        r"full\s+name\s\*:\s\*(.+)",

    ]



    for pattern in patterns:



        match = re.search(

            pattern,

            text,

            flags=re.IGNORECASE,

        )



        if not match:

            continue



        employee_name = (

            match.group(1)

            .strip()

        )



        # Only use the first line.

        employee_name = (

            employee_name

            .splitlines()[0]

            .strip()

        )



        if not employee_name:

            continue



        employee = (

            Employee.objects

            .filter(

                full_name__iexact=employee_name

            )

            .first()

        )



        if employee:

            return (

                employee,

                100,

                f"Employee explicitly identified as '{employee.full_name}'.",

            )



        # Try a safer token-based fallback.

        name_parts = [

            part

            for part in employee_name.split()

            if len(part) >= 2

        ]



        if len(name_parts) >= 2:



            query = Employee.objects.all()



            for part in name_parts:

                query = query.filter(

                    full_name__icontains=part

                )



            employee = query.first()



            if employee:

                return (

                    employee,

                    95,

                    f"Employee matched from labelled name '{employee_name}'.",

                )



    return None, 0, ""





def extract_labelled_dates(text):
    """
    Extract issue, expiry and review dates from explicit labels.

    Explicit labels always take priority over generic date detection.

    Supported date formats include:

        31/12/2027
        31-12-2027
        31.12.2027
        2027-12-31
        2027/12/31
        2027.12.31
        31 December 2027
        31 Dec 2027

    Returns:

        (
            issue_date,
            expiry_date,
            review_date,
        )

    The returned values are date strings and are converted to
    Python date objects later by parse_detected_date().
    """

    if not text:
        return None, None, None

    # ======================================================
    # DATE PATTERN
    # ======================================================

    date_pattern = (
        r"("
        r"\d{1,2}[./-]\d{1,2}[./-]\d{4}"
        r"|"
        r"\d{4}[./-]\d{1,2}[./-]\d{1,2}"
        r"|"
        r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}"
        r")"
    )

    # ======================================================
    # EXPLICIT LABEL MATCHER
    # ======================================================

    def find_date(labels):
        """
        Find a date immediately associated with one of the
        supplied explicit labels.

        Example:

            Issue Date: 04 October 2026
            Review Date: 04 October 2027
            Expiry Date: 04 October 2028
        """

        label_pattern = "|".join(
            re.escape(label)
            for label in labels
        )

        pattern = (
            rf"(?:{label_pattern})"
            rf"\s*[:\-]?\s*"
            rf"{date_pattern}"
        )

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            return None

        return match.group(1)

    # ======================================================
    # ISSUE DATE
    # ======================================================

    issue_date = find_date(
        [
            "issue date",
            "issued date",
            "date issued",
            "effective date",
            "commencement date",
            "start date",
        ]
    )

    # ======================================================
    # EXPIRY DATE
    # ======================================================

    expiry_date = find_date(
        [
            "expiry date",
            "expiration date",
            "expiry",
            "expiration",
            "expires",
            "valid until",
            "valid to",
        ]
    )

    # ======================================================
    # REVIEW DATE
    # ======================================================

    review_date = find_date(
        [
            "review date",
            "next review date",
            "next review",
            "review due",
            "review by",
            "date for review",
        ]
    )

    return (
        issue_date,
        expiry_date,
        review_date,
    )


# ==========================================================



# ANALYSE ITEM



# ==========================================================





def analyse_item(item, uploaded_file=None):

    """

    Analyse one bulk-import item.



    Workflow:



        staged file

        -> text extraction

        -> classification

        -> metadata extraction

        -> relationship matching

        -> duplicate detection

        -> confidence evaluation

        -> review/ready status



    If uploaded_file is not supplied, the persisted

    Cloudinary staging file is used.

    """



    item.status = BulkImportItem.Status.ANALYSING

    item.error_message = ""

    item.extraction_error = ""



    item.save(

        update_fields=[

            "status",

            "error_message",

            "extraction_error",

        ]

    )



    try:



        # ==================================================

        # GET FILE

        # ==================================================



        if uploaded_file is None:

            uploaded_file = get_staged_file_for_extraction(item)



        try:

            uploaded_file.seek(0)

        except (AttributeError, OSError):

            pass



        # ==================================================

        # TEXT EXTRACTION

        # ==================================================



        extraction = extract_text(

            uploaded_file

        )



        extracted_text = (

            extraction.get(

                "text",

                "",

            )

            or ""

        )



        extraction_method = (

            extraction.get(

                "method",

                "",

            )

            or ""

        )



        extraction_error = (

            extraction.get(

                "error",

                "",

            )

            or ""

        )



        # Keep extracted content bounded.

        item.extracted_text = (

            extracted_text[:200000]

        )



        item.extraction_method = (

            extraction_method[:50]

        )



        item.extraction_error = (

            extraction_error[:5000]

        )



        # ==================================================

        # CLASSIFICATION

        # ==================================================



        classification = classify_document(

            filename=item.original_filename,

            text=extracted_text,

        )



        item.suggested_category = (

            classification.get(

                "category",

                "",

            )

            or ""

        )



        item.suggested_document_type = (

            classification.get(

                "document_type",

                "",

            )

            or ""

        )



        item.suggested_reference = (

            classification.get(

                "reference",

                "",

            )

            or ""

        )



        item.suggested_version = (

            classification.get(

                "version",

                "",

            )

            or ""

        )



        item.suggested_sensitive = bool(

            classification.get(

                "sensitive",

                False,

            )

        )



        item.confidence_score = int(

            classification.get(

                "confidence_score",

                0,

            )

            or 0

        )



        item.confidence_label = (

            classification.get(

                "confidence_label",

                "",

            )

            or confidence_label(

                item.confidence_score

            )

        )



        item.classification_reasons = (

            classification.get(

                "reasons",

                [],

            )

            or []

        )



        # ==================================================

        # EXTRACTED FIELDS

        # ==================================================



        item.extracted_fields = {

            "classification": {

                "category": (

                    item.suggested_category

                ),

                "document_type": (

                    item.suggested_document_type

                ),

                "reference": (

                    item.suggested_reference

                ),

                "version": (

                    item.suggested_version

                ),

                "confidence": (

                    item.confidence_score

                ),

            },

            "extraction": {

                "method": (

                    item.extraction_method

                ),

                "error": (

                    item.extraction_error

                ),

            },

        }



        # ==================================================

        # SUGGESTED NAME

        # ==================================================



        base_name = (

            item.original_filename

            .rsplit(

                ".",

                1,

            )[0]

        )



        item.suggested_name = (

            base_name

            .replace(

                "_",

                " ",

            )

            .replace(

                "-",

                " ",

            )

            .strip()

        )[:255]



        # ==================================================

        # DATES

        # ==================================================



        (

            labelled_issue_date,

            labelled_expiry_date,

            labelled_review_date,

        ) = extract_labelled_dates(

            extracted_text

        )



        if (

            labelled_issue_date

            or labelled_expiry_date

            or labelled_review_date

        ):



            issue_date = parse_detected_date(

                labelled_issue_date

            )



            expiry_date = parse_detected_date(

                labelled_expiry_date

            )



            review_date = parse_detected_date(

                labelled_review_date

            )



        else:



            (

                issue_date,

                expiry_date,

                review_date,

            ) = map_extracted_dates(

                classification.get(

                    "dates",

                    [],

                )

            )



        item.suggested_issue_date = (

            issue_date

        )



        item.suggested_expiry_date = (

            expiry_date

        )



        item.suggested_review_date = (

            review_date

        )



        item.extracted_fields["dates"] = {

            "issue_date": (

                str(issue_date)

                if issue_date

                else ""

            ),

            "expiry_date": (

                str(expiry_date)

                if expiry_date

                else ""

            ),

            "review_date": (

                str(review_date)

                if review_date

                else ""

            ),

        }





        # ==================================================

        # DATABASE MATCHING

        # ==================================================



        labelled_employee = None

        labelled_employee_score = 0

        labelled_employee_reason = ""



        if item.suggested_category == "employee":



            (

                labelled_employee,

                labelled_employee_score,

                labelled_employee_reason,

            ) = find_labelled_employee(

                extracted_text

            )



        if labelled_employee:



            match_result = {

                "related_type": "employee",

                "object": labelled_employee,

                "score": labelled_employee_score,

                "reason": labelled_employee_reason,

            }



        else:



            match_result = match_related_record(

                category=item.suggested_category,

                filename=item.original_filename,

                text=extracted_text,

            )



        related_type = (

            match_result.get(

                "related_type",

                "",

            )

            or ""

        )



        related_object = (

            match_result.get(

                "object"

            )

        )



        match_score = int(

            match_result.get(

                "score",

                0,

            )

            or 0

        )



        if match_score >= 95:

            item.confidence_score = min(

                99,

                item.confidence_score + 8,

            )



            item.confidence_label = confidence_label(

                item.confidence_score

            )



        match_reason = (

            match_result.get(

                "reason",

                "",

            )

            or ""

        )



        item.suggested_related_type = (

            related_type

        )



        # ==================================================

        # RESET RELATIONSHIP SUGGESTIONS

        # ==================================================



        item.suggested_employee_id = None

        item.suggested_customer_id = None

        item.suggested_vehicle_id = None

        item.suggested_supplier_id = None

        item.suggested_contract_id = None



        # ==================================================

        # SAVE RELATED OBJECT ID

        # ==================================================



        if related_object is not None:



            object_id = int(

                related_object.pk

            )



            if related_type == "employee":



                item.suggested_employee_id = (

                    object_id

                )



            elif related_type == "customer":



                item.suggested_customer_id = (

                    object_id

                )



            elif related_type == "vehicle":



                item.suggested_vehicle_id = (

                    object_id

                )



            elif related_type == "supplier":



                item.suggested_supplier_id = (

                    object_id

                )



            elif related_type == "contract":



                item.suggested_contract_id = (

                    object_id

                )



        # ==================================================

        # MATCH REASON

        # ==================================================



        if match_reason:



            reasons = list(

                item.classification_reasons

                or []

            )



            reasons.append(

                match_reason

            )



            item.classification_reasons = (

                reasons[:20]

            )



        # ==================================================

        # SAVE RELATIONSHIP MATCH

        # ==================================================



        item.extracted_fields[

            "relationship_match"

        ] = {

            "related_type": (

                related_type

            ),

            "object_id": (

                int(

                    related_object.pk

                )

                if related_object is not None

                else None

            ),

            "score": match_score,

            "reason": match_reason,

        }



        # ==================================================

        # DUPLICATE DETECTION

        # ==================================================



        existing_duplicate = (

            find_existing_duplicate(item)

        )



        if existing_duplicate:



            item.duplicate_document = (

                existing_duplicate

            )



            item.duplicate_score = 100



            item.status = (

                BulkImportItem.Status.DUPLICATE

            )



            reasons = list(

                item.classification_reasons

                or []

            )



            reasons.append(

                "Exact SHA-256 duplicate of an "

                "existing Company Document."

            )



            item.classification_reasons = (

                reasons[:20]

            )



        else:



            batch_duplicate = (

                find_batch_duplicate(item)

            )



            if batch_duplicate:



                item.duplicate_document = None

                item.duplicate_score = 100



                item.status = (

                    BulkImportItem.Status.DUPLICATE

                )



                reasons = list(

                    item.classification_reasons

                    or []

                )



                reasons.append(

                    "Exact duplicate of another "

                    "file in this import batch."

                )



                item.classification_reasons = (

                    reasons[:20]

                )



            elif (

                item.confidence_score

                >= ANALYSIS_READY_THRESHOLD

                and not extraction_error

            ):



                item.status = (

                    BulkImportItem.Status.READY

                )



            else:



                item.status = (

                    BulkImportItem.Status.REVIEW

                )



        # ==================================================

        # FINALISE ANALYSIS

        # ==================================================



        item.analysed_at = timezone.now()



        item.save()



        return item



    except Exception as exc:



        item.status = (

            BulkImportItem.Status.FAILED

        )



        error_message = str(exc)



        if "404 Client Error" in error_message:



            error_message = (

                "The temporary Cloudinary staging file "

                "could not be found. The document must be "

                "uploaded again before it can be analysed."

            )



        elif (

            "staged file is missing"

            in error_message.lower()

        ):



            error_message = (

                "The temporary staging file is missing. "

                "Please upload the document again."

            )



        item.error_message = (

            error_message[:5000]

        )



        item.analysed_at = timezone.now()



        item.save(

            update_fields=[

                "status",

                "error_message",

                "analysed_at",

            ]

        )



        raise





# ==========================================================

# ANALYSE BATCH

# ==========================================================



@transaction.atomic

def analyse_batch(batch):

    """

    Analyse all pending/failed items in a batch.



    Items are processed individually so one failed document

    does not prevent the remaining files from being analysed.

    """



    batch.status = (

        BulkImportBatch.Status.ANALYSING

    )



    batch.started_at = (

        batch.started_at

        or timezone.now()

    )



    batch.error_message = ""



    batch.save(

        update_fields=[

            "status",

            "started_at",

            "error_message",

        ]

    )



    items = (

        batch.items

        .filter(

            status__in=[

                BulkImportItem.Status.PENDING,

                BulkImportItem.Status.FAILED,

            ]

        )

        .order_by("id")

    )



    for item in items:



        try:

            analyse_item(item)



        except Exception:

            # The item itself records the error.

            # Continue analysing the remaining files.

            continue



    refresh_batch_statistics(

        batch

    )



    batch.status = (

        BulkImportBatch.Status.REVIEW

    )



    batch.save(

        update_fields=[

            "status",

        ]

    )



    return batch





# ==========================================================

# REFRESH BATCH STATISTICS

# ==========================================================



def refresh_batch_statistics(batch):

    """

    Recalculate batch-level counters from its items.

    """



    items = batch.items.all()



    batch.processed_files = (

        items.filter(

            status__in=[

                BulkImportItem.Status.READY,

                BulkImportItem.Status.REVIEW,

                BulkImportItem.Status.APPROVED,

                BulkImportItem.Status.IMPORTED,

                BulkImportItem.Status.DUPLICATE,

                BulkImportItem.Status.FAILED,

                BulkImportItem.Status.SKIPPED,

            ]

        ).count()

    )



    batch.approved_files = (

        items.filter(

            status=BulkImportItem.Status.APPROVED

        ).count()

    )



    batch.imported_files = (

        items.filter(

            status=BulkImportItem.Status.IMPORTED

        ).count()

    )



    batch.review_required = (

        items.filter(

            status=BulkImportItem.Status.REVIEW

        ).count()

    )



    batch.duplicate_count = (

        items.filter(

            status=BulkImportItem.Status.DUPLICATE

        ).count()

    )



    batch.failed_count = (

        items.filter(

            status=BulkImportItem.Status.FAILED

        ).count()

    )



    batch.save(

        update_fields=[

            "processed_files",

            "approved_files",

            "imported_files",

            "review_required",

            "duplicate_count",

            "failed_count",

        ]

    )



    return batch





# ==========================================================

# STAGED FILE VALIDATION

# ==========================================================



def validate_staged_file(item):

    """

    Confirm that the staging file exists both in the database

    and in Cloudinary RAW storage.

    """



    if not item.staging_file:

        return False



    try:

        file_name = item.staging_file.name



    except Exception:

        return False



    if not file_name:

        return False



    try:



        raw_url, _ = cloudinary_url(

            file_name,

            resource_type="raw",

            type="upload",

            secure=True,

        )



        response = requests.head(

            raw_url,

            timeout=20,

            allow_redirects=True,

        )



        if response.status_code == 200:

            return True



        # Some Cloudinary configurations may not support

        # HEAD correctly. Fall back to a lightweight GET.



        response = requests.get(

            raw_url,

            timeout=20,

            stream=True,

        )



        return response.status_code == 200



    except Exception:

        return False



def get_staged_file_for_extraction(item):

    """

    Download a staged company document explicitly as a

    Cloudinary RAW resource.



    This avoids MediaCloudinaryStorage generating an

    image/upload URL for non-image company documents.

    """



    if not item.staging_file:

        raise ValueError("The staged file is missing.")



    file_name = item.staging_file.name



    if not file_name:

        raise ValueError(

            "The staged file has no storage name."

        )



    raw_url, _ = cloudinary_url(

        file_name,

        resource_type="raw",

        type="upload",

        secure=True,

    )



    response = requests.get(

        raw_url,

        timeout=60,

    )



    response.raise_for_status()



    file_object = BytesIO(response.content)



    file_object.name = (

        item.original_filename

        or os.path.basename(file_name)

    )



    file_object.seek(0)



    return file_object


def parse_detected_date(value):
    """
    Convert a detected date string into a Python date object.

    Supports:
        31/12/2027
        31-12-2027
        31.12.2027
        2027-12-31
        2027/12/31
        2027.12.31
        31 December 2027
        31 Dec 2027
    """

    if not value:
        return None

    value = str(value).strip()

    if not value:
        return None

    formats = [
        # Australian numeric formats
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",

        # ISO-style formats
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",

        # Month-name formats
        "%d %B %Y",
        "%d %b %Y",

        # Month-name formats with commas
        "%d %B, %Y",
        "%d %b, %Y",
    ]

    for date_format in formats:
        try:
            return datetime.strptime(
                value,
                date_format,
            ).date()
        except ValueError:
            continue

    return None


# ==========================================================

# PERMANENT COMPANY DOCUMENT IMPORT

# ==========================================================





def upload_permanent_raw_document(uploaded_file):

    """

    Upload an approved bulk-import file into the permanent

    Company Documents Cloudinary RAW folder.



    This intentionally bypasses the FileField storage backend

    and uploads directly as a RAW Cloudinary resource.

    """



    folder = timezone.now().strftime(

        "company_documents/%Y/%m"

    )



    try:

        uploaded_file.seek(0)

    except (AttributeError, OSError):

        pass



    result = cloudinary.uploader.upload(

        uploaded_file,

        resource_type="raw",

        folder=folder,

        use_filename=True,

        unique_filename=True,

        overwrite=False,

    )



    public_id = result.get("public_id")



    if not public_id:

        raise ValueError(

            "Cloudinary did not return a permanent document public ID."

        )



    return public_id





def delete_staged_raw_document(item):

    """

    Remove the temporary Cloudinary staging file after

    successful permanent import.



    Cleanup failure must never invalidate an already

    successful permanent document import.

    """



    if not item.staging_file:

        return



    file_name = item.staging_file.name



    if not file_name:

        return



    try:

        cloudinary.uploader.destroy(

            file_name,

            resource_type="raw",

            type="upload",

            invalidate=True,

        )

    except Exception:

        pass


def resolve_bulk_relationship(item):
    """
    Resolve the approved relationship suggestion into the
    actual Django model instance.

    Relationship handling rules:

    1. No suggested relationship:
           company / None

    2. Company relationship:
           company / None

    3. A real related database record has been approved:
           related_type / related_object

    4. A relationship category was suggested but no actual
       record was selected:
           company / None

       This is intentional.

       Documents such as reusable templates, policies,
       registers, checklists and standard forms can belong
       to a document category such as Employee, Contract,
       Supplier or Vehicle without being attached to one
       specific employee, contract, supplier or vehicle.

    5. If an actual relationship ID was supplied but that
       database record has since been deleted, fail safely
       rather than silently importing a broken relationship.
    """

    # ======================================================
    # READ SUGGESTED RELATIONSHIP TYPE
    # ======================================================

    related_type = (
        item.suggested_related_type or ""
    ).strip().lower()

    # ------------------------------------------------------
    # No relationship suggestion.
    # ------------------------------------------------------

    if not related_type:
        return "company", None

    # ======================================================
    # VALIDATE RELATIONSHIP TYPE
    # ======================================================

    valid_related_types = {
        value
        for value, label in CompanyDocument.RelatedType.choices
    }

    if related_type not in valid_related_types:
        raise ValueError(
            f"Invalid related type '{related_type}'."
        )

    # ======================================================
    # COMPANY-LEVEL DOCUMENT
    # ======================================================

    if related_type == "company":
        return "company", None

    # ======================================================
    # RELATIONSHIP FIELD MAP
    # ======================================================

    relationship_map = {
        "employee": (
            "suggested_employee_id",
            "employee",
        ),

        "customer": (
            "suggested_customer_id",
            "customer",
        ),

        "vehicle": (
            "suggested_vehicle_id",
            "vehicle",
        ),

        "supplier": (
            "suggested_supplier_id",
            "supplier",
        ),

        "contract": (
            "suggested_contract_id",
            "contract",
        ),
    }

    mapping = relationship_map.get(
        related_type
    )

    if not mapping:
        raise ValueError(
            f"Relationship type '{related_type}' "
            f"cannot be resolved."
        )

    suggested_id_field, document_field = mapping

    # ======================================================
    # GET ACTUAL APPROVED RECORD
    # ======================================================

    object_id = getattr(
        item,
        suggested_id_field,
        None,
    )

    # ------------------------------------------------------
    # IMPORTANT:
    #
    # A classifier can identify the document as belonging to
    # an entity category without identifying a specific entity.
    #
    # Example:
    #
    #     "Employment Agreement Template"
    #
    # may correctly classify as:
    #
    #     related_type = employee
    #
    # but there may be no actual employee selected.
    #
    # In that case this is a valid company-level document.
    # ------------------------------------------------------

    if not object_id:
        return "company", None

    # ======================================================
    # RESOLVE ACTUAL MODEL
    # ======================================================

    relation_field = (
        CompanyDocument._meta.get_field(
            document_field
        )
    )

    related_model = (
        relation_field.remote_field.model
    )

    related_object = (
        related_model.objects
        .filter(pk=object_id)
        .first()
    )

    # ------------------------------------------------------
    # An explicit relationship was approved, but the target
    # record no longer exists.
    #
    # Do not silently convert this into a company-level
    # document because that would hide a genuine data
    # integrity problem.
    # ------------------------------------------------------

    if related_object is None:
        raise ValueError(
            f"The selected {related_type} record "
            f"no longer exists."
        )

    # ======================================================
    # SUCCESSFUL REAL RELATIONSHIP
    # ======================================================

    return related_type, related_object

def parse_import_version(value):

    """

    Convert the suggested version into an integer.



    Examples:



        2       -> 2

        "2"     -> 2

        "v2"    -> 2

        "Version 3" -> 3



    Falls back to version 1.

    """



    if value is None:

        return 1



    value = str(value).strip()



    if not value:

        return 1



    if value.isdigit():

        return max(1, int(value))



    import re



    match = re.search(

        r"\b(?:v|version)?\s\*(\d+)\b",

        value,

        flags=re.IGNORECASE,

    )



    if match:

        return max(

            1,

            int(match.group(1)),

        )



    return 1



def build_company_document_from_bulk_item(
    item,
    uploaded_by,
    permanent_public_id,
):
    """
    Build a CompanyDocument instance from an approved BulkImportItem.

    The file itself is already uploaded to Cloudinary.

    Therefore the FileField receives the permanent
    Cloudinary public ID instead of uploading the file
    a second time through Django storage.

    Important import rules:

    - The classifier may use categories that are broader than
      the categories currently supported by CompanyDocument.
    - Unsupported classifier categories are mapped to the closest
      safe permanent CompanyDocument category.
    - A relationship is only created when a real related database
      object has been identified.
    - Reusable templates are allowed to remain company-level
      documents without a fake employee/customer/vehicle/etc.
      relationship.
    """

    # ======================================================
    # CLASSIFIED CATEGORY
    # ======================================================

    classifier_category = (
        item.suggested_category or ""
    ).strip().lower()

    # ------------------------------------------------------
    # CompanyDocument supports a smaller set of categories
    # than the intelligence/classification layer.
    #
    # Keep the classifier expressive while translating its
    # result into a valid permanent CompanyDocument category.
    # ------------------------------------------------------

    category_map = {
        # Direct CompanyDocument categories
        "company": "company",
        "employee": "employee",
        "customer": "customer",
        "insurance": "insurance",
        "vehicle": "vehicle",
        "contract": "contract",
        "whs": "whs",
        "finance": "finance",
        "licence": "licence",
        "operations": "operations",
        "supplier": "supplier",
        "property": "property",
        "other": "other",

        # Classifier categories that do not currently have
        # dedicated CompanyDocument categories.
        #
        # Preserve their meaning through document_type while
        # storing them in a valid permanent category.
        "equipment": "other",
        "chemicals": "whs",
        "training": "other",
        "marketing": "company",
        "business_continuity": "company",
        "quality": "operations",
        "privacy": "company",
    }

    category = category_map.get(
        classifier_category
    )

    # ------------------------------------------------------
    # FINAL SAFETY CHECK
    # ------------------------------------------------------

    valid_categories = {
        value
        for value, label in CompanyDocument.Category.choices
    }

    if not category:
        raise ValueError(
            "The approved document has an unsupported "
            f"classifier category: '{classifier_category}'."
        )

    if category not in valid_categories:
        raise ValueError(
            "The approved document resolved to an invalid "
            f"CompanyDocument category: '{category}'."
        )

    # ======================================================
    # RELATIONSHIP
    # ======================================================

    related_type, related_object = (
        resolve_bulk_relationship(item)
    )

    # ------------------------------------------------------
    # IMPORTANT:
    #
    # A reusable company template can legitimately have:
    #
    #   category = employee
    #   related_type = company
    #   employee = NULL
    #
    # or:
    #
    #   category = contract
    #   related_type = company
    #   contract = NULL
    #
    # We must NOT invent a relationship simply because the
    # classifier recognised the document as employee/contract/
    # supplier/etc.
    # ------------------------------------------------------

    if not related_object:
        related_type = "company"

    # ======================================================
    # NAME
    # ======================================================

    suggested_name = (
        item.suggested_name or ""
    ).strip()

    if not suggested_name:
        suggested_name = (
            item.original_filename
            or "Imported Document"
        )

    # ======================================================
    # DOCUMENT TYPE
    # ======================================================

    document_type = (
        item.suggested_document_type or ""
    ).strip()

    # Keep the classifier's document type intact.

    # ======================================================
    # DESCRIPTION
    # ======================================================

    description = (
        item.suggested_description or ""
    ).strip()

    # ======================================================
    # DOCUMENT REFERENCE
    # ======================================================

    document_reference = (
        item.suggested_reference or ""
    ).strip()

    # ======================================================
    # BUILD DOCUMENT
    # ======================================================

    document = CompanyDocument(
        name=suggested_name[:255],

        category=category,

        document_type=document_type[:150],

        description=description,

        document_reference=document_reference[:150],

        original_filename=(
            item.original_filename or ""
        )[:255],

        file_size=item.file_size or 0,

        mime_type=(
            item.mime_type or ""
        )[:255],

        file_hash=(
            item.file_hash or ""
        )[:64],

        issue_date=item.suggested_issue_date,

        expiry_date=item.suggested_expiry_date,

        review_date=item.suggested_review_date,

        is_sensitive=bool(
            item.suggested_sensitive
        ),

        status=CompanyDocument.Status.ACTIVE,

        related_type=related_type,

        version=parse_import_version(
            item.suggested_version
        ),

        uploaded_by=uploaded_by,
    )

    # ======================================================
    # ASSIGN RELATED OBJECT
    # ======================================================

    if related_type == "employee":
        document.employee = related_object

    elif related_type == "customer":
        document.customer = related_object

    elif related_type == "vehicle":
        document.vehicle = related_object

    elif related_type == "supplier":
        document.supplier = related_object

    elif related_type == "contract":
        document.contract = related_object

    # ======================================================
    # PERMANENT CLOUDINARY FILE
    # ======================================================

    # IMPORTANT:
    #
    # Do NOT call document.file.save().
    #
    # The file has already been uploaded directly to
    # Cloudinary as a permanent RAW resource.

    document.file.name = permanent_public_id
    document.file._committed = True

    return document


def import_bulk_item(item, user):

    """

    Import one approved BulkImportItem into CompanyDocument.



    The operation is intentionally idempotent:



    - Already imported items are returned as imported.

    - Non-approved items are skipped.

    - Existing documents with the same SHA-256 are treated as duplicates.

    - The staged Cloudinary RAW file is downloaded and then uploaded

      as a permanent CompanyDocument RAW resource.

    - The permanent CompanyDocument is created only after the permanent

      Cloudinary upload succeeds.

    - If database creation fails after the Cloudinary upload, the newly

      uploaded permanent resource is removed.

    """



    # ------------------------------------------------------

    # LOCK ITEM

    # ------------------------------------------------------



    with transaction.atomic():



        locked_item = (

            BulkImportItem.objects

            .select_for_update()

            .select_related("batch")

            .get(pk=item.pk)

        )



        # --------------------------------------------------

        # IDEMPOTENCY

        # --------------------------------------------------



        if (

            locked_item.status

            == BulkImportItem.Status.IMPORTED

        ):

            return {

                "status": "imported",

                "document": locked_item.imported_document,

            }



        # --------------------------------------------------

        # ONLY APPROVED ITEMS CAN BE IMPORTED

        # --------------------------------------------------



        if (

            locked_item.status

            != BulkImportItem.Status.APPROVED

        ):

            return {

                "status": "skipped",

                "document": None,

            }



        # --------------------------------------------------

        # VALIDATE STAGED FILE

        # --------------------------------------------------



        validate_staged_file(locked_item)



        # --------------------------------------------------

        # CHECK EXACT EXISTING DUPLICATE

        # --------------------------------------------------



        existing_duplicate = find_existing_duplicate(

            locked_item

        )



        if existing_duplicate:



            locked_item.status = (

                BulkImportItem.Status.DUPLICATE

            )



            locked_item.duplicate_document = (

                existing_duplicate

            )



            locked_item.duplicate_score = 100



            locked_item.error_message = ""



            locked_item.save(

                update_fields=[

                    "status",

                    "duplicate_document",

                    "duplicate_score",

                    "error_message",

                ]

            )



            return {

                "status": "duplicate",

                "document": existing_duplicate,

            }



        # --------------------------------------------------

        # DOWNLOAD STAGED RAW FILE

        # --------------------------------------------------



        uploaded_file = (

            get_staged_file_for_extraction(

                locked_item

            )

        )



        if uploaded_file is None:

            raise ValueError(

                "Unable to retrieve the staged document "

                "from Cloudinary."

            )



        # --------------------------------------------------

        # ENSURE FILE HASH EXISTS

        # --------------------------------------------------



        if not locked_item.file_hash:



            calculated_hash = calculate_hash(

                uploaded_file

            )



            locked_item.file_hash = calculated_hash



            # Reset because the hash calculation may have

            # consumed the file stream.

            uploaded_file.seek(0)



            # Re-check the database for an exact duplicate

            # now that the hash has been calculated.

            existing_duplicate = (

                CompanyDocument.objects

                .filter(

                    file_hash=calculated_hash

                )

                .order_by("-id")

                .first()

            )



            if existing_duplicate:



                locked_item.status = (

                    BulkImportItem.Status.DUPLICATE

                )



                locked_item.duplicate_document = (

                    existing_duplicate

                )



                locked_item.duplicate_score = 100



                locked_item.error_message = ""



                locked_item.save(

                    update_fields=[

                        "file_hash",

                        "status",

                        "duplicate_document",

                        "duplicate_score",

                        "error_message",

                    ]

                )



                return {

                    "status": "duplicate",

                    "document": existing_duplicate,

                }



            locked_item.save(

                update_fields=[

                    "file_hash",

                ]

            )



        # --------------------------------------------------

        # RESET FILE STREAM BEFORE CLOUDINARY UPLOAD

        # --------------------------------------------------



        uploaded_file.seek(0)



        # --------------------------------------------------

        # UPLOAD PERMANENT RAW DOCUMENT

        # --------------------------------------------------



        permanent_result = (

            upload_permanent_raw_document(

                uploaded_file

            )

        )



        if not permanent_result:

            raise ValueError(

                "Cloudinary did not return a permanent "

                "document upload result."

            )



        if isinstance(

            permanent_result,

            dict,

        ):

            permanent_public_id = (

                permanent_result.get(

                    "public_id"

                )

            )

        else:

            permanent_public_id = (

                getattr(

                    permanent_result,

                    "public_id",

                    None,

                )

                or str(permanent_result)

            )



        if not permanent_public_id:

            raise ValueError(

                "The permanent Cloudinary upload did not "

                "return a public_id."

            )



        # --------------------------------------------------

        # CREATE COMPANY DOCUMENT

        # --------------------------------------------------



        try:



            document = (

                build_company_document_from_bulk_item(

                    item=locked_item,

                    permanent_public_id=(

                        permanent_public_id

                    ),

                    uploaded_by=user,

                )

            )



            document.save()



        except Exception:



            # ----------------------------------------------

            # Database creation failed after Cloudinary

            # upload. Remove the orphaned permanent file.

            # ----------------------------------------------



            try:

                cloudinary.uploader.destroy(

                    permanent_public_id,

                    resource_type="raw",

                    type="upload",

                    invalidate=True,

                )

            except Exception:

                pass



            raise



        # --------------------------------------------------

        # AUDIT

        # --------------------------------------------------



        CompanyDocumentAudit.objects.create(

            document=document,

            user=user,

            action="uploaded",

            metadata={

                "source": "bulk_import",

                "batch_reference": (

                    locked_item.batch.batch_reference

                ),

                "bulk_import_item_id": locked_item.pk,

                "original_filename": (

                    locked_item.original_filename

                ),

            },

        )



        # --------------------------------------------------

        # MARK ITEM IMPORTED

        # --------------------------------------------------



        locked_item.status = (

            BulkImportItem.Status.IMPORTED

        )



        locked_item.imported_document = document



        locked_item.imported_at = timezone.now()



        locked_item.error_message = ""



        locked_item.save(

            update_fields=[

                "status",

                "imported_document",

                "imported_at",

                "error_message",

            ]

        )



    # ------------------------------------------------------

    # CLEAN UP STAGING FILE

    #

    # Do this AFTER the database transaction succeeds.

    # ------------------------------------------------------



    try:



        delete_staged_raw_document(

            locked_item

        )



    except Exception:

        # Staging cleanup must never make a successful

        # permanent import appear to have failed.

        pass



    return {

        "status": "imported",

        "document": document,

    }





def import_approved_batch(batch, user):

    """

    Import all approved items in a batch.



    Each document is processed independently.



    One failed document does not roll back documents

    that were successfully imported.

    """



    results = {

        "imported": 0,

        "duplicates": 0,

        "failed": 0,

        "skipped": 0,

    }



    # ------------------------------------------------------

    # LOCK BATCH

    # ------------------------------------------------------



    with transaction.atomic():



        batch = (

            BulkImportBatch.objects

            .select_for_update()

            .get(pk=batch.pk)

        )



        batch.status = (

            BulkImportBatch.Status.IMPORTING

        )



        batch.started_at = (

            batch.started_at

            or timezone.now()

        )



        batch.error_message = ""



        batch.save(

            update_fields=[

                "status",

                "started_at",

                "error_message",

            ]

        )



    # ------------------------------------------------------

    # GET APPROVED ITEMS

    # ------------------------------------------------------



    approved_items = list(

        batch.items

        .filter(

            status=BulkImportItem.Status.APPROVED

        )

        .order_by("id")

    )



    if not approved_items:



        with transaction.atomic():



            batch = (

                BulkImportBatch.objects

                .select_for_update()

                .get(pk=batch.pk)

            )



            refresh_batch_statistics(batch)



            remaining_review = (

                batch.items

                .filter(

                    status__in=[

                        BulkImportItem.Status.READY,

                        BulkImportItem.Status.REVIEW,

                        BulkImportItem.Status.APPROVED,

                    ]

                )

                .exists()

            )



            failed_exists = (

                batch.items

                .filter(

                    status=BulkImportItem.Status.FAILED

                )

                .exists()

            )



            if remaining_review or failed_exists:

                batch.status = (

                    BulkImportBatch.Status.PARTIAL

                )

            else:

                batch.status = (

                    BulkImportBatch.Status.COMPLETED

                )



            batch.completed_at = timezone.now()



            batch.save(

                update_fields=[

                    "status",

                    "completed_at",

                    "processed_files",

                    "approved_files",

                    "imported_files",

                    "review_required",

                    "duplicate_count",

                    "failed_count",

                ]

            )



        return results



    # ------------------------------------------------------

    # IMPORT EACH DOCUMENT INDEPENDENTLY

    # ------------------------------------------------------



    for item in approved_items:



        try:



            result = import_bulk_item(

                item=item,

                user=user,

            )



            result_status = result.get(

                "status"

            )



            if result_status == "imported":



                results["imported"] += 1



            elif result_status == "duplicate":



                results["duplicates"] += 1



            elif result_status == "skipped":



                results["skipped"] += 1



            else:



                results["failed"] += 1



        except Exception as exc:



            results["failed"] += 1



            # ----------------------------------------------

            # Keep failed documents reviewable.

            # ----------------------------------------------



            BulkImportItem.objects.filter(

                pk=item.pk,

            ).update(

                status=BulkImportItem.Status.FAILED,

                error_message=str(exc)[:5000],

            )



    # ------------------------------------------------------

    # FINAL BATCH STATUS

    # ------------------------------------------------------



    with transaction.atomic():



        batch = (

            BulkImportBatch.objects

            .select_for_update()

            .get(pk=batch.pk)

        )



        refresh_batch_statistics(batch)



        remaining_review = (

            batch.items

            .filter(

                status__in=[

                    BulkImportItem.Status.READY,

                    BulkImportItem.Status.REVIEW,

                    BulkImportItem.Status.APPROVED,

                ]

            )

            .exists()

        )



        failed_exists = (

            batch.items

            .filter(

                status=BulkImportItem.Status.FAILED

            )

            .exists()

        )



        duplicate_exists = (

            batch.items

            .filter(

                status=BulkImportItem.Status.DUPLICATE

            )

            .exists()

        )



        if (

            failed_exists

            or remaining_review

            or duplicate_exists

        ):

            batch.status = (

                BulkImportBatch.Status.PARTIAL

            )

        else:

            batch.status = (

                BulkImportBatch.Status.COMPLETED

            )



        batch.completed_at = timezone.now()



        batch.save(

            update_fields=[

                "status",

                "completed_at",

                "processed_files",

                "approved_files",

                "imported_files",

                "review_required",

                "duplicate_count",

                "failed_count",

            ]

        )



    return results