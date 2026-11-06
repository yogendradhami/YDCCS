import csv
import uuid
from datetime import timedelta
from io import BytesIO, StringIO
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import models, transaction
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from dashboard.decorators import admin_required
from employees.models import Employee
from notifications.utils import notify_user

from .forms import (
    InductionDeclarationForm,
    InductionModuleReviewForm,
    InductionSupervisorVerificationForm,
    InductionSetupForm,
    ModuleAssessmentForm,
    ModuleCompletionForm,
    OnboardingDocumentUploadForm,
    OnboardingReviewForm,
)

from .models import (
    EmployeeInduction,
    InductionAssessmentAttempt,
    InductionModule,
    InductionModuleCompletion,
    InductionModuleReview,
    InductionProgramme,
    InductionSupervisorVerification,
    OnboardingRequirement,
    EmployeeOnboardingProfile,
    EmployeeOnboardingDocument,
    add_calendar_months,
)


def _prepare_module_progress(induction, modules):
    for module in modules:
        training_version = module.training_versions.filter(
            version=module.version,
        ).first()
        module.training_version_record = training_version
        module.training_content = (
            training_version.content
            if training_version
            else {
                "introduction": module.content,
                "objectives": [],
                "sections": [],
                "assessment": [],
                "verification_tasks": [],
            }
        )
        module.current_completion = induction.latest_module_completion(
            module=module,
            module_version=module.version,
        )
        current_attempts = induction.assessment_attempts.filter(
            module=module,
            module_version=module.version,
        )
        if induction.renewal_started_at:
            current_attempts = current_attempts.filter(
                submitted_at__gte=induction.renewal_started_at,
            )
        module.current_attempt = current_attempts.first()
        module.best_attempt = (
            current_attempts.filter(
                passed=True,
            )
            .order_by("-score", "-submitted_at")
            .first()
        )
        module.assessment_passed = current_attempts.filter(passed=True).exists()
        module.practical_tasks = module.training_content.get(
            "verification_tasks",
            [],
        )
        verifications = induction.supervisor_verifications.filter(
            module=module,
            module_version=module.version,
        )
        if induction.renewal_started_at:
            verifications = verifications.filter(
                verified_at__gte=induction.renewal_started_at,
            )
        module.current_verification = verifications.first()
        module.retraining_required = bool(
            module.current_completion
            and module.current_completion.review_status == "redo_required"
        ) or (
            not module.current_completion
            and induction.completions.filter(module=module).exists()
        )
    return modules


def _write_training_csv_row(writer, values):
    protected_values = []
    for value in values:
        if isinstance(value, str) and value.lstrip(" \t\r\n").startswith(
            ("=", "+", "-", "@")
        ):
            value = f"'{value}"
        protected_values.append(value)
    writer.writerow(protected_values)


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
    today = timezone.localdate()

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
        "renewals_due": inductions.filter(
            expires_on__lt=today,
        ).exclude(status="cancelled").count(),
        "renewals_soon": inductions.filter(
            expires_on__gte=today,
            expires_on__lte=today + timedelta(days=30),
        ).exclude(status="cancelled").count(),
        "pending_reviews": InductionModuleCompletion.objects.filter(
            induction__in=inductions,
            review_status="pending",
            module_version=models.F("module__version"),
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
            induction = form.save()
            if induction.completed_at:
                induction.expires_on = add_calendar_months(
                    timezone.localtime(induction.completed_at).date(),
                    induction.expiry_months,
                )
                induction.save(update_fields=["expires_on"])

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


@admin_required
@require_POST
def dashboard_induction_publish(request, induction_id=None):
    output = StringIO()
    try:
        call_command("seed_induction", stdout=output)
    except CommandError as error:
        messages.error(request, f"Induction curriculum was not published: {error}")
    else:
        messages.success(
            request,
            "Approved induction curriculum published. "
            + " ".join(output.getvalue().split()),
        )
    if induction_id:
        return redirect("induction_detail", induction_id=induction_id)
    return redirect("induction_dashboard")


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

    modules = _prepare_module_progress(
        induction,
        list(induction.required_modules()),
    )

    completed_ids = induction.completed_module_ids()
    now = timezone.localtime()
    pending_reviews = induction.completions.filter(
        review_status="pending",
        module_version=models.F("module__version"),
    ).count()
    required_count = induction.required_count()
    completion_count = len(completed_ids)

    return render(
        request,
        "dashboard/induction/induction_detail.html",
        {
            "induction": induction,
            "modules": modules,
            "completed_ids": completed_ids,
            "progress": (
                round(completion_count * 100 / required_count)
                if required_count
                else 0
            ),
            "review_form": InductionModuleReviewForm(),
            "attempts": induction.assessment_attempts.select_related(
                "module",
            )[:50],
            "verifications": induction.supervisor_verifications.select_related(
                "module",
                "supervisor",
            )[:50],
            "retraining_ids": induction.retraining_module_ids(),
            "pending_reviews": pending_reviews,
            "expiry_elapsed": bool(
                induction.expires_on
                and induction.expires_on <= timezone.localdate()
            ),
            "days_until_expiry": (
                (induction.expires_on - now.date()).days
                if induction.expires_on
                else None
            ),
        },
    )


@admin_required
@require_POST
def induction_module_review(request, induction_id, module_id, completion_id):
    induction = get_object_or_404(
        EmployeeInduction.objects.select_related("employee"),
        pk=induction_id,
    )
    module = get_object_or_404(
        induction.required_modules(),
        pk=module_id,
    )
    completion = get_object_or_404(
        InductionModuleCompletion,
        pk=completion_id,
        induction=induction,
        module=module,
        module_version=module.version,
    )
    latest_completion = induction.latest_module_completion(
        module,
        module_version=module.version,
    )
    if latest_completion != completion:
        messages.error(
            request,
            "This submission has been superseded. Review the latest module submission.",
        )
        return redirect("induction_detail", induction_id=induction.pk)

    form = InductionModuleReviewForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Choose a review decision and add any required note.")
        return redirect("induction_detail", induction_id=induction.pk)

    with transaction.atomic():
        completion.review_status = form.cleaned_data["decision"]
        completion.review_note = form.cleaned_data["review_note"].strip()
        completion.reviewed_by = request.user
        completion.reviewed_at = timezone.now()
        InductionModuleReview.objects.create(
            completion=completion,
            decision=completion.review_status,
            review_note=completion.review_note,
            reviewed_by=request.user,
        )
        completion.save(
            update_fields=[
                "review_status",
                "review_note",
                "reviewed_by",
                "reviewed_at",
            ]
        )
    if completion.review_status == "redo_required":
        induction.status = "in_progress"
        induction.save(update_fields=["status"])
        message = (
            f"Redo requested for “{module.title}”. "
            "The employee has been notified in their portal."
        )
    else:
        induction.mark_completed()
        message = (
            f"“{module.title}” was approved. "
            "The employee has been notified in their portal."
        )

    if induction.employee.user_id:
        if completion.review_status == "redo_required":
            notification_message = (
                f"Your manager asked you to redo “{module.title}”. "
                f"{completion.review_note} Open the module and review the "
                "material before submitting it again."
            )
        else:
            notification_message = (
                f"Your completion of “{module.title}” has been approved."
            )
        notify_user(
            induction.employee.user,
            "Induction module review",
            notification_message,
            "employee",
            reverse("employee_induction_module", args=[module.pk]),
        )
    messages.success(request, message)
    return redirect("induction_detail", induction_id=induction.pk)


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

    induction.begin_renewal_if_expired()
    induction.mark_started()

    modules = _prepare_module_progress(
        induction,
        list(induction.required_modules()),
    )

    completed_ids = induction.completed_module_ids()

    total = len(modules)

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
            "retraining_ids": induction.retraining_module_ids(),
            "assessment_attempts": sum(
                induction.assessment_attempts.filter(
                    module=module,
                    module_version=module.version,
                ).count()
                for module in modules
            ),
            "verification_pending": sum(
                bool(module.practical_tasks)
                and (
                    not module.current_verification
                    or module.current_verification.result != "competent"
                )
                for module in modules
            ),
            "completed": completed,
            "total": total,
            "outstanding": total - completed,
            "progress": progress,
            "declaration_form": declaration_form,
            "is_renewal": bool(induction.renewal_started_at),
            "expires_on": induction.expires_on,
            "days_until_expiry": (
                (induction.expires_on - timezone.localdate()).days
                if induction.expires_on
                else None
            ),
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
    induction.begin_renewal_if_expired()

    # Only allow the employee to access modules
    # that are actually assigned to their induction.
    module = get_object_or_404(
        induction.required_modules(),
        id=module_id,
    )

    training_version = module.training_versions.filter(
        version=module.version,
    ).first()
    training = (
        training_version.content
        if training_version
        else {
            "introduction": module.content,
            "objectives": [],
            "sections": [],
            "assessment": [],
            "verification_tasks": [],
            "legacy_snapshot": True,
        }
    )
    questions = training.get("assessment", [])
    latest_completion = induction.latest_module_completion(
        module=module,
        module_version=module.version,
    )
    completion = (
        latest_completion
        if latest_completion and latest_completion.review_status != "redo_required"
        else None
    )
    attempts = induction.assessment_attempts.filter(
        module=module,
        module_version=module.version,
    )
    assessment_attempts = attempts
    if induction.renewal_started_at:
        assessment_attempts = assessment_attempts.filter(
            submitted_at__gte=induction.renewal_started_at,
        )
    if latest_completion and latest_completion.review_status == "redo_required":
        assessment_attempts = assessment_attempts.filter(
            submitted_at__gt=latest_completion.completed_at,
        )
    latest_attempt = attempts.first()
    assessment_passed = assessment_attempts.filter(passed=True).exists()
    assessment_form = ModuleAssessmentForm(
        questions,
        initial={"submission_key": uuid.uuid4()},
    )
    completion_form = ModuleCompletionForm()
    attempt_feedback = []
    assessment_score = None

    if request.method == "POST":
        action = request.POST.get("action")

        if completion:
            messages.info(
                request,
                "This training version has already been acknowledged. Its record is retained.",
            )
        elif action == "submit_assessment":
            if not training_version or not questions:
                messages.error(
                    request,
                    "This module's assessment is not configured yet. Contact your manager.",
                )
            else:
                assessment_form = ModuleAssessmentForm(
                    questions,
                    request.POST,
                )
                if assessment_form.is_valid():
                    submission_key = assessment_form.cleaned_data[
                        "submission_key"
                    ]
                    answers = {
                        f"question_{index}": int(
                            assessment_form.cleaned_data[f"question_{index}"]
                        )
                        for index in range(len(questions))
                    }
                    correct_count = sum(
                        answers[f"question_{index}"] == question["correct"]
                        for index, question in enumerate(questions)
                    )
                    score = round(correct_count * 100 / len(questions))
                    latest_attempt, _ = (
                        InductionAssessmentAttempt.objects.get_or_create(
                            submission_key=submission_key,
                            defaults={
                                "induction": induction,
                                "module": module,
                                "module_version": module.version,
                                "answers": answers,
                                "score": score,
                                "passed": score >= 80,
                            },
                        )
                    )
                    if (
                        latest_attempt.induction_id != induction.pk
                        or latest_attempt.module_id != module.pk
                        or latest_attempt.module_version != module.version
                    ):
                        assessment_form.add_error(
                            None,
                            "This assessment submission has already been used.",
                        )
                        latest_attempt = None
                    if latest_attempt:
                        assessment_score = latest_attempt.score
                        assessment_passed = assessment_attempts.filter(
                            passed=True,
                        ).exists()
                        attempt_feedback = _build_assessment_feedback(
                            questions,
                            latest_attempt.answers,
                        )
                        if latest_attempt.passed:
                            messages.success(
                                request,
                                "Assessment passed. You can now acknowledge this training version.",
                            )
                        else:
                            messages.warning(
                                request,
                                "Assessment not passed yet. Review the explanations and retake it.",
                            )
                        assessment_form = ModuleAssessmentForm(
                            questions,
                            initial={"submission_key": uuid.uuid4()},
                        )
                else:
                    messages.error(
                        request,
                        "Answer every assessment question before submitting.",
                    )
        elif action == "complete_module":
            completion_form = ModuleCompletionForm(request.POST)
            passed_assessment = assessment_attempts.filter(passed=True).exists()
            if latest_completion and latest_completion.review_status == "redo_required":
                passed_assessment = assessment_attempts.filter(
                    passed=True,
                    submitted_at__gt=latest_completion.completed_at,
                ).exists()
            if not passed_assessment:
                completion_form.add_error(
                    None,
                    "Pass this module's assessment before acknowledging it.",
                )
            elif not completion_form.is_valid():
                messages.error(
                    request,
                    "Confirm the acknowledgement before completing the module.",
                )
            else:
                previous_attempt = (
                    induction.completions.filter(
                        module=module,
                        module_version=module.version,
                    )
                    .order_by("-attempt_number", "-completed_at")
                    .first()
                )
                defaults = {
                    "module_title_snapshot": module.title,
                    "module_version": module.version,
                    "attempt_number": (
                        previous_attempt.attempt_number + 1
                        if previous_attempt
                        else 1
                    ),
                    "acknowledgement": True,
                    "review_status": "pending",
                    "review_note": "",
                    "reviewed_by": None,
                    "reviewed_at": None,
                    "acknowledgement_text": (
                        training_version.acknowledgement_text
                        if training_version
                        else module.acknowledgement_text
                    ),
                    "notes": completion_form.cleaned_data["notes"],
                }
                with transaction.atomic():
                    latest_completion, created = (
                        InductionModuleCompletion.objects.get_or_create(
                            induction=induction,
                            module=module,
                            module_version=module.version,
                            attempt_number=defaults["attempt_number"],
                            defaults=defaults,
                        )
                    )
                    induction.status = "in_progress"
                    induction.save(update_fields=["status"])
                if created:
                    messages.success(
                        request,
                        f'"{module.title}" v{module.version} was submitted for manager review.',
                    )
                else:
                    messages.info(
                        request,
                        "This training version was already acknowledged.",
                    )
        else:
            messages.error(request, "Choose an assessment or acknowledgement action.")

    if latest_attempt and not attempt_feedback and latest_attempt.answers:
        attempt_feedback = _build_assessment_feedback(
            questions,
            latest_attempt.answers,
        )
        assessment_score = latest_attempt.score

    modules = _prepare_module_progress(
        induction,
        list(induction.required_modules()),
    )
    completed_ids = induction.completed_module_ids()
    current_module = next(item for item in modules if item.pk == module.pk)

    return render(
        request,
        "employees/employee_induction_module.html",
        {
            "employee": employee,
            "induction": induction,
            "module": current_module,
            "training": training,
            "training_version": training_version,
            "completion": completion,
            "latest_completion": latest_completion,
            "completion_form": completion_form,
            "assessment_form": assessment_form,
            "attempts": attempts,
            "latest_attempt": latest_attempt,
            "assessment_score": assessment_score,
            "assessment_passed": assessment_passed,
            "attempt_feedback": attempt_feedback,
            "passing_score": 80,
            "verification_url": (
                reverse(
                    "induction_supervisor_verification",
                    args=[induction.pk, module.pk],
                )
                if training.get("verification_tasks")
                else None
            ),
            "completed_ids": completed_ids,
            "retraining_ids": induction.retraining_module_ids(),
            "modules": modules,
        },
    )


def _build_assessment_feedback(questions, answers):
    feedback = []
    for index, question in enumerate(questions):
        selected = answers.get(f"question_{index}")
        correct = question["correct"]
        feedback.append(
            {
                "question": question["question"],
                "selected": selected,
                "selected_text": (
                    question["choices"][selected]
                    if isinstance(selected, int)
                    and 0 <= selected < len(question["choices"])
                    else "Not answered"
                ),
                "correct_text": question["choices"][correct],
                "is_correct": selected == correct,
                "explanation": question["explanation"],
            }
        )
    return feedback


@admin_required
def induction_supervisor_verification(request, induction_id, module_id):
    induction = get_object_or_404(
        EmployeeInduction.objects.select_related("employee"),
        pk=induction_id,
    )
    module = get_object_or_404(
        induction.required_modules(),
        pk=module_id,
    )
    training_version = module.training_versions.filter(
        version=module.version,
    ).first()
    tasks = (
        training_version.content.get("verification_tasks", [])
        if training_version
        else []
    )
    if not tasks:
        raise Http404("This module has no practical verification tasks.")

    form = InductionSupervisorVerificationForm(tasks)
    if request.method == "POST":
        form = InductionSupervisorVerificationForm(tasks, request.POST)
        if form.is_valid():
            InductionSupervisorVerification.objects.create(
                induction=induction,
                module=module,
                module_version=module.version,
                practical_task=form.cleaned_data["practical_task"],
                result=form.cleaned_data["result"],
                comments=form.cleaned_data["comments"],
                supervisor=request.user,
            )
            messages.success(
                request,
                f"Practical verification recorded for {module.title}.",
            )
            return redirect(
                "induction_detail",
                induction_id=induction.pk,
            )

    verification_history = induction.supervisor_verifications.filter(
        module=module,
        module_version=module.version,
    ).select_related("supervisor")
    return render(
        request,
        "dashboard/induction/induction_verification.html",
        {
            "induction": induction,
            "module": module,
            "training_version": training_version,
            "form": form,
            "verification_history": verification_history,
        },
    )


@admin_required
def induction_training_export(request, induction_id):
    induction = get_object_or_404(
        EmployeeInduction.objects.select_related("employee", "programme"),
        pk=induction_id,
    )
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="induction-{induction.pk}-training-records.csv"'
    )
    writer = csv.writer(response)
    _write_training_csv_row(
        writer,
        [
            "Employee",
            "Training type",
            "Module",
            "Version",
            "Result",
            "Score",
            "Recorded at",
            "Recorded by",
            "Notes",
        ]
    )
    for completion in induction.completions.select_related("module").order_by(
        "completed_at",
    ):
        _write_training_csv_row(
            writer,
            [
                induction.employee.full_name,
                "Acknowledgement",
                completion.module_title_snapshot,
                completion.module_version,
                "Completed",
                "",
                completion.completed_at.isoformat(),
                induction.declaration_name or "",
                completion.notes,
            ]
        )
    for attempt in induction.assessment_attempts.select_related("module").order_by(
        "submitted_at",
    ):
        _write_training_csv_row(
            writer,
            [
                induction.employee.full_name,
                "Assessment",
                attempt.module.title,
                attempt.module_version,
                "Pass" if attempt.passed else "Fail",
                attempt.score,
                attempt.submitted_at.isoformat(),
                "",
                "",
            ]
        )
    for verification in induction.supervisor_verifications.select_related(
        "module",
        "supervisor",
    ).order_by("verified_at"):
        _write_training_csv_row(
            writer,
            [
                induction.employee.full_name,
                "Practical verification",
                verification.module.title,
                verification.module_version,
                verification.get_result_display(),
                "",
                verification.verified_at.isoformat(),
                verification.supervisor.get_full_name()
                or verification.supervisor.get_username(),
                f"{verification.practical_task}: {verification.comments}",
            ]
        )
    return response


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
    induction.begin_renewal_if_expired()

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