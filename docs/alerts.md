# Real-Time Alert Center

This document records the operational baseline, data contracts, phased implementation scope, and compatibility boundaries for the Alert Center (Issue #1202).

## Current Baseline

Current runtime alerts are orchestrated by the background worker in `src/services/alert_worker.py`, with rule evaluation reusing the EventMonitor rule model in `src/services/alert_service.py` and `src/agent/events.py`.

- Configuration entry points: `AGENT_EVENT_MONITOR_ENABLED`, `AGENT_EVENT_MONITOR_INTERVAL_MINUTES`, `AGENT_EVENT_ALERT_RULES_JSON`.
- Runtime entry point: `main.py` registers the `agent_event_monitor` background task in schedule mode; the background worker reads persisted active rules each cycle and continues to support legacy `AGENT_EVENT_ALERT_RULES_JSON`.
- Notification delivery: After triggering, `NotificationService.send(..., route_type="alert")` is reused, continuing to follow the notification gateway's alert routing configuration.
- Web/System configuration validation: `src/services/system_config_service.py` performs JSON and rule semantic validation on `AGENT_EVENT_ALERT_RULES_JSON`.

The current runtime supports three rule types:

| `alert_type` | Direction Field | Threshold Field | Current Semantics |
| --- | --- | --- | --- |
| `price_cross` | `direction`: `above` / `below` | `price` | Real-time price crosses above or below a fixed price |
| `price_change_percent` | `direction`: `up` / `down` | `change_pct` | Real-time price change reaches a specified percentage |
| `volume_spike` | - | `multiplier` | Latest volume exceeds a specified multiple of the 20-day average |

`sentiment_shift`, `risk_flag`, `custom` and similar types are reserved for future expansion; the current runtime does not accept these types as executable rules.

## Legacy Configuration Compatibility

`AGENT_EVENT_ALERT_RULES_JSON` continues to be retained as a legacy runtime rule source and is not automatically migrated, deleted, overwritten, or rewritten from existing user `.env` / Web configurations.

- An empty string or empty array indicates no legacy rules are configured; schedule mode still registers the background worker so that persisted active rules created via the API can be evaluated without a restart.
- Strict validation is performed when saving Web/System configurations; invalid JSON, missing fields, illegal direction, illegal threshold, or unsupported rule type should return a configuration error.
- During runtime loading, a single invalid rule is skipped; remaining valid rules continue to work, preventing a single misconfiguration from breaking the entire schedule process.
- The current worker uses an in-process fingerprint to prevent repeated push notifications for continuous trigger conditions; this is not the Alert Center's cooldown model and does not provide cross-process or post-restart cooldown state.

## Data Contracts

The following contracts are used to align subsequent P1+ API, worker, Web, and storage implementations. P0 only defines field and semantic boundaries and does not imply that these persisted entities currently exist.

### `alert_rule`

A manageable alert rule.

| Field | Description |
| --- | --- |
| `id` | Rule ID; legacy JSON rules do not have a persisted ID in P0 |
| `name` | User-readable name; can be generated from rule type and target if not provided |
| `target_scope` | Target scope, e.g., single symbol, watchlist, portfolio, market |
| `target` | Target ticker or target reference, e.g., stock code, watchlist ID, portfolio ID |
| `alert_type` | Rule type; P1 initially only allows `price_cross`, `price_change_percent`, `volume_spike` |
| `parameters` | Rule parameters, e.g., `direction`, `price`, `change_pct`, `multiplier` |
| `severity` | Alert severity, e.g., info, warning, critical |
| `enabled` | Whether enabled |
| `cooldown_policy` | Cooldown policy; P0 only defines the field, execution semantics come in P4 |
| `notification_policy` | Notification policy; defaults to reusing `NotificationService`'s alert routing |
| `source` | Creation source, e.g., legacy_env, web, api, import |
| `created_at` / `updated_at` | Creation and update timestamps |

### `alert_trigger`

A real or recordable rule trigger event.

| Field | Description |
| --- | --- |
| `id` | Trigger record ID |
| `rule_id` | Corresponding rule ID; legacy env rules may record a temporary reference |
| `target` | Actual triggered target |
| `observed_value` | Observed value, e.g., current price, price change percentage, volume multiplier |
| `threshold` | Trigger threshold |
| `reason` | Human-readable trigger reason |
| `data_source` | Data source or provider |
| `data_timestamp` | Data timestamp; must not be fabricated as current time when missing |
| `triggered_at` | Trigger timestamp |
| `status` | Trigger status, e.g., triggered, skipped, degraded, failed |
| `diagnostics` | Sanitized diagnostic information |

### `alert_notification`

A notification attempt corresponding to a trigger.

| Field | Description |
| --- | --- |
| `id` | Notification attempt ID |
| `trigger_id` | Corresponding trigger record ID |
| `channel` | Notification channel |
| `attempt` | Attempt number |
| `success` | Whether successful |
| `error_code` | Structured error code |
| `retryable` | Whether retry is recommended |
| `latency_ms` | Elapsed time |
| `diagnostics` | Sanitized delivery diagnostics; must not contain tokens, complete webhook URLs, email passwords, or bot secrets |
| `created_at` | Attempt timestamp |

### `alert_cooldown`

Cooldown state at the rule or target level.

| Field | Description |
| --- | --- |
| `rule_id` | Corresponding rule ID |
| `target` | Cooldown target |
| `severity` | Optional severity dimension |
| `last_triggered_at` | Last trigger timestamp |
| `cooldown_until` | Cooldown expiration timestamp |
| `reason` | Cooldown reason |
| `state` | Current state, e.g., active, expired |
| `updated_at` | Update timestamp |

## Storage Evaluation

The repository already has a SQLite storage layer and repository/service layering:

- `src/storage.py` manages SQLite connections, SQLAlchemy ORM models, and `DatabaseManager`.
- `src/repositories/` contains the data access layer, e.g., `PortfolioRepository`.
- `src/services/` contains the business service layer, e.g., `PortfolioService`, `PortfolioRiskService`.
- The default database path follows existing configuration, typically at `data/stock_analysis.db`.

For P1/P2 alert persistence, it is recommended to reuse the above patterns: define alert ORM models in the storage layer, encapsulate CRUD and queries in the repository layer, and handle rule evaluation, assessment state, notification results, and cooldown semantics in the service layer. P0 does not create new tables and does not change the existing database.

If subsequent PRs require schema changes, they must also provide:

- Idempotent initialization: Repeated starts or repeated initialization must not destroy existing data.
- Backward compatibility: When no Alert Center is configured, daily analysis, ticker queries, notifications, market review, and portfolio functions must not be affected.
- Rollback instructions: The minimum rollback method must include at least reverting the PR; if new tables or indexes are created, it must specify whether to preserve data and how to manually clean up.
- Data migration boundaries: `AGENT_EVENT_ALERT_RULES_JSON` must not be automatically migrated, deleted, or overwritten unless the user explicitly performs an import action.

## P1 Alert API MVP

P1 adds a backend Alert API and schema, locking the Alert Center's minimum API contract, without integrating Web pages or background workers.

- New API file: `api/v1/endpoints/alerts.py`.
- New schema file: `api/v1/schemas/alerts.py`.
- API scope:
  - `GET /api/v1/alerts/rules`
  - `POST /api/v1/alerts/rules`
  - `GET /api/v1/alerts/rules/{rule_id}`
  - `PATCH /api/v1/alerts/rules/{rule_id}`
  - `DELETE /api/v1/alerts/rules/{rule_id}`
  - `POST /api/v1/alerts/rules/{rule_id}/enable`
  - `POST /api/v1/alerts/rules/{rule_id}/disable`
  - `POST /api/v1/alerts/rules/{rule_id}/test`
  - `GET /api/v1/alerts/triggers`
  - `GET /api/v1/alerts/notifications`
- The initial version of rules still only supports `price_cross`, `price_change_percent`, `volume_spike`; future types like `sentiment_shift`, `risk_flag`, `custom` return structured unsupported errors.
- The `test` endpoint only performs a one-time dry-run evaluation, does not send notifications, and does not write real trigger records or notification attempts.
- `cooldown_policy` / `notification_policy` in P1 are reserved fields only: the API can store and return these opaque configurations but does not execute cooldown or custom notification semantics.
- API responses must be sanitized and must not echo back tokens, complete webhook URLs, email passwords, cookies, or bot secrets.
- `AGENT_EVENT_ALERT_RULES_JSON` continues to be retained as a legacy configuration entry point; P1 does not automatically migrate, delete, overwrite, or rewrite legacy configurations.

P1 does NOT:

- Add new Web Alert Center pages, routes, or sidebar entries.
- Have the schedule worker load persisted active rules or implement merging/deduplication of persisted rules with legacy JSON.
- Implement real `alert_trigger` / `alert_notification` writes; P1 only provides query interfaces and table structures.
- Implement `alert_cooldown` execution semantics.
- Implement MACD, KDJ, CCI, RSI, portfolio risk, or Market Light alert rules.

## P2 Alert Evaluation Worker

P2 switches the schedule runtime from one-time legacy `EventMonitor` construction at startup to background worker evaluation of persisted active rules and legacy JSON rules each cycle.

- `AGENT_EVENT_MONITOR_ENABLED` continues to serve as the master switch; the background task name remains `agent_event_monitor`.
- The worker reads `enabled=true` `alert_rules` from the DB each cycle and re-parses `AGENT_EVENT_ALERT_RULES_JSON`; new API rules do not require restarting the schedule process.
- DB rules and legacy rules are deduplicated by `target_scope + target + alert_type + canonical(parameters)`; DB rules take precedence on conflicts; legacy configuration is not automatically migrated, deleted, or rewritten.
- Each rule is evaluated independently; a single failure only writes a `failed` assessment state and does not affect other rules in the same cycle or the main analysis flow.
- `alert_triggers` in P2 records minimum evaluation history: `triggered`, `skipped`, `degraded`, `failed`; normal `not_triggered` does not write history to avoid polling table churn.
- Missing real-time market data, missing fields, or non-evaluable scenarios record `skipped`; unavailable daily line data or incomplete structure records `degraded`; diagnostic information is sanitized.
- After triggering, `NotificationService.send(..., route_type="alert")` is still called; the in-process fingerprint only prevents repeated push notifications for continuous trigger conditions and does not execute `cooldown_policy`.

P2 does NOT:

- Add new Web Alert Center pages, routes, or sidebar entries.
- Write `alert_notifications` or record per-channel notification attempts.
- Implement `alert_cooldown`, `cooldown_policy`, or `notification_policy` execution semantics.
- Implement MACD, KDJ, CCI, RSI, portfolio risk, or Market Light alert rules.

## P3 Web Alert Center MVP

P3 adds an `/alerts` Alert Center entry point in the WebUI, allowing users to manage the current three runtime rule types without directly editing legacy JSON.

- A new "Alerts" sidebar entry is added; the page supports rule lists, pagination, enable/disable filtering, and rule type filtering.
- The rule creation form only supports `single_symbol` target scope and the three currently executable rule types:
  - `price_cross`: `direction` is `above` / `below`, with `price` filled in.
  - `price_change_percent`: `direction` is `up` / `down`, with `change_pct` filled in.
  - `volume_spike`: fill in `multiplier`.
- Rule operations support enable, disable, delete, and one-time dry-run testing.
- Dry-run tests only display fields declared in `AlertRuleTestResponse`: rule ID, status, whether triggered, observed value, and message; extension diagnostic fields like `threshold`, `data_source`, `data_timestamp` need to be explicitly exposed by the backend schema before display.
- Trigger history displays records written by the P2 worker: `triggered`, `skipped`, `degraded`, `failed`; normal `not_triggered` is still not written to history.
- The notification attempt area only queries the existing `GET /api/v1/alerts/notifications`; since the P2 runtime does not write per-channel notification attempts, it currently usually displays a "No notification attempt records" empty state and does not infer notification delivery results from trigger status.
- The Web page does not expose an `AGENT_EVENT_ALERT_RULES_JSON` edit entry point and does not automatically migrate, delete, or overwrite legacy configurations.

P3 does NOT:

- Add or modify backend APIs, schemas, storage, or worker behavior.
- Implement rule editing, advanced target/source filtering, watchlist/portfolio targets, technical indicator rules, or Market Light integration.
- Execute `cooldown_policy` / `notification_policy` or write `alert_notifications`.

## P4 Notification Results and Persisted Cooldown

P4 makes real alert triggers have troubleshootable notification results and gives persisted rules created via the Alert API business cooldown states that persist across restarts.

- For DB persisted rules, `triggered` history is deduplicated by `rule_id + target + data_source + data_timestamp` for the same data point: only the earliest `alert_triggers` record is kept for the same trigger event; repeated polling hits reuse existing trigger records; when `data_timestamp` is missing, deduplication is skipped to avoid incorrectly merging data points that cannot be proven to be from the same source. Even if subsequently suppressed by cooldown or notification noise reduction, corresponding notification attempts or synthetic suppression states are still recorded via `alert_notifications`.
- `alert_notifications` records real per-channel notification attempts, including `channel`, `success`, `error_code`, `retryable`, `latency_ms`, and sanitized `diagnostics`.
- Non-channel delivery states use synthetic channel records:
  - `__cooldown__`: Alert business cooldown suppression, `error_code="cooldown_active"`.
  - `__cooldown_read_failed__`: After failing to read persisted cooldown state, the worker process uses a temporary in-process fallback suppression, `error_code="cooldown_read_failed"`.
  - `__noise_suppressed__`: Notification infrastructure noise reduction suppression, `error_code="noise_suppressed"`.
  - `__no_channel__`: Alert routing did not match any available notification channel.
  - `__dispatch__`: Notification dispatch-level fallback or exception.
- Cooldown layering:
  - DB persisted rules use `alert_cooldowns` as the alert business cooldown in the normal path, no longer determined by the worker process fingerprint; only when reading persisted cooldown state fails, the in-process fingerprint is temporarily used to prevent the same rule from repeatedly pushing each cycle during DB anomalies.
  - Legacy `AGENT_EVENT_ALERT_RULES_JSON` rules continue to use the worker process fingerprint and do not write `alert_cooldowns`.
  - `notification_noise.py` still serves as a global safety net for the notification infrastructure layer; it is not the alert business cooldown, and suppression by it does not write to or extend `alert_cooldowns`.
- DB rule `cooldown_policy.cooldown_seconds` is normalized to a non-negative integer; when missing, a default 24-hour business cooldown is used; `0` disables DB business cooldown.
- `GET /api/v1/alerts/rules` returns read-only `last_triggered_at` / `cooldown_until` / `cooldown_active` summaries; `cooldown_active` is calculated by the backend using consistent cooldown time semantics; the Web does not parse naive ISO strings in the browser to infer state.
- The Web Alert Center displays cooldown state and notification results in read-only mode and does not provide a cooldown policy edit form.

P4 does NOT:

- Add new technical indicator, portfolio, watchlist, portfolio, watchlist, or Market Light alert rules.
- Implement target-level cross-rule merged cooldown; target-level merging is deferred to the portfolio/market integration phase.
- Rewrite the notification channel gateway; `NotificationService.send()` continues to maintain boolean return compatibility, with structured results provided via a new compatible interface.
- Automatically migrate, delete, or overwrite legacy `AGENT_EVENT_ALERT_RULES_JSON`.

## P5 Technical Indicator Rules

P5 adds daily line technical indicator rules to the existing Alert API, Web Alert Center, and `src/services/alert_worker.py` evaluation pipeline. Rules still write to `alert_rules`, with triggering, degradation, failure, notification results, and persisted cooldown continuing to reuse P2-P4's `alert_triggers`, `alert_notifications`, and `alert_cooldowns` semantics.

P5 supported `alert_type` and `parameters`:

| alert_type | parameters | Trigger Semantics |
| --- | --- | --- |
| `ma_price_cross` | `direction=above|below`, `window` defaults to `20`, integer `[2,250]` | Close crosses above/below MA(window) edge |
| `rsi_threshold` | `direction=above|below`, `period` defaults to `12`, integer `[2,250]`, `threshold` required and `0..100` | RSI crosses above/below threshold edge |
| `macd_cross` | `direction=bullish_cross|bearish_cross`, `fast_period=12`, `slow_period=26`, `signal_period=9`, all `[2,250]` and `fast_period < slow_period` | DIF/DEA golden cross/death cross edge |
| `kdj_cross` | `direction=bullish_cross|bearish_cross`, `period=9`, `k_period=3`, `d_period=3`, all `[2,250]` | K/D golden cross/death cross edge |
| `cci_threshold` | `direction=above|below`, `period` defaults to `14`, integer `[2,250]`, `threshold` required and finite number | CCI crosses above/below threshold edge |

Evaluation rules:

- The initial version uniformly uses daily line close; no intraday lines.
- Edge triggering only compares the two most recently closed daily lines; non-edge but current level already satisfying the threshold still returns `not_triggered`, preventing rules created on the first day from misreporting historical state as new triggers.
- Edge triggering includes the case where the previous bar exactly equals the threshold or zero axis: `above` / `bullish_cross` uses `prev <= threshold < current`, `below` / `bearish_cross` uses `prev >= threshold > current`.
- Partial bar only uses server-local timezone heuristics: when current local time is before 16:00, the last row date equaling local today or indeterminate date is conservatively discarded; no distinction is made between A-share, HK, US market timezones or trading calendars. The Issue #1386 P0 market phase baseline is not yet integrated with technical indicator rules; precise partial bar determination for alerts is deferred to a later phase.
- `src/services/alert_indicators.py` normalizes OHLCV and calculates MA, RSI, MACD, KDJ, CCI independently, without relying on fetcher-precomputed MA5/MA10/MA20.
- RSI uses Wilder's EMA / SMMA: `avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()`, `avg_loss` similarly, not using rolling SMA.
- MACD uses `EMA(fast_period) - EMA(slow_period)` to obtain DIF, with DEA as DIF's `EMA(signal_period)`; golden cross/death cross compares DIF-DEA edge crossing relative to 0.
- KDJ uses the most recent `period` days' highest/lowest prices to calculate RSV, and uses EMA with `alpha=1/k_period`, `alpha=1/d_period` to obtain K/D; golden cross/death cross compares K-D edge crossing relative to 0.
- CCI uses typical price `(high + low + close) / 3`, calculated as `(TP - MA(TP)) / (0.015 * mean_deviation)` based on `period`-day average and mean absolute deviation.
- `compute_required_bars(alert_type, params)` defines the minimum valid closed bars: MA=`window+1`, RSI=`period+1`, MACD=`slow_period+signal_period+1`, KDJ=`period+k_period+d_period+1`, CCI=`period+1`.
- Fetch days use `requested_days = min(max(required_bars * 3, required_bars + 30), 365)`; the API rejects combinations where `required_bars > 365` to prevent creating rules with permanently insufficient samples; within the same worker cycle, daily line data is cached by `(stock_code, requested_days)` and released at cycle end.
- Missing data, missing columns, or valid samples fewer than `required_bars` write `degraded`; data source exceptions follow `volume_spike` semantics returning `evaluation_error` / `failed` without sending notifications.

Compatibility boundaries:

- `AGENT_EVENT_ALERT_RULES_JSON` remains the legacy JSON path, only supporting `price_cross`, `price_change_percent`, `volume_spike` rule types; P5 technical indicators are only created via Alert API / Web.
- Does not extend `src/agent/events.py`'s legacy `AlertType` or `_RUNTIME_SUPPORTED_ALERT_TYPES`.
- P5 create/update parameter errors follow the existing Alert API error contract: HTTP 400 + `validation_error`; unsupported types return HTTP 400 + `unsupported_alert_type`.
- The Web Alert Center only extends the existing creation form, list display, type filtering, and dry-run testing without adding a new rule editor; dry-run tests do not write trigger history, and API responses continue to use the `triggered` / `not_triggered` / `evaluation_error` three-state pattern, with the `degraded` status written by the worker viewable through trigger history.
- After reverting the P5 PR, technically indicator rule records created in the database will be preserved; old code encountering unsupported `alert_type` during worker loading will skip them without affecting legacy three-type rule execution. If cleanup is needed, a maintainer must confirm before manually deleting the relevant `alert_rules` records.

P5 does NOT:

- Support MACD histogram expansion/contraction.
- Support KDJ overbought/oversold zone rules.
- Support MA-to-MA dual moving average crossovers.
- Support intraday lines, precise market calendar determination, or multi-market timezone precise partial bar.
- Support legacy `AGENT_EVENT_ALERT_RULES_JSON` technical indicator rules.
- Introduce a DSL, rule engine, new database tables, or a technical indicator rule engine within the analysis report pipeline.

## P6 Portfolio and Watchlist Integration

P6 adds `watchlist`, `portfolio_holdings`, `portfolio_account` three target scope types to the existing Alert API, Web Alert Center, and `src/services/alert_worker.py` evaluation pipeline. Rules still write to `alert_rules`, with triggering, degradation, failure, notification results, and persisted cooldown continuing to reuse P2-P4's `alert_triggers`, `alert_notifications`, and `alert_cooldowns` semantics without adding new tables or migrations.

### P6 Scope/Type Matrix

| `target_scope` | `target` | Allowed `alert_type` | Evaluation Method |
| --- | --- | --- | --- |
| `single_symbol` | Stock code | P1 three price/volume rules + P5 technical indicators | Single rule, single ticker |
| `watchlist` | `default` | P1 three price/volume rules + P5 technical indicators | Refresh and read current `STOCK_LIST` each cycle, expand by stock code |
| `portfolio_holdings` | `all` or active account ID | P1 three price/volume rules + P5 technical indicators | Expand symbols from non-zero holdings in portfolio snapshot, deduplicate by symbol |
| `portfolio_account` | `all` or active account ID | `portfolio_stop_loss`, `portfolio_concentration`, `portfolio_drawdown`, `portfolio_price_stale` | Account-level risk assessment, not expanded to individual tickers |

When creating/updating rules, `watchlist` / `portfolio_holdings` do not validate the parent `target` as a stock code; `portfolio_account` prohibits price/volume/technical indicator types; `portfolio_holdings` and `portfolio_account` with `target=<id>` validate that the account exists and is active, returning HTTP 400 + `validation_error` if not found. Legacy `AGENT_EVENT_ALERT_RULES_JSON` does not support watchlist, portfolio, or technical indicator extensions, continuing to only support `single_symbol` with `price_cross`, `price_change_percent`, `volume_spike`.

### Target Identity Contract

P6 separates displayable targets from persistable targets:

| Scenario | `effective_target` | `display_target` |
| --- | --- | --- |
| `single_symbol` | `<symbol>` | `<symbol>` |
| `watchlist` expanded sub-target | `<symbol>` | `Watchlist - <symbol>` |
| `portfolio_holdings` expanded sub-target | `<symbol>` | `Holdings - <symbol>` |
| `portfolio_account target=all` | `account:all` | `All Accounts` |
| `portfolio_account target=<id>` | `account:<id>` | `Account <id>` |

- `alert_triggers.target`, `alert_cooldowns.target`, and P4 `rule_id + target + data_source + data_timestamp` deduplication all use `effective_target`.
- `RuntimeAlertRule.key` uses `{parent_key}|{effective_target}` for expanded sub-targets to prevent in-process fallback when DB cooldown reading fails from suppressing different sub-targets under the same parent rule.
- `display_target` is not written to `alert_triggers.target` and is only used for notification titles, dry-run `target_results`, and Web display.
- P6 does not implement cross-rule same-ticker notification merging; if the same stock hits both a watchlist sub-rule and an independent `single_symbol` rule, each rule records and notifies independently.

### Dry-run Aggregation

- `POST /api/v1/alerts/rules/{rule_id}/test` returns aggregated fields for batch rules: `evaluated_count`, `triggered_count`, `degraded_count`, `skipped_count`, `target_results`.
- Expanded target soft cap is 100; targets exceeding the soft cap in dry-run are marked as `degraded` aggregation results and logged. The worker runtime only evaluates the first 100 expanded targets and writes a warning, without writing `alert_triggers` history for the overflow itself.
- Dry-run uses limited concurrency evaluation, with a per-target timeout of 10 seconds and a total evaluation timeout of 30 seconds; incomplete targets are marked as `skipped`.
- When any target is triggered, the top-level `status=triggered`; when no triggers but there are successful evaluations, skipped, or degraded targets, the top-level `status=not_triggered`; only when unable to expand or all targets fail does it return `evaluation_error`.
- Empty watchlist / empty holdings: dry-run returns `not_triggered` with `record_status=skipped` in `target_results`; the worker writes `skipped` history.
- `degraded_count` counts all entries with `record_status=degraded` across all expanded evaluation results; `target_results` displays only the first 20 entries, sorted with triggered first, then degraded/failed, then by target.

### Portfolio Risk Rules

| `alert_type` | Parameters | Observed Value | Trigger Semantics |
| --- | --- | --- | --- |
| `portfolio_stop_loss` | `mode=near|breach`, default `near` | Maximum `loss_pct` among affected tickers | `near` uses `stop_loss.near_alert`, `breach` only counts `is_triggered=true` items; at most one trigger per account per cycle |
| `portfolio_concentration` | - | `concentration.top_weight_pct` | `top_weight_pct >= portfolio_risk_concentration_alert_pct` |
| `portfolio_drawdown` | - | `drawdown.max_drawdown_pct` | Reuses `PortfolioRiskService`'s `drawdown.alert`; `current_drawdown_pct` written to diagnostics |
| `portfolio_price_stale` | - | Count of stale/missing price holdings | Any position with `price_stale=true` or `price_available=false` |

Portfolio diagnostics must contain `account_id` (or `all`), `currency`, `as_of`, `price_stale`, `fx_stale`, `data_available`, `top_affected_symbols`. `portfolio_stop_loss`, `portfolio_concentration`, `portfolio_drawdown` reuse `PortfolioRiskService.get_risk_report()`; `portfolio_price_stale` reuses `PortfolioService.get_portfolio_snapshot()`'s position price metadata.

### Web and Cooldown Summary

- The Web creation form adds target scope selection; `watchlist` / `portfolio_holdings` only show price/volume/P5 technical indicator types, `portfolio_account` only shows four portfolio risk types.
- When loading the account list fails for `portfolio_holdings` / `portfolio_account`, the form retains the `all` option and displays an error.
- The `cooldown_active` on the rule list is accurate for `single_symbol` and `portfolio_account`; for `watchlist` / `portfolio_holdings`, it is a parent rule summary and does not represent each sub-target's cooldown state; sub-target cooldown is based on trigger history and `effective_target`.
- The dry-run UI displays aggregate counts and up to 20 `target_results` details.

P6 does NOT:

- Implement P7 Market Light.
- Implement pre-earnings date or pre-dividend/rights date reminders; such rules need a stable date contract before a separate follow-up.
- Implement sector-level concentration alerts; P6 concentration uses symbol-level `top_weight_pct`.
- Implement cross-rule same-ticker notification merging, intraday lines, multi-market timezone precise determination, or legacy JSON extensions.

## Phase Awareness and Public Summary Integration (Refs #1386 P6)

This section describes the alert visibility integration for #1386 P6, distinct from the "P6 Portfolio and Watchlist Integration" above. This integration does not add new alert tables, does not perform migrations, and does not automatically trigger lightweight LLM analysis; it only writes the phase/pack summary that was public at the time of triggering into the existing trigger history.

- `AlertTriggerItem` retains the `diagnostics` string and adds derived fields `market_phase_summary`, `analysis_context_pack_overview`, `analysis_visibility_source`.
- Real `status=triggered` worker records merge a sibling key `analysis_visibility` in the JSON diagnostics, containing `market_phase_summary`, `analysis_context_pack_overview`, `source`. Old plain-text diagnostics retain their original text; API derived fields return `null`, and source returns `legacy_text`.
- `analysis_visibility_source` values are `alert_trigger_market_context`, `analysis_history_snapshot`, `evaluator_snapshot`, `legacy_text`, or `null`.
- Symbol targets use `get_market_for_stock(normalize_stock_code(effective_target))` to construct the phase at trigger time; `target_scope=market` directly uses `normalize_market_region(target)` without inferring `cn|hk|us|jp|kr` as stock codes; when the account level cannot uniquely locate a market, the summary is allowed to fall to `unknown`.
- `analysis_context_pack_overview` only comes from evaluator-provided overviews or historical snapshots within the last 30 days. Recent history queries reuse code variant candidates from the history service, executed in a best-effort + in-batch short cache manner; missing or failed parsing returns `null` without fabricating packs.
- Alert notifications only output public summaries: phase label, trigger source, partial-bar warning, data quality level, and the first two limitations. Notifications must not output raw context packs, prompts, news article text, complete diagnostics JSON, webhook URLs, tokens, or portfolio-sensitive details.
- Web alert history displays phase badge, data quality level, and limitations empty state; old trigger records missing public summaries do not affect list reading.
- #1390 P6 further reuses `DecisionSignal`: stock-level real triggers prioritize associating the same ticker's latest active signal and writing a low-sensitivity `decision_signal_summary` to diagnostics; when no active signal exists, only a minimal `source_type=alert/action=alert` signal is created. `trace_id=alert-rule-<hash>` is only used for best-effort idempotent deduplication of same-source retries and does not overwrite active signals; new alert signals do not write `market_phase` to avoid the same rule creating duplicates across phases. `market`, `portfolio_account`, overflow, or triggers that cannot be parsed to a specific stock do not create individual stock signals.

See [DecisionSignal Decision Signals Topic](decision-signals.md) for DecisionSignal fields, sanitization, migration, and rollback boundaries.

The user boundary for #1386 P7: Alert integration only explains the phase and data quality summary that was already public at trigger time; it does not automatically initiate lightweight LLM intraday analysis, nor does it add new alert tables, rule types, environment variables, or migrations. When phased analysis is needed, it should still be triggered through the analysis API / Web manual analysis entry; alert notifications only retain the phase label, trigger source, partial-bar warning, data quality level, and the first two limitations.

Rolling back this integration only requires reverting the worker/API/Web changes; existing `diagnostics.analysis_visibility` is retained as plain JSON diagnostics and old code will not read this sibling key.

## P7 Market Traffic Light Structured Alerts

P7 adds `target_scope=market` to the existing Alert API, Web Alert Center, and `src/services/alert_worker.py`, consuming structured `MarketLightSnapshot` without parsing Markdown, extending legacy `AGENT_EVENT_ALERT_RULES_JSON`, or adding new tables. Market review history still writes one `analysis_history(code=MARKET, report_type=market_review)`; multi-market reviews save the snapshot map of actually reviewed regions via `context_snapshot.market_light_snapshots`.

### P7 Scope/Type Matrix

| `target_scope` | `target` | Allowed `alert_type` | Parameters | Trigger Semantics |
| --- | --- | --- | --- | --- |
| `market` | `cn` / `hk` / `us` / `jp` / `kr` | `market_light_status` | `statuses=["red","yellow"]`, only `red/yellow` allowed, default `["red","yellow"]` | Triggers when current `MarketLightSnapshot.status` hits the list |
| `market` | `cn` / `hk` / `us` / `jp` / `kr` | `market_light_score_drop` | `min_drop > 0` | `prev.score - current.score >= min_drop`, and `prev.trade_date < current.trade_date` |

Scope/type validation is a bidirectional constraint: `target_scope=market` can only use two Market Light rule types; `market_light_*` rules can only use `target_scope=market`. `target` is strictly limited to `cn|hk|us|jp|kr` after `strip().lower()`, with invalid targets returning HTTP 400 + `validation_error`.

### `MarketLightSnapshot` Contract

Structured snapshot fields are: `region`, `trade_date`, `status`, `score`, `label`, `temperature_label`, `reasons`, `guidance`, `dimensions`, `data_quality`. The `trade_date` in the first version is fixed to `MarketOverview.date`; P7 does not parse provider quote as-of.

`dimensions` uses the canonical scorer as the single source of truth; `build_market_light_snapshot()`, the market review injection block, and the alert service do not re-implement scoring. `_build_market_temperature()` is just a thin wrapper; the traffic light `status` threshold remains `60/40`, and the temperature label threshold remains `70/55/40`.

| dimension | `available=true` condition | fallback score |
| --- | --- | --- |
| `breadth` | `has_market_stats && (up_count + down_count) > 0` | `50` |
| `index` | `indices` non-empty and at least one `change_pct != None` | `50` |
| `limit` | `has_market_stats && (limit_up_count + limit_down_count) > 0` | `50` |

`data_quality=unavailable` means `index.available=false`; both market rule types return `skipped` without triggering notifications; `partial` means at least one dimension is fallback; `ok` means all three are available. `market_light_status` can trigger under `ok/partial`; `partial` triggers must include `missing_dimensions` in diagnostics. `market_light_score_drop` directly compares the canonical aggregate score; comparison is still allowed when either side is `partial`, but diagnostics must include `partial_comparison=true` and `missing_dimensions`.

### Baseline, Trading Day, and Deduplication

- Market review persistence must use the same `MarketOverview` shared with report generation to create `MarketLightSnapshot`; secondary market data fetching during persistence is prohibited.
- `load_previous_snapshot(region, before_trade_date)` scans `analysis_history(code=MARKET, report_type=market_review)`, skips legacy records missing `context_snapshot.market_light_snapshots[region]`, first selects the largest `snapshot.trade_date` less than `before_trade_date`, then within the same `trade_date` takes the latest valid snapshot by `created_at DESC, id DESC`; later-inserted old trading day backfills do not override the correct baseline.
- If the target `trade_date` only has corrupted snapshots, `market_light_score_drop` returns `degraded` without automatically falling back to an older trading day for best-effort comparison.
- `market_light_score_drop` in the first version only performs cross-trading-day comparison; when no previous trading day baseline or same-day baseline exists, it returns `skipped`; query/parsing exceptions return `degraded`.
- The worker performs a region trading day gate for `target_scope=market` and respects `TRADING_DAY_CHECK_ENABLED` / `config.trading_day_check_enabled`; when checks are disabled, evaluation is allowed; when checks are enabled and the region is not a trading day, it returns `skipped` without fetching the current snapshot.
- Trigger history writes `target=<region>`, `observed_value=<score>`, `data_source=market_light`, `data_timestamp=<trade_date 00:00:00>`, continuing to reuse P4's `rule_id + target + data_source + data_timestamp` deduplication.

### Web and Rollback Boundaries

- The Web Alert Center adds `market` scope, region selection, two market rule parameter controls, type filtering, region display, and parameter display; API snake_case mapping uses `statuses` and `min_drop`.
- Legacy `AGENT_EVENT_ALERT_RULES_JSON` does not support market rules; P7 does not update `.env.example` since no new configuration items are added.
- P7 does not implement index decline, sector anomalies, limit up/down structure deterioration, intraday lines, multi-market timezone precise quote as-of parsing, or DSL/rule engines.

## P8 User Configuration and Deployment Boundaries

P8 does not add new rule types, APIs, table structures, or worker behavior; it organizes the P0-P7 merged capabilities into user and deployer-facing configuration documentation. The alert worker is only registered in schedule mode, with the core switch still being `AGENT_EVENT_MONITOR_ENABLED` and the polling interval still `AGENT_EVENT_MONITOR_INTERVAL_MINUTES`. Notification channels continue to use alert routing; see `NOTIFICATION_ALERT_CHANNELS` and `route_type=alert` in [Notification Configuration](notifications.md).

### Local Configuration

When running locally with `python main.py --schedule`, `python main.py --serve --schedule`, or equivalent built-in schedule modes, setting `AGENT_EVENT_MONITOR_ENABLED=true` starts the background alert worker; `AGENT_EVENT_MONITOR_INTERVAL_MINUTES` controls the polling interval.

There are two rule sources:

- Alert API / Web Alert Center persisted rules: The recommended entry point, supporting `single_symbol`, `watchlist`, `portfolio_holdings`, `portfolio_account`, `market`, covering real-time price, price change percentage, volume, daily technical indicators, portfolio risk, and market traffic light rules.
- Legacy `AGENT_EVENT_ALERT_RULES_JSON`: Only compatible with three basic `single_symbol` rule types: `price_cross`, `price_change_percent`, `volume_spike`; does not support P5 technical indicators, P6 watchlist/portfolio, or P7 market light. The system does not automatically migrate, delete, or overwrite legacy JSON.

### Docker

The repository's `docker/Dockerfile` default command is `python main.py --schedule`, so the container only needs `AGENT_EVENT_MONITOR_ENABLED=true` configured to enable the alert worker in schedule mode. Web/API persisted rules depend on the application database; Docker deployments need to preserve the `data/` database volume to avoid losing rules, trigger history, notification attempts, and cooldown state after container rebuilds. Legacy JSON is still injected via environment variables, not through a Docker-specific configuration system.

### GitHub Actions

The repository's `.github/workflows/00-daily-analysis.yml` is a one-shot analysis workflow that actually calls `python main.py`, `python main.py --market-review`, or `python main.py --no-market-review` without running the `--schedule` background alert worker, and does not map `AGENT_EVENT_*` variables. Only adding `AGENT_EVENT_MONITOR_ENABLED` or `AGENT_EVENT_ALERT_RULES_JSON` in repository Secrets/Variables will not cause the default Actions to start continuously polling alerts.

If alert polling in GitHub Actions is needed, a subsequent separate PR must clarify the schedule startup method, env mapping, rule sources, and persisted database strategy; P8 does not change existing workflows.

### Web and Desktop

The Web Alert Center `/alerts` is the primary entry point for persisted rules: rules can be created, enabled/disabled, deleted, one-time dry-run tests executed, trigger history and read-only cooldown state viewed. Batch rule list cooldown status is a parent rule summary; whether sub-targets are cooled down is based on `target` / `effective_target` in the trigger history.

Desktop does not add a native alert management interface; desktop users reuse the built-in or external WebUI's `/alerts` page. Desktop rollback does not require cleaning up additional state.

### State, Notifications, and Rollback

The worker writes `triggered`, `skipped`, `degraded`, `failed` to `alert_triggers` as evaluation history; normal un-triggered events do not write history. `skipped` means the rule had no evaluable conditions this cycle, such as market not being a trading day or missing the previous trading day baseline; `degraded` means data source, portfolio snapshot, historical snapshot, or parsing process exceptions occurred, and results are unusable for triggering notifications.

After real triggers, `alert_notifications` and `alert_cooldowns` are written; DB persisted rules perform best-effort deduplication for the same data point by `rule_id + target + data_source + data_timestamp`. Legacy JSON rules continue to only use the in-process fingerprint and do not write persisted cooldown.

Rolling back P8 only requires reverting documentation, configuration instructions, and Web text changes; there are no database migrations or user data cleanup. When rolling back earlier Phases, previously created persisted rules are not automatically deleted and are handled according to the Phase rollback instructions below.

## Phase Boundaries

- P0: This document, contracts, storage evaluation, and compatibility testing.
- P1: Alert API MVP, initial version only covers existing three runtime rule types.
- P2: Alert evaluation worker and runtime unification, allowing persisted active rules and legacy JSON to coexist.
- P3: Web Alert Center MVP.
- P4: Trigger history, notification results, and cooldown state.
- P5: Technical indicator rules.
- P6: Portfolio and watchlist integration.
- P7: Market traffic light and market integration.
- P8: Documentation, migration, and finalization.

## P0 Does NOT

- P0 does not add `api/v1/schemas/alerts.py` or Alert API.
- P0 does not add Web Alert Center pages, routes, or sidebar entries.
- P0 does not add database tables, repositories, or migrations.
- P0 does not implement trigger history, notification results, or cooldown state writes.
- P0 does not automatically migrate, delete, or overwrite `AGENT_EVENT_ALERT_RULES_JSON`.
- P0 does not implement MACD, KDJ, CCI, RSI, portfolio risk, or Market Light alert rules.
- P0 does not rewrite `NotificationService` or the notification routing framework.

## Rollback

- P0 is documentation and test finalization. If only rolling back P0, reverting the corresponding PR is sufficient; no database, configuration, or user data migrations need additional handling.
- P1 adds Alert API code and `alert_rules` / `alert_triggers` / `alert_notifications` SQLite tables. The minimum rollback method is reverting the P1 PR; the revert will remove API, service, repository, schema, and ORM definitions, but SQLite tables and data already created by `Base.metadata.create_all()` will not be automatically deleted. If cleanup is needed, a maintainer must confirm before manually deleting the relevant tables.
- P3 is Web and documentation changes. The minimum rollback method is reverting the P3 PR; it will not delete existing rules, trigger history, or legacy JSON configuration.
- P4 adds the `alert_cooldowns` SQLite table and begins writing `alert_notifications`. The minimum rollback method is reverting the P4 PR; already created `alert_cooldowns`, `alert_triggers`, `alert_notifications` data will not be automatically deleted. If cleanup is needed, a maintainer must confirm before manually deleting the corresponding tables or records.
- P5 adds technical indicator rules supported by Alert API/Web. The minimum rollback method is reverting the P5 PR; already created P5 `alert_rules` records will not be automatically deleted, and old code will skip unsupported `alert_type` during worker loading without affecting legacy three-type rule execution. If cleanup is needed, a maintainer must confirm before manually deleting the relevant rule records.
- P6 adds watchlist, portfolio holdings, and portfolio account rules supported by Alert API/Web. The minimum rollback method is reverting the P6 PR; there are no new tables or migrations, and already created P6 `alert_rules` will be preserved. Before rollback, it is recommended to disable/delete non-`single_symbol` P6 rules; otherwise the old worker may evaluate `watchlist` / `portfolio_holdings` parent `target` as a stock code and generate failed/skipped noise, and portfolio-specific `alert_type` will be skipped during worker loading.
- P7 adds `market` rules supported by Alert API/Web and market review `market_light_snapshots` historical snapshots. The minimum rollback method is reverting the P7 PR; there are no new tables or migrations, and already created P7 `alert_rules` will be preserved. Before rollback, it is recommended to disable/delete `target_scope=market` rules; the old worker will skip unsupported `market_light_*` types or generate configuration noise from unrecognized scope/type.
