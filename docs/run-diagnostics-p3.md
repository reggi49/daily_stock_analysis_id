# Run Diagnostics & Data Reliability 1.0 (Phase 3)

This document records the delivery scope for #1391 Phase 3: without adding new configuration, completing run diagnostics visibility and backfilling history troubleshooting info into backend context snapshots for faster self-deployed environment anomaly diagnosis.

## Scope of This Round

- History report details add a collapsible "Run Diagnostics / Data Reliability" section; after #1523, the Web display title is adjusted to "Run Diagnostics / Run Status"; the history section title remains unchanged.
- The task panel shows collapsible trace information for in-progress tasks, for correlation with backend logs, SSE, and history report diagnostics.
- History reports fetch diagnostic summaries via read-only API:

```http
GET /api/v1/history/{record_id}/diagnostics
```

- If a synchronous analysis response already includes `diagnostic_summary`, the frontend can display it directly without additional history API requests.
- The diagnostics panel supports copying backend-generated sanitized `copy_text` for issue reporting or deployment troubleshooting.
- The analysis chain backfills task/Provider/LLM/notification diagnostics into `context_snapshot.diagnostics` after history persistence; the history diagnostics interface aggregates these into user-readable summaries.
- The home page Run Flow panel reuses the same RunFlowSnapshot contract to display active tasks, completed reports, and market reviews; active tasks append real-time event streams via optional incremental SSE events, then refetch the snapshot for eventual consistency after completion or disconnection.

## Run Flow Real-Time Incremental Updates

Run flow incremental updates do not add a standalone SSE endpoint; they continue reusing:

```http
GET /api/v1/analysis/tasks/stream
```

Compatibility contract:

- Event type remains `task_progress`.
- Original task payload fields remain unchanged.
- When the progress update comes from run diagnostics, an optional `flow_event` field may be appended; old clients ignore this field.
- `flow_event` uses the same sanitized event structure as `RunFlowSnapshot.events[]`: `id`, `timestamp`, `severity`, `type`, `node_id`, `title`, `message`, `metadata`.
- Active tasks may append `provider_run_started` / `llm_run_started` real-time events; these events are only used for the running card display and are overridden by the `provider_run` / `llm_run` result events of the same `node_id` after completion; history diagnostics still use final results.
- The backend TaskQueue retains only the most recent N run flow events per active task to prevent unbounded memory growth; full history is based on `context_snapshot.diagnostics` and history RunFlowSnapshot.

Example:

```json
{
  "task_id": "3f87...",
  "trace_id": "3f87...",
  "stock_code": "600519",
  "status": "processing",
  "progress": 64,
  "message": "LLM is generating analysis results",
  "flow_event": {
    "id": "flow_0002",
    "timestamp": "2026-06-08T22:30:24",
    "severity": "success",
    "type": "llm_run",
    "node_id": "llm_analysis_1",
    "title": "LLM Success",
    "message": "LLM deepseek-chat succeeded"
  }
}
```

Run diagnostic record functions trigger the event sink with fail-open semantics after provider, LLM, history persistence, and notification records are successfully written to in-memory diagnostics. Sink failures only log a warning and do not change the success/failure determination of analysis, persistence, or notifications.

News intelligence search is also integrated into the same provider diagnostic semantics: `SearchService.search_stock_news()` records `data_type=news_search` for search providers such as Tavily, SearXNG, Bocha, and Brave, including attempt count, filtered result count, cache hit, and failure reasons. When multiple search providers attempt sequentially, the Web Run Flow main diagram aggregates them into a single "News Sentiment" node by default, with the card showing the provider chain and status, and the node detail showing success/failure counts and fallback/retry counts; for troubleshooting, you can expand this aggregated node to view individual provider attempts.

The Run Flow topology data source lane is primarily sorted by node start time; if a provider/LLM node only has completion time and duration, `started_at` is derived from `ended_at - duration_ms` and displayed on the card. Nodes without available time retain the original display order as fallback. The main diagram expresses the flow structure of "Entry -> Data Source -> ContextPack -> LLM -> Persistence/Notification"; full troubleshooting details are preserved in the event stream, node details, and aggregated node expanded state.

The Web Run Flow main diagram uses the frontend internal display model, without changing the backend `RunFlowSnapshot` contract:

- Provider attempts are aggregated by `metadata.data_type` into data source nodes, e.g., realtime quotes, daily data, news sentiment.
- `context_block_*` nodes collapse into `ContextPack` details by default to avoid mixing with provider attempts in the data source lane.
- Clicking an aggregated node shows an attempts table in the detail area; after clicking "Show Attempts", the child provider nodes of the current aggregate group return to the topology.
- The event stream still displays complete events; event-associated nodes map to currently visible nodes, pointing to the aggregate node when collapsed and to specific attempts when expanded.
- Topology connections use a multi-connection strategy: horizontal main flow uses left/right ports, same-lane vertical relationships use bottom-to-top, and fallback/retry continues using text labels and dashed line styles.

## Run Flow API

```http
GET /api/v1/analysis/tasks/{task_id}/flow
GET /api/v1/history/{record_id}/flow
```

- Both endpoints return the same `RunFlowSnapshot` contract.
- Active tasks missing diagnostics return a skeleton flow without fabricating provider / LLM events.
- Active tasks with recent `flow_event` data return these real events in the snapshot, and can construct temporary nodes based on node metadata in the events.
- Completed history prioritizes building the full topology from `context_snapshot.diagnostics` and `analysis_context_pack_overview`.
- Market review history records use `code=MARKET`, `report_type=market_review`, and use the same `/history/{record_id}/flow` and Web Run Flow panel without a separate UI fork.
- `cancel_requested` and `cancelled` are valid run flow states; user cancellation should not be mapped to `failed`.

## Run Flow View

The Run Flow view is a visual troubleshooting entry point above the run diagnostic summary, used to trace the approximate path of a single analysis from trigger, data retrieval, ContextPack assembly, LLM generation, to persistence/notification. It does not replace the diagnostic summary's `copy_text`; instead it organizes the same batch of sanitized diagnostic evidence into nodes, connections, events, and summary metrics for quick anomaly or degradation identification from the Web home page.

The backend provides two read-only snapshot endpoints:

```http
GET /api/v1/analysis/tasks/{task_id}/flow
GET /api/v1/history/{record_id}/flow
```

- `tasks/{task_id}/flow` targets active tasks. When the task is still in the in-memory queue, the current task snapshot is returned; when the task is completed, it attempts to read history diagnostics by the same `task_id/query_id`. Missing diagnostics return a skeleton flow without fabricating provider, LLM, or notification events.
- `history/{record_id}/flow` targets history reports, supporting history record primary key IDs or parseable `query_id`. Individual stock analysis and `MARKET/market_review` market review share the same `RunFlowSnapshot` contract.
- When the same page triggers individual stock analysis, the stock flow can generate or reuse the daily market context as needed; this is not an independent analysis step but Prompt background generation. The backend uses a separate `market_context_*` query_id with `scope=daily_market_context` to persist this market context, avoiding shared query_id with stock reports.
- For compatibility with early mixed diagnostics, the run flow filters by report type during history reads with low-risk filtering: `MARKET/market_review` records hide individual stock quotes, daily data, technical, fundamentals, and chip provider nodes; individual stock records hide pre-first-stock market news search and pre-first-stock LLM market persistence/notification nodes.
- Notification skip or unconfigured scenarios allow `attempts=0`; the run flow displays as skipped without causing `/flow` to return 500 due to Pydantic validation failure.
- Snapshot top-level includes `summary`, `lanes`, `nodes`, `edges`, `events`, and `generated_at`. Node status uses `pending/running/success/failed/degraded/fallback/timeout/cancel_requested/cancelled/skipped/unknown`, where user cancellation states are not mapped to `failed`.
- For old history, missing `context_snapshot.diagnostics`, or insufficient evidence, the backend returns `unknown` or skeleton nodes; the Web side displays as empty/unknown status without affecting report detail reading.

Web entry points:

- The home page active task card provides a run flow entry; opening the drawer fetches the task snapshot by `task_id`.
- History report summary and run diagnostics section provide a run flow entry; opening the drawer fetches the history snapshot by history record ID.
- The panel displays summary, basic topology, event stream, and node details; complex topology aggregation, real-time incremental events, and layout polish will continue in subsequent phases.

Sanitization and compatibility boundaries:

- Run flow only reads existing task information, history results, and low-sensitivity diagnostic fields from `context_snapshot.diagnostics`; it adds no new configuration items, does not change database structure, and does not migrate old history.
- `model`, `provider`, `fallback_model` are only for displaying actual diagnosed call information; they do not participate in model selection, request routing, Base URL resolution, or configuration saving.
- `metadata`, error messages, and local paths undergo backend trimming and sanitization to avoid exposing API keys, tokens, cookies, webhooks, prompt/raw response, proxy headers, and local absolute paths.
- During rollback, Web entry points and query paths can be removed; the backend's new read-only snapshot endpoints do not change the success/failure semantics of existing analysis, history, notification, or diagnostic summary interfaces.

## Status Text

Overall status:

- `normal`: Normal
- `degraded`: Partially degraded
- `failed`: Failed
- `unknown`: Unknown

Component status:

- `ok`: Normal
- `degraded`: Degraded after recent failure
- `failed`: Failed
- `unknown`: Unknown
- `not_configured`: Not configured
- `skipped`: Skipped

## Interaction Boundaries

- The diagnostics section is collapsed by default to avoid crowding out main report content.
- The initial view shows only overall status, primary cause, and essential trace info.
- Component status and advanced JSON fields are placed in the expanded area; advanced fields are further collapsible to avoid information overload.
- Old reports, failed interfaces, or insufficient evidence show `unknown` without affecting report reading.

## Compatibility Boundaries

- This round adds no `.env` configuration items, does not modify database structure, and introduces no data migration.
- The Web only consumes optional fields appended in Phase 1/2 and read-only diagnostic interfaces; the backend completes diagnostic persistence and refresh logic in `src/core/pipeline.py`, `src/services/run_diagnostics.py`, `src/storage.py`, and `src/services/history_service.py`, providing readable endpoints via `api/v1/endpoints/history.py`.
- Backend changes include task orchestration, post-persistence backfill, history diagnostic queries, and notification result diagnostic records; these chains only append `context_snapshot.diagnostics` snapshots and summaries without changing the analysis main flow, notification send success/failure semantics, or history report main fields.
- Copy text is generated and sanitized by the backend; the frontend is only responsible for display and copying.
- Desktop reuses Web build artifacts without separately modifying the Electron main process or packaging scripts.
- Runtime configuration/model/provider/base_url compatibility semantics are not adjusted: besides the diagnostic persistence chain, provider priority, LiteLLM routing, runtime cleanup, and configuration fallback logic remain unchanged.
- Old history and old configuration compatibility rules remain unchanged: the new optional fields in history diagnostic queries do not affect existing history query response parsing; rollback involves removing this round's display and related frontend query paths, or restoring models and configurations per existing guides.
- Rollback strategy: prioritize rolling back frontend display and query entry points; to fully isolate new chains, roll back this round's PR (after rollback, history records retain original responses and the new diagnostic endpoints are no longer displayed in Web).

### Structured Detection Clarification

This round's review's structured detection flagged external model/API compatibility and runtime configuration migration risks; re-examination conclusions:

- Model name/provider/Base URL: This round does not add, replace, or reorder any model names, providers, Base URLs, channels, or fallback defaults, nor does it change parsing priority for `LITELLM_MODEL`, `AGENT_LITELLM_MODEL`, `VISION_MODEL`, `LITELLM_FALLBACK_MODELS`, `OPENAI_*`, `GEMINI_*`, `ANTHROPIC_*`, or `DEEPSEEK_*`.
- SDK/dependency defaults: This round does not modify `requirements.txt`, `package.json` dependency constraints, or LiteLLM/OpenAI-compatible call default parameters; external references remain based on official documentation and current locked dependency descriptions recorded in `docs/llm-providers.md` and `docs/LLM_CONFIG_GUIDE*.md`.
- Pre-save cleanup/configuration migration: This round does not trigger migration, cleanup, deletion, or writeback strategy changes for `.env`, Web settings page channels, desktop user data directories, Docker runtime configuration files, or old configurations.
- The actual runtime changes in this round only write existing analysis traces, provider/LLM/notification results, and sanitized error summaries into `context_snapshot.diagnostics`, displayed via history read-only interfaces and Web default-collapsed panels; diagnostic record failures are handled with fail-open, not changing analysis or notification success/failure determination.
- Therefore, this is a structured detection false positive/documentation clarification; no new official sources, old configuration migration steps, or provider rollback paths need to be executed. For rollback, remove the diagnostic display/query entry points per this section's rollback strategy; model and runtime configuration recovery paths remain unchanged.

## Compatibility Regression & Verification (Key Evidence Before PR Merge)

- Backend regression coverage:
  - `tests/test_pipeline_market_phase_context.py`
  - `tests/test_realtime_types.py`
  - `tests/test_scheduler_background.py`
  - `tests/test_analysis_api_contract.py` (subset: diagnostic context input/output/status query contracts)
  - `tests/test_analysis_history.py` (subset: history API and persistence chain)
- Coverage relationships: API contracts are covered by `tests/test_analysis_api_contract.py` and `tests/test_analysis_history.py`; task orchestration, history persistence, and `context_snapshot.diagnostics` are covered by `tests/test_pipeline_market_phase_context.py`; notification paths are covered by the existing notification regression and import checks in `./scripts/ci_gate.sh`.
- Regression commands (must confirm all pass before PR merge):

```bash
./scripts/ci_gate.sh
python -m pytest tests/test_realtime_types.py tests/test_scheduler_background.py tests/test_pipeline_market_phase_context.py tests/test_analysis_api_contract.py tests/test_analysis_history.py
cd apps/dsa-web && npm run lint && npm run build
```

## Verification Recommendations

```bash
cd apps/dsa-web
npm run lint
npm run build
```

Optional supplementary execution (non-blocking):

```bash
cd apps/dsa-web
npm test -- --run src/components/report/__tests__/ReportDiagnostics.test.tsx src/components/tasks/__tests__/TaskPanel.test.tsx src/hooks/__tests__/useTaskStream.test.tsx
```

Optional deterministic script verification:

```bash
python -m py_compile api/v1/endpoints/analysis.py api/v1/endpoints/history.py api/v1/schemas/analysis.py api/v1/schemas/history.py src/core/pipeline.py src/services/run_diagnostics.py src/storage.py
```

## Rollback

Minimum rollback method: revert the Phase 3 PR. Since this round is an optional field and read-only interface enhancement, after rollback, backend history snapshots and persisted data are retained, and Web no longer displays the diagnostics panel and trace diagnostic entry point.
