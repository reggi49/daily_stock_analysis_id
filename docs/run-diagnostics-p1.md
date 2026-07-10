# Run Diagnostics & Data Reliability 1.0 (Phase 1)

This document records the minimal runtime scope for #1391 Phase 1: unifying `trace_id` and recording structured provider attempts for the first batch of critical data paths.

## Scope of This Round

- API / Web async task creation: `TaskInfo` uses `task_id` as the default `trace_id`.
- Task list, task status, and SSE events add the `trace_id` field; old clients may ignore it.
- Synchronous analysis uses the current `query_id` as the default `trace_id`.
- The pipeline establishes a lightweight diagnostic context at runtime, spanning daily data preparation and individual stock analysis.
- `data_provider/base.py` records `ProviderRun`-style events for the following paths:
  - `daily_data`
  - `realtime_quote`
- Diagnostic records are written to an in-memory context and saved with the analysis `context_snapshot.diagnostics`; old history records missing this field maintain compatibility.

## `ProviderRun` Fields

Minimal fields for v1:

- `trace_id`
- `data_type`
- `provider`
- `operation`
- `success`
- `latency_ms`
- `error_type`
- `error_message_sanitized`
- `fallback_to`
- `record_count`
- `created_at`

Error summaries undergo basic sanitization to avoid outputting tokens, API keys, Authorization headers, cookies, webhook URLs with sensitive parameters, etc.

## Stability Boundaries

- Diagnostic record failures only log a warning; they do not affect the main analysis, data source fallback, or history persistence.
- This round adds no new configuration items, does not change data source priorities, and does not alter fallback strategies.
- This round adds no new Web display components; `trace_id` and provider runs first enter API/SSE/history snapshots for reuse by subsequent Phase 2/3 aggregation and display.

## Verification Recommendations

```bash
python -m pytest tests/test_run_diagnostics_p1.py tests/test_analysis_api_contract.py::AnalysisApiContractTestCase::test_get_analysis_status_normalizes_completed_queue_result_contract
python -m py_compile src/services/run_diagnostics.py src/services/task_queue.py src/services/analysis_service.py src/core/pipeline.py data_provider/base.py api/v1/schemas/analysis.py api/v1/endpoints/analysis.py
```
