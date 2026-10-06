from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse

from employees.models import Employee

from .middleware import EmployeeInductionMiddleware
from .models import EmployeeInduction, InductionProgramme


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
