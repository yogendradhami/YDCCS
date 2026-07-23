Environment & secrets

Overview

This project uses environment variables for all secrets and third-party keys. The project root contains `.env.example` which lists the variables you should set for local development.

Do not commit `.env` to Git. `.gitignore` already excludes it.

Loading

`config/settings.py` includes a small loader that reads `.env` from the project root and sets any variables that are not already present in the environment. This means:

- For local dev, copy `.env.example` to `.env` and fill the values.
- For CI/CD or production, supply secrets via the environment (GitHub Actions secrets, Docker secrets, cloud provider env variables).

Recommended variables (examples)

```
DJANGO_SECRET_KEY=change-me-local
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=YD Commercial Cleaning <no-reply@example.com>
ADMIN_EMAIL=

RESEND_API_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/google/oauth/callback/

STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_CURRENCY=aud
```

If you prefer using `python-dotenv`, install it and update your workflow, but note the repo already includes an internal loader so installing `python-dotenv` is optional.

Security checklist before publishing

- Ensure `DEBUG=False` in production.
- Set `DJANGO_ALLOWED_HOSTS` to the production host(s).
- Store all keys in a secrets manager when deploying (GitHub Secrets, cloud provider secrets, or Docker secrets).
- Rotate any keys that were committed earlier and scrub git history if necessary.

If you want, I can generate a `.env` template file for local use with placeholders (not real secrets).