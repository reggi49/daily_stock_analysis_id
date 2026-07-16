# -*- coding: utf-8 -*-
"""Tests for Issue #1386 P5 phase decision guardrails."""

from types import SimpleNamespace

from src.analyzer import AnalysisResult
from src.phase_decision_guardrail import apply_phase_decision_guardrails


def _result(**kwargs) -> AnalysisResult:
    defaults = {
        "code": "600519",
        "name": "Kweichow Moutai",
        "trend_prediction": "long",
        "sentiment_score": 76,
        "operation_advice": "Buy now",
        "decision_type": "buy",
        "confidence_level": "high",
        "analysis_summary": "Strong intraday",
        "dashboard": {
            "core_conclusion": {"one_sentence": "Buy now"},
            "phase_decision": {
                "action_window": "intraday tracking",
                "immediate_action": "Buy now",
                "watch_conditions": ["Heavy volume breakthrough"],
                "next_check_time": "14:30",
                "confidence_reason": "The trend is strong",
                "data_limitations": [],
            },
        },
    }
    defaults.update(kwargs)
    return AnalysisResult(**defaults)


def _phase(phase: str = "intraday") -> dict:
    return {
        "phase": phase,
        "market": "cn",
        "market_local_time": "2026-06-02T10:30:00+08:00",
        "is_trading_day": True,
        "is_market_open_now": phase == "intraday",
        "is_partial_bar": phase in {"intraday", "lunch_break", "closing_auction"},
        "warnings": ["calendar_unavailable"],
    }


def _overview(status: str = "stale") -> dict:
    return {
        "subject": {"code": "600519", "stock_name": "Kweichow Moutai", "market": "cn"},
        "blocks": [
            {
                "key": "quote",
                "label": "Quotes",
                "status": status,
                "source": "tencent",
                "warnings": [],
                "missing_reasons": [],
            },
            {
                "key": "daily_bars",
                "label": "daily line",
                "status": "available",
                "source": "akshare",
                "warnings": [],
                "missing_reasons": [],
            },
            {
                "key": "technical",
                "label": "Technology",
                "status": "available",
                "source": "local",
                "warnings": [],
                "missing_reasons": [],
            },
        ],
        "data_quality": {
            "overall_score": 65,
            "level": "limited",
            "limitations": ["quote: stale"],
        },
    }


def test_degraded_core_data_caps_high_confidence_buy() -> None:
    result = _result()

    adjustments = apply_phase_decision_guardrails(
        result,
        market_phase_summary=_phase("intraday"),
        analysis_context_pack_overview=_overview("stale"),
        report_language="zh",
    )

    assert "confidence_capped_core_data_degraded" in adjustments
    assert result.confidence_level == "in"
    pd = result.dashboard["phase_decision"]
    assert pd["phase_context"]["phase"] == "intraday"
    assert "quote: stale" in pd["data_limitations"]
    assert "Core Quotes" in pd["confidence_reason"]


def test_degraded_core_data_caps_high_confidence_hold_advice() -> None:
    result = _result(
        operation_advice="No additional positions for now，wait and see",
        decision_type="hold",
        confidence_level="high",
        dashboard={
            "core_conclusion": {"one_sentence": "No additional positions for now，wait and see"},
            "phase_decision": {
                "action_window": "intraday tracking",
                "immediate_action": "No additional positions for now，wait and see",
                "watch_conditions": ["Heavy volume breakthrough"],
                "next_check_time": "14:30",
                "confidence_reason": "Trend not confirmed",
                "data_limitations": [],
            },
        },
    )

    adjustments = apply_phase_decision_guardrails(
        result,
        market_phase_summary=_phase("intraday"),
        analysis_context_pack_overview=_overview("stale"),
        report_language="zh",
    )

    assert "confidence_capped_core_data_degraded" in adjustments
    assert result.confidence_level == "in"
    assert "Core Quotes" in result.dashboard["phase_decision"]["confidence_reason"]
    assert "quote: stale" in result.dashboard["phase_decision"]["data_limitations"]


def test_premarket_high_confidence_immediate_action_is_conservative() -> None:
    result = _result()

    adjustments = apply_phase_decision_guardrails(
        result,
        market_phase_summary=_phase("premarket"),
        analysis_context_pack_overview=_overview("available"),
        report_language="zh",
    )

    assert "confidence_capped_non_intraday_action" in adjustments
    assert result.confidence_level == "low"
    assert result.dashboard["phase_decision"]["immediate_action"] == "Waiting for intraday confirmation，Chasing high is prohibited。"


def test_premarket_medium_confidence_immediate_action_rewrites_action_only() -> None:
    result = _result(
        operation_advice="Hold unless confirmed",
        decision_type="hold",
        confidence_level="Medium",
        report_language="en",
        dashboard={
            "core_conclusion": {"one_sentence": "Wait"},
            "phase_decision": {
                "action_window": "Premarket plan",
                "immediate_action": "buy now",
                "watch_conditions": ["breakout with volume"],
                "next_check_time": "market open",
                "confidence_reason": "Setup is forming",
                "data_limitations": [],
            },
        },
    )

    adjustments = apply_phase_decision_guardrails(
        result,
        market_phase_summary=_phase("premarket"),
        analysis_context_pack_overview=_overview("available"),
        report_language="en",
    )

    assert "non_intraday_action_adjusted" in adjustments
    assert "confidence_capped_non_intraday_action" not in adjustments
    assert result.confidence_level == "Medium"
    assert result.dashboard["phase_decision"]["immediate_action"] == (
        "Wait for intraday confirmation; do not chase."
    )
    assert "buy now" not in result.dashboard["phase_decision"]["immediate_action"].lower()


def test_unknown_low_confidence_immediate_action_rewrites_action_only() -> None:
    result = _result(
        operation_advice="Mainly observation",
        decision_type="hold",
        confidence_level="low",
        dashboard={
            "core_conclusion": {"one_sentence": "Mainly observation"},
            "phase_decision": {
                "action_window": "Unknown stage observation",
                "immediate_action": "Buy now",
                "watch_conditions": ["Confirm market opening status"],
                "next_check_time": "After confirming the stage",
                "confidence_reason": "Stage unknown",
                "data_limitations": [],
            },
        },
    )

    adjustments = apply_phase_decision_guardrails(
        result,
        market_phase_summary=_phase("unknown"),
        analysis_context_pack_overview=_overview("available"),
        report_language="zh",
    )

    assert "non_intraday_action_adjusted" in adjustments
    assert "confidence_capped_non_intraday_action" not in adjustments
    assert result.confidence_level == "low"
    assert result.dashboard["phase_decision"]["immediate_action"] == "Waiting for intraday confirmation，Chasing high is prohibited。"


def test_premarket_degraded_immediate_action_uses_strongest_cap() -> None:
    result = _result()

    adjustments = apply_phase_decision_guardrails(
        result,
        market_phase_summary=_phase("premarket"),
        analysis_context_pack_overview=_overview("stale"),
        report_language="zh",
    )

    assert "confidence_capped_core_data_degraded" in adjustments
    assert "confidence_capped_non_intraday_action" in adjustments
    assert result.confidence_level == "low"
    assert result.dashboard["phase_decision"]["immediate_action"] == "Waiting for intraday confirmation，Chasing high is prohibited。"


def test_intraday_postmarket_recap_wording_is_adjusted_in_zh_and_en() -> None:
    zh_result = _result(
        operation_advice="After today's close, the review shows that it can be bought",
        analysis_summary="Tomorrow will focus on breakthroughs",
        dashboard={
            "core_conclusion": {"one_sentence": "The review after today’s close showed a strong bias"},
            "phase_decision": {"immediate_action": "Tomorrow will focus on breakthroughs", "watch_conditions": []},
        },
    )

    zh_adjustments = apply_phase_decision_guardrails(
        zh_result,
        market_phase_summary=_phase("intraday"),
        analysis_context_pack_overview=_overview("available"),
        report_language="zh",
    )

    assert "postmarket_recap_wording_adjusted" in zh_adjustments
    assert "After today's close" not in zh_result.dashboard["core_conclusion"]["one_sentence"]
    assert "Tomorrow's focus" not in zh_result.analysis_summary

    en_result = _result(
        operation_advice="Buy after today's close",
        analysis_summary="Focus tomorrow on the breakout",
        confidence_level="High",
        report_language="en",
        dashboard={
            "core_conclusion": {"one_sentence": "After today's close, buy"},
            "phase_decision": {"immediate_action": "focus tomorrow", "watch_conditions": []},
        },
    )

    en_adjustments = apply_phase_decision_guardrails(
        en_result,
        market_phase_summary=_phase("intraday"),
        analysis_context_pack_overview=_overview("available"),
        report_language="en",
    )

    assert "postmarket_recap_wording_adjusted" in en_adjustments
    assert "after today's close" not in en_result.dashboard["core_conclusion"]["one_sentence"].lower()
    assert "focus tomorrow" not in en_result.analysis_summary.lower()


def test_postmarket_recap_and_missing_inputs_are_fail_open() -> None:
    postmarket = _result(
        operation_advice="The review after today’s close shows that it can be held",
        dashboard={
            "core_conclusion": {"one_sentence": "The review after today’s close shows that it can be held"},
            "phase_decision": {"watch_conditions": ["Do not break the support"]},
        },
    )

    adjustments = apply_phase_decision_guardrails(
        postmarket,
        market_phase_summary=_phase("postmarket"),
        analysis_context_pack_overview=None,
        report_language="zh",
    )

    assert adjustments == []
    assert "After today's close" in postmarket.dashboard["core_conclusion"]["one_sentence"]
    assert postmarket.dashboard["phase_decision"]["watch_conditions"] == ["Do not break the support"]

    missing = _result(dashboard={})
    adjustments = apply_phase_decision_guardrails(
        missing,
        market_phase_summary=None,
        analysis_context_pack_overview=None,
        report_language="zh",
    )

    assert adjustments == []
    assert missing.dashboard["phase_decision"]["watch_conditions"] == []
    assert missing.dashboard["phase_decision"]["data_limitations"] == []


def test_guardrail_creates_dashboard_for_agent_compatible_result_object() -> None:
    result = SimpleNamespace(
        confidence_level="high",
        decision_type="hold",
        operation_advice="hold",
        analysis_summary="Test summary",
    )

    adjustments = apply_phase_decision_guardrails(
        result,
        market_phase_summary=_phase("intraday"),
        analysis_context_pack_overview=_overview("available"),
        report_language="zh",
    )

    assert adjustments == []
    assert result.dashboard["phase_decision"]["phase_context"]["phase"] == "intraday"
    assert result.dashboard["phase_decision"]["watch_conditions"] == []
