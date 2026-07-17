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
    """Market review region configuration"""

    region: str  # "cn" | "hk" | "us" | "jp" | "kr" | "id"
    # Index code used to judge overall trend, cn uses Shanghai Composite 000001, us uses S&P SPX
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
        "Ashares Market Review",
        "stock market Quotes analysis",
        "Ashares market Hotspot plate",
    ],
    prompt_index_hint="Analyze the Shanghai Stock Exchange、Shenzhen Certificate、Trend characteristics of various indices such as GEM",
    has_market_stats=True,
    has_sector_rankings=True,
)

US_PROFILE = MarketProfile(
    region="us",
    mood_index_code="SPX",
    news_queries=[
        "US stocks Market",
        "US stock market",
        "S&P 500 NASDAQ",
    ],
    prompt_index_hint="Analyze S&P500、Nasdaq、Trend characteristics of the Dow and other indexes",
    has_market_stats=False,
    has_sector_rankings=False,
)

HK_PROFILE = MarketProfile(
    region="hk",
    mood_index_code="HSI",
    news_queries=[
        "Hong Kong stocks Market Review",
        "Hong Kong stock market",
        "Hang Seng Index Quotes",
    ],
    prompt_index_hint="Analyze the Hang Seng Index、Hang Seng Technology Index、Trend characteristics of various indices such as the State-owned Enterprise Index",
    has_market_stats=False,
    has_sector_rankings=False,
)

JP_PROFILE = MarketProfile(
    region="jp",
    mood_index_code="N225",
    news_queries=[
        "Japanese stock market Nikkei225",
        "Japan stock market Nikkei TOPIX",
        "Nikkei225 Topix Index Quotes",
    ],
    prompt_index_hint="Analyzing the Nikkei225、Trend characteristics of major Japanese indexes such as the Topix Index",
    has_market_stats=False,
    has_sector_rankings=False,
)

KR_PROFILE = MarketProfile(
    region="kr",
    mood_index_code="KS11",
    news_queries=[
        "Korean stock market KOSPI",
        "Korea stock market KOSPI KOSDAQ",
        "KOSPI KOSDAQ Quotes",
    ],
    prompt_index_hint="analysis KOSPI、KOSDAQ Trend characteristics of major Korean indexes such as",
    has_market_stats=False,
    has_sector_rankings=False,
)


ID_PROFILE = MarketProfile(
    region="id",
    mood_index_code="JKSE",
    news_queries=[
        "IHSG pasar saham Indonesia",
        "Indonesia stock market IDX JCI",
        "IHSG BEI analisis pasar hari ini",
    ],
    prompt_index_hint="Analyze the trend characteristics of main Indonesian indices such as the Jakarta Composite Index (IHSG/JKSE), LQ45, etc.",
    has_market_stats=False,
    has_sector_rankings=False,
)


ID_PROFILE = MarketProfile(
    region="id",
    mood_index_code="JKSE",
    news_queries=[
        "IHSG pasar saham Indonesia",
        "Indonesia stock market IDX JCI",
        "IHSG BEI analisis pasar hari ini",
    ],
    prompt_index_hint="分析雅加达综合指数（IHSG/JKSE）、LQ45 等印尼主要指数走势特点",
    has_market_stats=False,
    has_sector_rankings=False,
)


def get_profile(region: str) -> MarketProfile:
    """Return the corresponding MarketProfile based on the region"""
    if region == "us":
        return US_PROFILE
    if region == "hk":
        return HK_PROFILE
    if region == "jp":
        return JP_PROFILE
    if region == "kr":
        return KR_PROFILE
    if region == "id":
        return ID_PROFILE
    if region == "id":
        return ID_PROFILE
    return CN_PROFILE
