# -*- coding: utf-8 -*-
"""Tests for Issue #1381 daily market context decision guardrail."""

from __future__ import annotations

from src.analyzer import AnalysisResult
from src.daily_market_context_guardrail import apply_daily_market_context_guardrail


def _result() -> AnalysisResult:
    return AnalysisResult(
        code="600519",
        name="Kweichow Moutai",
        sentiment_score=82,
        trend_prediction="long",
        operation_advice="Buy now and actively add positions",
        decision_type="buy",
        confidence_level="high",
        analysis_summary="Strong signal from individual stocks",
        dashboard={
            "operation_advice": "Buy now and actively add positions",
            "decision_type": "buy",
            "core_conclusion": {
                "one_sentence": "Buy now and actively add positions",
                "position_advice": {
                    "no_position": "Buy now and actively add positions",
                    "has_position": "Continue to add positions",
                },
            },
            "battle_plan": {
                "position_strategy": {
                    "suggested_position": "Buy with full position",
                    "entry_plan": "Buy immediately after a breakout",
                    "risk_control": "Step back and continue to add positions",
                },
            },
            "phase_decision": {
                "data_limitations": [],
                "confidence_reason": "The trend is strong",
            },
        },
    )


def test_conservative_market_context_softens_aggressive_buy() -> None:
    result = _result()

    adjustments = apply_daily_market_context_guardrail(
        result,
        daily_market_context={
            "region": "cn",
            "trade_date": "2026-06-06",
            "summary": "The market ebbs，high risk，It is recommended to wait and see，Position limit30%。",
            "risk_tags": ["high_risk", "low_position_cap"],
        },
        report_language="zh",
    )

    assert "daily_market_context_buy_softened" in adjustments
    assert result.decision_type == "hold"
    assert result.operation_advice == "wait and see"
    assert len(result.operation_advice) <= 20
    assert result.confidence_level == "in"
    assert result.sentiment_score == 52
    assert result.dashboard["operation_advice"] == result.operation_advice
    assert result.dashboard["decision_type"] == "hold"
    assert result.dashboard["sentiment_score"] == 52
    core = result.dashboard["core_conclusion"]
    assert core["one_sentence"] == result.operation_advice
    assert core["position_advice"] == {
        "no_position": "The market environment is cautious，No new positions will be opened at the moment，Waiting for risk mitigation or confirmation signals。",
        "has_position": "Only Ogura observation is retained，No expansion of positions yet；If it falls below the risk control level, reduce the position first。",
    }
    position_strategy = result.dashboard["battle_plan"]["position_strategy"]
    assert position_strategy == {
        "suggested_position": "Ogura/low position",
        "entry_plan": "The market environment is cautious，No new positions will be opened at the moment，Waiting for risk mitigation or confirmation signals。",
        "risk_control": "Do not expand positions until market risks are alleviated，Strictly control drawdowns。",
    }
    phase_decision = result.dashboard["phase_decision"]
    assert any("Market environment" in item for item in phase_decision["data_limitations"])
    assert "Market environment" in phase_decision["confidence_reason"]


def test_position_cap_only_market_context_softens_aggressive_buy() -> None:
    cases = [
        ("zh", "market shock，The position does not exceed30%。", "Buy now and actively add positions", "high", "wait and see"),
        ("en", "Major indices are mixed. Position limit 30%.", "Buy now and add aggressively.", "High", "Watch"),
    ]
    for language, summary, advice, confidence, expected_advice in cases:
        result = _result()
        result.operation_advice = advice
        result.confidence_level = confidence

        adjustments = apply_daily_market_context_guardrail(
            result,
            daily_market_context={
                "region": "us" if language == "en" else "cn",
                "trade_date": "2026-06-06",
                "summary": summary,
                "risk_tags": [],
                "position_cap": "30%",
            },
            report_language=language,
        )

        assert "daily_market_context_buy_softened" in adjustments
        assert result.decision_type == "hold"
        assert result.operation_advice == expected_advice


def test_neutral_market_context_leaves_hold_unchanged() -> None:
    result = _result()
    result.decision_type = "hold"
    result.operation_advice = "hold observation"
    result.confidence_level = "in"

    adjustments = apply_daily_market_context_guardrail(
        result,
        daily_market_context={
            "region": "cn",
            "trade_date": "2026-06-06",
            "summary": "market shock，structural differentiation。",
            "risk_tags": [],
        },
        report_language="zh",
    )

    assert adjustments == []
    assert result.decision_type == "hold"
    assert result.operation_advice == "hold observation"


def test_conservative_market_context_does_not_soften_negative_buy_language() -> None:
    result = _result()
    result.decision_type = "buy"
    result.operation_advice = "No additional positions for now，Continue to hold and observe。"
    result.confidence_level = "high"

    adjustments = apply_daily_market_context_guardrail(
        result,
        daily_market_context={
            "region": "cn",
            "trade_date": "2026-06-06",
            "summary": "The market ebbs，high risk，It is recommended to wait and see，Position limit30%。",
            "risk_tags": ["high_risk", "low_position_cap"],
        },
        report_language="zh",
    )

    assert adjustments == []
    assert result.decision_type == "buy"
    assert result.operation_advice == "No additional positions for now，Continue to hold and observe。"


def test_conservative_market_context_does_not_soften_no_action_in_english() -> None:
    result = _result()
    result.decision_type = "hold"
    result.operation_advice = "No add now; keep watching for confirmation."

    adjustments = apply_daily_market_context_guardrail(
        result,
        daily_market_context={
            "region": "us",
            "trade_date": "2026-06-06",
            "summary": "Market cooling and elevated risk. Cautious on new positions."
        },
        report_language="en",
    )

    assert adjustments == []
    assert result.decision_type == "hold"
    assert result.operation_advice == "No add now; keep watching for confirmation."


def test_conservative_market_context_does_not_soften_explicit_negative_add_position() -> None:
    result = _result()
    result.decision_type = "buy"
    result.operation_advice = "Not recommended to add positions，Waiting for a clearer window。"
    result.confidence_level = "high"

    adjustments = apply_daily_market_context_guardrail(
        result,
        daily_market_context={
            "region": "cn",
            "trade_date": "2026-06-06",
            "summary": "The market ebbs，high risk，It is recommended to wait and see，Position limit30%。",
            "risk_tags": ["high_risk", "low_position_cap"],
        },
        report_language="zh",
    )

    assert adjustments == []
    assert result.decision_type == "buy"
    assert result.operation_advice == "Not recommended to add positions，Waiting for a clearer window。"


def test_conservative_market_context_softens_generic_buy_advice_phrase() -> None:
    result = _result()
    result.operation_advice = "Buy back，Strong support to attack。"
    result.confidence_level = "high"

    adjustments = apply_daily_market_context_guardrail(
        result,
        daily_market_context={
            "region": "cn",
            "trade_date": "2026-06-06",
            "summary": "The market ebbs，high risk，It is recommended to wait and see，Position limit30%。",
            "risk_tags": ["high_risk", "low_position_cap"],
        },
        report_language="zh",
    )

    assert "daily_market_context_buy_softened" in adjustments
    assert result.decision_type == "hold"
    assert result.operation_advice == "wait and see"


def test_conservative_market_context_softens_when_risk_warning_then_recommend_buy() -> None:
    result = _result()
    result.decision_type = "buy"
    result.operation_advice = "Risks cannot be ignored，But it is recommended to buy and wait for confirmation signals。"
    result.confidence_level = "high"

    adjustments = apply_daily_market_context_guardrail(
        result,
        daily_market_context={
            "region": "cn",
            "trade_date": "2026-06-06",
            "summary": "The market ebbs，high risk，It is recommended to wait and see，Position limit30%。",
            "risk_tags": ["high_risk", "low_position_cap"],
        },
        report_language="zh",
    )

    assert "daily_market_context_buy_softened" in adjustments
    assert result.decision_type == "hold"
    assert result.operation_advice == "wait and see"


def test_conservative_market_context_softens_when_negated_chase_then_recommend_buy() -> None:
    result = _result()
    result.decision_type = "buy"
    result.operation_advice = "It is not recommended to chase high，But it is recommended to buy in batches。"
    result.confidence_level = "high"

    adjustments = apply_daily_market_context_guardrail(
        result,
        daily_market_context={
            "region": "cn",
            "trade_date": "2026-06-06",
            "summary": "The market ebbs，high risk，It is recommended to wait and see，Position limit30%。",
            "risk_tags": ["high_risk", "low_position_cap"],
        },
        report_language="zh",
    )

    assert "daily_market_context_buy_softened" in adjustments
    assert result.decision_type == "hold"
    assert result.operation_advice == "wait and see"


def test_conservative_market_context_does_not_soften_buy_when_negated_explicitly_in_english() -> None:
    result = _result()
    result.decision_type = "buy"
    result.operation_advice = "No buy now; avoid adding."

    adjustments = apply_daily_market_context_guardrail(
        result,
        daily_market_context={
            "region": "cn",
            "trade_date": "2026-06-06",
            "summary": "The market ebbs，high risk，It is recommended to wait and see，Position limit30%。",
            "risk_tags": ["high_risk", "low_position_cap"],
        },
        report_language="en",
    )

    assert adjustments == []
    assert result.decision_type == "buy"
    assert result.operation_advice == "No buy now; avoid adding."


def test_conservative_market_context_does_not_soften_do_not_buy_in_english() -> None:
    result = _result()
    result.decision_type = "buy"
    result.operation_advice = "Do not buy now; sell into strength."

    adjustments = apply_daily_market_context_guardrail(
        result,
        daily_market_context={
            "region": "us",
            "trade_date": "2026-06-06",
            "summary": "Market cooling and elevated risk. Cautious on new positions.",
        },
        report_language="en",
    )

    assert adjustments == []
    assert result.decision_type == "buy"
    assert result.operation_advice == "Do not buy now; sell into strength."
