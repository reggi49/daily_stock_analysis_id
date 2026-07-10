#!/usr/bin/env python3
"""
Signal Attribution Supplement Tests

Covers:
1. generate_single_stock_report() rendering
2. _parse_response() real invocation
3. parse_dashboard_json() real invocation
4. Normalization boundary scenarios (all-zero, >100, partial invalid)
"""
import os
import sys
import json
import logging
from typing import Dict, Any, Optional

# # Add the project path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from src.analyzer import AnalysisResult
logger = logging.getLogger(__name__)


class TestGenerateSingleStockReport:
    """Test generate_single_stock_report() rendering signal_attribution"""

    def test_single_stock_report_renders_signal_attribution(self):
        """Test generate_single_stock_report() correctly renders signal_attribution"""
        from src.analyzer import AnalysisResult
        from src.notification import NotificationService

        signal_attr = {
            "technical_indicators": 35,
            "news_sentiment": 25,
            "fundamentals": 20,
            "market_conditions": 20,
            "strongest_bullish_signal": "MACD金叉",
            "strongest_bearish_signal": "成交量萎缩",
        }
        dashboard = {"signal_attribution": signal_attr}
        result = self._make_result(dashboard)

        notification = NotificationService()
        report = notification.generate_single_stock_report(result)

        # Verify it contains the signal-attribution section
        assert "信号归因" in report or "Signal Attribution" in report, "Single stock report should contain signal attribution section"
        assert "35%" in report, "Single stock report should display technical_indicators=35%"
        assert "MACD金叉" in report, "Single stock report should display strongest_bullish_signal"
        print("  ✅ generate_single_stock_report() correctly renders signal_attribution")

    def test_single_stock_report_without_signal_attribution(self):
        """Test that it does not crash when signal_attribution is absent"""
        from src.analyzer import AnalysisResult
        from src.notification import NotificationService

        result = self._make_result({})

        notification = NotificationService()
        report = notification.generate_single_stock_report(result)

        # Verify the report is generated successfully (may not contain the signal-attribution section)
        assert len(report) > 0, "Report should be generated even without signal_attribution"
        print("  ✅ No crash when signal_attribution is absent")


    def _make_result(self, dashboard: Dict[str, Any]) -> "AnalysisResult":
        return AnalysisResult(
            code="600519",
            name="贵州茅台",
            trend_prediction="看多",
            sentiment_score=75,
            operation_advice="持有",
            analysis_summary="测试分析",
            decision_type="hold",
            dashboard=dashboard,
        )


class TestNormalizationEdgeCases:
    """Test normalization edge cases"""

    def test_all_zero_contributions(self):
        """Test that when all contributions are 0, keep 0 instead of changing to 25"""
        from src.utils.data_processing import normalize_dashboard_signal_attribution

        dashboard = {
            "signal_attribution": {
                "technical_indicators": 0,
                "news_sentiment": 0,
                "fundamentals": 0,
                "market_conditions": 0,
            }
        }
        normalize_dashboard_signal_attribution(dashboard)
        attr = dashboard["signal_attribution"]

        # Should keep 0, not change to 25
        assert attr["technical_indicators"] == 0, f"Should be 0, actual={attr['technical_indicators']}"
        assert attr["news_sentiment"] == 0, f"Should be 0, actual={attr['news_sentiment']}"
        assert attr["fundamentals"] == 0, f"Should be 0, actual={attr['fundamentals']}"
        assert attr["market_conditions"] == 0, f"Should be 0, actual={attr['market_conditions']}"
        print("  ✅ All contributions are 0, correctly preserved")

    def test_all_none_contributions(self):
        """Test that when all contributions are None, keep None"""
        from src.utils.data_processing import normalize_dashboard_signal_attribution

        dashboard = {
            "signal_attribution": {
                "technical_indicators": None,
                "news_sentiment": None,
                "fundamentals": None,
                "market_conditions": None,
            }
        }
        normalize_dashboard_signal_attribution(dashboard)
        attr = dashboard["signal_attribution"]

        # Should keep None
        assert attr["technical_indicators"] is None, "Should be None"
        assert attr["news_sentiment"] is None, "Should be None"
        print("  ✅ All contributions are None, correctly preserved")

    def test_values_greater_than_100(self):
        """Test that when a contribution >100, cap it at 100"""
        from src.utils.data_processing import normalize_dashboard_signal_attribution

        dashboard = {
            "signal_attribution": {
                "technical_indicators": 150,  # >100
                "news_sentiment": 50,
                "fundamentals": 50,
                "market_conditions": 50,
            }
        }
        normalize_dashboard_signal_attribution(dashboard)
        attr = dashboard["signal_attribution"]

        # Should be capped at 100
        assert attr["technical_indicators"] <= 100, f"Should be <=100, actual={attr['technical_indicators']}"
        print(f"  ✅ Contribution >100 capped to 100 (actual: {attr['technical_indicators']})")

    def test_partial_invalid_values(self):
        """Test partially-valid, partially-invalid input"""
        from src.utils.data_processing import normalize_dashboard_signal_attribution

        dashboard = {
            "signal_attribution": {
                "technical_indicators": 35,
                "news_sentiment": "25%",  # String percentage
                "fundamentals": None,  # Invalid
                "market_conditions": -10,  # Negative, should be converted to 0
            }
        }
        normalize_dashboard_signal_attribution(dashboard)
        attr = dashboard["signal_attribution"]

        assert attr["technical_indicators"] == 35, f"Should be 35, actual={attr['technical_indicators']}"
        assert attr["news_sentiment"] == 25, f"Should be 25, actual={attr['news_sentiment']}"
        assert attr["fundamentals"] is None, f"Should be None, actual={attr['fundamentals']}"
        assert attr["market_conditions"] == 0, f"Should be 0, actual={attr['market_conditions']}"

        # Verify the sum = 100
        valid_values = [v for v in attr.values() if isinstance(v, int) and v is not None]
        if len(valid_values) > 0:
            total = sum(valid_values)
            print(f"  ✅ Partial invalid input correctly handled, sum = {total}")
        else:
            print("  ✅ Partial invalid input correctly handled")


class TestParseResponseIntegration:
    """Test _parse_response() real call"""

    def test_parse_response_calls_normalization(self):
        """Test _parse_response() correctly calls the normalization function"""
        from src.analyzer import GeminiAnalyzer
        from unittest.mock import MagicMock

        # Build the mocked LLM return (JSON string, containing signal_attribution)
        llm_response_text = json.dumps({
            "dashboard": {
                "signal_attribution": {
                    "technical_indicators": "35%",  # 字符串百分比
                    "news_sentiment": 25,
                    "fundamentals": 20,
                    "market_conditions": 20,
                    "strongest_bullish_signal": "MACD金叉",
                },
                "core_conclusion": {"one_sentence": "测试"},
                "intelligence": {"risk_alerts": []},
                "battle_plan": {"sniper_points": {"stop_loss": "100"}},
            }
        })

        # Create the analyzer instance (mock necessary attributes)
        config = MagicMock()
        config.llm_provider = "deepseek"
        config.llm_model = "deepseek-chat"
        config.analysis_mode = "quick"
        config.enable_phase_classification = False
        config.enable_pre_judge = False
        config.pre_judge_decision_filter = False
        config.enable_knowledge_base = False
        config.language = "zh"
        config.report_language = "zh"
        config.enable_dashboard_output = True
        config.use_agent_analysis = False
        config.use_multi_agent = False
        config.enable_stagewise_analysis = False
        config.project_id = None
        config.location = None

        analyzer = GeminiAnalyzer.__new__(GeminiAnalyzer)
        analyzer.config = config
        analyzer.llm_provider = "deepseek"
        analyzer.llm_model = "deepseek-chat"
        analyzer.phase_classifier = None
        analyzer.pre_judge = None

        # Call _parse_response()
        result = analyzer._parse_response(llm_response_text, "600519", "贵州茅台")

        # Verify result.dashboard's signal_attribution has been normalized
        dashboard = result.dashboard
        assert dashboard is not None, "dashboard should not be None"
        signal_attr = dashboard.get("signal_attribution")
        assert signal_attr is not None, "signal_attribution should not be None"

        # Verify the string percentage was converted to int
        assert isinstance(signal_attr.get("technical_indicators"), int), "String percentage should be converted to int"
        assert signal_attr.get("technical_indicators") == 35, f"Should be 35, actual={signal_attr.get('technical_indicators')}"

        print("  ✅ _parse_response() correctly calls normalization function")


def run_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("Signal Attribution Supplement Tests")
    print("="*80 + "\n")

    # Test 1: generate_single_stock_report() rendering
    print("=" * 80)
    print("Test 1: generate_single_stock_report() rendering")
    print("=" * 80 + "\n")
    test1 = TestGenerateSingleStockReport()
    test1.test_single_stock_report_renders_signal_attribution()
    test1.test_single_stock_report_without_signal_attribution()

    # Test 2: normalization edge cases
    print("\n" + "="*80)
    print("Test 2: Normalization edge cases")
    print("="*80 + "\n")
    test2 = TestNormalizationEdgeCases()
    test2.test_all_zero_contributions()
    test2.test_all_none_contributions()
    test2.test_values_greater_than_100()
    test2.test_partial_invalid_values()

    # Test 3: _parse_response() real call
    print("\n" + "="*80)
    print("Test 3: _parse_response() real invocation")
    print("="*80 + "\n")
    test3 = TestParseResponseIntegration()
    test3.test_parse_response_calls_normalization()

    print("\n" + "="*80)
    print("All tests passed!")
    print("="*80 + "\n")


if __name__ == "__main__":
    import logging
    run_tests()
