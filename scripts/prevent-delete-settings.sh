#!/bin/sh
# Helper script to block accidental deletion of ydcleaning/settings.py
# This script is tracked in the repo; the git hook will call it.

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGED_DELETIONS=$(git diff --cached --name-status | awk '$1=="D" {print $2}')

for f in $STAGED_DELETIONS; do
  if [ "$f" = "ydcleaning/settings.py" ] || [ "$f" = "./ydcleaning/settings.py" ]; then
    echo "\nError: Commit includes deletion of ydcleaning/settings.py — this file is protected by repository policy."
    echo "If you really want to remove it, remove it from staged changes and run the commit again with --no-verify."
    echo "Example: git reset HEAD ydcleaning/settings.py && git rm ydcleaning/settings.py && git commit -m 'Remove settings' --no-verify"
    exit 1
  fi
done

exit 0
