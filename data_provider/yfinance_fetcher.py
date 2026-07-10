# -*- coding: utf-8 -*-
"""
===================================
YfinanceFetcher - Data source (Priority 4)
===================================

Data source：Yahoo Finance（pass yfinance Library）
Features：international data sources、There may be delays or missing
position：A last resort when all domestic data sources fail

key strategies：
1. automatically A The stock code is converted to yfinance Format（.SS / .SZ）
2. deal with Yahoo Finance Data format differences
3. Exponential backoff retry after failure
"""

import csv
import logging
from datetime import datetime
from io import StringIO
from typing import Optional, List, Dict, Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from .base import BaseFetcher, DataFetchError, STANDARD_COLUMNS, is_bse_code
from .realtime_types import UnifiedRealtimeQuote, RealtimeSource
from .us_index_mapping import get_us_index_yf_symbol, is_us_stock_code
from src.services.market_symbol_utils import get_suffix_market, is_suffix_market_symbol

# like，capital letters
try:
    from src.data.stock_mapping import STOCK_NAME_MAP, is_meaningful_stock_name
except (ImportError, ModuleNotFoundError):
    STOCK_NAME_MAP = {}

    def is_meaningful_stock_name(name: str | None, stock_code: str) -> bool:
        """Simple name validity check"""
        if not name:
            return False
        n = str(name).strip()
        return bool(n and n.upper() != str(stock_code).strip().upper())

import os

logger = logging.getLogger(__name__)


class YfinanceFetcher(BaseFetcher):
    """
    Yahoo Finance Data source implementation

    priority：4（lowest，as a cover）
    Data source：Yahoo Finance

    key strategies：
    - Automatically convert stock symbol formats
    - Handle time zone and data format differences
    - Exponential backoff retry after failure

    Things to note：
    - A Stock data may be delayed
    - Data may not be available for some stocks
    - Data accuracy may differ slightly from domestic sources
    """

    name = "YfinanceFetcher"
    priority = int(os.getenv("YFINANCE_PRIORITY", "4"))

    def __init__(self):
        """initialization YfinanceFetcher"""
        pass

    @staticmethod
    def _is_jp_kr_suffix_stock(stock_code: str) -> bool:
        """Return True for supported JP/KR suffix-only Yahoo symbols."""
        return is_suffix_market_symbol(stock_code, "jp") or is_suffix_market_symbol(stock_code, "kr")

    @staticmethod
    def _is_tw_suffix_stock(stock_code: str) -> bool:
        """Return True for supported Taiwan suffix-only Yahoo symbols (TWSE `.TW` / TPEx `.TWO`).

        Taiwan base codes are 4-6 digits (common stocks 4, ETFs/others up to 6,
        e.g. 00878 / 006208), wider than the JP `.T` range.
        """
        return is_suffix_market_symbol(stock_code, "tw")

    def _convert_stock_code(self, stock_code: str) -> str:
        """
        Convert stock symbol to Yahoo Finance Format

        Yahoo Finance Shenzhen stock market：
        - AShanghai stock market：600519.SS (Shanghai Stock Exchange)
        - AShenzhen stock market：000001.SZ (Shenzhen Stock Exchange)
        - Hong Kong stocks：0700.HK (Hong Kong Stock Exchange)
        - US stocks：AAPL, TSLA, GOOGL (No suffix required)

        Args:
            stock_code: original code，capital letters '600519', 'hk00700', 'AAPL'

        Returns:
            Yahoo Finance format code

        Examples:
            >>> fetcher._convert_stock_code('600519')
            '600519.SS'
            >>> fetcher._convert_stock_code('hk00700')
            '0700.HK'
            >>> fetcher._convert_stock_code('AAPL')
            'AAPL'
        """
        code = stock_code.strip().upper()

        # capital letters：capital letters Yahoo Finance capital letters（capital letters SPX -> ^GSPC）
        yf_symbol, _ = get_us_index_yf_symbol(code)
        if yf_symbol:
            logger.debug(f"Identified as US stock code: {code} -> {yf_symbol}")
            return yf_symbol

        # US stocks：1-5 capital letters（suffix .X suffix），Return as is
        if is_us_stock_code(code):
            logger.debug(f"Identified as US stock code: {code}")
            return code

        # Japanese stocks/Korean stocks/Taiwan stocks MVP：explicit Yahoo Finance suffix-only code，Pass it as is Yahoo。
        if self._is_jp_kr_suffix_stock(code) or self._is_tw_suffix_stock(code):
            logger.debug(f"Identified as Japan, Korea and Taiwan Yahoo suffix code: {code}")
            return code

        # Hong Kong stocks：hkprefix -> .HKsuffix
        if code.startswith('HK'):
            hk_code = code[2:].lstrip('0') or '0'  # Strip leading zeros but keep at least one
            hk_code = hk_code.zfill(4)  # Pad to 4 digits
            logger.debug(f"Convert Hong Kong stock code: {stock_code} -> {hk_code}.HK")
            return f"{hk_code}.HK"

        # Already contains the suffix
        if '.SS' in code or '.SZ' in code or '.HK' in code or '.BJ' in code:
            return code

        # remove possible .SH suffix
        code = code.replace('.SH', '')

        # ETF: Shanghai ETF (51xx, 52xx, 56xx, 58xx) -> .SS; Shenzhen ETF (15xx, 16xx, 18xx) -> .SZ
        if len(code) == 6:
            if code.startswith(('51', '52', '56', '58')):
                return f"{code}.SS"
            if code.startswith(('15', '16', '18')):
                return f"{code}.SZ"

        # BSE (Beijing Stock Exchange): 8xxxxx, 4xxxxx, 920xxx
        if is_bse_code(code):
            base = code.split('.')[0] if '.' in code else code
            return f"{base}.BJ"

        # Ashare：Determine the market based on code prefix
        if code.startswith(('600', '601', '603', '688')):
            return f"{code}.SS"
        elif code.startswith(('000', '002', '300')):
            return f"{code}.SZ"
        else:
            logger.warning(f"market {code} market，Not found")
            return f"{code}.SZ"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        from Yahoo Finance Get raw data

        use yfinance.download() Get historical data

        process：
        1. Convert stock symbol format
        2. call yfinance API
        3. Processing returned data
        """
        import yfinance as yf

        # Convert code format
        yf_code = self._convert_stock_code(stock_code)

        logger.debug(f"call yfinance.download({yf_code}, {start_date}, {end_date})")

        try:
            # use yfinance Download data
            df = yf.download(
                tickers=yf_code,
                start=start_date,
                end=end_date,
                progress=False,  # Disable progress bar
                auto_adjust=True,  # Auto-adjust prices (forward-adjusted)
                multi_level_index=True
            )

            # filter out yf_code columns, Avoid confusion of multiple stock data
            if isinstance(df.columns, pd.MultiIndex) and len(df.columns) > 1:
                ticker_level = df.columns.get_level_values(1)
                mask = ticker_level == yf_code
                if mask.any():
                    df = df.loc[:, mask].copy()

            if df.empty:
                raise DataFetchError(f"Yahoo Finance Not found {stock_code} data")

            return df

        except Exception as e:
            if isinstance(e, DataFetchError):
                raise
            raise DataFetchError(f"Yahoo Finance Failed to get data: {e}") from e

    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        standardization Yahoo Finance data

        yfinance Returned column names：
        Open, High, Low, Close, Volume（index is date）

        Notice：new version yfinance return MultiIndex List，capital letters ('Close', 'AMD')
        Column names need to be flattened before processing

        Need to be mapped to standard column names：
        date, open, high, low, close, volume, amount, pct_chg
        """
        df = df.copy()

        # deal with MultiIndex List（new version yfinance Return format）
        # Get the first level column name: ('Close', 'AMD') -> 'Close'
        if isinstance(df.columns, pd.MultiIndex):
            logger.debug("detected MultiIndex List，flatten")
            # Get the first level column name（Price level: Close, High, Low, etc.）
            df.columns = df.columns.get_level_values(0)

        # Reset index，Change date from index to column
        df = df.reset_index()

        # Column name mapping（yfinance Calculate the increase or decrease）
        column_mapping = {
            'Date': 'date',
            'Datetime': 'date',
            'datetime': 'date',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
        }

        df = df.rename(columns=column_mapping)
        if 'date' not in df.columns:
            index_col = df.columns[0] if len(df.columns) else None
            if index_col is not None:
                candidate = df[index_col]
                if pd.api.types.is_datetime64_any_dtype(candidate):
                    df = df.rename(columns={index_col: 'date'})
                elif not pd.api.types.is_numeric_dtype(candidate):
                    parsed_dates = pd.to_datetime(candidate, errors='coerce')
                    if parsed_dates.notna().any():
                        df = df.rename(columns={index_col: 'date'})
                        df['date'] = parsed_dates

        # Calculate the increase or decrease（because yfinance Not provided directly）
        if 'close' in df.columns:
            df['pct_chg'] = df['close'].pct_change() * 100
            df['pct_chg'] = df['pct_chg'].fillna(0).round(2)

        # Calculate turnover（yfinance Not available，Use estimates）
        # Turnover ≈ Volume * average price
        if 'volume' in df.columns and 'close' in df.columns:
            df['amount'] = df['volume'] * df['close']
        else:
            df['amount'] = 0

        # Add stock symbol column
        df['code'] = stock_code

        # Keep only the columns you need
        keep_cols = ['code'] + STANDARD_COLUMNS
        existing_cols = [col for col in keep_cols if col in df.columns]
        df = df[existing_cols]

        return df

    def _fetch_yf_ticker_data(self, yf, yf_code: str, name: str, return_code: str) -> Optional[Dict[str, Any]]:
        """
        pass yfinance Pull a single index/Stock market data。

        Args:
            yf: yfinance module reference
            yf_code: yfinance code used（capital letters '000001.SS'、'^GSPC'）
            name: Index display name
            return_code: Write results dict of code Field（capital letters 'sh000001'、'SPX'）

        Returns:
            Quote Dictionary，Return on failure None
        """
        ticker = yf.Ticker(yf_code)
        # Take the data of the past two days to calculate the increase and decrease
        hist = ticker.history(period='2d')
        if hist.empty:
            return None
        today_row = hist.iloc[-1]
        prev_row = hist.iloc[-2] if len(hist) > 1 else today_row
        price = float(today_row['Close'])
        prev_close = float(prev_row['Close'])
        change = price - prev_close
        change_pct = (change / prev_close) * 100 if prev_close else 0
        high = float(today_row['High'])
        low = float(today_row['Low'])
        # amplitude = (Highest - lowest) / Collected yesterday * 100
        amplitude = ((high - low) / prev_close * 100) if prev_close else 0
        return {
            'code': return_code,
            'name': name,
            'current': price,
            'change': change,
            'change_pct': change_pct,
            'open': float(today_row['Open']),
            'high': high,
            'low': low,
            'prev_close': prev_close,
            'volume': float(today_row['Volume']),
            'amount': 0.0,  # Yahoo Finance does not provide accurate turnover
            'amplitude': amplitude,
        }

    def get_main_indices(self, region: str = "cn") -> Optional[List[Dict[str, Any]]]:
        """
        Get major index quotes (Yahoo Finance)，support A share、US stocks、Hong Kong stocks、Japanese stocks、Korean stocks and Taiwan stocks。
        region=us entrusted to _get_us_main_indices。
        region=hk entrusted to _get_hk_main_indices。
        region=jp/kr/tw are respectively delegated to the corresponding market index method.。
        """
        import yfinance as yf

        if region == "us":
            return self._get_us_main_indices(yf)
        if region == "hk":
            return self._get_hk_main_indices(yf)
        if region == "jp":
            return self._get_jp_main_indices(yf)
        if region == "kr":
            return self._get_kr_main_indices(yf)
        if region == "tw":
            return self._get_tw_main_indices(yf)

        # A stock index：akshare code -> (yfinance code, display name)
        yf_mapping = {
            'sh000001': ('000001.SS', 'Shanghai Composite Index'),
            'sz399001': ('399001.SZ', 'Shenzhen Component Index'),
            'sz399006': ('399006.SZ', 'GEM Index'),
            'sh000688': ('000688.SS', 'Science and Technology50'),
            'sh000016': ('000016.SS', 'Shanghai Stock Exchange50'),
            'sh000300': ('000300.SS', 'Shanghai and Shenzhen300'),
        }

        results = []
        try:
            for ak_code, (yf_code, name) in yf_mapping.items():
                try:
                    item = self._fetch_yf_ticker_data(yf, yf_code, name, ak_code)
                    if item:
                        results.append(item)
                        logger.debug(f"[Yfinance] Get index {name} success")
                except Exception as e:
                    logger.warning(f"[Yfinance] Get index {name} fail: {e}")

            if results:
                logger.info(f"[Yfinance] successfully obtained {len(results)} indivual A Stock Index Quotes")
                return results

        except Exception as e:
            logger.error(f"[Yfinance] get A Stock index market failure: {e}")

        return None

    def _get_us_main_indices(self, yf) -> Optional[List[Dict[str, Any]]]:
        """Get quotes from major U.S. stock indexes（SPX、IXIC、DJI、VIX），Reuse _fetch_yf_ticker_data"""
        # Core US stock indexes required for market review
        us_indices = ['SPX', 'IXIC', 'DJI', 'VIX']
        results = []
        try:
            for code in us_indices:
                yf_symbol, name = get_us_index_yf_symbol(code)
                if not yf_symbol:
                    continue
                try:
                    item = self._fetch_yf_ticker_data(yf, yf_symbol, name, code)
                    if item:
                        results.append(item)
                        logger.debug(f"[Yfinance] Get US stock index {name} success")
                except Exception as e:
                    logger.warning(f"[Yfinance] Get US stock index {name} fail: {e}")

            if results:
                logger.info(f"[Yfinance] successfully obtained {len(results)} U.S. stock index quotes")
                return results

        except Exception as e:
            logger.error(f"[Yfinance] Failed to obtain US stock index quotes: {e}")

        return None

    def _get_hk_main_indices(self, yf) -> Optional[List[Dict[str, Any]]]:
        """Get quotes from major Hong Kong stock indexes（HSI、HSTECH、HSCEI），Reuse _fetch_yf_ticker_data"""
        # Yahoo Finance Hong Kong stock index symbol mapping：
        # - HSI -> ^HSI
        # - HSTECH -> HSTECH.HK（no ^HSTECH）
        # - HSCEI -> ^HSCE（no ^HSCEI）
        # solidify tests/test_yfinance_hk_indices.py solidify，Avoid non-deterministic failures caused by online dependencies。
        hk_indices = {
            'HSI': ('^HSI', 'Hang Seng Index'),
            'HSTECH': ('HSTECH.HK', 'Hang Seng Technology Index'),
            'HSCEI': ('^HSCE', 'State-owned enterprise index'),
        }
        results = []
        try:
            for code, (yf_symbol, name) in hk_indices.items():
                try:
                    item = self._fetch_yf_ticker_data(yf, yf_symbol, name, code)
                    if item:
                        results.append(item)
                        logger.debug(f"[Yfinance] Get Hong Kong stock index {name} success")
                except Exception as e:
                    logger.warning(f"[Yfinance] Get Hong Kong stock index {name} fail: {e}")

            if results:
                logger.info(f"[Yfinance] successfully obtained {len(results)} Hong Kong stock index quotes")
                return results

        except Exception as e:
            logger.error(f"[Yfinance] Failed to obtain Hong Kong stock index quotes: {e}")

        return None

    def _get_jp_main_indices(self, yf) -> Optional[List[Dict[str, Any]]]:
        """Get quotes from Japan's major indexes（Nikkei225、TOPIX），Reuse _fetch_yf_ticker_data。"""
        jp_indices = {
            'N225': ('^N225', 'Nikkei225'),
            'TOPX': ('^TOPX', 'Get Japan Index'),
        }
        results = []
        try:
            for code, (yf_symbol, name) in jp_indices.items():
                try:
                    item = self._fetch_yf_ticker_data(yf, yf_symbol, name, code)
                    if item:
                        results.append(item)
                        logger.debug(f"[Yfinance] Get Japan Index {name} success")
                except Exception as e:
                    logger.warning(f"[Yfinance] Get Japan Index {name} fail: {e}")
            if results:
                logger.info(f"[Yfinance] successfully obtained {len(results)} Failed to obtain Japanese index quotes")
                return results
        except Exception as e:
            logger.error(f"[Yfinance] Failed to obtain Japanese index quotes: {e}")
        return None

    def _get_kr_main_indices(self, yf) -> Optional[List[Dict[str, Any]]]:
        """Get quotes on major Korean indexes（KOSPI、KOSDAQ），Reuse _fetch_yf_ticker_data。"""
        kr_indices = {
            'KS11': ('^KS11', 'KOSPI'),
            'KQ11': ('^KQ11', 'KOSDAQ'),
        }
        results = []
        try:
            for code, (yf_symbol, name) in kr_indices.items():
                try:
                    item = self._fetch_yf_ticker_data(yf, yf_symbol, name, code)
                    if item:
                        results.append(item)
                        logger.debug(f"[Yfinance] Get Korea Index {name} success")
                except Exception as e:
                    logger.warning(f"[Yfinance] Get Korea Index {name} fail: {e}")
            if results:
                logger.info(f"[Yfinance] successfully obtained {len(results)} Korea Index Quotes")
                return results
        except Exception as e:
            logger.error(f"[Yfinance] Failed to obtain Korean index quotes: {e}")
        return None

    def _get_tw_main_indices(self, yf) -> Optional[List[Dict[str, Any]]]:
        """Get Taiwan’s major index quotes（weighted index ^TWII、Counter buying index ^TWOII），Reuse _fetch_yf_ticker_data。"""
        tw_indices = {
            'TWII': ('^TWII', 'Taiwan Weighted Index'),
            'TWOII': ('^TWOII', 'Taiwan counter buying index'),
        }
        results = []
        try:
            for code, (yf_symbol, name) in tw_indices.items():
                try:
                    item = self._fetch_yf_ticker_data(yf, yf_symbol, name, code)
                    if item:
                        results.append(item)
                        logger.debug(f"[Yfinance] Failed to obtain Taiwan index quotes {name} success")
                except Exception as e:
                    logger.warning(f"[Yfinance] Failed to obtain Taiwan index quotes {name} fail: {e}")
            if results:
                logger.info(f"[Yfinance] successfully obtained {len(results)} Taiwan Index Quotes")
                return results
        except Exception as e:
            logger.error(f"[Yfinance] Failed to obtain Taiwan index quotes: {e}")
        return None

    def _is_us_stock(self, stock_code: str) -> bool:
        """
        Determine whether the code is a US stock stock（Exclude U.S. stock indexes）。

        entrusted to us_index_mapping Modular is_us_stock_code()。
        """
        return is_us_stock_code(stock_code)

    def _get_us_stock_quote_from_stooq(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """
        use Stooq Provides key-free security for real-time market conditions of U.S. stocks。

        Stooq Provides the latest trading day quotes，Not as accurate as time-sharing real-time interface，But in Yahoo / yfinance
        When being restricted，At least it can Web UI Provide available prices；If yesterday’s closing price is available，It also provides derivative indicators such as price increases and decreases.。
        """
        symbol = stock_code.strip().upper()
        stooq_symbol = f"{symbol.lower()}.us"
        url = f"https://stooq.com/q/l/?s={stooq_symbol}"
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; DSA/1.0; +https://github.com/ZhuLinsen/daily_stock_analysis)",
                "Accept": "text/plain,text/csv,*/*",
            },
        )

        try:
            with urlopen(request, timeout=15) as response:
                payload = response.read().decode("utf-8", "ignore").strip()
        except (HTTPError, URLError, TimeoutError) as exc:
            logger.warning(f"[Stooq] Get US stocks {symbol} Real-time quotes failed: {exc}")
            return None

        if not payload or payload.upper().startswith("NO DATA"):
            logger.warning(f"[Stooq] Unable to obtain {symbol} market data")
            return None

        def _fetch_prev_close() -> Optional[float]:
            history_url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&i=d"
            history_request = Request(
                history_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; DSA/1.0; +https://github.com/ZhuLinsen/daily_stock_analysis)",
                    "Accept": "text/plain,text/csv,*/*",
                },
            )
            try:
                with urlopen(history_request, timeout=15) as response:
                    history_payload = response.read().decode("utf-8", "ignore").strip()
            except (HTTPError, URLError, TimeoutError) as exc:
                logger.debug(f"[Stooq] Get US stocks {symbol} Daily history of failure: {exc}")
                return None

            if not history_payload or history_payload.upper().startswith("NO DATA"):
                return None

            try:
                reader = csv.reader(StringIO(history_payload))
                header = next(reader, None)
                if not header:
                    return None

                header_tokens = [cell.strip().lower() for cell in header]
                has_header = "close" in header_tokens and "date" in header_tokens
                if not has_header:
                    return None

                date_index = header_tokens.index("date")
                close_index = header_tokens.index("close")

                daily_rows: list[tuple[datetime, float]] = []
                for row in reader:
                    if not row:
                        continue
                    date_text = row[date_index].strip() if len(row) > date_index else ""
                    close_text = row[close_index].strip() if len(row) > close_index else ""
                    if not date_text or not close_text:
                        continue
                    try:
                        dt = datetime.strptime(date_text, "%Y-%m-%d")
                        close_val = float(close_text)
                    except Exception:
                        continue
                    daily_rows.append((dt, close_val))

                if len(daily_rows) < 2:
                    return None

                daily_rows.sort(key=lambda item: item[0])
                return daily_rows[-2][1]
            except Exception:
                return None

        try:
            reader = csv.reader(StringIO(payload))
            first_row = next(reader, None)
            if first_row is None:
                raise ValueError(f"unexpected Stooq payload: {payload}")

            normalized_first_row = [cell.strip() for cell in first_row]
            header_tokens = {cell.lower() for cell in normalized_first_row if cell}
            has_header = 'open' in header_tokens and 'close' in header_tokens
            row = next(reader, None) if has_header else first_row
            if row is None:
                raise ValueError(f"unexpected Stooq payload: {payload}")

            normalized_row = [cell.strip() for cell in row]
            while normalized_row and normalized_row[-1] == '':
                normalized_row.pop()

            if len(normalized_row) >= 8:
                open_index, high_index, low_index, price_index, volume_index = 3, 4, 5, 6, 7
            elif len(normalized_row) >= 7:
                open_index, high_index, low_index, price_index, volume_index = 2, 3, 4, 5, 6
            else:
                raise ValueError(f"unexpected Stooq payload: {payload}")

            open_price = float(normalized_row[open_index])
            high = float(normalized_row[high_index])
            low = float(normalized_row[low_index])
            price = float(normalized_row[price_index])
            volume = int(float(normalized_row[volume_index]))

            prev_close = _fetch_prev_close()
            change_amount = None
            change_pct = None
            amplitude = None
            if prev_close is not None and prev_close > 0:
                change_amount = price - prev_close
                change_pct = (change_amount / prev_close) * 100
                amplitude = ((high - low) / prev_close) * 100

            quote = UnifiedRealtimeQuote(
                code=symbol,
                name=STOCK_NAME_MAP.get(symbol, ''),
                source=RealtimeSource.STOOQ,
                price=price,
                change_pct=round(change_pct, 2) if change_pct is not None else None,
                change_amount=round(change_amount, 4) if change_amount is not None else None,
                volume=volume,
                amount=None,
                volume_ratio=None,
                turnover_rate=None,
                amplitude=round(amplitude, 2) if amplitude is not None else None,
                open_price=open_price,
                high=high,
                low=low,
                pre_close=prev_close,
                pe_ratio=None,
                pb_ratio=None,
                total_mv=None,
                circ_mv=None,
            )
            logger.info(f"[Stooq] Get US stocks {symbol} The bottom line is successful: price={price}")
            return quote
        except Exception as exc:
            logger.warning(f"[Stooq] Analyzing U.S. stocks {symbol} Quote failed: {exc}")
            return None

    def _get_us_index_realtime_quote(
        self,
        user_code: str,
        yf_symbol: str,
        index_name: str,
    ) -> Optional[UnifiedRealtimeQuote]:
        """
        Get realtime quote for US index (e.g. SPX -> ^GSPC).

        Args:
            user_code: User input code (e.g. SPX)
            yf_symbol: Yahoo Finance symbol (e.g. ^GSPC)
            index_name: Chinese name for the index

        Returns:
            UnifiedRealtimeQuote or None
        """
        import yfinance as yf

        try:
            logger.debug(f"[Yfinance] Get US stock index {user_code} ({yf_symbol}) Real-time quotes")
            ticker = yf.Ticker(yf_symbol)

            try:
                info = ticker.fast_info
                if info is None:
                    raise ValueError("fast_info is None")
                price = getattr(info, 'lastPrice', None) or getattr(info, 'last_price', None)
                prev_close = getattr(info, 'previousClose', None) or getattr(info, 'previous_close', None)
                open_price = getattr(info, 'open', None)
                high = getattr(info, 'dayHigh', None) or getattr(info, 'day_high', None)
                low = getattr(info, 'dayLow', None) or getattr(info, 'day_low', None)
                volume = getattr(info, 'lastVolume', None) or getattr(info, 'last_volume', None)
            except Exception:
                logger.debug("[Yfinance] fast_info fail，try history method")
                hist = ticker.history(period='2d')
                if hist.empty:
                    logger.warning(f"[Yfinance] Unable to obtain {yf_symbol} data")
                    return None
                today = hist.iloc[-1]
                prev = hist.iloc[-2] if len(hist) > 1 else today
                price = float(today['Close'])
                prev_close = float(prev['Close'])
                open_price = float(today['Open'])
                high = float(today['High'])
                low = float(today['Low'])
                volume = int(today['Volume'])

            change_amount = None
            change_pct = None
            if price is not None and prev_close is not None and prev_close > 0:
                change_amount = price - prev_close
                change_pct = (change_amount / prev_close) * 100

            amplitude = None
            if high is not None and low is not None and prev_close is not None and prev_close > 0:
                amplitude = ((high - low) / prev_close) * 100

            try:
                ticker_info = ticker.info or {}
            except Exception:
                ticker_info = {}
            missing_fields = [
                field
                for field, value in {
                    "price": price,
                    "prev_close": prev_close,
                    "volume": volume,
                    "amount": None,
                    "pe_ratio": None,
                    "pb_ratio": None,
                }.items()
                if value is None
            ]

            quote = UnifiedRealtimeQuote(
                code=user_code,
                name=index_name or user_code,
                source=RealtimeSource.FALLBACK,
                market="us",
                currency=str(ticker_info.get("currency") or "").upper() or None,
                data_quality="partial" if missing_fields else "ok",
                missing_fields=missing_fields or None,
                price=price,
                change_pct=round(change_pct, 2) if change_pct is not None else None,
                change_amount=round(change_amount, 4) if change_amount is not None else None,
                volume=volume,
                amount=None,
                volume_ratio=None,
                turnover_rate=None,
                amplitude=round(amplitude, 2) if amplitude is not None else None,
                open_price=open_price,
                high=high,
                low=low,
                pre_close=prev_close,
                pe_ratio=None,
                pb_ratio=None,
                total_mv=None,
                circ_mv=None,
            )
            logger.info(f"[Yfinance] Get US stock index {user_code} Real-time market success: price={price}")
            return quote
        except Exception as e:
            logger.warning(f"[Yfinance] Get US stock index {user_code} Real-time quotes failed: {e}")
            return None

    def get_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """
        Get US stocks/U.S. stock index real-time market data

        and U.S. stock indexes（AAPL、TSLA）and U.S. stock indexes（SPX、DJI wait）。
        Data source：yfinance Ticker.info

        Args:
            stock_code: US stock code or index code，capital letters 'AMD', 'AAPL', 'SPX', 'DJI'

        Returns:
            UnifiedRealtimeQuote object，Return on failure to obtain None
        """
        import yfinance as yf

        # capital letters：Use mapping（SPX -> ^GSPC）
        yf_symbol, index_name = get_us_index_yf_symbol(stock_code)
        if yf_symbol:
            return self._get_us_index_realtime_quote(
                user_code=stock_code.strip().upper(),
                yf_symbol=yf_symbol,
                index_name=index_name,
            )

        # Only deal with U.S. stocks or JP/KR/TW suffix-only stock
        if not (
            self._is_us_stock(stock_code)
            or self._is_jp_kr_suffix_stock(stock_code)
            or self._is_tw_suffix_stock(stock_code)
        ):
            logger.debug(f"[Yfinance] {stock_code} Not US stocks or Japan and South Korea suffix code，jump over")
            return None

        try:
            symbol = self._convert_stock_code(stock_code)
            is_us_symbol = self._is_us_stock(symbol)
            suffix_market = get_suffix_market(symbol)
            logger.debug(f"[Yfinance] get {symbol} Real-time quotes")

            ticker = yf.Ticker(symbol)

            # try to get fast_info（faster，But there are fewer fields）
            try:
                info = ticker.fast_info
                if info is None:
                    raise ValueError("fast_info is None")

                price = getattr(info, 'lastPrice', None) or getattr(info, 'last_price', None)
                prev_close = getattr(info, 'previousClose', None) or getattr(info, 'previous_close', None)
                open_price = getattr(info, 'open', None)
                high = getattr(info, 'dayHigh', None) or getattr(info, 'day_high', None)
                low = getattr(info, 'dayLow', None) or getattr(info, 'day_low', None)
                volume = getattr(info, 'lastVolume', None) or getattr(info, 'last_volume', None)
                market_cap = getattr(info, 'marketCap', None) or getattr(info, 'market_cap', None)

            except Exception:
                # Fallback to history Method to get the latest data
                logger.debug("[Yfinance] fast_info fail，try history method")
                hist = ticker.history(period='2d')
                if hist.empty:
                    if is_us_symbol:
                        logger.warning(f"[Yfinance] Unable to obtain {symbol} data，try Stooq reveal all the details")
                        return self._get_us_stock_quote_from_stooq(symbol)
                    logger.warning(f"[Yfinance] Unable to obtain {symbol} data")
                    return None

                today = hist.iloc[-1]
                prev = hist.iloc[-2] if len(hist) > 1 else today

                price = float(today['Close'])
                prev_close = float(prev['Close'])
                open_price = float(today['Open'])
                high = float(today['High'])
                low = float(today['Low'])
                volume = int(today['Volume'])
                market_cap = None

            # Calculate the increase or decrease
            change_amount = None
            change_pct = None
            if price is not None and prev_close is not None and prev_close > 0:
                change_amount = price - prev_close
                change_pct = (change_amount / prev_close) * 100

            # Calculate amplitude
            amplitude = None
            if high is not None and low is not None and prev_close is not None and prev_close > 0:
                amplitude = ((high - low) / prev_close) * 100

            # Get the stock name and provider metadata
            try:
                ticker_info = ticker.info or {}
            except Exception:
                ticker_info = {}
            try:
                info_name = ticker_info.get('shortName', '') or ticker_info.get('longName', '') or ''
                name = info_name if is_meaningful_stock_name(info_name, symbol) else STOCK_NAME_MAP.get(symbol, '')
            except Exception:
                name = STOCK_NAME_MAP.get(symbol, '')

            missing_fields = [
                field
                for field, value in {
                    "price": price,
                    "prev_close": prev_close,
                    "volume": volume,
                    "amount": None,
                    "pe_ratio": None,
                    "pb_ratio": None,
                }.items()
                if value is None
            ]
            quote = UnifiedRealtimeQuote(
                code=symbol,
                name=name,
                source=RealtimeSource.FALLBACK,
                market=suffix_market or ("us" if is_us_symbol else None),
                currency=str(ticker_info.get("currency") or "").upper() or None,
                data_quality="partial" if missing_fields else "ok",
                missing_fields=missing_fields or None,
                price=price,
                change_pct=round(change_pct, 2) if change_pct is not None else None,
                change_amount=round(change_amount, 4) if change_amount is not None else None,
                volume=volume,
                amount=None,  # yfinance does not directly provide turnover
                volume_ratio=None,
                turnover_rate=None,
                amplitude=round(amplitude, 2) if amplitude is not None else None,
                open_price=open_price,
                high=high,
                low=low,
                pre_close=prev_close,
                pe_ratio=None,
                pb_ratio=None,
                total_mv=market_cap,
                circ_mv=None,
            )

            logger.info(f"[Yfinance] get {symbol} Real-time market success: price={price}")
            return quote

        except Exception as e:
            if self._is_us_stock(stock_code):
                logger.warning(f"[Yfinance] Get US stocks {stock_code} Real-time quotes failed: {e}，try Stooq reveal all the details")
                return self._get_us_stock_quote_from_stooq(stock_code)
            logger.warning(f"[Yfinance] get {stock_code} Real-time quotes failed: {e}")
            return None


if __name__ == "__main__":
    # test code
    logging.basicConfig(level=logging.DEBUG)

    fetcher = YfinanceFetcher()

    try:
        df = fetcher.get_daily_data('600519')  # Moutai
        print(f"get success，common {len(df)} piece of data")
        print(df.tail())
    except Exception as e:
        print(f"Failed to obtain: {e}")
