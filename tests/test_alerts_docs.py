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
    assert "P1 Alert API MVP" in doc
    assert "P0 Don't do it" in doc


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
        "## Storage solution evaluation",
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
        "P0 No new stage is added `api/v1/schemas/alerts.py`",
        "P0 No new stage is added Web Alarm center page",
        "P0 No new database tables are added during this stage",
        "P0 Stage does not implement trigger history",
        "P0 Stages are not automatically migrated、delete or overwrite `AGENT_EVENT_ALERT_RULES_JSON`",
        "P0 Stages are not rewritten `NotificationService`",
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
        "Desensitization",
        "reserved fields",
        "No cooling or custom notification semantics are performed",
    ):
        assert token in doc


def test_alerts_doc_keeps_p1_non_goals_explicit() -> None:
    doc = _read_doc()

    for token in (
        "No new addition Web Alarm center page",
        "Don't let schedule worker Load persistence active rules",
        "not realizing reality `alert_trigger` / `alert_notification` write",
        "Not realized `alert_cooldown` execution semantics",
        "Not realized MACD、KDJ、CCI、RSI",
        "No automatic migration、Delete、overwrite or overwrite legacy Configuration",
    ):
        assert token in doc


def test_alerts_doc_defines_p2_worker_scope() -> None:
    doc = _read_doc()

    for token in (
        "## P2 Alarm evaluation Worker",
        "src/services/alert_worker.py",
        "agent_event_monitor",
        "persistence active rules",
        "legacy JSON",
        "`triggered`、`skipped`、`degraded`、`failed`",
        "Don't write `alert_notifications`",
        "Not executed `cooldown_policy`",
    ):
        assert token in doc


def test_alerts_doc_describes_p1_rollback_for_created_tables() -> None:
    doc = _read_doc()

    for token in (
        "P1 New Alert API code",
        "`alert_rules` / `alert_triggers` / `alert_notifications` SQLite table",
        "Base.metadata.create_all()",
        "SQLite Tables and data will not be automatically deleted",
        "Manually delete related tables",
    ):
        assert token in doc


def test_alerts_doc_defines_p4_notification_and_cooldown_scope() -> None:
    doc = _read_doc()

    for token in (
        "## P4 Notification results and persistent cooling",
        "`alert_cooldowns`",
        "`alert_notifications`",
        "`rule_id + target + data_source + data_timestamp`",
        "Deduplication of the same data point",
        "`data_timestamp` No deduplication is performed when missing",
        "`__cooldown__`",
        "`__cooldown_read_failed__`",
        "`__noise_suppressed__`",
        "notification_noise.py",
        "DB Persistence rules normal path usage `alert_cooldowns`",
        "Failed to read persistent cooling status",
        "legacy `AGENT_EVENT_ALERT_RULES_JSON` Rules continue to be used worker In-process fingerprint",
        "will not be written or extended `alert_cooldowns`",
        "The minimal rollback method is revert P4 PR",
    ):
        assert token in doc


def test_alerts_doc_defines_p5_indicator_scope() -> None:
    doc = _read_doc()

    for token in (
        "## P5 Technical indicator rules",
        "ma_price_cross",
        "rsi_threshold",
        "macd_cross",
        "kdj_cross",
        "cci_threshold",
        "compute_required_bars",
        "requested_days",
        "required_bars > 365",
        "The last two closing daily bars",
        "prev <= threshold < current",
        "Wilder",
        "SMMA",
        "alpha=1/period",
        "EMA(fast_period)",
        "alpha=1/k_period",
        "0.015 * mean_deviation",
        "Server local time zone heuristic",
        "16:00",
        "If the date cannot be determined, it will be discarded conservatively.",
        "legacy JSON path",
        "Not extended `src/agent/events.py`",
        "HTTP 400 + `validation_error`",
        "HTTP 400 + `unsupported_alert_type`",
        "Not supported MACD Cylinder magnification/shrink",
        "Not supported KDJ overbought/oversold zone rules",
        "Not supported MA with MA Double moving average crossover",
        "Does not support minute lines",
        "revert P5 PR",
        "skip unsupported `alert_type`",
    ):
        assert token in doc


def test_alerts_doc_defines_p6_portfolio_and_watchlist_scope() -> None:
    doc = _read_doc()

    for token in (
        "## P6 Linkage between positions and self-selected stocks",
        "P6 scope/type matrix",
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
        "Parent rule summary",
        "legacy `AGENT_EVENT_ALERT_RULES_JSON` Not supported watchlist、portfolio",
        "sector level concentration",
        "P6 PR",
    ):
        assert token in doc


def test_alerts_doc_defines_p7_market_light_scope() -> None:
    doc = _read_doc()

    for token in (
        "## P7 Large market traffic light structured alarm",
        "MarketLightSnapshot",
        "`target_scope=market`",
        "`market_light_status`",
        "`market_light_score_drop`",
        "`statuses=[\"red\",\"yellow\"]`",
        "`min_drop > 0`",
        "`cn` / `hk` / `us`",
        "Two-way constraints",
        "`context_snapshot.market_light_snapshots`",
        "`data_quality=unavailable`",
        "`partial_comparison=true`",
        "`missing_dimensions`",
        "canonical scorer",
        "thin wrapper",
        "`load_previous_snapshot(region, before_trade_date)`",
        "maximum `snapshot.trade_date`",
        "old trading day backfill",
        "`TRADING_DAY_CHECK_ENABLED`",
        "`data_source=market_light`",
        "legacy `AGENT_EVENT_ALERT_RULES_JSON` Not supported market rules",
        "revert P7 PR",
    ):
        assert token in doc


def test_alerts_doc_covers_issue_1386_p7_user_visibility_boundary() -> None:
    doc = _read_doc()
    p7_section = doc.split("#1386 P7 user boundaries：", 1)[1].split(
        "\n\nRoll back this linkage",
        1,
    )[0]

    for token in (
        "Summary of stages and data quality already publicly available when triggered",
        "Will not automatically launch lightweight LLM intraday analysis",
        "No new alarm table will be added、Rule type、environment variables or migration",
        "analysis API / Web Manual analysis entry",
        "Alarm notifications only retain stage labels、trigger source、partial-bar warning、Data quality level and the first two limitations",
    ):
        assert token in p7_section


def test_alerts_doc_defines_p8_user_and_deployment_boundaries() -> None:
    doc = _read_doc()

    for token in (
        "## P8 User configuration and deployment boundaries",
        "`AGENT_EVENT_MONITOR_ENABLED`",
        "`AGENT_EVENT_MONITOR_INTERVAL_MINUTES`",
        "`NOTIFICATION_ALERT_CHANNELS`",
        "`route_type=alert`",
        "Alert API / Web Alarm center persistence rules",
        "legacy `AGENT_EVENT_ALERT_RULES_JSON`",
        "Only compatible with `single_symbol`",
        "P5 Technical indicators、P6 watchlist/portfolio or P7 market light",
        "docker/Dockerfile",
        "`python main.py --schedule`",
        "Reserve `data/` database volume",
        ".github/workflows/00-daily-analysis.yml",
        "One-time analysis workflow",
        "Not running `--schedule` Backstage alert worker",
        "no mapping `AGENT_EVENT_*`",
        "`/alerts`",
        "Desktop No new native alarm management interface will be added",
        "`triggered`、`skipped`、`degraded`、`failed`",
        "`rule_id + target + data_source + data_timestamp`",
        "rollback P8 Just revert Documentation、configuration instructions and Web Copywriting changes",
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
