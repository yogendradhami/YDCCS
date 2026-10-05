import cloudinary
from cloudinary_storage.storage import MediaCloudinaryStorage


class CompanyDocumentStorage(MediaCloudinaryStorage):
    """
    Cloudinary storage backend dedicated to company documents.

    All company documents are uploaded as RAW Cloudinary resources.

    This allows files such as:

    PDF
    DOC
    DOCX
    XLS
    XLSX
    PPT
    PPTX
    CSV
    TXT
    ZIP
    RAR
    JPG
    PNG
    WEBP
    and other file types.

    The normal MediaCloudinaryStorage upload path can interpret
    certain document formats incorrectly. Using resource_type='raw'
    prevents DOCX/XLSX/ZIP files from being treated as image media.
    """

    def _upload(self, name, content):
        """
        Upload a file directly to Cloudinary as a RAW resource.
        """

        upload_options = {
            "resource_type": "raw",
            "use_filename": True,
            "unique_filename": True,
            "overwrite": False,
        }

        return cloudinary.uploader.upload(
            content,
            **upload_options,
        )