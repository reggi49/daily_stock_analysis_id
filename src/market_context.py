# -*- coding: utf-8 -*-
"""
Market context detection for LLM prompts.

Detects the market (A-shares, HK, US) from a stock code and returns
market-specific role descriptions so prompts are not hardcoded to a
single market.

Fixes: https://github.com/ZhuLinsen/daily_stock_analysis/issues/644
"""

import re
from typing import Optional

from src.services.market_symbol_utils import get_suffix_market


def detect_market(stock_code: Optional[str]) -> str:
    """Detect market from stock code.

    Returns:
        One of 'cn', 'hk', 'us', or 'cn' as fallback.
    """
    if not stock_code:
        return "cn"

    code = stock_code.strip().upper()

    # HK stocks: HK00700, 00700.HK, or 5-digit pure numbers
    if code.startswith("HK") or code.endswith(".HK"):
        return "hk"
    lower = code.lower()
    if lower.endswith(".hk"):
        return "hk"
    # 5-digit pure numbers are HK (A-shares are 6-digit)
    if code.isdigit() and len(code) == 5:
        return "hk"

    # Suffix-only Yahoo symbols for JP/KR/TW. Bare Korean/Taiwan numeric
    # codes keep existing fallback semantics to avoid cross-market collisions.
    suffix_market = get_suffix_market(code)
    if suffix_market:
        return suffix_market

    # US stocks: 1-5 uppercase letters (AAPL, TSLA, GOOGL)
    # Also handles suffixed forms like BRK.B
    if re.match(r'^[A-Z]{1,5}(\.[A-Z]{1,2})?$', code):
        return "us"

    # Default: A-shares (6-digit numbers like 600519, 000001)
    return "cn"


# -- Market-specific role descriptions --

_MARKET_ROLES = {
    "cn": {
        "zh": " A Korean stocks",
        "en": "China A-shares",
    },
    "hk": {
        "zh": "Korean stocks",
        "en": "Hong Kong stock",
    },
    "us": {
        "zh": "Korean stocks",
        "en": "US stock",
    },
    "jp": {
        "zh": "Taiwan stocks",
        "en": "Japan stock",
    },
    "kr": {
        "zh": "Korean stocks",
        "en": "Korea stock",
    },
    "tw": {
        "zh": "Taiwan stocks",
        "en": "Taiwan stock",
    },
}

_MARKET_GUIDELINES = {
    "cn": {
        "zh": (
            "- The object of this analysis is **A Korean stocks**（Stocks listed on China's Shanghai and Shenzhen exchanges）。\n"
            "- Please pay attention A Stock-specific price limit mechanism（±10%/±20%/±30%）、T+1 Trading system and related policy factors。"
        ),
        "en": (
            "- This analysis covers a **China A-share** (listed on Shanghai/Shenzhen exchanges).\n"
            "- Consider A-share-specific rules: daily price limits (±10%/±20%/±30%), T+1 settlement, and PRC policy factors."
        ),
    },
    "hk": {
        "zh": (
            "- The object of this analysis is **Korean stocks**（Stocks listed on the Hong Kong Stock Exchange）。\n"
            "- There is no price limit for Hong Kong stocks，support T+0 trade，Need to pay attention to the Hong Kong dollar exchange rate、North-South Fund Flows and Special Rules of the Stock Exchange。"
        ),
        "en": (
            "- This analysis covers a **Hong Kong stock** (listed on HKEX).\n"
            "- HK stocks have no daily price limits, allow T+0 trading. Consider HKD FX, Southbound/Northbound flows, and HKEX-specific rules."
        ),
    },
    "us": {
        "zh": (
            "- The object of this analysis is **Korean stocks**（U.S. exchange-listed stocks）。\n"
            "- There is no price limit for U.S. stocks（But there is a fuse mechanism），support T+0 Trading and Pre-Market and Post-Market Trading，Pay attention to the US dollar exchange rate、Fed policy and SEC Regulatory developments。"
        ),
        "en": (
            "- This analysis covers a **US stock** (listed on NYSE/NASDAQ).\n"
            "- US stocks have no daily price limits (but have circuit breakers), allow T+0 and pre/after-market trading. Consider USD FX, Fed policy, and SEC regulations."
        ),
    },
    "jp": {
        "zh": (
            "- The object of this analysis is **Taiwan stocks**（Japan Exchange Listed Stocks，Yahoo Finance suffix like `.T`）。\n"
            "- Please analyze according to the Japanese market context，Pay attention to the Japanese yen exchange rate、Bank of Japan policy、Corporate governance and industry cycles；Don't apply A Stock price limit、Northbound funds、Dragon and Tiger List、Margin and securities lending, etc. A Stock exclusive concept。"
        ),
        "en": (
            "- This analysis covers a **Japan stock** (Yahoo Finance suffix such as `.T`).\n"
            "- Use Japan-market context: JPY FX, BOJ policy, corporate governance, and sector cycles; do not apply China A-share concepts such as daily price-limit boards, Northbound flows, Dragon Tiger lists, or margin-financing narratives."
        ),
    },
    "kr": {
        "zh": (
            "- The object of this analysis is **Korean stocks**（Korea Exchange/KOSDAQ listed stocks，suffix `.KS` / `.KQ` suffix）。\n"
            "- Please analyze according to the Korean market context，Pay attention to the Korean won exchange rate、Bank of Korea policy、semiconductor/Internet industry cycle and Korean trading system；Don't apply A Stock price limit、Northbound funds、Dragon and Tiger List、Margin and securities lending, etc. A Stock exclusive concept。"
        ),
        "en": (
            "- This analysis covers a **Korea stock** (KOSPI/KOSDAQ suffix `.KS` / `.KQ`).\n"
            "- Use Korea-market context: KRW FX, Bank of Korea policy, semiconductor/internet cycles, and local trading rules; do not apply China A-share concepts such as daily price-limit boards, Northbound flows, Dragon Tiger lists, or margin-financing narratives."
        ),
    },
    "tw": {
        "zh": (
            "- The object of this analysis is **Taiwan stocks**（Listed on Taiwan Stock Exchange `.TW`，Or over the counter at Taiwan Counter Buying Center `.TWO`）。\n"
            "- Please analyze according to Taiwan market context，Follow NT$（TWD）exchange rate、Taiwan central bank policy、semiconductor/Electronic OEM industry chain、"
            "Three major legal persons（foreign investment／Put a letter／proprietor）Trading exceeds、Margin lending and hedging，as well as TWSE/TPEx ±10% price limit system；"
            "Don't apply A Exclusive northbound funds、Concepts such as Dragon and Tiger List（The legal person structure and capital flow caliber of Taiwan stocks are related to A stocks are different）。"
        ),
        "en": (
            "- This analysis covers a **Taiwan stock** (TWSE-listed `.TW`, or TPEx/OTC `.TWO`).\n"
            "- Use Taiwan-market context: TWD FX, Central Bank of the ROC policy, the semiconductor/"
            "electronics-foundry supply chain, the three institutional investor groups (foreign / "
            "investment-trust / dealer), margin trading and day trading, and the TWSE/TPEx ±10% daily "
            "price limit; do not apply China A-share-specific concepts such as Northbound flows or Dragon Tiger lists."
        ),
    },
}


def get_market_role(stock_code: Optional[str], lang: str = "zh") -> str:
    """Return market-specific role description for LLM prompt.

    Args:
        stock_code: The stock code being analyzed.
        lang: 'zh' or 'en'.

    Returns:
        Role string like 'A Korean stocks' or 'US stock investment analysis'.
    """
    market = detect_market(stock_code)
    lang_key = "en" if lang in ("en", "ko") else "zh"
    return _MARKET_ROLES.get(market, _MARKET_ROLES["cn"])[lang_key]


def get_market_guidelines(stock_code: Optional[str], lang: str = "zh") -> str:
    """Return market-specific analysis guidelines for LLM prompt.

    Args:
        stock_code: The stock code being analyzed.
        lang: 'zh' or 'en'.

    Returns:
        Multi-line string with market-specific guidelines.
    """
    market = detect_market(stock_code)
    lang_key = "en" if lang in ("en", "ko") else "zh"
    return _MARKET_GUIDELINES.get(market, _MARKET_GUIDELINES["cn"])[lang_key]
