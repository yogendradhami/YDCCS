from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SecurityFinding",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("fingerprint", models.CharField(max_length=64, unique=True)),
                ("title", models.CharField(max_length=220)),
                ("description", models.TextField()),
                (
                    "severity",
                    models.CharField(
                        choices=[
                            ("critical", "Critical"),
                            ("high", "High"),
                            ("medium", "Medium"),
                            ("low", "Low"),
                            ("info", "Informational"),
                        ],
                        db_index=True,
                        default="medium",
                        max_length=12,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("open", "Open"),
                            ("investigating", "Investigating"),
                            ("resolved", "Resolved"),
                            ("ignored", "Ignored"),
                        ],
                        db_index=True,
                        default="open",
                        max_length=20,
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("request", "Request monitoring"),
                            ("audit", "Scheduled audit"),
                            ("django", "Django security check"),
                            ("dependency", "Dependency scan"),
                            ("uptime", "Availability monitoring"),
                        ],
                        default="audit",
                        max_length=20,
                    ),
                ),
                ("path", models.CharField(blank=True, max_length=500)),
                ("source_ip", models.GenericIPAddressField(blank=True, null=True)),
                ("first_seen", models.DateTimeField(default=django.utils.timezone.now)),
                ("last_seen", models.DateTimeField(default=django.utils.timezone.now)),
                ("occurrences", models.PositiveIntegerField(default=1)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                (
                    "resolved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="resolved_security_findings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-last_seen"],
                "indexes": [
                    models.Index(
                        fields=["status", "severity"],
                        name="secmon_status_sev_idx",
                    ),
                    models.Index(
                        fields=["source", "-last_seen"],
                        name="secmon_source_last_idx",
                    ),
                ],
            },
        ),
    ]
