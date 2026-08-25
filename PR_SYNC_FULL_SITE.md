Title: Sync/full-site — Full site sync, static fixes, CI & Docker

Summary:
This PR brings the workspace in line with the live site snapshot and fixes for local development.

What changed (high level):
- Added responsive public templates and mirrored static assets.
- Implemented `Service` and `BlogPost` models with admin and migrations.
- Added gallery detail pages and pagination.
- Fixed template syntax and static serving (WhiteNoise + collectstatic).
- Added `core` management commands: `seed_site` and `attach_gallery_images`.
- Added CI workflow (`.github/workflows/ci.yml`) and basic view tests.
- Added `docker-compose.dev.yml` and `README_DOCKER.md` for local dev.

Migrations & Seeds:
- Run `python manage.py migrate` then `python manage.py seed_site`.
- Optionally run `python manage.py attach_gallery_images` to populate gallery images.

How to test locally:
1. Using local venv:
   - `source venv/bin/activate`
   - `pip install -r requirements.txt`
   - `python manage.py migrate`
   - `python manage.py runserver`
2. Using Docker Compose:
   - Copy `.env` from `.env.example` and fill secrets
   - `docker compose -f docker-compose.dev.yml up --build`

Deploy checklist (suggested):
- Ensure production env vars are set (SECRET_KEY, DB, Stripe, email, ELFSIGHT_WIDGET_ID, GA_TRACKING_ID).
- Rotate any keys if they were used in this repo history.
- Run migrations on deploy: `python manage.py migrate`.
- Collect static: `python manage.py collectstatic --noinput`.
- Verify `ELFSIGHT_WIDGET_ID` and GA IDs are set before enabling widgets.
- Run smoke tests and spot-check homepage, services, blog, gallery.

Notes:
- No sensitive keys were added to the repo; settings use env vars.
- If you want me to open the PR on GitHub I will use the gh CLI — this requires the `gh` tool authenticated on this machine. Otherwise the draft `PR_SYNC_FULL_SITE.md` is available here for manual PR creation.
