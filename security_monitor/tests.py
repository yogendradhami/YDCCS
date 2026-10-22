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
