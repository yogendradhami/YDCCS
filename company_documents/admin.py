from django.contrib import admin

from .models import CompanyDocument, CompanyDocumentAudit


@admin.register(CompanyDocument)
class CompanyDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "document_type",
        "expiry_date",
        "status",
        "version",
        "uploaded_by",
        "uploaded_at",
    )

    list_filter = (
        "category",
        "status",
        "is_sensitive",
    )

    search_fields = (
        "name",
        "document_reference",
        "original_filename",
        "description",
    )

    readonly_fields = (
        "original_filename",
        "file_size",
        "mime_type",
        "version",
        "uploaded_by",
        "uploaded_at",
        "updated_at",
    )


@admin.register(CompanyDocumentAudit)
class CompanyDocumentAuditAdmin(admin.ModelAdmin):
    list_display = (
        "document",
        "action",
        "user",
        "created_at",
    )

    list_filter = (
        "action",
        "created_at",
    )

    search_fields = (
        "document__name",
        "user__username",
    )

    readonly_fields = (
        "document",
        "user",
        "action",
        "metadata",
        "created_at",
    )