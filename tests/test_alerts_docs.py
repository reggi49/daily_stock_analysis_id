# -*- coding: utf-8 -*-
"""Contract checks for the alert-center documentation."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "alerts.md"


def _read_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_alerts_doc_exists_and_links_p0_scope() -> None:
    doc = _read_doc()

    assert "Issue #1202" in doc
    assert "AGENT_EVENT_ALERT_RULES_JSON" in doc
    assert "EventMonitor" in doc
    assert "P1: Alert API MVP" in doc
    assert "P0 Does NOT" in doc


def test_alerts_doc_covers_legacy_runtime_rules() -> None:
    doc = _read_doc()

    for token in ("price_cross", "price_change_percent", "volume_spike"):
        assert token in doc
    for token in ("sentiment_shift", "risk_flag", "custom"):
        assert token in doc


def test_alerts_doc_defines_required_contract_entities() -> None:
    doc = _read_doc()

    required_sections = (
        "### `alert_rule`",
        "### `alert_trigger`",
        "### `alert_notification`",
        "### `alert_cooldown`",
    )
    for section in required_sections:
        assert section in doc

    required_fields = (
        "target_scope",
        "parameters",
        "cooldown_policy",
        "notification_policy",
        "observed_value",
        "data_timestamp",
        "trigger_id",
        "latency_ms",
        "cooldown_until",
    )
    for field_name in required_fields:
        assert field_name in doc


def test_alerts_doc_covers_storage_evaluation_and_rollback() -> None:
    doc = _read_doc()

    assert (PROJECT_ROOT / "src" / "storage.py").is_file()

    for token in (
        "## Storage Evaluation",
        "src/storage.py",
        "src/repositories/",
        "src/services/",
        "data/stock_analysis.db",
        "Idempotent initialization",
        "Rollback instructions",
    ):
        assert token in doc


def test_alerts_doc_keeps_p0_non_goals_explicit() -> None:
    doc = _read_doc()

    for token in (
        "P0 does not add `api/v1/schemas/alerts.py` or Alert API",
        "P0 does not add Web Alert Center pages",
        "P0 does not add database tables, repositories, or migrations",
        "P0 does not implement trigger history",
        "P0 does not automatically migrate, delete, or overwrite `AGENT_EVENT_ALERT_RULES_JSON`",
        "P0 does not rewrite `NotificationService` or the notification routing framework",
    ):
        assert token in doc


def test_alerts_doc_defines_p1_api_mvp_scope() -> None:
    doc = _read_doc()

    for token in (
        "api/v1/endpoints/alerts.py",
        "api/v1/schemas/alerts.py",
        "GET /api/v1/alerts/rules",
        "POST /api/v1/alerts/rules",
        "GET /api/v1/alerts/rules/{rule_id}",
        "PATCH /api/v1/alerts/rules/{rule_id}",
        "DELETE /api/v1/alerts/rules/{rule_id}",
        "POST /api/v1/alerts/rules/{rule_id}/enable",
        "POST /api/v1/alerts/rules/{rule_id}/disable",
        "POST /api/v1/alerts/rules/{rule_id}/test",
        "GET /api/v1/alerts/triggers",
        "GET /api/v1/alerts/notifications",
        "price_cross",
        "price_change_percent",
        "volume_spike",
        "unsupported",
        "sanitized",
        "reserved fields",
        "does not execute cooldown or custom notification semantics",
    ):
        assert token in doc


def test_alerts_doc_keeps_p1_non_goals_explicit() -> None:
    doc = _read_doc()

    for token in (
        "Add new Web Alert Center pages",
        "Have the schedule worker load persisted active rules",
        "Implement real `alert_trigger` / `alert_notification` writes",
        "Implement `alert_cooldown` execution semantics",
        "Implement MACD, KDJ, CCI, RSI",
        "does not automatically migrate, delete, overwrite, or rewrite legacy configurations",
    ):
        assert token in doc


def test_alerts_doc_defines_p2_worker_scope() -> None:
    doc = _read_doc()

    for token in (
        "## P2 Alert Evaluation Worker",
        "src/services/alert_worker.py",
        "agent_event_monitor",
        "persisted active rules",
        "legacy JSON",
        "`triggered`, `skipped`, `degraded`, `failed`",
        "Write `alert_notifications`",
        "cooldown_policy",
    ):
        assert token in doc


def test_alerts_doc_describes_p1_rollback_for_created_tables() -> None:
    doc = _read_doc()

    for token in (
        "P1 adds Alert API code",
        "SQLite tables",
        "Base.metadata.create_all()",
        "will not be automatically deleted",
        "manually deleting the relevant tables",
    ):
        assert token in doc


def test_alerts_doc_defines_p4_notification_and_cooldown_scope() -> None:
    doc = _read_doc()

    for token in (
        "## P4 Notification Results and Persisted Cooldown",
        "`alert_cooldowns`",
        "`alert_notifications`",
        "rule_id + target + data_source + data_timestamp",
        "deduplicated",
        "when `data_timestamp` is missing, deduplication is skipped",
        "`__cooldown__`",
        "`__cooldown_read_failed__`",
        "`__noise_suppressed__`",
        "notification_noise.py",
        "use `alert_cooldowns` as the alert business cooldown in the normal path",
        "only when reading persisted cooldown state fails",
        "Legacy `AGENT_EVENT_ALERT_RULES_JSON` rules continue to use the worker process fingerprint",
        "does not write to or extend `alert_cooldowns`",
        "reverting the P4 PR",
    ):
        assert token in doc


def test_alerts_doc_defines_p5_indicator_scope() -> None:
    doc = _read_doc()

    for token in (
        "## P5 Technical Indicator Rules",
        "ma_price_cross",
        "rsi_threshold",
        "macd_cross",
        "kdj_cross",
        "cci_threshold",
        "compute_required_bars",
        "requested_days",
        "required_bars > 365",
        "the two most recently closed daily lines",
        "prev <= threshold < current",
        "Wilder",
        "SMMA",
        "alpha=1/period",
        "EMA(fast_period)",
        "alpha=1/k_period",
        "0.015 * mean_deviation",
        "server-local timezone heuristics",
        "16:00",
        "is conservatively discarded",
        "legacy JSON path",
        "Does not extend `src/agent/events.py`",
        "HTTP 400 + `validation_error`",
        "HTTP 400 + `unsupported_alert_type`",
        "Support MACD histogram expansion/contraction",
        "Support KDJ overbought/oversold zone rules",
        "Support MA-to-MA dual moving average crossovers",
        "Support intraday lines",
        "reverting the P5 PR",
        "unsupported `alert_type`",
    ):
        assert token in doc


def test_alerts_doc_defines_p6_portfolio_and_watchlist_scope() -> None:
    doc = _read_doc()

    for token in (
        "## P6 Portfolio and Watchlist Integration",
        "P6 Scope/Type Matrix",
        "`watchlist`",
        "`portfolio_holdings`",
        "`portfolio_account`",
        "`portfolio_stop_loss`",
        "`portfolio_concentration`",
        "`portfolio_drawdown`",
        "`portfolio_price_stale`",
        "Target Identity Contract",
        "`effective_target`",
        "`RuntimeAlertRule.key`",
        "`{parent_key}|{effective_target}`",
        "dry-run",
        "`degraded_count`",
        "soft cap",
        "cooldown_active",
        "parent rule summary",
        "Legacy `AGENT_EVENT_ALERT_RULES_JSON` does not support watchlist, portfolio",
        "sector-level concentration",
        "reverting the P6 PR",
    ):
        assert token in doc


def test_alerts_doc_defines_p7_market_light_scope() -> None:
    doc = _read_doc()

    for token in (
        "## P7 Market Traffic Light Structured Alerts",
        "MarketLightSnapshot",
        "`target_scope=market`",
        "`market_light_status`",
        "`market_light_score_drop`",
        "`statuses=[\"red\",\"yellow\"]`",
        "`min_drop > 0`",
        "`cn` / `hk` / `us`",
        "bidirectional constraint",
        "`context_snapshot.market_light_snapshots`",
        "`data_quality=unavailable`",
        "`partial_comparison=true`",
        "`missing_dimensions`",
        "canonical scorer",
        "thin wrapper",
        "`load_previous_snapshot(region, before_trade_date)`",
        "largest `snapshot.trade_date`",
        "old trading day backfill",
        "`TRADING_DAY_CHECK_ENABLED`",
        "`data_source=market_light`",
        "Legacy `AGENT_EVENT_ALERT_RULES_JSON` does not support market rules",
        "reverting the P7 PR",
    ):
        assert token in doc


def test_alerts_doc_covers_issue_1386_p7_user_visibility_boundary() -> None:
    doc = _read_doc()
    p7_section = doc.split("The user boundary for #1386 P7:", 1)[1].split(
        "Rolling back this integration",
        1,
    )[0]

    for token in (
        "phase and data quality summary that was already public at trigger time",
        "it does not automatically initiate lightweight LLM intraday analysis",
        "nor does it add new alert tables, rule types, environment variables, or migrations",
        "analysis API / Web manual analysis entry",
        "alert notifications only retain the phase label, trigger source, partial-bar warning, data quality level, and the first two limitations",
    ):
        assert token in p7_section


def test_alerts_doc_defines_p8_user_and_deployment_boundaries() -> None:
    doc = _read_doc()

    for token in (
        "## P8 User Configuration and Deployment Boundaries",
        "`AGENT_EVENT_MONITOR_ENABLED`",
        "`AGENT_EVENT_MONITOR_INTERVAL_MINUTES`",
        "`NOTIFICATION_ALERT_CHANNELS`",
        "`route_type=alert`",
        "Alert API / Web Alert Center persisted rules",
        "legacy `AGENT_EVENT_ALERT_RULES_JSON`",
        "Only compatible with three basic `single_symbol`",
        "P5 technical indicators, P6 watchlist/portfolio, or P7 market light",
        "docker/Dockerfile",
        "`python main.py --schedule`",
        "preserve the `data/` database volume",
        ".github/workflows/00-daily-analysis.yml",
        "one-shot analysis workflow",
        "without running the `--schedule` background alert worker",
        "does not map `AGENT_EVENT_*`",
        "`/alerts`",
        "Desktop does not add a native alert management interface",
        "`triggered`, `skipped`, `degraded`, `failed`",
        "rule_id + target + data_source + data_timestamp",
        "Rolling back P8 only requires reverting documentation, configuration instructions, and Web text changes",
    ):
        assert token in doc


def test_changelog_mentions_alert_p6_release_note() -> None:
    changelog = (PROJECT_ROOT / "docs" / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "P6" in changelog
    assert "Optional stocks" in changelog
    assert "Position" in changelog
    assert "Account linkage rules" in changelog


def test_changelog_mentions_alert_p8_docs_closeout() -> None:
    changelog = (PROJECT_ROOT / "docs" / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "Complete the alarm center P8 Documentation and configuration closing instructions" in changelog
    assert "GitHub Actions with Desktop border" in changelog


def test_changelog_unreleased_keeps_flat_entries() -> None:
    changelog = (PROJECT_ROOT / "docs" / "CHANGELOG.md").read_text(encoding="utf-8")
    unreleased = changelog.split("## [Unreleased]", 1)[1].split("\n## [", 1)[0]

    assert "\n### " not in unreleased
