# -*- coding: utf-8 -*-
"""Tests for low-sensitive DecisionSignal summary helpers."""

from __future__ import annotations

from src.services.decision_signal_summary import (
    format_decision_signal_excerpt,
    summarize_decision_signal,
)


def test_summarize_decision_signal_keeps_only_low_sensitive_fields() -> None:
    summary = summarize_decision_signal({
        "id": 42,
        "stock_code": "600519",
        "stock_name": "Kweichow Moutai",
        "market": "cn",
        "action": "sell",
        "action_label": "sell",
        "horizon": "3d",
        "status": "active",
        "source_type": "alert",
        "source_agent": "alert_worker",
        "source_report_id": 88,
        "reason": "token=secret-value Stop loss triggered",
        "watch_conditions": ["Observe quantity energy", "password=hidden"],
        "risk_summary": {"drawdown": "webhook=https://hooks.slack.com/services/T/B/C"},
        "created_at": "2026-06-18T10:00:00+08:00",
        "expires_at": "2026-06-25T10:00:00+08:00",
        "metadata": {"webhook_url": "https://hooks.slack.com/services/T/B/C"},
        "evidence": {"secret": "raw"},
        "diagnostics": "authorization=Bearer raw",
    })

    assert summary is not None
    assert set(summary) == {
        "id",
        "stock_code",
        "stock_name",
        "market",
        "action",
        "action_label",
        "horizon",
        "status",
        "source_type",
        "source_report_id",
        "reason",
        "watch_conditions",
        "risk_summary",
        "created_at",
        "expires_at",
    }
    assert summary["reason"] == "token=[REDACTED] Stop loss triggered"
    assert summary["watch_conditions"] == ["Observe quantity energy", "password=[REDACTED]"]
    assert summary["risk_summary"] == {"drawdown": "webhook=[REDACTED_URL]"}


def test_summarize_decision_signal_rejects_non_dict_and_empty_payload() -> None:
    assert summarize_decision_signal(None) is None
    assert summarize_decision_signal(["not", "a", "dict"]) is None
    assert summarize_decision_signal({"metadata": {"token": "secret"}, "evidence": {"raw": True}}) is None
    assert summarize_decision_signal({"stock_code": "", "reason": None}) is None


def test_format_decision_signal_excerpt_formats_chinese_list_and_dict_fields() -> None:
    excerpt = format_decision_signal_excerpt({
        "action_label": "sell",
        "horizon": "3d",
        "source_report_id": 88,
        "reason": "Falling below the stop loss line",
        "watch_conditions": ["observe 1660 support", "Waiting for volume to shrink"],
        "risk_summary": {"drawdown": "Combination retracement expansion"},
    })

    assert excerpt.startswith("**AI decision signal**")
    assert "action: sell | cycle: 3d | report: #88" in excerpt
    assert "- Reason: Falling below the stop loss line" in excerpt
    assert "- Observation conditions: observe 1660 support；Waiting for volume to shrink" in excerpt
    assert "- risk: drawdown: Combination retracement expansion" in excerpt


def test_format_decision_signal_excerpt_formats_english_and_redacts_text() -> None:
    excerpt = format_decision_signal_excerpt({
        "action": "alert",
        "horizon": "5d",
        "reason": "authorization: Bearer raw-token",
        "watch_conditions": "Check price",
        "risk_summary": "token=hidden",
    }, report_language="en")

    assert excerpt.startswith("**AI decision signal**")
    assert "Action: alert | Horizon: 5d" in excerpt
    assert "- Reason: authorization: [REDACTED]" in excerpt
    assert "- Watch: Check price" in excerpt
    assert "- Risk: token=[REDACTED]" in excerpt


def test_format_decision_signal_excerpt_returns_empty_for_invalid_input() -> None:
    assert format_decision_signal_excerpt(None) == ""
    assert format_decision_signal_excerpt({}) == ""
    assert format_decision_signal_excerpt(["not", "a", "dict"]) == ""
