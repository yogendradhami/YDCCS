import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def snapshot_existing_module_content(apps, schema_editor):
    InductionModule = apps.get_model("induction", "InductionModule")
    InductionModuleVersion = apps.get_model(
        "induction",
        "InductionModuleVersion",
    )
    database = schema_editor.connection.alias

    for module in InductionModule.objects.using(database).iterator():
        InductionModuleVersion.objects.using(database).get_or_create(
            module_id=module.pk,
            version=module.version,
            defaults={
                "content": {
                    "introduction": module.content,
                    "legacy_snapshot": True,
                    "objectives": [],
                    "sections": [],
                    "assessment": [],
                    "verification_tasks": [],
                },
                "acknowledgement_text": module.acknowledgement_text,
            },
        )


def ensure_training_tables(apps, schema_editor):
    models_to_ensure = (
        "InductionModuleVersion",
        "InductionAssessmentAttempt",
        "InductionSupervisorVerification",
    )
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        existing_tables = set(connection.introspection.table_names(cursor))

    for model_name in models_to_ensure:
        model = apps.get_model("induction", model_name)
        table_name = model._meta.db_table
        if table_name not in existing_tables:
            schema_editor.create_model(model)
            existing_tables.add(table_name)
            continue

        with connection.cursor() as cursor:
            existing_columns = {
                column.name
                for column in connection.introspection.get_table_description(
                    cursor,
                    table_name,
                )
            }
        expected_columns = {
            field.column for field in model._meta.local_concrete_fields
        }
        missing_columns = expected_columns - existing_columns
        if missing_columns:
            raise RuntimeError(
                f"Existing {table_name} is missing expected columns: "
                f"{', '.join(sorted(missing_columns))}. "
                "Repair the table before applying induction migrations."
            )


def ensure_module_version_constraint(apps, schema_editor):
    model = apps.get_model("induction", "InductionModuleVersion")
    constraint_name = "unique_induction_module_version"
    expected_columns = ["module_id", "version"]
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(
            cursor,
            model._meta.db_table,
        )

    existing = constraints.get(constraint_name)
    if existing is not None:
        if (
            existing.get("unique")
            and existing.get("columns") == expected_columns
        ):
            return
        raise RuntimeError(
            f"Constraint {constraint_name} exists on {model._meta.db_table} "
            "with an unexpected definition."
        )

    schema_editor.add_constraint(
        model,
        models.UniqueConstraint(
            fields=("module", "version"),
            name=constraint_name,
        ),
    )


class Migration(migrations.Migration):
    dependencies = [
        ("induction", "0004_alter_employeeonboardingprofile_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="InductionModuleVersion",
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
                        ("version", models.PositiveIntegerField()),
                        ("content", models.JSONField(default=dict)),
                        (
                            "acknowledgement_text",
                            models.CharField(max_length=300),
                        ),
                        (
                            "created_at",
                            models.DateTimeField(auto_now_add=True),
                        ),
                        (
                            "module",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="training_versions",
                                to="induction.inductionmodule",
                            ),
                        ),
                    ],
                    options={
                        "ordering": ["module_id", "version"],
                    },
                )
            ],
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="InductionAssessmentAttempt",
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
                        ("module_version", models.PositiveIntegerField()),
                        (
                            "submission_key",
                            models.UUIDField(
                                default=uuid.uuid4,
                                editable=False,
                                unique=True,
                            ),
                        ),
                        ("answers", models.JSONField(default=dict)),
                        ("score", models.PositiveSmallIntegerField()),
                        ("passed", models.BooleanField()),
                        (
                            "submitted_at",
                            models.DateTimeField(auto_now_add=True),
                        ),
                        (
                            "induction",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="assessment_attempts",
                                to="induction.employeeinduction",
                            ),
                        ),
                        (
                            "module",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="assessment_attempts",
                                to="induction.inductionmodule",
                            ),
                        ),
                    ],
                    options={
                        "ordering": ["-submitted_at", "-pk"],
                        "indexes": [
                            models.Index(
                                fields=[
                                    "induction",
                                    "module",
                                    "module_version",
                                    "-submitted_at",
                                ],
                                name="ind_assessment_lookup_idx",
                            )
                        ],
                    },
                )
            ],
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="InductionSupervisorVerification",
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
                        ("module_version", models.PositiveIntegerField()),
                        (
                            "practical_task",
                            models.CharField(max_length=300),
                        ),
                        (
                            "result",
                            models.CharField(
                                choices=[
                                    ("competent", "Competent"),
                                    (
                                        "further_training",
                                        "Further training required",
                                    ),
                                ],
                                max_length=24,
                            ),
                        ),
                        ("comments", models.TextField(blank=True)),
                        (
                            "verified_at",
                            models.DateTimeField(default=timezone.now),
                        ),
                        (
                            "induction",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="supervisor_verifications",
                                to="induction.employeeinduction",
                            ),
                        ),
                        (
                            "module",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="supervisor_verifications",
                                to="induction.inductionmodule",
                            ),
                        ),
                        (
                            "supervisor",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="induction_verifications",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                    ],
                    options={
                        "ordering": ["-verified_at", "-pk"],
                    },
                )
            ],
        ),
        migrations.RunPython(
            ensure_training_tables,
            migrations.RunPython.noop,
        ),
        migrations.RunPython(
            snapshot_existing_module_content,
            migrations.RunPython.noop,
        ),
        migrations.RemoveConstraint(
            model_name="inductionmodulecompletion",
            name="unique_induction_module_completion",
        ),
        migrations.AddConstraint(
            model_name="inductionmodulecompletion",
            constraint=models.UniqueConstraint(
                fields=("induction", "module", "module_version"),
                name="unique_induction_module_completion",
            ),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    ensure_module_version_constraint,
                    migrations.RunPython.noop,
                )
            ],
            state_operations=[
                migrations.AddConstraint(
                    model_name="inductionmoduleversion",
                    constraint=models.UniqueConstraint(
                        fields=("module", "version"),
                        name="unique_induction_module_version",
                    ),
                )
            ],
        ),
    ]
