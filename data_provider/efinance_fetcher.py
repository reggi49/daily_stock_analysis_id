# -*- coding: utf-8 -*-
"""
===================================
EfinanceFetcher - Prioritize data sources (Priority 0)
===================================

Data source：Oriental wealth crawler（pass efinance Library）
Features：free、No need Token、Comprehensive data、API concise
storehouse：https://github.com/Micro-sheep/efinance

and AkshareFetcher similar，but efinance Library：
1. API More concise and easy to use
2. Support batch acquisition of data
3. More stable interface encapsulation

Anti-ban strategy：
1. Sleep randomly before each request 1.5-3.0 Second
2. Random rotation User-Agent
3. use tenacity Implement exponential backoff retries
4. fuse mechanism：Automatically cool down after consecutive failures
"""

import logging
import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd
import requests  # Import requests to capture exceptions
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

# Timeout (seconds) for efinance library calls that go through eastmoney APIs
# with no built-in timeout.  Prevents indefinite hangs when hosts are unreachable.
try:
    _EF_CALL_TIMEOUT = int(os.environ.get("EFINANCE_CALL_TIMEOUT", "30"))
except (ValueError, TypeError):
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "EFINANCE_CALL_TIMEOUT is not a valid integer, using default 30s"
    )
    _EF_CALL_TIMEOUT = 30

from src.patches.eastmoney_patch import eastmoney_patch
from src.config import get_config
from .base import (
    BaseFetcher,
    DataFetchError,
    RateLimitError,
    STANDARD_COLUMNS,
    is_bse_code,
    is_st_stock,
    is_kc_cy_stock,
    normalize_stock_code,
    _is_hk_market,
    _is_etf_code as _is_a_share_etf_code,
)
from .realtime_types import (
    UnifiedRealtimeQuote, RealtimeSource,
    get_realtime_circuit_breaker,
    safe_float, safe_int  # Use unified type conversion functions
)


# Avoid duplicate requests，Avoid duplicate requests
@dataclass
class EfinanceRealtimeQuote:
    """
    Real-time market data（from efinance）- Backwards compatible aliases
    
    New code is recommended to use UnifiedRealtimeQuote
    """
    code: str
    name: str = ""
    price: float = 0.0           # latest price
    change_pct: float = 0.0      # Increase or decrease(%)
    change_amount: float = 0.0   # Changes
    
    # Avoid duplicate requests
    volume: int = 0              # Volume
    amount: float = 0.0          # Turnover
    turnover_rate: float = 0.0   # turnover rate(%)
    amplitude: float = 0.0       # amplitude(%)
    
    # Avoid duplicate requests
    high: float = 0.0            # highest price
    low: float = 0.0             # lowest price
    open_price: float = 0.0      # opening price
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'code': self.code,
            'name': self.name,
            'price': self.price,
            'change_pct': self.change_pct,
            'change_amount': self.change_amount,
            'volume': self.volume,
            'amount': self.amount,
            'turnover_rate': self.turnover_rate,
            'amplitude': self.amplitude,
            'high': self.high,
            'low': self.low,
            'open': self.open_price,
        }


logger = logging.getLogger(__name__)

EASTMONEY_HISTORY_ENDPOINT = "push2his.eastmoney.com/api/qt/stock/kline/get"


# User-Agent Avoid duplicate requests，Avoid duplicate requests
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]


# Avoid duplicate requests（Avoid duplicate requests）
# TTL set to 10 minute (600Second)：Avoid repeated pulls in batch analysis scenarios
_realtime_cache: Dict[str, Any] = {
    'data': None,
    'timestamp': 0,
    'ttl': 600  # 10-minute cache TTL
}

# ETF real-time quotation cache (cached separately from stocks)
_etf_realtime_cache: Dict[str, Any] = {
    'data': None,
    'timestamp': 0,
    'ttl': 600  # 10-minute cache TTL
}

_ETF_SH_PREFIXES = ('51', '52', '56', '58')
_ETF_SZ_PREFIXES = ('15', '16', '18')


def _is_etf_code(stock_code: str) -> bool:
    """
    Determine whether the code is ETF fund
    
    ETF code rules：
    - Shanghai Stock Exchange ETF: 51xxxx, 52xxxx, 56xxxx, 58xxxx
    - Shenzhen Stock Exchange ETF: 15xxxx, 16xxxx, 18xxxx
    
    Args:
        stock_code: stock/Fund code
        
    Returns:
        True means yes ETF code，False Indicates a common stock code
    """
    return _is_a_share_etf_code(stock_code)


def _build_eastmoney_etf_secid(stock_code: str) -> str:
    """Build Eastmoney secid for A-share ETF historical K-line queries."""
    code = normalize_stock_code(stock_code)
    if not _is_etf_code(code):
        raise DataFetchError(f"Unrecognized ETF code {stock_code}")
    if code.startswith(_ETF_SH_PREFIXES):
        return f"1.{code}"
    if code.startswith(_ETF_SZ_PREFIXES):
        return f"0.{code}"
    raise DataFetchError(f"Unable to determine ETF {stock_code} of Eastmoney market prefix")


def _is_us_code(stock_code: str) -> bool:
    """
    Determine whether the code is a US stock
    
    US stock code rules：
    - 1-5capital letters，like 'AAPL', 'TSLA'
    - may contain '.'，like 'BRK.B'
    """
    code = stock_code.strip().upper()
    return bool(re.match(r'^[A-Z]{1,5}(\.[A-Z])?$', code))


def _ef_call_with_timeout(func, *args, timeout=None, **kwargs):
    """Run an efinance library call in a thread with a timeout.

    efinance internally uses requests/urllib3 with no timeout, so when
    eastmoney hosts are unreachable the call can hang for many minutes.
    This helper caps the *calling thread's* wait time.  Note: Python threads
    cannot be forcibly killed, so the worker thread may continue running in
    the background until the OS-level TCP timeout fires or the process exits.
    This is acceptable — the calling thread returns promptly on timeout.
    """
    if timeout is None:
        timeout = _EF_CALL_TIMEOUT
    # Do NOT use 'with ThreadPoolExecutor(...)' here: the context manager calls
    # shutdown(wait=True) on __exit__, which would re-block on the hung thread.
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(func, *args, **kwargs)
        return future.result(timeout=timeout)
    finally:
        # wait=False: calling thread returns immediately; worker cleans up later
        executor.shutdown(wait=False)


def _classify_eastmoney_error(exc: Exception) -> Tuple[str, str]:
    """
    Classify Eastmoney request failures into stable log categories.
    """
    message = str(exc).strip()
    lowered = message.lower()

    remote_disconnect_keywords = (
        'remotedisconnected',
        'remote end closed connection without response',
        'connection aborted',
        'connection broken',
        'protocolerror',
    )
    timeout_keywords = (
        'timeout',
        'timed out',
        'readtimeout',
        'connecttimeout',
    )
    rate_limit_keywords = (
        'banned',
        'blocked',
        'frequency',
        'rate limit',
        'too many requests',
        '429',
        'limit',
        'forbidden',
        '403',
    )

    if any(keyword in lowered for keyword in remote_disconnect_keywords):
        return "remote_disconnect", message
    if isinstance(exc, (TimeoutError, requests.exceptions.Timeout)) or any(
        keyword in lowered for keyword in timeout_keywords
    ):
        return "timeout", message
    if any(keyword in lowered for keyword in rate_limit_keywords):
        return "rate_limit_or_anti_bot", message
    if isinstance(exc, requests.exceptions.RequestException):
        return "request_error", message
    return "unknown_request_error", message


class EfinanceFetcher(BaseFetcher):
    """
    Efinance Data source implementation
    
    priority：0（Highest，take precedence over AkshareFetcher）
    Data source：Oriental Fortune Network（pass efinance library encapsulation）
    storehouse：https://github.com/Micro-sheep/efinance
    
    main API：
    - ef.stock.get_quote_history(): Get history K line data
    - ef.stock.get_base_info(): Get basic stock information
    - ef.stock.get_realtime_quotes(): Get real-time quotes
    
    key strategies：
    - Sleep randomly before each request 1.5-3.0 Second
    - random User-Agent rotation
    - Exponential backoff retry after failure（most3Second-rate）
    """
    
    name = "EfinanceFetcher"
    priority = int(os.getenv("EFINANCE_PRIORITY", "0"))  # Highest priority, placed before AkshareFetcher
    
    def __init__(self, sleep_min: float = 1.5, sleep_max: float = 3.0):
        """
        initialization EfinanceFetcher
        
        Args:
            sleep_min: Minimum sleep time（Second）
            sleep_max: Maximum sleep time（Second）
        """
        self.sleep_min = sleep_min
        self.sleep_max = sleep_max
        self._last_request_time: Optional[float] = None
        # The patching operation will be performed only after Dongcai patch is enabled.
        if get_config().enable_eastmoney_patch:
            eastmoney_patch()

    @staticmethod
    def _build_history_failure_message(
        stock_code: str,
        beg_date: str,
        end_date: str,
        exc: Exception,
        elapsed: float,
        is_etf: bool = False,
    ) -> Tuple[str, str]:
        category, detail = _classify_eastmoney_error(exc)
        instrument_type = "ETF" if is_etf else "stock"
        message = (
            "Eastmoney historyKLine interface failed: "
            f"endpoint={EASTMONEY_HISTORY_ENDPOINT}, stock_code={stock_code}, "
            f"market_type={instrument_type}, range={beg_date}~{end_date}, "
            f"category={category}, error_type={type(exc).__name__}, elapsed={elapsed:.2f}s, detail={detail}"
        )
        return category, message

    def _set_random_user_agent(self) -> None:
        """
        by modifying User-Agent
        
        by modifying requests Session of headers accomplish
        This is one of the key anti-crawling strategies
        """
        try:
            random_ua = random.choice(USER_AGENTS)
            logger.debug(f"set up User-Agent: {random_ua[:50]}...")
        except Exception as e:
            logger.debug(f"set up User-Agent fail: {e}")
    
    def _enforce_rate_limit(self) -> None:
        """
        Enforce rate limits
        
        Strategy：
        1. Check the time interval since the last request
        2. If the interval is insufficient，Supplementary sleep time
        3. Then perform random jitter hibernate
        """
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            min_interval = self.sleep_min
            if elapsed < min_interval:
                additional_sleep = min_interval - elapsed
                logger.debug(f"Does not support US stocks {additional_sleep:.2f} Second")
                time.sleep(additional_sleep)
        
        # perform random jitter hibernate
        self.random_sleep(self.sleep_min, self.sleep_max)
        self._last_request_time = time.time()
    
    @retry(
        stop=stop_after_attempt(1),  # Reduced to 1 retry to avoid triggering rate limits
        wait=wait_exponential(multiplier=1, min=4, max=60),  # Keep wait time settings
        retry=retry_if_exception_type((
            ConnectionError,
            TimeoutError,
            requests.exceptions.RequestException,
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        from efinance Get raw data
        
        Automatic selection based on tag type API：
        - US stocks：Not supported，throw exception let DataFetcherManager Switch to another data source
        - common stock：use ef.stock.get_quote_history()
        - ETF fund：use ef.stock.get_quote_history()（ETF is an exchange security，Use stocks K Line interface）
        
        process：
        1. Determine code type（US stocks/stock/ETF）
        2. by modifying User-Agent
        3. Enforce rate limiting（Random sleep）
        4. Call the corresponding efinance API
        5. Processing returned data
        """
        # US stocks do not support，throw exception let DataFetcherManager switch to AkshareFetcher/YfinanceFetcher
        if _is_us_code(stock_code):
            raise DataFetchError(f"EfinanceFetcher Does not support US stocks {stock_code}，Please use AkshareFetcher or YfinanceFetcher")

        # efinance history K The online interface may return unexpected market data on Hong Kong stock codes.，
        # Explicitly skip and hand over to AkShare/Tushare/YFinance/Longbridge Waiting for the Hong Kong stock market to bottom out。
        if _is_hk_market(stock_code):
            raise DataFetchError(f"EfinanceFetcher Does not support Hong Kong stock daily line {stock_code}，Please use AkshareFetcher or other Hong Kong stock data sources")
        
        # Choose different acquisition methods based on code type
        if _is_etf_code(stock_code):
            return self._fetch_etf_data(stock_code, start_date, end_date)
        else:
            return self._fetch_stock_data(stock_code, start_date, end_date)
    
    def _fetch_stock_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        get normal A stock historical data
        
        Data source：ef.stock.get_quote_history()
        
        API Parameter description：
        - stock_codes: Stock code
        - beg: start date，Format 'YYYYMMDD'
        - end: end date，Format 'YYYYMMDD'
        - klt: cycle，101=daily line
        - fqt: Restoration method，1=Former restoration of rights
        """
        import efinance as ef
        
        # Anti-ban strategy 1: random User-Agent
        self._set_random_user_agent()
        
        # Anti-ban strategy 2: Forced sleep
        self._enforce_rate_limit()
        
        # use（efinance use YYYYMMDD Format）
        beg_date = start_date.replace('-', '')
        end_date_fmt = end_date.replace('-', '')
        
        logger.info(f"[APIcall] ef.stock.get_quote_history(stock_codes={stock_code}, "
                   f"beg={beg_date}, end={end_date_fmt}, klt=101, fqt=1)")
        
        api_start = time.time()
        try:
            # call efinance get A Stock daily data
            # klt=101 Get daily data
            # fqt=1 Obtain pre-reinstatement data
            df = _ef_call_with_timeout(
                ef.stock.get_quote_history,
                stock_codes=stock_code,
                beg=beg_date,
                end=end_date_fmt,
                klt=101,  # daily line
                fqt=1,    # Former restoration of rights
                timeout=60,
            )
            
            api_elapsed = time.time() - api_start
            
            # Record return data summary
            if df is not None and not df.empty:
                logger.info(
                    "[APIreturn] Eastmoney historyKline success: "
                    f"endpoint={EASTMONEY_HISTORY_ENDPOINT}, stock_code={stock_code}, "
                    f"range={beg_date}~{end_date_fmt}, rows={len(df)}, elapsed={api_elapsed:.2f}s"
                )
                logger.info(f"[APIreturn] List: {list(df.columns)}")
                if '日期' in df.columns:
                    logger.info(f"[APIreturn] date range: {df['日期'].iloc[0]} ~ {df['日期'].iloc[-1]}")
                logger.debug(f"[APIreturn] Latest 3 rows of data:\n{df.tail(3).to_string()}")
            else:
                logger.warning(
                    "[APIreturn] Eastmoney historyKLine is empty: "
                    f"endpoint={EASTMONEY_HISTORY_ENDPOINT}, stock_code={stock_code}, "
                    f"range={beg_date}~{end_date_fmt}, elapsed={api_elapsed:.2f}s"
                )
            
            return df
            
        except Exception as e:
            api_elapsed = time.time() - api_start
            category, failure_message = self._build_history_failure_message(
                stock_code=stock_code,
                beg_date=beg_date,
                end_date=end_date_fmt,
                exc=e,
                elapsed=api_elapsed,
            )

            if category == "rate_limit_or_anti_bot":
                logger.warning(failure_message)
                raise RateLimitError(f"efinance may be rate-limited: {failure_message}") from e

            logger.error(failure_message)
            raise DataFetchError(f"efinance failed to get data: {failure_message}") from e
    
    def _fetch_etf_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        get ETF Fund historical data

        Exchange-traded ETFs have OHLCV data just like regular stocks, so we use
        ef.stock.get_quote_history (the stock K-line API) which returns full
        open/high/low/close/volume data.

        Previously this method used ef.fund.get_quote_history which only returns
        NAV data (net unit value/Cumulative net worth) without volume or OHLC, causing:
        - Issue #541: 'got an unexpected keyword argument beg'
        - Issue #527: ETF volume/turnover always showing 0

        Args:
            stock_code: ETF code, e.g. '512400', '159883', '515120'
            start_date: Start date, format 'YYYY-MM-DD'
            end_date: End date, format 'YYYY-MM-DD'

        Returns:
            ETF historical OHLCV DataFrame
        """
        import efinance as ef

        # Anti-ban strategy 1: random User-Agent
        self._set_random_user_agent()

        # Anti-ban strategy 2: enforce rate limit
        self._enforce_rate_limit()

        # Format dates (efinance uses YYYYMMDD)
        beg_date = start_date.replace('-', '')
        end_date_fmt = end_date.replace('-', '')
        secid = _build_eastmoney_etf_secid(stock_code)

        logger.info(
            f"[APIcall] ef.stock.get_quote_history(stock_codes={secid}, "
            f"beg={beg_date}, end={end_date_fmt}, klt=101, fqt=1, "
            f"quote_id_mode=True, use_id_cache=False)  [ETF stock_code={stock_code}]"
        )

        api_start = time.time()
        try:
            # ETFs are exchange-traded securities; use the stock API to get full OHLCV data
            df = _ef_call_with_timeout(
                ef.stock.get_quote_history,
                stock_codes=secid,
                beg=beg_date,
                end=end_date_fmt,
                klt=101,  # daily
                fqt=1,    # forward-adjusted
                quote_id_mode=True,
                use_id_cache=False,
                timeout=60,
            )

            api_elapsed = time.time() - api_start

            if df is not None and not df.empty:
                logger.info(
                    "[APIreturn] Eastmoney historyKline success [ETF]: "
                    f"endpoint={EASTMONEY_HISTORY_ENDPOINT}, stock_code={stock_code}, secid={secid}, "
                    f"range={beg_date}~{end_date_fmt}, rows={len(df)}, elapsed={api_elapsed:.2f}s"
                )
                logger.info(f"[APIreturn] List: {list(df.columns)}")
                if '日期' in df.columns:
                    logger.info(f"[APIreturn] date range: {df['日期'].iloc[0]} ~ {df['日期'].iloc[-1]}")
                logger.debug(f"[APIreturn] up to date3piece of data:\n{df.tail(3).to_string()}")
            else:
                logger.warning(
                    "[APIreturn] Eastmoney historyKLine is empty [ETF]: "
                    f"endpoint={EASTMONEY_HISTORY_ENDPOINT}, stock_code={stock_code}, secid={secid}, "
                    f"range={beg_date}~{end_date_fmt}, elapsed={api_elapsed:.2f}s"
                )

            return df

        except Exception as e:
            api_elapsed = time.time() - api_start
            category, failure_message = self._build_history_failure_message(
                stock_code=stock_code,
                beg_date=beg_date,
                end_date=end_date_fmt,
                exc=e,
                elapsed=api_elapsed,
                is_etf=True,
            )

            if category == "rate_limit_or_anti_bot":
                logger.warning(failure_message)
                raise RateLimitError(f"efinance May be restricted: {failure_message}") from e

            logger.error(failure_message)
            raise DataFetchError(f"efinance get ETF Data failed: {failure_message}") from e
    
    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        standardization efinance data
        
        efinance Returned column names（Chinese）：
        Stock name, Stock code, date, opening, close, Highest, lowest, Volume, Turnover, amplitude, Increase or decrease, Changes, turnover rate
        
        Need to be mapped to standard column names：
        date, open, high, low, close, volume, amount, pct_chg
        """
        df = df.copy()
        
        # Column mapping (efinance Chinese column names -> standard English column names)
        column_mapping = {
            'date': 'date',
            'opening': 'open',
            'close': 'close',
            'Highest': 'high',
            'lowest': 'low',
            'Volume': 'volume',
            'Turnover': 'amount',
            'Increase or decrease': 'pct_chg',
            'Stock code': 'code',
            'Stock name': 'name',
        }
        
        # Rename columns
        df = df.rename(columns=column_mapping)
        
        # Fallback: if OHLC columns are missing (e.g. very old data path), fill from close
        if 'close' in df.columns and 'open' not in df.columns:
            df['open'] = df['close']
            df['high'] = df['close']
            df['low'] = df['close']
            
        # Fill volume and amount if missing
        if 'volume' not in df.columns:
            df['volume'] = 0
        if 'amount' not in df.columns:
            df['amount'] = 0

        
        # if not code List，Add manually
        if 'code' not in df.columns:
            df['code'] = stock_code
        
        # Keep only the columns you need
        keep_cols = ['code'] + STANDARD_COLUMNS
        existing_cols = [col for col in keep_cols if col in df.columns]
        df = df[existing_cols]
        
        return df
    
    def get_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """
        Get real-time market data
        
        Data source：ef.stock.get_realtime_quotes()
        ETF data source：ef.stock.get_realtime_quotes(['ETF'])
        
        Args:
            stock_code: Stock code
            
        Returns:
            UnifiedRealtimeQuote object，Return on failure to obtain None
        """
        # ETF Requires separate request ETF Real-time market interface
        if _is_etf_code(stock_code):
            return self._get_etf_realtime_quote(stock_code)

        import efinance as ef
        circuit_breaker = get_realtime_circuit_breaker()
        source_key = "efinance"
        
        # Check fuse status
        if not circuit_breaker.is_available(source_key):
            logger.info(f"[fuse] data source {source_key} in fuse state，jump over")
            return None
        
        try:
            # Check cache
            current_time = time.time()
            if (_realtime_cache['data'] is not None and 
                current_time - _realtime_cache['timestamp'] < _realtime_cache['ttl']):
                df = _realtime_cache['data']
                cache_age = int(current_time - _realtime_cache['timestamp'])
                logger.debug(f"[cache hit] Real-time quotes(efinance) - cache age {cache_age}s/{_realtime_cache['ttl']}s")
            else:
                # real-time quotes
                logger.info(f"[success] real-time quotes Real-time quotes(efinance)")
                # Anti-ban strategy
                self._set_random_user_agent()
                self._enforce_rate_limit()
                
                logger.info(f"[APIcall] ef.stock.get_realtime_quotes() Get real-time quotes...")
                import time as _time
                api_start = _time.time()
                
                # efinance real-time quotes API (with timeout to avoid indefinite hangs)
                df = _ef_call_with_timeout(ef.stock.get_realtime_quotes)
                
                api_elapsed = _time.time() - api_start
                logger.info(f"[APIreturn] ef.stock.get_realtime_quotes success: return {len(df)} only stocks, time consuming {api_elapsed:.2f}s")
                circuit_breaker.record_success(source_key)
                
                # Update cache
                _realtime_cache['data'] = df
                _realtime_cache['timestamp'] = current_time
                logger.info(f"[cache updates] Real-time quotes(efinance) cache flushed，TTL={_realtime_cache['ttl']}s")
            
            # Find specific stocks
            # efinance The returned column names may be 'Stock code' or 'code'
            code_col = '股票代码' if '股票代码' in df.columns else 'code'
            row = df[df[code_col] == stock_code]
            if row.empty:
                logger.info(f"[APIreturn] No stock found {stock_code} real-time quotes")
                return None
            
            row = row.iloc[0]
            
            # use realtime_types.py Unified conversion function in
            # Get column names（May be Chinese or English）
            name_col = '股票名称' if '股票名称' in df.columns else 'name'
            price_col = '最新价' if '最新价' in df.columns else 'price'
            pct_col = '涨跌幅' if '涨跌幅' in df.columns else 'pct_chg'
            chg_col = '涨跌额' if '涨跌额' in df.columns else 'change'
            vol_col = '成交量' if '成交量' in df.columns else 'volume'
            amt_col = '成交额' if '成交额' in df.columns else 'amount'
            turn_col = '换手率' if '换手率' in df.columns else 'turnover_rate'
            amp_col = '振幅' if '振幅' in df.columns else 'amplitude'
            high_col = '最高' if '最高' in df.columns else 'high'
            low_col = '最低' if '最低' in df.columns else 'low'
            open_col = '开盘' if '开盘' in df.columns else 'open'
            # efinance Also returns the quantity ratio、P/E ratio、Market value and other fields
            vol_ratio_col = '量比' if '量比' in df.columns else 'volume_ratio'
            pe_col = '市盈率' if '市盈率' in df.columns else 'pe_ratio'
            total_mv_col = '总市值' if '总市值' in df.columns else 'total_mv'
            circ_mv_col = '流通市值' if '流通市值' in df.columns else 'circ_mv'
            
            quote = UnifiedRealtimeQuote(
                code=stock_code,
                name=str(row.get(name_col, '')),
                source=RealtimeSource.EFINANCE,
                price=safe_float(row.get(price_col)),
                change_pct=safe_float(row.get(pct_col)),
                change_amount=safe_float(row.get(chg_col)),
                volume=safe_int(row.get(vol_col)),
                amount=safe_float(row.get(amt_col)),
                turnover_rate=safe_float(row.get(turn_col)),
                amplitude=safe_float(row.get(amp_col)),
                high=safe_float(row.get(high_col)),
                low=safe_float(row.get(low_col)),
                open_price=safe_float(row.get(open_col)),
                volume_ratio=safe_float(row.get(vol_ratio_col)),  # Quantity ratio
                pe_ratio=safe_float(row.get(pe_col)),  # P/E ratio
                total_mv=safe_float(row.get(total_mv_col)),  # total market capitalization
                circ_mv=safe_float(row.get(circ_mv_col)),  # Circulation market value
            )
            
            logger.info(f"[Real-time quotes-efinance] {stock_code} {quote.name}: price={quote.price}, ups and downs={quote.change_pct}%, "
                       f"Quantity ratio={quote.volume_ratio}, turnover rate={quote.turnover_rate}%")
            return quote
            
        except FuturesTimeoutError:
            logger.info(f"[time out] ef.stock.get_realtime_quotes() Exceed {_EF_CALL_TIMEOUT}s，jump over {stock_code}")
            circuit_breaker.record_failure(source_key, "timeout")
            return None
        except Exception as e:
            logger.info(f"[APImistake] get {stock_code} Real-time quotes(efinance)fail: {e}")
            circuit_breaker.record_failure(source_key, str(e))
            return None

    def _get_etf_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """
        get ETF Real-time quotes

        efinance The default real-time interface only returns stock data，ETF Need to be passed in explicitly ['ETF']。
        """
        import efinance as ef
        circuit_breaker = get_realtime_circuit_breaker()
        source_key = "efinance_etf"

        if not circuit_breaker.is_available(source_key):
            logger.info(f"[fuse] data source {source_key} in fuse state，jump over")
            return None

        try:
            current_time = time.time()
            if (
                _etf_realtime_cache['data'] is not None and
                current_time - _etf_realtime_cache['timestamp'] < _etf_realtime_cache['ttl']
            ):
                df = _etf_realtime_cache['data']
                cache_age = int(current_time - _etf_realtime_cache['timestamp'])
                logger.debug(f"[cache hit] ETFReal-time quotes(efinance) - cache age {cache_age}s/{_etf_realtime_cache['ttl']}s")
            else:
                self._set_random_user_agent()
                self._enforce_rate_limit()

                logger.info("[APIcall] ef.stock.get_realtime_quotes(['ETF']) getETFReal-time quotes...")
                import time as _time
                api_start = _time.time()
                df = _ef_call_with_timeout(ef.stock.get_realtime_quotes, ['ETF'])
                api_elapsed = _time.time() - api_start

                if df is not None and not df.empty:
                    logger.info(f"[APIreturn] ETF Real-time market success: {len(df)} strip, time consuming {api_elapsed:.2f}s")
                    circuit_breaker.record_success(source_key)
                else:
                    logger.info(f"[APIreturn] ETF Real-time market data is empty, time consuming {api_elapsed:.2f}s")
                    df = pd.DataFrame()

                _etf_realtime_cache['data'] = df
                _etf_realtime_cache['timestamp'] = current_time

            if df is None or df.empty:
                logger.info(f"[Real-time quotes] ETFReal-time market data is empty(efinance)，jump over {stock_code}")
                return None

            code_col = '股票代码' if '股票代码' in df.columns else 'code'
            code_series = df[code_col].astype(str).str.zfill(6)
            target_code = str(stock_code).strip().zfill(6)
            row = df[code_series == target_code]
            if row.empty:
                logger.info(f"[APIreturn] not found ETF {stock_code} real-time quotes(efinance)")
                return None

            row = row.iloc[0]
            name_col = '股票名称' if '股票名称' in df.columns else 'name'
            price_col = '最新价' if '最新价' in df.columns else 'price'
            pct_col = '涨跌幅' if '涨跌幅' in df.columns else 'pct_chg'
            chg_col = '涨跌额' if '涨跌额' in df.columns else 'change'
            vol_col = '成交量' if '成交量' in df.columns else 'volume'
            amt_col = '成交额' if '成交额' in df.columns else 'amount'
            turn_col = '换手率' if '换手率' in df.columns else 'turnover_rate'
            amp_col = '振幅' if '振幅' in df.columns else 'amplitude'
            high_col = '最高' if '最高' in df.columns else 'high'
            low_col = '最低' if '最低' in df.columns else 'low'
            open_col = '开盘' if '开盘' in df.columns else 'open'

            quote = UnifiedRealtimeQuote(
                code=target_code,
                name=str(row.get(name_col, '')),
                source=RealtimeSource.EFINANCE,
                price=safe_float(row.get(price_col)),
                change_pct=safe_float(row.get(pct_col)),
                change_amount=safe_float(row.get(chg_col)),
                volume=safe_int(row.get(vol_col)),
                amount=safe_float(row.get(amt_col)),
                turnover_rate=safe_float(row.get(turn_col)),
                amplitude=safe_float(row.get(amp_col)),
                high=safe_float(row.get(high_col)),
                low=safe_float(row.get(low_col)),
                open_price=safe_float(row.get(open_col)),
            )

            logger.info(
                f"[ETFReal-time quotes-efinance] {target_code} {quote.name}: "
                f"price={quote.price}, ups and downs={quote.change_pct}%, turnover rate={quote.turnover_rate}%"
            )
            return quote
        except Exception as e:
            logger.info(f"[APImistake] get ETF {stock_code} Real-time quotes(efinance)fail: {e}")
            circuit_breaker.record_failure(source_key, str(e))
            return None

    def get_main_indices(self, region: str = "cn") -> Optional[List[Dict[str, Any]]]:
        """
        Get real-time quotes of major indices (efinance)，Only supports A share
        """
        if region != "cn":
            return None
        import efinance as ef

        indices_map = {
            '000001': ('Shanghai Composite Index', 'sh000001'),
            '399001': ('Shenzhen Component Index', 'sz399001'),
            '399006': ('GEM Index', 'sz399006'),
            '000688': ('Science and Technology50', 'sh000688'),
            '000016': ('Shanghai Stock Exchange50', 'sh000016'),
            '000300': ('Shanghai and Shenzhen300', 'sh000300'),
        }

        try:
            self._set_random_user_agent()
            self._enforce_rate_limit()

            logger.info("[APIcall] ef.stock.get_realtime_quotes(['Shanghai and Shenzhen Series Index']) Get index quotes...")
            import time as _time
            api_start = _time.time()
            df = _ef_call_with_timeout(ef.stock.get_realtime_quotes, ['沪深系列指数'])
            api_elapsed = _time.time() - api_start

            if df is None or df.empty:
                logger.warning(f"[APIreturn] Index market is empty, time consuming {api_elapsed:.2f}s")
                return None

            logger.info(f"[APIreturn] Index market success: {len(df)} strip, time consuming {api_elapsed:.2f}s")
            code_col = '股票代码' if '股票代码' in df.columns else 'code'
            code_series = df[code_col].astype(str).str.zfill(6)

            results: List[Dict[str, Any]] = []
            for code, (name, full_code) in indices_map.items():
                row = df[code_series == code]
                if row.empty:
                    continue
                item = row.iloc[0]

                price_col = '最新价' if '最新价' in df.columns else 'price'
                pct_col = '涨跌幅' if '涨跌幅' in df.columns else 'pct_chg'
                chg_col = '涨跌额' if '涨跌额' in df.columns else 'change'
                open_cols = [column for column in ('今开', '开盘', 'open') if column in df.columns]
                high_col = '最高' if '最高' in df.columns else 'high'
                low_col = '最低' if '最低' in df.columns else 'low'
                vol_col = '成交量' if '成交量' in df.columns else 'volume'
                amt_col = '成交额' if '成交额' in df.columns else 'amount'
                amp_col = '振幅' if '振幅' in df.columns else 'amplitude'

                current = safe_float(item.get(price_col, 0))
                change_amount = safe_float(item.get(chg_col, 0))
                open_price = 0.0
                for column in open_cols:
                    candidate = safe_float(item.get(column), default=None)
                    if candidate not in (None, 0.0):
                        open_price = candidate
                        break
                if open_price == 0.0 and open_cols:
                    open_price = safe_float(item.get(open_cols[0], 0), 0)

                results.append({
                    'code': full_code,
                    'name': name,
                    'current': current,
                    'change': change_amount,
                    'change_pct': safe_float(item.get(pct_col, 0)),
                    'open': open_price,
                    'high': safe_float(item.get(high_col, 0)),
                    'low': safe_float(item.get(low_col, 0)),
                    'prev_close': current - change_amount if current or change_amount else 0,
                    'volume': safe_float(item.get(vol_col, 0)),
                    'amount': safe_float(item.get(amt_col, 0)),
                    'amplitude': safe_float(item.get(amp_col, 0)),
                })

            if results:
                logger.info(f"[efinance] Get {len(results)} index quotes")
            return results if results else None
        except Exception as e:
            logger.error(f"[efinance] Failed to obtain index quotes: {e}")
            return None

    def get_market_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get market rise and fall statistics (efinance)
        """
        import efinance as ef

        try:
            self._set_random_user_agent()
            self._enforce_rate_limit()

            current_time = time.time()
            if (
                _realtime_cache['data'] is not None and
                current_time - _realtime_cache['timestamp'] < _realtime_cache['ttl']
            ):
                df = _realtime_cache['data']
                logger.info(
                    "[MarketStats] component=market_stats provider=EfinanceFetcher "
                    "api=ef.stock.get_realtime_quotes action=cache_hit cache_age=%.0fs",
                    current_time - _realtime_cache['timestamp'],
                )
            else:
                started_at = time.monotonic()
                logger.info(
                    "[MarketStats] component=market_stats provider=EfinanceFetcher "
                    "api=ef.stock.get_realtime_quotes action=request_start"
                )
                df = _ef_call_with_timeout(ef.stock.get_realtime_quotes)
                elapsed = time.monotonic() - started_at
                logger.info(
                    "[MarketStats] component=market_stats provider=EfinanceFetcher "
                    "api=ef.stock.get_realtime_quotes action=request_complete elapsed=%.2fs",
                    elapsed,
                )
                _realtime_cache['data'] = df
                _realtime_cache['timestamp'] = current_time

            if df is None or df.empty:
                logger.warning(
                    "[MarketStats] component=market_stats provider=EfinanceFetcher "
                    "api=ef.stock.get_realtime_quotes action=parse status=empty"
                )
                return None

            return self._calc_market_stats(df)
        except Exception as e:
            logger.error(
                "[MarketStats] component=market_stats provider=EfinanceFetcher "
                "api=ef.stock.get_realtime_quotes action=failed error=%s",
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

            # A. Determine the rise and fall ratio of each stock (Use pure numeric codes to determine)
            if is_bse_code(pure_code): 
                ratio = 0.30
            elif is_kc_cy_stock(pure_code): #pure_code.startswith(('688', '30')):
                ratio = 0.20
            elif is_st_stock(name): #'ST' in str_name:
                ratio = 0.05
            else:
                ratio = 0.10

            # B. strictly follow A Stock rules calculate price limit：Collected yesterday * (1 ± Proportion) -> Rounding retained2decimal places
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
        Get the sector rise and fall list (efinance)
        """
        import efinance as ef

        try:
            self._set_random_user_agent()
            self._enforce_rate_limit()

            logger.info("[APIcall] ef.stock.get_realtime_quotes(['Industry sector']) Get sector quotes...")
            df = _ef_call_with_timeout(ef.stock.get_realtime_quotes, ['行业板块'])
            if df is None or df.empty:
                logger.warning("[efinance] Sector market data is empty")
                return None

            change_col = '涨跌幅' if '涨跌幅' in df.columns else 'pct_chg'
            name_col = '股票名称' if '股票名称' in df.columns else 'name'
            if change_col not in df.columns or name_col not in df.columns:
                return None

            df[change_col] = pd.to_numeric(df[change_col], errors='coerce')
            df = df.dropna(subset=[change_col])
            top = df.nlargest(n, change_col)
            bottom = df.nsmallest(n, change_col)

            top_sectors = [
                {'name': str(row[name_col]), 'change_pct': float(row[change_col])}
                for _, row in top.iterrows()
            ]
            bottom_sectors = [
                {'name': str(row[name_col]), 'change_pct': float(row[change_col])}
                for _, row in bottom.iterrows()
            ]
            return top_sectors, bottom_sectors
        except Exception as e:
            logger.error(f"[efinance] Failed to obtain section ranking: {e}")
            return None
    
    def get_base_info(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        Get basic stock information
        
        Data source：ef.stock.get_base_info()
        Include：P/E ratio、price to book ratio、Industry、total market capitalization、Circulation market value、ROE、Net interest rate, etc.
        
        Args:
            stock_code: Stock code
            
        Returns:
            Dictionary containing basic information，Return on failure to obtain None
        """
        import efinance as ef
        
        try:
            # Anti-ban strategy
            self._set_random_user_agent()
            self._enforce_rate_limit()
            
            logger.info(f"[APIcall] ef.stock.get_base_info(stock_codes={stock_code}) Get basic information...")
            import time as _time
            api_start = _time.time()
            
            info = _ef_call_with_timeout(ef.stock.get_base_info, stock_code)
            
            api_elapsed = _time.time() - api_start
            logger.info(f"[APIreturn] ef.stock.get_base_info success, time consuming {api_elapsed:.2f}s")
            
            if info is None:
                logger.warning(f"[APIreturn] Not obtained {stock_code} basic information")
                return None
            
            # Convert to dictionary
            if isinstance(info, pd.Series):
                return info.to_dict()
            elif isinstance(info, pd.DataFrame):
                if not info.empty:
                    return info.iloc[0].to_dict()
            
            return None
            
        except Exception as e:
            logger.error(f"[APImistake] get {stock_code} Basic information failed: {e}")
            return None
    
    def get_belong_board(self, stock_code: str) -> Optional[pd.DataFrame]:
        """
        Get the sector to which the stock belongs
        
        Data source：ef.stock.get_belong_board()
        
        Args:
            stock_code: Stock code
            
        Returns:
            Sector DataFrame，Return on failure to obtain None
        """
        import efinance as ef
        
        try:
            # Anti-ban strategy
            self._set_random_user_agent()
            self._enforce_rate_limit()
            
            logger.info(f"[APIcall] ef.stock.get_belong_board(stock_code={stock_code}) Get the section it belongs to...")
            import time as _time
            api_start = _time.time()
            
            df = _ef_call_with_timeout(ef.stock.get_belong_board, stock_code)
            
            api_elapsed = _time.time() - api_start
            
            if df is not None and not df.empty:
                logger.info(f"[APIreturn] ef.stock.get_belong_board success: return {len(df)} sectors, time consuming {api_elapsed:.2f}s")
                return df
            else:
                logger.warning(f"[APIreturn] Not obtained {stock_code} sector information")
                return None
            
        except FuturesTimeoutError:
            logger.warning(f"[time out] ef.stock.get_belong_board({stock_code}) Exceed {_EF_CALL_TIMEOUT}s，jump over")
            return None
        except Exception as e:
            logger.error(f"[APImistake] get {stock_code} The section to which it belongs failed: {e}")
            return None
    
    def get_enhanced_data(self, stock_code: str, days: int = 60) -> Dict[str, Any]:
        """
        Get augmented data（historyKWire + Real-time quotes + Historical data days）
        
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
            'base_info': None,
            'belong_board': None,
        }
        
        # Get daily data
        try:
            df = self.get_daily_data(stock_code, days=days)
            result['daily_data'] = df
        except Exception as e:
            logger.error(f"get {stock_code} Daily data failed: {e}")
        
        # Get real-time quotes
        result['realtime_quote'] = self.get_realtime_quote(stock_code)
        
        # Get basic information
        result['base_info'] = self.get_base_info(stock_code)
        
        # Get the section it belongs to
        result['belong_board'] = self.get_belong_board(stock_code)
        
        return result


if __name__ == "__main__":
    # test code
    logging.basicConfig(level=logging.DEBUG)
    
    fetcher = EfinanceFetcher()
    
    # Test common stocks
    print("=" * 50)
    print("Test common stock data acquisition (efinance)")
    print("=" * 50)
    try:
        df = fetcher.get_daily_data('600519')  # 茅台
        print(f"[stock] get success，common {len(df)} piece of data")
        print(df.tail())
    except Exception as e:
        print(f"[stock] Failed to obtain: {e}")
    
    # test ETF fund
    print("\n" + "=" * 50)
    print("test ETF Fund data acquisition (efinance)")
    print("=" * 50)
    try:
        df = fetcher.get_daily_data('512400')  # 有色龙头ETF
        print(f"[ETF] get success，common {len(df)} piece of data")
        print(df.tail())
    except Exception as e:
        print(f"[ETF] Failed to obtain: {e}")
    
    # Test real-time market conditions
    print("\n" + "=" * 50)
    print("Test real-time market quotation acquisition (efinance)")
    print("=" * 50)
    try:
        quote = fetcher.get_realtime_quote('600519')
        if quote:
            print(f"[Real-time quotes] {quote.name}: price={quote.price}, Increase or decrease={quote.change_pct}%")
        else:
            print("[Real-time quotes] No data obtained")
    except Exception as e:
        print(f"[Real-time quotes] Failed to obtain: {e}")
    
    # Test basic information
    print("\n" + "=" * 50)
    print("Obtain basic test information (efinance)")
    print("=" * 50)
    try:
        info = fetcher.get_base_info('600519')
        if info:
            print(f"[Historical data days] P/E ratio={info.get('市盈率(动)', 'N/A')}, price to book ratio={info.get('市净率', 'N/A')}")
        else:
            print("[Historical data days] No data obtained")
    except Exception as e:
        print(f"[Historical data days] Failed to obtain: {e}")

    # Test market statistics 
    print("\n" + "=" * 50)
    print("Testing get_market_stats (efinance)")
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
