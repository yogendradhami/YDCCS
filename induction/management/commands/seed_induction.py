from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from induction.models import (
    EmployeeInduction,
    InductionModule,
    InductionModuleVersion,
    InductionProgramme,
)
from induction.training_content import MODULES


LEGACY_STANDALONE_MODULE_CODES = {"chemical-safety", "equipment"}


class Command(BaseCommand):
    help = (
        "Install the versioned South Australian employee induction and "
        "assessment content without deleting training history."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        codes = [item["code"] for item in MODULES]
        if len(codes) != len(set(codes)):
            raise CommandError("The induction module content has duplicate codes.")
        if len(MODULES) != 10:
            raise CommandError("The published induction must contain ten modules.")

        for data in MODULES:
            version_candidate = InductionModuleVersion(
                version=1,
                content=data["content"],
                acknowledgement_text=data["acknowledgement_text"],
            )
            try:
                version_candidate.full_clean(
                    exclude=["module"],
                    validate_unique=False,
                )
            except ValidationError as error:
                raise CommandError(
                    f"Invalid content for {data['code']}: {error}"
                ) from error

        programme, _ = InductionProgramme.objects.update_or_create(
            name="YD Commercial Cleaning New Starter Induction",
            version=1,
            defaults={
                "description": (
                    "Role-ready onboarding and workplace training for YD "
                    "Commercial Cleaning employees."
                ),
                "active": True,
            },
        )

        created_count = 0
        updated_count = 0
        versioned_count = 0
        versioned_module_ids = []

        for data in MODULES:
            content = data["content"]
            module, created = InductionModule.objects.get_or_create(
                code=data["code"],
                defaults={
                    "title": data["title"],
                    "category": data["category"],
                    "role": "all",
                    "summary": data["summary"],
                    "content": self._plain_text(content),
                    "acknowledgement_text": data["acknowledgement_text"],
                    "version": 1,
                    "sort_order": data["sort_order"],
                    "mandatory": True,
                    "active": True,
                },
            )

            if created:
                version_record = InductionModuleVersion(
                    module=module,
                    version=module.version,
                    content=content,
                    acknowledgement_text=data["acknowledgement_text"],
                )
                version_record.full_clean()
                version_record.save()
                created_count += 1
                continue

            current_version = (
                module.training_versions.filter(version=module.version).first()
            )
            needs_new_version = (
                current_version is None
                or current_version.content != content
                or current_version.acknowledgement_text
                != data["acknowledgement_text"]
            )
            if needs_new_version:
                next_version = module.version + 1
                version_record = InductionModuleVersion(
                    module=module,
                    version=next_version,
                    content=content,
                    acknowledgement_text=data["acknowledgement_text"],
                )
                version_record.full_clean()
                version_record.save()
                module.version = next_version
                versioned_count += 1
                versioned_module_ids.append(module.pk)

            module.title = data["title"]
            module.category = data["category"]
            module.role = "all"
            module.summary = data["summary"]
            module.content = self._plain_text(content)
            module.acknowledgement_text = data["acknowledgement_text"]
            module.sort_order = data["sort_order"]
            module.mandatory = True
            module.active = True
            module.save()
            updated_count += 1

        # These legacy rows are kept for their historical completion references.
        # Their material is incorporated into the new ten-module curriculum.
        InductionModule.objects.filter(
            code__in=LEGACY_STANDALONE_MODULE_CODES,
        ).update(active=False)
        retraining_count = 0
        if versioned_module_ids:
            retraining_count = EmployeeInduction.objects.filter(
                status="completed",
                completions__module_id__in=versioned_module_ids,
            ).distinct().update(status="in_progress")

        self.stdout.write(self.style.SUCCESS("Induction content is ready."))
        self.stdout.write(f"Programme: {programme}")
        self.stdout.write(f"Modules created: {created_count}")
        self.stdout.write(f"Modules updated: {updated_count}")
        self.stdout.write(f"New training versions: {versioned_count}")
        self.stdout.write(
            f"Completed inductions requiring retraining: {retraining_count}"
        )
        self.stdout.write(
            "Legacy chemical/equipment rows retained but excluded from new assignments."
        )

    @staticmethod
    def _plain_text(content):
        paragraphs = [content["introduction"], content["why"]]
        paragraphs.extend(section["body"] for section in content["sections"])
        return "\n\n".join(paragraphs)
