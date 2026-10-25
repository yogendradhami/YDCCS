import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import URLResolver, get_resolver, resolve

from .middleware import (
    ExceptionLoggingMiddleware,
    RoleAccessMiddleware,
    SlowRequestLoggingMiddleware,
    dashboard_required_permissions,
)


class DashboardPermissionMappingTests(SimpleTestCase):
    def test_customer_routes_require_customer_permissions(self):
        self.assertEqual(
            dashboard_required_permissions("/dashboard/customers/", "GET"),
            ("customers.view_customer",),
        )
        self.assertEqual(
            dashboard_required_permissions(
                "/dashboard/customer/12/followup/",
                "POST",
            ),
            ("customers.change_customer",),
        )

    def test_company_document_bulk_import_routes_use_their_own_models(self):
        self.assertEqual(
            dashboard_required_permissions(
                "/dashboard/company-documents/bulk-import/",
                "GET",
            ),
            ("company_documents.view_bulkimportbatch",),
        )
        self.assertEqual(
            dashboard_required_permissions(
                "/dashboard/company-documents/bulk-import/12/delete/",
                "POST",
            ),
            ("company_documents.delete_bulkimportbatch",),
        )
        self.assertEqual(
            dashboard_required_permissions(
                "/dashboard/company-documents/bulk-import/item/4/edit/",
                "GET",
            ),
            ("company_documents.change_bulkimportitem",),
        )

    def test_support_routes_use_ticket_or_live_chat_permissions(self):
        self.assertEqual(
            dashboard_required_permissions(
                "/dashboard/support/tickets/4/update/",
                "POST",
            ),
            ("support.change_supportticket",),
        )
        self.assertEqual(
            dashboard_required_permissions(
                "/dashboard/support/live-chat/4/takeover/",
                "POST",
            ),
            ("support.change_livechatconversation",),
        )

    def test_unknown_dashboard_route_is_denied_by_default(self):
        self.assertEqual(
            dashboard_required_permissions("/dashboard/", "GET"),
            (
                "dashboard.view_activitylog",
                "bookings.view_booking",
                "dashboard.view_cleaningsupply",
                "customers.view_customer",
                "employees.view_employee",
                "dashboard.view_equipment",
                "gallery.view_galleryitem",
                "quotes.view_quoterequest",
                "reviews.view_review",
                "dashboard.view_vehicle",
            ),
        )
        self.assertIsNone(
            dashboard_required_permissions("/dashboard/unmapped/", "GET")
        )

    def test_security_monitor_and_user_role_routes_use_dedicated_permissions(self):
        self.assertEqual(
            dashboard_required_permissions("/dashboard/security/", "GET"),
            (
                "security_monitor.view_securityfinding",
                "security_monitor.view_securityalertdelivery",
            ),
        )
        self.assertEqual(
            dashboard_required_permissions(
                "/dashboard/security/findings/12/update/", "POST"
            ),
            ("security_monitor.change_securityfinding",),
        )
        self.assertEqual(
            dashboard_required_permissions(
                "/dashboard/users/positions/4/edit/", "POST"
            ),
            ("security.manage_security_roles",),
        )

    def test_aggregated_reports_require_every_model_permission(self):
        self.assertEqual(
            dashboard_required_permissions("/dashboard/financials/", "GET"),
            (
                "invoices.view_invoice",
                "expenses.view_expense",
                "payroll.view_payrollrecord",
            ),
        )
        self.assertEqual(
            dashboard_required_permissions(
                "/dashboard/bookings/12/create-invoice/", "POST"
            ),
            ("bookings.view_booking", "invoices.add_invoice"),
        )
        self.assertEqual(
            dashboard_required_permissions(
                "/dashboard/company-documents/bulk-import/12/approve/", "POST"
            ),
            (
                "company_documents.view_bulkimportbatch",
                "company_documents.change_bulkimportitem",
            ),
        )

    def test_permission_action_uses_http_method(self):
        self.assertEqual(
            dashboard_required_permissions("/dashboard/invoices/12/mark-unpaid/", "GET"),
            ("invoices.change_invoice",),
        )
        self.assertEqual(
            dashboard_required_permissions("/dashboard/invoices/12/mark-unpaid/", "POST"),
            ("invoices.change_invoice",),
        )
        self.assertEqual(
            dashboard_required_permissions("/dashboard/invoices/12/", "DELETE"),
            None,
        )
        self.assertIsNone(
            dashboard_required_permissions("/dashboard/customers/", "POST")
        )
        for unsupported_method in ("PUT", "PATCH", "OPTIONS"):
            self.assertIsNone(
                dashboard_required_permissions(
                    "/dashboard/invoices/12/mark-unpaid/", unsupported_method
                )
            )
        self.assertEqual(
            dashboard_required_permissions("/dashboard/ai-quote-estimator/", "POST"),
            ("invoices.view_invoice",),
        )

    def test_every_dashboard_url_name_is_explicitly_mapped(self):
        def walk(patterns, prefix=""):
            for pattern in patterns:
                route = prefix + str(pattern.pattern)
                if isinstance(pattern, URLResolver):
                    yield from walk(pattern.url_patterns, route)
                elif route.startswith("dashboard/") and pattern.name not in {
                    "dashboard_login",
                    "dashboard_logout",
                }:
                    yield route, pattern.name

        for route, url_name in walk(get_resolver().url_patterns):
            concrete_path = re.sub(r"<int:[^>]+>", "1", route)
            concrete_path = re.sub(r"<str:[^>]+>", "sample", concrete_path)
            path = "/" + concrete_path
            self.assertIsNotNone(resolve(path))
            with self.subTest(route=route, url_name=url_name):
                self.assertTrue(
                    any(
                        dashboard_required_permissions(path, method, url_name)
                        is not None
                        for method in ("GET", "POST")
                    )
                )


class DashboardAuthorizationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="dashboard-viewer",
            password="unused-test-password",
            is_staff=True,
        )

    def grant(self, *permissions):
        permission_objects = []
        for permission in permissions:
            app_label, codename = permission.split(".", 1)
            permission_objects.append(
                Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename,
                )
            )
        self.user.user_permissions.add(*permission_objects)
        for permission_cache in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            if hasattr(self.user, permission_cache):
                delattr(self.user, permission_cache)

    def request(self, path, method="GET"):
        factory = RequestFactory()
        request = getattr(factory, method.lower())(path)
        request.user = self.user
        return request

    def middleware(self, path, method="GET"):
        middleware = RoleAccessMiddleware(lambda request: HttpResponse("allowed"))
        return middleware(self.request(path, method))

    def test_dashboard_home_access_does_not_grant_security_access(self):
        home_permissions = dashboard_required_permissions("/dashboard/", "GET")
        self.grant("security.access_dashboard", *home_permissions)

        self.assertEqual(self.middleware("/dashboard/").status_code, 200)
        self.assertFalse(self.user.has_perm("security.view_security_center"))
        self.assertFalse(self.user.has_perm("security.manage_users"))
        with self.assertRaises(PermissionDenied):
            self.middleware("/dashboard/security/audit/")
        with self.assertRaises(PermissionDenied):
            self.middleware("/dashboard/users/")

    def test_multi_model_report_denies_role_missing_one_read_permission(self):
        self.grant(
            "security.access_dashboard",
            "invoices.view_invoice",
            "expenses.view_expense",
        )
        with self.assertRaises(PermissionDenied):
            self.middleware("/dashboard/financials/")

        self.grant("payroll.view_payrollrecord")
        self.assertEqual(self.middleware("/dashboard/financials/").status_code, 200)

    def test_unknown_nested_dashboard_route_fails_closed(self):
        self.grant("security.access_dashboard", "customers.view_customer")
        with self.assertRaises(PermissionDenied):
            self.middleware("/dashboard/customers/not-a-real-route/")

    def test_read_only_security_role_cannot_post_audit_or_update_findings(self):
        from security.views import security_center
        from security_monitor.views import run_security_audit, update_finding

        self.grant(
            "security.access_dashboard",
            "security.view_security_center",
            "security_monitor.view_securityfinding",
            "security_monitor.view_securityalertdelivery",
        )
        self.assertEqual(self.middleware("/dashboard/security/").status_code, 200)
        with self.assertRaises(PermissionDenied):
            self.middleware("/dashboard/security/audit/", "POST")
        with self.assertRaises(PermissionDenied):
            self.middleware("/dashboard/security/findings/1/update/", "POST")

        response = security_center(self.request("/dashboard/security/audit/", "POST"))
        self.assertEqual(response.status_code, 403)
        response = run_security_audit(
            self.request("/dashboard/security/audit/run/", "POST")
        )
        self.assertEqual(response.status_code, 403)
        response = update_finding(
            self.request("/dashboard/security/findings/1/update/", "POST"), 1
        )
        self.assertEqual(response.status_code, 403)

    def test_security_finding_editor_can_post_with_model_change_permission(self):
        from django.http import Http404
        from security_monitor.views import update_finding

        self.grant("security.access_dashboard", "security_monitor.change_securityfinding")
        self.assertEqual(
            self.middleware("/dashboard/security/findings/1/update/", "POST").status_code,
            200,
        )
        with self.assertRaises(Http404):
            update_finding(
                self.request("/dashboard/security/findings/1/update/", "POST"), 1
            )

    def test_post_only_mutations_reject_get_requests(self):
        from dashboard.views import (
            email_business_report,
            email_employee_performance_report,
            receive_purchase_order,
            send_customer_followup,
            send_quote_followup_email,
        )
        from payroll.views import mark_payroll_paid

        for view, args in (
            (receive_purchase_order, (1,)),
            (mark_payroll_paid, (1,)),
            (send_customer_followup, (1,)),
            (send_quote_followup_email, (1,)),
            (email_business_report, ()),
            (email_employee_performance_report, ()),
        ):
            response = view(self.request("/dashboard/action/", "GET"), *args)
            self.assertEqual(response.status_code, 405)

    def test_manager_role_gets_security_monitor_read_access_only(self):
        from django.contrib.auth.models import Group

        manager = Group.objects.get(name="Manager")
        manager_permissions = set(
            manager.permissions.filter(
                content_type__app_label="security_monitor"
            ).values_list("codename", flat=True)
        )
        self.assertIn("view_securityfinding", manager_permissions)
        self.assertIn("view_securityalertdelivery", manager_permissions)
        self.assertNotIn("change_securityfinding", manager_permissions)

        administrator = Group.objects.get(name="Administrator")
        self.assertTrue(
            administrator.permissions.filter(
                content_type__app_label="security_monitor",
                codename="change_securityfinding",
            ).exists()
        )


class ExceptionLoggingMiddlewareTests(SimpleTestCase):
    def test_unhandled_exception_logs_traceback_and_path(self):
        middleware = ExceptionLoggingMiddleware(lambda request: None)
        request = RequestFactory().post("/example/upload/")
        try:
            raise RuntimeError("upload failed")
        except RuntimeError as exception:
            with self.assertLogs("core.middleware", level="ERROR") as captured:
                self.assertIsNone(middleware.process_exception(request, exception))

        self.assertIn("POST /example/upload/", captured.output[0])
        self.assertIn("Traceback", captured.output[0])
        self.assertIn("upload failed", captured.output[0])

    def test_expected_not_found_is_not_logged_as_server_error(self):
        middleware = ExceptionLoggingMiddleware(lambda request: None)
        request = RequestFactory().get("/missing/")
        with self.assertNoLogs("core.middleware", level="ERROR"):
            self.assertIsNone(middleware.process_exception(request, Http404()))


class SlowRequestLoggingMiddlewareTests(SimpleTestCase):
    def test_slow_request_logs_elapsed_time_and_database_stats(self):
        middleware = SlowRequestLoggingMiddleware(lambda request: None)
        middleware.SLOW_REQUEST_SECONDS = 0

        with self.assertLogs("core.middleware", level="WARNING") as captured:
            middleware(RequestFactory().get("/slow/"))

        self.assertIn("path=/slow/", captured.output[0])
        self.assertIn("total_ms=", captured.output[0])
        self.assertIn("db_queries=0", captured.output[0])
