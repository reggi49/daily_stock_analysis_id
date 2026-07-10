# AGENTS.md

This file governs the default development workflow for this repository. Its goal is to reduce redundant communication, minimize rework, and keep changes aligned with the current project structure.

If this file conflicts with the scripts, workflows, or actual code in the repository, treat the executable content as the source of truth, and fix the documentation in related changes to prevent rule drift.

## 1. Hard Rules

- Follow existing directory boundaries:
  - Backend logic goes in `src/`, `data_provider/`, `api/`, `bot/`
  - Web frontend changes go in `apps/dsa-web/`
  - Desktop changes go in `apps/dsa-desktop/`
  - Deployment and pipeline changes go in `scripts/`, `.github/workflows/`, `docker/`
- Do not run `git commit`, `git tag`, or `git push` without explicit confirmation.
- Commit messages must be in English; do not add `Co-Authored-By`.
- Do not hardcode secrets, credentials, paths, model names, ports, or environment-specific logic.
- Prefer reusing existing modules, configuration entry points, scripts, and tests over adding parallel implementations.
- Stability takes priority over "quick improvements" by default; refrain from refactoring, abstraction, or infrastructure migration not directly required by the current task.
- When adding new configuration items, you must also update `.env.example` and related documentation.
- When changes affect user-facing capabilities, CLI/API behavior, deployment methods, notification methods, or report structure, you must also update related documentation and `docs/CHANGELOG.md`.
- When modifying report format, report rendering, or the Web UI, the PR description must include screenshots of affected reports/pages. Before/after comparisons are preferred when differences exist. If screenshots are not possible, explain the reason and provide alternative visual evidence.
- Issue/PR process screenshots, review screenshots, one-time acceptance screenshots, and temporary visual evidence must not be committed as repository files. They should be placed in PR descriptions, PR comments, GitHub attachments, Actions artifacts, or externally accessible evidence links. Exceptions exist for diagrams that must be retained in long-term product documentation, but file names and document semantics must be detached from specific issue/PR numbers.
- The `[Unreleased]` section in `docs/CHANGELOG.md` uses a **flat format**: each entry on its own line, formatted as `- [type] description`, where type is one of: `New`/`Improvement`/`Fix`/`Docs`/`Test`/`chore`. **Do not add `### Category Headings` inside `[Unreleased]`** to reduce merge conflicts across concurrent PRs. The maintainer will consolidate entries into a titled format at release time.
- `README.md` is only for project positioning, core capability overview, quick start, main entry points, sponsorship/collaboration, and other homepage-level information. Avoid updating README unless necessary to prevent continuous bloat.
- For finer-grained module behavior, page interactions, specialized configuration, troubleshooting instructions, field contracts, implementation semantics, and edge cases, prefer updating the corresponding `docs/*.md` or specialized documentation instead of writing to README.
- When updating one language of the bilingual (Chinese/English) documentation, assess whether the other language needs to be updated as well. If not synchronized, document the reason in the delivery notes.
- Comments, docstrings, and log messages should prioritize clarity and accuracy. English is not strictly required, but should be consistent with the file context.

## 1.1 PR Title Convention (Non-blocking Recommendation)

- Use `<type>: <change description>` as the PR title format, e.g., `fix: fix market analysis history loss`. Preferred types are `fix`/`feat`/`refactor`/`docs`/`chore`/`test`/`ci`.
- The title should describe the actual change. Avoid adding `[codex]`, `codex`, `autocode`, `copilot`, or other tool/agent source prefixes.
- This convention is only for collaboration readability and consistency guidance; it should not be used as a standalone review process blocker.

## 1.2 Contribution Quality Baseline

- This repository does not accept PRs that substitute real design convergence with code volume stacking, diff surface expansion, or patch-style review responses.
- Contribution quality is measured by: whether it solves a clear problem, minimizes impact surface, maintains consistency with existing contracts, and covers real risk paths. It is not measured by new line count, file count, feature promotion, or "looks complete."
- Do not use this repository as a low-cost experimentation ground, resume showcase, or contribution farming venue. Every PR must demonstrate that the author understands the current system contracts and has completed basic self-review, integration, and verification.
- Using AI-assisted development is not inherently problematic. The problem is submitting AI-generated code without human semantic review, verification, or convergence. Such PRs will be treated as low-quality submissions.
- After review feedback, do not simply append local patches at the locations called out and claim "all fixed." The author must re-examine all entry points, configurations, tests, documentation, workflows, and user-facing paths affected by the same business semantic.
- If a PR continues to exhibit the same type of contract drift, repeated fallbacks, tests bypassing real risk layers, or PR body inconsistencies with the actual diff after multiple review rounds, maintainers may request the PR be closed and redone rather than continuing point-by-point review.

## 2. AI Collaboration Asset Governance

- `AGENTS.md` is the single source of truth for AI collaboration rules in this repository.
- `CLAUDE.md` must be a symlink to `AGENTS.md` for compatibility with the Claude ecosystem.
- `.github/copilot-instructions.md` and `.github/instructions/*.instructions.md` are mirrors or layered supplements for GitHub Copilot / Coding Agents. If they conflict with this file, `AGENTS.md` takes precedence.
- Repository collaboration skills are stored in `.claude/skills/`; analysis artifacts are stored in `.claude/reviews/`. The former may be committed; the latter are treated as local artifacts by default.
- The root `SKILL.md` and `docs/openclaw-skill-integration.md` are product or external integration documentation, not the source of truth for repository collaboration rules.
- If `.agents/skills/` or other agent-specific directories are added in the future, a single source of truth must be established first, then synchronized via scripts or mirrors. Long-term manual maintenance of multiple synonymous content sources is prohibited.
- When modifying AI collaboration governance assets, run:

```bash
python scripts/check_ai_assets.py
```

## 3. Repository Overview

- Project positioning: Intelligent stock analysis system covering A-shares, Hong Kong stocks, and US stocks.
- Main flow: Data fetching -> Technical analysis/News retrieval -> LLM analysis -> Report generation -> Notification delivery.
- Key entry points:
  - `main.py`: Main analysis task entry point
  - `server.py`: FastAPI server entry point
  - `apps/dsa-web/`: Web frontend
  - `apps/dsa-desktop/`: Electron desktop app
  - `.github/workflows/`: CI, releases, daily tasks
- Core responsibilities:
  - `src/core/`: Main flow orchestration
  - `src/services/`: Business service layer
  - `src/repositories/`: Data access layer
  - `src/reports/`: Report generation
  - `src/schemas/`: Schema / data structures
  - `data_provider/`: Multi-data-source adaptation and fallback
  - `api/`: FastAPI API
  - `bot/`: Bot integration
  - `scripts/`: Local scripts
  - `.github/scripts/`: GitHub automation scripts
  - `tests/`: pytest tests
  - `docs/`: Documentation and guides

## 4. Common Commands

### Running the Application

```bash
python main.py
python main.py --debug
python main.py --dry-run
python main.py --stocks 600519,hk00700,AAPL
python main.py --market-review
python main.py --schedule
python main.py --serve
python main.py --serve-only
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### Backend Verification

```bash
pip install -r requirements.txt
pip install flake8 pytest
./scripts/ci_gate.sh
python -m pytest -m "not network"
python -m py_compile <changed_python_files>
```

### Web / Desktop

```bash
cd apps/dsa-web
npm ci
npm run lint
npm run build

cd ../dsa-desktop
npm install
npm run build
```

### PR / CI Evidence

```bash
gh pr view <pr_number>
gh pr checks <pr_number>
gh run view <run_id> --log-failed
```

## 5. Default Workflow

1. Determine the task type: `fix / feat / refactor / docs / chore / test / review`
2. Read the existing implementation, configuration, tests, scripts, workflows, and documentation before making changes.
3. Identify the change boundary: Backend / API / Web / Desktop / Workflow / Docs / AI collaboration assets.
4. Assess whether the change hits high-risk areas: configuration semantics, API/Schema, data source fallback, report structure, authentication, scheduling, release process, desktop startup chain.
5. Make only the minimal changes directly related to the current task; do not bundle unrelated refactoring.
6. If documentation, scripts, or workflow descriptions are inconsistent, trust the actual code and workflows first, then decide whether to fix the documentation.
7. After changes, run the verification matrix below.
8. The final delivery should default to explaining:
   - What changed
   - Why this change was made
   - Verification status
   - Unverified items
   - Risk points
   - Rollback method

## 6. Verification Matrix

### CI Coverage Principles

The repository CI currently includes:

| Check Item | Source | Description | Blocking? |
| --- | --- | --- | --- |
| `ai-governance` | `.github/workflows/ci.yml` | Validates `AGENTS.md` / `CLAUDE.md` / `.github` instructions / `.claude/skills` relationships | Yes |
| `backend-gate` | `.github/workflows/ci.yml` | Runs `./scripts/ci_gate.sh` | Yes |
| `docker-build` | `.github/workflows/ci.yml` | Docker build and critical module import smoke test | Yes |
| `web-gate` | `.github/workflows/ci.yml` | Runs `npm run lint` + `npm run build` when frontend files change | Yes (when triggered) |
| `network-smoke` | `.github/workflows/network-smoke.yml` | `pytest -m network` + `scripts/test.sh quick` | No, observational |
| `pr-review` | `.github/workflows/pr-review.yml` | PR static checks + AI review + auto-labeling | No, supplementary |

If the PR already has corresponding CI results, you may reference the CI conclusions directly. If CI does not cover the changed areas, or there are significant differences between local and CI environments, supplementary explanation of local verification and gaps is required.

### By Change Area

- Python backend changes:
  - Scope: `main.py`, `src/`, `data_provider/`, `api/`, `bot/`, `tests/`
  - Preferred: `./scripts/ci_gate.sh`
  - Minimum: `python -m py_compile <changed_python_files>`
  - If it affects API, task orchestration, report generation, notification delivery, data source fallback, authentication, or scheduling, the delivery notes must state whether the corresponding paths were covered.

- Web frontend changes:
  - Scope: `apps/dsa-web/`
  - Default: `cd apps/dsa-web && npm ci && npm run lint && npm run build`
  - If it involves API integration, routing, state management, Markdown/chart rendering, or authentication state, the delivery notes must explicitly describe the integration surface and uncovered risks.

- Desktop changes:
  - Scope: `apps/dsa-desktop/`, `scripts/run-desktop.ps1`, `scripts/build-desktop*.ps1`, `scripts/build-*.sh`, `docs/desktop-package.md`
  - Default: Build Web first, then build Desktop
  - If platform limitations prevent full verification, explicitly state whether Web build artifacts, Electron builds, and Release workflow impacts were verified.

- API / Schema / Authentication linked changes:
  - Scope: `api/**`, `src/schemas/**`, `src/services/**`, `apps/dsa-web/**`, `apps/dsa-desktop/**`
  - At minimum, cover the corresponding backend verification + affected client build verification.
  - If it involves login, cookies, sessions, polling state, field additions/removals, or enum changes, you must explicitly describe the compatibility impact.

- Documentation and governance file changes:
  - Scope: `README.md`, `docs/**`, `AGENTS.md`, `.github/copilot-instructions.md`, `.github/instructions/**`, `.claude/skills/**`
  - Code testing is not mandatory.
  - Verify that commands, configuration items, file names, and workflow names are consistent with the actual repository.
  - When modifying AI collaboration governance assets, run `python scripts/check_ai_assets.py`.

- Workflow / Script / Docker changes:
  - Scope: `.github/**`, `scripts/**`, `docker/**`
  - Run the local verification closest to the change area.
  - When delivering, state which pipeline, release path, or deployment path is affected.
  - If Docker / GitHub Actions related verification was not performed, explicitly state the reason and potential risks.

- Network or third-party dependency changes:
  - Run offline or deterministic checks first.
  - Prioritize verifying that timeout, retry, fallback, error messages, and degradation paths still hold.
  - If online verification was not performed, you must explicitly state the reason.

## 7. Stability Guardrails

- Configuration and runtime entry points:
  - When modifying `.env` semantics, defaults, CLI parameters, service startup methods, or scheduling semantics, simultaneously evaluate the impact on local runs, Docker, GitHub Actions, API, Web, and Desktop.
  - New configurations should default to "runnable without configuration, enhanced with configuration," avoiding layered switches and mutually exclusive modes.

- Data sources and fallback:
  - When modifying `data_provider/`, pay attention to data source priority, failure degradation, field standardization, caching, and timeout strategies.
  - A single data source failure should not bring down the entire analysis flow, unless the requirement explicitly demands fail-fast.

- API / Web / Desktop compatibility:
  - When modifying API / Schema / authentication / report payloads, simultaneously check backend, Web, and Desktop compatibility.
  - Default to appending fields, preserving old fields, or providing a compatibility layer to avoid breaking existing clients without notice.

- Reports / Prompts / Notifications:
  - When modifying report structure, prompts, extractors, notification templates, or bot pipelines, check whether upstream inputs and downstream consumers remain compatible.
  - A single notification channel failure should not bring down the entire analysis main flow, unless the requirement explicitly demands fail-fast.
  - When modifying `EXTRACT_PROMPT` in `src/services/image_stock_extractor.py`, include the full updated prompt in the PR description.

- Workflow / Release / Packaging:
  - When modifying auto-tagging, Release, Docker publishing, daily analysis, or desktop packaging flows, evaluate trigger conditions, artifact paths, permission boundaries, and rollback methods.
  - Auto-tagging defaults to opt-in: version number updates are only triggered when the commit title contains `#patch`, `#minor`, or `#major`, unless the requirement explicitly changes the release strategy.

## 8. Issue / PR / Skill Workflow

- The repository already has the following skills that can be prioritized for reuse:
  - `.claude/skills/analyze-issue/SKILL.md`
  - `.claude/skills/analyze-pr/SKILL.md`
  - `.claude/skills/fix-issue/SKILL.md`
- If the task is clearly issue analysis, PR review, or issue fixing, prioritize executing the corresponding skill and save artifacts to `.claude/reviews/`.
- Commands, templates, verification order, and delivery structure in skills must be consistent with `AGENTS.md`.
- Before any PR creation/update, PR review, or issue analysis, you must sync to the latest code baseline: check workspace status and run `git fetch --all --prune`; if the workspace is clean and the current branch can be fast-forwarded, run `git pull --ff-only`. If there are local changes, conflicts, untracked risk files, or the branch cannot be fast-forwarded, do not force branch switching, stashing, resetting, or overwriting local state. PR review / issue analysis may use the already-fetched remote refs/PR head for analysis, and the analysis document must clearly record the reason for not updating the local working tree, the current local HEAD, and the remote baseline used. PR creation/update should first describe the difference between the current branch and the target baseline, and request user confirmation for rebase, merge, or continuing on the current branch when necessary.
- Skills default to reading CI / workflow evidence first, then deciding whether to supplement with local verification.
- Aside from the safe fast-forward sync for PR creation/update, PR review / issue analysis described above, skills must not default to running `git pull`, `git push`, `git tag`, `gh pr create`, or other operations that change remote or current branch state. These operations must require user confirmation.
- PR review default order:
  1. Necessity
  2. Relevance
  3. Title suggestion (`<type>: <change description>`, without tool/agent prefixes; not a hard blocking item)
  4. Description completeness (against `.github/PULL_REQUEST_TEMPLATE.md`)
  5. Verification evidence
  6. Implementation correctness
  7. Merge decision
- For `fix` type PRs, you must explain: original problem, root cause, fix point, and regression risk.
- Merge blocking conditions:
  - Correctness or security issues
  - Blocking CI failures
  - PR description materially contradicts the actual changes
  - Missing rollback plan
  - Recurring un-converged contract drift, patch stacking, or verification evidence distortion

## 8.1 Review Feedback Handling and Patch Stacking Prohibition

When handling review feedback, appending local patches only at the locations called out by the reviewer and claiming "all fixed" is prohibited. You must first re-understand the business contracts pointed out by the reviewer, then check all entry points, configurations, tests, documentation, workflows, and user-facing paths affected by the same semantic.

After receiving review feedback, you must follow this order:

1. List each original issue raised by the reviewer.
2. Explain the root cause, not just describe "which lines were changed."
3. Identify all related paths affected by the same semantic, e.g., runtime, API/Web, CLI, diagnostics, workflow, docs, tests.
4. Fix the complete contract, not just the currently failing test or the currently commented line.
5. Add regression tests covering the reviewer's counter-examples, final entry verification, or explicitly explain why verification is not possible.
6. Simultaneously update the PR body to ensure scope, verification results, compatibility, risks, and rollback plan are consistent with the current HEAD.

If you cannot achieve the above convergence, do not continue stacking patches and do not claim ready for merge. You should proactively explain that the current PR needs to be split, closed and redone, or request maintainer confirmation of a new minimal scope.

The following behaviors will be treated as low-quality PRs:

- Using broad fallback, silent degradation, or `return False/None/[]` to obscure unclear contracts.
- Mocking out real risk layers in tests, only proving partial implementation passes.
- Claiming the issue is closed after CI passes, without covering the reviewer's counter-examples.
- PR body is inconsistent with the actual diff, verification results, or compatibility risks.
- Continuing to append scattered patches after review instead of re-converging complete semantics.
- The same business semantic appears inconsistently across runtime, Web/API, docs, workflow, and tests.

CI passing only indicates automated checks passed; it cannot substitute for human semantic convergence, nor can it alone prove that the reviewer's counter-examples have been closed.

## 9. Delivery and Release

- Default delivery structure:
  - `What changed`
  - `Why this change was made`
  - `Verification status`
  - `Unverified items`
  - `Risk points`
  - `Rollback method`
- For `docs` tasks, you may write: `Docs only, tests not run`, but you still need to state whether commands and file names were verified.
- Auto-tagging does not trigger by default; version number updates are only triggered when the commit title contains `#patch`, `#minor`, or `#major`.
- Manual tagging must use annotated tags.
- User-visible changes should be merged via PR by default, with labels and verification notes completed.
