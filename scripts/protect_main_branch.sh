#!/usr/bin/env bash

set -euo pipefail

BRANCH="${1:-main}"
REQUIRED_CHECK="${2:-CI / ci}"

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) is required. Install it, then rerun this command."
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "You are not authenticated with GitHub CLI."
  echo "Run: gh auth login"
  exit 1
fi

origin_url="$(git remote get-url origin)"
repo_slug=""

case "$origin_url" in
  git@github.com:*)
    repo_slug="${origin_url#git@github.com:}"
    repo_slug="${repo_slug%.git}"
    ;;
  https://github.com/*)
    repo_slug="${origin_url#https://github.com/}"
    repo_slug="${repo_slug%.git}"
    ;;
  *)
    echo "Unsupported origin URL format: $origin_url"
    exit 1
    ;;
esac

payload_file="$(mktemp)"
trap 'rm -f "$payload_file"' EXIT

cat > "$payload_file" <<JSON
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["$REQUIRED_CHECK"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 1
  },
  "restrictions": null
}
JSON

gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  "repos/${repo_slug}/branches/${BRANCH}/protection" \
  --input "$payload_file" \
  >/dev/null

echo "Branch protection updated for ${repo_slug}:${BRANCH}."
echo "Required status check: ${REQUIRED_CHECK}"
