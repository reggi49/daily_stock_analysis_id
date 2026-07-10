# -*- coding: utf-8 -*-
"""
===================================
Automatic failover - Anti-ban flow control strategy
===================================

Anti-ban flow control strategy，Data source priority：
1. Data source priority
2. Automatic failover
3. Anti-ban flow control strategy

Data source priority（Configured）：
【Configured TUSHARE_TOKEN hour】
1. TushareFetcher (Priority 0) - 🔥 highest priority（Dynamic promotion）
2. EfinanceFetcher (Priority 0) - Same priority
3. AkshareFetcher (Priority 1) - from akshare Library
4. PytdxFetcher (Priority 2) - from pytdx Library（Tong Da Xin）
5. BaostockFetcher (Priority 3) - from baostock Library
6. YfinanceFetcher (Priority 4) - from yfinance Library

【Not configured TUSHARE_TOKEN hour】
1. EfinanceFetcher (Priority 0) - highest priority，from efinance Library
2. AkshareFetcher (Priority 1) - from akshare Library
3. PytdxFetcher (Priority 2) - from pytdx Library（Tong Da Xin）
4. TushareFetcher (Priority 2) - from tushare Library（Not available）
5. BaostockFetcher (Priority 3) - from baostock Library
6. YfinanceFetcher (Priority 4) - from yfinance Library
7. LongbridgeFetcher (Priority 5) - long bridge OpenAPI（US stocks/Hong Kong stocks are in trouble）

hint：The smaller the priority number, the higher the priority.，Arranged in initialization order with the same priority
"""

from .base import BaseFetcher, DataFetcherManager
from .efinance_fetcher import EfinanceFetcher
from .tencent_fetcher import TencentFetcher
from .akshare_fetcher import AkshareFetcher, is_hk_stock_code
from .tushare_fetcher import TushareFetcher
from .pytdx_fetcher import PytdxFetcher
from .baostock_fetcher import BaostockFetcher
from .yfinance_fetcher import YfinanceFetcher
from .longbridge_fetcher import LongbridgeFetcher
from .finnhub_fetcher import FinnhubFetcher
from .alphavantage_fetcher import AlphaVantageFetcher
from .us_index_mapping import is_us_index_code, is_us_stock_code, get_us_index_yf_symbol, US_INDEX_MAPPING

__all__ = [
    'BaseFetcher',
    'DataFetcherManager',
    'EfinanceFetcher',
    'TencentFetcher',
    'AkshareFetcher',
    'TushareFetcher',
    'PytdxFetcher',
    'BaostockFetcher',
    'YfinanceFetcher',
    'LongbridgeFetcher',
    'FinnhubFetcher',
    'AlphaVantageFetcher',
    'is_us_index_code',
    'is_us_stock_code',
    'is_hk_stock_code',
    'get_us_index_yf_symbol',
    'US_INDEX_MAPPING',
]
