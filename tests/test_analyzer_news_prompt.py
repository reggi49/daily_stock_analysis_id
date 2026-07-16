# -*- coding: utf-8 -*-
"""Tests for analyzer news prompt hard constraints (Issue #697)."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

try:
    import litellm  # noqa: F401
except ModuleNotFoundError:
    from tests.litellm_stub import ensure_litellm_stub

    ensure_litellm_stub()

from src.analyzer import (
    GeminiAnalyzer,
    _BULLISH_TREND_HINTS,
    _contains_trend_hint,
    _infer_trend_direction,
    _sanitize_trend_analysis_for_prompt,
)


class AnalyzerNewsPromptTestCase(unittest.TestCase):
    def test_contains_trend_hint_treats_non_adjacent_negation_as_negated(self) -> None:
        self.assertFalse(_contains_trend_hint("An upward trend has not yet formed，Continue to observe。", _BULLISH_TREND_HINTS))
        self.assertFalse(_contains_trend_hint("No upward trend formed，Continue to observe。", _BULLISH_TREND_HINTS))
        self.assertFalse(_contains_trend_hint("No upward trend has formed，Continue to observe。", _BULLISH_TREND_HINTS))
        self.assertFalse(_contains_trend_hint("No multi-head arrangement is formed，Continue to observe。", _BULLISH_TREND_HINTS))
        self.assertFalse(_contains_trend_hint("There are currently no long positions，Still need to observe。", _BULLISH_TREND_HINTS))
        self.assertFalse(_contains_trend_hint("Not yet an upward trend，Rebound still to be confirmed。", _BULLISH_TREND_HINTS))
        self.assertFalse(_contains_trend_hint("Current non-multiple arrangement，Still need to observe。", _BULLISH_TREND_HINTS))
        self.assertFalse(_contains_trend_hint("This is not a bullish trend yet.", _BULLISH_TREND_HINTS))

    def test_contains_trend_hint_scans_later_non_negated_occurrences(self) -> None:
        self.assertTrue(
            _contains_trend_hint(
                "Not a multi-head arrangement，After subsequent heavy volume, the bull arrangement signal appears again。",
                _BULLISH_TREND_HINTS,
            )
        )

    def test_contains_trend_hint_keeps_contrast_clause_target_hint(self) -> None:
        self.assertTrue(_contains_trend_hint("Not short but long arrangement，trend fix。", _BULLISH_TREND_HINTS))
        self.assertFalse(_contains_trend_hint("Not turning into an uptrend，Rebound still to be confirmed。", _BULLISH_TREND_HINTS))

    def test_contains_trend_hint_ignores_single_character_prefixes_in_common_words(self) -> None:
        self.assertTrue(_contains_trend_hint("Very obvious multi-head arrangement，The trend continues。", _BULLISH_TREND_HINTS))
        self.assertTrue(_contains_trend_hint("The upward trend in the future will be further confirmed if the volume increases。", _BULLISH_TREND_HINTS))
        self.assertEqual(
            _infer_trend_direction({"trend_status": "Very obvious multi-head arrangement", "ma_alignment": "The future upward trend is gradually clear"}),
            "bullish",
        )

    def test_infer_trend_direction_recognizes_weak_bullish_and_bearish_states(self) -> None:
        self.assertEqual(
            _infer_trend_direction({"trend_status": "Weak bulls", "ma_alignment": "Weak bulls，MA5>MA10 But MA10≤MA20"}),
            "bullish",
        )
        self.assertEqual(
            _infer_trend_direction({"trend_status": "Weak short", "ma_alignment": "Weak short，MA5<MA10 But MA10≥MA20"}),
            "bearish",
        )

    def test_infer_trend_direction_ignores_negated_bullish_hints(self) -> None:
        self.assertEqual(
            _infer_trend_direction({"trend_status": "No upward trend formed", "ma_alignment": "Current non-multiple arrangement"}),
            "neutral",
        )
        self.assertEqual(
            _infer_trend_direction({"trend_status": "No multi-head arrangement is formed", "ma_alignment": "No upward trend currently"}),
            "neutral",
        )

    def test_infer_trend_direction_keeps_contrast_clause_final_direction(self) -> None:
        self.assertEqual(
            _infer_trend_direction({"trend_status": "Not short but long arrangement", "ma_alignment": ""}),
            "bullish",
        )

    def test_analysis_prompt_resolves_shared_skill_prompt_state_by_default(self) -> None:
        with patch.object(GeminiAnalyzer, "_init_litellm", return_value=None):
            analyzer = GeminiAnalyzer()

        fake_state = SimpleNamespace(
            skill_instructions="### Skills 1: Swing low buy\n- Pay attention to support confirmation",
            default_skill_policy="",
        )
        with patch("src.agent.factory.resolve_skill_prompt_state", return_value=fake_state):
            prompt = analyzer._get_analysis_system_prompt("zh", stock_code="600519")

        self.assertIn("### Skills 1: Swing low buy", prompt)
        self.assertNotIn("Focus on trend trading", prompt)

    def test_analysis_prompt_uses_injected_skill_sections_instead_of_hardcoded_trend_baseline(self) -> None:
        with patch.object(GeminiAnalyzer, "_init_litellm", return_value=None):
            analyzer = GeminiAnalyzer(
                skill_instructions="### Skills 1: entanglement\n- Pay attention to the center and divergence",
                default_skill_policy="",
            )

        prompt = analyzer._get_analysis_system_prompt("zh", stock_code="600519")

        self.assertIn("### Skills 1: entanglement", prompt)
        self.assertNotIn("Focus on trend trading", prompt)
        self.assertNotIn("multi-head arrangement：MA5 > MA10 > MA20", prompt)

    def test_analysis_prompt_keeps_injected_default_policy_for_implicit_default_run(self) -> None:
        with patch.object(GeminiAnalyzer, "_init_litellm", return_value=None):
            analyzer = GeminiAnalyzer(
                skill_instructions="### Skills 1: Default bull trend",
                default_skill_policy="## Default skill baseline（must be strictly followed）\n- **Necessary conditions for multi-head arrangement**：MA5 > MA10 > MA20",
                use_legacy_default_prompt=True,
            )

        prompt = analyzer._get_analysis_system_prompt("zh", stock_code="600519")

        self.assertIn("Focus on trend trading", prompt)
        self.assertIn("Necessary conditions for multi-head arrangement", prompt)
        self.assertIn("multi-head arrangement：MA5 > MA10 > MA20", prompt)

    def test_analysis_prompt_requires_phase_decision_in_main_and_legacy_modes(self) -> None:
        for legacy in (False, True):
            with patch.object(GeminiAnalyzer, "_init_litellm", return_value=None):
                analyzer = GeminiAnalyzer(
                    skill_instructions="",
                    default_skill_policy="",
                    use_legacy_default_prompt=legacy,
                )

            prompt = analyzer._get_analysis_system_prompt("zh", stock_code="600519")

            self.assertIn('"phase_decision"', prompt)
            self.assertIn('"watch_conditions"', prompt)
            self.assertIn('"data_limitations"', prompt)
            self.assertIn("quote/daily_bars/technical exist stale、fallback、missing、fetch_failed、partial or estimated", prompt)
            self.assertIn("`confidence_level` Not allowed to be high", prompt)

    def test_analysis_prompt_contains_actionability_guardrails(self) -> None:
        with patch.object(GeminiAnalyzer, "_init_litellm", return_value=None):
            analyzer = GeminiAnalyzer()

        prompt = analyzer._get_analysis_system_prompt("zh", stock_code="002812")

        self.assertIn("Operability and stability constraints", prompt)
        self.assertIn("It should not be determined just because of the rise or fall in a single day.", prompt)
        self.assertIn("support/pressure level", prompt)
        self.assertIn("Washing dishes and observing", prompt)

    def test_analysis_prompt_score_scale_splits_reduce_and_sell_bands(self) -> None:
        for legacy in (False, True):
            with self.subTest(legacy=legacy):
                with patch.object(GeminiAnalyzer, "_init_litellm", return_value=None):
                    analyzer = GeminiAnalyzer(
                        skill_instructions="",
                        default_skill_policy="",
                        use_legacy_default_prompt=legacy,
                    )

                prompt = analyzer._get_analysis_system_prompt("zh", stock_code="600519")

                self.assertIn("### Reduce positions（20-39points）", prompt)
                self.assertIn("### sell（0-19points）", prompt)
                self.assertIn("20-39：Reduce positions，`action=reduce`，`decision_type=sell`。", prompt)
                self.assertIn("0-19：sell，`action=sell`，`decision_type=sell`。", prompt)
                self.assertNotIn("### sell/Reduce positions（0-39points）", prompt)

    def test_prompt_contains_time_constraints(self) -> None:
        with patch.object(GeminiAnalyzer, "_init_litellm", return_value=None):
            analyzer = GeminiAnalyzer()

        context = {
            "code": "600519",
            "stock_name": "Kweichow Moutai",
            "date": "2026-03-16",
            "today": {},
            "fundamental_context": {
                "earnings": {
                    "data": {
                        "financial_report": {"report_date": "2025-12-31", "revenue": 1000},
                        "dividend": {"ttm_cash_dividend_per_share": 1.2, "ttm_dividend_yield_pct": 2.4},
                    }
                }
            },
        }
        fake_cfg = SimpleNamespace(
            news_max_age_days=30,
            news_strategy_profile="medium",  # 7 days
        )
        with patch("src.analyzer.get_config", return_value=fake_cfg):
            prompt = analyzer._format_prompt(context, "Kweichow Moutai", news_context="news")

        self.assertIn("near7News search results for the day", prompt)
        self.assertIn("Each entry must have a specific date（YYYY-MM-DD）", prompt)
        self.assertIn("beyond near7News in the Japanese window will be ignored", prompt)
        self.assertIn("Time unknown、News whose publication date cannot be determined will be ignored.", prompt)
        self.assertIn("Financial reporting and dividends（Value investment caliber）", prompt)
        self.assertIn("Fabrication is prohibited", prompt)

    def test_prompt_includes_capital_flow_as_operation_filter(self) -> None:
        with patch.object(GeminiAnalyzer, "_init_litellm", return_value=None):
            analyzer = GeminiAnalyzer()

        context = {
            "code": "002812",
            "stock_name": "Enjie shares",
            "date": "2026-04-01",
            "today": {"close": 32.8, "ma5": 31.2, "ma10": 30.5, "ma20": 29.8},
            "fundamental_context": {
                "capital_flow": {
                    "status": "ok",
                    "data": {
                        "stock_flow": {
                            "main_net_inflow": -1200000,
                            "inflow_5d": -3600000,
                            "inflow_10d": -5200000,
                        },
                        "sector_rankings": {
                            "top": [{"name": "battery"}],
                            "bottom": [{"name": "Chemical industry"}],
                        },
                    },
                }
            },
        }

        prompt = analyzer._format_prompt(context, "Enjie shares", news_context=None)

        self.assertIn("Main flow of funds（Action suggestions filter）", prompt)
        self.assertIn("Main net inflow", prompt)
        self.assertIn("-1200000", prompt)
        self.assertIn("When the pressure is close and the main force flows out, no additional buying is allowed.", prompt)
        self.assertIn("Washing dishes and observing", prompt)

    def test_prompt_prefers_context_news_window_days(self) -> None:
        with patch.object(GeminiAnalyzer, "_init_litellm", return_value=None):
            analyzer = GeminiAnalyzer()

        context = {
            "code": "600519",
            "stock_name": "Kweichow Moutai",
            "date": "2026-03-16",
            "today": {},
            "news_window_days": 1,
        }
        fake_cfg = SimpleNamespace(
            news_max_age_days=30,
            news_strategy_profile="long",  # 30 days if fallback is used
        )
        with patch("src.analyzer.get_config", return_value=fake_cfg):
            prompt = analyzer._format_prompt(context, "Kweichow Moutai", news_context="news")

        self.assertIn("near1News search results for the day", prompt)
        self.assertIn("beyond near1News in the Japanese window will be ignored", prompt)

    def test_format_prompt_injects_market_phase_and_pack_summary_before_technical_data(self) -> None:
        with patch.object(GeminiAnalyzer, "_init_litellm", return_value=None):
            analyzer = GeminiAnalyzer()

        context = {
            "code": "600519",
            "stock_name": "Kweichow Moutai",
            "date": "2026-03-27",
            "today": {},
            "market_phase_context": {
                "market": "cn",
                "phase": "premarket",
                "market_local_time": "2026-03-27T09:00:00+08:00",
                "effective_daily_bar_date": "2026-03-26",
                "is_partial_bar": False,
                "minutes_to_open": 30,
                "warnings": [],
            },
        }

        prompt = analyzer._format_prompt(
            context,
            "Kweichow Moutai",
            news_context=None,
            analysis_context_pack_summary="\n## Analysis context package summary\n- Data block status：Quotes available\n",
        )

        phase_index = prompt.index("market stage context")
        pack_index = prompt.index("Analysis context package summary")
        technical_index = prompt.index("Technical data")
        self.assertLess(phase_index, technical_index)
        self.assertLess(phase_index, pack_index)
        self.assertLess(pack_index, technical_index)
        self.assertIn("Before the market", prompt)
        self.assertIn("Shall not be described“Today’s trend has already occurred”", prompt)

    def test_format_prompt_omits_market_phase_section_without_context(self) -> None:
        with patch.object(GeminiAnalyzer, "_init_litellm", return_value=None):
            analyzer = GeminiAnalyzer()

        context = {
            "code": "600519",
            "stock_name": "Kweichow Moutai",
            "date": "2026-03-27",
            "today": {},
        }

        prompt = analyzer._format_prompt(context, "Kweichow Moutai", news_context=None)

        self.assertNotIn("market stage context", prompt)
        self.assertNotIn("Analysis context package summary", prompt)

    def test_format_prompt_labels_intraday_partial_quote_as_estimated(self) -> None:
        with patch.object(GeminiAnalyzer, "_init_litellm", return_value=None):
            analyzer = GeminiAnalyzer()

        context = {
            "code": "600519",
            "stock_name": "Kweichow Moutai",
            "date": "2026-03-27",
            "today": {"close": 1880.0},
            "market_phase_context": {
                "phase": "intraday",
                "is_partial_bar": True,
                "warnings": [],
            },
        }

        prompt = analyzer._format_prompt(context, "Kweichow Moutai", news_context=None)

        self.assertIn("### Latest Quotes", prompt)
        self.assertIn("| Intraday estimated price | 1880.0 Yuan |", prompt)
        self.assertNotIn("### Today's Quote", prompt)
        self.assertNotIn("| closing price | 1880.0 Yuan |", prompt)

    def test_format_prompt_uses_complete_daily_labels_for_premarket_and_non_trading(self) -> None:
        with patch.object(GeminiAnalyzer, "_init_litellm", return_value=None):
            analyzer = GeminiAnalyzer()

        for phase in ("premarket", "non_trading"):
            context = {
                "code": "600519",
                "stock_name": "Kweichow Moutai",
                "date": "2026-03-27",
                "today": {
                    "close": 1870.0,
                    "open": 1860.0,
                    "high": 1880.0,
                    "low": 1855.0,
                },
                "market_phase_context": {
                    "phase": phase,
                    "is_partial_bar": False,
                    "warnings": [],
                },
            }

            prompt = analyzer._format_prompt(context, "Kweichow Moutai", news_context=None)

            self.assertIn("### Quotes from the last full trading day", prompt)
            self.assertIn("| Last full trading day's closing price | 1870.0 Yuan |", prompt)
            self.assertIn("| opening price | 1860.0 Yuan |", prompt)
            self.assertIn("| highest price | 1880.0 Yuan |", prompt)
            self.assertIn("| lowest price | 1855.0 Yuan |", prompt)
            self.assertNotIn("### Today's Quote", prompt)
            self.assertNotIn("| closing price | 1870.0 Yuan |", prompt)

    def test_format_prompt_does_not_label_realtime_overlay_as_previous_close(self) -> None:
        with patch.object(GeminiAnalyzer, "_init_litellm", return_value=None):
            analyzer = GeminiAnalyzer()

        for phase in ("premarket", "non_trading"):
            context = {
                "code": "600519",
                "stock_name": "Kweichow Moutai",
                "date": "2026-03-27",
                "today": {
                    "close": 1882.5,
                    "open": 1878.0,
                    "high": 1885.0,
                    "low": 1876.0,
                    "pct_chg": 0.42,
                    "volume": 1200000,
                    "amount": 226000000,
                    "data_source": "realtime:tencent",
                    "is_estimated": True,
                    "estimated_fields": ["close", "open", "high", "low"],
                },
                "market_phase_context": {
                    "phase": phase,
                    "is_partial_bar": False,
                    "warnings": [],
                },
            }

            prompt = analyzer._format_prompt(context, "Kweichow Moutai", news_context=None)

            self.assertIn("### Latest Quotes", prompt)
            self.assertIn("| Real-time price estimate | 1882.5 Yuan |", prompt)
            self.assertNotIn("### Quotes from the last full trading day", prompt)
            self.assertNotIn("| Last full trading day's closing price | 1882.5 Yuan |", prompt)
            self.assertNotIn("| opening price |", prompt)
            self.assertNotIn("| highest price |", prompt)
            self.assertNotIn("| lowest price |", prompt)
            self.assertIn("| Real-time price increase and decrease | 0.42% |", prompt)
            self.assertIn("| Real-time trading volume | 120.00 10,000 shares |", prompt)
            self.assertIn("| Real-time trading volume | 2.26 billion |", prompt)
            self.assertNotIn("| Increase or decrease | 0.42% |", prompt)
            self.assertNotIn("| Volume | 120.00 10,000 shares |", prompt)
            self.assertNotIn("| Turnover | 2.26 billion |", prompt)

    def test_format_prompt_does_not_label_date_mismatch_as_previous_close(self) -> None:
        with patch.object(GeminiAnalyzer, "_init_litellm", return_value=None):
            analyzer = GeminiAnalyzer()

        context = {
            "code": "600519",
            "stock_name": "Kweichow Moutai",
            "date": "2026-03-27",
            "today": {
                "close": 1882.5,
                "open": 1878.0,
                "high": 1885.0,
                "low": 1876.0,
                "date": "2026-03-27",
            },
            "market_phase_context": {
                "phase": "premarket",
                "effective_daily_bar_date": "2026-03-26",
                "is_partial_bar": False,
                "warnings": [],
            },
        }

        prompt = analyzer._format_prompt(context, "Kweichow Moutai", news_context=None)

        self.assertIn("### Latest Quotes", prompt)
        self.assertIn("| latest price | 1882.5 Yuan |", prompt)
        self.assertNotIn("### Quotes from the last full trading day", prompt)
        self.assertNotIn("| Last full trading day's closing price | 1882.5 Yuan |", prompt)
        self.assertNotIn("| opening price |", prompt)
        self.assertNotIn("| highest price |", prompt)
        self.assertNotIn("| lowest price |", prompt)

    def test_format_prompt_keeps_legacy_quote_labels_without_partial_intraday_context(self) -> None:
        with patch.object(GeminiAnalyzer, "_init_litellm", return_value=None):
            analyzer = GeminiAnalyzer()

        for phase_context in (
            {"phase": "intraday", "is_partial_bar": False, "warnings": []},
            {"phase": "intraday", "warnings": []},
            {"phase": "postmarket", "is_partial_bar": False, "warnings": []},
            {"phase": "unknown", "is_partial_bar": True, "warnings": []},
            None,
        ):
            context = {
                "code": "600519",
                "stock_name": "Kweichow Moutai",
                "date": "2026-03-27",
                "today": {"close": 1880.0},
            }
            if phase_context is not None:
                context["market_phase_context"] = phase_context

            prompt = analyzer._format_prompt(context, "Kweichow Moutai", news_context=None)

            self.assertIn("### Today's Quote", prompt)
            self.assertIn("| closing price | 1880.0 Yuan |", prompt)

    def test_format_prompt_omits_legacy_trend_checks_for_nondefault_skill_mode(self) -> None:
        with patch.object(GeminiAnalyzer, "_init_litellm", return_value=None):
            analyzer = GeminiAnalyzer(
                skill_instructions="### Skills 1: entanglement\n- Pay attention to the center and divergence",
                default_skill_policy="",
                use_legacy_default_prompt=False,
            )

        context = {
            "code": "600519",
            "stock_name": "Kweichow Moutai",
            "date": "2026-03-16",
            "today": {"close": 100, "ma5": 99, "ma10": 98, "ma20": 97},
            "trend_analysis": {
                "trend_status": "The shock is strong",
                "ma_alignment": "Divergent after bonding",
                "trend_strength": 61,
                "bias_ma5": 1.2,
                "bias_ma10": 2.4,
                "volume_status": "equal amount",
                "volume_trend": "Moderate energy",
                "buy_signal": "observe",
                "signal_score": 58,
                "signal_reasons": ["Structure to be confirmed"],
                "risk_factors": ["No divergence confirmed"],
            },
        }
        prompt = analyzer._format_prompt(context, "Kweichow Moutai", news_context=None)

        self.assertIn("Whether the current structure meets the key triggering conditions for activating skills", prompt)
        self.assertNotIn("Are you satisfied? MA5>MA10>MA20 multi-head arrangement", prompt)
        self.assertNotIn("exceed5%Must be marked\"It is strictly forbidden to chase high\"", prompt)
        self.assertNotIn("MA5>MA10>MA20for long", prompt)

    def test_format_prompt_removes_bullish_reasons_when_final_trend_is_bearish(self) -> None:
        with patch.object(GeminiAnalyzer, "_init_litellm", return_value=None):
            analyzer = GeminiAnalyzer(
                skill_instructions="### Skills 1: entanglement\n- Pay attention to the center and divergence",
                default_skill_policy="",
                use_legacy_default_prompt=False,
            )

        context = {
            "code": "603259",
            "stock_name": "WuXi AppTec",
            "date": "2026-04-28",
            "today": {"close": 58.6, "ma5": 57.2, "ma10": 58.8, "ma20": 60.4},
            "yesterday": {"close": 57.8},
            "volume_change_ratio": 12.4,
            "trend_analysis": {
                "trend_status": "Short arrangement",
                "ma_alignment": "Short arrangement MA5<MA10<MA20",
                "trend_strength": 34,
                "bias_ma5": 2.1,
                "bias_ma10": -0.8,
                "volume_status": "Increase the volume",
                "volume_trend": "Heavy volume shock",
                "buy_signal": "observe",
                "signal_score": 41,
                "signal_reasons": ["multi-head arrangement，Continue to rise", "Event catalysis exists but the technology needs to be confirmed"],
                "risk_factors": ["fell belowMA20，Trend under pressure"],
            },
        }

        prompt = analyzer._format_prompt(
            context,
            "WuXi AppTec",
            news_context="2026-04-27 First quarter earnings beat expectations，Order growth。",
        )

        self.assertIn("Short arrangement MA5<MA10<MA20", prompt)
        self.assertNotIn("multi-head arrangement，Continue to rise", prompt)
        self.assertIn("Event catalysis exists but the technology needs to be confirmed", prompt)
        self.assertIn("Event first、Technology to be confirmed", prompt)
        self.assertIn("Energy abnormality prompt", prompt)
        self.assertIn("technical consistency", prompt)

    def test_format_prompt_removes_bearish_risks_when_final_trend_is_bullish(self) -> None:
        with patch.object(GeminiAnalyzer, "_init_litellm", return_value=None):
            analyzer = GeminiAnalyzer(
                skill_instructions="### Skills 1: entanglement\n- Pay attention to the center and divergence",
                default_skill_policy="",
                use_legacy_default_prompt=False,
            )

        context = {
            "code": "600519",
            "stock_name": "Kweichow Moutai",
            "date": "2026-04-28",
            "today": {"close": 1688.0, "ma5": 1675.0, "ma10": 1660.0, "ma20": 1640.0},
            "trend_analysis": {
                "trend_status": "multi-head arrangement",
                "ma_alignment": "multi-head arrangement MA5>MA10>MA20",
                "trend_strength": 78,
                "bias_ma5": 1.8,
                "bias_ma10": 3.2,
                "volume_status": "equal amount",
                "volume_trend": "Coordination of quantity and price",
                "buy_signal": "Stronger",
                "signal_score": 73,
                "signal_reasons": ["multi-head arrangement，Continue to rise", "Short arrangement，Continued decline"],
                "risk_factors": ["Short arrangement，Continued decline", "Volatility may amplify before financial report disclosure"],
            },
        }

        prompt = analyzer._format_prompt(context, "Kweichow Moutai", news_context=None)

        self.assertIn("multi-head arrangement MA5>MA10>MA20", prompt)
        self.assertIn("Volatility may amplify before financial report disclosure", prompt)
        self.assertNotIn("Short arrangement，Continued decline\n", prompt)
        self.assertNotIn("Short arrangement，Continued decline", prompt)
        self.assertIn("Reasons for short positions that directly conflict with the long-term main judgment have been eliminated.", prompt)
        self.assertIn("Short structural risk statements that directly conflict with the long primary judgment have been eliminated.", prompt)

    def test_format_prompt_removes_bullish_reasons_when_final_trend_is_weak_bearish(self) -> None:
        with patch.object(GeminiAnalyzer, "_init_litellm", return_value=None):
            analyzer = GeminiAnalyzer(
                skill_instructions="### Skills 1: entanglement\n- Pay attention to the center and divergence",
                default_skill_policy="",
                use_legacy_default_prompt=False,
            )

        context = {
            "code": "300750",
            "stock_name": "Ningde era",
            "date": "2026-04-28",
            "today": {"close": 178.5, "ma5": 176.0, "ma10": 180.2, "ma20": 179.9},
            "trend_analysis": {
                "trend_status": "Weak short",
                "ma_alignment": "Weak short，MA5<MA10 But MA10≥MA20",
                "trend_strength": 43,
                "bias_ma5": 1.4,
                "bias_ma10": -0.9,
                "volume_status": "equal amount",
                "volume_trend": "Average capacity",
                "buy_signal": "observe",
                "signal_score": 45,
                "signal_reasons": ["Weak bull repair", "multi-head arrangement，Continue to rise", "Event catalysis exists but the technology needs to be confirmed"],
                "risk_factors": ["MA10 Suppression is still there"],
            },
        }

        prompt = analyzer._format_prompt(
            context,
            "Ningde era",
            news_context="2026-04-27 new product launch，Market sentiment picks up。",
        )

        self.assertIn("Weak short，MA5<MA10 But MA10≥MA20", prompt)
        self.assertNotIn("Weak bull repair", prompt)
        self.assertNotIn("multi-head arrangement，Continue to rise", prompt)
        self.assertIn("Event catalysis exists but the technology needs to be confirmed", prompt)
        self.assertIn("Structural reasons for bullish positions that directly conflict with the primary judgment of short sellers have been eliminated.", prompt)

    def test_sanitize_trend_analysis_for_prompt_returns_derived_copy_only(self) -> None:
        original = {
            "trend_status": "Short arrangement",
            "ma_alignment": "Short arrangement MA5<MA10<MA20",
            "signal_reasons": ["multi-head arrangement，Continue to rise", "Event catalysis exists but the technology needs to be confirmed"],
            "risk_factors": ["fell belowMA20，Trend under pressure"],
        }

        sanitized = _sanitize_trend_analysis_for_prompt(original, volume_change_ratio=12.4)

        self.assertEqual(
            original["signal_reasons"],
            ["multi-head arrangement，Continue to rise", "Event catalysis exists but the technology needs to be confirmed"],
        )
        self.assertNotIn("prompt_consistency_notes", original)
        self.assertNotIn("prompt_trend_direction", original)
        self.assertNotIn("multi-head arrangement，Continue to rise", sanitized["signal_reasons"])
        self.assertEqual(sanitized["prompt_trend_direction"], "bearish")


if __name__ == "__main__":
    unittest.main()
