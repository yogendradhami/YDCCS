<<<<<<< HEAD
# YD Commercial Cleaning — Developer README

Quick start

1. Create and activate a virtualenv:
=======
# YD Commercial Cleaning (Django monolith)

Quick purpose
- This repo is a single Django project with many apps (portal, dashboard, bookings, invoices,
  employees, notifications, etc.). Agents should treat it as a monolithic Django web app.

Essential entrypoints
- `manage.py` — Django CLI used for running the dev server, migrations, tests and management commands.
- `config/settings.py` — central configuration. This project now reads secrets from a `.env` file using `django-environ`.
- `templates/`, `static/`, `media/` — top-level template and static folders used across apps.

Common workflows (commands)
- Use the provided virtualenv if present: `source venv/bin/activate`.
- Run migrations: `python manage.py migrate`.
- Create a superuser: `python manage.py createsuperuser`.
- Start dev server: `python manage.py runserver`.
- Run tests: `python manage.py test` (each app contains `tests.py`).
- Collect static files for production: `python manage.py collectstatic`.

Quick setup (local)
1. Copy the example env and fill sensitive values:

```bash
cp .env.example .env
# edit .env and set SECRET_KEY, DEBUG=True for local development, DB and any API keys
```

2. Create virtualenv and install dependencies:
>>>>>>> 5815f15 (Initial project commit)

```bash
python -m venv venv
source venv/bin/activate
<<<<<<< HEAD
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill values:

```bash
cp .env.example .env
# edit .env to add secrets
```

4. Run migrations and start dev server:
=======
pip install -r requirements.txt
```

3. Run migrations and start dev server:
>>>>>>> 5815f15 (Initial project commit)

```bash
python manage.py migrate
python manage.py runserver
```

<<<<<<< HEAD
Notes
- All secrets and API keys must be provided via environment variables. See `.env.example`.
- The project defaults to SQLite for local development. For production set `DATABASE_URL`.
- Use the provided GitHub Actions workflow to run tests on push/PR.
=======
CI & Deployment
- A GitHub Actions workflow is included at `.github/workflows/ci.yml` to run migrations and tests on push/PR.
- A `Dockerfile` and `docker-compose.yml` are provided for containerized local development. Use `docker-compose up --build` to run.

Error monitoring (Sentry)
- To enable Sentry, add `SENTRY_DSN` to your `.env` file. The project will initialise Sentry automatically when the DSN is present.
- Optional Sentry env vars:
    - `SENTRY_TRACES_SAMPLE_RATE` (float, default 0.0)
    - `SENTRY_SEND_PII` (bool, default False)
    - `SENTRY_ENVIRONMENT` (string, default `production` or `development` depending on `DEBUG`)

Makefile
- There is a `Makefile` with convenience targets: `make run`, `make migrate`, `make test`, `make docker-up`, etc.
>>>>>>> 5815f15 (Initial project commit)
