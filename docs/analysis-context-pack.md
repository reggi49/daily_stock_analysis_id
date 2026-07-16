# AnalysisContextPack: P0 Inventory, P1/P2 Contracts, P3 Runtime Consumption, P4 Visibility, P5 Data Quality, #1386 P6 Linkage, and #1389 P6 Migration & Rollback

This page is a dedicated document for Issue #1389, recording the real sources, consumption paths, field status boundaries of the current DSA analysis context, as well as the `AnalysisContextPack` internal contracts, builder, runtime consumption, low-sensitivity visibility, data quality scoring, alerts/holdings/history/backtest linkage, migration, and rollback boundaries. P0 is responsible for current-state inventory and contract boundaries; P1 only adds internal schema/envelope, block catalog, type conventions, and redacted serialization; P2 only assembles packs from pipeline artifacts; P3 only connects low-sensitivity summaries to standard analysis and Agent initial prompts; P4 only connects low-sensitivity overviews to history details, synchronous analysis responses, completed task status, and Web report pages; P5 completes data quality scoring, `fetch_failed` status, prompt data limits, and overview low-sensitivity display within the same `PACK_VERSION = "1.0"`; #1386 P6 reuses the same public overview for alerts, holdings, history, backtests, and notification linkage, adding an optional auxiliary `portfolio` block for manual holding analysis; #1389 P6 only completes documentation, configuration visibility, migration, and rollback notes without adding pack runtime, pack feature flags, DB migration, or schema versions.

## Terminology and Boundaries

The repository contains multiple data planes named context/snapshot; P0 must disambiguate first to avoid mistaking existing runtime structures for future packs.

| Term | Current Meaning | Primary Consumer | P0 Boundary |
| --- | --- | --- | --- |
| `storage.get_analysis_context()` | Technical context from the last two days of OHLCV generated from the database in `src/storage.py`, containing `today`, `yesterday`, `volume_change_ratio`, `price_change_ratio`, `ma_status`, etc. Current implementation accepts `target_date` but actually fetches the latest two days. | Standard analysis main path, Agent tool `get_analysis_context` | Recorded as historical technical input source; not directly equated to future pack. |
| `enhanced_context` | Prompt context in standard analysis enhanced by `src/core/pipeline.py` based on DB technical context, realtime quotes, chips, trends, fundamentals, and language info. | `src/analyzer.py` prompt rendering, `_build_context_snapshot()` | Records current prompt input surface; P0 does not change field names or structure. |
| `analysis_history.context_snapshot` | Persisted snapshot written to history table after analysis. Standard analysis typically contains `enhanced_context`, `news_content`, `realtime_quote_raw`, `chip_distribution_raw`; Agent path saves `initial_context`. | History details, synchronous analysis/status responses, backtests, partial fundamentals fallback display | Recorded as persisted consumption surface; must preserve `context_snapshot.enhanced_context.date` compatibility. |
| Agent executor message context | Context injected into first user message by `AgentExecutor._build_user_message()`, applicable to `AGENT_ARCH=single` path, currently containing stock code, report type, output language, `realtime_quote`, `chip_distribution`, `news_context`. | Single Agent first-round LLM message | Records current first-round visible fields; P0 does not add runtime injection. |
| Agent orchestrator `AgentContext` | Multi-agent shared context written by `AgentOrchestrator._build_context()`, applicable to `AGENT_ARCH=multi` path, can pre-inject `realtime_quote`, `daily_history`, `chip_distribution`, `trend_result`, `news_context`. | Technical / Intel / Risk / Decision multi-agent pipeline | Recorded as orchestrator internal shared data plane; does not pre-inject `fundamental_context`; `trend_result` existence depends on whether the caller passes it in. |

## P0 Scope and Non-goals

P0's goal is to enable subsequent P1/P2/P3 to design `AnalysisContextPack` based on real repository boundaries, rather than prematurely refactoring the runtime.

- P0 covers context inventory across seven paths: standard analysis, Agent, alerts, holdings, backtests, history, and notifications.
- P0 fixes field quality status words; P1 has already added `AnalysisContextPack` internal schema, but still adds no builder, no runtime connection, and no full pack exposure.
- P0 does not add builders, configuration items, database fields, or change API, report, history, or notification payloads.
- P0 does not connect to runtime, does not modify `src/` analysis, Agent, alerts, holdings, backtest, or notification logic.
- P0 does not pack-ify `market_review`, `market_light`, or market red-green light topic snapshots; these are only recorded as other `report_kind` / topic consumption boundaries within historical snapshots.
- P0 at that time does not add `fetch_failed` to field quality status words; P5 has added this status within the same 1.0 umbrella to clearly distinguish "not supported" from "this fetch failed".
- P0 does not expand implementation details in README; this page serves as a dedicated document, discoverable via `docs/INDEX.md` / `docs/INDEX_EN.md` entry points.

## P1 Internal Contracts

P1 implements `src/schemas/analysis_context_pack.py`, only defining internal schema/envelope for P2 builder and P3 runtime consumption to reuse the same structure. P1 does not fill runtime data, add new fetchers, change prompts, write to history/task/report metadata, or expose the complete pack to API, Web, Bot, Desktop, or notifications.

P1 schema includes:

- `PACK_VERSION = "1.0"`, marked via `AnalysisContextPack.pack_version`.
- `ContextFieldStatus`: P1 first version only allows `available`, `missing`, `not_supported`, `fallback`, `stale`, `estimated`, `partial`; P5 has added `fetch_failed`, indicating the field or data block explicitly failed this fetch, not representing full analysis failure.
- `AnalysisSubject`: Top-level identity slot containing only `code`, `stock_name`, `market`; `exchange`, `currency`, `industry` are reserved for future extension; P2 builder does not expand P1 schema and does not duplicate `identity` blocks.
- `AnalysisContextItem`: Field-level input item containing `status`, `value`, `source`, `timestamp`, `fallback_from`, `missing_reason`, `warnings`, `metadata`.
- `AnalysisContextBlock`: Data block-level grouping containing `status`, `items`, `source`, `timestamp`, `warnings`, `metadata`, where `items` is `Dict[str, AnalysisContextItem]`.
- `DataQuality`: P1 only retains `warnings` and `metadata` containers; P5 has added `overall_score`, `level`, `block_scores`, `limitations`, maintaining low-sensitivity without carrying raw payloads.
- `AnalysisContextPack`: Top-level envelope containing `pack_version`, `subject`, `phase`, `blocks`, `data_quality`, `metadata`, `created_at`.

Time field conventions:

- `AnalysisContextPack.created_at` uses `datetime`, output as ISO 8601 string via `model_dump(mode="json")`.
- `AnalysisContextItem.timestamp` and `AnalysisContextBlock.timestamp` use `Optional[str]`, conventionally ISO 8601 datetime strings; P1 schema validates this format at construction; date-only, natural language time, or slash-separated dates are rejected; P2 builder reuses existing artifact timestamps without forced secondary conversion.

Status semantics:

- `block.status` represents whole-block availability.
- `item.status` represents field-level quality.
- P1 does not implement automatic aggregation from `item.status` to `block.status`.

P1 Block Catalog:

| block key | P1 semantics | P1 boundary |
| --- | --- | --- |
| `quote` | Realtime quotes and pricing-related inputs | Only defines expressible positions; does not fetch or fill data. |
| `daily_bars` | Complete daily bar window and latest complete daily bar date | P1 does not determine partial bars. |
| `technical` | Technical indicators, volume-price structure, and patterns | P1 does not generate indicators. |
| `fundamentals` | Valuation, growth, profitability, financials, and shareholder returns | P1 does not add new fundamentals fetchers. |
| `news` | News, announcements, sentiment, and catalyst event inputs | P1 does not change news search. |
| `portfolio` | Holding status, account summary, cost, quantity, position, and stale summary | P1 does not include transaction flows, cash flows, or full account privacy data. |
| `chip` / `capital_flow` | Chips, capital flow, and main-force behavior | Future extension keys; P1 only allows contractual expression. |
| `events` / `market_context` | Risk events, market breadth, indices, sectors, and hotspot environment | Future extension keys; does not include `market_review` / `market_light` as first-version single-stock pack. |

The `phase` field only accepts #1386 `MarketPhaseContext.to_dict()` output, maintaining `Dict[str, Any]` without redefining phase enums or phase sub-models.

Redaction boundaries:

- `AnalysisContextPack.to_safe_dict()` first executes `model_dump(mode="json")`, then calls `redact_sensitive_mapping()`.
- `redact_sensitive_mapping()` only performs dict/list key-based recursive redaction, replacing values with `[REDACTED]` when hitting sensitive keys or phrases like `api_key`, `access_token`, `refresh_token`, `authorization_header`, `webhook_url`, `password`, `cookie`, `secret`, `token`, `sendkey`, `license_key`.
- P1 does not scan ordinary string values, does not do URL regex redaction, and does not treat `data_api` or bare `api` / `key` as sensitive hits, avoiding turning this contract into a general secrets engine.

## P2 Builder Contract

P2 adds `AnalysisContextBuilder`, but the first version only acts as an assembler: assembling internal `AnalysisContextPack` from artifacts already obtained by the standard analysis pipeline. The "reuse existing data sources" in the issue acceptance criteria is interpreted in this slice as reusing pipeline-fetched `realtime_quote`, `base_context`, `enhanced_context`, `trend_result`, `chip_data`, `fundamental_context`, `news_context`, and other artifacts; the builder itself is zero-fetch, not calling DB, fetcher, SearchService, Agent tools, or specific providers.

P2 input contract uses `PipelineAnalysisArtifacts`: `code`, `stock_name`, `market`, `phase`, `base_context`, `enhanced_context`, `realtime_quote`, `trend_result`, `chip_data`, `fundamental_context`, `news_context`, `news_result_count`, `metadata`. Single-stock `build()` and batch `build_batch()` reuse the same structure to avoid signature changes when P3 runtime is integrated.

P2 block assembly boundaries:

- `subject` still only writes `code`, `stock_name`, `market` three fields without expanding `AnalysisSubject`.
- `phase` only accepts the passed-in `MarketPhaseContext.to_dict()` output, not back-derived from `enhanced_context`.
- `quote` assembled from `realtime_quote`; missing is `missing`; `source=fallback` or explicit `fallback_from` maps to `fallback`, but `source` preserves the real successful source; `fallback_from` is only filled when explicitly provided in artifact/metadata, otherwise only stable warning codes are recorded without fabricating provider chains.
- `quote` passes through #1386 P3 `fetched_at`, `provider_timestamp`, `is_stale`, `stale_seconds`, `fallback_from`. Status priority is fixed as `STALE > FALLBACK > AVAILABLE`: `is_stale=True`, `price_stale`, `quote_stale`, `quote_stale_seconds` explicit markers are marked as `stale`; `stale_seconds` with `is_stale=False` is metadata only, not independently inferring stale. Builder only maps upstream artifacts without quality scoring.
- `daily_bars` only expresses complete daily bar windows, preferring `base_context.today`, `base_context.yesterday`, `base_context.date`, `base_context.data_missing`; date-only goes into `value` or `metadata`, not `timestamp`.
- `enhanced_context.today` `is_partial_bar`, `is_estimated`, `estimated_fields` prefer entering `technical`; when missing, still compatible with `enhanced_context.today.data_source` as `realtime:*` old heuristic. partial/estimated only enters `technical`; `daily_bars` does not carry partial/estimated; warnings use `intraday_realtime_overlay`.
- `technical` prefers reusing `trend_result.to_dict()`; when no trend artifact, is `missing`.
- `chip` reuses `chip_data.to_dict()`; when no chip artifact, defaults to `missing`; only marked `not_supported` when input metadata/artifact explicitly indicates not_supported.
- `fundamentals` only reads `fundamental_context` parameter; `ok` maps to `available`, `not_supported` maps to `not_supported`, `partial` maps to `partial`; after P5, `failed` maps to `fetch_failed` + stable reason code `fundamental_pipeline_failed`; does not write raw `errors[]` text.
- `news` non-blank string is `available`, blank or missing is `missing`; `news_result_count` written to pack metadata.

P2 does not assemble `portfolio`, `events`, `market_context`, nor does it split `capital_flow` into an independent block; the first version only retains it in fundamentals coverage/source chain metadata. P2 at that time also does not change prompts, does not let standard analysis or Agent runtime consume packs, does not write to history/task/report metadata, and does not expose full pack to API/Web/Bot/Desktop/notifications; P5 only adds low-sensitivity scoring, `fetch_failed` granularity, and prompt limits on the existing builder without adding new fetchers.

## P3 Runtime Consumption

P3 connects runtime consumption after P2 `AnalysisContextBuilder`, but consumption is limited to low-sensitivity `analysis_context_pack_summary`. `StockAnalysisPipeline` is the sole producer of the summary: completing `PipelineAnalysisArtifacts` -> `AnalysisContextBuilder.build()` -> `format_analysis_context_pack_prompt_section()` within both standard analysis and Agent paths; downstream analyzer, single-agent, multi-agent only receive the summary string, not constructing complete packs themselves nor reading `AnalysisContextPack.to_safe_dict()` block item raw values.

Standard analysis prompt order is fixed as: basic info -> #1386 `market_phase_context` rendered block -> `analysis_context_pack_summary` -> technical, realtime quotes, news, and other existing blocks. `analysis_context_pack_summary` only contains subject, `pack_version`, block `status` / `source` / `warnings` / `missing_reason`, `metadata.news_result_count`, `data_quality.warnings`, and P5 low-sensitivity data limits; it must not output `news.content`, `trend_result`, `chip`, `fundamental_context` or other raw payloads.

Agent path also only passes the summary. `AgentExecutor._build_user_message()` inserts the summary after the market phase section and before pre-fetched JSON; `AgentOrchestrator._build_context()` only puts the summary into `ctx.meta["analysis_context_pack_summary"]`, prohibiting writes to `ctx.data`; `BaseAgent._build_messages()` inserts the summary after the market phase user message and before `_inject_cached_data()`. Agent path reads `storage.get_analysis_context()` once after `_ensure_agent_history()` prefetch as the low-sensitivity status source for `daily_bars`; when the read fails or no context is available, `daily_bars_missing` is marked; this read is fail-open and does not write daily bar raw payloads into Agent runtime context. Agent first round does not reuse standard analysis news search; `news` block being `missing` is the expected P3 state.

P3 at that time does not persist full packs, does not add API/Web/Bot/Desktop fields, does not change report JSON schema, and does not write summaries to `analysis_history.context_snapshot`, task status, or report metadata; history snapshots and diagnostic snapshots strip `market_phase_context`, `analysis_context_pack`, `analysis_context_pack_summary` and other runtime prompt keys. P4 on this basis adds low-sensitivity overview, with visibility limited to history details, synchronous analysis responses, completed task status, and Web report pages; P5 continues reusing summary consumption paths without changing LLM output JSON schema. Agent tool-level pack cache reuse remains future work.

## #1381 Daily Market Context

#1381 adds a small daily market environment summary channel outside AnalysisContextPack, avoiding direct packification of `market_review` / `market_light`. `DAILY_MARKET_CONTEXT_ENABLED` defaults to enabled; when `MARKET_REVIEW_ENABLED=true` and `DAILY_MARKET_CONTEXT_ENABLED=true`, `StockAnalysisPipeline` loads the day's market context by stock market (`cn` / `hk` / `us`): preferring reusing same-day same-market records from `analysis_history(code=MARKET, report_type=market_review)`; when no same-day record exists, calling `run_market_review(..., return_structured=True, send_notification=False)` to generate this context, with in-process cache to prevent duplicate generation within the same Pipeline, and serialization via market review lock on CLI/scheduled-task concurrent paths. `DAILY_MARKET_CONTEXT_ENABLED=false` only disables low-sensitivity summary injection and guardrails for individual stock analysis, not the market review itself.

**Background:** `#1381` focuses on single-stock analysis daily market context reuse and fallback control, not changing existing intraday phases, daily reports, or status modeling architecture. This section aligns with the #1381 entry in `docs/CHANGELOG.md` [Unreleased] and serves as the convergence boundary for this round's change description.
**Scope (this round's implementation scope):** `#1381` only covers backend runtime market context injection, same-day/target trading-day reuse control, and guardrails; does not include independent API, Web phase result display, four-phase daily report structured persistence, or new daily report status tables. Main entry points are `main.py` (scheduling and `--no-market-review`), `src/core/pipeline.py`, `src/core/market_review.py`, `src/services/daily_market_context.py`, `src/analyzer.py`, `src/analysis_context_pack_overview.py`, `src/agent/executor.py`, `src/agent/orchestrator.py`, `src/agent/agents/base_agent.py`, `src/daily_market_context_guardrail.py`; Web side only synchronizes `DAILY_MARKET_CONTEXT_ENABLED` setting text/help, without adding phase result display.
**Acceptance criteria boundary:** This PR only corresponds to #1381's runtime integration and guardrail sub-goals; unless independent API, Web phase display, four-phase daily report persistence, and daily report status table have been implemented and verified in subsequent changes, Issue #1381 must not be marked as fully accepted.
**Compatibility/Risk:** `#1381` does not change `provider/model/base_url`, default model, or configuration cleanup/backfill/migration semantics; does not add database or runtime configuration table changes. `main.py::_bootstrap_environment`, `src/core/pipeline.py`, `src/analyzer.py`, `src/agent/executor.py`, `src/agent/orchestrator.py`, `src/agent/agents/base_agent.py`, `src/services/daily_market_context.py`, `src/daily_market_context_guardrail.py` only consume LLM and market review context within existing read pipelines without adding `SystemConfig` save or writeback branches. Official compatibility basis follows `LiteLLM OpenAI-compatible` and `OpenAI Chat Completion` (see "Compatibility Evidence and Verification Boundaries" below); rollback method is standard release rollback (reverting related commits), optionally with restart and clearing `env_file` / `--env-file` / process-level same-name environment overrides to restore user historical persisted configuration.
**Compatibility evidence and verification boundaries:** This round only reuses existing LLM configuration pipeline reads without adding `.env` write branches, configuration migration/cleanup/writeback entry points. Official basis follows: `LiteLLM OpenAI-compatible` <https://docs.litellm.ai/docs/providers/openai_compatible>, `OpenAI Chat Completion` <https://platform.openai.com/docs/api-reference/chat/create>; version constraints per `requirements.txt` (`litellm`, `openai`) current window. Traceable code paths: `main.py::_bootstrap_environment`, `src/analyzer.py::_init_litellm`, `src/agent/agents/base_agent.py::_get_analyzer_config` (read-only), `src/agent/executor.py`, `src/agent/orchestrator.py`, `src/core/pipeline.py`, `src/services/daily_market_context.py`, `src/daily_market_context_guardrail.py`. Regression verification points: `tests/test_config_env_compat.py`, `tests/test_config_registry.py`, `tests/test_system_config_service.py`, `tests/test_system_config_api.py`, `tests/test_llm_channel_config.py`, `tests/test_market_review_runtime.py`.

Standard analysis and Agent analysis only receive low-sensitivity fields: `daily_market_context` (region, trade_date, summary, risk_tags, source, optional position_cap) and `daily_market_context_summary` prompt segment, not passing full `market_review_payload`, raw news, keys, or notification configuration. Standard analysis prompt inserts the market summary after the market phase section and before technical data; Agent single and multi-agent paths insert the same summary after market phase and before pre-fetched data. Agent free chat only injects when the caller has already provided `daily_market_context` / `daily_market_context_summary`; it does not auto-trigger market review for every chat.

Result post-processing adds a conservative market environment guardrail: when the summary or tags indicate `high_risk`, `market_cooling`, `conservative`, `low_position_cap`, and the context is conservative/high-risk, the model giving a `buy` decision (including "buy immediately/chase/aggressive add") is softened to wait-and-see or small-position wait-for-confirmation, and high confidence is reduced to medium. This guardrail only modifies the current `AnalysisResult` and dashboard low-sensitivity limit notes, without adding database tables or API fields. Rollback method is reverting #1381 related services, prompt injection, and guardrail code; existing market review history records remain compatible.

## P4 History, Task Status, and Web Visibility

P4 projects the P3-built `AnalysisContextPack` into a public low-sensitivity `analysis_context_pack_overview`. This overview is generated by a dedicated renderer; the public API does not allow directly returning `AnalysisContextPack.to_safe_dict()` or full pack dumps. Renderer only outputs whitelisted fields: `pack_version`, `created_at`, `subject.code` / `stock_name` / `market`, data block `key` / `label` / `status` / `source` / `warnings` / `missing_reasons`, `counts` by block status, top-level `data_quality.warnings`, and `metadata.trigger_source` / `metadata.news_result_count`. P5 adds `data_quality` low-sensitivity object to the same overview without duplicating top-level `warnings`.

Overview does not output `blocks.*.items`, `items.value`, `news.content`, `trend_result`, `chip`, `fundamental_context` raw payloads, nor `api_key`, `token`, `cookie`, `webhook_url`, `password`, `secret`, `authorization`, `sendkey`, `license_key` sensitive keys or values.

P4 persistence surface only writes `analysis_context_pack_overview` at the top level of `analysis_history.context_snapshot`. Runtime prompt fields are still stripped from `enhanced_context` and history snapshots: `market_phase_context`, `analysis_context_pack`, `analysis_context_pack_summary` do not enter public history details or task status. When `SAVE_CONTEXT_SNAPSHOT=false`, the entire `analysis_history.context_snapshot` is not persisted, so the overview, `market_phase_summary`, `enhanced_context`, or raw snapshot fields are also not written to the database; old records or records missing the overview continue returning empty fields without affecting history detail reads.

Public API field is fixed at `report.details.analysis_context_pack_overview`; Web reads `analysisContextPackOverview` after deep camelCase. Connection surfaces include:

- `GET /api/v1/history/{record_id}` history details.
- Synchronous `POST /api/v1/analysis/analyze` returned `AnalysisResultResponse.report.details`, but overview depends on persisted `analysis_history.context_snapshot`; when `SAVE_CONTEXT_SNAPSHOT=false`, new records do not guarantee returning overview.
- Completed `GET /api/v1/analysis/status/{task_id}`, including in-memory queue enrichment and DB completed fallback.

API returning `details.context_snapshot` to Web strips top-level `analysis_context_pack_overview` via `sanitize_context_snapshot_for_api()` to avoid raw snapshot panel duplication or being exported as full context; overview is only separately extracted via `extract_analysis_context_pack_overview()`. Agent path and standard analysis path write the same overview shape; Agent without news count may have `metadata.news_result_count` as null.

P4 Web display only renders `AnalysisContextSummary` on report detail pages, positioned after strategy points and news and before run diagnostics; this area defaults to collapsed, with the collapsed header showing available count, missing count, non-zero other status counts, and trigger source; expanded it shows data block status badges, source, warning, missing reason, status counts, and news result count. After P5, collapsed header also shows quality score/level, expanded shows `limitations` and `fetch_failed` status. When no overview exists, no placeholder is rendered. In #1386 P4b, Web displays `report.meta.market_phase_summary` phase tags on the same report detail page and continues reusing this low-sensitivity data quality summary; does not expand full pack, prompt summary, raw payload, or snapshot internal field public surfaces. P4/P5 does not cover pending/processing TaskPanel AnalysisContextPack data quality summaries or SSE in-progress overview visibility, does not change notification summaries, Bot/Desktop dedicated display, or `market_review` overview.

## P5 Data Quality Scoring and Prompt Data Limits

P5 completes three items without upgrading `PACK_VERSION`, adding new fetchers, new configuration items, or historical migration: internal low-sensitivity data quality scoring, cross-model-agnostic prompt data limit blocks, and expanded low-sensitivity visibility for existing `analysis_context_pack_overview`. #1389 P5 still does not change LLM output JSON schema or do post-processing forced rewriting; #1386 P5 consumes the low-sensitivity input quality here, outputting intraday action fields and quality guardrail results in report `dashboard.phase_decision`.

Status contract adds `fetch_failed` for "current field or data block explicitly failed this fetch". First version only used when existing artifacts explicitly fail, e.g., `fundamental_context.status == "failed"`; empty news, unconfigured search, no realtime quote artifact, or missing chip retain existing `missing` / `not_supported` semantics to avoid misreporting un-enabled capabilities as fetch failures. `fetch_failed` does not represent full analysis failure.

`DataQuality` adds the following low-sensitivity fields while preserving old `warnings` / `metadata`:

- `overall_score: Optional[int]`: 0-100 total score.
- `level: Optional["good"|"usable"|"limited"|"poor"]`: `>=85 good`, `>=70 usable`, `>=55 limited`, otherwise `poor`.
- `block_scores: Dict[str, int]`: Fixed six-block status scores.
- `limitations: List[str]`: Up to 5 stable limitation descriptions in `block: status` format.

Scoring only calculates the fixed six blocks, not re-normalizing with auxiliary block absence; future new blocks do not automatically affect total score. Weights are fixed as `quote=25`, `daily_bars=25`, `technical=25`, `news=10`, `fundamentals=10`, `chip=5`; status scores are fixed as `available=100`, `partial=75`, `estimated=75`, `not_supported=70`, `fallback=65`, `stale=50`, `missing=35`, `fetch_failed=25`. Total score formula is `round(sum(block_score * weight) / 100)`.

`limitations` prefers listing core blocks `quote` / `daily_bars` / `technical` `stale`, `fallback`, `missing`, `fetch_failed`, `partial`, `estimated`; then lists auxiliary blocks `news` / `fundamentals` / `chip` `fetch_failed`, `fallback`, `stale`. Auxiliary blocks that are merely missing do not enter the limitation list, avoiding interpreting news absence, unconfigured search, or unsupported capabilities as bullish/bearish.

Prompt data limits are only rendered within `format_analysis_context_pack_prompt_section()`, immediately following the pack summary, so standard analysis, single Agent, and multi-agent reuse the same consumption path. Chinese output is `Data limits`, English output is `Data Limitations`; score line is only output when a real score exists. When `quote`, `daily_bars`, or `technical` are in degraded status, the prompt explicitly requires the final JSON `confidence_level` to not be `high` / `High`. Prompt continues using only status/source/warnings/missing_reason/low-sensitivity scoring without outputting raw payloads, news text, trend raw values, secrets, tokens, or webhooks.

#1386 P2-full adds a minimal `phase × degraded data` cross-constraint after P5 score/limitations and before confidence/safety: when `AnalysisContextPack.phase` comes from a valid `MarketPhaseContext` and `quote`, `daily_bars`, or `technical` have degraded status, the prompt only supplements how current-phase data quality limits intraday judgment, opening plans, or conservative analysis; it does not replace P5's confidence/safety rules or repeat `market_phase_context` phase-only text. When `pack.phase` is missing, non-dict, or contains illegal phase, it fails open, retaining only P5's general data limits.

Overview only extends the existing public surface: `analysis_context_pack_overview.data_quality` whitelist includes `overall_score`, `level`, `block_scores`, `limitations`, without duplicating public `warnings`. `render_analysis_context_pack_overview()` and `extract_analysis_context_pack_overview()` / persisted sanitizer both clean this object; old overviews missing `data_quality` still read normally. `details.context_snapshot` continues stripping top-level `analysis_context_pack_overview` without exposing full pack.

## P6 Alerts, Holdings, History, and Backtest Linkage

#1386 P6 does not add new pack versions nor expose full packs to more public surfaces. It only reuses P4/P5-defined `analysis_context_pack_overview` and #1386-defined `market_phase_summary`:

- Alert trigger records still write to existing `alert_triggers.diagnostics` text field; when diagnostics can be JSON-ified, the worker merges `analysis_visibility.analysis_context_pack_overview`, with source limited to evaluator-carried overview or last 30 days history snapshot. Old pure-text diagnostics are not overwritten; API derived fields are null with source `legacy_text`.
- Holding manual analysis constructs low-sensitivity `portfolio_context` via API and passes it into the pipeline; builder adds an optional `portfolio` block to the pack. This block only contains account ID/name, symbol, market, currency, quantity, avg cost, total cost, unrealized PnL, price source/provider/date/stale/available, and cost method; it does not contain transaction flows, cash flows, news text, prompts, keys, or webhooks.
- `portfolio` block is an auxiliary block with `metadata={"auxiliary": true, "quality_weighted": false}`, not changing P5's fixed six blocks `quote`, `daily_bars`, `technical`, `news`, `fundamentals`, `chip` weights, total score, or limitations caliber.
- `portfolio_context` is only passed through within task execution; `TaskInfo.to_dict()`, task lists, SSE `task_created/task_started/task_completed/task_failed/task_progress` payloads do not expose this object.
- History list, single-stock history, StockBar, and backtest results only read public `market_phase_summary` from `context_snapshot` top level; old records, `SAVE_CONTEXT_SNAPSHOT=false`, or parse failures return `null` / `unknown` without failing.
- Backtest phase filter only buckets based on public summary: `premarket` stays premarket, `intraday|lunch_break|closing_auction` buckets into intraday, `postmarket` stays postmarket, `non_trading|missing|invalid` buckets into unknown. When phase filtering is active, repository first batch-reads results and snapshots by SQL condition, service layer buckets then paginates and counts, avoiding post-API-pagination temporary filtering.
- Notification summary only consumes `market_phase_summary` and `analysis_context_pack_overview.data_quality`, outputting phase, trigger source, partial-bar warning, quality level, and first two limitations; does not output raw pack, `analysis_context_pack_summary` prompt string, news text, or holding-sensitive details.

## P6 Documentation, Migration, and Rollback

P6 does not change P1-P5 runtime behavior, only writing the already-implemented contracts, visibility, configuration, migration, and rollback boundaries into stable documentation. It does not add pack enable/disable feature flags, does not upgrade `PACK_VERSION = "1.0"`, does not add API parameters, does not change report JSON schema, and does not perform database migration.

Four data planes must be understood separately:

| Data Plane | Location | Visibility | P6 Boundary |
| --- | --- | --- | --- |
| Internal full pack | `AnalysisContextPack` / `AnalysisContextBuilder` artifacts | Internal runtime use only | Not a public API, not written to history, no external stable wire contract promised. |
| LLM low-sensitivity summary | `analysis_context_pack_summary` | Standard analysis, single Agent, multi-agent prompts | Only contains subject, pack version, block status/source/warnings/missing reason, news result count, and data limits; does not contain `items.value`, news text, trend/chip/fundamentals raw payloads, secrets, tokens, or webhooks. |
| Public low-sensitivity overview | `report.details.analysis_context_pack_overview` | History details, synchronous analysis responses, completed task status, Web report pages | Only outputs whitelisted fields and `data_quality` low-sensitivity scoring; does not output full pack, prompt summary, or raw payloads. |
| History context snapshot | `analysis_history.context_snapshot` | Persisted for history/API/Web/diagnostic reads | `details.context_snapshot` strips `analysis_context_pack_overview` and `market_phase_summary` via `sanitize_context_snapshot_for_api()`, avoiding raw panel duplication of stable summaries. |

Summary visibility matrix:

| Consumption Surface | Exposed Content | Not Exposed Content |
| --- | --- | --- |
| LLM Prompt | `analysis_context_pack_summary` low-sensitivity status summary and data limits | Full pack, `items.value`, news text, trend/chip/fundamentals raw payloads, secrets/tokens/webhooks |
| `GET /api/v1/history/{record_id}` | `report.details.analysis_context_pack_overview` | Full pack, prompt summary, raw `analysis_context_pack_overview` duplicate |
| Synchronous `POST /api/v1/analysis/analyze` | `report.details.analysis_context_pack_overview`, provided this history has persisted `analysis_history.context_snapshot` | Full pack, prompt summary |
| Completed `GET /api/v1/analysis/status/{task_id}` | `status.result.report.details.analysis_context_pack_overview` | Full pack, prompt summary |
| Web report page | Default-collapsed `AnalysisContextSummary`, showing block status, source, missing reason, quality score, and limits | Full pack, raw payloads, prompt summary |
| Raw `details.context_snapshot` | Stripped history snapshot | Top-level `analysis_context_pack_overview`, `market_phase_summary` |
| Notifications, Bot, Desktop dedicated display | P6 adds no dedicated display | Full pack, prompt summary, raw payloads |

Field quality status complete set remains `available`, `missing`, `not_supported`, `fallback`, `stale`, `estimated`, `partial`, `fetch_failed`. These statuses explain input data quality, not indicating whether analysis tasks, alerts, backtests, or notification delivery themselves succeeded or failed.

Sanitization boundaries:

- Full `AnalysisContextPack` does not enter public API, Web, notifications, Bot, or Desktop dedicated display.
- `AnalysisContextPack.to_safe_dict()` only serves as internal safe serialization helper; public overview must still be projected via `render_analysis_context_pack_overview()`.
- `analysis_context_pack_summary` and overview must not output `items.value`, news text, `trend_result`, `chip`, `fundamental_context` raw payloads, API keys, tokens, cookies, full webhook URLs, email passwords, secrets, authorization, sendkeys, or license keys.
- Persisted overview re-reads must go through `extract_analysis_context_pack_overview()` / persisted sanitizer; API transparency panel must continue stripping top-level stable summaries via `sanitize_context_snapshot_for_api()`.

Migration boundaries:

- P6 does not perform DB migration; old history records missing `analysis_context_pack_overview` or `data_quality` return empty fields; reports still read normally.
- `SAVE_CONTEXT_SNAPSHOT=true` is the default behavior, continuing to persist `analysis_history.context_snapshot` as history transparency and diagnostic source.
- `SAVE_CONTEXT_SNAPSHOT=false` or CLI `--no-context-snapshot` stops persisting the full `analysis_history.context_snapshot`; in other words, new history does not persist the full `analysis_history.context_snapshot`, including `enhanced_context`, `market_phase_summary`, `analysis_context_pack_overview`, `diagnostics`, `realtime_quote_raw`, and other raw snapshot fields.
- Disabling persistence does not affect current `AnalysisContextPack` construction, `analysis_context_pack_summary` prompt injection, or in-memory `result.diagnostic_context_snapshot`.

Rollback methods:

| Method | Effect | Cannot Do |
| --- | --- | --- |
| Release or code rollback of P3-P5 changes | Removes pack prompt summary, overview, and data quality integration | - |
| `SAVE_CONTEXT_SNAPSHOT=false` or `--no-context-snapshot` | Stops saving new history `context_snapshot`, thus no longer exposing overview / phase summary / raw snapshot from new history | Cannot disable current pack construction or low-sensitivity summary in LLM prompts |
| Runtime pack master switch | Currently does not exist | Cannot one-click disable P3-P5 pack integration via env; requires code rollback or separate future design |

## Field Quality Status

Future pack field quality status is fixed in P0 with seven words; P5 adds `fetch_failed` within the same 1.0 umbrella. They describe field or data block quality, not whether business processes succeeded.

| Status | Meaning | Example Boundary |
| --- | --- | --- |
| `available` | Field exists, source and timestamp are interpretable, current path can use it normally. | Realtime quotes return price and source; historical K-line window meets calculation needs. |
| `missing` | Current path needs this field, but it was not fetched or is empty. | DB has no recent daily bars; standard analysis enters `data_missing` result. |
| `not_supported` | Current market, data source, or path does not support this field; should not be misreported as error. | Some markets lack chip distribution or capital flow. |
| `fallback` | Primary source unavailable; fallback source or old path used. | Holding price falls back from realtime quotes to historical close price. |
| `stale` | Field exists, but time freshness is insufficient. | `price_stale` / `fx_stale` in holding valuations. |
| `estimated` | Field is an estimate; should not be treated as complete fact. | Intraday technical estimates generated after supplementing today's bar with realtime prices. |
| `partial` | Data block partially available, partially missing. | Market red-green light `data_quality=partial` or tool returning `partial_cache`. |
| `fetch_failed` | Current path confirms a fetch was attempted, but this fetch failed. | `fundamental_context.status == "failed"` maps to fundamentals block fetch failure. |

## Existing Status Mapping

The repository already has many status words. P0 only establishes mapping or non-mapping relationships to avoid mixing business result status into field quality enums later.

| Existing Word or Field | Current Location | Suggested Relationship | Notes |
| --- | --- | --- | --- |
| `data_missing` | Standard analysis missing historical data result | Can map to `missing` | This is a core input absence, not a business success status. |
| `cache_hit` / `partial_cache` | Agent history data tool | `partial_cache` can map to `partial` | `cache_hit` is source/cache metadata, not quality status. |
| `source` / `data_source` / `realtime_source` | Data source, alerts, context snapshots | Do not map | These are source metadata and should be preserved alongside field quality status. |
| `price_source=missing` | Holding snapshot | Can map to `missing` | Indicates valuation price unavailable. |
| `price_stale` / `fx_stale` | Holding snapshot | Can map to `stale` | Preserves original field as business metadata. |
| `triggered` / `skipped` / `degraded` / `failed` | Alert evaluation and records | Do not map | This is rule evaluation or recording status, not field-level quality status. |
| `insufficient_data` / `completed` / `error` | Backtest service | Do not map | This is backtest execution status; can explain trigger cause in pack summary. |
| `sent` / `no_channel` / `partial_failed` / `all_failed` | Notification delivery | Do not map | This is notification delivery result, cannot back-infer analysis input quality. |
| `data_quality=ok/partial/unavailable` | Market red-green light | `partial` can map; `unavailable` maps to `missing` or `not_supported` per field scenario | P0 does not include market red-green light in first-version single-stock pack. |
| `fetch_failed` | Data quality granularity | P5 maps to `fetch_failed` | Only used when existing artifact explicitly fails, not representing full analysis failure. |

## Seven-Path Inventory

### Standard Analysis

Standard analysis main pipeline assembles inputs in `src/core/pipeline.py`: first reads `storage.get_analysis_context()`, then supplements realtime quotes, chips, trend analysis, news, fundamentals, and report language by availability, finally handing off to `src/analyzer.py` for prompt rendering. Current duplication points are mainly that realtime fields simultaneously exist in `enhanced_context.realtime`, `realtime_quote_raw`, and report meta; naming includes `source`, `data_source`, `realtime_source` and other source fields.

First-version pack can extract single-stock core identity, quotes, daily bars, technical, news, fundamentals, and data quality summaries from the standard analysis path; P0 does not change `_enhance_context()`, `_build_context_snapshot()`, or analyzer prompt.

### Agent

Agent has three data planes that need separate recording. `src/core/pipeline.py`'s Agent path constructs `initial_context`, which always contains `fundamental_context` and adds `trend_result` when available, ultimately persisted as the Agent path's `context_snapshot`. `AgentExecutor._build_user_message()` only applies to `AGENT_ARCH=single`; first-round messages only explicitly inject `realtime_quote`, `chip_distribution`, `news_context` and other fetched context, not explicitly injecting `fundamental_context` or `trend_result`. `AgentOrchestrator._build_context()` applies to `AGENT_ARCH=multi`, can pre-inject `realtime_quote`, `daily_history`, `chip_distribution`, `trend_result`, `news_context`; these fields entering `AgentContext` are injected as pre-fetched data into stage agent messages; but orchestrator does not pre-inject `fundamental_context`. `trend_result` is not inherently present, depending on whether the caller passes it in.

Agent tools also independently call `get_realtime_quote`, `get_daily_history`, `get_chip_distribution`, `get_analysis_context`, `get_stock_info` and other tools, easily generating duplicate requests with standard analysis pre-fetching. Current pack generation only reuses `storage.get_analysis_context()` daily bar availability status after Agent history prefetch, without reusing or exposing full tool-level pack cache; P5 will decide whether to do deeper data quality scoring and tool cache reuse.

### Alerts

Alert pipeline evaluates rules, records trigger history, and distributes notifications in `src/services/alert_worker.py`; see [Real-time Alert Center](alerts.md) for detailed field semantics. Alert statuses like `triggered`, `skipped`, `degraded`, `failed` are rule evaluation or recording statuses and cannot be directly written into field quality enums.

First-version pack does not treat alert rule evaluation as an input data block; alerts only consume pack field quality summaries going forward, such as whether core quotes are fallback, stale, or partial.

### Holdings

Holding snapshots aggregate account, position, cost, price, exchange rate, and risk inputs in `src/services/portfolio_service.py`; API output structure is in `api/v1/schemas/portfolio.py`. Existing fields include `price_source`, `price_provider`, `price_date`, `price_stale`, `price_available`, `fx_stale`, etc.

First-version pack can record "whether holding, account summary, cost, quantity, position, unrealized PnL, price/exchange rate stale summary", but does not include transaction flows, cash flows, corporate actions, or full account privacy data.

### Backtest

Backtest service consumes historical analysis records and daily bar data in `src/services/backtest_service.py` and `src/repositories/backtest_repo.py`. Existing `parse_analysis_date_from_snapshot()` depends on `analysis_history.context_snapshot.enhanced_context.date` to parse analysis dates.

P0 must mark `enhanced_context.date` as a compatibility boundary. Future packs can add clearer date fields, but must not delete or rename the current historical snapshot date position without migration.

### History

History details return `raw_result`, `news_content`, `context_snapshot`, and other fields in `src/services/history_service.py`, `api/v1/endpoints/history.py`, `api/v1/schemas/history.py`. Synchronous analysis/status responses also read `context_snapshot.enhanced_context`, `realtime_quote_raw`, and fundamentals fallback in `api/v1/endpoints/analysis.py`.

P0 only records the history consumption surface. Full pack should not be publicly exposed to history details or public API by default; subsequent P4 if display is needed should prefer exposing summaries, sources, and degradation notes.

### Notifications

Notification pipeline consumes `AnalysisResult`, dashboard, market snapshot, `data_sources` and other outputs in `src/notification.py`, recording `sent`, `no_channel`, `partial_failed`, `all_failed` and other delivery statuses; see [Notification Capabilities Baseline](notifications.md) for channel configuration and boundaries.

Notifications are not a fact data layer; delivery failures should not be miswritten as input quality failures. Going forward, only pack summaries should be consumed when necessary, such as "realtime quotes degraded", "fundamentals missing", "news sources insufficient".

## Source Code Anchors

| Domain | Anchors |
| --- | --- |
| Standard Analysis | `src/core/pipeline.py`, `src/storage.py`, `src/analyzer.py` |
| Agent | `src/agent/orchestrator.py`, `src/agent/executor.py`, `src/agent/tools/data_tools.py` |
| Alerts | `src/services/alert_worker.py`, `docs/alerts.md` |
| Holdings | `src/services/portfolio_service.py`, `api/v1/schemas/portfolio.py` |
| Backtest | `src/services/backtest_service.py`, `src/repositories/backtest_repo.py` |
| History | `src/services/history_service.py`, `api/v1/endpoints/history.py`, `api/v1/endpoints/analysis.py`, `api/v1/schemas/history.py` |
| Notifications | `src/notification.py`, `docs/notifications.md` |

## Compatibility and Safety Boundaries

- `analysis_history.context_snapshot.enhanced_context.date` is the current backtest date parsing compatibility point; P1/P2 must not break it without migration.
- Full pack is not publicly exposed to history, API, Web, or notifications by default; P4/P5 only expose `analysis_context_pack_overview` low-sensitivity summary, source, fallback, stale, missing reason, block status count, and `data_quality` low-sensitivity scoring.
- Pack, logs, history snapshots, and API responses must not record API keys, tokens, cookies, full webhook URLs, email passwords, private environment variables, or other secrets.
- `source`, `timestamp`, `fallback`, `stale`, `partial` and other quality metadata are only used to explain input limitations, not to block analysis; unless the existing core path is inherently fail-fast.
- #1386's pre-market / intraday phase awareness is important background for future `phase` / `data_quality` fields; P0 only records the relationship without connecting to runtime.
