Security & Secrets
------------------

1. Rotate any API keys/secrets that were committed to the repository (Stripe, Google, Gmail, Resend).

2. To remove secrets from Git history (if this repo becomes a git repo):
   - Use `git-filter-repo` or the BFG Repo-Cleaner to strip sensitive files/strings, then force-push and rotate keys.
   - Example (git-filter-repo):
     ```bash
     pip install git-filter-repo
     git clone --mirror <repo.git> repo.git
     cd repo.git
     git filter-repo --replace-text ../sensitive.txt
     git push --force
     ```

3. Environment practice:
   - Never commit `.env`. Use `.env.example` (already present) to document required variables.
   - Use orchestration secrets (GitHub Secrets, Docker secrets, or environment variables) in CI/CD.

4. Rotate keys after removal from history. Updating history does not invalidate exposed keys — rotate them.
