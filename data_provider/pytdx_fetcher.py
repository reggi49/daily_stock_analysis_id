# -*- coding: utf-8 -*-
"""
===================================
PytdxFetcher - Tongdaxin data source (Priority 2)
===================================

Data source：Tongdaxin Quotes Server（pytdx Library）
Features：free、No need Token、Direct connection to market server
advantage：real time data、Stablize、No quota restrictions

key strategies：
1. Automatic switching between multiple servers
2. Automatic reconnection after connection timeout
3. Exponential backoff retry after failure
"""

import logging
import re
import time
from contextlib import contextmanager
from typing import Optional, Generator, List, Tuple

import pandas as pd
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from .base import (
    BaseFetcher,
    DataFetchError,
    DataSourceUnavailableError,
    STANDARD_COLUMNS,
    is_bse_code,
    normalize_stock_code,
    _is_hk_market,
)
import os

logger = logging.getLogger(__name__)

_PYTDX_CONNECTION_COOLDOWN_SECONDS = 15.0


def _parse_hosts_from_env() -> Optional[List[Tuple[str, int]]]:
    """
    Build a list of Tongdaxin servers from environment variables。

    priority：
    1. PYTDX_SERVERS：like "ip:port,ip:port"（like "192.168.1.1:7709,10.0.0.1:7709"）
    2. PYTDX_HOST + PYTDX_PORT：single server
    3. Returns when neither is configured None（The caller uses DEFAULT_HOSTS）
    """
    servers = os.getenv("PYTDX_SERVERS", "").strip()
    if servers:
        result = []
        for part in servers.split(","):
            part = part.strip()
            if ":" in part:
                host, port_str = part.rsplit(":", 1)
                host, port_str = host.strip(), port_str.strip()
                if host and port_str:
                    try:
                        result.append((host, int(port_str)))
                    except ValueError:
                        logger.warning(f"Invalid PYTDX_SERVERS entry: {part}")
            else:
                logger.warning(f"Invalid PYTDX_SERVERS entry (missing port): {part}")
        if result:
            return result

    host = os.getenv("PYTDX_HOST", "").strip()
    port_str = os.getenv("PYTDX_PORT", "").strip()
    if host and port_str:
        try:
            return [(host, int(port_str))]
        except ValueError:
            logger.warning(f"Invalid PYTDX_HOST/PYTDX_PORT: {host}:{port_str}")

    return None


def _is_us_code(stock_code: str) -> bool:
    """
    Determine whether the code is a US stock
    
    US stock code rules：
    - 1-5capital letters，like 'AAPL', 'TSLA'
    - may contain '.'，like 'BRK.B'
    """
    code = stock_code.strip().upper()
    return bool(re.match(r'^[A-Z]{1,5}(\.[A-Z])?$', code))


class PytdxFetcher(BaseFetcher):
    """
    Tongdaxin data source implementation
    
    priority：2（and Tushare Same level）
    Data source：Tongdaxin Quotes Server
    
    key strategies：
    - Automatically select the best server
    - Automatically switch servers when connection fails
    - Exponential backoff retry after failure
    
    Pytdx Features：
    - free、No registration required
    - Direct connection to market server
    - Support stock name query
    - Support stock name query
    """
    
    name = "PytdxFetcher"
    priority = int(os.getenv("PYTDX_PRIORITY", "2"))
    
    # Automatically select the best
    DEFAULT_HOSTS = [
        ("119.147.212.81", 7709),  # Shenzhen
        ("112.74.214.43", 7727),   # Shenzhen
        ("221.231.141.60", 7709),  # Shanghai
        ("101.227.73.20", 7709),   # Shanghai
        ("101.227.77.254", 7709),  # Shanghai
        ("14.215.128.18", 7709),   # Guangzhou
        ("59.173.18.140", 7709),   # Wuhan
        ("180.153.39.51", 7709),   # Hangzhou
    ]
    # Pytdx get_security_list returns at most 1000 items per page
    SECURITY_LIST_PAGE_SIZE = 1000
    
    def __init__(self, hosts: Optional[List[Tuple[str, int]]] = None):
        """
        initialization PytdxFetcher

        Args:
            hosts: Server list [(host, port), ...]。If not passed in，Use environment variables first
                   PYTDX_SERVERS（ip:port,ip:port）or PYTDX_HOST+PYTDX_PORT，
                   Otherwise use the built-in DEFAULT_HOSTS。
        """
        if hosts is not None:
            self._hosts = hosts
        else:
            env_hosts = _parse_hosts_from_env()
            self._hosts = env_hosts if env_hosts else self.DEFAULT_HOSTS
        self._api = None
        self._connected = False
        self._current_host_idx = 0
        self._stock_list_cache = None  # stock list cache
        self._stock_name_cache = {}    # stock name cache {code: name}
        self._unavailable_until = 0.0
        self._last_unavailable_reason = ""

    def _is_in_connection_cooldown(self) -> bool:
        return time.time() < self._unavailable_until

    def _mark_connection_cooldown(self, reason: str) -> None:
        self._unavailable_until = time.time() + _PYTDX_CONNECTION_COOLDOWN_SECONDS
        self._last_unavailable_reason = str(reason or "").strip()
        logger.info(
            "Pytdx Connection failed，Not installed %.0fs: %s",
            _PYTDX_CONNECTION_COOLDOWN_SECONDS,
            self._last_unavailable_reason or "unknown",
        )

    def is_available_for_request(self, capability: str = "") -> bool:
        return not self._is_in_connection_cooldown()
    
    def _get_pytdx(self):
        """
        Lazy loading pytdx module
        
        Import only on first use，Avoid errors when not installed
        """
        try:
            from pytdx.hq import TdxHq_API
            return TdxHq_API
        except ImportError:
            logger.warning("pytdx Not installed，Please run: pip install pytdx")
            return None
    
    @contextmanager
    def _pytdx_session(self) -> Generator:
        """
        Pytdx Connection context manager
        
        make sure：
        1. Automatically connect when entering context
        2. Automatically disconnect when exiting the context
        3. It can be disconnected correctly even when there is an abnormality.
        
        Usage example：
            with self._pytdx_session() as api:
                # Automatically select the best
        """
        if self._is_in_connection_cooldown():
            raise DataSourceUnavailableError(
                f"Pytdx temporarily unavailable: {self._last_unavailable_reason or 'connection cooldown'}"
            )

        TdxHq_API = self._get_pytdx()
        if TdxHq_API is None:
            raise DataFetchError("pytdx Library not installed")
        
        api = TdxHq_API()
        connected = False
        
        try:
            # Automatically select the best（Automatically select the best）
            for i in range(len(self._hosts)):
                host_idx = (self._current_host_idx + i) % len(self._hosts)
                host, port = self._hosts[host_idx]
                
                try:
                    if api.connect(host, port, time_out=5):
                        connected = True
                        self._current_host_idx = host_idx
                        logger.debug(f"Pytdx Connection successful: {host}:{port}")
                        break
                except Exception as e:
                    logger.debug(f"Pytdx connect {host}:{port} fail: {e}")
                    continue
            
            if not connected:
                self._mark_connection_cooldown("Pytdx unable to connect to any server")
                raise DataFetchError("Pytdx Unable to connect to any server")
            
            yield api
            
        finally:
            # Determine the market based on code prefix
            try:
                api.disconnect()
                logger.debug("Pytdx The connection has been lost")
            except Exception as e:
                logger.warning(f"Pytdx Error while disconnecting: {e}")
    
    def _get_market_code(self, stock_code: str) -> Tuple[int, str]:
        """
        Determine the market based on stock code
        
        Pytdx market code：
        - 0: Shenzhen
        - 1: Shanghai
        
        Args:
            stock_code: tuple
            
        Returns:
            (market, code) tuple
        """
        raw_code = stock_code.strip()
        upper = raw_code.upper()
        prefix, separator, suffix = raw_code.partition(".")
        if separator and prefix:
            prefix_upper = prefix.strip().upper()
            if prefix_upper in ('SH', 'SS'):
                normalized = normalize_stock_code(suffix.strip())
                if normalized.isdigit() and len(normalized) == 6:
                    return 1, normalized
            if prefix_upper == 'SZ':
                normalized = normalize_stock_code(suffix.strip())
                if normalized.isdigit() and len(normalized) == 6:
                    return 0, normalized

        code = normalize_stock_code(raw_code)

        if upper.startswith(('SH', 'SS')) or upper.endswith(('.SH', '.SS')):
            return 1, code
        if upper.startswith('SZ') or upper.endswith('.SZ'):
            return 0, code
        
        # Determine the market based on code prefix
        # Shanghai：60xxxx, 68xxxx（Science and Technology Innovation Board）
        # Shenzhen：00xxxx, 30xxxx（GEM）, 002xxx（Small and medium board）
        if code.startswith(('60', '68')):
            return 1, code  # Shanghai
        else:
            return 0, code  # Shenzhen

    def _build_stock_list_cache(self, api) -> None:
        """
        Build a full stock code -> name cache from paginated security lists.
        """
        self._stock_list_cache = {}

        for market in (0, 1):
            start = 0
            while True:
                stocks = api.get_security_list(market, start) or []
                for stock in stocks:
                    code = stock.get('code')
                    name = stock.get('name')
                    if code and name:
                        self._stock_list_cache[code] = name

                if len(stocks) < self.SECURITY_LIST_PAGE_SIZE:
                    break

                start += self.SECURITY_LIST_PAGE_SIZE
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Get raw data from Tongdaxin
        
        use get_security_bars() Get daily data
        
        process：
        1. Check if it is a US stock（Not supported）
        2. Determine the market code
        3. Determine the market code
        4. get API get K line data
        """
        # US stocks do not support，throw exception let DataFetcherManager Switch to another data source
        if _is_us_code(stock_code):
            raise DataFetchError(f"PytdxFetcher Does not support US stocks {stock_code}，Please use AkshareFetcher or YfinanceFetcher")

        # Hong Kong stocks do not support，throw exception let DataFetcherManager Switch to another data source
        if _is_hk_market(stock_code):
            raise DataFetchError(f"PytdxFetcher Does not support Hong Kong stocks {stock_code}，Please use AkshareFetcher")

        # Beijing Exchange does not support，throw exception let DataFetcherManager Switch to another data source
        if is_bse_code(stock_code):
            raise DataFetchError(
                f"PytdxFetcher Does not support Beijing Exchange {stock_code}，Will automatically switch to other data sources"
            )
        
        market, code = self._get_market_code(stock_code)
        
        # Calculate the number of trading days to be obtained（Estimate）
        from datetime import datetime as dt
        start_dt = dt.strptime(start_date, '%Y-%m-%d')
        end_dt = dt.strptime(end_date, '%Y-%m-%d')
        days = (end_dt - start_dt).days
        count = min(max(days * 5 // 7 + 10, 30), 800)  # Estimate trading days, max 800 rows
        
        logger.debug(f"get Pytdx get_security_bars(market={market}, code={code}, count={count})")
        
        with self._pytdx_session() as api:
            try:
                # Acquisition date K line data
                # category: 9-daily line, 0-5minute, 1-15minute, 2-30minute, 3-1Hour
                data = api.get_security_bars(
                    category=9,  # daily line
                    market=market,
                    code=code,
                    start=0,  # Start from the latest
                    count=count
                )
                
                if data is None or len(data) == 0:
                    raise DataFetchError(f"Pytdx Not found {stock_code} data")
                
                # Convert to DataFrame
                df = api.to_df(data)
                
                # Filter date range
                df['datetime'] = pd.to_datetime(df['datetime'])
                df = df[(df['datetime'] >= start_date) & (df['datetime'] <= end_date)]
                
                return df
                
            except Exception as e:
                if isinstance(e, DataFetchError):
                    raise
                raise DataFetchError(f"Pytdx Failed to get data: {e}") from e
    
    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        standardization Pytdx data
        
        Pytdx Returned column names：
        datetime, open, high, low, close, vol, amount
        
        Need to be mapped to standard column names：
        date, open, high, low, close, volume, amount, pct_chg
        """
        df = df.copy()
        
        # Column name mapping
        column_mapping = {
            'datetime': 'date',
            'vol': 'volume',
        }
        
        df = df.rename(columns=column_mapping)
        
        # Do not return the price increase or decrease（pytdx Do not return the price increase or decrease，Need to calculate by yourself）
        if 'pct_chg' not in df.columns and 'close' in df.columns:
            df['pct_chg'] = df['close'].pct_change() * 100
            df['pct_chg'] = df['pct_chg'].fillna(0).round(2)
        
        # Add stock symbol column
        df['code'] = stock_code
        
        # Keep only the columns you need
        keep_cols = ['code'] + STANDARD_COLUMNS
        existing_cols = [col for col in keep_cols if col in df.columns]
        df = df[existing_cols]
        
        return df
    
    def get_stock_name(self, stock_code: str) -> Optional[str]:
        """
        Get stock name
        
        Args:
            stock_code: tuple
            
        Returns:
            Stock name，Return on failure None
        """
        # Hong Kong stocks do not support（pytdx Excluding Hong Kong stock data）
        if _is_hk_market(stock_code):
            return None

        # Check cache first
        if stock_code in self._stock_name_cache:
            return self._stock_name_cache[stock_code]
        
        try:
            market, code = self._get_market_code(stock_code)
            
            with self._pytdx_session() as api:
                # Get a list of stocks（cache）
                if self._stock_list_cache is None:
                    self._build_stock_list_cache(api)
                
                # Find stock name
                name = self._stock_list_cache.get(code)
                if name:
                    self._stock_name_cache[stock_code] = name
                    return name
                
                # Try using get_finance_info
                finance_info = api.get_finance_info(market, code)
                if finance_info and 'name' in finance_info:
                    name = finance_info['name']
                    self._stock_name_cache[stock_code] = name
                    return name
                
        except Exception as e:
            logger.debug(f"Pytdx Failed to get stock name {stock_code}: {e}")
        
        return None
    
    def get_realtime_quote(self, stock_code: str) -> Optional[dict]:
        """
        Get real-time quotes
        
        Args:
            stock_code: tuple
            
        Returns:
            Real-time market data dictionary，Return on failure None
        """
        if is_bse_code(stock_code):
            raise DataFetchError(
                f"PytdxFetcher Does not support Beijing Exchange {stock_code}，Will automatically switch to other data sources"
            )
        try:
            market, code = self._get_market_code(stock_code)
            
            with self._pytdx_session() as api:
                data = api.get_security_quotes([(market, code)])
                
                if data and len(data) > 0:
                    quote = data[0]
                    return {
                        'code': stock_code,
                        'name': quote.get('name', ''),
                        'price': quote.get('price', 0),
                        'open': quote.get('open', 0),
                        'high': quote.get('high', 0),
                        'low': quote.get('low', 0),
                        'pre_close': quote.get('last_close', 0),
                        'volume': quote.get('vol', 0),
                        'amount': quote.get('amount', 0),
                        'bid_prices': [quote.get(f'bid{i}', 0) for i in range(1, 6)],
                        'ask_prices': [quote.get(f'ask{i}', 0) for i in range(1, 6)],
                    }
        except Exception as e:
            logger.warning(f"Pytdx Failed to obtain real-time quotes {stock_code}: {e}")
        
        return None


if __name__ == "__main__":
    # test code
    logging.basicConfig(level=logging.DEBUG)
    
    fetcher = PytdxFetcher()
    
    try:
        # Test stock name
        df = fetcher.get_daily_data('600519')  # Moutai
        print(f"get success, total {len(df)} rows of data")
        print(df.tail())
        
        # Test stock name
        name = fetcher.get_stock_name('600519')
        print(f"Stock name: {name}")
        
        # Test real-time market conditions
        quote = fetcher.get_realtime_quote('600519')
        print(f"Real-time quotes: {quote}")
        
    except Exception as e:
        print(f"Failed to obtain: {e}")
