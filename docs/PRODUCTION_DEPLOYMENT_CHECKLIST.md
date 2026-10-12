# Production Deployment Checklist

**Project:** YD Commercial Cleaning (Django)  
**Deployment:** Render (confirm the service and branch before deploying)

Use this checklist before and after production deployments. It complements the existing [environment configuration guide](ENVIRONMENT.md).

## Before deployment

### Repository and changes

- [ ] Confirm the intended branch and commit.
- [ ] Review `git status -sb` and `git diff --check`.
- [ ] Review all staged changes; do not stage everything blindly.
- [ ] Ensure no `.env`, private keys, database dumps, tokens, passwords or real credentials are tracked.
- [ ] Run a secret scanner against the repository and, when needed, Git history.
- [ ] Confirm dependencies and migrations are included intentionally.

### Django checks

Activate the project's virtual environment, then run:

```bash
python manage.py check
python manage.py test
python manage.py collectstatic --noinput
```

If the project has a documented test-settings module, use it when tests must run against an isolated test database. Do not point test runs at the live production database.

Review test failures and static collection output before deployment. Run any additional targeted tests relevant to the changed modules.

### Environment and security

- [ ] Production `DJANGO_DEBUG` is disabled.
- [ ] `DJANGO_SECRET_KEY` is strong, private and set in the deployment environment.
- [ ] Allowed hosts and HTTPS settings match the production domain.
- [ ] `DATABASE_URL` and `REDIS_URL` are configured as required.
- [ ] Email, Cloudinary, payment, OAuth and SMS settings are present only where those integrations are enabled.
- [ ] No secrets are printed by diagnostics, test output or deployment scripts.
- [ ] Any exposed credentials have been rotated and old credentials revoked.

### Database changes

- [ ] Read migration files and assess whether changes are backwards compatible.
- [ ] Ensure a current, restorable database backup exists before risky changes.
- [ ] Plan migration execution and rollback/recovery for production.
- [ ] Do not run destructive database commands without explicit review.

## Deploy

1. Push the reviewed commit to the intended GitHub branch.
2. Confirm Render is configured to deploy that branch.
3. Review the build and deployment logs.
4. Confirm migrations run through the project's approved deployment process.
5. Confirm the new deployment becomes healthy before treating it as complete.

Do not assume that a Git push means the deployment succeeded.

## After deployment

- [ ] Open the public site over HTTPS.
- [ ] Check critical pages, static assets and media.
- [ ] Test login and role-based access.
- [ ] Test a representative booking or quote workflow.
- [ ] Confirm email delivery if email behavior changed.
- [ ] Confirm database, Redis, storage and external API integrations as applicable.
- [ ] Check Render health, error logs and relevant provider logs.
- [ ] Confirm no secrets appear in browser responses or logs.
- [ ] Record the deployed commit and verification outcome.

## Rollback

If a deployment is unhealthy:

1. Identify whether the problem is application code, environment configuration, a migration or an external dependency.
2. Use Render's supported rollback/redeploy process where appropriate.
3. Restore a compatible configuration and verify service health.
4. Do not reverse database migrations or restore a backup without assessing data loss and compatibility.
5. Record the incident and follow-up fix.

## Git commands for a reviewed deployment

```bash
git status -sb
git branch --show-current
git diff --check
git diff
git diff --cached
```

After staging only intended files, review the staged diff, commit, and push to the confirmed branch. Avoid `git add .` until you have checked for secrets and unrelated files.
