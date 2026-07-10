# Run Diagnostics & Data Reliability 1.0 (Phase 2)

This document records the backend scope for #1391 Phase 2: based on Phase 1's `trace_id` and provider run records, generating user-readable run diagnostic summaries with copyable sanitized troubleshooting text.

## Scope of This Round

- New `RunDiagnosticSummary` aggregation logic, outputting overall status:
  - `normal`
  - `degraded` (partially degraded)
  - `failed`
  - `unknown`
- Summary covers the following critical paths:
  - Realtime quotes
  - Daily data
  - News search
  - LLM
  - Notifications
  - History persistence
- `AnalysisService` sync/async task results add optional `diagnostic_summary`.
- New history report diagnostic API:

```http
GET /api/v1/history/{record_id}/diagnostics
```

`record_id` accepts a history record primary key ID or `query_id`, returning the diagnostic summary and `copy_text`.

## Copyable Troubleshooting Info

`copy_text` is plain text for issues/troubleshooting, containing:

- `trace_id`
- `query_id`
- `stock_code`
- `trigger_source`
- Overall `data_status`
- Brief status for realtime quotes, daily data, news, LLM, notifications, and history persistence
- Primary cause

Before generation, it reuses run diagnostic sanitization rules to avoid outputting tokens, API keys, Authorization headers, cookies, webhook URLs, email passwords, proxy credentials, or other sensitive information.

## Compatibility Boundaries

- This round adds no new configuration items, does not change data source priorities, and does not alter fallback strategies.
- This round does not modify any LLM/provider/Base URL/configuration migration semantics; it only adds diagnostic fields and query interfaces in history snapshots.
- The API only appends optional fields and adds new read-only interfaces; old clients may ignore them.
- Old reports without `context_snapshot.diagnostics` return `unknown` without errors.
- Notification diagnostics are recorded in the current task context; if history reports have no notification evidence at save time, the summary shows the notification result as unknown.
- Diagnostic summary generation failures must not affect report reading or the analysis main flow.

### Structured Detection Alert Clarification

- The "model/provider/base URL compatibility risk" flagged by automated detection comes from: `src/agent/factory.py` adding **numeric safety fallbacks** (`_coerce_config_int`) for `agent_max_steps` and `agent_orchestrator_timeout_s`, so the scan may misidentify it as a configuration-sensitive path; this hit is triggered by test and routing protection, not a runtime configuration or compatibility semantic change.
- When a numeric configuration has an invalid value, the system logs a `warning` to `src.agent.factory` (example: `[AgentFactory] Invalid value for agent_max_steps...`) and falls back to the default value; the log is for diagnosing "parameter not taking effect" issues, independent of model/provider/base URL compatibility.
- This round confirms no silent migration/clearing/rewriting:
  - `src/core/pipeline.py` and `src/services/analysis_service.py` only add diagnostic records, not modifying any `litellm_model`, `agent_litellm_model`, `openai_base_url`, or channel `LLM_*` fields in `Config`.
  - `src/agent/factory.py`'s `_coerce_config_int` only computes `max_steps` and `timeout_seconds` when building execution parameters and does not write back to the `config` object; `litellm_model`, `agent_litellm_model`, and `openai_base_url` original values are fully passed through in the construction chain.
  - This round does not trigger `Config` runtime cleanup, persistence writeback, or migration flows, so there is no risk of runtime configuration being rewritten.
- Regression verification: `tests/test_agent_pipeline.py::TestAgentConfig::test_build_agent_executor_does_not_mutate_llm_route_config` and `tests/test_agent_pipeline.py::TestAgentConfig::test_build_agent_executor_multi_arch_does_not_mutate_llm_route_config` explicitly assert that the above fields retain their original values after `build_agent_executor`.
- Rollback path: To restore old behavior, remove this round's related commits; or remove `diag_*` fields from the `context_snapshot`/`RunDiagnosticSummary` deserialization chain. No additional migration or fixes are needed for the main chain or model/provider configuration.

## Verification Recommendations

```bash
python -m pytest tests/test_run_diagnostics_p2.py tests/test_run_diagnostics_p1.py
python -m py_compile src/services/run_diagnostics.py src/services/history_service.py api/v1/endpoints/history.py api/v1/schemas/history.py
```
