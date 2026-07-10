# -*- coding: utf-8 -*-
"""
===================================
BaostockFetcher - Alternate data sources 2 (Priority 3)
===================================

Data source: Securities Treasure (Baostock)
Features: free, no need Token, requires explicit login/logout
Advantage: stable, no quota restrictions

Key strategies:
1. Manage bs.login() and bs.logout() lifecycle
2. Use context managers to prevent connection leaks
3. Exponential backoff retry after failure
"""

import logging
import re
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Generator

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
    STANDARD_COLUMNS,
    is_bse_code,
    normalize_stock_code,
    _is_hk_market,
)
import os

logger = logging.getLogger(__name__)


def _is_us_code(stock_code: str) -> bool:
    """
    Determine whether the code is a US stock.
    
    US stock code rules:
    - 1-5 capital letters, like 'AAPL', 'TSLA'
    - may contain '.', like 'BRK.B'
    """
    code = stock_code.strip().upper()
    return bool(re.match(r'^[A-Z]{1,5}(\.[A-Z])?$', code))


class BaostockFetcher(BaseFetcher):
    """
    Baostock data source implementation.
    
    priority: 3
    Data source: Securities Treasure Baostock API
    
    Key strategies:
    - Use context managers to manage connection lifecycle
    - Re-login for every request/logout, lightweight
    - Exponential backoff retry after failure
    
    Baostock features:
    - free, no registration required
    - Requires explicit login/logout
    - Data updates are slightly delayed (T+1)
    """
    
    name = "BaostockFetcher"
    priority = int(os.getenv("BAOSTOCK_PRIORITY", "3"))
    
    def __init__(self):
        """Initialize BaostockFetcher."""
        self._bs_module = None
    
    def _get_baostock(self):
        """
        Lazy-load baostock module.
        
        Import only on first use to avoid errors when not installed.
        """
        if self._bs_module is None:
            import baostock as bs
            self._bs_module = bs
        return self._bs_module
    
    @contextmanager
    def _baostock_session(self) -> Generator:
        """
        Baostock connection context manager.
        
        Ensures:
        1. Automatically log in when entering context
        2. Automatically log out when exiting context
        3. Proper cleanup even on exceptions
        
        Usage example:
            with self._baostock_session():
                # lightweight code
        """
        bs = self._get_baostock()
        login_result = None
        
        try:
            # Login to Baostock
            login_result = bs.login()
            
            if login_result.error_code != '0':
                raise DataFetchError(f"Baostock login failed: {login_result.error_msg}")
            
            logger.debug("Baostock login successful")
            
            yield bs
            
        finally:
            # Logout, cleanup
            try:
                logout_result = bs.logout()
                if logout_result.error_code == '0':
                    logger.debug("Baostock logout successful")
                else:
                    logger.warning(f"Baostock logout exception: {logout_result.error_msg}")
            except Exception as e:
                logger.warning(f"Baostock error while logging out: {e}")
    
    def _convert_stock_code(self, stock_code: str) -> str:
        """
        Convert stock symbol to Baostock format.
        
        Baostock required format:
        - Shanghai Stock Exchange: sh.600519
        - Shenzhen Stock Exchange: sz.000001
        
        Args:
            stock_code: original code, like '600519', '000001'
            
        Returns:
            Baostock format code, like 'sh.600519', 'sz.000001'
        """
        raw_code = stock_code.strip()
        upper = raw_code.upper()

        # HK stocks are not supported by Baostock
        if _is_hk_market(raw_code):
            raise DataFetchError(f"BaostockFetcher does not support {raw_code}, please use AkshareFetcher")

        # Check for already-formatted baostock codes (e.g. sh.600519, sz.000001)
        if raw_code.startswith(('sh.', 'sz.')):
            return raw_code.lower()

        exchange_hint = None
        if upper.startswith(('SH', 'SS')) or upper.endswith(('.SH', '.SS')):
            exchange_hint = 'sh'
        elif upper.startswith('SZ') or upper.endswith('.SZ'):
            exchange_hint = 'sz'

        code = normalize_stock_code(raw_code)

        if exchange_hint in ('sh', 'sz') and code.isdigit() and len(code) == 6:
            return f"{exchange_hint}.{code}"
        
        # ETF: Shanghai ETF (51xx, 52xx, 56xx, 58xx) -> sh; Shenzhen ETF (15xx, 16xx, 18xx) -> sz
        if len(code) == 6:
            if code.startswith(('51', '52', '56', '58')):
                return f"sh.{code}"
            if code.startswith(('15', '16', '18')):
                return f"sz.{code}"

        # Determine the market based on code prefix
        if code.startswith(('600', '601', '603', '605', '688')):
            return f"sh.{code}"
        elif code.startswith(('000', '001', '002', '003', '300', '301')):
            return f"sz.{code}"
        else:
            logger.warning(f"Unable to determine stock {code} market, defaulting to Shenzhen")
            return f"sz.{code}"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch raw data from Baostock.
        
        Uses query_history_k_data_plus() to get daily data.
        
        Process:
        1. Check if it is a US stock (not supported)
        2. Use context managers to manage connections
        3. Convert stock symbol format
        4. Call API to query data
        5. Convert the result to DataFrame
        """
        # US stocks not supported
        if _is_us_code(stock_code):
            raise DataFetchError(f"BaostockFetcher does not support US stocks {stock_code}, please use AkshareFetcher or YfinanceFetcher")

        # Hong Kong stocks not supported
        if _is_hk_market(stock_code):
            raise DataFetchError(f"BaostockFetcher does not support {stock_code}, please use AkshareFetcher")

        # Beijing Exchange not supported
        if is_bse_code(stock_code):
            raise DataFetchError(
                f"BaostockFetcher does not support Beijing Exchange {stock_code}, will automatically switch to other data sources"
            )
        
        # Convert code format
        bs_code = self._convert_stock_code(stock_code)
        
        logger.debug(f"call Baostock query_history_k_data_plus({bs_code}, {start_date}, {end_date})")
        
        with self._baostock_session() as bs:
            try:
                # Query daily data
                # adjustflag: 1=post-adjustment, 2=pre-adjustment, 3=no adjustment
                rs = bs.query_history_k_data_plus(
                    code=bs_code,
                    fields="date,open,high,low,close,volume,amount,pctChg",
                    start_date=start_date,
                    end_date=end_date,
                    frequency="d",  # daily
                    adjustflag="2"  # pre-adjustment
                )
                
                if rs.error_code != '0':
                    raise DataFetchError(f"Baostock Query failed: {rs.error_msg}")
                
                # Convert to DataFrame
                data_list = []
                while rs.next():
                    data_list.append(rs.get_row_data())
                
                if not data_list:
                    raise DataFetchError(f"Baostock Not found {stock_code} data")
                
                df = pd.DataFrame(data_list, columns=rs.fields)
                
                return df
                
            except Exception as e:
                if isinstance(e, DataFetchError):
                    raise
                raise DataFetchError(f"Baostock Failed to get data: {e}") from e
    
    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        Normalize Baostock data.
        
        Baostock returned column names:
        date, open, high, low, close, volume, amount, pctChg
        
        Need to map to standard column names:
        date, open, high, low, close, volume, amount, pct_chg
        """
        df = df.copy()
        
        # Column name mapping (just need to handle pctChg)
        column_mapping = {
            'pctChg': 'pct_chg',
        }
        
        df = df.rename(columns=column_mapping)
        
        # All returned values are strings (Baostock returns all as strings)
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Add stock symbol column
        df['code'] = stock_code
        
        # Keep only the columns you need
        keep_cols = ['code'] + STANDARD_COLUMNS
        existing_cols = [col for col in keep_cols if col in df.columns]
        df = df[existing_cols]
        
        return df

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        """
        Get stock name.
        
        Uses Baostock's query_stock_basic interface to obtain basic stock information.
        
        Args:
            stock_code: Stock code
            
        Returns:
            Stock name, or None on failure
        """
        # Check cache
        if hasattr(self, '_stock_name_cache') and stock_code in self._stock_name_cache:
            return self._stock_name_cache[stock_code]
        
        # Initialize cache
        if not hasattr(self, '_stock_name_cache'):
            self._stock_name_cache = {}
        
        try:
            bs_code = self._convert_stock_code(stock_code)
            
            with self._baostock_session() as bs:
                # Query basic stock information
                rs = bs.query_stock_basic(code=bs_code)
                
                if rs.error_code == '0':
                    data_list = []
                    while rs.next():
                        data_list.append(rs.get_row_data())
                    
                    if data_list:
                        # Baostock returned fields: code, code_name, ipoDate, outDate, type, status
                        fields = rs.fields
                        name_idx = fields.index('code_name') if 'code_name' in fields else None
                        if name_idx is not None and len(data_list[0]) > name_idx:
                            name = data_list[0][name_idx]
                            self._stock_name_cache[stock_code] = name
                            logger.debug(f"Baostock stock name retrieved: {stock_code} -> {name}")
                            return name
                
        except Exception as e:
            logger.warning(f"Baostock Failed to get stock name {stock_code}: {e}")
        
        return None
    
    def get_stock_list(self) -> Optional[pd.DataFrame]:
        """
        Interface to obtain the list of all stocks.
        
        Uses Baostock's query_stock_basic interface to obtain the list of all stocks.
        
        Returns:
            DataFrame containing code and name columns, or None on failure
        """
        try:
            with self._baostock_session() as bs:
                # Remove
                rs = bs.query_stock_basic()
                
                if rs.error_code == '0':
                    data_list = []
                    while rs.next():
                        data_list.append(rs.get_row_data())
                    
                    if data_list:
                        df = pd.DataFrame(data_list, columns=rs.fields)
                        
                        # Convert code format (remove sh. or sz. prefix)
                        df['code'] = df['code'].apply(lambda x: x.split('.')[1] if '.' in x else x)
                        df = df.rename(columns={'code_name': 'name'})
                        
                        # Update cache
                        if not hasattr(self, '_stock_name_cache'):
                            self._stock_name_cache = {}
                        for _, row in df.iterrows():
                            self._stock_name_cache[row['code']] = row['name']
                        
                        logger.info(f"Baostock stock list retrieved: {len(df)} entries")
                        return df[['code', 'name']]
                
        except Exception as e:
            logger.warning(f"Baostock get_stock_list failed: {e}")
        
        return None


if __name__ == "__main__":
    # test code
    logging.basicConfig(level=logging.DEBUG)
    
    fetcher = BaostockFetcher()
    
    try:
        # Test stock data
        df = fetcher.get_daily_data('600519')  # Moutai
        print(f"get success, total {len(df)} rows of data")
        print(df.tail())
        
        # Test stock name
        name = fetcher.get_stock_name('600519')
        print(f"Stock name: {name}")
        
    except Exception as e:
        print(f"Failed to obtain: {e}")
