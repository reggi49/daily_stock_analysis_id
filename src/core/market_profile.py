# -*- coding: utf-8 -*-
"""
Market Review Region Profiles

Defines per-region metadata such as index codes, news search queries, and prompt
hints, allowing MarketAnalyzer to switch A-share / HK / US / JP / KR review
behaviour by region.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class MarketProfile:
    """Market review region profile configuration."""

    region: str  # "cn" | "hk" | "us" | "jp" | "kr"
    # Index code used to gauge overall trend: Shanghai Composite 000001 for cn, S&P 500 SPX for us
    mood_index_code: str
    # News search keywords
    news_queries: List[str]
    # Index commentary prompt hint
    prompt_index_hint: str
    # Whether market stats include advance/decline counts and limit up/down (A-shares yes, US no)
    has_market_stats: bool
    # Whether market stats include sector rankings (A-shares yes, US not yet)
    has_sector_rankings: bool


CN_PROFILE = MarketProfile(
    region="cn",
    mood_index_code="000001",
    news_queries=[
        "A股 大盘 复盘",
        "股市 行情 分析",
        "A股 市场 热点 板块",
    ],
    prompt_index_hint="分析上证、深证、创业板等各指数走势特点",
    has_market_stats=True,
    has_sector_rankings=True,
)

US_PROFILE = MarketProfile(
    region="us",
    mood_index_code="SPX",
    news_queries=[
        "美股 大盘",
        "US stock market",
        "S&P 500 NASDAQ",
    ],
    prompt_index_hint="分析标普500、纳斯达克、道指等各指数走势特点",
    has_market_stats=False,
    has_sector_rankings=False,
)

HK_PROFILE = MarketProfile(
    region="hk",
    mood_index_code="HSI",
    news_queries=[
        "港股 大盘 复盘",
        "Hong Kong stock market",
        "恒生指数 行情",
    ],
    prompt_index_hint="分析恒生指数、恒生科技指数、国企指数等各指数走势特点",
    has_market_stats=False,
    has_sector_rankings=False,
)

JP_PROFILE = MarketProfile(
    region="jp",
    mood_index_code="N225",
    news_queries=[
        "日本股市 日经225",
        "Japan stock market Nikkei TOPIX",
        "日经225 东证指数 行情",
    ],
    prompt_index_hint="分析日经225、东证指数等日本主要指数走势特点",
    has_market_stats=False,
    has_sector_rankings=False,
)

KR_PROFILE = MarketProfile(
    region="kr",
    mood_index_code="KS11",
    news_queries=[
        "韩国股市 KOSPI",
        "Korea stock market KOSPI KOSDAQ",
        "KOSPI KOSDAQ 行情",
    ],
    prompt_index_hint="分析 KOSPI、KOSDAQ 等韩国主要指数走势特点",
    has_market_stats=False,
    has_sector_rankings=False,
)


def get_profile(region: str) -> MarketProfile:
    """Return the MarketProfile for the given region."""
    if region == "us":
        return US_PROFILE
    if region == "hk":
        return HK_PROFILE
    if region == "jp":
        return JP_PROFILE
    if region == "kr":
        return KR_PROFILE
    return CN_PROFILE
