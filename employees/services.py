from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction


@transaction.atomic
def create_employee_from_form(form):
    access_mode = form.cleaned_data["access_mode"]
    employee = form.save(commit=False)
    uploaded_image = form.cleaned_data.get("image")
    linked_user = None

    try:
        if access_mode == "create":
            user_model = get_user_model()
            username_field = user_model.USERNAME_FIELD
            login_email = form.cleaned_data["login_email"].strip().lower()
            username = form.cleaned_data["username"].strip()
            create_values = {
                username_field: username,
                "password": form.cleaned_data["password1"],
                "is_active": employee.active,
            }
            email_field = getattr(user_model, "EMAIL_FIELD", "email")
            if any(field.name == email_field for field in user_model._meta.fields):
                if email_field != username_field:
                    create_values[email_field] = login_email
            linked_user = user_model._default_manager.create_user(**create_values)

        elif access_mode == "link":
            user_model = get_user_model()
            try:
                linked_user = (
                    user_model._default_manager.select_for_update()
                    .get(
                        pk=form.cleaned_data["existing_user"].pk,
                        is_active=True,
                        is_staff=False,
                        is_superuser=False,
                    )
                )
            except user_model.DoesNotExist as error:
                raise ValidationError(
                    "That account is no longer available. Choose another account."
                ) from error

            if hasattr(linked_user, "employee_profile"):
                raise ValidationError(
                    "That account is already linked to an employee."
                )

        employee.user = linked_user
        employee.save()
        form.save_m2m()
    except Exception:
        if uploaded_image and employee.image.name:
            try:
                employee.image.storage.delete(employee.image.name)
            except Exception:
                pass
        raise

    return employee, access_mode in {"create", "link"}