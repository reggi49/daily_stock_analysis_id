# -*- coding: utf-8 -*-
"""Unit tests for report language helpers."""

import unittest

from src.report_language import (
    SUPPORTED_REPORT_LANGUAGES,
    get_bias_status_emoji,
    get_localized_stock_name,
    get_report_labels,
    get_sentiment_label,
    get_signal_level,
    infer_decision_type_from_advice,
    localize_operation_advice,
    localize_trend_prediction,
    localize_bias_status,
    normalize_report_language,
)


class ReportLanguageTestCase(unittest.TestCase):
    def test_get_signal_level_handles_compound_sell_advice(self) -> None:
        signal_text, emoji, signal_tag = get_signal_level("sell/wait and see", 60, "zh")

        self.assertEqual(signal_text, "sell")
        self.assertEqual(emoji, "🔴")
        self.assertEqual(signal_tag, "sell")

    def test_get_signal_level_handles_compound_buy_advice_in_english(self) -> None:
        signal_text, emoji, signal_tag = get_signal_level("Buy / Watch", 40, "en")

        self.assertEqual(signal_text, "Buy")
        self.assertEqual(emoji, "🟢")
        self.assertEqual(signal_tag, "buy")

    def test_get_signal_level_score_fallback_uses_canonical_scale(self) -> None:
        self.assertEqual(get_signal_level("", 28, "zh"), ("Reduce positions", "🟠", "reduce"))
        self.assertEqual(get_signal_level("", 38, "zh"), ("Reduce positions", "🟠", "reduce"))
        self.assertEqual(get_signal_level("", 42, "zh"), ("wait and see", "⚪", "watch"))
        self.assertEqual(get_signal_level("", 55, "zh"), ("wait and see", "⚪", "watch"))
        self.assertEqual(get_signal_level("", 60, "zh"), ("Buy", "🟢", "buy"))
        self.assertEqual(get_signal_level("", 66, "zh"), ("Buy", "🟢", "buy"))
        self.assertEqual(get_signal_level("", 72, "zh"), ("Buy", "🟢", "buy"))

    def test_get_localized_stock_name_replaces_placeholder_for_english(self) -> None:
        self.assertEqual(
            get_localized_stock_name("stocksAAPL", "AAPL", "en"),
            "Unnamed Stock",
        )

    def test_get_sentiment_label_preserves_higher_band_thresholds(self) -> None:
        self.assertEqual(get_sentiment_label(80, "en"), "Very Bullish")
        self.assertEqual(get_sentiment_label(60, "en"), "Bullish")
        self.assertEqual(get_sentiment_label(40, "zh"), "Neutral")
        self.assertEqual(get_sentiment_label(20, "zh"), "pessimistic")

    def test_localize_trend_prediction_preserves_fine_grain_zh_states(self) -> None:
        self.assertEqual(localize_trend_prediction("multi-head arrangement", "zh"), "multi-head arrangement")
        self.assertEqual(localize_trend_prediction("Weak short", "zh"), "Weak short")

    def test_localize_trend_prediction_still_translates_english_input_for_zh(self) -> None:
        self.assertEqual(localize_trend_prediction("bullish", "zh"), "long")
        self.assertEqual(localize_trend_prediction("very bearish", "zh"), "Strongly bearish")

    def test_bias_status_helpers_support_english_values(self) -> None:
        self.assertEqual(localize_bias_status("Safe", "en"), "Safe")
        self.assertEqual(localize_bias_status("alert", "en"), "Caution")
        self.assertEqual(get_bias_status_emoji("Safe"), "✅")
        self.assertEqual(get_bias_status_emoji("Caution"), "⚠️")

    def test_infer_decision_type_from_advice_matches_chinese_phrases(self) -> None:
        self.assertEqual(infer_decision_type_from_advice("Recommended to buy"), "buy")
        self.assertEqual(infer_decision_type_from_advice("Recommended to hold"), "hold")
        self.assertEqual(infer_decision_type_from_advice("Recommended to reduce positions"), "sell")
        self.assertEqual(infer_decision_type_from_advice("continue to hold"), "hold")
        self.assertEqual(infer_decision_type_from_advice("It is recommended to wash the dishes and observe"), "hold")
        self.assertEqual(infer_decision_type_from_advice("Washing dishes and observing", default=""), "hold")
        self.assertEqual(infer_decision_type_from_advice("observe", default=""), "hold")
        self.assertEqual(infer_decision_type_from_advice("Not recommended to buy"), "hold")
        self.assertEqual(
            infer_decision_type_from_advice("If it does not fall below the support level, continue to hold."),
            "hold",
        )
        self.assertEqual(
            infer_decision_type_from_advice("You can still hold it without breaking the support"),
            "hold",
        )


class KoreanReportLanguageTestCase(unittest.TestCase):
    def test_korean_is_supported(self) -> None:
        self.assertIn("ko", SUPPORTED_REPORT_LANGUAGES)

    def test_normalize_korean_aliases(self) -> None:
        self.assertEqual(normalize_report_language("ko"), "ko")
        self.assertEqual(normalize_report_language("korean"), "ko")
        self.assertEqual(normalize_report_language("ko-KR"), "ko")
        self.assertEqual(normalize_report_language("kr"), "ko")

    def test_unknown_language_falls_back_to_default(self) -> None:
        self.assertEqual(normalize_report_language("fr"), "zh")
        self.assertEqual(normalize_report_language(None), "zh")

    def test_korean_labels_cover_full_english_key_set(self) -> None:
        ko_labels = get_report_labels("ko")
        en_labels = get_report_labels("en")
        self.assertEqual(set(ko_labels.keys()), set(en_labels.keys()))
        self.assertEqual(ko_labels["dashboard_title"], "결정 대시보드")
        self.assertEqual(ko_labels["risk_alerts_label"], "리스크 경보")

    def test_korean_sentiment_label_bands(self) -> None:
        self.assertEqual(get_sentiment_label(80, "ko"), "매우 낙관")
        self.assertEqual(get_sentiment_label(40, "ko"), "중립")
        self.assertEqual(get_sentiment_label(0, "ko"), "매우 비관")

    def test_korean_operation_advice_and_trend(self) -> None:
        self.assertEqual(localize_operation_advice("Buy", "ko"), "매수")
        self.assertEqual(localize_operation_advice("strong sell", "ko"), "적극 매도")
        self.assertEqual(localize_trend_prediction("bullish", "ko"), "상승")

    def test_korean_localized_stock_name_placeholder(self) -> None:
        self.assertEqual(
            get_localized_stock_name("stocksAAPL", "AAPL", "ko"),
            "미확인 종목",
        )

    def test_existing_languages_unchanged(self) -> None:
        self.assertEqual(get_sentiment_label(80, "en"), "Very Bullish")
        self.assertEqual(get_sentiment_label(40, "zh"), "Neutral")

    def test_korean_advice_canonicalizes_to_decision_type(self) -> None:
        self.assertEqual(infer_decision_type_from_advice("매수"), "buy")
        self.assertEqual(infer_decision_type_from_advice("매도"), "sell")
        self.assertEqual(infer_decision_type_from_advice("보유"), "hold")
        self.assertEqual(infer_decision_type_from_advice("관망"), "hold")

    def test_korean_advice_resolves_signal_level(self) -> None:
        self.assertEqual(get_signal_level("매수", 72, "ko"), ("매수", "🟢", "buy"))
        self.assertEqual(get_signal_level("매도", 30, "ko"), ("매도", "🔴", "sell"))

    def test_korean_values_canonicalize_back_for_other_languages(self) -> None:
        self.assertEqual(localize_trend_prediction("상승", "en"), "Bullish")
        self.assertEqual(localize_operation_advice("적극 매도", "zh"), "Strong Sell")


if __name__ == "__main__":
    unittest.main()
