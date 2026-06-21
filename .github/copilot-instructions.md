Project: YD Commercial Cleaning (Django monolith)

Quick purpose
- This repo is a single Django project with many apps (portal, dashboard, bookings, invoices,
  employees, notifications, etc.). Agents should treat it as a monolithic Django web app.

Essential entrypoints
- `manage.py` — Django CLI used for running the dev server, migrations, tests and management commands.
- `ydcleaning/settings.py` — central configuration: INSTALLED_APPS, TEMPLATES, DATABASES, third-party keys.
- `templates/`, `static/`, `media/` — top-level template and static folders used across apps.

Common workflows (commands)
- Use the provided virtualenv if present: `source venv/bin/activate`.
- Run migrations: `python manage.py migrate`.
- Create a superuser: `python manage.py createsuperuser`.
- Start dev server: `python manage.py runserver`.
- Run tests: `python manage.py test` (each app contains `tests.py`).
- Collect static files for production: `python manage.py collectstatic`.

Architecture & patterns to know
- Monolithic Django project: many small Django apps live at project root (e.g. `bookings`, `invoices`, `customers`).
- Each app typically follows the Django pattern: `models.py`, `views.py`, `forms.py`, `urls.py`, `tests.py`, `migrations/`.
- Templates are centralized in the repository `templates/` folder (examples: `portal_*`, `employee_portal_*`, `dashboard_*`).
- Context processors are used for global template data: see `notifications/context_processors.py` and `dashboard/context_processors.py` and their use in `ydcleaning/settings.py`.
- App registration: some apps declare their AppConfig explicitly (example: `notifications.apps.NotificationsConfig` in `INSTALLED_APPS`).

External integrations & secrets (discovered)
- Stripe keys, Google OAuth, Gmail SMTP credentials and a Resend API key are present in `ydcleaning/settings.py`.
- Do NOT commit or leak credentials; prefer using environment variables when modifying config.

Conventions & naming
- Template naming: `portal_*` for customer portal pages, `employee_*` for staff portal, `dashboard_*` for admin dashboards.
- Reusable partials live under `templates/partials/` (e.g. `partials/navbar.html`, `partials/footer.html`).
- Files named `*_form.html`, `*_list.html`, `*_detail.html` follow CRUD view patterns.

Where to look for common tasks
- Add a new app: follow existing apps (create `models.py`, `views.py`, `urls.py`, `templates/<app>/...`, add to `INSTALLED_APPS`).
- Change global layout: edit `templates/base.html` and `templates/partials/*`.
- Inspect routing: `ydcleaning/urls.py` and each app's `urls.py`.

Testing & debugging tips
- The project uses SQLite by default (`db.sqlite3`); tests run against the same DB engine.
- If tests fail locally, run a single app test: `python manage.py test bookings`.
- Use Django logging or add print/debug breakpoints in views — runserver runs synchronously for quick iteration.

Useful files to reference
- `ydcleaning/settings.py` — configuration and integrations.
- `manage.py` — run commands.
- `templates/base.html` and `templates/partials/*` — shared UI layout.
- Examples of app layout: `bookings/`, `invoices/`, `employees/`, `notifications/`.

Behavior to avoid
- Do not commit or print secret API keys. If a change touches `ydcleaning/settings.py`, prefer replacing secrets with environment variables.

If anything is unclear or missing, tell me which area (setup, specific app, or integration) you want expanded and I will iterate.
