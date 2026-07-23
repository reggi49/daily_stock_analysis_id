#!/usr/bin/env bash
# =============================================================================
# setup-gh-secrets-vars.sh
# -----------------------------------------------------------------------------
# Phase 0 bootstrap for the "daily_stock_analysis_id" repository.
#
# Sets the GitHub Actions SECRETS:
#   - TAVILY_API_KEYS   (web/news search provider)
#   - BRAVE_API_KEYS    (web/news search provider)
#
# Sets the GitHub Actions VARIABLES:
#   - REPORT_TYPE=full          (generate the full analysis report)
#   - SINGLE_STOCK_NOTIFY=true  (emit per-stock notifications)
#
# Then verifies everything with `gh secret list` and `gh variable list`.
#
# Requirements:
#   - GitHub CLI (gh) installed and authenticated (`gh auth status`).
#   - Write access to the target repository.
#
# The secret VALUES are never hard-coded here. They are read from the
# environment so nothing sensitive is committed to the repo:
#   TAVILY_API_KEYS  - one or more Tavily keys (comma separated is fine)
#   BRAVE_API_KEYS   - one or more Brave keys  (comma separated is fine)
#
# Usage:
#   export TAVILY_API_KEYS="tvly-xxxx,tvly-yyyy"
#   export BRAVE_API_KEYS="brv-xxxx"
#   ./scripts/setup-gh-secrets-vars.sh
#
# Optional overrides:
#   REPO="owner/daily_stock_analysis_id" ./scripts/setup-gh-secrets-vars.sh
#   REPORT_TYPE=brief SINGLE_STOCK_NOTIFY=false ./scripts/setup-gh-secrets-vars.sh
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration (overridable via environment)
# -----------------------------------------------------------------------------
REPO="${REPO:-}"
REPORT_TYPE="${REPORT_TYPE:-full}"
SINGLE_STOCK_NOTIFY="${SINGLE_STOCK_NOTIFY:-true}"

# -----------------------------------------------------------------------------
# Small logging helpers
# -----------------------------------------------------------------------------
log()  { printf '\033[1;34m[INFO]\033[0m  %s\n' "$*"; }
ok()   { printf '\033[1;32m[ OK ]\033[0m  %s\n' "$*"; }
warn() { printf '\033[1;33m[WARN]\033[0m  %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[FAIL]\033[0m  %s\n' "$*" >&2; exit 1; }

# -----------------------------------------------------------------------------
# Preconditions
# -----------------------------------------------------------------------------
command -v gh >/dev/null 2>&1 || die "GitHub CLI (gh) is not installed or not on PATH."

if ! gh auth status >/dev/null 2>&1; then
	die "gh is not authenticated. Run 'gh auth login' first."
fi

# Build the --repo flag only when REPO is explicitly provided, otherwise let
# gh infer the repository from the current git remote.
REPO_ARGS=()
if [[ -n "${REPO}" ]]; then
	REPO_ARGS=(--repo "${REPO}")
	log "Target repository: ${REPO}"
else
	log "Target repository: (inferred from current git remote)"
fi

# -----------------------------------------------------------------------------
# Validate required secret values are present in the environment
# -----------------------------------------------------------------------------
: "${TAVILY_API_KEYS:?Environment variable TAVILY_API_KEYS must be set (secret value).}"
: "${BRAVE_API_KEYS:?Environment variable BRAVE_API_KEYS must be set (secret value).}"

# -----------------------------------------------------------------------------
# 1) Secrets
# -----------------------------------------------------------------------------
log "Setting secret TAVILY_API_KEYS ..."
printf '%s' "${TAVILY_API_KEYS}" | gh secret set TAVILY_API_KEYS "${REPO_ARGS[@]}" --body -
ok "Secret TAVILY_API_KEYS set."

log "Setting secret BRAVE_API_KEYS ..."
printf '%s' "${BRAVE_API_KEYS}" | gh secret set BRAVE_API_KEYS "${REPO_ARGS[@]}" --body -
ok "Secret BRAVE_API_KEYS set."

# -----------------------------------------------------------------------------
# 2) Variables
# -----------------------------------------------------------------------------
log "Setting variable REPORT_TYPE=${REPORT_TYPE} ..."
gh variable set REPORT_TYPE "${REPO_ARGS[@]}" --body "${REPORT_TYPE}"
ok "Variable REPORT_TYPE set."

log "Setting variable SINGLE_STOCK_NOTIFY=${SINGLE_STOCK_NOTIFY} ..."
gh variable set SINGLE_STOCK_NOTIFY "${REPO_ARGS[@]}" --body "${SINGLE_STOCK_NOTIFY}"
ok "Variable SINGLE_STOCK_NOTIFY set."

# -----------------------------------------------------------------------------
# 3) Verification
# -----------------------------------------------------------------------------
echo
log "===== gh secret list ====="
gh secret list "${REPO_ARGS[@]}"

echo
log "===== gh variable list ====="
gh variable list "${REPO_ARGS[@]}"

# -----------------------------------------------------------------------------
# 4) Assert the expected entries exist
# -----------------------------------------------------------------------------
echo
log "Verifying expected entries are present ..."

secrets_out="$(gh secret list "${REPO_ARGS[@]}")"
vars_out="$(gh variable list "${REPO_ARGS[@]}")"

check() {
	local needle="$1" haystack="$2" label="$3"
	if grep -q -- "${needle}" <<<"${haystack}"; then
		ok "${label} present."
	else
		die "${label} MISSING from listing."
	fi
}

check "TAVILY_API_KEYS"      "${secrets_out}" "Secret TAVILY_API_KEYS"
check "BRAVE_API_KEYS"       "${secrets_out}" "Secret BRAVE_API_KEYS"
check "REPORT_TYPE"          "${vars_out}"    "Variable REPORT_TYPE"
check "SINGLE_STOCK_NOTIFY"  "${vars_out}"    "Variable SINGLE_STOCK_NOTIFY"

echo
ok "All secrets and variables configured and verified successfully."
