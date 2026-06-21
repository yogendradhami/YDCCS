# YD Commercial Cleaning — Developer README

Quick start

1. Create and activate a virtualenv:

```bash
python -m venv venv
source venv/bin/activate
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

```bash
python manage.py migrate
python manage.py runserver
```

Notes
- All secrets and API keys must be provided via environment variables. See `.env.example`.
- The project defaults to SQLite for local development. For production set `DATABASE_URL`.
- Use the provided GitHub Actions workflow to run tests on push/PR.
