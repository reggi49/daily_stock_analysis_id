# Run Diagnostics & Data Reliability 1.0 (Phase 0)

This document defines **Phase 0 (P0)** for #1391: without introducing new pages, changing the global analysis strategy, or altering fallback core semantics, it converges contract boundaries and scopes the runtime fix range for this round.

## Goals

- Provide unified terminology for subsequent implementation: `trace_id`, critical path records, diagnostic summaries, sanitized troubleshooting info.
- Define Phase 1 scope to avoid expanding the requirement into a "full observability platform."
- Solidify fail-open, security, and retention baselines to reduce regression risk.

## Current Document Scope (This Round)

- This file is the Phase 0 contract and acceptance boundary document. The current PR covers docs + runtime fix; this round also completes the A-share code attribution boundary for `baostock_fetcher.py`, `pytdx_fetcher.py`, and `tushare_fetcher.py`, with regression verification via `tests/test_a_share_fetcher_code_conversion.py`.
- Attribution boundaries must cover bare codes and prefix codes (e.g., `000001`, `000001.SZ`, `SH000001`, `SH.000001`, `SZ000001`, `SZ.000001`), avoiding misclassification of SH/SZ prefix semantics.
- Unless new LLM provider/model/Base URL semantic migration is required, this round narrows the Tushare A-share attribution scope to: `600/601/603/605/688`, `000/001/002/003/300/301`, with regression for `605`, `001`, `003`, and `301` scenarios; this scope change is not treated as a provider configuration/routing strategy expansion.

## Non-Goals

- Not building an OpenTelemetry / APM / Grafana-style monitoring system.
- Not displaying p95, full Provider call details, or a complete operations panel in the first version.
- Not changing existing data source priorities, analysis strategies, or notification strategies.
- Not modifying the LLM provider list, Base URL, `llm_call` runtime parameters, or `REPORT_*` configuration semantics and migration paths; this round's changes are limited to A-share code attribution parsing and diagnostic field boundaries.

### Acceptance Boundaries (This Round)

- This round is a `fix` (docs + runtime fix); changes only converge A-share code attribution semantics, not modifying provider lists, Base URL, `llm_call` runtime semantics, or `REPORT_*` configuration migration paths.
- `data_provider/baostock_fetcher.py`, `data_provider/pytdx_fetcher.py`, `data_provider/tushare_fetcher.py` handle only the following this round:
  - Bare codes and suffix codes: `000001`, `000001.SH`, `000001.SZ`
  - Prefix codes: `SH000001`, `SH.000001`, `SZ000001`, `SZ.000001`
- `SH000001`/`SH.000001`/`SZ000001`/`SZ.000001` scenarios are correctness blockers that must be covered by `tests/test_a_share_fetcher_code_conversion.py` regression tests.
- Minimum regression scope: `python -m pytest tests/test_a_share_fetcher_code_conversion.py` and `./scripts/ci_gate.sh`, with results and blockers synced in the PR description.
- Rollback priority is to restore the three file changes to the pre-merge commit; other scopes should not be rolled back together.

## Terminology & Contracts (P0 Draft)

### 1) `trace_id`

- Meaning: A unified correlation ID for a single analysis run.
- Requirements:
  - Each analysis task has only one `trace_id`.
  - Generated at the entry point, or mapped from an existing task ID (e.g., Web task).
  - Appears in logs/structured diagnostics for troubleshooting correlation.

### 2) `RunDiagnosticSummary`

- Meaning: A brief run diagnostic summary for user consumption.
- Suggested fields (minimal for v1):
  - `trace_id`
  - `status`: `ok` / `degraded` / `failed`
  - `data_status`: Whether critical data paths are degraded
  - `notify_status`: Notification result summary
  - `error_hint`: Sanitized brief cause
- Note: This is a user-facing capability, not equivalent to a full internal event log.

### 3) Critical Path Records (Minimal Set)

v1 only requires recording the following key node results (success/failure/degradation + brief cause):

- `realtime_quote`
- `daily_data`
- `llm_call`
- `report_persist`
- `notification_dispatch`

> Note: `news`, `fundamental`, `capital_flow`, etc. are deferred to subsequent expansions and are not blocking items for v1.

## Security & Stability Boundaries (P0 Must-Comply)

### Fail-Open

- Diagnostic record failures should not block the main analysis flow.
- Even if diagnostic writes fail, analysis results must still be produced (unless the main flow itself fails).

### Sanitization

- Copied troubleshooting info must not contain secrets, tokens, complete webhook URLs, or user account identifiers.
- Error message output should focus on summaries and avoid leaking raw sensitive text from third-party responses.

### Retention

- Diagnostic data retention should be configurable or uniformly cleanable.
- Default strategy should be conservative (e.g., only retain for a necessary time window) to avoid unbounded growth.

### Compatibility

- New fields should be appended by default, without breaking existing API / Web / Desktop read paths.
- Old history records missing new fields should safely fall back.

## Phase 0 Delivery Checklist

- [x] Goals/non-goals defined to prevent scope creep.
- [x] Minimal contract for `trace_id` and `RunDiagnosticSummary` defined.
- [x] Critical path coverage scope for v1 clarified.
- [x] Fail-open, sanitization, retention, and compatibility baselines solidified.

## Future Phases (Description Only, Not Implemented in P0)

- Phase 1: `trace_id` integration and minimal critical path record implementation.
- Phase 2: Generate and persist `RunDiagnosticSummary`, with copyable sanitized troubleshooting info.
- Phase 3: Minimal Web-side display (collapsed by default), with documentation and rollback notes.
