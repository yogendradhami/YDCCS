# Secret Rotation Runbook

**Project:** YD Commercial Cleaning (Django)  
**Purpose:** Safely replace credentials that may have been exposed.  
**Rule:** Never put real secret values in this document, Git, issue comments, screenshots, or chat messages.

## 1. Immediate response

If a credential may have been exposed:

1. Identify the provider and the credential's permissions.
2. Revoke or disable the exposed credential as soon as practical. For production database credentials, coordinate the replacement to avoid unnecessary downtime.
3. Review provider audit logs, access logs, recent deployments, and billing/activity for suspicious use.
4. Generate a replacement using the provider's official dashboard or CLI.
5. Update every service that consumes the credential.
6. Verify the integration and then confirm the old credential is revoked.
7. Record the rotation date and result without recording the secret itself.

Deleting a secret from a file or commit does **not** make the old credential safe. Treat it as compromised.

## 2. Rotation inventory

Check each service actually enabled in this deployment.

| Area | Examples of credentials/configuration | Rotation and verification |
|---|---|---|
| Django | `DJANGO_SECRET_KEY` | Generate a high-entropy replacement, update all app instances, restart/redeploy, test login and signed data. Review effects on sessions and signatures. |
| Authentication | SimpleJWT signing configuration, API tokens | Rotate the configured signing key/secret, revoke or expire affected tokens, test token issue/refresh and protected endpoints. |
| PostgreSQL | `DATABASE_URL` or database username/password | Change database credentials at the database provider, update Render and other consumers, test database access, then revoke old credentials. |
| Redis / Channels | `REDIS_URL` | Rotate Redis password or credentials if supported, update all consumers, test WebSockets/background work. |
| Email / Resend | `RESEND_API_KEY`, SMTP credentials | Revoke the exposed key/password, issue a replacement, update environment variables, test a non-sensitive email. |
| Cloudinary | Cloud name, API key, API secret | Rotate the exposed API secret/key in Cloudinary, update deployment configuration, test upload and retrieval. Cloud name alone is generally an identifier, not an authentication secret. |
| Google | OAuth client secret, service-account key, API keys | Rotate/restrict the affected credential, inspect access, update callback/configuration, test the OAuth flow. Rotate only credentials that exist in the project. |
| Stripe | Secret API key, webhook signing secret | Roll keys using Stripe's supported rotation process, update server and webhook configuration, verify test events and payment flows. Never expose secret keys in browser code. |
| Twilio | Auth token or API key | Rotate in Twilio, update SMS consumers, verify delivery and review usage logs. |
| GitHub / CI | Personal access tokens, deploy keys, Actions secrets | Revoke exposed credentials, replace secrets in the relevant settings, review workflow runs and repository access. |
| Render | API tokens and service environment variables | Revoke exposed Render API tokens; update service variables and redeploy. Review access to the service and logs. |

Do not create or rotate credentials for integrations that the application does not use.

## 3. Local development

From the repository root:

```bash
# Confirm the current branch and working tree
git status -sb
git branch --show-current

# Inspect which environment files are tracked (names only)
git ls-files '.env' '.env.*'
```

If a real environment file is tracked, stop and remove it from version control carefully; do not print its contents. Ensure local secret files are ignored by Git. Keep example files limited to placeholders.

Generate a new Django secret locally with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Copy the output directly into the trusted local secret store or deployment settings. Do not commit it or paste it into chat.

## 4. Render deployment

1. Open the correct Render service and its Environment settings.
2. Update the relevant variable(s) with replacement credentials.
3. Check all other consumers, including background workers, scheduled jobs and separate services.
4. Save the changes and deploy/restart according to the service's normal procedure.
5. Check deployment logs for startup/configuration errors without printing environment values.
6. Run the verification checklist below.
7. Revoke the old credential if it was not already revoked.

For database credential changes, make sure the new database user/password is valid before restarting all consumers. Prefer a controlled overlap only when the provider supports it and the exposed credential has been contained.

## 5. Verification checklist

- [ ] Django starts with production debug mode disabled.
- [ ] Database queries and migrations work as expected.
- [ ] Login, password reset and API authentication work.
- [ ] Redis/Channels features work if enabled.
- [ ] Email and quote/booking notifications work.
- [ ] Cloudinary upload and media access work if enabled.
- [ ] Payment and webhook flows work if enabled.
- [ ] Scheduled jobs/background workers work.
- [ ] Old credentials are revoked or disabled.
- [ ] Provider activity and billing have been reviewed.
- [ ] No actual credentials were added to Git during the process.

## 6. Git history and repository cleanup

If a secret was committed:

1. Revoke/rotate it first.
2. Remove the secret from the current tracked files and replace it with environment-variable configuration.
3. Scan the repository and its history using a secret scanner such as [Gitleaks](https://github.com/gitleaks/gitleaks).
4. Review findings privately; redact secret values in reports.
5. If history rewriting is necessary, coordinate with collaborators, rewrite only after making a controlled backup, force-push carefully, and require collaborators to re-clone or clean their local history.
6. Review forks, cached artifacts, CI logs, release assets and any copied files.

History cleanup is not a substitute for credential rotation.

## 7. Completion record

Record only non-secret metadata:

- Date/time of rotation:
- Service/provider:
- Credential label or variable name:
- Old credential revoked: Yes / No / Not applicable
- Deployment verified: Yes / No
- Activity logs reviewed: Yes / No
- Follow-up required:

Never record the credential value, full connection URL, token, password or private key.
