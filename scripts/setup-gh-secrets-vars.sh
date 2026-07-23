#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Setup GitHub Secrets & Variables untuk repo daily_stock_analysis_id
# - Secrets : TAVILY_API_KEYS, BRAVE_API_KEYS (dari env var lokal)
# - Variables: REPORT_TYPE=full, SINGLE_STOCK_NOTIFY=true
# Override target repo: REPO=owner/nama bash scripts/setup-gh-secrets-vars.sh
# ============================================================

REPO_NAME="daily_stock_analysis_id"

if [[ -n "${REPO:-}" ]]; then
  TARGET_REPO="$REPO"
else
  OWNER="$(gh api user -q .login)"
  TARGET_REPO="${OWNER}/${REPO_NAME}"
fi

echo "==> Target repo: ${TARGET_REPO}"

# Pastikan repo bisa diakses (fail-fast dengan pesan jelas)
if ! gh repo view "$TARGET_REPO" --json nameWithOwner -q .nameWithOwner >/dev/null 2>&1; then
  echo "ERROR: repo ${TARGET_REPO} tidak ditemukan / tidak bisa diakses oleh akun gh saat ini." >&2
  echo "Cek: gh auth status, atau jalankan ulang dengan REPO=owner/nama." >&2
  exit 1
fi

# Validasi env var sumber secret
: "${TAVILY_API_KEYS:?ERROR: env var TAVILY_API_KEYS belum di-set di shell ini}"
: "${BRAVE_API_KEYS:?ERROR: env var BRAVE_API_KEYS belum di-set di shell ini}"

echo "==> Set secret TAVILY_API_KEYS"
gh secret set TAVILY_API_KEYS --repo "$TARGET_REPO" --body "$TAVILY_API_KEYS"

echo "==> Set secret BRAVE_API_KEYS"
gh secret set BRAVE_API_KEYS --repo "$TARGET_REPO" --body "$BRAVE_API_KEYS"

echo "==> Set variable REPORT_TYPE=full"
gh variable set REPORT_TYPE --repo "$TARGET_REPO" --body "full"

echo "==> Set variable SINGLE_STOCK_NOTIFY=true"
gh variable set SINGLE_STOCK_NOTIFY --repo "$TARGET_REPO" --body "true"

echo ""
echo "==> Verifikasi: gh secret list"
gh secret list --repo "$TARGET_REPO"

echo ""
echo "==> Verifikasi: gh variable list"
gh variable list --repo "$TARGET_REPO"

echo ""
echo "==> DONE: secrets & variables ter-set di ${TARGET_REPO}"
