# -*- coding: utf-8 -*-
"""Tests for Issue #1390 P0 decision action taxonomy helpers."""

import pytest

from src.schemas.decision_action import (
    build_action_fields,
    localize_action_label,
    normalize_decision_action,
)
from src.schemas.decision_scale import action_for_score, decision_type_for_score, signal_key_for_score


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("strong_buy", "buy"),
        ("Strong buy", "buy"),
        ("Buy", "buy"),
        ("Layout", "buy"),
        ("Open a position", "buy"),
        ("add", "add"),
        ("Add to position", "add"),
        ("Overweight", "add"),
        ("accumulate", "add"),
        ("hold", "hold"),
        ("hold", "hold"),
        ("hold observation", "hold"),
        ("Washing dishes and observing", "hold"),
        ("watch", "watch"),
        ("wait and see", "watch"),
        ("wait", "watch"),
        ("wait", "watch"),
        ("reduce", "reduce"),
        ("Reduce positions", "reduce"),
        ("trim", "reduce"),
        ("sell", "sell"),
        ("sell", "sell"),
        ("Clearance", "sell"),
        ("strong_sell", "sell"),
        ("Strong Sell", "sell"),
        ("avoid", "avoid"),
        ("Avoid", "avoid"),
        ("avoid", "avoid"),
        ("Not recommended to buy", "avoid"),
        ("avoid buying", "avoid"),
        ("do not buy", "avoid"),
        ("alert", "alert"),
        ("Risk warning", "alert"),
        ("Be alert", "alert"),
        ("trigger alarm", "alert"),
        ("risk alert", "alert"),
    ],
)
def test_normalize_decision_action_matrix(value: str, expected: str) -> None:
    assert normalize_decision_action(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        None,
        "observe",
        "Wait for a breakout to buy",
        "waiting to buy",
        "buy or sell",
        "buy or sell",
        "Buying orders strengthen，Continue to observe",
        "Selling pressure eases，Continue to observe",
        "Seller rating divergence",
        "no buyback announced",
        "cannot buyback shares now",
        "share buy-back announced",
        "share buy back announced",
        "no selloff risk",
        "not selloff yet",
        "sell-off risk remains low",
        "sell off risk remains low",
        "no sell-off pressure",
        "risk alert, avoid buying",
        "Risk warning，avoid buying",
        "General review instructions",
    ],
)
def test_normalize_decision_action_unknown_or_ambiguous_returns_none(value: str | None) -> None:
    assert normalize_decision_action(value) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Not buying yet", "avoid"),
        ("Don't buy", "avoid"),
        ("Not suitable to buy", "avoid"),
        ("Don’t buy yet", "avoid"),
        ("No need to buy", "avoid"),
        ("No need to buy", "avoid"),
        ("Not recommended to open a position", "avoid"),
        ("Not opening a position yet", "avoid"),
        ("No need to open a position", "avoid"),
        ("No need to open a position", "avoid"),
        ("Layout not recommended", "avoid"),
        ("No layout first", "avoid"),
        ("No layout required", "avoid"),
        ("No layout required", "avoid"),
        ("no buy", "avoid"),
        ("no need to buy", "avoid"),
        ("need not buy", "avoid"),
        ("cannot buy", "avoid"),
        ("can't buy", "avoid"),
        ("not a buy yet", "avoid"),
        ("not to buy", "avoid"),
        ("avoid buying", "avoid"),
        ("avoid buying into weakness", "avoid"),
        ("Not recommended to add positions", "hold"),
        ("No need to add position", "hold"),
        ("no add", "hold"),
        ("no need to add", "hold"),
        ("need not add", "hold"),
        ("cannot add", "hold"),
        ("not to add", "hold"),
        ("no accumulate", "hold"),
        ("can't accumulate", "hold"),
        ("not to accumulate", "hold"),
        ("Not recommended to sell", "hold"),
        ("No need to sell", "hold"),
        ("No need to sell", "hold"),
        ("don't sell", "hold"),
        ("Not for sale yet", "hold"),
        ("no sell", "hold"),
        ("no need to sell", "hold"),
        ("cannot sell", "hold"),
        ("can't sell", "hold"),
        ("not a sell yet", "hold"),
        ("not to sell", "hold"),
        ("No need to reduce positions", "hold"),
        ("No need to reduce positions", "hold"),
        ("no reduce", "hold"),
        ("no need to reduce", "hold"),
        ("cannot reduce", "hold"),
        ("not to reduce", "hold"),
        ("no trim", "hold"),
        ("can't trim", "hold"),
        ("not a trim yet", "hold"),
        ("not to trim", "hold"),
        ("avoid selling into weakness", "hold"),
        ("avoid trimming before earnings", "hold"),
        ("avoid reducing exposure before earnings", "hold"),
        ("Not recommended for clearance", "hold"),
    ],
)
def test_normalize_decision_action_handles_negated_trade_actions(value: str, expected: str) -> None:
    assert normalize_decision_action(value) == expected


@pytest.mark.parametrize(
    "advice",
    [
        "No need to buy，Waiting for confirmation",
        "No need to open a position，Continue to observe",
        "No layout required，Waiting for a breakthrough",
        "no buy until breakout",
        "no need to buy before confirmation",
        "cannot buy before confirmation",
        "can't buy before confirmation",
        "not a buy yet",
        "not to buy",
    ],
)
def test_build_action_fields_prioritizes_negated_buy_advice_over_embedded_buy_phrase(advice: str) -> None:
    assert build_action_fields(operation_advice=advice) == {
        "action": "avoid",
        "action_label": "Avoid",
    }


@pytest.mark.parametrize(
    "advice",
    [
        "No need to add position，Maintain position",
        "No need to sell，continue to hold",
        "No need to reduce positions，Waiting for confirmation",
        "no add before confirmation",
        "cannot add before confirmation",
        "no need to accumulate here",
        "can't accumulate here",
        "no sell before earnings",
        "cannot sell before earnings",
        "no need to reduce exposure",
        "can't reduce exposure",
        "no trim while trend holds",
        "cannot trim while trend holds",
        "not a sell yet",
        "not a trim yet",
        "not to sell",
        "not to trim",
        "avoid selling into weakness",
        "avoid trimming before earnings",
        "avoid reducing exposure before earnings",
    ],
)
def test_build_action_fields_prioritizes_negated_hold_advice_over_embedded_trade_phrase(advice: str) -> None:
    assert build_action_fields(operation_advice=advice) == {
        "action": "hold",
        "action_label": "hold",
    }


@pytest.mark.parametrize(
    "advice",
    [
        "risk alert, avoid buying",
        "Risk warning，avoid buying",
    ],
)
def test_build_action_fields_keeps_multi_guard_advice_empty(advice: str) -> None:
    assert build_action_fields(operation_advice=advice) == {
        "action": None,
        "action_label": None,
    }


@pytest.mark.parametrize(
    "advice",
    [
        "Buying orders strengthen，Continue to observe",
        "Selling pressure eases，Continue to observe",
        "Seller rating divergence",
    ],
)
def test_build_action_fields_keeps_chinese_financial_context_empty(advice: str) -> None:
    assert build_action_fields(operation_advice=advice) == {
        "action": None,
        "action_label": None,
    }


@pytest.mark.parametrize(
    "advice",
    [
        "no buyback announced",
        "cannot buyback shares now",
        "no selloff risk",
        "not selloff yet",
    ],
)
def test_build_action_fields_keeps_financial_compound_terms_empty(advice: str) -> None:
    assert build_action_fields(operation_advice=advice) == {
        "action": None,
        "action_label": None,
    }


@pytest.mark.parametrize(
    "advice",
    [
        "share buy-back announced",
        "share buy back announced",
        "sell-off risk remains low",
        "sell off risk remains low",
        "no sell-off pressure",
    ],
)
def test_build_action_fields_keeps_hyphenated_financial_compound_terms_empty(advice: str) -> None:
    assert build_action_fields(operation_advice=advice) == {
        "action": None,
        "action_label": None,
    }


@pytest.mark.parametrize(
    ("advice", "expected_action", "expected_label"),
    [
        ("buy after sell-off", "buy", "Buy"),
        ("sell after buy-back rumor", "sell", "sell"),
    ],
)
def test_financial_compound_mask_preserves_separate_action_terms(
    advice: str,
    expected_action: str,
    expected_label: str,
) -> None:
    assert normalize_decision_action(advice) == expected_action
    assert build_action_fields(operation_advice=advice) == {
        "action": expected_action,
        "action_label": expected_label,
    }


def test_localize_action_label_uses_report_language() -> None:
    assert localize_action_label("avoid", "zh") == "Avoid"
    assert localize_action_label("avoid", "en") == "Avoid"


def test_build_action_fields_respects_market_review_exclusion() -> None:
    fields = build_action_fields(
        operation_advice="Buy",
        explicit_action="buy",
        report_type="market_review",
    )

    assert fields == {"action": None, "action_label": None}


def test_build_action_fields_prefers_explicit_action_over_advice() -> None:
    fields = build_action_fields(
        operation_advice="Buy",
        explicit_action="watch",
        report_language="zh",
    )

    assert fields == {"action": "watch", "action_label": "wait and see"}


def test_build_action_fields_keeps_empty_action_without_advice_or_explicit_action() -> None:
    fields = build_action_fields(
        operation_advice=None,
        report_language="zh",
    )

    assert fields == {"action": None, "action_label": None}


@pytest.mark.parametrize(
    ("score", "expected_signal", "expected_action", "expected_decision_type"),
    [
        (28, "reduce", "reduce", "sell"),
        (38, "reduce", "reduce", "sell"),
        (42, "watch", "watch", "hold"),
        (55, "watch", "watch", "hold"),
        (60, "buy", "buy", "buy"),
        (66, "buy", "buy", "buy"),
        (72, "buy", "buy", "buy"),
    ],
)
def test_canonical_score_scale_boundaries(
    score: int,
    expected_signal: str,
    expected_action: str,
    expected_decision_type: str,
) -> None:
    assert signal_key_for_score(score) == expected_signal
    assert action_for_score(score) == expected_action
    assert decision_type_for_score(score) == expected_decision_type


def test_build_action_fields_can_align_neutral_action_with_directional_score() -> None:
    assert build_action_fields(
        operation_advice="hold",
        sentiment_score=72,
        align_with_score=True,
    ) == {"action": "buy", "action_label": "Buy"}

    assert build_action_fields(
        operation_advice="wait and see",
        sentiment_score=28,
        align_with_score=True,
    ) == {"action": "reduce", "action_label": "Reduce positions"}


def test_build_action_fields_keeps_neutral_score_conflict_when_guardrail_is_explicit() -> None:
    assert build_action_fields(
        operation_advice="hold/Wait and see and wait to step back",
        sentiment_score=72,
        guardrail_reason="Waiting for confirmation",
        align_with_score=True,
    ) == {"action": "watch", "action_label": "wait and see"}
