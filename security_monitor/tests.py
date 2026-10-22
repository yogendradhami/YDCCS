from django.test import TestCase

from security_monitor.models import SecurityFinding
from security_monitor.scanners import record_finding
from security_monitor.models import (
    SecurityAlertDelivery,
    SecurityFinding,
)


from django.core import mail
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from datetime import timedelta
from unittest.mock import patch

from security_monitor.notifications import (
    send_security_alert,
    send_security_report,
)



class SecurityFindingTests(TestCase):
    def test_new_finding_is_created(self):
        finding, created = record_finding(
            title="Test security finding",
            description="Test detection.",
            severity=SecurityFinding.Severity.MEDIUM,
            source=SecurityFinding.Source.AUDIT,
            path="/test-security/",
        )

        self.assertTrue(created)
        self.assertEqual(finding.occurrences, 1)

    def test_repeated_finding_updates_existing_record(self):
        kwargs = {
            "title": "Repeated test finding",
            "description": "Test detection.",
            "severity": SecurityFinding.Severity.MEDIUM,
            "source": SecurityFinding.Source.AUDIT,
            "path": "/repeated-test/",
        }

        first, created_first = record_finding(**kwargs)
        second, created_second = record_finding(
            **{**kwargs, "description": "Detected again."}
        )

        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.occurrences, 2)
        self.assertEqual(second.description, "Detected again.")


    def test_critical_finding_queues_an_alert(self):
        finding, created = record_finding(
            title="Critical security test",
            description="Testing alert queue creation.",
            severity=SecurityFinding.Severity.CRITICAL,
            source=SecurityFinding.Source.AUDIT,
            path="/critical-test/",
        )

        self.assertTrue(created)
        self.assertTrue(
            SecurityAlertDelivery.objects.filter(
                finding=finding,
                status=SecurityAlertDelivery.Status.PENDING,
            ).exists()
        )


    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SECURITY_ALERT_EMAIL="security-test@example.com",
        DEFAULT_FROM_EMAIL="noreply@example.com",
    )
    def test_alert_processor_sends_and_marks_delivery_sent(self):
        finding, _ = record_finding(
            title="Queued email test",
            description="Testing alert delivery.",
            severity=SecurityFinding.Severity.CRITICAL,
            source=SecurityFinding.Source.AUDIT,
            path="/queued-email-test/",
        )

        delivery = SecurityAlertDelivery.objects.get(finding=finding)

        call_command("process_security_alerts", verbosity=0)

        delivery.refresh_from_db()

        self.assertEqual(
            delivery.status,
            SecurityAlertDelivery.Status.SENT,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].to,
            ["security-test@example.com"],
        )


    
    def test_high_finding_queues_an_alert(self):
        finding, created = record_finding(
            title="High security test",
            description="Testing high severity alert creation.",
            severity=SecurityFinding.Severity.HIGH,
            source=SecurityFinding.Source.AUDIT,
            path="/high-test/",
        )

        self.assertTrue(created)
        self.assertTrue(
            SecurityAlertDelivery.objects.filter(
                finding=finding,
                status=SecurityAlertDelivery.Status.PENDING,
            ).exists()
        )

    def test_resolved_finding_reopens_when_detected_again(self):
        finding, _ = record_finding(
            title="Recurring finding test",
            description="First detection.",
            severity=SecurityFinding.Severity.HIGH,
            source=SecurityFinding.Source.AUDIT,
            path="/recurring-test/",
        )

        finding.status = SecurityFinding.Status.RESOLVED
        finding.resolved_at = timezone.now()
        finding.save(update_fields=["status", "resolved_at"])

        updated, created = record_finding(
            title="Recurring finding test",
            description="Detected again.",
            severity=SecurityFinding.Severity.HIGH,
            source=SecurityFinding.Source.AUDIT,
            path="/recurring-test/",
        )

        self.assertFalse(created)
        self.assertEqual(updated.pk, finding.pk)
        self.assertEqual(updated.status, SecurityFinding.Status.OPEN)
        self.assertIsNone(updated.resolved_at)
        self.assertEqual(updated.occurrences, 2)



    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SECURITY_ALERT_EMAIL="security-test@example.com",
        DEFAULT_FROM_EMAIL="noreply@example.com",
        SITE_URL="https://www.ydcleaning.com.au",
        SECURITY_DASHBOARD_URL=(
            "https://www.ydcleaning.com.au/dashboard/security/"
        ),
    )
    def test_security_alert_renders_branded_html_and_dashboard_link(self):
        finding, _ = record_finding(
            title="Missing security header",
            description="The website is missing a recommended header.",
            severity=SecurityFinding.Severity.HIGH,
            source=SecurityFinding.Source.AUDIT,
            path="/security-test/",
        )

        result = send_security_alert(finding)

        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)

        message = mail.outbox[0]
        self.assertIn("[HIGH]", message.subject)
        self.assertEqual(message.to, ["security-test@example.com"])
        self.assertTrue(message.body)
        self.assertEqual(len(message.alternatives), 1)

        html_body, content_type = message.alternatives[0]

        self.assertEqual(content_type, "text/html")
        self.assertIn("Security incident alert", html_body)
        self.assertIn("Missing security header", html_body)
        self.assertIn("The website is missing a recommended header.", html_body)
        self.assertIn(
            "https://www.ydcleaning.com.au/dashboard/security/",
            html_body,
        )

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SECURITY_ALERT_EMAIL="security-test@example.com",
        DEFAULT_FROM_EMAIL="noreply@example.com",
        SITE_URL="https://www.ydcleaning.com.au",
        SECURITY_DASHBOARD_URL=(
            "https://www.ydcleaning.com.au/dashboard/security/"
        ),
    )
    def test_security_report_renders_correct_severity_counts(self):
        record_finding(
            title="Critical audit test",
            description="Critical test finding.",
            severity=SecurityFinding.Severity.CRITICAL,
            source=SecurityFinding.Source.AUDIT,
            path="/critical-report-test/",
        )

        record_finding(
            title="High audit test",
            description="High test finding.",
            severity=SecurityFinding.Severity.HIGH,
            source=SecurityFinding.Source.AUDIT,
            path="/high-report-test/",
        )

        result = send_security_report()

        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)

        message = mail.outbox[0]
        self.assertIn("Scheduled Security Audit Report", message.subject)
        self.assertEqual(len(message.alternatives), 1)

        html_body, content_type = message.alternatives[0]

        self.assertEqual(content_type, "text/html")
        self.assertIn("Security audit report", html_body)
        self.assertIn("Critical audit test", html_body)
        self.assertIn("High audit test", html_body)
        self.assertIn(
            "https://www.ydcleaning.com.au/dashboard/security/",
            html_body,
        )

        self.assertEqual(
            SecurityFinding.objects.filter(
                severity=SecurityFinding.Severity.CRITICAL,
                status__in=[
                    SecurityFinding.Status.OPEN,
                    SecurityFinding.Status.INVESTIGATING,
                ],
            ).count(),
            1,
        )
        self.assertEqual(
            SecurityFinding.objects.filter(
                severity=SecurityFinding.Severity.HIGH,
                status__in=[
                    SecurityFinding.Status.OPEN,
                    SecurityFinding.Status.INVESTIGATING,
                ],
            ).count(),
            1,
        )

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SECURITY_ALERT_EMAIL="security-test@example.com",
        DEFAULT_FROM_EMAIL="noreply@example.com",
    )
    def test_failed_delivery_is_scheduled_for_retry(self):
        finding, _ = record_finding(
            title="Retry test finding",
            description="Testing email retry.",
            severity=SecurityFinding.Severity.HIGH,
            source=SecurityFinding.Source.AUDIT,
            path="/retry-test/",
        )

        delivery = SecurityAlertDelivery.objects.get(finding=finding)
        original_attempts = delivery.attempts

        with patch(
            "security_monitor.management.commands."
            "process_security_alerts.send_security_alert",
            return_value=False,
        ):
            call_command("process_security_alerts", verbosity=0)

        delivery.refresh_from_db()

        self.assertEqual(
            delivery.status,
            SecurityAlertDelivery.Status.PENDING,
        )
        self.assertEqual(delivery.attempts, original_attempts + 1)
        self.assertTrue(delivery.last_error)
        self.assertGreater(delivery.next_attempt_at, timezone.now())
        self.assertIsNone(delivery.sent_at)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SECURITY_ALERT_EMAIL="security-test@example.com",
        DEFAULT_FROM_EMAIL="noreply@example.com",
    )
    def test_delivery_stops_retrying_at_five_attempts(self):
        finding, _ = record_finding(
            title="Retry limit test",
            description="Testing retry limit.",
            severity=SecurityFinding.Severity.CRITICAL,
            source=SecurityFinding.Source.AUDIT,
            path="/retry-limit-test/",
        )

        delivery = SecurityAlertDelivery.objects.get(finding=finding)
        delivery.attempts = 4
        delivery.next_attempt_at = (
            timezone.now() - timedelta(minutes=1)
        )
        delivery.save(update_fields=["attempts", "next_attempt_at"])

        with patch(
            "security_monitor.management.commands."
            "process_security_alerts.send_security_alert",
            return_value=False,
        ):
            call_command("process_security_alerts", verbosity=0)

        delivery.refresh_from_db()

        self.assertEqual(delivery.attempts, 5)
        self.assertEqual(
            delivery.status,
            SecurityAlertDelivery.Status.FAILED,
        )
        self.assertTrue(delivery.last_error)
        self.assertIsNone(delivery.sent_at)
