# DecisionSignal Topic

This page consolidates #1390 P7, explaining how DSA distills AI recommendations from individual stock analysis, Agent, alerts, and portfolio risk into queryable, feedback-capable, post-hoc evaluable `DecisionSignal` assets. It is a structured index above reports, not a replacement for Markdown reports, `operation_advice`, three-state `decision_type`, alert rules, or real trading systems.

## Capability Boundaries

- `DecisionSignal` only records recommendations, evidence summaries, risks, observation conditions, lifecycle, and source; it does not execute orders or portfolio adjustments.
- Write failures, extraction failures, alert signal association failures, and notification delivery failures do not block the main analysis, alert triggering, or report saving.
- P7 does not add new API endpoints, database fields, environment variables, config registry entries, or `.env.example` content.
- There are currently no `DECISION_SIGNAL_*` toggles; signal functionality is disabled or rolled back by reverting the corresponding code.

## Fields and Enums

Core fields are defined in `api/v1/schemas/decision_signals.py`, including:

- Identity and source: `stock_code`, `stock_name`, `market`, `source_type`, `source_agent`, `source_report_id`, `trace_id`, `trigger_source`.
- Recommendation semantics: `action`, `action_label`, `confidence`, `score`, `horizon`, `market_phase`, `plan_quality`, `status`.
- Plan and explanation: `entry_low`, `entry_high`, `stop_loss`, `target_price`, `invalidation`, `watch_conditions`, `reason`, `risk_summary`, `catalyst_summary`.
- Evidence and quality: `evidence`, `data_quality_summary`, `metadata`.
- Lifecycle: `expires_at`, `created_at`, `updated_at`.

Enum values:

| Field | Values |
| --- | --- |
| `market` | `cn`, `hk`, `us`, `jp`, `kr`, `tw` |
| `source_type` | `analysis`, `agent`, `alert`, `market_review`, `manual` |
| `market_phase` | `premarket`, `intraday`, `lunch_break`, `closing_auction`, `postmarket`, `non_trading`, `unknown` |
| `action` | `buy`, `add`, `hold`, `reduce`, `sell`, `watch`, `avoid`, `alert` |
| `horizon` | `intraday`, `1d`, `3d`, `5d`, `10d`, `swing`, `long` |
| `plan_quality` | `complete`, `partial`, `minimal`, `unknown` |
| `status` | `active`, `expired`, `invalidated`, `closed`, `archived` |

Web display must map these wire values to user-readable labels in the current UI language; API responses continue to preserve the original enum values.

## Canonical Scoring and Action Calibration

Individual stock analysis, technical scoring fallback, report display fallback, and `DecisionSignal` extraction share the `decision-scale-v1` calibration. `decision_type` retains only `buy|hold|sell` for compatibility statistics; the more granular eight-state `action` is the authoritative field.

- User-visible fields have two categories: `operation_advice` preserves the text calibration (e.g., "hold and observe"), while `action` serves as the unified eight-state decision calibration (e.g., `hold/watch/reduce`) for risk control, backtesting, and list display. Newly generated or final saved reports should prefer consistency between the two; for historical records or payloads with semantic conflicts, `action` is the priority field for list, backtesting, DecisionSignal, and other structured displays, with `operation_advice` retained as explanatory text.

| score | signal key | `action` | legacy `decision_type` | semantics |
| --- | --- | --- | --- | --- |
| 80-100 | `strong_buy` | `buy` | `buy` | Strong buy, high-conviction opportunity, executable buy/add plan |
| 60-79 | `buy` | `buy` | `buy` | Positive opportunity, minor pending confirmations allowed |
| 40-59 | `watch` | `watch` | `hold` | Signal divergence or insufficient confirmation, wait for trigger conditions |
| 20-39 | `reduce` | `reduce` | `sell` | Risk notably elevated, prioritize reducing exposure |
| 0-19 | `sell` | `sell` | `sell` | Trend or risk significantly deteriorated, prioritize exit |

If `score >= 60` but the final `action` is `hold/watch`, or `score < 40` but the final `action` is still `hold/watch`, there must be an explicit guardrail explanation, such as `dashboard.decision_stability.reason`, `dashboard.decision_score_calibration.guardrail_reason`, or `metadata.guardrail_reason`. Risk control degradation preserves `raw_score`, `adjusted_score`, `raw_action`, `final_action`, and the reason; neutral actions without an explicit reason are aligned to `buy/reduce/sell` by canonical score during DecisionSignal extraction.

## Lifecycle, Deduplication, and State

`src/services/decision_signal_service.py` is the main entry point for signal lifecycle:

- When `horizon` and `expires_at` are explicitly provided, they take priority.
- When `horizon` is not provided, `alert` or pre-market/intraday/lunch-break/closing-auction phases default to `intraday`; post-market, non-trading, unknown phase, or missing phase defaults to `3d`.
- `intraday` expiration time first reads low-sensitivity `metadata.market_phase_summary.minutes_to_close/minutes_to_open`; when missing, falls back to market TTL.
- `expired`, `invalidated`, `closed`, `archived` cannot be directly restored to `active` via `PATCH /status`.
- Same-source deduplication prefers `(source_report_id, source_type, market, stock_code, action, horizon, market_phase)`; when no report but `trace_id` is available, uses the trace dimension.
- New opposite active signals mark old active signals as `invalidated` and write the invalidation source into metadata.

## API

Current public endpoints are documented in `api/v1/endpoints/decision_signals.py` and `docs/architecture/api_spec.json`:

- `POST /api/v1/decision-signals`: Create or deduplicate by same-source key, returns `{ item, created }`.
- `GET /api/v1/decision-signals`: Paginated query, supports market, stock, action, phase, source, status, time range, and holding filters.
- `GET /api/v1/decision-signals/{signal_id}`: Query single record.
- `PATCH /api/v1/decision-signals/{signal_id}/status`: Update status and optional metadata.
- `GET /api/v1/decision-signals/latest/{stock_code}`: Query latest active signal for a stock.
- `POST /api/v1/decision-signals/outcomes/run`: Explicitly trigger post-hoc evaluation.
- `GET /api/v1/decision-signals/outcomes`, `GET /api/v1/decision-signals/outcomes/stats`, `GET /api/v1/decision-signals/{signal_id}/outcomes`: Query post-hoc results and statistics.
- `GET/PUT /api/v1/decision-signals/{signal_id}/feedback`: Query or write useful / not useful feedback.
- `POST /api/v1/decision-signals/reassess`: Preview signals under different decision styles based on source historical reports; does not persist.

These endpoints inherit existing `/api/v1/*` admin authentication; when `ADMIN_AUTH_ENABLED=true`, a valid admin session cookie is required.

## Reassess Preview

The first version of `reassess` only does preview, and does not create or update `DecisionSignal`.

Requests only support:

```json
{
  "source_report_id": 123,
  "decision_profile": "aggressive",
  "persist": false
}
```

Contract boundaries:

- `source_report_id` is the sole source of truth; reassessment only reads the corresponding persisted historical report snapshot.
- Does not support `signal_id`, and does not accept client-submitted `action`, `score`, `confidence`, prices, metadata, or guardrail results; extra fields are rejected by request validation.
- `persist=true` currently always returns HTTP 400 with error code `unsupported_operation`. Saving reassessment results depends on future fieldification of the `decision_profile` field.
- Reassessment does not silently fetch realtime quotes, nor does it use current market data to fill historical snapshots.
- When the historical report does not exist, is not an individual stock report, or the snapshot lacks structured decision inputs, explicit errors are returned.
- Data quality is normalized to `high`, `medium`, `low`, `poor`, `unknown`; guardrail only uses the normalized level.
- `guardrail_result` is machine audit data recording raw/final action, pass/fail, violations, and adjustments; `warnings` is a user-readable summary; tests and client logic should prefer the stable `code`.
- Blocked previews still return HTTP 200; the UI must prominently display `blocked_reason` and not treat it as an ordinary executable signal.
- `aggressive` is not model sampling temperature semantics and does not auto-generate three profile sets of signals.

## Web Display

The Web entry point is at `/decision-signals`:

- Default query is `status=active`.
- The top of the page provides a page-level "Current Stock" primary path, independent of the advanced list filter. After the user submits a primary stock, selects an autocomplete candidate, or clicks a candidate chip, the latest active and timeline share the same applied stock context; only modifying the input draft does not trigger latest or timeline queries.
- Current stock candidates prefer showing recently analyzed stocks; if no historical candidates exist, or historical candidate loading fails, fallback displays active high-popularity stocks from the stock index. Candidates only serve as manual click entry points and do not auto-submit queries on page load; when both historical and stock index are unavailable, only a no-candidate fallback message is shown.
- The current stock context displays the applied code, name, and derivable market, with a clear entry point. Clearing returns latest and timeline to the guided state and does not affect advanced list filtering or list source detail drawers.
- Supports advanced list filtering by market, stock code, action, market phase, source, source report ID, and status; these filters are not equivalent to the current stock context and do not pollute the latest active query.
- Single stock signal timeline reuses the existing `GET /api/v1/decision-signals` list API without adding a new timeline endpoint. The timeline requires applying a non-empty current stock before querying; without a current stock, only the guided state is shown without fetching market-only or global timelines.
- Timeline only supports `30d`, `90d`, `180d` time ranges, defaulting to `90d`; up to 100 records per request. When `total > items.length`, Web displays "Showing only the latest 100 signals; narrow the time range" to avoid silently showing incomplete trajectories.
- Timeline filters maintain independent market, range, status forms and query button. When selecting a new current stock, if the market is derivable, the timeline market is initialized for this one selection only; the user can manually change the market later, and queries use the form snapshot at button submission time.
- Timeline status filter only supports `all` and `active`: `all` does not pass `status`, `active` passes `status=active`. P1 does not provide terminal status filtering or frontend terminal filtering.
- Signal performance statistics maintain the global reviewed-outcome calibration, which is not equal to the currently visible signal count and does not change with current stock or advanced list filter; when reviewed sample count is 0, Web displays a zero-sample empty state rather than a set of `0/-` metrics.
- P1 does not provide profile filter; `decision_profile` still only exists in metadata and cannot be reliably filtered server-side. Historical signals with missing or invalid profiles display as `unknown` in Web, not mislabeled as `balanced`.
- Market filter in API / service layer and Web frontend all support `cn/hk/us/jp/kr/tw`; `jp/kr/tw` frontend localization labels are complete, `tw` signals can be written via API, queried by `market=tw`, and selected via market filter on the Web DecisionSignal page (Taiwan stocks (tw)); alert (market light) market supports `cn/hk/us/jp/kr`.
- Detail drawer displays action, status, score, confidence, horizon, plan quality, market phase, price plan, risk, observation conditions, evidence, data quality, and metadata.
- Detail drawer or page context with an existing source report ID can initiate reassess preview; when no available source report ID, the entry is disabled. Preview does not add to list, latest, or timeline, and does not provide a save button.
- Web can only mark signals as `closed`, `invalidated`, or `archived`; does not provide terminal state restoration to active.
- Historical report details no longer embed display of report-bound `source_type=analysis` signals, nor do they trigger `source_report_id` signal queries when opening report details; to view report source signals, use the `/decision-signals` page with precise source report ID filtering, or open the deep link `/decision-signals?sourceReportId=<recordId>`. This filter and deep link use the precise `source_type=analysis + source_report_id` query to preserve the legacy report best-effort lazy backfill entry point.
- Portfolio page asynchronously queries each unique holding's latest active signal; single query failure only shows a degraded message and does not block the portfolio snapshot or other holding signals.

All user-visible enums must use i18n labels; technical IDs, stock codes, API field names, env keys, and URL examples may remain in English.

## Decision Profile Metadata

P1 auto-generated `source_type=analysis` signals write default decision style metadata into metadata:

- `decision_profile=balanced`
- `profile_source=auto_default`: Normal new analysis generation path.
- `profile_source=backfill_defaulted`: Historical report lazy backfill path.
- `profile_policy_version=decision-profile-v1`
- `signal_generation_version=legacy-report-extractor-v1`
- `decision_signal_metadata_version=decision-signal-metadata-v1`

`profile_policy_version` only represents the default profile metadata contract version and does not imply an implemented independent profile policy engine, scoring engine, or multi-profile generation. P1/P2 does not write `scoring_version` or `scoring_breakdown`; if these fields are needed, they should be defined by subsequent reassess / scoring issues.

## Alerts, Notifications, and Portfolio Risk

- Real stock-level alert triggers prefer associating the same target's latest active signal and writing a low-sensitivity `decision_signal_summary` into `alert_triggers.diagnostics`.
- When no active signal exists, the alert worker only creates a minimal `source_type=alert/action=alert` signal.
- Alert signal `trace_id=alert-rule-<hash>` is only for same-source retry best-effort deduplication and does not overwrite the active signal itself.
- Notifications only reference public summary fields: `action`, `horizon`, `reason`, `watch_conditions`, `risk_summary`, `source_report_id`.
- Notifications must not output signal `metadata`, `evidence`, raw diagnostics, webhook URL, token, or cookie.
- `GET /api/v1/portfolio/risk` `decision_signal_risk` only counts current holdings' active `sell/reduce/alert` signals; query failure uses fail-open.

For more alert and notification details, see `docs/alerts.md` and `docs/notifications.md`.

## Post-hoc Evaluation and Feedback

P5 saves user feedback and post-hoc results via sidecar tables, without extending the `decision_signals` main table:

- `decision_signal_feedback` saves each signal's latest `useful|not_useful` feedback, optional reason/notes, and source.
- `decision_signal_outcomes` idempotently saves post-hoc evaluation results by `(signal_id, horizon, engine_version)`.
- Current `engine_version=decision-signal-v1`.
- Post-hoc evaluation only supports daily-data-verifiable `1d/3d/5d/10d`; `intraday/swing/long`, non-directional actions, missing prices, and insufficient forward bars write `eval_status=unable` with explicit `unable_reason`.
- During evaluation, action, market, market_phase, source_type, source_agent, plan_quality, data_quality_level, and holding_state statistical dimensions are frozen; historical statistics do not depend on subsequent live joins.

## Sanitization and Low-sensitivity Boundaries

Signal writes and status updates use `sanitize_decision_signal_text()` and `sanitize_decision_signal_payload()` from `src/utils/sanitize.py`:

- Text fields, JSON fields, and display short text are sanitized before writing.
- Covers sensitive keys, Bearer, Authorization/Cookie header or assignment, token-like strings, webhook URLs, URL userinfo, and URLs with sensitive query/fragment parameters.
- Ordinary evidence URLs are preserved for source traceability.
- `trace_id` is a same-source deduplication identity field; if it contains a credential that would be sanitized, the API rejects the request rather than saving the redaction-broken identity value.
- Web JSON display only shows backend-sanitized data and should not reassemble raw diagnostics or configuration values.

P7's global acceptance confirms that the signal pool, notification summary, and Web display do not leak tokens, cookies, webhook URLs, API keys, email passwords, or other sensitive information.

## Migration and Rollback

This feature completed the required tables and sidecar structures in P1-P6; P7 adds no new migration.

Migration notes:

- After upgrade, no new `.env`, `.env.example`, or Web settings items are needed.
- Old historical reports are not batch backfilled. Only when explicitly calling the signal list endpoint or triggering a precise query `source_type=analysis + source_report_id` on the Web AI Recommendations page with no match will best-effort lazy backfill occur.
- Existing `decision_signals`, feedback, and outcome data remains compatible.

Rollback notes:

- There are currently no `DECISION_SIGNAL_*` toggles; the rollback method for disabling signal extraction/writing is to revert the corresponding code.
- After rollback, normal report saving, alert triggering, notification delivery, and portfolio risk main flow continue along existing paths.
- Rollback does not automatically delete historical `decision_signals`, `decision_signal_feedback`, or `decision_signal_outcomes` data; if cleanup is needed, the maintainer should develop a separate data cleanup strategy.
