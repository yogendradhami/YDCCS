from django.core.management.base import BaseCommand

from induction.models import (
    InductionProgramme,
    InductionModule,
)


class Command(BaseCommand):
    help = "Create the default YD Commercial Cleaning induction programme and modules."

    def handle(self, *args, **options):

        # ---------------------------------------------------------
        # INDUCTION PROGRAMME
        # ---------------------------------------------------------

        programme, created = (
            InductionProgramme.objects.update_or_create(
                name="YD Commercial Cleaning New Starter Induction",
                version=1,
                defaults={
                    "description": (
                        "Mandatory onboarding and workplace induction "
                        "programme for YD Commercial Cleaning employees."
                    ),
                    "active": True,
                },
            )
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created induction programme: {programme}"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Induction programme already exists: {programme}"
                )
            )

        # ---------------------------------------------------------
        # INDUCTION MODULES
        #
        # IMPORTANT:
        # InductionModule currently does NOT have a programme FK.
        # Therefore modules are created independently and are
        # selected by EmployeeInduction.required_modules().
        # ---------------------------------------------------------

        modules = [
            {
                "code": "welcome-company",
                "title": "Welcome to YD Commercial Cleaning",
                "category": "welcome",
                "role": "all",
                "summary": (
                    "Company introduction and workplace expectations."
                ),
                "content": """
Welcome to YD Commercial Cleaning.

This module introduces our company, service standards,
workplace expectations and commitment to providing safe,
professional and reliable cleaning services.

Employees are expected to:

- Maintain professional behaviour.
- Treat customers and colleagues respectfully.
- Follow company procedures.
- Protect customer property and information.
- Report hazards and incidents.
- Complete required training.
- Maintain appropriate uniform and presentation.
""".strip(),
                "acknowledgement_text": (
                    "I confirm that I have read and understood "
                    "the company induction information."
                ),
                "version": 1,
                "sort_order": 10,
                "mandatory": True,
                "active": True,
            },
            {
                "code": "whs-safety",
                "title": "Work Health and Safety",
                "category": "whs",
                "role": "all",
                "summary": (
                    "Workplace health and safety responsibilities."
                ),
                "content": """
Work Health and Safety is a core responsibility.

Employees must:

- Follow WHS procedures.
- Use equipment correctly.
- Wear required PPE.
- Report hazards.
- Report injuries and incidents.
- Never deliberately bypass safety controls.
- Follow supervisor instructions.
- Keep work areas safe and organised.

If you identify an immediate danger, stop work where
appropriate and notify your supervisor.
""".strip(),
                "acknowledgement_text": (
                    "I understand my WHS responsibilities "
                    "and agree to follow workplace safety procedures."
                ),
                "version": 1,
                "sort_order": 20,
                "mandatory": True,
                "active": True,
            },
            {
                "code": "ppe",
                "title": "Personal Protective Equipment",
                "category": "whs",
                "role": "all",
                "summary": (
                    "Correct use and care of PPE."
                ),
                "content": """
Employees must use the PPE required for the task.

Depending on the work, PPE may include:

- Gloves.
- Safety footwear.
- Eye protection.
- Masks or respiratory protection where required.
- Protective clothing.

PPE must be inspected before use and replaced when damaged
or unsuitable.
""".strip(),
                "acknowledgement_text": (
                    "I understand when and how required PPE must be used."
                ),
                "version": 1,
                "sort_order": 30,
                "mandatory": True,
                "active": True,
            },
            {
                "code": "chemical-safety",
                "title": "Chemical Safety",
                "category": "whs",
                "role": "all",
                "summary": (
                    "Safe handling and storage of cleaning chemicals."
                ),
                "content": """
Cleaning chemicals must be handled safely.

Employees must:

- Read product labels.
- Follow product instructions.
- Use required PPE.
- Never mix incompatible chemicals.
- Store chemicals correctly.
- Keep chemicals away from food.
- Report spills immediately.
- Follow applicable Safety Data Sheet requirements.

Never mix bleach with acids, ammonia or other incompatible
chemicals.
""".strip(),
                "acknowledgement_text": (
                    "I understand the basic requirements for "
                    "safe handling and storage of cleaning chemicals."
                ),
                "version": 1,
                "sort_order": 40,
                "mandatory": True,
                "active": True,
            },
            {
                "code": "manual-handling",
                "title": "Manual Handling",
                "category": "whs",
                "role": "all",
                "summary": (
                    "Safe lifting, carrying and movement of equipment."
                ),
                "content": """
Employees must use safe manual-handling practices.

Before moving an item:

- Assess the load.
- Check the path.
- Use suitable equipment where available.
- Ask for assistance when required.
- Avoid unnecessary twisting.
- Use appropriate lifting techniques.

Report manual-handling hazards to your supervisor.
""".strip(),
                "acknowledgement_text": (
                    "I understand the importance of safe manual handling."
                ),
                "version": 1,
                "sort_order": 50,
                "mandatory": True,
                "active": True,
            },
            {
                "code": "equipment",
                "title": "Cleaning Equipment",
                "category": "operations",
                "role": "all",
                "summary": (
                    "Safe and professional use of cleaning equipment."
                ),
                "content": """
Only use equipment that you have been trained and authorised
to operate.

Before use:

- Inspect equipment.
- Check cables and plugs where applicable.
- Confirm the equipment is suitable for the task.
- Follow manufacturer instructions.

Report damaged equipment immediately and do not continue
using unsafe equipment.
""".strip(),
                "acknowledgement_text": (
                    "I understand that equipment must only be used "
                    "when I am trained and authorised to do so."
                ),
                "version": 1,
                "sort_order": 60,
                "mandatory": True,
                "active": True,
            },
            {
                "code": "incident-reporting",
                "title": "Incident and Hazard Reporting",
                "category": "whs",
                "role": "all",
                "summary": (
                    "How to report incidents, injuries and hazards."
                ),
                "content": """
All hazards, incidents, injuries, property damage and
near misses must be reported promptly.

Examples include:

- Employee injury.
- Customer injury.
- Chemical spill.
- Damaged customer property.
- Damaged equipment.
- Unsafe work conditions.
- Security concerns.

When in doubt, report the issue to your supervisor.
""".strip(),
                "acknowledgement_text": (
                    "I understand that workplace incidents and hazards "
                    "must be reported promptly."
                ),
                "version": 1,
                "sort_order": 70,
                "mandatory": True,
                "active": True,
            },
            {
                "code": "customer-conduct",
                "title": "Customer Service and Professional Conduct",
                "category": "conduct",
                "role": "all",
                "summary": (
                    "Professional behaviour at customer locations."
                ),
                "content": """
Employees represent YD Commercial Cleaning when working
at customer premises.

Employees must:

- Be respectful.
- Maintain professional communication.
- Protect customer property.
- Avoid inappropriate conversations.
- Never use customer property without permission.
- Maintain confidentiality.
- Follow site-specific instructions.
- Report customer concerns to management.
""".strip(),
                "acknowledgement_text": (
                    "I understand the professional conduct expected "
                    "when working at customer premises."
                ),
                "version": 1,
                "sort_order": 80,
                "mandatory": True,
                "active": True,
            },
            {
                "code": "privacy-confidentiality",
                "title": "Privacy and Confidentiality",
                "category": "conduct",
                "role": "all",
                "summary": (
                    "Protection of customer and company information."
                ),
                "content": """
Employees may encounter confidential customer and company
information.

Employees must not:

- Share customer information without authorisation.
- Photograph private information without permission.
- Discuss customer information with unauthorised people.
- Access systems without authorisation.
- Share passwords.

Information must only be used for legitimate work purposes.
""".strip(),
                "acknowledgement_text": (
                    "I understand my responsibility to protect "
                    "confidential company and customer information."
                ),
                "version": 1,
                "sort_order": 90,
                "mandatory": True,
                "active": True,
            },
            {
                "code": "emergency-procedures",
                "title": "Emergency Procedures",
                "category": "whs",
                "role": "all",
                "summary": (
                    "Emergency response and evacuation expectations."
                ),
                "content": """
Employees must understand the emergency procedures
applicable to each workplace.

In an emergency:

- Stay calm.
- Follow site emergency procedures.
- Follow supervisor or emergency warden instructions.
- Use designated evacuation routes.
- Do not re-enter an unsafe area.
- Contact emergency services where appropriate.

Employees must familiarise themselves with emergency exits
at customer sites.
""".strip(),
                "acknowledgement_text": (
                    "I understand that emergency procedures must "
                    "be followed at each workplace."
                ),
                "version": 1,
                "sort_order": 100,
                "mandatory": True,
                "active": True,
            },
            {
                "code": "time-attendance",
                "title": "Attendance and Timekeeping",
                "category": "operations",
                "role": "all",
                "summary": (
                    "Attendance, punctuality and timekeeping."
                ),
                "content": """
Employees are expected to attend scheduled shifts on time.

Employees must:

- Follow rostered working hours.
- Clock in and out correctly where required.
- Notify management if they cannot attend.
- Follow leave procedures.
- Maintain accurate timesheets.

Attendance issues may be addressed through company procedures.
""".strip(),
                "acknowledgement_text": (
                    "I understand the company's expectations "
                    "regarding attendance and timekeeping."
                ),
                "version": 1,
                "sort_order": 110,
                "mandatory": True,
                "active": True,
            },
            {
                "code": "uniform-appearance",
                "title": "Uniform and Professional Appearance",
                "category": "conduct",
                "role": "all",
                "summary": (
                    "Uniform, presentation and personal hygiene."
                ),
                "content": """
Employees must maintain a clean and professional appearance.

Where a company uniform is provided:

- Wear the required uniform.
- Keep the uniform clean.
- Wear suitable footwear.
- Maintain appropriate personal hygiene.
- Display identification where required.
""".strip(),
                "acknowledgement_text": (
                    "I understand the company's expectations "
                    "for uniform and professional presentation."
                ),
                "version": 1,
                "sort_order": 120,
                "mandatory": True,
                "active": True,
            },
        ]

        created_count = 0
        updated_count = 0

        for data in modules:

            module, created = (
                InductionModule.objects.update_or_create(
                    code=data["code"],
                    defaults=data,
                )
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Induction setup complete."
            )
        )

        self.stdout.write(
            f"Programme: {programme}"
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Modules created: {created_count}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Modules updated: {updated_count}"
            )
        )