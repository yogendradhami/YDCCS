from django.contrib.auth.models import Group, Permission, User
from django.db.models.signals import post_migrate
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError


ROLE_APP_LABELS = {
    "Operations": {
        "bookings",
        "contracts",
        "employees",
        "gallery",
        "reports",
        "rosters",
        "attendance",
        "leave_management",
    },
    "Finance": {"invoices", "payroll", "expenses"},
    "HR": {
        "employees",
        "attendance",
        "leave_management",
        "payroll",
        "company_documents",
        "induction",
    },
}
SAFE_PERMISSION_APPS = {
    "analytics",
    "attendance",
    "bookings",
    "blog",
    "cleaning_game",
    "company_documents",
    "contracts",
    "core",
    "corporate",
    "customers",
    "dashboard",
    "employees",
    "expenses",
    "gallery",
    "google_reviews",
    "induction",
    "invoices",
    "leave_management",
    "locations",
    "payroll",
    "quotes",
    "reports",
    "reviews",
    "rosters",
    "security",
    "security_monitor",
    "services",
    "support",
}


@receiver(post_migrate)
def seed_security_roles(sender, **kwargs):
    if sender.label == "security_monitor":
        monitor_permissions = list(
            Permission.objects.select_related("content_type").filter(
                content_type__app_label="security_monitor",
            )
        )
        for role_name, permission_set in {
            "Administrator": monitor_permissions,
            "Manager": [
                permission
                for permission in monitor_permissions
                if permission.codename.startswith("view_")
            ],
        }.items():
            group = Group.objects.filter(name=role_name).first()
            if group:
                group.permissions.add(*permission_set)
        return

    if sender.label != "security":
        return

    permissions = list(
        Permission.objects.select_related("content_type").filter(
            content_type__app_label__in=SAFE_PERMISSION_APPS,
        )
    )
    by_group = {
        "Administrator": permissions,
        "Manager": [
            permission
            for permission in permissions
            if (
                permission.content_type.app_label == "security"
                and permission.codename in {"access_dashboard", "view_security_center"}
            )
            or (
                permission.content_type.app_label == "security_monitor"
                and permission.codename.startswith("view_")
            )
            or permission.content_type.app_label not in {"security", "security_monitor"}
        ],
        "Operations": [
            permission
            for permission in permissions
            if permission.content_type.app_label in ROLE_APP_LABELS["Operations"]
            or (
                permission.content_type.app_label == "security"
                and permission.codename == "access_dashboard"
            )
        ],
        "Finance": [
            permission
            for permission in permissions
            if permission.content_type.app_label in ROLE_APP_LABELS["Finance"]
            or (
                permission.content_type.app_label == "security"
                and permission.codename == "access_dashboard"
            )
        ],
        "HR": [
            permission
            for permission in permissions
            if permission.content_type.app_label in ROLE_APP_LABELS["HR"]
            or (
                permission.content_type.app_label == "security"
                and permission.codename == "access_dashboard"
            )
        ],
        "Viewer": [
            permission
            for permission in permissions
            if (
                permission.codename.startswith("view_")
                and permission.content_type.app_label not in {"security", "security_monitor"}
            )
            or (
                permission.content_type.app_label == "security"
                and permission.codename == "access_dashboard"
            )
        ],
    }

    administrator_created = False
    for role_name, role_permissions in by_group.items():
        group, created = Group.objects.get_or_create(name=role_name)
        if role_name == "Administrator":
            administrator_created = created
        # Keep role presets safe from Django's built-in user/group
        # administration permissions, which can grant superuser access.
        safe_permissions = [
            permission
            for permission in role_permissions
            if permission.content_type.app_label not in {"auth", "admin"}
            and (
                role_name == "Administrator"
                or permission.codename != "manage_security_roles"
            )
        ]
        if created or not group.permissions.exists():
            group.permissions.set(safe_permissions)
        else:
            # Add the dashboard/security permissions introduced with this app
            # without overwriting any role permissions an administrator set.
            required_codenames = {"access_dashboard"}
            if role_name in {"Administrator", "Manager"}:
                required_codenames.add("manage_users")
                required_codenames.add("view_security_center")
            if role_name == "Administrator":
                required_codenames.add("manage_security_roles")
            required_permissions = [
                permission
                for permission in permissions
                if permission.content_type.app_label == "security"
                and permission.codename in required_codenames
            ]
            group.permissions.add(*required_permissions)

    administrator = Group.objects.get(name="Administrator")
    if administrator_created:
        for user in User.objects.filter(is_staff=True, is_superuser=False).iterator():
            user.groups.add(administrator)


@receiver(pre_save, sender=User)
def prevent_duplicate_account_email(sender, instance, **kwargs):
    email = (instance.email or "").strip().casefold()
    if not email:
        return

    if instance.pk:
        previous_email = (
            sender.objects.filter(pk=instance.pk)
            .values_list("email", flat=True)
            .first()
        )
        if (previous_email or "").strip().casefold() == email:
            return

    duplicate = sender.objects.filter(email__iexact=email)
    if instance.pk:
        duplicate = duplicate.exclude(pk=instance.pk)
    if duplicate.exists():
        raise ValidationError({"email": "An account already uses this email address."})

    instance.email = email

