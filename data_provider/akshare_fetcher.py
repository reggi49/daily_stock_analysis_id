# -*- coding: utf-8 -*-
"""
===================================
AkshareFetcher - master data source (Priority 1)
===================================

Data source:
1. EastMoney crawler (via akshare Library) - Default data source
2. Sina Finance - Alternative data source
3. Tencent Finance - Alternative data source

Features: free, no token needed, comprehensive data
Risk: The crawler mechanism is easily blocked by anti-crawling

Anti-ban strategy:
1. Sleep randomly 2-5 seconds before each request
2. Random rotation of User-Agent
3. Use tenacity for exponential backoff retries
4. Fuse mechanism: Automatically cool down after consecutive failures

Augmented data:
- Real-time quotes: volume ratio, turnover rate, P/E ratio, price limit, total market cap, circulating market value
- Chip distribution: profit ratio, average cost, chip concentration
"""

import logging
import multiprocessing
import os
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from src.patches.eastmoney_patch import eastmoney_patch
from src.config import get_config
from .base import BaseFetcher, DataFetchError, RateLimitError, STANDARD_COLUMNS, is_bse_code, is_st_stock, is_kc_cy_stock, normalize_stock_code
from .realtime_types import (
    UnifiedRealtimeQuote, ChipDistribution, RealtimeSource,
    get_realtime_circuit_breaker, get_chip_circuit_breaker,
    safe_float, safe_int  # Use unified type conversion functions
)
from .us_index_mapping import is_us_index_code, is_us_stock_code


# Alias for random rotation RealtimeQuote
RealtimeQuote = UnifiedRealtimeQuote


logger = logging.getLogger(__name__)

SINA_REALTIME_ENDPOINT = "hq.sinajs.cn/list"
TENCENT_REALTIME_ENDPOINT = "qt.gtimg.cn/q"
_AKSHARE_HISTORY_CALL_TIMEOUT = 30.0
_AKSHARE_TIMEOUT_PROCESS_JOIN_GRACE = 1.0
_AKSHARE_TIMEOUT_PROCESS_START_METHOD = "spawn"


# User-Agent for random rotation, cache real-time market data
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]


# Cache real-time market data (avoid duplicate requests)
# TTL set to 20 minutes (1200 seconds):
# - Batch analysis scenario: generally 30 stocks completed within 5 minutes, 20 minutes is enough
# - Real-time requirements: stock analysis does not require second-level real-time data, 20 minutes delay is acceptable
# - Anti-ban: reduce API call frequency
_realtime_cache: Dict[str, Any] = {
    'data': None,
    'timestamp': 0,
    'ttl': 1200  # 20-minute cache TTL
}

# ETF real-time quotation cache
_etf_realtime_cache: Dict[str, Any] = {
    'data': None,
    'timestamp': 0,
    'ttl': 1200  # 20-minute cache TTL
}


def _is_etf_code(stock_code: str) -> bool:
    """
    Determine whether the code is an ETF fund code.
    
    ETF code ranges:
    - Shanghai Stock Exchange ETF: 51xxxx, 52xxxx, 56xxxx, 58xxxx
    - Shenzhen Stock Exchange ETF: 15xxxx, 16xxxx, 18xxxx
    
    Args:
        stock_code: stock/fund code
        
    Returns:
        True if it is an ETF code, False indicates a common stock code
    """
    etf_prefixes = ('51', '52', '56', '58', '15', '16', '18')
    code = stock_code.strip().split('.')[0]
    return code.startswith(etf_prefixes) and len(code) == 6


def _is_hk_code(stock_code: str) -> bool:
    """
    Determine whether the code is a Hong Kong stock.

    Hong Kong stock code rules:
    - 5-digit code, like '00700' (Tencent Holdings)
    - Some Hong Kong stock codes may have prefixes, like 'hk00700', 'hk1810'

    Args:
        stock_code: Stock code

    Returns:
        True indicates a Hong Kong stock code, False means it is not a Hong Kong stock code
    """
    # Remove possible 'hk' prefix and check if it is a pure number
    code = stock_code.strip().lower()
    if code.endswith('.hk'):
        numeric_part = code[:-3]
        return numeric_part.isdigit() and 1 <= len(numeric_part) <= 5
    if code.startswith('hk'):
        # With hk prefix, it must be Hong Kong stocks; the prefix removed should be pure numbers (1-5 digits)
        numeric_part = code[2:]
        return numeric_part.isdigit() and 1 <= len(numeric_part) <= 5
    # Without prefix, only pure 5-digit numbers are considered Hong Kong stocks (avoid misjudging A-share codes)
    return code.isdigit() and len(code) == 5


def _normalize_tencent_volume(fields: List[str]) -> Optional[int]:
    """
    Normalize Tencent real-time market trading volume into shares.

    Tencent returns content pair fields 6; the public description and actual return are not fully consistent.
    Prioritize turnover rate, price, and circulating market capitalization cross-check; select the closer one
    between the original value and the old "hand-to-share" conversion. If cross-checking is not possible,
    fall back to the "hand-to-share" logic to avoid the traditional Tencent return content returning
    the original trading volume divided by 100.
    """
    if len(fields) <= 6 or not fields[6]:
        return None

    raw_volume = safe_int(fields[6])
    if raw_volume is None:
        return None

    price = safe_float(fields[3]) if len(fields) > 3 else None
    turnover_rate = safe_float(fields[38]) if len(fields) > 38 else None
    circ_mv_yi = safe_float(fields[44]) if len(fields) > 44 and fields[44] else None
    circ_mv = circ_mv_yi * 100000000 if circ_mv_yi is not None else None

    if price and price > 0 and turnover_rate and turnover_rate > 0 and circ_mv and circ_mv > 0:
        expected_volume = (circ_mv / price) * (turnover_rate / 100)
        if expected_volume > 0:
            raw_delta = abs(raw_volume - expected_volume)
            hand_to_share_volume = raw_volume * 100
            hand_delta = abs(hand_to_share_volume - expected_volume)
            return raw_volume if raw_delta <= hand_delta else hand_to_share_volume

    return raw_volume * 100


def _parse_tencent_amount(fields: List[str]) -> Optional[float]:
    """
    Parse Tencent's real-time market turnover, the unit is yuan.

    Observed return content, field 35 contains the more precise "price/volume/turnover"
    triplet. Field 37 is the old "ten thousand yuan" caliber pocket field.
    """
    if len(fields) > 35 and fields[35]:
        parts = fields[35].split("/")
        if len(parts) >= 3:
            precise_amount = safe_float(parts[2])
            if precise_amount is not None:
                return precise_amount

    amount_wan = safe_float(fields[37]) if len(fields) > 37 and fields[37] else None
    return amount_wan * 10000 if amount_wan is not None else None


def is_hk_stock_code(stock_code: str) -> bool:
    """
    Public API: determine if a stock code is a Hong Kong stock.

    Delegates to _is_hk_code for internal compatibility.

    Args:
        stock_code: Stock code (e.g. '00700', 'hk00700')

    Returns:
        True if HK stock, False otherwise
    """
    return _is_hk_code(stock_code)


def _is_us_code(stock_code: str) -> bool:
    """
    Determine whether the code is a US stock (excludes U.S. stock indexes).

    Delegates to us_index_mapping module's is_us_stock_code().

    Args:
        stock_code: Stock code

    Returns:
        True indicates a U.S. stock code, False indicates it is not a US stock code

    Examples:
        >>> _is_us_code('AAPL')
        True
        >>> _is_us_code('TSLA')
        True
        >>> _is_us_code('SPX')
        False
        >>> _is_us_code('600519')
        False
    """
    return is_us_stock_code(stock_code)


def _to_sina_tx_symbol(stock_code: str) -> str:
    """Convert 6-digit A-share code to sh/sz/bj prefixed symbol for Sina/Tencent APIs."""
    base = (stock_code.strip().split(".")[0] if "." in stock_code else stock_code).strip()
    if is_bse_code(base):
        return f"bj{base}"
    # Shanghai: 60xxxx, 5xxxx (ETF), 90xxxx (B-shares)
    if base.startswith(("6", "5", "90")):
        return f"sh{base}"
    return f"sz{base}"


def _classify_realtime_http_error(exc: Exception) -> Tuple[str, str]:
    """
    Classify Sina/Tencent realtime quote failures into stable categories.
    """
    detail = str(exc).strip() or type(exc).__name__
    lowered = detail.lower()

    remote_disconnect_keywords = (
        "remotedisconnected",
        "remote end closed connection without response",
        "connection aborted",
        "connection broken",
        "protocolerror",
        "chunkedencodingerror",
    )
    timeout_keywords = (
        "timeout",
        "timed out",
        "readtimeout",
        "connecttimeout",
    )
    rate_limit_keywords = (
        "banned",
        "blocked",
        "frequency",
        "rate limit",
        "too many requests",
        "429",
        "limit",
        "forbidden",
        "403",
    )

    if any(keyword in lowered for keyword in remote_disconnect_keywords):
        return "remote_disconnect", detail
    if isinstance(exc, (TimeoutError, requests.exceptions.Timeout)) or any(
        keyword in lowered for keyword in timeout_keywords
    ):
        return "timeout", detail
    if any(keyword in lowered for keyword in rate_limit_keywords):
        return "rate_limit_or_anti_bot", detail
    if isinstance(exc, requests.exceptions.RequestException):
        return "request_error", detail
    return "unknown_request_error", detail


def _build_realtime_failure_message(
    source_name: str,
    endpoint: str,
    stock_code: str,
    symbol: str,
    category: str,
    detail: str,
    elapsed: float,
    error_type: str,
) -> str:
    return (
        f"{source_name} Real-time market interface failed: endpoint={endpoint}, stock_code={stock_code}, "
        f"symbol={symbol}, category={category}, error_type={error_type}, "
        f"elapsed={elapsed:.2f}s, detail={detail}"
    )


def _akshare_call_with_timeout(
    func,
    *args,
    timeout: Optional[float] = None,
    call_name: str = "akshare",
    **kwargs,
):
    """Run an akshare call with a bounded wait time."""
    wait_seconds = _AKSHARE_HISTORY_CALL_TIMEOUT if timeout is None else float(timeout)

    multiprocessing.freeze_support()
    ctx = multiprocessing.get_context(_AKSHARE_TIMEOUT_PROCESS_START_METHOD)
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    process = ctx.Process(
        target=_akshare_timeout_worker,
        args=(child_conn, func, args, kwargs),
        name=f"akshare-{call_name}",
        daemon=True,
    )

    process.start()
    child_conn.close()

    try:
        if not parent_conn.poll(wait_seconds):
            _terminate_akshare_process(process)
            raise TimeoutError(f"{call_name} call more than {wait_seconds:g}s，gave up waiting")

        try:
            ok, value = parent_conn.recv()
        except EOFError as exc:
            raise RuntimeError(f"{call_name} The calling process did not return a result") from exc
    finally:
        parent_conn.close()
        process.join(_AKSHARE_TIMEOUT_PROCESS_JOIN_GRACE)
        _terminate_akshare_process(process)

    if ok:
        return value
    raise value


def _akshare_timeout_worker(conn, func, args, kwargs) -> None:
    try:
        conn.send((True, func(*args, **kwargs)))
    except BaseException as exc:
        try:
            conn.send((False, exc))
        except BaseException:
            try:
                conn.send((False, RuntimeError(f"{type(exc).__name__}: {exc}")))
            except BaseException:
                pass
    finally:
        conn.close()


def _terminate_akshare_process(process) -> None:
    if process.is_alive():
        process.terminate()
        process.join(_AKSHARE_TIMEOUT_PROCESS_JOIN_GRACE)
    if process.is_alive():
        process.kill()
        process.join(_AKSHARE_TIMEOUT_PROCESS_JOIN_GRACE)


class AkshareFetcher(BaseFetcher):
    """
    Akshare Data source implementation
    
    priority：1（Highest）
    Data source：key strategies
    
    key strategies：
    - Sleep randomly before each request 2.0-5.0 Second
    - random User-Agent rotation
    - Exponential backoff retry after failure（most3Second-rate）
    """
    
    name = "AkshareFetcher"
    priority = int(os.getenv("AKSHARE_PRIORITY", "1"))
    
    def __init__(self, sleep_min: float = 2.0, sleep_max: float = 5.0):
        """
        initialization AkshareFetcher
        
        Args:
            sleep_min: Minimum sleep time（Second）
            sleep_max: Maximum sleep time（Second）
        """
        self.sleep_min = sleep_min
        self.sleep_max = sleep_max
        self._last_request_time: Optional[float] = None
        self._history_call_timeout = _AKSHARE_HISTORY_CALL_TIMEOUT
        # The patching operation will be performed only after Dongcai patch is enabled.
        if get_config().enable_eastmoney_patch:
            eastmoney_patch()
    
    def _set_random_user_agent(self) -> None:
        """
        Set random User-Agent

        Modifies the requests Session headers to achieve this.
        This is one of the key anti-crawling strategies.
        """
        try:
            import akshare as ak
            # akshare uses requests internally; we influence it through environment variables or direct settings
            # Actually akshare uses the session here, with fake_useragent as a supplement
            random_ua = random.choice(USER_AGENTS)
            logger.debug(f"set up User-Agent: {random_ua[:50]}...")
        except Exception as e:
            logger.debug(f"set up User-Agent failed: {e}")
    
    def _enforce_rate_limit(self) -> None:
        """
        Enforce rate limits.

        Strategy:
        1. Check the time interval since the last request
        2. If the interval is insufficient, supplement sleep time
        3. Then perform random jitter sleep
        """
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            min_interval = self.sleep_min
            if elapsed < min_interval:
                additional_sleep = min_interval - elapsed
                logger.debug(f"Supplementary sleep {additional_sleep:.2f} seconds")
                time.sleep(additional_sleep)
        
        # Perform random jitter sleep
        self.random_sleep(self.sleep_min, self.sleep_max)
        self._last_request_time = time.time()
    
    @retry(
        stop=stop_after_attempt(3),  # Max 3 retries
        wait=wait_exponential(multiplier=1, min=2, max=30),  # Exponential backoff: 2, 4, 8... max 30 seconds
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch data from Akshare with automatic type-based routing.

        Automatic type-based routing API:
        - US stocks: not supported, exception thrown by YfinanceFetcher for consistent restoration price (Issue #311)
        - Hong Kong stocks: use ak.stock_hk_hist()
        - ETF funds: use ak.fund_etf_hist_em()
        - Regular A-share: use ak.stock_zh_a_hist()

        Process:
        1. Determine code type (US stocks/Hong Kong stocks/ETF/A-share)
        2. Set random User-Agent
        3. Enforce rate limiting (random sleep)
        4. Call the corresponding akshare API
        5. Process returned data
        """
        # Choose different fetch methods based on code type
        if _is_us_code(stock_code):
            # US stocks: akshare's stock_us_daily has known issues with restoration (See Issue #311)
            # Delegated to YfinanceFetcher for consistent restoration price
            raise DataFetchError(
                f"AkshareFetcher does not support US stocks {stock_code}, please use YfinanceFetcher for correct restoration price"
            )
        elif _is_hk_code(stock_code):
            return self._fetch_hk_data(stock_code, start_date, end_date)
        elif _is_etf_code(stock_code):
            return self._fetch_etf_data(stock_code, start_date, end_date)
        else:
            return self._fetch_stock_data(stock_code, start_date, end_date)
    
    def _fetch_stock_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch regular A-share historical data.

        Strategy:
        1. First try EastMoney interface (ak.stock_zh_a_hist)
        2. On failure, try Sina Finance interface (ak.stock_zh_a_daily)
        3. Finally try Tencent Finance interface (ak.stock_zh_a_hist_tx)
        """
        # Try list
        methods = [
            (self._fetch_stock_data_em, "EastMoney"),
            (self._fetch_stock_data_sina, "Sina Finance"),
            (self._fetch_stock_data_tx, "Tencent Finance"),
        ]

        last_error = None

        for fetch_method, source_name in methods:
            try:
                logger.info(f"[data source] Trying {source_name} to fetch {stock_code}...")
                df = fetch_method(stock_code, start_date, end_date)

                if df is not None and not df.empty:
                    logger.info(f"[data source] {source_name} fetch succeeded")
                    return df
            except Exception as e:
                last_error = e
                logger.warning(f"[data source] {source_name} failed to fetch: {e}")

        # All failed
        raise DataFetchError(f"Akshare failed to fetch from all channels: {last_error}")

    def _fetch_stock_data_em(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch regular A-share historical data (EastMoney).
        Data source: ak.stock_zh_a_hist()
        """
        import akshare as ak

        # Anti-ban strategy 1: random User-Agent
        self._set_random_user_agent()

        # Anti-ban strategy 2: Forced sleep
        self._enforce_rate_limit()

        logger.info(f"[APIcall] ak.stock_zh_a_hist(symbol={stock_code}, ...)")

        try:
            import time as _time
            api_start = _time.time()

            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq"
            )

            api_elapsed = _time.time() - api_start

            if df is not None and not df.empty:
                logger.info(f"[APIreturn] ak.stock_zh_a_hist success: {len(df)} rows, elapsed {api_elapsed:.2f}s")
                return df
            else:
                logger.warning(f"[APIreturn] ak.stock_zh_a_hist may be rate-limited")
                return pd.DataFrame()

        except Exception as e:
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['banned', 'blocked', '频率', 'rate', '限制']):
                raise RateLimitError(f"Akshare(EM) may be rate-limited: {e}") from e
            raise e

    def _fetch_stock_data_sina(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch regular A-share historical data (Sina Finance).
        Data source: ak.stock_zh_a_daily()
        """
        import akshare as ak

        # Convert code format：sh600000, sz000001, bj920748
        symbol = _to_sina_tx_symbol(stock_code)

        self._enforce_rate_limit()

        try:
            df = _akshare_call_with_timeout(
                ak.stock_zh_a_daily,
                symbol=symbol,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq",
                timeout=self._history_call_timeout,
                call_name="ak.stock_zh_a_daily",
            )

            # Standardized Sina data column names
            # Sina return：date, open, high, low, close, volume, amount, outstanding_share, turnover
            if df is not None and not df.empty:
                # Make sure the date column exists
                if 'date' in df.columns:
                    df = df.rename(columns={'date': '日期'})

                # Map additional columns to match _normalize_data expectations
                # _normalize_data expect：date, opening, close, Highest, lowest, Volume, Turnover
                rename_map = {
                    'open': 'opening', 'high': 'Highest', 'low': 'lowest',
                    'close': 'close', 'volume': 'Volume', 'amount': 'Turnover'
                }
                df = df.rename(columns=rename_map)

                # Calculate the increase or decrease（Sina interface may not return）
                if '收盘' in df.columns:
                    df['涨跌幅'] = df['收盘'].pct_change() * 100
                    df['涨跌幅'] = df['涨跌幅'].fillna(0)

                return df
            return pd.DataFrame()

        except Exception as e:
            raise e

    def _fetch_stock_data_tx(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch regular A-share historical data (Tencent Finance).
        Data source: ak.stock_zh_a_hist_tx()
        """
        import akshare as ak

        # Convert code format：sh600000, sz000001, bj920748
        symbol = _to_sina_tx_symbol(stock_code)

        self._enforce_rate_limit()

        try:
            df = _akshare_call_with_timeout(
                ak.stock_zh_a_hist_tx,
                symbol=symbol,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq",
                timeout=self._history_call_timeout,
                call_name="ak.stock_zh_a_hist_tx",
            )

            # Standardized Tencent data column naming
            # Tencent returns：date, open, close, high, low, volume, amount
            if df is not None and not df.empty:
                rename_map = {
                    'date': 'date', 'open': 'opening', 'high': 'Highest',
                    'low': 'lowest', 'close': 'close', 'volume': 'Volume',
                    'amount': 'Turnover'
                }
                df = df.rename(columns=rename_map)

                # Tencent data usually contains 'Increase or decrease'，Calculate if not
                if 'pct_chg' in df.columns:
                    df = df.rename(columns={'pct_chg': '涨跌幅'})
                elif '收盘' in df.columns:
                    df['涨跌幅'] = df['收盘'].pct_change() * 100
                    df['涨跌幅'] = df['涨跌幅'].fillna(0)

                return df
            return pd.DataFrame()

        except Exception as e:
            raise e
    
    def _fetch_etf_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch ETF fund historical data.
        
        Data source: ak.fund_etf_hist_em()
        
        Args:
            stock_code: ETF code, e.g. '512400', '159883'
            start_date: start date, format 'YYYY-MM-DD'
            end_date: end date, format 'YYYY-MM-DD'
            
        Returns:
            ETF historical data DataFrame
        """
        import akshare as ak
        
        # Anti-ban strategy 1: random User-Agent
        self._set_random_user_agent()
        
        # Anti-ban strategy 2: Forced sleep
        self._enforce_rate_limit()
        
        logger.info(f"[APIcall] ak.fund_etf_hist_em(symbol={stock_code}, period=daily, "
                   f"start_date={start_date.replace('-', '')}, end_date={end_date.replace('-', '')}, adjust=qfq)")
        
        try:
            import time as _time
            api_start = _time.time()
            
            # call akshare to get ETF daily data
            df = ak.fund_etf_hist_em(
                symbol=stock_code,
                period="daily",
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq"  # forward-adjusted
            )
            
            api_elapsed = _time.time() - api_start
            
            # Log return data summary
            if df is not None and not df.empty:
                logger.info(f"[APIreturn] ak.fund_etf_hist_em success: returned {len(df)} rows of data, elapsed {api_elapsed:.2f}s")
                logger.info(f"[APIreturn] Columns: {list(df.columns)}")
                logger.info(f"[APIreturn] Date range: {df['日期'].iloc[0]} ~ {df['日期'].iloc[-1]}")
                logger.debug(f"[APIreturn] Latest 3 rows of data:\n{df.tail(3).to_string()}")
            else:
                logger.warning(f"[APIreturn] ak.fund_etf_hist_em may be rate-limited, elapsed {api_elapsed:.2f}s")
            
            return df
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Detect anti-climbing bans
            if any(keyword in error_msg for keyword in ['banned', 'blocked', '频率', 'rate', '限制']):
                logger.warning(f"Possible ban detected: {e}")
                raise RateLimitError(f"Akshare May be restricted: {e}") from e
            
            raise DataFetchError(f"Akshare get ETF Data failed: {e}") from e
    
    def _fetch_us_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical data on US stocks.
        
        Data source: ak.stock_us_daily() (Sina Finance)
        
        Args:
            stock_code: US stock code, e.g. 'AMD', 'AAPL', 'TSLA'
            start_date: start date, format 'YYYY-MM-DD'
            end_date: end date, format 'YYYY-MM-DD'
            
        Returns:
            US stock historical data DataFrame
        """
        import akshare as ak
        
        # Anti-ban strategy 1: random User-Agent
        self._set_random_user_agent()
        
        # Anti-ban strategy 2: Forced sleep
        self._enforce_rate_limit()
        
        # Use capital letters directly for U.S. stock codes
        symbol = stock_code.strip().upper()
        
        logger.info(f"[APIcall] ak.stock_us_daily(symbol={symbol}, adjust=qfq)")
        
        try:
            import time as _time
            api_start = _time.time()
            
            # call akshare Get daily data on US stocks
            # stock_us_daily Return all historical data，Subsequent filtering by date is required
            df = ak.stock_us_daily(
                symbol=symbol,
                adjust="qfq"  # 前复权
            )
            
            api_elapsed = _time.time() - api_start
            
            # Record return data summary
            if df is not None and not df.empty:
                logger.info(f"[APIreturn] ak.stock_us_daily success: return {len(df)} row data, time consuming {api_elapsed:.2f}s")
                logger.info(f"[APIreturn] List: {list(df.columns)}")
                
                # Filter by date
                df['date'] = pd.to_datetime(df['date'])
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]
                
                if not df.empty:
                    logger.info(f"[APIreturn] Filtered date range: {df['date'].iloc[0].strftime('%Y-%m-%d')} ~ {df['date'].iloc[-1].strftime('%Y-%m-%d')}")
                    logger.debug(f"[APIreturn] up to date3piece of data:\n{df.tail(3).to_string()}")
                else:
                    logger.warning(f"[APIreturn] The data is empty after filtering，date range {start_date} ~ {end_date} No data")
                
                # Convert column names to Chinese format to match _normalize_data
                # stock_us_daily return: date, open, high, low, close, volume
                rename_map = {
                    'date': 'date',
                    'open': 'opening',
                    'high': 'Highest',
                    'low': 'lowest',
                    'close': 'close',
                    'volume': 'Volume',
                }
                df = df.rename(columns=rename_map)
                
                # Calculate the increase or decrease（The US stock interface does not return directly）
                if '收盘' in df.columns:
                    df['涨跌幅'] = df['收盘'].pct_change() * 100
                    df['涨跌幅'] = df['涨跌幅'].fillna(0)
                
                # Estimated turnover（US stock interface does not return）
                if '成交量' in df.columns and '收盘' in df.columns:
                    df['成交额'] = df['成交量'] * df['收盘']
                else:
                    df['成交额'] = 0
                
                return df
            else:
                logger.warning(f"[APIreturn] ak.stock_us_daily May be restricted, time consuming {api_elapsed:.2f}s")
                return pd.DataFrame()
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Detect anti-climbing bans
            if any(keyword in error_msg for keyword in ['banned', 'blocked', '频率', 'rate', '限制']):
                logger.warning(f"Possible ban detected: {e}")
                raise RateLimitError(f"Akshare May be restricted: {e}") from e
            
            raise DataFetchError(f"Akshare Failed to obtain US stock data: {e}") from e

    def _fetch_hk_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Get historical data of Hong Kong stocks
        
        Data source：ak.stock_hk_hist()
        
        Args:
            stock_code: Hong Kong stock code，like '00700', '01810'
            start_date: start date，Format 'YYYY-MM-DD'
            end_date: end date，Format 'YYYY-MM-DD'
            
        Returns:
            Hong Kong stock historical data DataFrame
        """
        import akshare as ak
        
        # Anti-ban strategy 1: random User-Agent
        self._set_random_user_agent()
        
        # Anti-ban strategy 2: Forced sleep
        self._enforce_rate_limit()
        
        # Make sure the code is formatted correctly（5digits）
        code = stock_code.lower().replace('hk', '').zfill(5)
        
        logger.info(f"[APIcall] ak.stock_hk_hist(symbol={code}, period=daily, "
                   f"start_date={start_date.replace('-', '')}, end_date={end_date.replace('-', '')}, adjust=qfq)")
        
        try:
            import time as _time
            api_start = _time.time()
            
            # call akshare Get daily data of Hong Kong stocks
            df = ak.stock_hk_hist(
                symbol=code,
                period="daily",
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq"  # 前复权
            )
            
            api_elapsed = _time.time() - api_start
            
            # Record return data summary
            if df is not None and not df.empty:
                logger.info(f"[APIreturn] ak.stock_hk_hist success: return {len(df)} row data, time consuming {api_elapsed:.2f}s")
                logger.info(f"[APIreturn] List: {list(df.columns)}")
                logger.info(f"[APIreturn] date range: {df['日期'].iloc[0]} ~ {df['日期'].iloc[-1]}")
                logger.debug(f"[APIreturn] up to date3piece of data:\n{df.tail(3).to_string()}")
            else:
                logger.warning(f"[APIreturn] ak.stock_hk_hist May be restricted, time consuming {api_elapsed:.2f}s")
            
            return df
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Detect anti-climbing bans
            if any(keyword in error_msg for keyword in ['banned', 'blocked', '频率', 'rate', '限制']):
                logger.warning(f"Possible ban detected: {e}")
                raise RateLimitError(f"Akshare May be restricted: {e}") from e
            
            raise DataFetchError(f"Akshare Failed to obtain Hong Kong stock data: {e}") from e
    
    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        standardization Akshare data
        
        Akshare Returned column names（Chinese）：
        date, opening, close, Highest, lowest, Volume, Turnover, amplitude, Increase or decrease, Changes, turnover rate
        
        Need to be mapped to standard column names：
        date, open, high, low, close, volume, amount, pct_chg
        """
        df = df.copy()
        
        # Column name mapping（Akshare Chinese listing -> Standard English listing）
        column_mapping = {
            'date': 'date',
            'opening': 'open',
            'close': 'close',
            'Highest': 'high',
            'lowest': 'low',
            'Volume': 'volume',
            'Turnover': 'amount',
            'Increase or decrease': 'pct_chg',
        }
        
        # Add stock symbol column
        df = df.rename(columns=column_mapping)
        
        # Add stock symbol column
        df['code'] = stock_code
        
        # Keep only the columns you need
        keep_cols = ['code'] + STANDARD_COLUMNS
        existing_cols = [col for col in keep_cols if col in df.columns]
        df = df[existing_cols]
        
        return df
    
    def get_realtime_quote(self, stock_code: str, source: str = "em") -> Optional[UnifiedRealtimeQuote]:
        """
        Get real-time market data（Support multiple data sources）

        Data source priority（Configurable）：
        1. em: Oriental Fortune（akshare ak.stock_zh_a_spot_em）- The most complete data，Content ratio/PE/PB/Market value etc.
        2. sina: Sina Finance（akshare ak.stock_zh_a_spot）- lightweight，Basic market conditions
        3. tencent: Tencent direct interface - Single stock query，small load

        Args:
            stock_code: stock/ETFcode
            source: Optional，Optional "em", "sina", "tencent"

        Returns:
            UnifiedRealtimeQuote object，Return on failure to obtain None
        """
        circuit_breaker = get_realtime_circuit_breaker()

        # Choose different acquisition methods based on code type
        if _is_us_code(stock_code):
            # Not used for US stocks Akshare，Depend on YfinanceFetcher Ensure that the restoration price is consistent
            logger.debug(f"[APIjump over] {stock_code} It’s US stocks，Akshare Does not support real-time quotes of U.S. stocks")
            return None
        elif _is_hk_code(stock_code):
            return self._get_hk_realtime_quote(stock_code)
        elif _is_etf_code(stock_code):
            source_key = "akshare_etf"
            if not circuit_breaker.is_available(source_key):
                logger.info(f"[fuse] data source {source_key} in fuse state，jump over")
                return None
            return self._get_etf_realtime_quote(stock_code)
        else:
            source_key = f"akshare_{source}"
            if not circuit_breaker.is_available(source_key):
                logger.info(f"[fuse] data source {source_key} in fuse state，jump over")
                return None
            # ordinary A share：according to source Select data source
            if source == "sina":
                return self._get_stock_realtime_quote_sina(stock_code)
            elif source == "tencent":
                return self._get_stock_realtime_quote_tencent(stock_code)
            else:
                return self._get_stock_realtime_quote_em(stock_code)
    
    def _get_stock_realtime_quote_em(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """
        get normal A Real-time stock market data（Oriental Wealth Data Source）
        
        Data source：ak.stock_zh_a_spot_em()
        advantage：The most complete data，Content ratio、turnover rate、P/E ratio、price limit、total market capitalization、Circulation market value, etc.
        shortcoming：Pull in full，Large amount of data，prone to timeout/Sina financial data source
        """
        import akshare as ak
        circuit_breaker = get_realtime_circuit_breaker()
        source_key = "akshare_em"
        
        try:
            # Check cache
            current_time = time.time()
            if (_realtime_cache['data'] is not None and 
                current_time - _realtime_cache['timestamp'] < _realtime_cache['ttl']):
                df = _realtime_cache['data']
                cache_age = int(current_time - _realtime_cache['timestamp'])
                logger.debug(f"[cache hit] AReal-time stock quotes(Dongcai) - cache age {cache_age}s/{_realtime_cache['ttl']}s")
            else:
                # Trigger full refresh
                logger.info(f"[cache miss] Trigger full refresh AReal-time stock quotes(Dongcai)")
                last_error: Optional[Exception] = None
                df = None
                for attempt in range(1, 3):
                    try:
                        # Anti-ban strategy
                        self._set_random_user_agent()
                        self._enforce_rate_limit()

                        logger.info(f"[APIcall] ak.stock_zh_a_spot_em() getAReal-time stock quotes... (attempt {attempt}/2)")
                        import time as _time
                        api_start = _time.time()

                        df = ak.stock_zh_a_spot_em()

                        api_elapsed = _time.time() - api_start
                        logger.info(f"[APIreturn] ak.stock_zh_a_spot_em success: return {len(df)} only stocks, time consuming {api_elapsed:.2f}s")
                        circuit_breaker.record_success(source_key)
                        break
                    except Exception as e:
                        last_error = e
                        logger.info(f"[APImistake] ak.stock_zh_a_spot_em Failed to obtain (attempt {attempt}/2): {e}")
                        time.sleep(min(2 ** attempt, 5))

                # Update cache：Successfully cached data；Avoid repeated requests to the same interface in the same round of tasks，Avoid repeated requests to the same interface in the same round of tasks
                if df is None:
                    logger.info(f"[APImistake] ak.stock_zh_a_spot_em ultimately failed: {last_error}")
                    circuit_breaker.record_failure(source_key, str(last_error))
                    df = pd.DataFrame()
                _realtime_cache['data'] = df
                _realtime_cache['timestamp'] = current_time
                logger.info(f"[cache updates] AReal-time stock quotes(Dongcai) cache flushed，TTL={_realtime_cache['ttl']}s")

            if df is None or df.empty:
                logger.info(f"[Real-time quotes] AStock real-time market data is empty，jump over {stock_code}")
                return None
            
            # Find specific stocks
            row = df[df['代码'] == stock_code]
            if row.empty:
                logger.info(f"[APIreturn] No stock found {stock_code} real-time quotes")
                return None
            
            row = row.iloc[0]
            
            # use realtime_types.py Unified conversion function in
            quote = UnifiedRealtimeQuote(
                code=stock_code,
                name=str(row.get('名称', '')),
                source=RealtimeSource.AKSHARE_EM,
                price=safe_float(row.get('最新价')),
                change_pct=safe_float(row.get('涨跌幅')),
                change_amount=safe_float(row.get('涨跌额')),
                volume=safe_int(row.get('成交量')),
                amount=safe_float(row.get('成交额')),
                volume_ratio=safe_float(row.get('量比')),
                turnover_rate=safe_float(row.get('换手率')),
                amplitude=safe_float(row.get('振幅')),
                open_price=safe_float(row.get('今开')),
                high=safe_float(row.get('最高')),
                low=safe_float(row.get('最低')),
                pe_ratio=safe_float(row.get('市盈率-动态')),
                pb_ratio=safe_float(row.get('市净率')),
                total_mv=safe_float(row.get('总市值')),
                circ_mv=safe_float(row.get('流通市值')),
                change_60d=safe_float(row.get('60日涨跌幅')),
                high_52w=safe_float(row.get('52周最高')),
                low_52w=safe_float(row.get('52周最低')),
            )
            
            logger.info(f"[Real-time quotes-Dongcai] {stock_code} {quote.name}: price={quote.price}, ups and downs={quote.change_pct}%, "
                       f"Quantity ratio={quote.volume_ratio}, turnover rate={quote.turnover_rate}%")
            return quote
            
        except Exception as e:
            logger.info(f"[APImistake] get {stock_code} Real-time quotes(Dongcai)fail: {e}")
            circuit_breaker.record_failure(source_key, str(e))
            return None
    
    def _get_stock_realtime_quote_sina(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """
        get normal A Real-time stock market data（Sina financial data source）
        
        Data source：Find the corresponding index（direct connection，Single stock query）
        advantage：Single stock query，small load，fast
        shortcoming：Fewer data fields，Incomparable/PE/PBwait
        
        Interface format：http://hq.sinajs.cn/list=sh600519,sz000001
        """
        circuit_breaker = get_realtime_circuit_breaker()
        source_key = "akshare_sina"
        symbol = _to_sina_tx_symbol(stock_code)
        url = f"http://{SINA_REALTIME_ENDPOINT}={symbol}"
        api_start = time.time()
        
        try:
            headers = {
                'Referer': 'http://finance.sina.com.cn',
                'User-Agent': random.choice(USER_AGENTS)
            }
            
            logger.info(
                f"[APIcall] Sina Finance interface acquisition {stock_code} Real-time quotes: endpoint={SINA_REALTIME_ENDPOINT}, symbol={symbol}"
            )
            
            self._enforce_rate_limit()
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'gbk'
            api_elapsed = time.time() - api_start
            
            if response.status_code != 200:
                failure_message = _build_realtime_failure_message(
                    source_name="新浪",
                    endpoint=SINA_REALTIME_ENDPOINT,
                    stock_code=stock_code,
                    symbol=symbol,
                    category="http_status",
                    detail=f"HTTP {response.status_code}",
                    elapsed=api_elapsed,
                    error_type="HTTPStatus",
                )
                logger.info(failure_message)
                circuit_breaker.record_failure(source_key, failure_message)
                return None
            
            # Parse data：var hq_str_sh600519="Kweichow Moutai,1866.000,1870.000,..."
            content = response.text.strip()
            if '=""' in content or not content:
                failure_message = _build_realtime_failure_message(
                    source_name="新浪",
                    endpoint=SINA_REALTIME_ENDPOINT,
                    stock_code=stock_code,
                    symbol=symbol,
                    category="empty_response",
                    detail="empty quote payload",
                    elapsed=api_elapsed,
                    error_type="EmptyResponse",
                )
                logger.info(failure_message)
                circuit_breaker.record_failure(source_key, failure_message)
                return None
            
            # Sina data field order
            data_start = content.find('"')
            data_end = content.rfind('"')
            if data_start == -1 or data_end == -1:
                failure_message = _build_realtime_failure_message(
                    source_name="新浪",
                    endpoint=SINA_REALTIME_ENDPOINT,
                    stock_code=stock_code,
                    symbol=symbol,
                    category="malformed_payload",
                    detail="quote payload missing quotes",
                    elapsed=api_elapsed,
                    error_type="MalformedPayload",
                )
                logger.info(failure_message)
                circuit_breaker.record_failure(source_key, failure_message)
                return None
            
            data_str = content[data_start+1:data_end]
            fields = data_str.split(',')
            
            if len(fields) < 32:
                failure_message = _build_realtime_failure_message(
                    source_name="新浪",
                    endpoint=SINA_REALTIME_ENDPOINT,
                    stock_code=stock_code,
                    symbol=symbol,
                    category="insufficient_fields",
                    detail=f"field_count={len(fields)}",
                    elapsed=api_elapsed,
                    error_type="InsufficientFields",
                )
                logger.info(failure_message)
                circuit_breaker.record_failure(source_key, failure_message)
                return None
            
            circuit_breaker.record_success(source_key)
            
            # Sina data field order：
            # 0:name 1:Open today 2:Collected yesterday 3:latest price 4:Highest 5:lowest 6:buy one price 7:Sell ​​one price
            # 8:Volume(share) 9:Turnover(Yuan) ... 30:date 31:time
            # use realtime_types.py Unified conversion function in
            price = safe_float(fields[3])
            pre_close = safe_float(fields[2])
            change_pct = None
            change_amount = None
            if price and pre_close and pre_close > 0:
                change_amount = price - pre_close
                change_pct = (change_amount / pre_close) * 100
            
            quote = UnifiedRealtimeQuote(
                code=stock_code,
                name=fields[0],
                source=RealtimeSource.AKSHARE_SINA,
                price=price,
                change_pct=change_pct,
                change_amount=change_amount,
                volume=safe_int(fields[8]),  # Volume（share）
                amount=safe_float(fields[9]),  # Turnover（Yuan）
                open_price=safe_float(fields[1]),
                high=safe_float(fields[4]),
                low=safe_float(fields[5]),
                pre_close=pre_close,
            )
            
            logger.info(
                f"[Real-time quotes-Sina] {stock_code} {quote.name}: endpoint={SINA_REALTIME_ENDPOINT}, "
                f"price={quote.price}, ups and downs={quote.change_pct}, Volume={quote.volume}, elapsed={api_elapsed:.2f}s"
            )
            return quote
            
        except Exception as e:
            api_elapsed = time.time() - api_start
            category, detail = _classify_realtime_http_error(e)
            failure_message = _build_realtime_failure_message(
                source_name="新浪",
                endpoint=SINA_REALTIME_ENDPOINT,
                stock_code=stock_code,
                symbol=symbol,
                category=category,
                detail=detail,
                elapsed=api_elapsed,
                error_type=type(e).__name__,
            )
            logger.info(failure_message)
            circuit_breaker.record_failure(source_key, failure_message)
            return None
    
    def _get_stock_realtime_quote_tencent(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """
        get normal A Real-time stock market data（Tencent financial data source）
        
        Data source：free（direct connection，Single stock query）
        advantage：Single stock query，small load，Including turnover rate
        shortcoming：Incomparable/PE/PBValuation data
        
        Interface format：http://qt.gtimg.cn/q=sh600519,sz000001
        """
        circuit_breaker = get_realtime_circuit_breaker()
        source_key = "akshare_tencent"
        symbol = _to_sina_tx_symbol(stock_code)
        url = f"http://{TENCENT_REALTIME_ENDPOINT}={symbol}"
        api_start = time.time()
        
        try:
            headers = {
                'Referer': 'http://finance.qq.com',
                'User-Agent': random.choice(USER_AGENTS)
            }
            
            logger.info(
                f"[APIcall] Tencent financial interface acquisition {stock_code} Real-time quotes: endpoint={TENCENT_REALTIME_ENDPOINT}, symbol={symbol}"
            )
            
            self._enforce_rate_limit()
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'gbk'
            api_elapsed = time.time() - api_start
            
            if response.status_code != 200:
                failure_message = _build_realtime_failure_message(
                    source_name="腾讯",
                    endpoint=TENCENT_REALTIME_ENDPOINT,
                    stock_code=stock_code,
                    symbol=symbol,
                    category="http_status",
                    detail=f"HTTP {response.status_code}",
                    elapsed=api_elapsed,
                    error_type="HTTPStatus",
                )
                logger.info(failure_message)
                circuit_breaker.record_failure(source_key, failure_message)
                return None
            
            content = response.text.strip()
            if '=""' in content or not content:
                failure_message = _build_realtime_failure_message(
                    source_name="腾讯",
                    endpoint=TENCENT_REALTIME_ENDPOINT,
                    stock_code=stock_code,
                    symbol=symbol,
                    category="empty_response",
                    detail="empty quote payload",
                    elapsed=api_elapsed,
                    error_type="EmptyResponse",
                )
                logger.info(failure_message)
                circuit_breaker.record_failure(source_key, failure_message)
                return None
            
            # Extract data
            data_start = content.find('"')
            data_end = content.rfind('"')
            if data_start == -1 or data_end == -1:
                failure_message = _build_realtime_failure_message(
                    source_name="腾讯",
                    endpoint=TENCENT_REALTIME_ENDPOINT,
                    stock_code=stock_code,
                    symbol=symbol,
                    category="malformed_payload",
                    detail="quote payload missing quotes",
                    elapsed=api_elapsed,
                    error_type="MalformedPayload",
                )
                logger.info(failure_message)
                circuit_breaker.record_failure(source_key, failure_message)
                return None
            
            data_str = content[data_start+1:data_end]
            fields = data_str.split('~')

            if len(fields) < 45:
                failure_message = _build_realtime_failure_message(
                    source_name="腾讯",
                    endpoint=TENCENT_REALTIME_ENDPOINT,
                    stock_code=stock_code,
                    symbol=symbol,
                    category="insufficient_fields",
                    detail=f"field_count={len(fields)}",
                    elapsed=api_elapsed,
                    error_type="InsufficientFields",
                )
                logger.info(failure_message)
                circuit_breaker.record_failure(source_key, failure_message)
                return None
            
            circuit_breaker.record_success(source_key)
            
            # Tencent data field order（whole）：
            # 1:name 2:code 3:latest price 4:Collected yesterday 5:Open today 6:Volume 7:Buy and sell five levels 8:Buy and sell five levels
            # 9-28:Buy and sell five levels 30:Timestamp 31:Changes 32:Increase or decrease(%) 33:Highest 34:lowest 35:close/Volume/Turnover
            # 36:Volume(change payload change) 37:Turnover(Ten thousand) 38:turnover rate(%) 39:P/E ratio 43:amplitude(%)
            # 44:Circulation market value(100 million) 45:total market capitalization(100 million) 46:price limit 47:price limit 48:limit price 49:Quantity ratio
            # use realtime_types.py Unified conversion function in
            amount = _parse_tencent_amount(fields)
            quote = UnifiedRealtimeQuote(
                code=stock_code,
                name=fields[1] if len(fields) > 1 else "",
                source=RealtimeSource.TENCENT,
                price=safe_float(fields[3]),
                change_pct=safe_float(fields[32]),
                change_amount=safe_float(fields[31]) if len(fields) > 31 else None,
                volume=_normalize_tencent_volume(fields),
                amount=amount,
                open_price=safe_float(fields[5]),
                high=safe_float(fields[33]) if len(fields) > 33 else None,  # 修正：Field 33 是最高价
                low=safe_float(fields[34]) if len(fields) > 34 else None,  # 修正：Field 34 是最低价
                pre_close=safe_float(fields[4]),
                turnover_rate=safe_float(fields[38]) if len(fields) > 38 else None,
                amplitude=safe_float(fields[43]) if len(fields) > 43 else None,
                volume_ratio=safe_float(fields[49]) if len(fields) > 49 else None,  # Quantity ratio
                pe_ratio=safe_float(fields[39]) if len(fields) > 39 else None,  # P/E ratio
                pb_ratio=safe_float(fields[46]) if len(fields) > 46 else None,  # price limit
                circ_mv=safe_float(fields[44]) * 100000000 if len(fields) > 44 and fields[44] else None,  # Circulation market value(100 million->Yuan)
                total_mv=safe_float(fields[45]) * 100000000 if len(fields) > 45 and fields[45] else None,  # total market capitalization(100 million->Yuan)
            )
            
            logger.info(
                f"[Real-time quotes-Tencent] {stock_code} {quote.name}: endpoint={TENCENT_REALTIME_ENDPOINT}, "
                f"price={quote.price}, ups and downs={quote.change_pct}%, Quantity ratio={quote.volume_ratio}, "
                f"turnover rate={quote.turnover_rate}%, elapsed={api_elapsed:.2f}s"
            )
            return quote
            
        except Exception as e:
            api_elapsed = time.time() - api_start
            category, detail = _classify_realtime_http_error(e)
            failure_message = _build_realtime_failure_message(
                source_name="腾讯",
                endpoint=TENCENT_REALTIME_ENDPOINT,
                stock_code=stock_code,
                symbol=symbol,
                category=category,
                detail=detail,
                elapsed=api_elapsed,
                error_type=type(e).__name__,
            )
            logger.info(failure_message)
            circuit_breaker.record_failure(source_key, failure_message)
            return None
    
    def _get_etf_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """
        get ETF Fund real-time market data
        
        Data source：ak.fund_etf_spot_em()
        Include：latest price、Increase or decrease、Volume、Turnover、Turnover rate, etc.
        
        Args:
            stock_code: ETF code
            
        Returns:
            UnifiedRealtimeQuote object，Return on failure to obtain None
        """
        import akshare as ak
        circuit_breaker = get_realtime_circuit_breaker()
        source_key = "akshare_etf"
        
        try:
            # Check cache
            current_time = time.time()
            if (_etf_realtime_cache['data'] is not None and 
                current_time - _etf_realtime_cache['timestamp'] < _etf_realtime_cache['ttl']):
                df = _etf_realtime_cache['data']
                logger.debug(f"[cache hit] Use cachedETFReal-time market data")
            else:
                last_error: Optional[Exception] = None
                df = None
                for attempt in range(1, 3):
                    try:
                        # Anti-ban strategy
                        self._set_random_user_agent()
                        self._enforce_rate_limit()

                        logger.info(f"[APIcall] ak.fund_etf_spot_em() getETFReal-time quotes... (attempt {attempt}/2)")
                        import time as _time
                        api_start = _time.time()

                        df = ak.fund_etf_spot_em()

                        api_elapsed = _time.time() - api_start
                        logger.info(f"[APIreturn] ak.fund_etf_spot_em success: return {len(df)} OnlyETF, time consuming {api_elapsed:.2f}s")
                        circuit_breaker.record_success(source_key)
                        break
                    except Exception as e:
                        last_error = e
                        logger.info(f"[APImistake] ak.fund_etf_spot_em Failed to obtain (attempt {attempt}/2): {e}")
                        time.sleep(min(2 ** attempt, 5))

                if df is None:
                    logger.info(f"[APImistake] ak.fund_etf_spot_em ultimately failed: {last_error}")
                    circuit_breaker.record_failure(source_key, str(last_error))
                    df = pd.DataFrame()
                _etf_realtime_cache['data'] = df
                _etf_realtime_cache['timestamp'] = current_time

            if df is None or df.empty:
                logger.info(f"[Real-time quotes] ETFReal-time market data is empty，jump over {stock_code}")
                return None
            
            # Find specified ETF
            row = df[df['代码'] == stock_code]
            if row.empty:
                logger.info(f"[APIreturn] not found ETF {stock_code} real-time quotes")
                return None
            
            row = row.iloc[0]
            
            # use realtime_types.py Unified conversion function in
            # ETF Market data construction
            quote = UnifiedRealtimeQuote(
                code=stock_code,
                name=str(row.get('名称', '')),
                source=RealtimeSource.AKSHARE_EM,
                price=safe_float(row.get('最新价')),
                change_pct=safe_float(row.get('涨跌幅')),
                change_amount=safe_float(row.get('涨跌额')),
                volume=safe_int(row.get('成交量')),
                amount=safe_float(row.get('成交额')),
                volume_ratio=safe_float(row.get('量比')),
                turnover_rate=safe_float(row.get('换手率')),
                amplitude=safe_float(row.get('振幅')),
                open_price=safe_float(row.get('开盘价')),
                high=safe_float(row.get('最高价')),
                low=safe_float(row.get('最低价')),
                total_mv=safe_float(row.get('总市值')),
                circ_mv=safe_float(row.get('流通市值')),
                high_52w=safe_float(row.get('52周最高')),
                low_52w=safe_float(row.get('52周最低')),
            )
            
            logger.info(f"[ETFReal-time quotes] {stock_code} {quote.name}: price={quote.price}, ups and downs={quote.change_pct}%, "
                       f"turnover rate={quote.turnover_rate}%")
            return quote
            
        except Exception as e:
            logger.info(f"[APImistake] get ETF {stock_code} Real-time quotes failed: {e}")
            circuit_breaker.record_failure(source_key, str(e))
            return None
    
    def _get_hk_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """
        Get real-time market data of Hong Kong stocks

        master data source：ak.stock_hk_spot_em()（Oriental Fortune）
        Alternate data sources：ak.stock_hk_spot()（Sina）
        Include：latest price、Increase or decrease、Volume、Turnover, etc.

        Args:
            stock_code: Hong Kong stock code

        Returns:
            UnifiedRealtimeQuote object，Return on failure to obtain None
        """
        import akshare as ak
        circuit_breaker = get_realtime_circuit_breaker()
        em_key = "akshare_hk_em"
        sina_key = "akshare_hk_sina"

        # Anti-ban strategy
        self._set_random_user_agent()
        self._enforce_rate_limit()

        # Make sure the code is formatted correctly（5digits）
        raw_code = stock_code.strip().lower()
        if raw_code.endswith('.hk'):
            raw_code = raw_code[:-3]
        if raw_code.startswith('hk'):
            raw_code = raw_code[2:]
        code = raw_code.zfill(5)

        # --- master data source：Oriental Fortune ---
        if circuit_breaker.is_available(em_key):
            try:
                logger.info(f"[APIcall] ak.stock_hk_spot_em() Get real-time quotes of Hong Kong stocks...")
                import time as _time
                api_start = _time.time()

                df = ak.stock_hk_spot_em()

                api_elapsed = _time.time() - api_start
                logger.info(f"[APIreturn] ak.stock_hk_spot_em success: return {len(df)} Only Hong Kong stocks, time consuming {api_elapsed:.2f}s")
                circuit_breaker.record_success(em_key)

                # Find designated Hong Kong stocks
                row = df[df['代码'] == code]
                if row.empty:
                    logger.info(f"[APIreturn] No Hong Kong stocks found {code} real-time quotes (stock_hk_spot_em)")
                else:
                    row = row.iloc[0]
                    quote = UnifiedRealtimeQuote(
                        code=stock_code,
                        name=str(row.get('名称', '')),
                        source=RealtimeSource.AKSHARE_EM,
                        price=safe_float(row.get('最新价')),
                        change_pct=safe_float(row.get('涨跌幅')),
                        change_amount=safe_float(row.get('涨跌额')),
                        volume=safe_int(row.get('成交量')),
                        amount=safe_float(row.get('成交额')),
                        volume_ratio=safe_float(row.get('量比')),
                        turnover_rate=safe_float(row.get('换手率')),
                        amplitude=safe_float(row.get('振幅')),
                        pe_ratio=safe_float(row.get('市盈率')),
                        pb_ratio=safe_float(row.get('市净率')),
                        total_mv=safe_float(row.get('总市值')),
                        circ_mv=safe_float(row.get('流通市值')),
                        high_52w=safe_float(row.get('52周最高')),
                        low_52w=safe_float(row.get('52周最低')),
                    )
                    logger.info(f"[Hong Kong stock real-time quotes] {stock_code} {quote.name}: price={quote.price}, ups and downs={quote.change_pct}%, "
                                f"turnover rate={quote.turnover_rate}%")
                    return quote

            except Exception as e:
                logger.warning(f"[APImistake] ak.stock_hk_spot_em Get Hong Kong stocks {stock_code} fail: {e}，try stock_hk_spot Alternate interface")
                circuit_breaker.record_failure(em_key, str(e))
        else:
            logger.info(f"[fuse] data source {em_key} in fuse state，Try using an alternate link")

        # --- Alternate data sources：Sina ---
        if not circuit_breaker.is_available(sina_key):
            logger.info(f"[fuse] data source {sina_key} in fuse state，Skip backup link")
            return None

        try:
            logger.info(f"[APIcall] ak.stock_hk_spot() Get real-time quotes of Hong Kong stocks（spare）...")
            import time as _time
            api_start = _time.time()

            df_spot = ak.stock_hk_spot()

            api_elapsed = _time.time() - api_start
            logger.info(f"[APIreturn] ak.stock_hk_spot success: return {len(df_spot)} Only Hong Kong stocks, time consuming {api_elapsed:.2f}s")

            row = df_spot[df_spot['代码'] == code]
            if row.empty:
                logger.info(f"[APIreturn] No Hong Kong stocks found {code} real-time quotes (stock_hk_spot)")
                return None

            row = row.iloc[0]
            quote = UnifiedRealtimeQuote(
                code=stock_code,
                name=str(row.get('名称', '')),
                source=RealtimeSource.AKSHARE_EM,
                price=safe_float(row.get('最新价')),
                change_pct=safe_float(row.get('涨跌幅')),
                change_amount=safe_float(row.get('涨跌额')),
                volume=safe_int(row.get('成交量')),
                amount=safe_float(row.get('成交额')),
            )
            circuit_breaker.record_success(sina_key)
            logger.info(f"[Hong Kong stock real-time quotes-spare] {stock_code} {quote.name}: price={quote.price}, ups and downs={quote.change_pct}%")
            return quote

        except Exception as e:
            logger.info(f"[APImistake] ak.stock_hk_spot The backup interface also fails: {e}")
            circuit_breaker.record_failure(sina_key, str(e))
            return None
    
    def get_chip_distribution(self, stock_code: str) -> Optional[ChipDistribution]:
        """
        Get chip distribution data
        
        Data source：ak.stock_cyq_em()
        Include：Profit ratio、average cost、Chip concentration
        
        Notice：ETF/The index does not have chip distribution data，will return directly None
        
        Args:
            stock_code: Stock code
            
        Returns:
            ChipDistribution object（Latest day's data），Return on failure to obtain None
        """
        import akshare as ak

        # There is no chip distribution data for U.S. stocks（Akshare Not supported）
        if _is_us_code(stock_code):
            logger.debug(f"[APIjump over] {stock_code} It’s US stocks，No chip distribution data")
            return None

        # yes（stock_cyq_em yes A Stock exclusive interface）
        if _is_hk_code(stock_code):
            logger.debug(f"[APIjump over] {stock_code} It’s Hong Kong stocks，No chip distribution data")
            return None

        # ETF/The index does not have chip distribution data
        if _is_etf_code(stock_code):
            logger.debug(f"[APIjump over] {stock_code} yes ETF/index，No chip distribution data")
            return None
        
        try:
            # Anti-ban strategy
            self._set_random_user_agent()
            self._enforce_rate_limit()
            
            logger.info(f"[APIcall] ak.stock_cyq_em(symbol={stock_code}) Major Index Code Mapping...")
            import time as _time
            api_start = _time.time()
            
            df = ak.stock_cyq_em(symbol=stock_code)
            
            api_elapsed = _time.time() - api_start
            
            if df.empty:
                logger.warning(f"[APIreturn] ak.stock_cyq_em May be restricted, time consuming {api_elapsed:.2f}s")
                return None
            
            logger.info(f"[APIreturn] ak.stock_cyq_em success: return {len(df)} day data, time consuming {api_elapsed:.2f}s")
            logger.debug(f"[APIreturn] Chip data column name: {list(df.columns)}")
            
            # Get the latest day's data
            latest = df.iloc[-1]
            
            # use realtime_types.py Unified conversion function in
            chip = ChipDistribution(
                code=stock_code,
                date=str(latest.get('日期', '')),
                profit_ratio=safe_float(latest.get('获利比例')),
                avg_cost=safe_float(latest.get('平均成本')),
                cost_90_low=safe_float(latest.get('90成本-低')),
                cost_90_high=safe_float(latest.get('90成本-高')),
                concentration_90=safe_float(latest.get('90集中度')),
                cost_70_low=safe_float(latest.get('70成本-低')),
                cost_70_high=safe_float(latest.get('70成本-高')),
                concentration_70=safe_float(latest.get('70集中度')),
            )
            
            logger.info(f"[Chip distribution] {stock_code} date={chip.date}: Profit ratio={chip.profit_ratio:.1%}, "
                       f"average cost={chip.avg_cost}, 90%Concentration={chip.concentration_90:.2%}, "
                       f"70%Concentration={chip.concentration_70:.2%}")
            return chip
            
        except Exception as e:
            logger.error(f"[APImistake] get {stock_code} Chip distribution failed: {e}")
            return None
    
    def get_enhanced_data(self, stock_code: str, days: int = 60) -> Dict[str, Any]:
        """
        Get augmented data（historyKWire + Real-time quotes + Chip distribution）
        
        Args:
            stock_code: Stock code
            days: Historical data days
            
        Returns:
            dictionary containing all data
        """
        result = {
            'code': stock_code,
            'daily_data': None,
            'realtime_quote': None,
            'chip_distribution': None,
        }
        
        # Get daily data
        try:
            df = self.get_daily_data(stock_code, days=days)
            result['daily_data'] = df
        except Exception as e:
            logger.error(f"get {stock_code} Shanghai Composite Index: {e}")
        
        # Get real-time quotes
        result['realtime_quote'] = self.get_realtime_quote(stock_code)
        
        # Major Index Code Mapping
        result['chip_distribution'] = self.get_chip_distribution(stock_code)
        
        return result

    def get_main_indices(self, region: str = "cn") -> Optional[List[Dict[str, Any]]]:
        """
        Get real-time quotes of major indices (Sina interface)，Only supports A share
        """
        if region != "cn":
            return None
        import akshare as ak

        # Major Index Code Mapping
        indices_map = {
            'sh000001': 'Shanghai Composite Index',
            'sz399001': 'Shenzhen Component Index',
            'sz399006': 'GEM Index',
            'sh000688': 'Science and Technology50',
            'sh000016': 'Shanghai Stock Exchange50',
            'sh000300': 'Shanghai and Shenzhen300',
        }

        try:
            self._set_random_user_agent()
            self._enforce_rate_limit()

            # use akshare Get index quotes（Find the corresponding index）
            df = ak.stock_zh_index_spot_sina()

            results = []
            if df is not None and not df.empty:
                for code, name in indices_map.items():
                    # Find the corresponding index
                    row = df[df['代码'] == code]
                    if row.empty:
                        # Try searching with prefix
                        row = df[df['代码'].str.contains(code)]

                    if not row.empty:
                        row = row.iloc[0]
                        current = safe_float(row.get('最新价', 0))
                        prev_close = safe_float(row.get('昨收', 0))
                        high = safe_float(row.get('最高', 0))
                        low = safe_float(row.get('最低', 0))

                        # Calculate amplitude
                        amplitude = 0.0
                        if prev_close > 0:
                            amplitude = (high - low) / prev_close * 100

                        results.append({
                            'code': code,
                            'name': name,
                            'current': current,
                            'change': safe_float(row.get('涨跌额', 0)),
                            'change_pct': safe_float(row.get('涨跌幅', 0)),
                            'open': safe_float(row.get('今开', 0)),
                            'high': high,
                            'low': low,
                            'prev_close': prev_close,
                            'volume': safe_float(row.get('成交量', 0)),
                            'amount': safe_float(row.get('成交额', 0)),
                            'amplitude': amplitude,
                        })
            return results

        except Exception as e:
            logger.error(f"[Akshare] Failed to obtain index quotes: {e}")
            return None

    def get_market_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get market rise and fall statistics

        Data source priority：
        1. Dongcai interface (ak.stock_zh_a_spot_em)
        2. Sina interface (ak.stock_zh_a_spot)
        """
        import akshare as ak

        # Priority Dongcai interface
        try:
            self._set_random_user_agent()
            self._enforce_rate_limit()

            started_at = time.monotonic()
            logger.info(
                "[MarketStats] component=market_stats provider=AkshareFetcher "
                "api=ak.stock_zh_a_spot_em action=request_start"
            )
            df = ak.stock_zh_a_spot_em()
            elapsed = time.monotonic() - started_at
            logger.info(
                "[MarketStats] component=market_stats provider=AkshareFetcher "
                "api=ak.stock_zh_a_spot_em action=request_complete elapsed=%.2fs",
                elapsed,
            )
            if df is not None and not df.empty:
                return self._calc_market_stats(df)
            logger.warning(
                "[MarketStats] component=market_stats provider=AkshareFetcher "
                "api=ak.stock_zh_a_spot_em action=parse status=empty"
            )
        except Exception as e:
            logger.warning(
                "[MarketStats] component=market_stats provider=AkshareFetcher "
                "api=ak.stock_zh_a_spot_em action=failed error=%s fallback=ak.stock_zh_a_spot",
                e,
            )

        # After the failure of Dongcai，Try Sina interface
        try:
            self._set_random_user_agent()
            self._enforce_rate_limit()

            started_at = time.monotonic()
            logger.info(
                "[MarketStats] component=market_stats provider=AkshareFetcher "
                "api=ak.stock_zh_a_spot action=request_start"
            )
            df = ak.stock_zh_a_spot()
            elapsed = time.monotonic() - started_at
            logger.info(
                "[MarketStats] component=market_stats provider=AkshareFetcher "
                "api=ak.stock_zh_a_spot action=request_complete elapsed=%.2fs",
                elapsed,
            )
            if df is not None and not df.empty:
                return self._calc_market_stats(df)
            logger.warning(
                "[MarketStats] component=market_stats provider=AkshareFetcher "
                "api=ak.stock_zh_a_spot action=parse status=empty"
            )
        except Exception as e:
            logger.error(
                "[MarketStats] component=market_stats provider=AkshareFetcher "
                "api=ak.stock_zh_a_spot action=failed error=%s",
                e,
            )

        return None

    def _calc_market_stats(
        self,
        df: pd.DataFrame,
        ) -> Optional[Dict[str, Any]]:
        """From the market DataFrame Calculate rise and fall statistics。"""
        import numpy as np

        df = df.copy()
        
        # 1. Extract basic comparison data：latest price、Collected yesterday
        # Compatible with column names returned by different interfaces sina/em efinance tushare xtdata
        code_col = next((c for c in ['代码', '股票代码', 'ts_code','stock_code'] if c in df.columns), None)
        name_col = next((c for c in ['名称', '股票名称','name','name'] if c in df.columns), None)
        close_col = next((c for c in ['最新价', '最新价', 'close','lastPrice'] if c in df.columns), None)
        pre_close_col = next((c for c in ['昨收', '昨日收盘', 'pre_close','lastClose'] if c in df.columns), None)
        amount_col = next((c for c in ['成交额', '成交额', 'amount','amount'] if c in df.columns), None) 
        
        limit_up_count = 0
        limit_down_count = 0
        up_count = 0
        down_count = 0
        flat_count = 0

        for code, name, current_price, pre_close, amount in zip(
            df[code_col], df[name_col], df[close_col], df[pre_close_col], df[amount_col]
        ):
            
            # Suspension filter efinance The suspension data is sometimes missing and the price is displayed as '-'，em displayed asnone
            if pd.isna(current_price) or pd.isna(pre_close) or current_price in ['-'] or pre_close in ['-'] or amount == 0:
                continue
            
            # em、efinance forstr need to be converted tofloat
            current_price = float(current_price)
            pre_close = float(pre_close)
            
            # Get the purely numeric code with the prefix removed
            pure_code = normalize_stock_code(str(code)) 

            # A. Use pure numeric codes to determine (Use pure numeric codes to determine)
            if is_bse_code(pure_code): 
                ratio = 0.30
            elif is_kc_cy_stock(pure_code): #pure_code.startswith(('688', '30')):
                ratio = 0.20
            elif is_st_stock(name): #'ST' in str_name:
                ratio = 0.05
            else:
                ratio = 0.10

            # B. strictly follow A Proportion：Collected yesterday * (1 ± Proportion) -> Rounding retained2Accurate comparison
            limit_up_price = np.floor(pre_close * (1 + ratio) * 100 + 0.5) / 100.0
            limit_down_price = np.floor(pre_close * (1 - ratio) * 100 + 0.5) / 100.0

            limit_up_price_Tolerance = round(abs(pre_close * (1 + ratio) - limit_up_price), 10)
            limit_down_price_Tolerance = round(abs(pre_close * (1 - ratio) - limit_down_price), 10)

            # C. Accurate comparison
            if current_price > 0 :
                is_limit_up = (current_price > 0) and (abs(current_price - limit_up_price) <= limit_up_price_Tolerance)
                is_limit_down = (current_price > 0) and (abs(current_price - limit_down_price) <= limit_down_price_Tolerance)

                if is_limit_up:
                    limit_up_count += 1
                if is_limit_down:
                    limit_down_count += 1

                if current_price > pre_close:
                    up_count += 1
                elif current_price < pre_close:
                    down_count += 1
                else:
                    flat_count += 1
                
        # Statistical quantity
        stats = {
            'up_count': up_count,
            'down_count': down_count,
            'flat_count': flat_count,
            'limit_up_count': limit_up_count,
            'limit_down_count': limit_down_count,
            'total_amount': 0.0,
        }
        
        # Turnover statistics
        if amount_col and amount_col in df.columns:
            df[amount_col] = pd.to_numeric(df[amount_col], errors='coerce')
            stats['total_amount'] = (df[amount_col].sum() / 1e8)
            
        return stats

    def get_sector_rankings(self, n: int = 5) -> Optional[Tuple[List[Dict], List[Dict]]]:
        """
        Get industry sector rise and fall lists

        Data source priority：
        1. Dongcai interface (ak.stock_board_industry_name_em)
        2. Sina interface (ak.stock_sector_spot)
        """
        import akshare as ak

        def _get_rank_top_n(df: pd.DataFrame, change_col: str, industry_name: str, n: int) -> Tuple[list, list]:
            df[change_col] = pd.to_numeric(df[change_col], errors='coerce')
            df = df.dropna(subset=[change_col])

            # before increasen
            top = df.nlargest(n, change_col)
            top_sectors = [
                {'name': row[industry_name], 'change_pct': row[change_col]}
                for _, row in top.iterrows()
            ]

            bottom = df.nsmallest(n, change_col)
            bottom_sectors = [
                {'name': row[industry_name], 'change_pct': row[change_col]}
                for _, row in bottom.iterrows()
            ]
            return top_sectors, bottom_sectors
        
        # Priority Dongcai interface
        try:
            self._set_random_user_agent()
            self._enforce_rate_limit()

            logger.info("[APIcall] ak.stock_board_industry_name_em() Get section ranking...")
            df = ak.stock_board_industry_name_em()
            if df is not None and not df.empty:
                change_col = '涨跌幅'
                name = '板块名称'
                return _get_rank_top_n(df, change_col, name, n)
            
        except Exception as e:
            logger.warning(f"[Akshare] Dongcai Interface failed to obtain industry sector rankings: {e}，Try Sina interface")

        # After the failure of Dongcai，Try Sina interface
        try:
            self._set_random_user_agent()
            self._enforce_rate_limit()

            logger.info("[APIcall] ak.stock_sector_spot() Get industry sector rankings(Sina)...")
            df = ak.stock_sector_spot(indicator='行业')
            if df is None or df.empty:
                return None
            change_col = '涨跌幅'
            name = '板块'
            return _get_rank_top_n(df, change_col, name, n)
        
        except Exception as e:
            logger.error(f"[Akshare] Sina interface also failed to obtain sector rankings: {e}")
            return None

    def get_concept_rankings(self, n: int = 5) -> Optional[Tuple[List[Dict], List[Dict]]]:
        """Get concept/Topic rise and fall list。"""
        import akshare as ak

        try:
            self._set_random_user_agent()
            self._enforce_rate_limit()

            logger.info("[APIcall] ak.stock_board_concept_name_em() Get concept ranking...")
            df = ak.stock_board_concept_name_em()
            if df is None or df.empty:
                return None

            change_col = '涨跌幅'
            name_col = '板块名称'
            if change_col not in df.columns or name_col not in df.columns:
                return None

            df = df.copy()
            df[change_col] = pd.to_numeric(df[change_col], errors='coerce')
            df = df.dropna(subset=[change_col])
            top = df.nlargest(n, change_col)
            bottom = df.nsmallest(n, change_col)
            return (
                [
                    {'name': str(row[name_col]), 'change_pct': float(row[change_col])}
                    for _, row in top.iterrows()
                ],
                [
                    {'name': str(row[name_col]), 'change_pct': float(row[change_col])}
                    for _, row in bottom.iterrows()
                ],
            )
        except Exception as e:
            logger.warning(f"[Akshare] Failed to obtain concept ranking: {e}")
            return None

    def get_hot_stocks(self, n: int = 10) -> Optional[List[Dict[str, Any]]]:
        """Get the popular stock list，Downgrade by configuration-free hot list data source。"""
        import akshare as ak

        fetch_attempts = (
            ("东方财富人气榜", lambda top_n: self._get_eastmoney_hot_stocks(ak, top_n)),
            ("东方财富飙升榜", lambda top_n: self._get_eastmoney_hot_up_stocks(ak, top_n)),
            ("雪球关注榜", lambda top_n: self._get_xueqiu_hot_stocks(ak, top_n)),
        )
        last_error = ""
        for source, fetch in fetch_attempts:
            try:
                rows = fetch(n)
                if rows:
                    return rows[:n]
            except Exception as e:
                last_error = f"{source}: {e}"
                logger.debug("[Akshare] Popular stock candidate source failed source=%s: %s", source, e)
        if last_error:
            logger.warning("[Akshare] Failed to obtain all candidate sources of popular stocks: %s", last_error)
        return None

    def _get_eastmoney_hot_stocks(self, ak: Any, n: int = 10) -> Optional[List[Dict[str, Any]]]:
        """Get Oriental Fortune Popular Stock List。"""
        self._set_random_user_agent()
        self._enforce_rate_limit()

        logger.info("[APIcall] ak.stock_hot_rank_em() Get Oriental Fortune's popular stocks...")
        df = ak.stock_hot_rank_em()
        if df is None or df.empty:
            return None

        rows: List[Dict[str, Any]] = []
        for _, row in df.head(n).iterrows():
            rows.append({
                'rank': self._safe_int(row.get('当前排名')),
                'code': str(row.get('代码', '')).strip(),
                'name': str(row.get('股票名称', '')).strip(),
                'price': self._safe_float(row.get('最新价')),
                'change_pct': self._safe_float(row.get('涨跌幅')),
                'source': 'Oriental Fortune Popularity List',
            })
        return rows

    def _get_eastmoney_hot_up_stocks(self, ak: Any, n: int = 10) -> Optional[List[Dict[str, Any]]]:
        """Get the Oriental Wealth Soaring List。"""
        self._set_random_user_agent()
        self._enforce_rate_limit()

        logger.info("[APIcall] ak.stock_hot_up_em() Get the Oriental Wealth Soaring List...")
        df = ak.stock_hot_up_em()
        if df is None or df.empty:
            return None

        code_col = self._find_first_column(df, ("代码", "股票代码"))
        name_col = self._find_first_column(df, ("股票名称", "名称", "股票简称"))
        rank_col = self._find_first_column(df, ("当前排名", "排名", "序号"))
        price_col = self._find_first_column(df, ("最新价", "现价"))
        change_col = self._find_column_containing(df, ("涨跌幅",))
        if not code_col or not name_col:
            return None

        rows: List[Dict[str, Any]] = []
        for _, row in df.head(n).iterrows():
            rows.append({
                'rank': self._safe_int(row.get(rank_col)) if rank_col else len(rows) + 1,
                'code': str(row.get(code_col, '')).strip(),
                'name': str(row.get(name_col, '')).strip(),
                'price': self._safe_float(row.get(price_col)) if price_col else None,
                'change_pct': self._safe_float(row.get(change_col)) if change_col else None,
                'source': 'Oriental wealth soaring list',
            })
        return rows

    def _get_xueqiu_hot_stocks(self, ak: Any, n: int = 10) -> Optional[List[Dict[str, Any]]]:
        """Get to the bottom of the snowball attention list。The interface is slow，Only try after failing on Popularity List。"""
        self._set_random_user_agent()
        self._enforce_rate_limit()

        logger.info("[APIcall] ak.stock_hot_follow_xq() Get snowball attention list...")
        df = ak.stock_hot_follow_xq(symbol='最热门')
        if df is None or df.empty:
            return None

        rows: List[Dict[str, Any]] = []
        for idx, (_, row) in enumerate(df.head(n).iterrows(), 1):
            rows.append({
                'rank': idx,
                'code': str(row.get('股票代码', '')).strip(),
                'name': str(row.get('股票简称', '')).strip(),
                'price': self._safe_float(row.get('最新价')),
                'change_pct': None,
                'source': 'Snowball attention list',
            })
        return rows

    def get_limit_up_pool(
        self,
        date: Optional[str] = None,
        n: int = 20,
    ) -> Optional[List[Dict[str, Any]]]:
        """Get the daily limit pool，Prioritize display by number of consecutive boards and board closing time。"""
        import akshare as ak

        query_date = date or datetime.now().strftime('%Y%m%d')
        try:
            self._set_random_user_agent()
            self._enforce_rate_limit()

            logger.info("[APIcall] ak.stock_zt_pool_em(date=%s) Get the daily limit pool...", query_date)
            df = ak.stock_zt_pool_em(date=query_date)
            if df is None or df.empty:
                return None

            df = df.copy()
            for col in ('连板数', '封板资金', '成交额', '换手率', '涨跌幅'):
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            if '首次封板时间' in df.columns:
                df['首次封板时间'] = df['首次封板时间'].map(self._normalize_limit_time_value)
                df['_首次封板时间排序'] = df['首次封板时间'].where(df['首次封板时间'] != '', '999999')
            sort_cols = [col for col in ('连板数', '_首次封板时间排序') if col in df.columns]
            if sort_cols:
                ascending = [False if col == '连板数' else True for col in sort_cols]
                df = df.sort_values(sort_cols, ascending=ascending)

            rows: List[Dict[str, Any]] = []
            for _, row in df.head(n).iterrows():
                rows.append({
                    'code': str(row.get('代码', '')).strip(),
                    'name': str(row.get('名称', '')).strip(),
                    'change_pct': self._safe_float(row.get('涨跌幅')),
                    'price': self._safe_float(row.get('最新价')),
                    'amount': self._safe_float(row.get('成交额')),
                    'turnover_rate': self._safe_float(row.get('换手率')),
                    'seal_amount': self._safe_float(row.get('封板资金')),
                    'first_limit_time': str(row.get('首次封板时间', '')).strip(),
                    'last_limit_time': self._normalize_limit_time_value(row.get('最后封板时间')),
                    'break_count': self._safe_int(row.get('炸板次数')),
                    'limit_stat': str(row.get('涨停统计', '')).strip(),
                    'consecutive_boards': self._safe_int(row.get('连板数')),
                    'industry': str(row.get('所属行业', '')).strip(),
                })
            return rows
        except Exception as e:
            logger.warning(f"[Akshare] Failed to obtain daily limit pool: {e}")
            return None

    @staticmethod
    def _normalize_limit_time_value(value: Any) -> str:
        """Normalize AkShare HHMMSS-like seal time values to zero-padded HHMMSS."""
        try:
            if pd.isna(value):
                return ""
        except TypeError:
            pass

        text = str(value).strip()
        if not text or text.lower() in {"nan", "nat", "none", "null", "-", "--"}:
            return ""

        if ":" in text:
            parts = text.split(":")
            try:
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
                second = int(parts[2]) if len(parts) > 2 else 0
                return f"{hour:02d}{minute:02d}{second:02d}"
            except (TypeError, ValueError):
                return text

        try:
            return f"{int(float(text)):06d}"
        except (TypeError, ValueError):
            digits = "".join(ch for ch in text if ch.isdigit())
            return digits.zfill(6) if digits else text

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            if pd.isna(value):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            if pd.isna(value):
                return 0
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _find_first_column(df: pd.DataFrame, candidates: Tuple[str, ...]) -> Optional[str]:
        columns = [str(col) for col in df.columns]
        for candidate in candidates:
            if candidate in columns:
                return candidate
        return None

    @staticmethod
    def _find_column_containing(df: pd.DataFrame, keywords: Tuple[str, ...]) -> Optional[str]:
        for col in df.columns:
            col_text = str(col)
            if all(keyword in col_text for keyword in keywords):
                return col
        return None


if __name__ == "__main__":
    # test code
    logging.basicConfig(level=logging.DEBUG)
    
    fetcher = AkshareFetcher()
    
    # Test common stocks
    print("=" * 50)
    print("Test common stock data acquisition")
    print("=" * 50)
    try:
        df = fetcher.get_daily_data('600519')  # 茅台
        print(f"[stock] get success，common {len(df)} piece of data")
        print(df.tail())
    except Exception as e:
        print(f"[stock] Failed to obtain: {e}")
    
    # test ETF fund
    print("\n" + "=" * 50)
    print("test ETF Fund data acquisition")
    print("=" * 50)
    try:
        df = fetcher.get_daily_data('512400')  # 有色龙头ETF
        print(f"[ETF] get success，common {len(df)} piece of data")
        print(df.tail())
    except Exception as e:
        print(f"[ETF] Failed to obtain: {e}")
    
    # test ETF Real-time quotes
    print("\n" + "=" * 50)
    print("test ETF Get real-time quotes")
    print("=" * 50)
    try:
        quote = fetcher.get_realtime_quote('512880')  # 证券ETF
        if quote:
            print(f"[ETFreal time] {quote.name}: price={quote.price}, Increase or decrease={quote.change_pct}%")
        else:
            print("[ETFreal time] No data obtained")
    except Exception as e:
        print(f"[ETFreal time] Failed to obtain: {e}")
    
    # Test Hong Kong stock historical data
    print("\n" + "=" * 50)
    print("Test the acquisition of historical data of Hong Kong stocks")
    print("=" * 50)
    try:
        df = fetcher.get_daily_data('00700')  # Tencent Holdings
        print(f"[Hong Kong stocks] get success，common {len(df)} piece of data")
        print(df.tail())
    except Exception as e:
        print(f"[Hong Kong stocks] Failed to obtain: {e}")
    
    # Test real-time market conditions of Hong Kong stocks
    print("\n" + "=" * 50)
    print("Test the acquisition of real-time market quotations of Hong Kong stocks")
    print("=" * 50)
    try:
        quote = fetcher.get_realtime_quote('00700')  # Tencent Holdings
        if quote:
            print(f"[Hong Kong stocks real-time] {quote.name}: price={quote.price}, Increase or decrease={quote.change_pct}%")
        else:
            print("[Hong Kong stocks real-time] No data obtained")
    except Exception as e:
        print(f"[Hong Kong stocks real-time] Failed to obtain: {e}")

    # Test market statistics
    print("\n" + "=" * 50)
    print("Testing get_market_stats (akshare)")
    print("=" * 50)
    try:
        stats = fetcher.get_market_stats()
        if stats:
            print(f"Market Stats successfully computed:")
            print(f"Up: {stats['up_count']} (Limit Up: {stats['limit_up_count']})")
            print(f"Down: {stats['down_count']} (Limit Down: {stats['limit_down_count']})")
            print(f"Flat: {stats['flat_count']}")
            print(f"Total Amount: {stats['total_amount']:.2f} 100 million (Yi)")
        else:
            print("Failed to compute market stats.")
    except Exception as e:
        print(f"Failed to compute market stats: {e}")

    # Test chip distribution data
    print("\n" + "=" * 50)
    print("Test chip distribution data acquisition")
    print("=" * 50)
    try:
        chip = fetcher.get_chip_distribution('600519')  # 茅台
    except Exception as e:
        print(f"[Chip distribution] Failed to obtain: {e}")

    # Test industry sector ranking
    print("\n" + "=" * 50)
    print("Obtain ranking of testing industry sectors")
    print("=" * 50)
    try:
        rankings = fetcher.get_sector_rankings(n=5)
        if rankings:
            top, bottom = rankings
            print("Gainer list Top 5:")
            for sector in top:
                print(f"{sector['name']}: {sector['change_pct']}%")
            print("\nLoser list Top 5:")
            for sector in bottom:
                print(f"{sector['name']}: {sector['change_pct']}%")
        else:
            print("No industry sector ranking data was obtained.")
    except Exception as e:
        print(f"[Industry sector ranking] Failed to obtain: {e}")
