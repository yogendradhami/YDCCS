from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from contracts.models import CleaningContract
from customers.models import Customer
from dashboard.models import ActivityLog, CareerApplication, CleaningSupply, EmailLog, Equipment, MaintenanceHistory, PurchaseOrder, Vehicle
from support.models import SupportTicket


class SystemWorkspacePageTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            "workspace-admin",
            "workspace-admin@example.com",
            "test-password",
        )
        self.client.force_login(self.admin)

    def test_requested_dashboard_pages_render_for_an_authorized_user(self):
        page_names = (
            "security_user_list",
            "security_center",
            "reminder_centre",
            "email_center",
            "email_log_list",
            "support_dashboard",
            "activity_log_list",
            "company_settings",
        )

        for page_name in page_names:
            with self.subTest(page=page_name):
                response = self.client.get(reverse(page_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "workspace.css")

    def test_user_and_position_workflows_render(self):
        group = Group.objects.create(name="Workspace Test Position")
        page_urls = (
            reverse("security_user_create"),
            reverse("security_user_edit", args=[self.admin.pk]),
            reverse("security_position_list"),
            reverse("security_position_create"),
            reverse("security_position_edit", args=[group.pk]),
        )

        for page_url in page_urls:
            with self.subTest(page=page_url):
                response = self.client.get(page_url)
                self.assertEqual(response.status_code, 200)

    def test_role_editor_groups_permissions_and_preserves_selection(self):
        permission = Permission.objects.get(
            content_type__app_label="security",
            codename="view_security_center",
        )
        group = Group.objects.create(name="Workspace Editor Position")
        group.permissions.add(permission)

        response = self.client.get(reverse("security_position_edit", args=[group.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Use least privilege")
        self.assertContains(response, "Application permissions")
        self.assertContains(response, "Security")
        self.assertRegex(
            response.content.decode(),
            rf'<input[^>]*value="{permission.pk}"[^>]*checked',
        )

    def test_create_role_saves_the_selected_permissions(self):
        permission = Permission.objects.get(
            content_type__app_label="security",
            codename="view_security_center",
        )

        response = self.client.post(
            reverse("security_position_create"),
            {"name": "Workspace Limited Role", "permissions": [str(permission.pk)]},
        )

        self.assertRedirects(response, reverse("security_position_list"))
        created_role = Group.objects.get(name="Workspace Limited Role")
        self.assertQuerySetEqual(
            created_role.permissions.values_list("pk", flat=True),
            [permission.pk],
        )

    def test_email_logs_filter_and_paginate_results(self):
        for index in range(13):
            EmailLog.objects.create(
                sent_by=self.admin,
                email_type="system",
                recipient_name=f"Target {index}",
                recipient_email=f"target-{index}@example.com",
                subject=f"Target message {index}",
                related_object=f"Record {index}",
            )
        for index in range(2):
            EmailLog.objects.create(
                sent_by=self.admin,
                email_type="invoice_reminder",
                recipient_name=f"Other {index}",
                recipient_email=f"other-{index}@example.com",
                subject="Other message",
            )

        url = reverse("email_log_list")
        query = {"q": "target", "type": "system", "page_size": "10", "sort": "oldest"}
        first_page = self.client.get(url, query)

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.context["filtered_count"], 13)
        self.assertEqual(len(first_page.context["email_logs"]), 10)
        self.assertEqual(first_page.context["page_obj"].number, 1)
        self.assertContains(first_page, "q=target&amp;type=system")

        second_page = self.client.get(url, {**query, "page": "2"})

        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(len(second_page.context["email_logs"]), 3)
        self.assertEqual(second_page.context["page_obj"].number, 2)
        self.assertEqual(second_page.context["filters"]["page_size"], "10")

    def test_activity_ledger_filters_and_preserves_pagination(self):
        for index in range(13):
            ActivityLog.objects.create(
                user=self.admin,
                action_type="booking",
                title=f"Target booking event {index}",
                description=f"Target audit context {index}",
            )
        for index in range(2):
            ActivityLog.objects.create(
                user=self.admin,
                action_type="invoice",
                title=f"Other invoice event {index}",
            )

        url = reverse("activity_log_list")
        query = {"q": "target", "action": "booking", "page_size": "10", "sort": "oldest"}
        first_page = self.client.get(url, query)

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.context["filtered_count"], 13)
        self.assertEqual(len(first_page.context["activities"]), 10)
        self.assertContains(first_page, "OPERATIONAL AUDIT TRAIL")
        self.assertContains(first_page, "q=target&amp;action=booking")

        second_page = self.client.get(url, {**query, "page": "2"})

        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(len(second_page.context["activities"]), 3)
        self.assertEqual(second_page.context["page_obj"].number, 2)

    def test_careers_pipeline_filters_and_preserves_pagination(self):
        for index in range(13):
            CareerApplication.objects.create(
                full_name=f"Target Applicant {index}",
                email=f"target-{index}@example.com",
                position="commercial_cleaner",
                status="new",
            )
        for index in range(2):
            CareerApplication.objects.create(
                full_name=f"Other Applicant {index}",
                email=f"other-{index}@example.com",
                position="team_leader",
                status="reviewing",
            )

        url = reverse("careers_list")
        query = {
            "q": "target",
            "status": "new",
            "position": "commercial_cleaner",
            "page_size": "10",
            "sort": "oldest",
        }
        first_page = self.client.get(url, query)

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.context["filtered_count"], 13)
        self.assertEqual(len(first_page.context["applications"]), 10)
        self.assertContains(first_page, "q=target&amp;status=new")

        second_page = self.client.get(url, {**query, "page": "2"})

        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(len(second_page.context["applications"]), 3)
        self.assertEqual(second_page.context["page_obj"].number, 2)

    def test_candidate_dossier_displays_all_submitted_application_details(self):
        application = CareerApplication.objects.create(
            full_name="Jordan Applicant",
            email="jordan@example.com",
            phone="0400000000",
            position="specialist_cleaner",
            employment_type="part_time",
            address="12 Example Road",
            suburb="Adelaide",
            date_of_birth=date(1990, 3, 5),
            work_rights="visa_holder",
            work_rights_details="Current work visa",
            has_drivers_license=True,
            has_vehicle=True,
            years_cleaning_experience=6,
            previous_cleaning_experience="Commercial and specialist cleaning",
            skills="Floor care, safe chemical handling",
            availability_days="Monday to Friday",
            availability_hours="Morning shifts",
            preferred_start_date=date(2026, 12, 1),
            reference_name="Alex Referee",
            reference_phone="0400000001",
            reference_relationship="Previous supervisor",
            cover_letter="I bring six years of cleaning experience.",
        )

        response = self.client.get(reverse("career_detail", args=[application.pk]))

        self.assertEqual(response.status_code, 200)
        for value in (
            "12 Example Road",
            "Current work visa",
            "Floor care, safe chemical handling",
            "Commercial and specialist cleaning",
            "Monday to Friday",
            "Morning shifts",
            "Alex Referee",
            "Previous supervisor",
            "I bring six years of cleaning experience.",
            "1 Dec 2026",
        ):
            with self.subTest(value=value):
                self.assertContains(response, value)

    def test_role_manager_sees_protected_roles_as_read_only(self):
        role_manager = get_user_model().objects.create_user(
            "workspace-role-manager",
            "workspace-role-manager@example.com",
            "test-password",
            is_staff=True,
        )
        role_manager.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="security",
                codename="access_dashboard",
            ),
            Permission.objects.get(
                content_type__app_label="security",
                codename="manage_users",
            ),
            Permission.objects.get(
                content_type__app_label="security",
                codename="manage_security_roles",
            ),
        )
        regular_position, _ = Group.objects.get_or_create(name="Operations Team")
        admin_position, _ = Group.objects.get_or_create(name="Administrator")
        elevated_position, _ = Group.objects.get_or_create(name="Security Team")
        regular_position.permissions.clear()
        admin_position.permissions.clear()
        elevated_position.permissions.clear()
        elevated_position.permissions.add(
            Permission.objects.get(
                content_type__app_label="security",
                codename="manage_security_roles",
            )
        )
        self.client.force_login(role_manager)

        response = self.client.get(reverse("security_position_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("security_position_edit", args=[regular_position.pk]))
        self.assertNotContains(response, reverse("security_position_edit", args=[admin_position.pk]))
        self.assertNotContains(response, reverse("security_position_edit", args=[elevated_position.pk]))
        self.assertContains(response, "Protected role")
        self.assertContains(response, "Edit permissions")

    def test_pages_linked_from_workspaces_render(self):
        customer_user = get_user_model().objects.create_user(
            "workspace-customer",
            "workspace-customer@example.com",
            "test-password",
        )
        customer = Customer.objects.create(
            user=customer_user,
            full_name="Workspace Customer",
            email="workspace-customer@example.com",
            phone="0400000000",
        )
        ticket = SupportTicket.objects.create(
            customer=customer,
            subject="Workspace ticket",
            message="Checking the linked staff workflow.",
        )
        linked_paths = (
            "/dashboard/invoices/",
            "/dashboard/calendar/",
            "/dashboard/leads/",
            "/dashboard/equipment/",
            "/dashboard/supplies/",
            "/dashboard/purchase-orders/",
            "/dashboard/vehicles/",
            "/dashboard/maintenance/",
            "/dashboard/contracts/",
            reverse("ticket_detail", args=[ticket.pk]),
        )

        for page_url in linked_paths:
            with self.subTest(page=page_url):
                response = self.client.get(page_url)
                self.assertEqual(response.status_code, 200)

    def test_reminder_center_displays_each_category_record(self):
        customer_user = get_user_model().objects.create_user(
            "reminder-workspace-customer",
            "reminder-workspace-customer@example.com",
            "test-password",
        )
        customer = Customer.objects.create(
            user=customer_user,
            full_name="Reminder Customer",
            email="reminder-workspace-customer@example.com",
            phone="0400000001",
        )
        today = timezone.localdate()
        overdue_date = today - timedelta(days=1)
        Equipment.objects.create(name="Floor machine", next_service_date=overdue_date)
        supply = CleaningSupply.objects.create(
            name="Neutral cleaner",
            current_stock=1,
            minimum_stock=5,
        )
        PurchaseOrder.objects.create(
            supply=supply,
            supplier_name="Local supplier",
            quantity=12,
        )
        Vehicle.objects.create(
            vehicle_name="Service van",
            registration_number="REMINDER-01",
            service_due_date=overdue_date,
        )
        MaintenanceHistory.objects.create(
            asset_type="vehicle",
            asset_name="Backup van",
            maintenance_date=overdue_date,
            next_service_date=overdue_date,
            description="Scheduled service",
        )
        CleaningContract.objects.create(
            customer=customer,
            service_type="Office cleaning",
            frequency="monthly",
            start_date=today,
            end_date=today + timedelta(days=10),
            preferred_time=timezone.datetime(2026, 11, 1, 9).time(),
            address="10 King Street",
            suburb_postcode="Adelaide 5000",
        )

        response = self.client.get(reverse("reminder_centre"))

        self.assertEqual(response.status_code, 200)
        for visible_detail in (
            "Floor machine",
            "Neutral cleaner",
            "Local supplier",
            "Service van",
            "Backup van",
            "Reminder Customer",
            "Office cleaning",
        ):
            with self.subTest(detail=visible_detail):
                self.assertContains(response, visible_detail)