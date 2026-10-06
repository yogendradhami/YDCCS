from pathlib import Path


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".doc",
    ".xlsx",
    ".xls",
    ".csv",
    ".txt",
}


def extract_text(uploaded_file):
    """
    Extract searchable text from common company document formats.

    The function accepts normal Django uploaded files as well as
    file-like objects retrieved from Cloudinary RAW storage.

    Returns:

    {
        "text": "...",
        "method": "docx",
        "error": "",
    }
    """

    filename = getattr(uploaded_file, "name", "") or ""

    extension = Path(filename).suffix.lower()

    try:
        if extension == ".docx":
            return _extract_docx(uploaded_file)

        if extension == ".doc":
            return {
                "text": "",
                "method": "unsupported",
                "error": (
                    "Legacy .doc extraction is not currently supported. "
                    "Please convert the document to .docx or PDF."
                ),
            }

        if extension == ".pdf":
            return _extract_pdf(uploaded_file)

        if extension in {".xlsx", ".xls"}:
            return _extract_excel(uploaded_file)

        if extension == ".csv":
            return _extract_csv(uploaded_file)

        if extension == ".txt":
            return _extract_text_file(uploaded_file)

        return {
            "text": "",
            "method": "unsupported",
            "error": (
                f"Content extraction is not currently supported "
                f"for {extension or 'this file type'}."
            ),
        }

    except Exception as exc:
        return {
            "text": "",
            "method": "error",
            "error": str(exc),
        }


def _extract_docx(uploaded_file):
    from docx import Document

    uploaded_file.seek(0)

    document = Document(uploaded_file)

    parts = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            parts.append(text)

    for table in document.tables:
        for row in table.rows:
            values = []

            for cell in row.cells:
                value = cell.text.strip()

                if value:
                    values.append(value)

            if values:
                parts.append(" | ".join(values))

    return {
        "text": "\n".join(parts),
        "method": "docx",
        "error": "",
    }


def _extract_pdf(uploaded_file):
    import fitz

    uploaded_file.seek(0)

    pdf = fitz.open(
        stream=uploaded_file.read(),
        filetype="pdf",
    )

    parts = []

    for page in pdf:
        text = page.get_text("text")

        if text:
            parts.append(text.strip())

    pdf.close()

    return {
        "text": "\n".join(parts),
        "method": "pdf",
        "error": "",
    }


def _extract_excel(uploaded_file):
    from openpyxl import load_workbook

    uploaded_file.seek(0)

    workbook = load_workbook(
        uploaded_file,
        read_only=True,
        data_only=True,
    )

    parts = []

    for worksheet in workbook.worksheets:
        parts.append(
            f"WORKSHEET: {worksheet.title}"
        )

        for row in worksheet.iter_rows(
            values_only=True
        ):
            values = [
                str(value).strip()
                for value in row
                if value is not None
                and str(value).strip()
            ]

            if values:
                parts.append(" | ".join(values))

    workbook.close()

    return {
        "text": "\n".join(parts),
        "method": "excel",
        "error": "",
    }


def _extract_csv(uploaded_file):
    import csv
    import io

    uploaded_file.seek(0)

    raw = uploaded_file.read()

    text = raw.decode(
        "utf-8",
        errors="replace",
    )

    reader = csv.reader(
        io.StringIO(text)
    )

    parts = []

    for row in reader:
        values = [
            value.strip()
            for value in row
            if value.strip()
        ]

        if values:
            parts.append(" | ".join(values))

    return {
        "text": "\n".join(parts),
        "method": "csv",
        "error": "",
    }


def _extract_text_file(uploaded_file):
    uploaded_file.seek(0)

    raw = uploaded_file.read()

    if isinstance(raw, bytes):
        text = raw.decode(
            "utf-8",
            errors="replace",
        )
    else:
        text = str(raw)

    return {
        "text": text,
        "method": "text",
        "error": "",
    }