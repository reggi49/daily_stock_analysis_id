# -*- coding: utf-8 -*-
"""Regression tests for Indonesian suffix-only market support."""

from data_provider.base import normalize_stock_code
from data_provider.yfinance_fetcher import YfinanceFetcher
from src.core.trading_calendar import get_market_for_stock
from src.services.stock_code_utils import is_code_like, normalize_code

def test_normalize_and_detect_id_suffix_codes() -> None:
    assert normalize_stock_code("bbca.jk") == "BBCA.JK"
    assert get_market_for_stock("BBCA.JK") == "id"
    assert is_code_like("BBCA.JK") is True
    assert normalize_code("BBCA.JK") == "BBCA.JK"

def test_yfinance_keeps_id_suffix_codes_and_indices() -> None:
    fetcher = YfinanceFetcher()
    assert fetcher._convert_stock_code("BBCA.JK") == "BBCA.JK"

    captured = []
    def fake_fetch(_yf, yf_code, name, return_code):
        captured.append((yf_code, name, return_code))
        return {"code": return_code, "name": name, "current": 1.0}

    fetcher._fetch_yf_ticker_data = fake_fetch
    id_indices = fetcher.get_main_indices("id") or []
    assert {item["code"] for item in id_indices} == {"JKSE", "LQ45"}
    assert ("^JKSE", "IDX Composite", "JKSE") in captured
    assert ("^JKLQ45", "LQ45", "LQ45") in captured
