from django.contrib import admin

from .models import (
    EmployeeInduction,
    InductionModule,
    InductionModuleCompletion,
    InductionProgramme,
)


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
        "completed_at",
        "acknowledgement",
    )

    list_filter = (
        "acknowledgement",
    )