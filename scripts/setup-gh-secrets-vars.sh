#!/usr/bin/env bash
set -euo pipefail

echo "==> Preconditions"

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI not found. Install from https://cli.github.com/" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: gh CLI not authenticated. Run: gh auth login" >&2
  exit 1
fi
echo "gh CLI found and authenticated."

# ---------------------------------------------------------------------------
# Resolve target repository.
#
# The deploy repo is YOUR fork "daily_stock_analysis_id", NOT the upstream
# ZhuLinsen/daily_stock_analysis. Auto-detecting via git remote points at the
# upstream, which causes: HTTP 403 (no write permission on actions/variables).
#
# Override anytime with:  GH_REPO="owner/repo" bash scripts/setup-gh-secrets-vars.sh
# ---------------------------------------------------------------------------
OWNER="$(gh api user --jq .login)"
REPO="${GH_REPO:-${OWNER}/daily_stock_analysis_id}"
echo "Target repository: ${REPO}"

# Fail fast (with a clear message) if the repo is missing or not writable.
if ! gh api "repos/${REPO}" >/dev/null 2>&1; then
  echo "ERROR: repository '${REPO}' not found or not accessible with this token." >&2
  echo "       Set the correct repo, e.g.: GH_REPO=\"${OWNER}/your-repo\" bash scripts/setup-gh-secrets-vars.sh" >&2
  exit 1
fi

CAN_PUSH="$(gh api "repos/${REPO}" --jq '.permissions.push')"
CAN_ADMIN="$(gh api "repos/${REPO}" --jq '.permissions.admin')"
echo "Permissions -> push: ${CAN_PUSH}, admin: ${CAN_ADMIN}"
if [ "$CAN_PUSH" != "true" ] && [ "$CAN_ADMIN" != "true" ]; then
  echo "ERROR: no write access to '${REPO}'. You cannot set secrets/variables here." >&2
  echo "       Use your own fork/deploy repo via GH_REPO=..." >&2
  exit 1
fi

echo
echo "==> Setting repository secrets"
if [ -n "${TAVILY_API_KEYS:-}" ]; then
  printf '%s' "$TAVILY_API_KEYS" | gh secret set TAVILY_API_KEYS --repo "$REPO"
  echo "set secret TAVILY_API_KEYS"
else
  echo "skip TAVILY_API_KEYS (export it first to set the secret)"
fi

if [ -n "${BRAVE_API_KEYS:-}" ]; then
  printf '%s' "$BRAVE_API_KEYS" | gh secret set BRAVE_API_KEYS --repo "$REPO"
  echo "set secret BRAVE_API_KEYS"
else
  echo "skip BRAVE_API_KEYS (export it first to set the secret)"
fi

echo
echo "==> Setting repository variables"
gh variable set REPORT_TYPE --repo "$REPO" --body "full"
echo "set variable REPORT_TYPE=full"
gh variable set SINGLE_STOCK_NOTIFY --repo "$REPO" --body "true"
echo "set variable SINGLE_STOCK_NOTIFY=true"

echo
echo "==> Verification: gh secret list"
gh secret list --repo "$REPO"

echo
echo "==> Verification: gh variable list"
gh variable list --repo "$REPO"

echo
echo "==> Done for ${REPO}"
