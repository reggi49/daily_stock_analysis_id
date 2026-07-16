# -*- coding: utf-8 -*-
"""
===================================
Report Engine - Report renderer tests
===================================

Tests for Jinja2 report rendering and fallback behavior.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch

try:
    import litellm  # noqa: F401
except ModuleNotFoundError:
    sys.modules["litellm"] = MagicMock()

from src.analyzer import AnalysisResult
from src.services.report_renderer import render


def _make_result(
    code: str = "600519",
    name: str = "Kweichow Moutai",
    sentiment_score: int = 72,
    operation_advice: str = "hold",
    analysis_summary: str = "Robust",
    decision_type: str = "hold",
    dashboard: dict = None,
    report_language: str = "zh",
    model_used: str = None,
) -> AnalysisResult:
    if dashboard is None:
        dashboard = {
            "core_conclusion": {"one_sentence": "wait and see"},
            "intelligence": {"risk_alerts": []},
            "battle_plan": {"sniper_points": {"stop_loss": "110"}},
        }
    return AnalysisResult(
        code=code,
        name=name,
        trend_prediction="long",
        sentiment_score=sentiment_score,
        operation_advice=operation_advice,
        analysis_summary=analysis_summary,
        decision_type=decision_type,
        dashboard=dashboard,
        report_language=report_language,
        model_used=model_used,
    )


def _make_renderer_config(show_llm_model: bool = True) -> MagicMock:
    config = MagicMock()
    config.report_templates_dir = "templates"
    config.report_language = "zh"
    config.report_show_llm_model = show_llm_model
    return config


def _with_decision_signal_summary(result: AnalysisResult) -> AnalysisResult:
    result.decision_signal_summary = {
        "action": "sell",
        "action_label": "sell",
        "horizon": "1d",
        "reason": "Technical weakness",
    }
    return result


class TestReportRenderer(unittest.TestCase):
    """Report renderer tests."""

    def test_render_markdown_summary_only(self) -> None:
        """Markdown platform renders with summary_only."""
        r = _make_result()
        out = render("markdown", [r], summary_only=True)
        self.assertIsNotNone(out)
        self.assertIn("Decision dashboard", out)
        self.assertIn("Kweichow Moutai", out)
        self.assertIn("hold", out)

    def test_render_markdown_full(self) -> None:
        """Markdown platform renders full report."""
        r = _make_result()
        out = render("markdown", [r], summary_only=False)
        self.assertIsNotNone(out)
        self.assertIn("Core conclusion", out)
        self.assertIn("battle plan", out)
        self.assertNotIn("Intraday Decision Guardrails", out)

    def test_render_markdown_keeps_decision_signal_out_of_summary(self) -> None:
        """Markdown summary stays compact while full details keep DecisionSignal excerpts."""
        r = _with_decision_signal_summary(_make_result())

        summary_out = render("markdown", [r], summary_only=True)
        self.assertIsNotNone(summary_out)
        self.assertNotIn("AI decision signal", summary_out)

        full_out = render("markdown", [r], summary_only=False)
        self.assertIsNotNone(full_out)
        summary_section, detail_section = full_out.split("---", 1)
        self.assertNotIn("AI decision signal", summary_section)
        self.assertIn("AI decision signal", detail_section)
        self.assertIn("action: sell", detail_section)
        self.assertIn("cycle: 1d", detail_section)
        self.assertIn("Reason: Technical weakness", detail_section)

    def test_render_markdown_phase_decision_section(self) -> None:
        """Markdown renders phase_decision when present."""
        r = _make_result(
            dashboard={
                "core_conclusion": {"one_sentence": "Waiting for confirmation"},
                "intelligence": {"risk_alerts": []},
                "phase_decision": {
                    "action_window": "intraday tracking",
                    "immediate_action": "Waiting for confirmation",
                    "watch_conditions": ["Heavy volume breakthrough"],
                    "next_check_time": "14:30",
                    "confidence_reason": "Data quality available",
                    "data_limitations": ["quote: stale"],
                },
                "battle_plan": {"sniper_points": {"stop_loss": "110"}},
            }
        )

        out = render("markdown", [r], summary_only=False)

        self.assertIsNotNone(out)
        self.assertIn("Intraday Decision Guardrails", out)
        self.assertIn("intraday tracking", out)
        self.assertIn("Heavy volume breakthrough", out)
        self.assertIn("quote: stale", out)

    def test_render_markdown_skips_context_only_phase_decision_shape(self) -> None:
        """Markdown skips mechanically shaped phase_decision without actionable content."""
        r = _make_result(
            dashboard={
                "core_conclusion": {"one_sentence": "wait and see"},
                "intelligence": {"risk_alerts": []},
                "phase_decision": {
                    "phase_context": {"phase": "intraday", "market": "cn"},
                    "action_window": None,
                    "immediate_action": None,
                    "watch_conditions": [],
                    "next_check_time": None,
                    "confidence_reason": None,
                    "data_limitations": [],
                },
                "battle_plan": {"sniper_points": {"stop_loss": "110"}},
            }
        )

        out = render("markdown", [r], summary_only=False)

        self.assertIsNotNone(out)
        self.assertNotIn("Intraday Decision Guardrails", out)

    def test_render_wechat(self) -> None:
        """Wechat platform renders."""
        r = _make_result()
        out = render("wechat", [r])
        self.assertIsNotNone(out)
        self.assertIn("Kweichow Moutai", out)

    def test_render_wechat_keeps_decision_signal_out_of_summary(self) -> None:
        """Wechat summary-only stays compact while full details keep DecisionSignal excerpts."""
        r = _with_decision_signal_summary(_make_result())

        summary_out = render("wechat", [r], summary_only=True)
        self.assertIsNotNone(summary_out)
        self.assertNotIn("AI decision signal", summary_out)

        full_out = render("wechat", [r], summary_only=False)
        self.assertIsNotNone(full_out)
        self.assertIn("AI decision signal", full_out)
        self.assertIn("action: sell", full_out)
        self.assertIn("cycle: 1d", full_out)
        self.assertIn("Reason: Technical weakness", full_out)

    def test_render_brief(self) -> None:
        """Brief platform renders 3-5 sentence summary."""
        r = _make_result()
        out = render("brief", [r])
        self.assertIsNotNone(out)
        self.assertIn("Decision briefing", out)
        self.assertIn("Kweichow Moutai", out)

    def test_render_brief_omits_decision_signal_excerpt(self) -> None:
        r = _with_decision_signal_summary(_make_result())

        out = render("brief", [r])

        self.assertIsNotNone(out)
        self.assertNotIn("AI decision signal", out)

    def test_render_brief_respects_model_visibility_toggle(self) -> None:
        r = _make_result(model_used="gemini/gemini-2.5-flash")

        with patch("src.services.report_renderer.get_config", return_value=_make_renderer_config(True)):
            visible = render("brief", [r])
        with patch("src.services.report_renderer.get_config", return_value=_make_renderer_config(False)):
            hidden = render("brief", [r])

        self.assertIsNotNone(visible)
        self.assertIsNotNone(hidden)
        self.assertIn("Analytical model: gemini/gemini-2.5-flash", visible)
        self.assertNotIn("Analytical model", hidden)
        self.assertNotIn("gemini/gemini-2.5-flash", hidden)

    def test_render_templates_show_compact_market_status_only(self) -> None:
        r = _make_result()
        r.market_phase_summary = {
            "phase": "intraday",
            "market": "cn",
            "trigger_source": "api",
            "is_partial_bar": True,
        }
        r.analysis_context_pack_overview = {
            "data_quality": {
                "level": "limited",
                "limitations": ["quote: stale", "news: missing", "technical: fallback"],
            }
        }
        r.raw_response = "raw context pack should not appear"

        out = render("brief", [r])

        self.assertIsNotNone(out)
        self.assertIn("market status：Ashares · intraday", out)
        self.assertNotIn("stage：intraday", out)
        self.assertNotIn("Intraday data tips", out)
        self.assertNotIn("Data quality: limited", out)
        self.assertNotIn("Limit: quote: stale", out)
        self.assertNotIn("Limit: news: missing", out)
        self.assertNotIn("technical: fallback", out)
        self.assertNotIn("raw context pack", out)

    def test_render_templates_skip_phase_pack_excerpt_when_summary_missing(self) -> None:
        r = _make_result()

        out = render("brief", [r])

        self.assertIsNotNone(out)
        self.assertNotIn("Summary source", out)
        self.assertNotIn("evaluator snapshot", out)

    def test_render_market_status_preserves_input_order(self) -> None:
        cn = _make_result(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=60,
        )
        cn.market_phase_summary = {"market": "cn", "phase": "postmarket"}
        us = _make_result(
            code="AAPL",
            name="Apple",
            sentiment_score=90,
        )
        us.market_phase_summary = {"market": "us", "phase": "premarket"}

        out = render("markdown", [cn, us], summary_only=True)

        self.assertIsNotNone(out)
        self.assertIn("market status：Ashares · after hours", out)
        self.assertNotIn("market status：US stocks · Before the market", out)

    def test_render_markdown_footer_uses_consistent_separator(self) -> None:
        r = _make_result(model_used="gemini/gemini-2.5-flash")

        with patch("src.services.report_renderer.get_config", return_value=_make_renderer_config(True)):
            out = render("markdown", [r], summary_only=True)

        self.assertIsNotNone(out)
        self.assertIn("Report generation time：", out)
        self.assertIn("Analytical model：gemini/gemini-2.5-flash", out)
        self.assertNotIn("Analytical model: gemini/gemini-2.5-flash", out)

    def test_render_markdown_in_english(self) -> None:
        """Markdown renderer switches headings and summary labels for English reports."""
        r = _make_result(
            name="Kweichow Moutai",
            operation_advice="Buy",
            analysis_summary="Momentum remains constructive.",
            report_language="en",
        )
        out = render("markdown", [r], summary_only=True)
        self.assertIsNotNone(out)
        self.assertIn("Decision Dashboard", out)
        self.assertIn("Summary", out)
        self.assertIn("Buy", out)

    def test_render_markdown_market_snapshot_uses_template_context(self) -> None:
        """Market snapshot macro should render localized labels with template context."""
        r = _make_result(
            code="AAPL",
            name="Apple",
            operation_advice="Buy",
            report_language="en",
        )
        r.market_snapshot = {
            "close": "180.10",
            "prev_close": "178.25",
            "open": "179.00",
            "high": "181.20",
            "low": "177.80",
            "pct_chg": "+1.04%",
            "change_amount": "1.85",
            "amplitude": "1.91%",
            "volume": "1200000",
            "amount": "215000000",
            "price": "180.35",
            "volume_ratio": "1.2",
            "turnover_rate": "0.8%",
            "source": "polygon",
        }

        out = render("markdown", [r], summary_only=False)

        self.assertIsNotNone(out)
        self.assertIn("Market Snapshot", out)
        self.assertIn("Volume Ratio", out)

    def test_render_markdown_collapses_unavailable_chip_structure(self) -> None:
        r = _make_result(
            dashboard={
                "core_conclusion": {"one_sentence": "wait and see"},
                "data_perspective": {
                    "chip_structure": {
                        "profit_ratio": "missing data，Unable to judge",
                        "avg_cost": "missing data，Unable to judge",
                        "concentration": "missing data，Unable to judge",
                        "chip_health": "missing data，Unable to judge",
                    }
                },
            }
        )

        out = render("markdown", [r], summary_only=False)

        self.assertIsNotNone(out)
        self.assertIn("**chips**: Chip distribution is not enabled or the data source is temporarily unavailable，Not included in chip judgment。", out)
        self.assertEqual(out.count("missing data，Unable to judge"), 0)

    def test_render_unknown_platform_returns_none(self) -> None:
        """Unknown platform returns None (caller fallback)."""
        r = _make_result()
        out = render("unknown_platform", [r])
        self.assertIsNone(out)

    def test_render_empty_results_returns_content(self) -> None:
        """Empty results still produces header."""
        out = render("markdown", [], summary_only=True)
        self.assertIsNotNone(out)
        self.assertIn("0", out)
