from django.http import Http404
from django.test import RequestFactory, SimpleTestCase

from .middleware import ExceptionLoggingMiddleware, SlowRequestLoggingMiddleware


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
