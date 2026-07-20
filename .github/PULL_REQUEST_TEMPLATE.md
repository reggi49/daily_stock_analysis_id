<!--
For English contributors: please fill in English.
-->

## PR Type

- [ ] fix
- [ ] feat
- [ ] refactor
- [ ] docs
- [ ] chore
- [ ] test

## Background And Problem

Describe the problem, its impact, and what triggers it.

## Scope Of Change

List the modules and files changed in this PR.

> Note: Please list all changed files based on the actual `git diff` output (file count is recommended) to avoid mismatches.

> If this PR modifies collaboration and governance files (such as `.github/PULL_REQUEST_TEMPLATE.md`, `.github/copilot-instructions.md`, `AGENTS.md`, `.github/instructions/*`, or `.claude/skills/**`), please supply the "reason for change + impact + rollback method (default: revert)" in the Summary / Compatibility / Rollback sections to keep the scope consistent.

> It is recommended to execute and paste the output of the following commands:

```bash
BASE_REF=$(git merge-base HEAD origin/main)
git diff --stat "$BASE_REF"..HEAD
git diff --name-only "$BASE_REF"..HEAD
```

- Total files / lines changed (paste `git diff --stat "$BASE_REF"..HEAD`):
- File list (list all changes from diff):
- Updated documentation files (`docs/*`):

## Issue Link

Fill in one of the following:
- `Fixes #<issue_number>`
- `Refs #<issue_number>`
- If no issue, explain the motivation and acceptance criteria

## Verification Commands And Results

Paste the commands you actually ran and their key output (don't just write "tested"):

```bash
# example
./scripts/ci_gate.sh
python -m pytest -m "not network"
```

> The `Full-suite note` must be consistent with the current Head CI status of the PR. If a local run has environment-specific failures, mark it clearly and provide the GitHub CI conclusion and link.
> Avoid keeping unrelated historical failure descriptions; report based on current results only.
> If previous runs have failure logs, update them to match the current Head CI.
> If the `Full-suite note` contradicts the current Head CI, please update the PR body before submitting.

- Complete the fields below in accordance with the `Full-suite note` (any omitted item is considered missing information):
  - ai-governance: `pass` / `fail`, with link
  - backend-gate: `pass` / `fail`, with link
  - docker-build: `pass` / `fail`, with link
  - web-gate: `pass` / `fail`, with link
  - If this PR modifies workflow template files like `.github/PULL_REQUEST_TEMPLATE.md`, explain the necessity, boundaries, and rollback (default: `revert this PR`); otherwise, split it into a separate chore PR.

Key output & conclusion:

- [Required] Current Head CI: `ai-governance:pass / backend-gate:pass / docker-build:pass / web-gate:pass` (replace with actual results) and link.
- If you need to keep local failure logs, specify "local environment differences + current CI pass/fail + CI link".
- If all passed, add: `Current status: all passed (pass)` and ensure Head CI is all pass.
- Suggest pasting this to the top of your PR body: `Current Head CI: ai-governance:pass / backend-gate:pass / docker-build:pass / web-gate:pass` (example only, replace with actual).

> If these checks conflict with the PR body, update the PR description to avoid review blocks.

## Visual Evidence (if applicable)

[Required] If this PR changes report formatting, report rendering, or Web UI, attach screenshots of the affected report/page here; before/after screenshots are preferred when relevant. Issue/PR process screenshots, review screenshots, one-off acceptance screenshots, and temporary visual evidence should be linked from the PR body/comments, GitHub attachments, Actions artifacts, or external accessible evidence; do not commit them as repository files.

> If screenshots cannot be provided, state the alternative evidence (such as Playwright/e2e artifact path, review links) and their query commands. Do not leave blank. For Web settings/report rendering changes, ensure evidence points directly to the changed sections.
>
> If this PR modifies the Web UI, provide at least one reproducible path:
>
> - Playwright screenshots: `apps/dsa-web/e2e/smoke.spec.ts` (`cd apps/dsa-web && npx playwright test e2e/smoke.spec.ts --grep "settings page renders title and save actions after login"`)
> - Review links: Actions artifacts, GitHub comment attachments, or external links.

> Alternative evidence template (recommended for settings page changes):
> - Command: `cd apps/dsa-web && npx playwright test e2e/smoke.spec.ts --grep "settings page"`
> - Artifact path: `apps/dsa-web/test-results/**/smoke-settings-page-*.png`
> - Description: Screenshots should show the changed settings items (fields, labels, help text)

- Screenshot links (required for Web UI/report changes; if not provided, explain in the "Reason if not applicable" section below with alternative evidence):
- Settings page recommended names: `smoke-settings-page-zh` / `smoke-settings-page-en`
- Before & After (if applicable):
- Settings field description: Screenshots or artifacts must clearly show the `MARKET_REVIEW_REGION` field and its help text (Chinese/English).
- Reason if not applicable (if no screenshots are attached, this must be filled with reproducible evidence and commands):
  - Playwright command (when no screenshots): `cd apps/dsa-web && npx playwright test e2e/smoke.spec.ts --grep "settings page"`
  - Artifact path (when no screenshots): `apps/dsa-web/test-results/**/smoke-settings-page-*.png`
  - Description: Screenshots (or artifacts) must show the modified setting fields and help text.

> If this PR changes Web settings fields (labels or help text), screenshots or alternative evidence must locate the setting area and trace back to the changes; this field is required.
> If this PR changes Web UI or report rendering and screenshots are not available, the reason section must provide reproducible alternative evidence (such as Playwright paths and commands). Do not leave blank.

## Compatibility And Risk

Describe compatibility impact and potential risks (write `None` if not applicable).

- If this PR changes third-party model/API compatibility, request parameters, routing prefixes, or provider fallback behavior, include an official source link or announcement and clarify whether the rule is permanent, runtime-specific, or a temporary compatibility workaround.
- If this PR does not touch third-party models/APIs, provider/model/base URL, or runtime config cleanup/migration, confirm with:
  `This PR does not change provider/model/base URL, runtime config cleanup/migration semantics; historical config remains unchanged; rollback method is revert.`
- If this PR changes `.github/PULL_REQUEST_TEMPLATE.md` or other PR workflow template files, specify: only affects collaboration workflow and templates (no runtime changes), rollback is revert, and mention any CI/checklist impact.
- If this PR depends on a specific runtime or pinned dependency window (for example a LiteLLM version range, OpenAI-compatible routing, or YAML alias behavior), state the compatibility window you verified and which code paths were covered.
- If this PR touches runtime config save/cleanup/migration/backfill logic, explicitly describe whether existing config is rewritten, cleared, migrated, or left intact, and how users can restore the previous behavior.
- If this PR does not touch provider/model/base URL or config cleanup/migration (this item is only a statement), specify: `This PR does not change provider/model/base URL, runtime config cleanup/migration semantics; historical config remains unchanged; rollback method is revert.`

## Rollback Plan

Provide at least one actionable rollback step (required).

- For compatibility fixes, include the minimal rollback path (for example `revert this PR`) and whether any additional config or data rollback is required.

## EXTRACT_PROMPT Change (if applicable)

If this PR changes `EXTRACT_PROMPT` in `src/services/image_stock_extractor.py`, paste the full updated prompt here:

<details>
<summary>Expand: Full EXTRACT_PROMPT</summary>

```
(paste full prompt here)
```

</details>

## Checklist

- [ ] This PR has a clear motivation and value
- [ ] Reproducible verification commands and results are included
- [ ] Compatibility and risk have been assessed
- [ ] A rollback plan is provided
- [ ] If report formatting or Web UI changed, affected report/page screenshots are linked in the PR body/comments and one-off acceptance screenshots are not committed as repository files
- [ ] If Web settings fields changed (labels or help text), screenshots of the settings page are required; if unavailable, provide alternative visual evidence with command + artifact path that points to the changed item.
- [ ] If user-visible changes are included, relevant docs and `docs/CHANGELOG.md` are updated; `README.md` is updated only for homepage-level changes, with details kept in `docs/*.md`
