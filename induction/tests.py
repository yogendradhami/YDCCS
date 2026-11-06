from copy import deepcopy
from datetime import timedelta
from io import StringIO
import uuid
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser, User
from django.core import mail
from django.core.management import call_command
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from employees.models import Employee
from notifications.models import Notification

from .middleware import EmployeeInductionMiddleware
from .models import (
    EmployeeInduction,
    InductionAssessmentAttempt,
    InductionModule,
    InductionModuleCompletion,
    InductionModuleReview,
    InductionModuleVersion,
    InductionProgramme,
    InductionSupervisorVerification,
)
from .training_content import MODULES


class InductionSeederTests(TestCase):
    def test_seed_is_idempotent_and_preserves_history_on_content_update(self):
        call_command("seed_induction", stdout=StringIO())
        call_command("seed_induction", stdout=StringIO())

        modules = list(InductionModule.objects.filter(active=True))
        self.assertEqual(len(modules), 10)
        self.assertTrue(all(module.version == 1 for module in modules))

        employee = Employee.objects.create(
            full_name="Seeder Test Employee",
            phone="0400000000",
        )
        induction = employee.induction
        induction.status = "completed"
        induction.save(update_fields=["status"])
        module = InductionModule.objects.get(code=MODULES[0]["code"])
        completion = InductionModuleCompletion.objects.create(
            induction=induction,
            module=module,
            module_title_snapshot=module.title,
            module_version=1,
            acknowledgement_text=module.acknowledgement_text,
        )
        completed_at = completion.completed_at

        revised_modules = deepcopy(MODULES)
        revised_modules[0]["content"]["introduction"] += (
            " Revised learning material."
        )
        with patch(
            "induction.management.commands.seed_induction.MODULES",
            revised_modules,
        ):
            call_command("seed_induction", stdout=StringIO())
            call_command("seed_induction", stdout=StringIO())

        module.refresh_from_db()
        induction.refresh_from_db()
        completion.refresh_from_db()
        self.assertEqual(module.version, 2)
        self.assertEqual(induction.status, "in_progress")
        self.assertEqual(completion.module_version, 1)
        self.assertEqual(completion.completed_at, completed_at)
        self.assertEqual(
            InductionModuleVersion.objects.filter(module=module).count(),
            2,
        )


class InductionTrainingContentTests(TestCase):
    def test_ten_modules_have_distinct_complete_training_packages(self):
        self.assertEqual(len(MODULES), 10)
        self.assertEqual(len({module["code"] for module in MODULES}), 10)
        self.assertEqual(
            len({module["content"]["introduction"] for module in MODULES}),
            10,
        )
        self.assertEqual(
            len({module["content"]["scenario"]["title"] for module in MODULES}),
            10,
        )
        self.assertEqual(
            len({module["acknowledgement_text"] for module in MODULES}),
            10,
        )
        questions = [
            question["question"]
            for module in MODULES
            for question in module["content"]["assessment"]
        ]
        self.assertEqual(len(questions), 60)
        self.assertEqual(len(set(questions)), 60)

        for module in MODULES:
            with self.subTest(module=module["code"]):
                content = module["content"]
                self.assertTrue(module["acknowledgement_text"])
                self.assertGreaterEqual(len(content["objectives"]), 3)
                self.assertGreaterEqual(len(content["sections"]), 3)
                self.assertTrue(content["procedure"])
                self.assertGreaterEqual(len(content["examples"]), 2)
                self.assertTrue(content["responsibilities"])
                self.assertTrue(content["mistakes"])
                self.assertTrue(content["when_things_go_wrong"])
                self.assertTrue(content["scenario"]["prompt"])
                self.assertEqual(len(content["assessment"]), 6)


class InductionAssessmentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="training-employee")
        self.employee = Employee.objects.create(
            user=self.user,
            full_name="Training Employee",
            phone="0400000000",
        )
        self.programme = InductionProgramme.objects.create(
            name="Training test programme",
        )
        self.induction = EmployeeInduction.objects.create(
            employee=self.employee,
            programme=self.programme,
        )
        self.content = MODULES[0]["content"]
        self.module = InductionModule.objects.create(
            code=MODULES[0]["code"],
            title=MODULES[0]["title"],
            category=MODULES[0]["category"],
            summary=MODULES[0]["summary"],
            content="Training content",
            acknowledgement_text=MODULES[0]["acknowledgement_text"],
            sort_order=MODULES[0]["sort_order"],
        )
        InductionModuleVersion.objects.create(
            module=self.module,
            version=1,
            content=self.content,
            acknowledgement_text=MODULES[0]["acknowledgement_text"],
        )
        self.client = Client()
        self.client.force_login(self.user)
        self.url = reverse(
            "employee_induction_module",
            args=[self.module.pk],
        )

    def _assessment_data(self, passed, submission_key=None):
        data = {
            "action": "submit_assessment",
            "submission_key": str(submission_key or uuid.uuid4()),
        }
        for index, question in enumerate(self.content["assessment"]):
            answer = question["correct"]
            if not passed:
                answer = 0 if answer != 0 else 1
            data[f"question_{index}"] = str(answer)
        return data

    def test_assessment_gate_and_successful_acknowledgement(self):
        failed_attempt = self._assessment_data(passed=False)
        response = self.client.post(self.url, failed_attempt)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            InductionAssessmentAttempt.objects.get().score,
            0,
        )

        response = self.client.post(
            self.url,
            {"action": "complete_module", "acknowledgement": "on"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            InductionModuleCompletion.objects.filter(
                induction=self.induction,
                module=self.module,
            ).exists()
        )

        self.client.post(self.url, self._assessment_data(passed=True))
        self.assertEqual(
            InductionAssessmentAttempt.objects.filter(passed=True).count(),
            1,
        )
        response = self.client.post(
            self.url,
            {"action": "complete_module", "acknowledgement": "on"},
        )
        self.assertEqual(response.status_code, 200)
        completion = InductionModuleCompletion.objects.get(
            induction=self.induction,
            module=self.module,
        )
        self.assertEqual(completion.module_version, 1)
        self.assertTrue(completion.acknowledgement)

    def test_assessment_submission_key_prevents_duplicate_attempts(self):
        key = uuid.uuid4()
        data = self._assessment_data(passed=True, submission_key=key)

        self.client.post(self.url, data)
        self.client.post(self.url, data)

        self.assertEqual(
            InductionAssessmentAttempt.objects.filter(
                submission_key=key,
            ).count(),
            1,
        )

    def test_new_version_requires_retraining_without_changing_history(self):
        old_completion = InductionModuleCompletion.objects.create(
            induction=self.induction,
            module=self.module,
            module_title_snapshot=self.module.title,
            module_version=1,
            acknowledgement=True,
            acknowledgement_text="I completed version 1.",
        )
        completed_at = old_completion.completed_at
        self.module.version = 2
        self.module.save(update_fields=["version"])
        InductionModuleVersion.objects.create(
            module=self.module,
            version=2,
            content=self.content,
            acknowledgement_text=MODULES[0]["acknowledgement_text"],
        )

        self.assertEqual(
            InductionModuleCompletion.objects.get(pk=old_completion.pk).completed_at,
            completed_at,
        )
        self.assertNotIn(
            self.module.pk,
            self.induction.completed_module_ids(),
        )
        self.assertIn(
            self.module.pk,
            self.induction.retraining_module_ids(),
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Training version 2")

    def test_expiry_renewal_creates_a_new_completion_attempt(self):
        prior_completion = InductionModuleCompletion.objects.create(
            induction=self.induction,
            module=self.module,
            module_title_snapshot=self.module.title,
            module_version=1,
            acknowledgement_text="I completed this module.",
            review_status="approved",
        )
        prior_completed_at = timezone.now() - timedelta(days=1)
        InductionModuleCompletion.objects.filter(
            pk=prior_completion.pk,
        ).update(completed_at=prior_completed_at)
        self.induction.status = "in_progress"
        self.induction.renewal_started_at = timezone.now()
        self.induction.save(update_fields=["status", "renewal_started_at"])

        self.client.post(self.url, self._assessment_data(passed=True))
        response = self.client.post(
            self.url,
            {"action": "complete_module", "acknowledgement": "on"},
        )

        self.assertEqual(response.status_code, 200)
        renewed_completion = InductionModuleCompletion.objects.get(
            induction=self.induction,
            module=self.module,
            attempt_number=2,
        )
        self.assertEqual(renewed_completion.review_status, "pending")
        self.assertEqual(
            InductionModuleCompletion.objects.filter(
                induction=self.induction,
                module=self.module,
            ).count(),
            2,
        )

    def test_supervisor_verification_and_training_export(self):
        verification_pack = next(
            item
            for item in MODULES
            if item["content"]["verification_tasks"]
        )
        verification_module = InductionModule.objects.create(
            code=verification_pack["code"],
            title=verification_pack["title"],
            category=verification_pack["category"],
            summary=verification_pack["summary"],
            content="Training content",
            acknowledgement_text=verification_pack["acknowledgement_text"],
            sort_order=verification_pack["sort_order"],
        )
        InductionModuleVersion.objects.create(
            module=verification_module,
            version=1,
            content=verification_pack["content"],
            acknowledgement_text=verification_pack["acknowledgement_text"],
        )
        supervisor = User.objects.create_superuser(
            username="training-supervisor",
            password="test-password",
        )
        client = Client()
        client.force_login(supervisor)
        verification_url = reverse(
            "induction_supervisor_verification",
            args=[self.induction.pk, verification_module.pk],
        )
        response = client.post(
            verification_url,
            {
                "practical_task": (
                    verification_pack["content"]["verification_tasks"][0]
                ),
                "result": "competent",
                "comments": "Completed safely under observation.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(InductionSupervisorVerification.objects.count(), 1)
        InductionModuleCompletion.objects.create(
            induction=self.induction,
            module=self.module,
            module_title_snapshot=self.module.title,
            module_version=1,
            acknowledgement_text="I completed this module.",
            notes="=SUM(1,1)",
        )

        export_url = reverse(
            "induction_training_export",
            args=[self.induction.pk],
        )
        response = client.get(export_url)
        self.assertEqual(response.status_code, 200)
        export = response.content.decode()
        self.assertIn("Practical verification", export)
        self.assertIn("Completed safely under observation.", export)
        self.assertIn("'=SUM(1,1)", export)

    def test_manager_can_reject_submission_and_employee_can_redo_it(self):
        self.client.post(self.url, self._assessment_data(passed=True))
        self.client.post(
            self.url,
            {"action": "complete_module", "acknowledgement": "on"},
        )
        first_completion = InductionModuleCompletion.objects.get(
            induction=self.induction,
            module=self.module,
            attempt_number=1,
        )
        self.assertEqual(first_completion.review_status, "pending")

        manager = User.objects.create_superuser(
            username="induction-review-manager",
            password="test-password",
        )
        manager_client = Client()
        manager_client.force_login(manager)
        review_url = reverse(
            "induction_module_review",
            args=[
                self.induction.pk,
                self.module.pk,
                first_completion.pk,
            ],
        )
        response = manager_client.post(
            review_url,
            {
                "decision": "redo_required",
                "review_note": "Please redo the spill response section.",
            },
        )
        self.assertEqual(response.status_code, 302)
        first_completion.refresh_from_db()
        self.assertEqual(first_completion.review_status, "redo_required")
        self.assertTrue(
            Notification.objects.filter(
                user=self.user,
                message__contains="spill response section",
            ).exists()
        )

        response = self.client.get(self.url)
        self.assertContains(response, "Please redo the spill response section.")
        self.client.post(self.url, self._assessment_data(passed=True))
        self.client.post(
            self.url,
            {"action": "complete_module", "acknowledgement": "on"},
        )
        second_completion = InductionModuleCompletion.objects.get(
            induction=self.induction,
            module=self.module,
            attempt_number=2,
        )
        self.assertEqual(second_completion.review_status, "pending")
        self.assertGreater(second_completion.completed_at, first_completion.completed_at)

        response = manager_client.post(
            reverse(
                "induction_module_review",
                args=[
                    self.induction.pk,
                    self.module.pk,
                    second_completion.pk,
                ],
            ),
            {"decision": "approved"},
        )
        self.assertEqual(response.status_code, 302)
        second_completion.refresh_from_db()
        self.assertEqual(second_completion.review_status, "approved")
        self.assertIn(self.module.pk, self.induction.completed_module_ids())
        self.assertEqual(
            list(
                InductionModuleReview.objects.filter(
                    completion=first_completion,
                ).values_list("decision", flat=True)
            ),
            ["redo_required"],
        )
        self.assertEqual(
            InductionModuleReview.objects.filter(
                completion=second_completion,
            ).count(),
            1,
        )
        dashboard_response = manager_client.get(
            reverse("induction_detail", args=[self.induction.pk]),
        )
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, "Review history")
        self.assertContains(dashboard_response, "Approve module completion")


class InductionExpiryReminderTests(TestCase):
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_portal_and_email_reminders_send_once_at_each_threshold(self):
        user = User.objects.create_user(
            username="expiry-employee",
            email="expiry@example.com",
        )
        employee = Employee.objects.create(
            user=user,
            full_name="Expiry Test Employee",
            phone="0400000000",
            email="employee@example.com",
        )
        programme = InductionProgramme.objects.create(name="Expiry programme")
        induction = EmployeeInduction.objects.create(
            employee=employee,
            programme=programme,
            status="completed",
        )
        today = timezone.localdate()
        induction.expires_on = today + timedelta(days=30)
        induction.save(update_fields=["expires_on"])
        output = StringIO()

        call_command("send_induction_expiry_reminders", stdout=output)
        call_command("send_induction_expiry_reminders", stdout=StringIO())
        self.assertEqual(Notification.objects.filter(user=user).count(), 1)
        self.assertEqual(len(mail.outbox), 1)

        induction.expires_on = today + timedelta(days=7)
        induction.save(update_fields=["expires_on"])
        call_command("send_induction_expiry_reminders", stdout=StringIO())
        self.assertEqual(Notification.objects.filter(user=user).count(), 2)
        self.assertEqual(len(mail.outbox), 2)

        induction.expires_on = today
        induction.save(update_fields=["expires_on"])
        call_command("send_induction_expiry_reminders", stdout=StringIO())
        self.assertEqual(Notification.objects.filter(user=user).count(), 3)
        self.assertEqual(len(mail.outbox), 3)

    def test_expired_induction_starts_a_renewal_before_employee_access(self):
        user = User.objects.create_user(username="renewal-employee")
        programme = InductionProgramme.objects.create(name="Renewal programme")
        employee = Employee.objects.create(
            user=user,
            full_name="Renewal Test Employee",
            phone="0400000000",
        )
        induction = employee.induction
        induction.programme = programme
        induction.status = "completed"
        induction.completed_at = timezone.now() - timedelta(days=400)
        induction.expires_on = timezone.localdate() - timedelta(days=1)
        induction.save()
        middleware = EmployeeInductionMiddleware(
            lambda request: HttpResponse("allowed")
        )
        request = RequestFactory().get("/employee/profile/")
        request.user = user

        response = middleware(request)

        induction.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(induction.status, "in_progress")
        self.assertIsNotNone(induction.renewal_started_at)
        self.assertEqual(induction.completed_module_ids(), set())


class InductionSetupViewTests(TestCase):
    def test_setup_page_renders_employee_and_all_configuration_fields(self):
        admin = User.objects.create_superuser(
            username="induction-admin",
            password="test-password",
        )
        employee = Employee.objects.create(
            full_name="Setup Test Employee",
            phone="0400000000",
            email="setup@example.com",
        )
        programme = InductionProgramme.objects.create(name="Starter programme")
        induction = EmployeeInduction.objects.create(
            employee=employee,
            programme=programme,
        )
        client = Client()
        client.force_login(admin)

        response = client.get(
            reverse("induction_setup", args=[induction.pk]),
        )

        self.assertEqual(response.status_code, 200, response.content.decode()[:500])
        self.assertContains(response, "Setup Test Employee")
        self.assertContains(response, "css/dashboard/induction-setup.css")
        for field_name in (
            "programme",
            "employment_type",
            "start_date",
            "expiry_months",
            "supervisor_name",
            "primary_work_location",
            "induction_duration_minutes",
            "notes",
        ):
            self.assertContains(response, f'name="{field_name}"')


class InductionDashboardTests(TestCase):
    def test_dashboard_can_publish_current_content_for_an_induction(self):
        manager = User.objects.create_superuser(
            username="induction-publisher",
            password="test-password",
        )
        programme = InductionProgramme.objects.create(
            name="Published training programme",
        )
        employee_user = User.objects.create_user(
            username="publish-test-employee",
            password="test-password",
        )
        employee = Employee.objects.create(
            user=employee_user,
            full_name="Publish Test Employee",
            phone="0400000000",
        )
        induction = employee.induction
        induction.programme = programme
        induction.save(update_fields=["programme"])
        client = Client()
        client.force_login(manager)

        response = client.get(
            reverse("induction_detail", args=[induction.pk]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Publish approved induction content")

        response = client.post(
            reverse("induction_publish_for_employee", args=[induction.pk]),
        )
        self.assertEqual(
            response.status_code,
            302,
            response.content.decode()[:500],
        )
        self.assertEqual(InductionModuleVersion.objects.count(), 10)
        response = client.get(
            reverse("induction_detail", args=[induction.pk]),
        )
        self.assertContains(response, "Welcome to YD Commercial Cleaning")
        self.assertNotContains(response, "Content not published")

        employee_client = Client()
        employee_client.force_login(employee_user)
        module = InductionModule.objects.get(code=MODULES[0]["code"])
        employee_response = employee_client.get(
            reverse("employee_induction_module", args=[module.pk]),
        )
        self.assertEqual(employee_response.status_code, 200)
        self.assertNotContains(
            employee_response,
            "does not contain the current assessment",
        )


class EmployeeInductionMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="induction-employee")
        self.employee = Employee.objects.create(
            user=self.user,
            full_name="Induction Employee",
            phone="0400000000",
        )
        self.middleware = EmployeeInductionMiddleware(
            lambda request: HttpResponse("allowed")
        )

    def get_response(self, path, user=None):
        request = self.factory.get(path)
        request.user = self.user if user is None else user
        return self.middleware(request)

    def test_employee_without_induction_is_redirected_to_induction(self):
        response = self.get_response("/employee/profile/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("employee_induction"))

    def test_employee_with_incomplete_induction_is_redirected(self):
        programme = InductionProgramme.objects.create(name="Test induction")
        EmployeeInduction.objects.create(
            employee=self.employee,
            programme=programme,
            status="assigned",
        )

        response = self.get_response("/employee/profile/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("employee_induction"))

    def test_completed_induction_allows_employee_request(self):
        programme = InductionProgramme.objects.create(name="Test induction")
        EmployeeInduction.objects.create(
            employee=self.employee,
            programme=programme,
            status="completed",
        )

        response = self.get_response("/employee/profile/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"allowed")

    def test_authentication_and_path_exclusions_are_preserved(self):
        self.assertEqual(
            self.get_response("/employee/induction/").status_code,
            200,
        )
        self.assertEqual(
            self.get_response("/employee/profile/", AnonymousUser()).status_code,
            200,
        )
        self.assertEqual(
            self.get_response("/dashboard/").status_code,
            200,
        )
