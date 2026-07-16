# -*- coding: utf-8 -*-
"""Contract checks for the AnalysisContextPack P0/P1 contract doc."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "analysis-context-pack.md"
FULL_GUIDE_PATH = PROJECT_ROOT / "docs" / "full-guide.md"
FULL_GUIDE_EN_PATH = PROJECT_ROOT / "docs" / "full-guide_EN.md"


def _read_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def _section(doc: str, heading: str) -> str:
    marker = f"## {heading}"
    assert marker in doc
    return doc.split(marker, 1)[1].split("\n## ", 1)[0]


def test_analysis_context_pack_doc_has_required_sections() -> None:
    doc = _read_doc()

    for heading in (
        "## Terms and Boundaries",
        "## P0 Scope and non-target",
        "## P1 internal contract",
        "## P2 Builder contract",
        "## P3 Runtime Consumption",
        "## P4 History、task status and Web visibility",
        "## P5 Data quality score vs. Prompt Data limits",
        "## P6 Documentation、Migration and rollback",
        "## Field quality status",
        "## Existing state mapping",
        "## Seven Paths Inventory",
        "## source code anchor",
        "## Compatibility and security boundaries",
    ):
        assert heading in doc


def test_analysis_context_pack_doc_disambiguates_context_surfaces() -> None:
    section = _section(_read_doc(), "Terms and Boundaries")

    for token in (
        "`storage.get_analysis_context()`",
        "`enhanced_context`",
        "`analysis_history.context_snapshot`",
        "Agent executor message context",
        "Agent orchestrator `AgentContext`",
        "`AGENT_ARCH=single`",
        "`AGENT_ARCH=multi`",
    ):
        assert token in section


def test_analysis_context_pack_doc_defines_p0_quality_states() -> None:
    section = _section(_read_doc(), "Field quality status")

    for state in (
        "`available`",
        "`missing`",
        "`not_supported`",
        "`fallback`",
        "`stale`",
        "`estimated`",
        "`partial`",
        "`fetch_failed`",
    ):
        assert state in section
    assert "P0 First fix the seven words" in section
    assert "P5 in the same 1.0 umbrella Append within `fetch_failed`" in section


def test_analysis_context_pack_doc_covers_seven_paths() -> None:
    section = _section(_read_doc(), "Seven Paths Inventory")

    for heading in (
        "### General analysis",
        "### Agent",
        "### Alarm",
        "### Position",
        "### backtest",
        "### history",
        "### Notification",
    ):
        assert heading in section


def test_analysis_context_pack_doc_records_agent_context_visibility() -> None:
    section = _section(_read_doc(), "Seven Paths Inventory")

    for token in (
        "`initial_context`",
        "`fundamental_context`",
        "No explicit injection `fundamental_context` or `trend_result`",
        "pre-fetched data",
        "No pre-injection `fundamental_context`",
    ):
        assert token in section


def test_analysis_context_pack_doc_records_non_goals_and_safety_boundaries() -> None:
    doc = _read_doc()

    for token in (
        "P1 Added `AnalysisContextPack` internal schema",
        "No new addition builder",
        "Not connected runtime",
        "Undisclosed complete pack",
        "No pack ization `market_review`",
        "`market_light`",
        "P5 Already in the same 1.0 umbrella Add this status within",
        "`analysis_history.context_snapshot.enhanced_context.date`",
        "complete pack Not public by default",
        "API key",
        "token",
        "cookie",
        "complete webhook URL",
        "Email password",
    ):
        assert token in doc


def test_analysis_context_pack_doc_defines_p1_schema_contract() -> None:
    section = _section(_read_doc(), "P1 internal contract")

    for token in (
        "`src/schemas/analysis_context_pack.py`",
        "`PACK_VERSION = \"1.0\"`",
        "`ContextFieldStatus`",
        "`AnalysisSubject`",
        "`AnalysisContextItem`",
        "`AnalysisContextBlock`",
        "`DataQuality`",
        "`AnalysisContextPack`",
        "`MarketPhaseContext.to_dict()`",
    ):
        assert token in section


def test_analysis_context_pack_doc_records_p1_block_catalog() -> None:
    section = _section(_read_doc(), "P1 internal contract")

    for token in (
        "P1 Block Catalog",
        "`quote`",
        "`daily_bars`",
        "`technical`",
        "`fundamentals`",
        "`news`",
        "`portfolio`",
        "`chip` / `capital_flow`",
        "`events` / `market_context`",
        "No duplicate addition `identity` block",
    ):
        assert token in section


def test_analysis_context_pack_doc_records_p1_time_and_status_semantics() -> None:
    section = _section(_read_doc(), "P1 internal contract")

    for token in (
        "`AnalysisContextPack.created_at` Use `datetime`",
        "`model_dump(mode=\"json\")` output ISO 8601",
        "`AnalysisContextItem.timestamp`",
        "`AnalysisContextBlock.timestamp`",
        "Optional[str]",
        "Verification at construction time",
        "date-only",
        "`block.status` Indicates overall block availability",
        "`item.status` Represents field-level quality",
        "Not realized `item.status` Arrive `block.status` Automatic aggregation derivation of",
    ):
        assert token in section


def test_analysis_context_pack_doc_records_p1_redaction_contract() -> None:
    section = _section(_read_doc(), "P1 internal contract")

    for token in (
        "`AnalysisContextPack.to_safe_dict()`",
        "`redact_sensitive_mapping()`",
        "`api_key`",
        "`access_token`",
        "`authorization_header`",
        "`webhook_url`",
        "`license_key`",
        "[REDACTED]",
        "`data_api`",
        "Do not scan plain string values",
        "Don't do it URL regular desensitization",
    ):
        assert token in section


def test_analysis_context_pack_doc_keeps_later_phases_out_of_p1() -> None:
    section = _section(_read_doc(), "P1 internal contract")

    for token in (
        "Runtime data is not populated",
        "No new addition fetcher",
        "Do not change Prompt",
        "Do not write history/task/report metadata",
        "not complete pack exposed to API、Web、Bot、Desktop or notice",
        "P2 builder",
        "P3 runtime",
    ):
        assert token in section


def test_analysis_context_pack_doc_defines_p2_builder_boundaries() -> None:
    section = _section(_read_doc(), "P2 Builder contract")

    for token in (
        "`AnalysisContextBuilder`",
        "assembler",
        "pipeline Already fetch",
        "zero-fetch",
        "`PipelineAnalysisArtifacts`",
        "`code`、`stock_name`、`market`",
        "`price_stale`",
        "`quote_stale`",
        "`intraday_realtime_overlay`",
        "`fetch_failed`",
        "P3 runtime",
        "Do not change Prompt",
        "Do not write history/task/report metadata",
    ):
        assert token in section


def test_analysis_context_pack_docs_record_issue_1386_p3_quality_boundaries() -> None:
    section = _section(_read_doc(), "P2 Builder contract")

    for token in (
        "`fetched_at`",
        "`provider_timestamp`",
        "`is_stale`",
        "`stale_seconds`",
        "`fallback_from`",
        "`STALE > FALLBACK > AVAILABLE`",
        "builder Only map upstream artifact，No quality rating",
        "`is_partial_bar`、`is_estimated`、`estimated_fields`",
        "`daily_bars` Not carrying partial/estimated",
    ):
        assert token in section

    full_guide = FULL_GUIDE_PATH.read_text(encoding="utf-8")
    full_guide_en = FULL_GUIDE_EN_PATH.read_text(encoding="utf-8")
    assert "Intraday packets and real-time quality control（Issue #1386 P3）" in full_guide
    assert "source` Keep actual success data sources token" in full_guide
    assert "`AnalysisContextBuilder` Map only these upstreams artifact" in full_guide
    assert "daily_bars` block still express storage Medium complete daily window" in full_guide
    assert "Intraday Data Packet and Realtime Quality Control (Issue #1386 P3)" in full_guide_en
    assert "source` keeps the actual successful provider token" in full_guide_en


def test_analysis_context_pack_doc_defines_p3_runtime_consumption_boundaries() -> None:
    section = _section(_read_doc(), "P3 Runtime Consumption")

    for token in (
        "`StockAnalysisPipeline` Yes summary sole producer of",
        "`PipelineAnalysisArtifacts` -> `AnalysisContextBuilder.build()`",
        "`format_analysis_context_pack_prompt_section()`",
        "`analysis_context_pack_summary`",
        "Basic information -> #1386 `market_phase_context` render block -> `analysis_context_pack_summary`",
        "`news.content`、`trend_result`、`chip`、`fundamental_context` Wait for original payload",
        "`AgentExecutor._build_user_message()`",
        "`AgentOrchestrator._build_context()`",
        "`ctx.meta[\"analysis_context_pack_summary\"]`",
        "Disable writing `ctx.data`",
        "`BaseAgent._build_messages()`",
        "`_inject_cached_data()`",
        "`news` block for `missing` is current P3 expected state",
        "`analysis_history.context_snapshot`",
        "`analysis_context_pack`",
        "`analysis_context_pack_summary`",
        "Agent Tool level pack cache Reuse",
        "P4 On this basis, add hypoallergenic overview",
        "P5 Continue to reuse summary Consumption path",
    ):
        assert token in section

    assert "P3-min" not in section


def test_analysis_context_pack_doc_defines_p4_visibility_contract() -> None:
    section = _section(_read_doc(), "P4 History、task status and Web visibility")

    for token in (
        "`analysis_context_pack_overview`",
        "dedicated renderer",
        "`AnalysisContextPack.to_safe_dict()`",
        "`report.details.analysis_context_pack_overview`",
        "`analysisContextPackOverview`",
        "`GET /api/v1/history/{record_id}`",
        "sync `POST /api/v1/analysis/analyze`",
        "overview Dependencies are persisted `analysis_history.context_snapshot`",
        "completed `GET /api/v1/analysis/status/{task_id}`",
        "`sanitize_context_snapshot_for_api()`",
        "`extract_analysis_context_pack_overview()`",
        "`items.value`",
        "`trend_result`",
        "`fundamental_context`",
        "`SAVE_CONTEXT_SNAPSHOT=false`",
        "Not persisting the entire copy `analysis_history.context_snapshot`",
        "`market_phase_summary`",
        "`enhanced_context`",
        "`AnalysisContextSummary`",
        "The position is after strategic points and information、Before running diagnostics",
        "Default folded",
        "Count of other non-zero states",
        "Not covered pending/processing TaskPanel",
        "No change notification summary",
        "quality points/level",
        "`fetch_failed` Status",
    ):
        assert token in section

    assert "After running diagnostics、Before strategic point" not in section


def test_analysis_context_pack_doc_defines_p5_data_quality_contract() -> None:
    section = _section(_read_doc(), "P5 Data quality score vs. Prompt Data limits")

    for token in (
        "`PACK_VERSION`",
        "`fetch_failed`",
        "`fundamental_context.status == \"failed\"`",
        "`overall_score`",
        "`level`",
        "`block_scores`",
        "`limitations`",
        "`quote=25`",
        "`fetch_failed=25`",
        "`Data Limitations`",
        "`confidence_level` Not allowed to do `high` / `High`",
        "`phase × degraded data`",
        "fail-open",
        "No replacement P5 of confidence/safety rules",
        "`analysis_context_pack_overview.data_quality`",
        "`details.context_snapshot`",
        "No new addition fetcher",
        "Do not change LLM output JSON schema",
        "`dashboard.phase_decision`",
    ):
        assert token in section


def test_analysis_context_pack_doc_defines_p6_migration_and_rollback_contract() -> None:
    section = _section(_read_doc(), "P6 Documentation、Migration and rollback")

    for token in (
        "Four data planes",
        "Internally complete pack",
        "`analysis_context_pack_summary`",
        "`analysis_context_pack_overview`",
        "`analysis_history.context_snapshot`",
        "Summary Visibility Matrix",
        "`SAVE_CONTEXT_SNAPSHOT=true`",
        "`SAVE_CONTEXT_SNAPSHOT=false`",
        "`--no-context-snapshot`",
        "Not persisting the entire copy `analysis_history.context_snapshot`",
        "This history has been made permanent `analysis_history.context_snapshot`",
        "`enhanced_context`",
        "`market_phase_summary`",
        "`diagnostics`",
        "`realtime_quote_raw`",
        "Does not affect the current time `AnalysisContextPack` build",
        "does not affect the memory `result.diagnostic_context_snapshot`",
        "Does not currently exist",
        "runtime pack main switch",
        "Release or code rollback",
        "secret",
        "token",
        "webhook",
    ):
        assert token in section


def test_analysis_context_pack_doc_maps_existing_status_terms() -> None:
    section = _section(_read_doc(), "Existing state mapping")

    for token in (
        "`degraded`",
        "`insufficient_data`",
        "`partial_failed`",
        "`data_missing`",
        "`price_stale`",
        "`data_quality=ok/partial/unavailable`",
        "Not mapped",
    ):
        assert token in section


def test_analysis_context_pack_doc_lists_source_anchors() -> None:
    section = _section(_read_doc(), "source code anchor")

    for path in (
        "src/core/pipeline.py",
        "src/storage.py",
        "src/analyzer.py",
        "src/agent/orchestrator.py",
        "src/agent/executor.py",
        "src/agent/tools/data_tools.py",
        "src/services/alert_worker.py",
        "src/services/portfolio_service.py",
        "src/services/backtest_service.py",
        "src/repositories/backtest_repo.py",
        "src/services/history_service.py",
        "api/v1/endpoints/history.py",
        "api/v1/endpoints/analysis.py",
        "api/v1/schemas/history.py",
        "api/v1/schemas/portfolio.py",
        "src/notification.py",
        "docs/alerts.md",
        "docs/notifications.md",
    ):
        assert path in section


def test_analysis_context_pack_doc_updates_indexes_and_changelog() -> None:
    index = (PROJECT_ROOT / "docs" / "INDEX.md").read_text(encoding="utf-8")
    index_en = (PROJECT_ROOT / "docs" / "INDEX_EN.md").read_text(encoding="utf-8")
    changelog = (PROJECT_ROOT / "docs" / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "[Analyze context package contract、Running consumption and visibility](analysis-context-pack.md)" in index
    assert "P1/P2 internal contract、P3 Prompt summary consumption、P4 history/API/Web Hypoallergenic visibility、P5 Data quality score、P6 Migration rollback" in index
    assert "#1386 stage awareness analysis、Migration and rollback portal" in index
    assert (
        "[Analysis Context Pack Contract, Runtime Consumption, And Visibility](analysis-context-pack.md) "
        "<sub><sub>![P6 Badge](https://img.shields.io/badge/P6-orange?style=flat)</sub></sub> "
        "(Chinese-only)"
    ) in index_en
    assert "P1/P2 internal contracts, P3 prompt-summary consumption, P4 history/API/Web low-sensitivity visibility, P5 data-quality scoring, and P6 migration/rollback notes" in index_en
    assert "#1386 market-phase analysis, migration, and rollback entry points" in index_en
    assert "New AnalysisContextPack P0 Contextual inventory" in changelog
    assert "New AnalysisContextPack P1 Internal contract and desensitized serialization testing" in changelog
    assert "New AnalysisContextPack P2 builder" in changelog
    assert "General analysis and Agent runtime Prompt Access AnalysisContextPack Hypoallergenic summary" in changelog
    assert "AnalysisContextPack P4 hypoallergenic overview Access history details" in changelog
    assert "AnalysisContextPack P5 Add data quality score" in changelog
    assert "clear AnalysisContextPack P6 Documentation、Migration and rollback boundaries" in changelog
    assert "#1386 P7 Before the market/intraday/Entrance to after-hours analysis、Migrate、Rollback and user-visible instructions" in changelog
    assert "#1386 P5 Added to individual stock analysis report `dashboard.phase_decision`" in changelog
    assert "Optimize Web Report details page information level" in changelog


def test_full_guides_cover_issue_1386_p7_user_migration_closeout() -> None:
    guide = (PROJECT_ROOT / "docs" / "full-guide.md").read_text(encoding="utf-8")
    guide_en = (PROJECT_ROOT / "docs" / "full-guide_EN.md").read_text(encoding="utf-8")

    for token in (
        "Documentation、Configuration and migration instructions（Issue #1386 P7）",
        "Before the market / intraday / After-hours analysis",
        "Generate opening plan and observation conditions",
        "intraday / noon / Nearing closing",
        "Make real-time status judgments、Risk and Opportunity Alerts",
        "`analysis_phase=auto|premarket|intraday|postmarket`",
        "The final reporting stage is still based on `report.meta.market_phase_summary.phase` Subject to",
        "Web main analysis / Reanalyze / Manual analysis of positions",
        "There is currently no stage coverage selector",
        "The ongoing task panel shows the request stage",
        "The final report page shows the final stage label",
        "Bot / CLI / schedule / Default GitHub Actions",
        "Only consume public `market_phase_summary` and hyposensitivity `analysis_context_pack_overview`",
        "Undisclosed complete pack、Prompt summary、News text or position sensitive details",
        "Old calls are not passed `analysis_phase` remain compatible",
        "Backtest query support `analysis_phase=premarket|intraday|postmarket|unknown`",
        "`SAVE_CONTEXT_SNAPSHOT=false`",
        "Do not close current session `AnalysisContextPack` build",
        "hypoallergenic `analysis_context_pack_summary`",
        "`analysis_phase=postmarket`",
        "Release rollback or code rollback required",
    ):
        assert token in guide

    for token in (
        "Documentation, Configuration, And Migration Notes (Issue #1386 P7)",
        "pre-market / intraday / post-market analysis",
        "opening plan and watch conditions",
        "Intraday / lunch break / near close",
        "live state, risk, and opportunity alerts",
        "`analysis_phase=auto|premarket|intraday|postmarket`",
        "final report phase remains `report.meta.market_phase_summary.phase`",
        "Web main analysis / re-analysis / portfolio manual analysis",
        "no phase override selector",
        "the in-progress task panel shows the requested phase",
        "the final report page shows the final phase label",
        "Bot / CLI / schedule / default GitHub Actions",
        "Only consume public `market_phase_summary` and low-sensitivity `analysis_context_pack_overview`",
        "do not expose the full pack, prompt summary, news body text, or sensitive portfolio details",
        "Older callers that omit `analysis_phase` remain compatible",
        "Backtest queries support `analysis_phase=premarket|intraday|postmarket|unknown`",
        "`SAVE_CONTEXT_SNAPSHOT=false`",
        "does not disable current-run `AnalysisContextPack` construction",
        "low-sensitivity `analysis_context_pack_summary`",
        "`analysis_phase=postmarket`",
        "requires a release rollback or code rollback",
    ):
        assert token in guide_en


def test_full_guides_clarify_pack_summary_does_not_replace_legacy_payload_channels() -> None:
    guide = (PROJECT_ROOT / "docs" / "full-guide.md").read_text(encoding="utf-8")
    guide_en = (PROJECT_ROOT / "docs" / "full-guide_EN.md").read_text(encoding="utf-8")

    assert "Added in this pack in summary block" in guide
    assert "will not be seen in full through this block `news.content`" in guide
    assert "existing `news_context`、Agent pre-fetched JSON and `enhanced_context` Original data channel remains P3 previous behavior" in guide
    assert "`report.details.analysis_context_pack_overview`" in guide
    assert "completed `/api/v1/analysis/status/{task_id}`" in guide
    assert "Web The end report page is at“strategic point”and“information”Then display the default collapsed data block summary" in guide
    assert "Collapse the header to display the available number、Missing number、Non-zero other state counts and trigger sources" in guide
    assert "Web The report page is collapsed by default after the strategic points and information to display the data block status." in guide
    assert "`details.context_snapshot` will peel off the top layer `analysis_context_pack_overview`" in guide
    assert "The synchronous analysis response will also read the data that has been dropped into the library this time. `analysis_history.context_snapshot` Extract overview" in guide
    assert "`SAVE_CONTEXT_SNAPSHOT=false` This field is not guaranteed to be returned for new records" in guide
    assert "AnalysisContextPack Data quality score vs. Prompt Data limits（Issue #1389 P5）" in guide
    assert "Intraday decision-making guardrails and quality checks（Issue #1386 P5）" in guide
    assert "`dashboard.phase_decision`" in guide
    assert "`fetch_failed`" in guide
    assert "Added quality score for folded head/level" in guide
    assert "`report.meta.market_phase_summary`" in guide
    assert "`details.context_snapshot` will peel off the top layer `market_phase_summary`" in guide
    assert "AnalysisContextPack Documentation、Migration and rollback（Issue #1389 P6）" in guide
    assert "`SAVE_CONTEXT_SNAPSHOT` is an existing environment variable" in guide
    assert "Not persisting the entire copy `analysis_history.context_snapshot`" in guide
    assert "Do not close current session `AnalysisContextPack` build" in guide
    assert "There is currently no runtime pack main switch" in guide

    assert "in this new pack-summary section" in guide_en
    assert "not full `news.content`" in guide_en
    assert "Existing `news_context`, Agent pre-fetched JSON, and `enhanced_context` raw-payload channels keep their pre-P3 behavior" in guide_en
    assert "`report.details.analysis_context_pack_overview`" in guide_en
    assert "completed `/api/v1/analysis/status/{task_id}`" in guide_en
    assert "The Web report page renders a collapsed data-block summary after Strategy and News" in guide_en
    assert "available/missing counts, non-zero other status counts, and trigger source" in guide_en
    assert "the Web report page shows the data-block summary collapsed after Strategy and News" in guide_en
    assert "API `details.context_snapshot` strips the top-level `analysis_context_pack_overview`" in guide_en
    assert "sync analysis responses also extract the overview from the just-persisted `analysis_history.context_snapshot`" in guide_en
    assert "new records do not guarantee this field when `SAVE_CONTEXT_SNAPSHOT=false`" in guide_en
    assert "AnalysisContextPack Data Quality Scoring and Prompt Limitations (Issue #1389 P5)" in guide_en
    assert "Intraday Decision Guardrails and Quality Checks (Issue #1386 P5)" in guide_en
    assert "`dashboard.phase_decision`" in guide_en
    assert "`fetch_failed`" in guide_en
    assert "adds quality score/level to the header" in guide_en
    assert "`report.meta.market_phase_summary`" in guide_en
    assert "API `details.context_snapshot` strips the top-level `market_phase_summary`" in guide_en
    assert "AnalysisContextPack Documentation, Migration, and Rollback (Issue #1389 P6)" in guide_en
    assert "`SAVE_CONTEXT_SNAPSHOT` is an existing environment variable" in guide_en
    assert "the full `analysis_history.context_snapshot` is not persisted" in guide_en
    assert "does not disable current-run `AnalysisContextPack` construction" in guide_en
    assert "There is no runtime pack master switch" in guide_en
