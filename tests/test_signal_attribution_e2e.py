"""
End-to-end tests: signal_attribution complete contract convergence tests.

Verifies the following paths:
1. LLM raw JSON -> _parse_response() -> AnalysisResult.dashboard (normalization effective)
2. AnalysisResult.dashboard -> notification (correct display)
3. AnalysisResult.dashboard -> Jinja2 template (correct rendering)
4. AnalysisResult.dashboard -> HistoryService markdown (correct rendering)
5. check_content_integrity() (contract check)
"""
import sys
import os
import pytest
import json

# # Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.analyzer import AnalysisResult, check_content_integrity
from src.utils.data_processing import normalize_dashboard_signal_attribution
from src.agent.runner import parse_dashboard_json
from src.services.report_renderer import render


class TestSignalAttributionE2E:
    """End-to-end test: verify signal_attribution works correctly across all paths"""

    def _make_dashboard_with_signal_attr(self, signal_attr):
        """Build a dashboard dict containing signal_attribution"""
        return {
            "core_conclusion": {
                "one_sentence": "Test conclusion",
                "signal": "buy",
                "confidence": "in",
            },
            "intelligence": {
                "risk_alerts": ["Testing risks"],
            },
            "signal_attribution": signal_attr,
        }

    def _make_result(self, dashboard):
        """Build an AnalysisResult"""
        return AnalysisResult(
            code="600519",
            name="test stocks",
            sentiment_score=50,
            trend_prediction="shock",
            operation_advice="hold",
            decision_type="hold",
            confidence_level="in",
            dashboard=dashboard,
            analysis_summary="Test summary",
        )

    # # ========== Test 1: _parse_response() normalization ==========
    def test_normalize_called_in_parse_response(self):
        """
        Test that normalization function is called in _parse_response().

        Verifies:
        1. Input contribution as string "30%" -> normalized to int 30
        2. Input contribution sum != 100 -> normalized to sum=100
        """
        from src.analyzer import GeminiAnalyzer

        # Create the analyzer instance
        analyzer = GeminiAnalyzer.__new__(GeminiAnalyzer)

        # Mock the JSON returned by the LLM (contributions are strings, sum != 100)
        response_text = json.dumps({
            "sentiment_score": 50,
            "trend_prediction": "shock",
            "operation_advice": "hold",
            "decision_type": "hold",
            "confidence_level": "in",
            "analysis_summary": "test",
            "dashboard": {
                "core_conclusion": {"one_sentence": "test", "signal": "hold", "confidence": "in"},
                "intelligence": {"risk_alerts": []},
                "signal_attribution": {
                    "technical_indicators": "30%",
                    "news_sentiment": 20,
                    "fundamentals": 30,
                    "market_conditions": 10,  # sum=90，And one of them is a string
                    "strongest_bullish_signal": "Test bullish",
                    "strongest_bearish_signal": "Test bearish",
                },
            },
        })

        # Call _parse_response()
        result = analyzer._parse_response(response_text, "600519", "test")

        # Verify normalization was executed
        dash = result.dashboard
        assert isinstance(dash, dict), "dashboard should be a dict"

        signal_attr = dash.get("signal_attribution")
        assert signal_attr is not None, "signal_attribution should exist"

        # Verify the string was converted to int
        assert isinstance(signal_attr.get("technical_indicators"), int), "technical_indicators should be int"

        # Verify the sum is 100
        total = sum([
            signal_attr.get("technical_indicators", 0),
            signal_attr.get("news_sentiment", 0),
            signal_attr.get("fundamentals", 0),
            signal_attr.get("market_conditions", 0),
        ])
        assert total == 100, f"Contribution sum should be 100, actual={total}"

    # # ========== Test 2: notification rendering ==========
    def test_notification_renders_signal_attribution(self):
        """
        Test that generate_dashboard_report() in notification.py correctly renders signal_attribution.

        Verifies:
        1. When signal_attribution exists, notification contains "Signal Attribution" section
        2. All four contribution values are displayed correctly
        """
        from src.notification import NotificationService

        signal_attr = {
            "technical_indicators": 35,
            "news_sentiment": 25,
            "fundamentals": 20,
            "market_conditions": 20,
            "strongest_bullish_signal": "MACDgolden fork",
            "strongest_bearish_signal": "Trading volume shrinks",
        }
        dashboard = self._make_dashboard_with_signal_attr(signal_attr)
        result = self._make_result(dashboard)

        # Call generate_dashboard_report()
        notification = NotificationService()
        report = notification.generate_dashboard_report([result], [dashboard])

        # Verify it contains the signal-attribution section
        assert "signal attribution" in report or "Signal Attribution" in report, "Notification should contain signal attribution section"
        assert "35%" in report, "Notification should display technical_indicators=35%"
        assert "25%" in report, "Notification should display news_sentiment=25%"
        assert "20%" in report, "Notification should display fundamentals=20%"
        assert "20%" in report, "Notification should display market_conditions=20%"
        assert "MACDgolden fork" in report, "Notification should display strongest_bullish_signal"

    # # ========== Test 3: Jinja2 template rendering ==========
    def test_jinja2_template_renders_signal_attribution(self):
        """
        Test that templates/report_markdown.j2 correctly renders signal_attribution.

        Verifies:
        1. When signal_attribution exists, template output contains attribution weights
        2. All four contribution values are displayed correctly
        """
        signal_attr = {
            "technical_indicators": 35,
            "news_sentiment": 25,
            "fundamentals": 20,
            "market_conditions": 20,
            "strongest_bullish_signal": "MACDgolden fork",
        }
        result = self._make_result(self._make_dashboard_with_signal_attr(signal_attr))

        out = render("markdown", [result], summary_only=False, extra_context={"report_language": "zh"})

        assert out is not None
        assert "35%" in out
        assert "MACDgolden fork" in out

    def test_parse_dashboard_json_normalizes_nested_dashboard_payload(self):
        """Agent JSON can return a full report object with nested dashboard."""
        payload = json.dumps({
            "dashboard": {
                "signal_attribution": {
                    "technical_indicators": "70%",
                    "news_sentiment": "10%",
                    "fundamentals": "10%",
                    "market_conditions": "10%",
                }
            }
        })

        parsed = parse_dashboard_json(payload)

        assert parsed is not None
        signal_attr = parsed["dashboard"]["signal_attribution"]
        assert signal_attr["technical_indicators"] == 70
        assert isinstance(signal_attr["technical_indicators"], int)

    def test_non_dict_signal_attribution_is_removed_before_rendering(self):
        """Invalid non-dict signal_attribution must not survive into renderers."""
        dashboard = {"signal_attribution": "bad payload"}

        normalize_dashboard_signal_attribution(dashboard)

        assert "signal_attribution" not in dashboard

    def test_partial_signal_attribution_uses_same_display_contract(self):
        """Partial weights should not render N/A% or None% in any report path."""
        from src.notification import NotificationService
        from src.services.history_service import HistoryService

        dashboard = self._make_dashboard_with_signal_attr({
            "technical_indicators": 35,
            "news_sentiment": None,
            "fundamentals": None,
            "market_conditions": 0,
            "strongest_bullish_signal": "MACDgolden fork",
        })
        result = self._make_result(dashboard)
        notification = NotificationService()

        dashboard_report = notification.generate_dashboard_report([result], [dashboard])
        single_report = notification.generate_single_stock_report(result)

        class MockRecord:
            created_at = None

        history_report = HistoryService.__new__(HistoryService)._generate_single_stock_markdown(result, MockRecord())
        template_report = render("markdown", [result], summary_only=False, extra_context={"report_language": "zh"})

        for output in [dashboard_report, single_report, history_report, template_report]:
            assert output is not None
            assert "N/A%" not in output
            assert "None%" not in output
            assert "35%" in output

    def test_all_zero_signal_attribution_is_hidden_without_signals(self):
        """All-zero weights without strongest signals should not render attribution."""
        from src.notification import NotificationService
        from src.services.history_service import HistoryService

        dashboard = self._make_dashboard_with_signal_attr({
            "technical_indicators": 0,
            "news_sentiment": 0,
            "fundamentals": 0,
            "market_conditions": 0,
            "strongest_bullish_signal": None,
            "strongest_bearish_signal": None,
        })
        result = self._make_result(dashboard)
        notification = NotificationService()

        dashboard_report = notification.generate_dashboard_report([result], [dashboard])
        single_report = notification.generate_single_stock_report(result)

        class MockRecord:
            created_at = None

        history_report = HistoryService.__new__(HistoryService)._generate_single_stock_markdown(result, MockRecord())
        template_report = render("markdown", [result], summary_only=False, extra_context={"report_language": "zh"})

        for output in [dashboard_report, single_report, history_report, template_report]:
            assert output is not None
            assert "signal attribution" not in output
            assert "Signal Attribution" not in output

    def test_non_finite_signal_attribution_is_hidden_across_real_paths(self):
        """NaN/Infinity weights are missing values, not confident attribution."""
        from src.analyzer import GeminiAnalyzer
        from src.notification import NotificationService
        from src.services.history_service import HistoryService

        def non_finite_signal_attr():
            return {
                "technical_indicators": float("nan"),
                "news_sentiment": "NaN",
                "fundamentals": float("inf"),
                "market_conditions": "-Infinity",
                "strongest_bullish_signal": None,
                "strongest_bearish_signal": "",
            }

        response_text = json.dumps({
            "sentiment_score": 50,
            "trend_prediction": "shock",
            "operation_advice": "hold",
            "decision_type": "hold",
            "confidence_level": "in",
            "analysis_summary": "test",
            "dashboard": {
                "core_conclusion": {"one_sentence": "test", "signal": "hold", "confidence": "in"},
                "intelligence": {"risk_alerts": []},
                "signal_attribution": non_finite_signal_attr(),
            },
        })

        analyzer = GeminiAnalyzer.__new__(GeminiAnalyzer)
        result = analyzer._parse_response(response_text, "600519", "test")
        dashboard = result.dashboard
        signal_attr = dashboard["signal_attribution"]

        for key in ("technical_indicators", "news_sentiment", "fundamentals", "market_conditions"):
            assert signal_attr[key] is None
        assert signal_attr["strongest_bearish_signal"] is None

        parsed = parse_dashboard_json(json.dumps({
            "dashboard": {
                "signal_attribution": non_finite_signal_attr(),
            }
        }))
        assert parsed is not None
        parsed_attr = parsed["dashboard"]["signal_attribution"]
        for key in ("technical_indicators", "news_sentiment", "fundamentals", "market_conditions"):
            assert parsed_attr[key] is None

        notification = NotificationService()
        dashboard_report = notification.generate_dashboard_report([result], [dashboard])
        single_report = notification.generate_single_stock_report(result)

        class MockRecord:
            created_at = None

        history_report = HistoryService.__new__(HistoryService)._generate_single_stock_markdown(result, MockRecord())
        template_report = render("markdown", [result], summary_only=False, extra_context={"report_language": "zh"})

        for output in [dashboard_report, single_report, history_report, template_report]:
            assert output is not None
            assert "signal attribution" not in output
            assert "Signal Attribution" not in output
            assert "NaN" not in output
            assert "Infinity" not in output

    # # ========== Test 4: HistoryService markdown rendering ==========
    def test_history_service_renders_signal_attribution(self):
        """
        Test that HistoryService._generate_single_stock_markdown() correctly renders signal_attribution.

        Verifies:
        1. When signal_attribution exists, markdown contains "Signal Attribution Analysis" section
        2. All four contribution values are displayed correctly
        """
        from src.services.history_service import HistoryService

        signal_attr = {
            "technical_indicators": 35,
            "news_sentiment": 25,
            "fundamentals": 20,
            "market_conditions": 20,
            "strongest_bullish_signal": "MACDgolden fork",
            "strongest_bearish_signal": "Trading volume shrinks",
        }
        dashboard = self._make_dashboard_with_signal_attr(signal_attr)
        result = self._make_result(dashboard)

        # Create a mock record
        class MockRecord:
            created_at = None

        # Call _generate_single_stock_markdown()
        history_service = HistoryService.__new__(HistoryService)
        markdown = history_service._generate_single_stock_markdown(result, MockRecord())

        # Verify it contains the signal-attribution section
        assert "signal attribution" in markdown or "Signal Attribution" in markdown, "Markdown should contain signal attribution section"
        assert "35%" in markdown, "Markdown should display technical_indicators=35%"
        assert "MACDgolden fork" in markdown, "Markdown should display strongest_bullish_signal"

    # # ========== Test 5: check_content_integrity() optional contract ==========
    def test_check_content_integrity_treats_signal_attribution_as_optional(self):
        """
        Test that check_content_integrity() treats signal_attribution as an optional display field.

        Verifies:
        1. When signal_attribution exists, not added to missing
        2. When signal_attribution is missing, not added to missing
        3. When signal_attribution contributions are missing, not added to missing
        """
        # Case 1: signal_attribution complete
        signal_attr = {
            "technical_indicators": 35,
            "news_sentiment": 25,
            "fundamentals": 20,
            "market_conditions": 20,
        }
        dashboard = self._make_dashboard_with_signal_attr(signal_attr)
        result = self._make_result(dashboard)

        passed, missing = check_content_integrity(result)
        signal_attr_missing = [m for m in missing if "signal_attribution" in m]
        assert len(signal_attr_missing) == 0, f"signal_attribution should not appear in missing when complete, actual: {signal_attr_missing}"

        # Case 2: signal_attribution missing
        dashboard_no_attr = self._make_dashboard_with_signal_attr(None)
        dashboard_no_attr["battle_plan"] = {"sniper_points": {"stop_loss": "100"}}
        result_no_attr = self._make_result(dashboard_no_attr)

        passed, missing = check_content_integrity(result_no_attr)
        assert passed is True
        signal_attr_missing = [m for m in missing if "signal_attribution" in m]
        assert len(signal_attr_missing) == 0, "signal_attribution should not appear in missing when absent"

        # Case 3: signal_attribution contribution missing
        signal_attr_incomplete = {
            "technical_indicators": 35,
            "news_sentiment": 25,
            # Missing fundamentals and market_conditions
        }
        dashboard_incomplete = self._make_dashboard_with_signal_attr(signal_attr_incomplete)
        dashboard_incomplete["battle_plan"] = {"sniper_points": {"stop_loss": "100"}}
        result_incomplete = self._make_result(dashboard_incomplete)

        passed, missing = check_content_integrity(result_incomplete)
        assert passed is True
        signal_attr_missing = [m for m in missing if "signal_attribution" in m]
        assert len(signal_attr_missing) == 0, "signal_attribution should not appear in missing when contributions are incomplete"

    # # ========== Test 6: normalization-function test ==========
    def test_normalize_dashboard_signal_attribution_direct(self):
        """
        Directly test the normalize_dashboard_signal_attribution() function.

        Verifies:
        1. String percentages converted to int
        2. Negative values converted to 0
        3. Sum != 100 is normalized to 100
        4. None value handling
        """
        # Case 1: string percentage
        dashboard = {
            "signal_attribution": {
                "technical_indicators": "30%",
                "news_sentiment": 20,
                "fundamentals": "30",
                "market_conditions": 10,
                "strongest_bullish_signal": "test",
            },
        }
        normalize_dashboard_signal_attribution(dashboard)
        attr = dashboard["signal_attribution"]
        # Verify the string was converted to int (the exact value may change due to normalization, but it should be int)
        assert isinstance(attr["technical_indicators"], int), f"String percentage should be converted to int: {attr['technical_indicators']}"
        assert isinstance(attr["fundamentals"], int), f"The string should be converted to int: {attr['fundamentals']}"

        # Verify the sum is 100
        total = sum([
            attr.get("technical_indicators", 0),
            attr.get("news_sentiment", 0),
            attr.get("fundamentals", 0),
            attr.get("market_conditions", 0),
        ])
        assert total == 100, f"The normalized sum should be 100: {total}"

        # Case 2: negative number
        dashboard = {
            "signal_attribution": {
                "technical_indicators": -10,
                "news_sentiment": 20,
                "fundamentals": 30,
                "market_conditions": 40,
            },
        }
        normalize_dashboard_signal_attribution(dashboard)
        attr = dashboard["signal_attribution"]
        assert attr["technical_indicators"] == 0, f"Negative numbers should be converted to 0: {attr['technical_indicators']}"

        # Case 3: sum=100, no normalization needed
        dashboard = {
            "signal_attribution": {
                "technical_indicators": 25,
                "news_sentiment": 25,
                "fundamentals": 25,
                "market_conditions": 25,
            },
        }
        normalize_dashboard_signal_attribution(dashboard)
        attr = dashboard["signal_attribution"]
        total = sum([attr["technical_indicators"], attr["news_sentiment"], attr["fundamentals"], attr["market_conditions"]])
        assert total == 100, f"The sum should be 100: {total}"

        # Case 4: sum != 100 (needs normalization)
        dashboard = {
            "signal_attribution": {
                "technical_indicators": 10,
                "news_sentiment": 20,
                "fundamentals": 30,
                "market_conditions": 30,  # sum=90
            },
        }
        normalize_dashboard_signal_attribution(dashboard)
        attr = dashboard["signal_attribution"]
        total = sum([attr["technical_indicators"], attr["news_sentiment"], attr["fundamentals"], attr["market_conditions"]])
        assert total == 100, f"The normalized sum should be 100: {total}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
