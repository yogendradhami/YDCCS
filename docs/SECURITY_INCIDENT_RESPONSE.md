# Security Incident Response

**Project:** YD Commercial Cleaning  
**Scope:** Suspected exposed credentials, unauthorized repository changes, suspicious API usage, or unexpected production access.

## Principles

- Contain exposure quickly; do not wait for a complete investigation before revoking a clearly compromised credential.
- Do not paste secrets into tickets, chat, terminal transcripts, screenshots, or public reports.
- Preserve useful evidence such as timestamps, commit hashes, provider event IDs and redacted logs.
- Rotate credentials at the provider that issued them.
- Verify recovery and document the outcome.

## Severity guide

| Severity | Example | Initial action |
|---|---|---|
| Critical | Production database credentials, cloud administrator token, payment secret or signing key publicly exposed | Revoke/contain immediately, inspect provider activity, assess data access, restore trusted credentials and verify production. |
| High | Email/SMS/API credential exposed or repository contains active secrets | Revoke/rotate promptly, inspect usage, update consumers and verify integrations. |
| Medium | A non-secret identifier or restricted test credential exposed | Confirm scope and permissions; restrict or rotate if it can grant access. |
| Low | Placeholder/example value with no access capability | Confirm it is genuinely non-secret and fix any misleading documentation. |

When uncertain, treat an active credential as compromised.

## Response procedure

### 1. Contain

1. Identify the provider, credential type and exposure location.
2. Revoke the exposed credential or disable its permissions at the issuing provider.
3. If a public repository exposes credentials, restrict repository access where appropriate, but do not rely on privacy changes as remediation.
4. For production database credentials, coordinate a replacement path that limits downtime while promptly preventing unauthorized access.
5. Preserve relevant logs and commit identifiers without copying secret values.

### 2. Investigate

Review relevant provider audit logs, login history, API usage, billing, deployment events, database access and email/SMS activity. Look for unexpected users, locations, requests, data exports, permission changes or spikes in usage.

Do not assume that no suspicious activity in the available logs proves that the credential was not used.

### 3. Eradicate and rotate

Follow [the Secret Rotation Runbook](SECRET_ROTATION_RUNBOOK.md). Replace the credential in all legitimate consumers, remove hardcoded values, and revoke old credentials. Check local environments, Render services, workers, scheduled jobs, GitHub Actions and any other deployment targets.

### 4. Recover

1. Deploy the corrected configuration.
2. Verify the service starts and critical workflows work.
3. Check error rates, authentication failures, provider activity and unexpected costs.
4. Keep monitoring for renewed suspicious activity.
5. If data may have been accessed, assess the affected data and obtain appropriate security, legal or privacy advice about notification obligations.

### 5. Close the incident

Record:

- Incident identifier and dates (with timezone)
- Credential category and affected service (not the credential value)
- Exposure location and known duration
- Containment and rotation actions
- Evidence and audit logs reviewed
- Impact assessment and uncertainty
- Recovery tests performed
- Follow-up actions, owner and due date

## Git and CI/CD precautions

- Search current files and Git history with a secret scanner.
- Remove active secrets from current files and configure environment variables.
- Review Actions logs, build artifacts, deployment logs, pull requests, forks and collaborator access.
- Rewrite Git history only when needed and coordinate the force-push with collaborators.
- Do not upload unredacted scanner output or secret-containing logs to an issue or pull request.

## Prevention checklist

- [ ] Production secrets are configured in the deployment environment or a secrets manager.
- [ ] Local environment files are excluded from Git.
- [ ] Example configuration files contain placeholders only.
- [ ] Production debug mode is disabled.
- [ ] Third-party credentials have minimum required permissions.
- [ ] Credentials are rotated when exposed and periodically according to provider/risk requirements.
- [ ] Repository access and CI/CD permissions are limited to trusted users.
- [ ] Provider activity and billing alerts are enabled where available.
