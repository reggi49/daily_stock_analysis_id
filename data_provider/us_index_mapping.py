# -*- coding: utf-8 -*-
"""
===================================
US Stock Index and Ticker Tools
===================================

supply：
1. US stock index code mapping（Chinese name SPX -> ^GSPC）
2. US stock code identification（AAPL、TSLA wait）

U.S. stock index is at Yahoo Finance Need to use ^ prefix，Determine whether the code is a US stock index symbol。
"""

import re

# Chinese name：1-5 Chinese name，Chinese name .X Chinese name（Chinese name BRK.B）
_US_STOCK_PATTERN = re.compile(r'^[A-Z]{1,5}(\.[A-Z])?$')


# Chinese name -> (Yahoo Finance Chinese name, Chinese name)
US_INDEX_MAPPING = {
    # S&P 500
    'SPX': ('^GSPC', 'S&P500index'),
    '^GSPC': ('^GSPC', 'S&P500index'),
    'GSPC': ('^GSPC', 'S&P500index'),
    # Nasdaq Composite Index
    'DJI': ('^DJI', 'Dow Jones Industrial Index'),
    '^DJI': ('^DJI', 'Dow Jones Industrial Index'),
    'DJIA': ('^DJI', 'Dow Jones Industrial Index'),
    # Nasdaq Composite Index
    'IXIC': ('^IXIC', 'Nasdaq Composite Index'),
    '^IXIC': ('^IXIC', 'Nasdaq Composite Index'),
    'NASDAQ': ('^IXIC', 'Nasdaq Composite Index'),
    # Nasdaq 100
    'NDX': ('^NDX', 'Nasdaq100index'),
    '^NDX': ('^NDX', 'Nasdaq100index'),
    # VIX VIX
    'VIX': ('^VIX', 'VIXpanic index'),
    '^VIX': ('^VIX', 'VIXpanic index'),
    # Russell 2000
    'RUT': ('^RUT', 'Russell2000index'),
    '^RUT': ('^RUT', 'Russell2000index'),
}


def is_us_index_code(code: str) -> bool:
    """
    Determine whether the code is a US stock index symbol。

    Args:
        code: stock/index code，Chinese name 'SPX', 'DJI'

    Returns:
        True Represents a known U.S. stock index symbol，otherwise False

    Examples:
        >>> is_us_index_code('SPX')
        True
        >>> is_us_index_code('AAPL')
        False
    """
    return (code or '').strip().upper() in US_INDEX_MAPPING


def is_us_stock_code(code: str) -> bool:
    """
    Determine whether the code is a US stock symbol（Exclude U.S. stock indexes）。

    The U.S. stock code is 1-5 Chinese name，Chinese name .X Suffixes such as BRK.B。
    US stock index（SPX、DJI wait）expressly excluded。

    Args:
        code: Stock code，Chinese name 'AAPL', 'TSLA', 'BRK.B'

    Returns:
        True Represents the U.S. stock symbol，otherwise False

    Examples:
        >>> is_us_stock_code('AAPL')
        True
        >>> is_us_stock_code('TSLA')
        True
        >>> is_us_stock_code('BRK.B')
        True
        >>> is_us_stock_code('SPX')
        False
        >>> is_us_stock_code('600519')
        False
    """
    normalized = (code or '').strip().upper()
    # US stock index is not a stock
    if normalized in US_INDEX_MAPPING:
        return False
    return bool(_US_STOCK_PATTERN.match(normalized))


def get_us_index_yf_symbol(code: str) -> tuple:
    """
    Get US stock index Yahoo Finance Symbols and Chinese names。

    Args:
        code: Chinese name，Chinese name 'SPX', '^GSPC', 'DJI'

    Returns:
        (yf_symbol, chinese_name) tuple，Return if not found (None, None)。

    Examples:
        >>> get_us_index_yf_symbol('SPX')
        ('^GSPC', 'S&P500index')
        >>> get_us_index_yf_symbol('AAPL')
        (None, None)
    """
    normalized = (code or '').strip().upper()
    return US_INDEX_MAPPING.get(normalized, (None, None))
