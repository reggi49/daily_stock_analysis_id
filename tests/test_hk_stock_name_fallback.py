# -*- coding: utf-8 -*-
"""
Regression tests for HK stock name fallback when stock_hk_spot_em fails.

Covers: data_provider/akshare_fetcher.py _get_hk_realtime_quote
"""

import sys
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from tests.litellm_stub import ensure_litellm_stub

ensure_litellm_stub()
try:
    import json_repair  # noqa: F401
except ImportError:
    if "json_repair" not in sys.modules:
        sys.modules["json_repair"] = MagicMock()

from data_provider.akshare_fetcher import AkshareFetcher


class _DummyCircuitBreaker:
    def __init__(self):
        self.failures = []
        self.successes = []

    def is_available(self, source: str) -> bool:
        return True

    def record_success(self, source: str) -> None:
        self.successes.append(source)

    def record_failure(self, source: str, error=None) -> None:
        self.failures.append((source, error))


def _make_spot_em_df():
    """Simulate stock_hk_spot_em() return value."""
    return pd.DataFrame([{
        'code': '00700',
        'Name': 'Tencent Holdings',
        'latest price': 370.0,
        'Increase or decrease': 1.5,
        'Changes': 5.5,
        'Volume': 10000,
        'Turnover': 3700000.0,
        'Quantity ratio': 1.2,
        'turnover rate': 0.3,
        'Amplitude': 2.0,
        'P/E ratio': 20.0,
        'price to book ratio': 3.5,
        'Total market capitalization': 3.5e12,
        'Circulation market value': 3.5e12,
        '52Weekly highest': 400.0,
        '52Weekly lowest': 280.0,
    }])


def _make_spot_df():
    """Simulate stock_hk_spot() return value (sina source)."""
    return pd.DataFrame([{
        'code': '00700',
        'Name': 'Tencent Holdings',
        'latest price': 368.0,
        'Changes': 3.5,
        'Increase or decrease': 0.96,
        'Buy': 367.8,
        'sell': 368.2,
        'Collected yesterday': 364.5,
        'Open today': 365.0,
        'highest': 370.0,
        'lowest': 364.0,
        'Volume': 9800,
        'Turnover': 3606400.0,
    }])


class TestHKRealtimeFallback(unittest.TestCase):
    """When stock_hk_spot_em fails it should fall back to stock_hk_spot."""

    def setUp(self):
        self.fetcher = AkshareFetcher()
        # Bypass rate limiting
        self.fetcher._enforce_rate_limit = lambda: None
        self.fetcher._set_random_user_agent = lambda: None

    @patch("data_provider.akshare_fetcher.get_realtime_circuit_breaker")
    def test_em_success_returns_quote_with_name(self, mock_cb):
        """When stock_hk_spot_em succeeds it returns the quote containing the name directly."""
        mock_cb.return_value = _DummyCircuitBreaker()
        ak_mock = MagicMock()
        ak_mock.stock_hk_spot_em.return_value = _make_spot_em_df()

        with patch.dict(sys.modules, {"akshare": ak_mock}):
            quote = self.fetcher._get_hk_realtime_quote("HK00700")

        self.assertIsNotNone(quote)
        self.assertEqual(quote.name, "Tencent Holdings")
        self.assertAlmostEqual(quote.price, 370.0)

    @patch("data_provider.akshare_fetcher.get_realtime_circuit_breaker")
    def test_em_failure_falls_back_to_spot(self, mock_cb):
        """When stock_hk_spot_em raises, it should fall back to stock_hk_spot and return the name."""
        mock_cb.return_value = _DummyCircuitBreaker()
        ak_mock = MagicMock()
        ak_mock.stock_hk_spot_em.side_effect = Exception("Interface exception：Data source is not available")
        ak_mock.stock_hk_spot.return_value = _make_spot_df()

        with patch.dict(sys.modules, {"akshare": ak_mock}):
            quote = self.fetcher._get_hk_realtime_quote("HK00700")

        self.assertIsNotNone(quote)
        self.assertEqual(quote.name, "Tencent Holdings")
        self.assertAlmostEqual(quote.price, 368.0)
        ak_mock.stock_hk_spot.assert_called_once()

    @patch("data_provider.akshare_fetcher.get_realtime_circuit_breaker")
    def test_both_fail_returns_none(self, mock_cb):
        """When both stock_hk_spot_em and stock_hk_spot fail, return None without raising."""
        mock_cb.return_value = _DummyCircuitBreaker()
        ak_mock = MagicMock()
        ak_mock.stock_hk_spot_em.side_effect = Exception("Oriental Fortune interface timeout")
        ak_mock.stock_hk_spot.side_effect = Exception("Sina interface timeout")

        with patch.dict(sys.modules, {"akshare": ak_mock}):
            quote = self.fetcher._get_hk_realtime_quote("HK00700")

        self.assertIsNone(quote)

    @patch("data_provider.akshare_fetcher.get_realtime_circuit_breaker")
    def test_em_returns_empty_df_falls_back_to_spot(self, mock_cb):
        """When stock_hk_spot_em returns an empty DataFrame it should fall back to stock_hk_spot."""
        mock_cb.return_value = _DummyCircuitBreaker()
        ak_mock = MagicMock()
        ak_mock.stock_hk_spot_em.return_value = pd.DataFrame(columns=['code', 'Name', 'latest price'])
        ak_mock.stock_hk_spot.return_value = _make_spot_df()

        with patch.dict(sys.modules, {"akshare": ak_mock}):
            quote = self.fetcher._get_hk_realtime_quote("HK00700")

        self.assertIsNotNone(quote)
        self.assertEqual(quote.name, "Tencent Holdings")

    @patch("data_provider.akshare_fetcher.get_realtime_circuit_breaker")
    def test_circuit_breaker_open_returns_none(self, mock_cb):
        """In a circuit-breaker state, return None directly."""
        cb = _DummyCircuitBreaker()
        cb.is_available = lambda source: False
        mock_cb.return_value = cb
        ak_mock = MagicMock()

        with patch.dict(sys.modules, {"akshare": ak_mock}):
            quote = self.fetcher._get_hk_realtime_quote("HK00700")

        self.assertIsNone(quote)
        ak_mock.stock_hk_spot_em.assert_not_called()


if __name__ == "__main__":
    unittest.main()
