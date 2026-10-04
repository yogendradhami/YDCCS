from io import BytesIO
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, FileResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib import colors

from dashboard.decorators import admin_required
from employees.models import Employee

from .forms import (
    InductionDeclarationForm,
    InductionSetupForm,
    ModuleCompletionForm,
    OnboardingDocumentUploadForm,
    OnboardingReviewForm,
)

from .models import (
    EmployeeInduction,
    InductionModule,
    InductionProgramme,
    OnboardingRequirement,
    EmployeeOnboardingProfile,
    EmployeeOnboardingDocument,
)


# ==========================================================
# DASHBOARD — INDUCTION LIST
# ==========================================================

@admin_required
def dashboard_induction_list(request):

    inductions = (
        EmployeeInduction.objects
        .select_related(
            "employee",
            "programme",
        )
        .order_by(
            "-assigned_at",
        )
    )

    context = {
        "inductions": inductions,

        "total": inductions.count(),

        "assigned": inductions.filter(
            status="assigned"
        ).count(),

        "in_progress": inductions.filter(
            status="in_progress"
        ).count(),

        "completed": inductions.filter(
            status="completed"
        ).count(),
    }

    return render(
        request,
        "dashboard/induction/induction_list.html",
        context,
    )


# ==========================================================
# DASHBOARD — SETUP
# ==========================================================

@admin_required
def dashboard_induction_setup(
    request,
    induction_id,
):

    induction = get_object_or_404(
        EmployeeInduction,
        id=induction_id,
    )

    if request.method == "POST":

        form = InductionSetupForm(
            request.POST,
            instance=induction,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Induction settings updated successfully.",
            )

            return redirect(
                "induction_detail",
                induction_id=induction.id,
            )

    else:

        form = InductionSetupForm(
            instance=induction,
        )

    return render(
        request,
        "dashboard/induction/induction_setup.html",
        {
            "induction": induction,
            "form": form,
        },
    )


# ==========================================================
# DASHBOARD — DETAIL
# ==========================================================

@admin_required
def dashboard_induction_detail(
    request,
    induction_id,
):

    induction = get_object_or_404(
        EmployeeInduction.objects
        .select_related(
            "employee",
            "programme",
        ),
        id=induction_id,
    )

    modules = induction.required_modules()

    completed_ids = set(
        induction.completions.values_list(
            "module_id",
            flat=True,
        )
    )

    return render(
        request,
        "dashboard/induction/induction_detail.html",
        {
            "induction": induction,
            "modules": modules,
            "completed_ids": completed_ids,
        },
    )


# ==========================================================
# DASHBOARD — CANCEL
# ==========================================================

@admin_required
def dashboard_induction_cancel(
    request,
    induction_id,
):

    induction = get_object_or_404(
        EmployeeInduction,
        id=induction_id,
    )

    if request.method == "POST":

        induction.status = "cancelled"

        induction.save(
            update_fields=[
                "status",
            ]
        )

        messages.success(
            request,
            "Induction cancelled.",
        )

    return redirect(
        "induction_dashboard",
    )


# ==========================================================
# EMPLOYEE — INDUCTION HOME
# ==========================================================

@login_required
def employee_induction(request):

    employee = get_object_or_404(
        Employee,
        user=request.user,
        active=True,
    )

    induction = get_object_or_404(
        EmployeeInduction.objects
        .select_related(
            "programme",
            "employee",
        ),
        employee=employee,
    )

    induction.mark_started()

    modules = induction.required_modules()

    completed_ids = set(
        induction.completions.values_list(
            "module_id",
            flat=True,
        )
    )

    total = modules.count()

    completed = len(completed_ids)

    progress = (
        round(
            (completed / total) * 100
        )
        if total
        else 0
    )

    declaration_form = InductionDeclarationForm(
        initial={
            "declaration_name":
                induction.declaration_name
        }
    )

    return render(
        request,
        "employees/employee_induction.html",
        {
            "employee": employee,
            "induction": induction,
            "modules": modules,
            "completed_ids": completed_ids,
            "completed": completed,
            "total": total,
            "progress": progress,
            "declaration_form": declaration_form,
        },
    )


# ==========================================================
# EMPLOYEE — MODULE
# ==========================================================


# ==========================================================
# EMPLOYEE — INDUCTION MODULE
# ==========================================================

@login_required
def employee_induction_module(
    request,
    module_id,
):
    employee = get_object_or_404(
        Employee,
        user=request.user,
        active=True,
    )

    induction = get_object_or_404(
        EmployeeInduction.objects.select_related(
            "employee",
            "programme",
        ),
        employee=employee,
    )

    # Only allow the employee to access modules
    # that are actually assigned to their induction.
    module = get_object_or_404(
        induction.required_modules(),
        id=module_id,
    )

    completion = (
        induction.completions
        .filter(module=module)
        .first()
    )

    if completion:
        completion_form = ModuleCompletionForm(
            instance=completion,
        )
    else:
        completion_form = ModuleCompletionForm()

    if request.method == "POST":

        # Do not allow completing the same module twice.
        if completion:
            messages.info(
                request,
                "This module has already been completed.",
            )

            return redirect(
                "employee_induction_module",
                module_id=module.id,
            )

        completion_form = ModuleCompletionForm(
            request.POST,
        )

        if completion_form.is_valid():

            completion = completion_form.save(
                commit=False
            )

            completion.induction = induction
            completion.module = module

            completion.save()

            messages.success(
                request,
                f'"{module.title}" has been completed successfully.',
            )

            return redirect(
                "employee_induction_module",
                module_id=module.id,
            )

    completed_ids = set(
        induction.completions.values_list(
            "module_id",
            flat=True,
        )
    )

    modules = induction.required_modules()

    return render(
        request,
        "employees/employee_induction_module.html",
        {
            "employee": employee,
            "induction": induction,
            "module": module,
            "completion": completion,
            "completion_form": completion_form,
            "completed_ids": completed_ids,
            "modules": modules,
        },
    )


# ==========================================================
# EMPLOYEE — FINAL DECLARATION
# ==========================================================

@login_required
def employee_induction_complete(request):

    employee = get_object_or_404(
        Employee,
        user=request.user,
        active=True,
    )

    induction = get_object_or_404(
        EmployeeInduction,
        employee=employee,
    )

    if request.method != "POST":

        return redirect(
            "employee_induction"
        )

    form = InductionDeclarationForm(
        request.POST,
    )

    if not form.is_valid():

        messages.error(
            request,
            "Please complete the final declaration.",
        )

        return redirect(
            "employee_induction"
        )

    induction.declaration_name = (
        form.cleaned_data[
            "declaration_name"
        ]
    )

    induction.declaration_at = timezone.now()

    induction.save(
        update_fields=[
            "declaration_name",
            "declaration_at",
        ]
    )

    if induction.mark_completed(
        request=request
    ):

        messages.success(
            request,
            "Congratulations. Your employee induction is complete.",
        )

    else:

        messages.error(
            request,
            "Please complete every mandatory induction module first.",
        )

    return redirect(
        "employee_induction"
    )


# ==========================================================
# PDF HELPERS
# ==========================================================

def _build_induction_pdf(
    induction,
    title,
    include_modules=True,
):

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    story = []

    story.append(
        Paragraph(
            "YD Commercial Cleaning",
            styles["Title"],
        )
    )

    story.append(
        Paragraph(
            title,
            styles["Heading2"],
        )
    )

    story.append(
        Spacer(
            1,
            15,
        )
    )

    employee = induction.employee

    details = [
        [
            "Employee",
            employee.full_name,
        ],
        [
            "Email",
            employee.email or "—",
        ],
        [
            "Phone",
            employee.phone or "—",
        ],
        [
            "Role",
            employee.get_role_display(),
        ],
        [
            "Employment Type",
            induction.get_employment_type_display(),
        ],
        [
            "Start Date",
            (
                induction.start_date.strftime(
                    "%d %B %Y"
                )
                if induction.start_date
                else "—"
            ),
        ],
        [
            "Supervisor",
            induction.supervisor_name or "—",
        ],
        [
            "Work Location",
            induction.primary_work_location or "—",
        ],
        [
            "Programme",
            str(induction.programme),
        ],
    ]

    table = Table(
        details,
        colWidths=[
            140,
            340,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor(
                        "#f1f5f9"
                    ),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor(
                        "#d1d5db"
                    ),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
            ]
        )
    )

    story.append(table)

    story.append(
        Spacer(
            1,
            20,
        )
    )

    if include_modules:

        story.append(
            Paragraph(
                "Completed Induction Modules",
                styles["Heading2"],
            )
        )

        rows = [
            [
                "Module",
                "Version",
                "Completed",
            ]
        ]

        for completion in (
            induction.completions
            .select_related("module")
            .all()
        ):

            rows.append(
                [
                    completion.module_title_snapshot,
                    f"v{completion.module_version}",
                    completion.completed_at.strftime(
                        "%d %b %Y %H:%M"
                    ),
                ]
            )

        if len(rows) == 1:

            rows.append(
                [
                    "No modules completed",
                    "",
                    "",
                ]
            )

        module_table = Table(
            rows,
            colWidths=[
                290,
                70,
                120,
            ],
            repeatRows=1,
        )

        module_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(
                            "#111827"
                        ),
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white,
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor(
                            "#d1d5db"
                        ),
                    ),
                    (
                        "PADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                ]
            )
        )

        story.append(
            module_table
        )

    story.append(
        Spacer(
            1,
            20,
        )
    )

    story.append(
        Paragraph(
            f"Induction Status: "
            f"<b>{induction.get_status_display()}</b>",
            styles["BodyText"],
        )
    )

    if induction.started_at:

        story.append(
            Paragraph(
                "Induction Started: "
                + induction.started_at.strftime(
                    "%d %B %Y %H:%M"
                ),
                styles["BodyText"],
            )
        )

    if induction.completed_at:

        story.append(
            Paragraph(
                "Induction Completed: "
                + induction.completed_at.strftime(
                    "%d %B %Y %H:%M"
                ),
                styles["BodyText"],
            )
        )

    if induction.declaration_name:

        story.append(
            Paragraph(
                f"Employee Declaration: "
                f"<b>{induction.declaration_name}</b>",
                styles["BodyText"],
            )
        )

    if induction.declaration_at:

        story.append(
            Paragraph(
                "Declaration Date: "
                + induction.declaration_at.strftime(
                    "%d %B %Y %H:%M"
                ),
                styles["BodyText"],
            )
        )

    story.append(
        Spacer(
            1,
            25,
        )
    )

    story.append(
        Paragraph(
            (
                "This document is an electronic record "
                "of the employee induction information "
                "held by YD Commercial Cleaning."
            ),
            styles["BodyText"],
        )
    )

    document.build(story)

    buffer.seek(0)

    return buffer


# ==========================================================
# COMPLETION PDF
# ==========================================================

@login_required
def induction_completion_pdf(
    request,
    induction_id=None,
):


    if induction_id:
        if not request.user.is_staff:
            return HttpResponse(
                "Forbidden",
                status=403,
            )

        induction = get_object_or_404(
            EmployeeInduction,
            id=induction_id,
        )

        if not request.user.is_staff:

            employee = get_object_or_404(
                Employee,
                user=request.user,
            )

            if induction.employee_id != employee.id:

                return HttpResponse(
                    "Forbidden",
                    status=403,
                )

    else:

        employee = get_object_or_404(
            Employee,
            user=request.user,
        )

        induction = get_object_or_404(
            EmployeeInduction,
            employee=employee,
        )

    if induction.status != "completed":

        return HttpResponse(
            "Induction has not been completed.",
            status=400,
        )

    pdf = _build_induction_pdf(
        induction,
        "Employee Induction Completion Certificate",
    )

    response = HttpResponse(
        pdf.getvalue(),
        content_type="application/pdf",
    )

    response[
        "Content-Disposition"
    ] = (
        'attachment; '
        f'filename="induction-completion-'
        f'{induction.employee.full_name.replace(" ", "-")}.pdf"'
    )

    return response


# ==========================================================
# START RECORD PDF
# ==========================================================

@login_required
def induction_start_record_pdf(
    request,
    induction_id=None,
):

    if induction_id:
        if not request.user.is_staff:
            return HttpResponse(
                "Forbidden",
                status=403,
            )

        induction = get_object_or_404(
            EmployeeInduction,
            id=induction_id,
        )

        # if not request.user.is_staff:

        #     employee = get_object_or_404(
        #         Employee,
        #         user=request.user,
        #     )

        #     if induction.employee_id != employee.id:

        #         return HttpResponse(
        #             "Forbidden",
        #             status=403,
        #         )

    else:

        employee = get_object_or_404(
            Employee,
            user=request.user,
            active=True,
        )

        induction = get_object_or_404(
            EmployeeInduction,
            employee=employee,
        )

    pdf = _build_induction_pdf(
        induction,
        "Employee Induction Start Record",
        include_modules=False,
    )

    response = HttpResponse(
        pdf.getvalue(),
        content_type="application/pdf",
    )

    response[
        "Content-Disposition"
    ] = (
        'attachment; '
        f'filename="induction-start-'
        f'{induction.employee.full_name.replace(" ", "-")}.pdf"'
    )

    return response


@login_required
def employee_onboarding(request):
    employee = get_object_or_404(
        Employee,
        user=request.user,
    )

    profile, _ = EmployeeOnboardingProfile.objects.get_or_create(
        employee=employee
    )

    requirements = list(
        profile.required_requirements()
    )

    requirement_rows = []

    for requirement in requirements:
        document = profile.current_document_for(
            requirement
        )

        requirement_rows.append(
            {
                "requirement": requirement,
                "document": document,
            }
        )

    all_documents = (
        EmployeeOnboardingDocument.objects
        .filter(employee=employee)
        .select_related("requirement")
        .order_by("-uploaded_at")
    )

    context = {
        "employee": employee,
        "profile": profile,
        "requirement_rows": requirement_rows,
        "all_documents": all_documents,
    }

    return render(
        request,
        "employees/employee_onboarding.html",
        context,
    )


@login_required
@require_POST
def employee_onboarding_upload(
    request,
    requirement_id,
):
    employee = get_object_or_404(
        Employee,
        user=request.user,
    )

    requirement = get_object_or_404(
        OnboardingRequirement,
        id=requirement_id,
        active=True,
    )

    if not requirement.employee_upload_allowed:
        raise PermissionDenied(
            "Employees cannot upload this requirement."
        )

    form = OnboardingDocumentUploadForm(
        request.POST,
        request.FILES,
    )

    if not form.is_valid():
        messages.error(
            request,
            "Please correct the document upload.",
        )
        return redirect("employee_onboarding")

    with transaction.atomic():

        # Make previous document versions non-current.
        EmployeeOnboardingDocument.objects.filter(
            employee=employee,
            requirement=requirement,
            is_current=True,
        ).update(
            is_current=False
        )

        latest = (
            EmployeeOnboardingDocument.objects
            .filter(
                employee=employee,
                requirement=requirement,
            )
            .order_by("-version")
            .first()
        )

        next_version = (
            latest.version + 1
            if latest
            else 1
        )

        document = form.save(commit=False)

        document.employee = employee
        document.requirement = requirement
        document.version = next_version
        document.is_current = True
        document.status = "pending"
        document.original_filename = (
            request.FILES["file"].name
        )
        document.uploaded_ip = (
            request.META.get("REMOTE_ADDR")
        )

        if requirement.expiry_days:
            document.expires_at = (
                document.calculate_expiry()
            )

        document.save()

        profile, _ = (
            EmployeeOnboardingProfile.objects
            .get_or_create(employee=employee)
        )

        profile.status = "under_review"
        profile.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    messages.success(
        request,
        f"{requirement.title} uploaded successfully "
        "and is waiting for HR review.",
    )

    return redirect("employee_onboarding")

@login_required
def onboarding_document_download(
    request,
    document_id,
):
    document = get_object_or_404(
        EmployeeOnboardingDocument.objects.select_related(
            "employee",
            "requirement",
        ),
        id=document_id,
    )

    is_staff = request.user.is_staff

    employee = Employee.objects.filter(
        user=request.user
    ).first()

    if not is_staff:
        if employee is None:
            raise PermissionDenied

        if document.employee_id != employee.id:
            raise PermissionDenied

    try:
        document.file.open("rb")
    except Exception:
        raise Http404(
            "The requested document could not be opened."
        )

    filename = (
        document.original_filename
        or Path(document.file.name).name
    )

    response = FileResponse(
        document.file,
        as_attachment=True,
        filename=filename,
    )

    response["Cache-Control"] = (
        "private, no-store, max-age=0"
    )

    response["Pragma"] = "no-cache"

    return response

@login_required
def onboarding_dashboard(request):
    if not request.user.is_staff:
        raise PermissionDenied

    profiles = (
        EmployeeOnboardingProfile.objects
        .select_related(
            "employee",
            "reviewed_by",
        )
        .order_by(
            "status",
            "-updated_at",
        )
    )

    context = {
        "profiles": profiles,
    }

    return render(
        request,
        "dashboard/onboarding/onboarding_list.html",
        context,
    )

@login_required
def onboarding_detail(
    request,
    employee_id,
):
    if not request.user.is_staff:
        raise PermissionDenied

    employee = get_object_or_404(
        Employee,
        id=employee_id,
    )

    profile, _ = (
        EmployeeOnboardingProfile.objects
        .get_or_create(employee=employee)
    )

    requirements = list(
        profile.required_requirements()
    )

    requirement_rows = []

    for requirement in requirements:
        document = profile.current_document_for(
            requirement
        )

        requirement_rows.append(
            {
                "requirement": requirement,
                "document": document,
            }
        )

    documents = (
        EmployeeOnboardingDocument.objects
        .filter(employee=employee)
        .select_related(
            "requirement",
            "reviewed_by",
        )
        .order_by(
            "-is_current",
            "-uploaded_at",
        )
    )

    context = {
        "employee": employee,
        "profile": profile,
        "requirement_rows": requirement_rows,
        "documents": documents,
    }

    return render(
        request,
        "dashboard/onboarding/onboarding_detail.html",
        context,
    )

@login_required
@require_POST
def onboarding_document_review(
    request,
    document_id,
):
    if not request.user.is_staff:
        raise PermissionDenied

    document = get_object_or_404(
        EmployeeOnboardingDocument.objects.select_related(
            "employee",
            "requirement",
        ),
        id=document_id,
    )

    form = OnboardingReviewForm(
        request.POST,
        instance=document,
    )

    if not form.is_valid():
        messages.error(
            request,
            "Please correct the review information.",
        )

        return redirect(
            "onboarding_detail",
            employee_id=document.employee_id,
        )

    document = form.save(commit=False)

    document.reviewed_by = request.user
    document.reviewed_at = timezone.now()

    if (
        document.status == "approved"
        and document.requirement.expiry_days
        and not document.expires_at
    ):
        document.expires_at = (
            document.calculate_expiry()
        )

    document.save()

    profile = get_object_or_404(
        EmployeeOnboardingProfile,
        employee_id=document.employee_id,
    )

    profile.refresh_status()

    messages.success(
        request,
        "Document review saved.",
    )

    return redirect(
        "onboarding_detail",
        employee_id=document.employee_id,
    )

@login_required
@require_POST
def onboarding_set_status(request, employee_id, status):
    """
    HR-only onboarding status transition.

    Ready for Work can only be granted when:
    - induction is complete
    - all required documents are approved
    - no required documents are pending
    - no required documents are rejected
    - no required documents are expired
    """

    if not request.user.is_staff:
        return HttpResponseForbidden(
            "You are not authorised to change onboarding status."
        )

    employee = get_object_or_404(
        Employee,
        id=employee_id,
    )

    profile = get_object_or_404(
        EmployeeOnboardingProfile,
        employee=employee,
    )

    if status == "ready":

        if not profile.can_be_ready_for_work():
            messages.error(
                request,
                (
                    "This employee cannot be marked Ready for Work. "
                    "Complete induction and approve all required "
                    "onboarding documents first."
                ),
            )

            return redirect(
                "onboarding_detail",
                employee_id=employee.id,
            )

        profile.approve_for_work(
            request.user
        )

        messages.success(
            request,
            (
                f"{employee.full_name} has been approved "
                "as Ready for Work."
            ),
        )

    elif status == "blocked":

        profile.block_from_work(
            request.user,
            notes=request.POST.get(
                "notes",
                "",
            ).strip(),
        )

        messages.warning(
            request,
            (
                f"{employee.full_name} has been blocked "
                "from work."
            ),
        )

    else:

        messages.error(
            request,
            "Invalid onboarding status transition.",
        )

    return redirect(
        "onboarding_detail",
        employee_id=employee.id,
    )