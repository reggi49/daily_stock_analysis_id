# -*- coding: utf-8 -*-
"""Tests for structure-aware decision stability calibration."""

from types import SimpleNamespace

from src.analyzer import AnalysisResult, _capital_flow_bias, stabilize_decision_with_structure


def _result(
    *,
    decision_type: str,
    operation_advice: str,
    score: int,
    current_price: float,
    change_pct: float = 0.0,
) -> AnalysisResult:
    return AnalysisResult(
        code="002812",
        name="Enjie shares",
        sentiment_score=score,
        trend_prediction="long" if decision_type == "buy" else "bearish",
        operation_advice=operation_advice,
        decision_type=decision_type,
        report_language="zh",
        current_price=current_price,
        change_pct=change_pct,
        dashboard={
            "core_conclusion": {"one_sentence": "original conclusion"},
            "data_perspective": {
                "price_position": {
                    "current_price": current_price,
                    "support_level": 30.0,
                    "resistance_level": 34.0,
                }
            },
        },
    )


def _fund_flow(main: float, five_day: float = 0.0, ten_day: float = 0.0) -> dict:
    return {
        "capital_flow": {
            "status": "ok",
            "data": {
                "stock_flow": {
                    "main_net_inflow": main,
                    "inflow_5d": five_day,
                    "inflow_10d": ten_day,
                }
            },
        }
    }


def _unsupported_fund_flow() -> dict:
    return {"capital_flow": {"status": "not_supported", "data": {}}}


def _unsupported_fund_flow_caps() -> dict:
    return {"capital_flow": {"status": "NOT_SUPPORTED", "data": {"stock_flow": {"main_net_inflow": 0}}}}


def test_capital_flow_bias_is_unavailable_when_stock_flow_data_is_missing() -> None:
    assert _capital_flow_bias(_unsupported_fund_flow()) == "unavailable"
    assert _capital_flow_bias({"capital_flow": {"status": "ok", "data": {}}}) == "unavailable"


def test_capital_flow_bias_is_neutral_when_missing_main_windows_conflict() -> None:
    context = {
        "capital_flow": {
            "data": {
                "stock_flow": {
                    "inflow_5d": 2_000_000,
                    "inflow_10d": -1_000_000,
                }
            }
        }
    }

    assert _capital_flow_bias(context) == "neutral"


def test_capital_flow_bias_is_neutral_when_main_conflicts_with_windows() -> None:
    context = _fund_flow(main=-500_000, five_day=1_200_000, ten_day=2_000_000)

    assert _capital_flow_bias(context) == "neutral"


def test_downgrades_buy_near_resistance_without_fund_confirmation() -> None:
    result = _result(
        decision_type="buy",
        operation_advice="Buy",
        score=65,
        current_price=33.4,
    )

    stabilize_decision_with_structure(
        result,
        SimpleNamespace(support_levels=[30.0], resistance_levels=[34.0]),
        _fund_flow(main=-1_000_000, five_day=-2_000_000),
    )

    assert result.decision_type == "hold"
    assert result.sentiment_score <= 59
    assert result.operation_advice == "Wait and see in shock"
    assert result.dashboard["decision_stability"]["applied"] is True
    assert "It is not advisable to pursue purchases just because of a short-term rebound." in result.risk_warning
    assert result.dashboard["core_conclusion"]["signal_type"] == "🟡wait and see"


def test_downgrades_buy_mid_range_with_neutral_fund_flow() -> None:
    result = _result(
        decision_type="buy",
        operation_advice="Buy",
        score=66,
        current_price=32.0,
    )

    stabilize_decision_with_structure(
        result,
        SimpleNamespace(support_levels=[30.0], resistance_levels=[34.0]),
        _fund_flow(main=0, five_day=0, ten_day=0),
    )

    assert result.decision_type == "hold"
    assert result.sentiment_score <= 59
    assert result.operation_advice == "Wait and see in shock"
    assert "Fund flow is unclear" in result.risk_warning


def test_downgrades_buy_when_capital_flow_is_unavailable() -> None:
    buy_result = _result(
        decision_type="buy",
        operation_advice="Buy",
        score=66,
        current_price=32.0,
    )
    sell_result = _result(
        decision_type="sell",
        operation_advice="sell",
        score=30,
        current_price=30.4,
        change_pct=-2.1,
    )

    stabilize_decision_with_structure(
        buy_result,
        SimpleNamespace(support_levels=[30.0], resistance_levels=[34.0]),
        _unsupported_fund_flow(),
    )
    stabilize_decision_with_structure(
        sell_result,
        SimpleNamespace(support_levels=[30.0], resistance_levels=[34.0]),
        _unsupported_fund_flow(),
    )

    assert buy_result.decision_type == "hold"
    assert buy_result.operation_advice == "hold observation"
    assert buy_result.confidence_level == "low"
    assert buy_result.sentiment_score <= 59
    assert buy_result.dashboard["decision_stability"]["applied"] is True
    assert "Buying conclusion lacks financial confirmation" in buy_result.dashboard["decision_stability"]["reason"]
    assert buy_result.dashboard["core_conclusion"]["signal_type"] == "🟡wait and see"
    assert sell_result.decision_type == "sell"
    assert sell_result.operation_advice == "sell"
    assert sell_result.dashboard["decision_stability"]["applied"] is False
    assert "Fund flow calibration not used" in sell_result.dashboard["decision_stability"]["reason"]


def test_downgrades_buy_when_capital_flow_values_are_na() -> None:
    result = _result(
        decision_type="buy",
        operation_advice="Buy",
        score=66,
        current_price=33.0,
    )

    stabilize_decision_with_structure(
        result,
        SimpleNamespace(support_levels=[30.0], resistance_levels=[34.0]),
        {
            "capital_flow": {
                "status": "ok",
                "data": {
                    "stock_flow": {
                        "main_net_inflow": "N/A",
                        "inflow_5d": "N/A",
                        "inflow_10d": "N/A",
                    }
                },
            }
        },
    )

    assert result.decision_type == "hold"
    assert result.operation_advice == "hold observation"
    assert result.dashboard["decision_stability"]["applied"] is True
    assert "Fund flow data is missing" in result.dashboard["decision_stability"]["capital_flow_status"]


def test_downgrades_buy_advice_when_decision_type_is_hold_and_capital_flow_unavailable() -> None:
    result = _result(
        decision_type="hold",
        operation_advice="Recommended to buy",
        score=68,
        current_price=32.0,
    )

    stabilize_decision_with_structure(
        result,
        SimpleNamespace(support_levels=[30.0], resistance_levels=[34.0]),
        _unsupported_fund_flow(),
    )

    assert result.decision_type == "hold"
    assert result.operation_advice == "hold observation"
    assert result.sentiment_score <= 59
    assert result.dashboard["decision_stability"]["applied"] is True
    assert "Buying conclusion lacks financial confirmation" in result.dashboard["decision_stability"]["reason"]


def test_downgrades_buy_when_capital_flow_status_is_unavailable_case_insensitive() -> None:
    buy_result = _result(
        decision_type="buy",
        operation_advice="Buy",
        score=66,
        current_price=32.0,
    )

    stabilize_decision_with_structure(
        buy_result,
        SimpleNamespace(support_levels=[30.0], resistance_levels=[34.0]),
        _unsupported_fund_flow_caps(),
    )

    assert buy_result.decision_type == "hold"
    assert buy_result.operation_advice == "hold observation"
    assert buy_result.dashboard["decision_stability"]["applied"] is True
    assert "Not supported yet" in str(buy_result.dashboard["decision_stability"]["capital_flow_status"])


def test_skips_downgrade_when_only_generic_risk_warning_and_sell_near_support() -> None:
    result = _result(
        decision_type="sell",
        operation_advice="sell",
        score=30,
        current_price=30.4,
        change_pct=1.0,
    )
    result.risk_warning = "Be aware of common retracement risks，It is recommended to pay attention to positions。"

    stabilize_decision_with_structure(
        result,
        SimpleNamespace(support_levels=[30.0], resistance_levels=[34.0]),
        _fund_flow(main=500_000, five_day=300_000),
    )

    assert result.decision_type == "hold"
    assert result.operation_advice == "Washing dishes and observing"
    assert "Prices are close to support and no continued outflows are seen" in result.risk_warning


def test_stability_can_infer_decision_from_natural_chinese_phrases_in_analyzer_path() -> None:
    result = _result(
        decision_type="Recommended to sell",
        operation_advice="Recommended to sell",
        score=30,
        current_price=30.4,
        change_pct=1.0,
    )

    stabilize_decision_with_structure(
        result,
        SimpleNamespace(support_levels=[30.0], resistance_levels=[34.0]),
        _fund_flow(main=500_000, five_day=300_000),
    )

    assert result.decision_type == "hold"
    assert result.operation_advice == "Washing dishes and observing"
    assert result.dashboard["decision_stability"]["applied"] is True


def test_downgrades_sell_near_support_without_sustained_outflow() -> None:
    result = _result(
        decision_type="sell",
        operation_advice="sell",
        score=30,
        current_price=30.4,
        change_pct=-2.1,
    )

    stabilize_decision_with_structure(
        result,
        SimpleNamespace(support_levels=[30.0], resistance_levels=[34.0]),
        _fund_flow(main=800_000, five_day=1_200_000),
    )

    assert result.decision_type == "hold"
    assert result.sentiment_score >= 45
    assert result.operation_advice == "Washing dishes and observing"
    assert "It is not advisable to sell directly just because of a single day's decline." in result.risk_warning


def test_preserves_sell_signal_when_significant_risk_exists_near_support() -> None:
    result = _result(
        decision_type="sell",
        operation_advice="sell",
        score=30,
        current_price=30.4,
        change_pct=-2.1,
    )
    result.risk_warning = "Major bad news：The company releases a major shareholding reduction plan"
    result.dashboard["intelligence"] = {"risk_alerts": ["Shareholders’ high-level shareholding reduction notice"]}

    stabilize_decision_with_structure(
        result,
        SimpleNamespace(support_levels=[30.0], resistance_levels=[34.0]),
        _fund_flow(main=800_000, five_day=1_200_000),
    )

    assert result.decision_type == "sell"
    assert result.operation_advice == "sell"


def test_refines_hold_pullback_near_support_as_shakeout_watch() -> None:
    result = _result(
        decision_type="hold",
        operation_advice="hold",
        score=52,
        current_price=30.5,
        change_pct=-1.6,
    )

    stabilize_decision_with_structure(
        result,
        SimpleNamespace(support_levels=[30.0], resistance_levels=[34.0]),
        _fund_flow(main=0, five_day=500_000),
    )

    assert result.decision_type == "hold"
    assert result.operation_advice == "Washing dishes and observing"
    assert "More suitable for washing dishes and observing" in result.risk_warning
