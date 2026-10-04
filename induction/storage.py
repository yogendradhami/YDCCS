from cloudinary_storage.storage import RawMediaCloudinaryStorage


class EmployeeOnboardingDocumentStorage(
    RawMediaCloudinaryStorage
):
    """
    Cloudinary RAW storage for employee onboarding documents.

    Used for:
    - PDF
    - DOC
    - DOCX
    - JPG
    - JPEG
    - PNG

    These files are stored as raw assets so Cloudinary does not
    attempt to process DOC/DOCX files as images.
    """

    pass