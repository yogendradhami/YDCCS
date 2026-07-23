Local development and run instructions

Quick start

1. Activate the virtualenv:

```bash
source venv/bin/activate
```

2. Install dependencies (if not already):

```bash
pip install -r requirements.txt
```

3. Copy the example env file and fill values:

```bash
cp .env.example .env
# Edit .env and set DJANGO_SECRET_KEY, RESEND_API_KEY, STRIPE keys, etc.
```

Note: `ydcleaning/settings.py` will automatically load `.env` and `.env.local` files from the project root when present.

4. Run migrations and create a superuser:

```bash
python manage.py migrate
python manage.py createsuperuser
```

5. Run the dev server:

```bash
python manage.py runserver
```

Quick checks

- Run Django system checks:

```bash
DJANGO_SECRET_KEY=dev-secret DJANGO_DEBUG=True DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost python manage.py check
```

- Run tests for an app (example):

```bash
python manage.py test bookings
```

Notes

- Do NOT commit `.env`. Use `.env.example` to document required variables.
- For production deployments, set `DEBUG=False` and set `DJANGO_ALLOWED_HOSTS` appropriately.
- Rotate keys immediately if any secret was previously committed to git history.

Useful env variables (documented in .env.example):
- DJANGO_SECRET_KEY
- DJANGO_DEBUG
- DJANGO_ALLOWED_HOSTS
- EMAIL_BACKEND, EMAIL_HOST, EMAIL_PORT, EMAIL_USE_TLS, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD
- STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY
- RESEND_API_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

If you'd like, I can add a `make` file or simple scripts to automate the setup steps.