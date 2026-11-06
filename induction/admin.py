from django.contrib import admin
from django import forms
from django.db import transaction

from .models import (
    EmployeeInduction,
    InductionAssessmentAttempt,
    InductionExpiryReminder,
    InductionModule,
    InductionModuleCompletion,
    InductionModuleReview,
    InductionModuleVersion,
    InductionProgramme,
    InductionSupervisorVerification,
)


class InductionModuleVersionAdminForm(forms.ModelForm):
    class Meta:
        model = InductionModuleVersion
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        module = cleaned_data.get("module")
        version = cleaned_data.get("version")
        if module and version is not None and version <= module.version:
            self.add_error(
                "version",
                "A new training version must be higher than the current version.",
            )
        return cleaned_data


@admin.register(InductionProgramme)
class InductionProgrammeAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "version",
        "active",
        "updated_at",
    )

    list_filter = (
        "active",
    )


@admin.register(InductionModule)
class InductionModuleAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "category",
        "role",
        "mandatory",
        "version",
        "active",
        "sort_order",
    )

    list_filter = (
        "category",
        "role",
        "mandatory",
        "active",
    )

    search_fields = (
        "title",
        "code",
        "content",
    )

    prepopulated_fields = {
        "code": ("title",),
    }

    readonly_fields = (
        "content",
        "acknowledgement_text",
        "version",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False


@admin.register(InductionModuleVersion)
class InductionModuleVersionAdmin(admin.ModelAdmin):
    form = InductionModuleVersionAdminForm

    list_display = (
        "module",
        "version",
        "created_at",
    )
    list_filter = (
        "version",
        "module__category",
    )
    search_fields = (
        "module__title",
        "module__code",
    )
    readonly_fields = (
        "created_at",
    )

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.module.version = obj.version
        obj.module.save(update_fields=["version", "updated_at"])

    def has_change_permission(self, request, obj=None):
        return obj is None and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EmployeeInduction)
class EmployeeInductionAdmin(admin.ModelAdmin):

    list_display = (
        "employee",
        "programme",
        "status",
        "start_date",
        "completed_at",
    )

    list_filter = (
        "status",
        "employment_type",
        "programme",
    )

    search_fields = (
        "employee__full_name",
        "employee__email",
    )


@admin.register(InductionModuleCompletion)
class InductionModuleCompletionAdmin(admin.ModelAdmin):

    list_display = (
        "induction",
        "module_title_snapshot",
        "module_version",
        "attempt_number",
        "completed_at",
        "acknowledgement",
        "review_status",
        "reviewed_by",
    )

    list_filter = (
        "acknowledgement",
        "review_status",
    )
    readonly_fields = (
        "induction",
        "module",
        "module_title_snapshot",
        "module_version",
        "attempt_number",
        "completed_at",
        "acknowledgement",
        "acknowledgement_text",
        "notes",
        "review_status",
        "review_note",
        "reviewed_by",
        "reviewed_at",
    )

    def has_add_permission(self, request):
        return False


@admin.register(InductionExpiryReminder)
class InductionExpiryReminderAdmin(admin.ModelAdmin):
    list_display = (
        "induction",
        "expiry_date",
        "days_before_expiry",
        "portal_status",
        "email_status",
    )
    list_filter = ("portal_status", "email_status", "days_before_expiry")
    search_fields = ("induction__employee__full_name",)
    readonly_fields = (
        "induction",
        "expiry_date",
        "days_before_expiry",
        "portal_status",
        "email_status",
        "portal_sent_at",
        "email_sent_at",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InductionModuleReview)
class InductionModuleReviewAdmin(admin.ModelAdmin):
    list_display = (
        "completion",
        "decision",
        "reviewed_by",
        "reviewed_at",
    )
    list_filter = ("decision", "reviewed_at")
    search_fields = (
        "completion__induction__employee__full_name",
        "completion__module_title_snapshot",
        "review_note",
    )
    readonly_fields = (
        "completion",
        "decision",
        "review_note",
        "reviewed_by",
        "reviewed_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InductionAssessmentAttempt)
class InductionAssessmentAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "induction",
        "module",
        "module_version",
        "score",
        "passed",
        "submitted_at",
    )
    list_filter = (
        "passed",
        "module",
        "module_version",
    )
    search_fields = (
        "induction__employee__full_name",
        "module__title",
    )
    readonly_fields = (
        "induction",
        "module",
        "module_version",
        "submission_key",
        "answers",
        "score",
        "passed",
        "submitted_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InductionSupervisorVerification)
class InductionSupervisorVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "induction",
        "module",
        "module_version",
        "result",
        "supervisor",
        "verified_at",
    )
    list_filter = (
        "result",
        "module",
        "verified_at",
    )
    search_fields = (
        "induction__employee__full_name",
        "module__title",
        "supervisor__username",
    )
    readonly_fields = (
        "induction",
        "module",
        "module_version",
        "practical_task",
        "result",
        "comments",
        "verified_at",
        "supervisor",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False