# YD Commercial Cleaning (Django monolith)

Quick purpose
- This repo is a single Django project with many apps (portal, dashboard, bookings, invoices, employees, notifications, etc.). Agents should treat it as a monolithic Django web app.

Essential entrypoints
- `manage.py` — Django CLI used for running the dev server, migrations, tests and management commands.
- `ydcleaning/settings.py` — central configuration. This project reads secrets from a `.env` file.
- `templates/`, `static/`, `media/` — top-level folders used across apps.

Common workflows (commands)
- Use the provided virtualenv if present: `source venv/bin/activate`.
- Run migrations: `python manage.py migrate`.
- Create a superuser: `python manage.py createsuperuser`.
- Start dev server: `python manage.py runserver`.
- Run tests: `python manage.py test`.
- Collect static files for production: `python manage.py collectstatic`.

Quick setup (local)
1. Copy the example env and fill sensitive values:

```bash
cp .env.example .env
# edit .env and set SECRET_KEY, DEBUG=True for local development, DB and any API keys
```

2. Create a virtual environment and activate it:

```bash
python -m venv venv
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run migrations and start the development server:

```bash
python manage.py migrate
python manage.py runserver
```

Required environment variables
- Copy `.env.example` or `.env.local.example` and fill in your values.
- The application reads secrets from `.env` and `.env.local`.

Key env vars for deployment:
- `DJANGO_SECRET_KEY` — a strong secret key for Django.
- `DJANGO_DEBUG=False` — turn off debug in production.
- `DJANGO_ALLOWED_HOSTS` — comma-separated hosts served by the app.
- `DATABASE_URL` — database connection string; defaults to SQLite locally.
- `EMAIL_BACKEND` — e.g. `django.core.mail.backends.smtp.EmailBackend`.
- `EMAIL_HOST` — usually `smtp.gmail.com` for Gmail SMTP.
- `EMAIL_PORT` — usually `587` for TLS.
- `EMAIL_USE_TLS` — `True` for SMTP TLS.
- `EMAIL_USE_SSL` — `False` for Gmail/TLS.
- `EMAIL_HOST_USER` — authenticated SMTP sender email.
- `EMAIL_HOST_PASSWORD` — SMTP password or app password.
- `DEFAULT_FROM_EMAIL` — sender email; left blank to auto-use `EMAIL_HOST_USER` for Gmail.

Email templates added:

- `templates/emails/application_received.txt`
- `templates/emails/application_received.html`
- `templates/emails/application_update.txt`
- `templates/emails/application_update.html`

Tests use Django's test email backend (`locmem`) to capture outgoing messages.
- `ADMIN_EMAIL` — admin notification address.
- `RESEND_API_KEY` — API key for Resend if used.
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI` — Google OAuth settings.
- `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_PHONE_NUMBER` — Twilio SMS settings.
- `STRIPE_SECRET_KEY` / `STRIPE_PUBLISHABLE_KEY` / `STRIPE_CURRENCY` — Stripe payment settings.

Docker deployment
- The project Dockerfile is configured to launch the `ydcleaning` Django project package with Gunicorn.
- Build the image from the repository root:

```bash
docker build -t ydcleaning-app .
```

- Run the container with production-like environment variables:

```bash
docker run --rm -p 8000:8000 \
  -e DJANGO_SETTINGS_MODULE=ydcleaning.settings \
  -e DJANGO_DEBUG=False \
  -e DJANGO_SECRET_KEY="your-production-secret" \
  -e DJANGO_ALLOWED_HOSTS="127.0.0.1,localhost" \
  -e DATABASE_URL="sqlite:////app/db.sqlite3" \
  ydcleaning-app
```

- If you need to collect static files inside the container first:

```bash
docker run --rm \
  -e DJANGO_SETTINGS_MODULE=ydcleaning.settings \
  -e DJANGO_DEBUG=False \
  -e DJANGO_SECRET_KEY="your-production-secret" \
  -e DJANGO_ALLOWED_HOSTS="127.0.0.1,localhost" \
  -e DATABASE_URL="sqlite:////app/db.sqlite3" \
  ydcleaning-app python manage.py collectstatic --noinput
```

Docker Compose (local development)
- The included `docker-compose.yml` is designed for local development and mounts the repository into the container.
- Copy your `.env` file first if you want environment variables loaded by Compose.

```bash
cp .env.example .env
docker compose up --build
```

Notes
- All secrets and API keys must be provided via environment variables. See `.env.example`.
- The project defaults to SQLite for local development.
- A GitHub Actions workflow is included at `.github/workflows/ci.yml` to run migrations and tests on push/PR.
- A `Dockerfile` and `docker-compose.yml` are included for containerized local development.

Error monitoring (Sentry)
- To enable Sentry, add `SENTRY_DSN` to your `.env` file. The project initializes Sentry automatically when the DSN is present.
- Optional Sentry env vars:
    - `SENTRY_TRACES_SAMPLE_RATE`
    - `SENTRY_SEND_PII`
    - `SENTRY_ENVIRONMENT`

Makefile
- There is a `Makefile` with convenience targets such as `make run`, `make migrate`, `make test`, and `make docker-up`.
# YDCCS

## Live website chat deployment and retention

- Live chat uses the existing Django Channels ASGI app (`Procfile`) and requires `REDIS_URL` in production. Production startup intentionally fails if Redis is not configured; the in-memory channel layer is development/test-only and cannot deliver across multiple workers.
- Keep the Render web service on the existing Daphne ASGI command. Configure `REDIS_URL` as a private Redis URL in the Render environment group and use HTTPS so browser chat connects over WSS. The ASGI origin check accepts allowed hosts and requires an HTTPS origin in production.
- Staff must have Django's `support.view_livechatconversation` permission to see chat lists/history and `support.change_livechatconversation` permission to take over, reply, or close conversations. Assign those permissions only to support roles that need them.
- `LIVE_CHAT_RETENTION_DAYS` defaults to `180` and must be at least one day. Waiting and active chats are never eligible for cleanup. A closed chat is eligible only when its explicit `closed_at` timestamp is at or before the retention cutoff and `legal_hold` is false. Set legal hold in Django admin when preservation is required.
- Migration `support.0008_livechat_retention_and_rate_limits` backfills pre-existing closed conversations from `updated_at`. This deliberately starts their retention clock at the last recorded update rather than assuming an earlier closure, avoiding premature deletion; review the affected population before using deletion mode.
- First run and review a dry run against the intended environment/database:

```bash
python manage.py migrate --plan
python manage.py cleanup_expired_live_chats --dry-run --batch-size 100
```

- There is no Render Blueprint or cron service in this repository. To schedule safe initial verification, add a Render Cron Job using the same repository, build environment, database environment group, and a daily schedule (for example, 02:00 UTC), with command:

```bash
python manage.py cleanup_expired_live_chats --dry-run --batch-size 100
```

- The command defaults to dry-run and deletes nothing unless `--delete` is explicitly supplied. Do not change the scheduled command to `--delete` until the retention policy, legal holds, dry-run counts, and database backup/recovery process have been reviewed and approved. Deletion cascades to messages and is not reversible except by restoring a database backup. Review cron output and application logs after each run; failures are counted and cause a non-zero command result for scheduler alerting.
- The 180-day default is an operational proposal, not a guarantee of compliance with Australian privacy, tax, contractual, litigation-hold, or record-keeping requirements. Obtain policy review before enabling deletion.
