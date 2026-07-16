#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Stock Index from CSV File

Input:
  - Tushare format: data/stock_list_{a,hk,us}.csv
  - Seed format: scripts/stock_index_seeds/stock_list_{jp,kr}.csv
  - AkShare format: logs/stock_basic_*.csv

Output: apps/dsa-web/public/stocks.index.json

Usage:
    python3 scripts/generate_index_from_csv.py              # Used by default Tushare
    python3 scripts/generate_index_from_csv.py --source akshare
    python3 scripts/generate_index_from_csv.py --test       # test mode
"""

import argparse
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add the project root to sys.path.
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from pypinyin import lazy_pinyin, Style
    PYPINYIN_AVAILABLE = True
except ImportError:
    lazy_pinyin = None
    Style = None
    PYPINYIN_AVAILABLE = False


def require_pypinyin() -> bool:
    """Ensure pypinyin is available before generating autocomplete assets."""
    if PYPINYIN_AVAILABLE:
        return True

    print("[Error] pypinyin not available; cannot generate stock autocomplete index.")
    print("[Info] Install dependencies with: pip install -r requirements.txt")
    return False


def load_csv_data(csv_path: Path) -> List[Dict[str, Any]]:
    """
    Load stock data from AkShare format CSV file

    Args:
        csv_path: CSV file path

    Returns:
        List of stock data
    """
    stocks = []

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            ts_code = row['ts_code'].strip()
            symbol = row['symbol'].strip()
            name = row['name'].strip()

            # Skip invalid rows.
            if not ts_code or not symbol or not name:
                continue

            stocks.append({
                'ts_code': ts_code,
                'symbol': symbol,
                'name': name,
                'area': row.get('area', ''),
                'industry': row.get('industry', ''),
                'list_date': row.get('list_date', ''),
            })

    return stocks


def load_tushare_data(data_dir: Path) -> List[Dict[str, Any]]:
    """
    from Tushare CSV File loads multi-market stock data

    Args:
        data_dir: List of stocks after the merger

    Returns:
        List of stocks after the merger
    """
    all_stocks = []
    seed_dir = Path(__file__).parent / 'stock_index_seeds'
    default_data_dir = Path(__file__).parent.parent / 'data'
    use_seed_fallback = data_dir.resolve() == default_data_dir.resolve()

    def _csv_path(file_name: str) -> Path:
        data_path = data_dir / file_name
        if data_path.exists() or not use_seed_fallback:
            return data_path
        return seed_dir / file_name

    market_files = {
        'CN': data_dir / 'stock_list_a.csv',
        'HK': data_dir / 'stock_list_hk.csv',
        'US': data_dir / 'stock_list_us.csv',
        'JP': _csv_path('stock_list_jp.csv'),
        'KR': _csv_path('stock_list_kr.csv'),
    }

    for market_name, csv_file in market_files.items():
        if not csv_file.exists():
            print(f"[Warning] File not found: {csv_file}")
            continue

        print(f"  Reading {market_name} market data: {csv_file.name}")

        try:
            file_stocks = []
            selected_us_stocks: Dict[str, tuple[Dict[str, Any], int]] = {}
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    # Common in US stocks
                    parsed = parse_stock_row(row, market_name)
                    if not parsed:
                        continue

                    if market_name == 'US':
                        # Tushare us_basic may include historical rows for a reused ticker.
                        # Keep one deterministic row per ts_code before generating the index.
                        delist_priority = get_us_delist_priority(row)
                        existing = selected_us_stocks.get(parsed['ts_code'])
                        if existing is None or delist_priority > existing[1]:
                            selected_us_stocks[parsed['ts_code']] = (parsed, delist_priority)
                        continue

                    if parsed:
                        all_stocks.append(parsed)
                        file_stocks.append(parsed)

            if market_name == 'US':
                file_stocks = [item for item, _priority in selected_us_stocks.values()]
                all_stocks.extend(file_stocks)

            print(f"    ✓ {market_name} market read complete: {len(file_stocks)} stocks")

        except Exception as e:
            print(f"    [Error] Failed to read {csv_file.name}: {e}")

    return all_stocks


def get_us_delist_priority(row: Dict[str, str]) -> int:
    """
    Generate deduplication priority for reused US stock tickers.

    Tushare us_basic delist_date is not always stable for the current record:
    - Empty string usually indicates the ticker is active
    - ``NaT`` actually indicates no delisting info
    - Actual date indicates clear delisting

    Therefore, deduplication priority is:
    1. delist_date is empty (active)
    2. delist_date is NaT
    3. delist_date is an actual date

    When same priority, the first CSV record is kept to avoid random name switching.
    """
    delist_date = (row.get('delist_date') or '').strip()
    if not delist_date:
        return 2
    if delist_date.upper() == 'NAT':
        return 1
    return 0


def load_akshare_data(logs_dir: Path) -> List[Dict[str, Any]]:
    """
    Load stock data from AkShare format CSV files.

    Args:
        logs_dir: Log directory path

    Returns:
        Stock list

    Note:
        AkShare input retains its original name field here, without applying the
        A-share XD/XR/DR status prefix correction logic used for Tushare data.
        The goal is to reuse AkShare's exported display names rather than normalizing twice.
    """
    csv_files = list(logs_dir.glob("stock_basic_*.csv"))

    if not csv_files:
        print("[Error] No CSV files found: logs/stock_basic_*.csv")
        return []

    # Use the latest CSV file
    csv_file = sorted(csv_files)[-1]
    print(f"  Reading AkShare data: {csv_file.name}")

    stocks = []
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            ts_code = row['ts_code'].strip()
            symbol = row['symbol'].strip()
            name = row['name'].strip()

            # Skip invalid rows.
            if not ts_code or not symbol or not name:
                continue

            stocks.append({
                'ts_code': ts_code,
                'symbol': symbol,
                'name': name,
                'area': row.get('area', ''),
                'industry': row.get('industry', ''),
                'list_date': row.get('list_date', ''),
            })

    print(f"    ✓ Read total {len(stocks)} stocks")
    return stocks


def generate_pinyin(name: str) -> tuple:
    """
    Generate pinyin for stock name

    Args:
        name: Stock name

    Returns:
        Tuple of (pinyin_full, pinyin_abbr)
    """
    if not PYPINYIN_AVAILABLE:
        raise RuntimeError("pypinyin is required to generate stock autocomplete index")

    try:
        normalized_name = normalize_name_for_pinyin(name)

        # Full pinyin spelling.
        py_full = lazy_pinyin(normalized_name, style=Style.NORMAL)
        pinyin_full = ''.join(py_full)

        # Pinyin abbreviation.
        py_abbr = lazy_pinyin(normalized_name, style=Style.FIRST_LETTER)
        pinyin_abbr = ''.join(py_abbr)

        return (pinyin_full, pinyin_abbr)
    except Exception as e:
        print(f"[Warning] Failed to generate pinyin for {name}: {e}")
        return (None, None)


def normalize_name_for_pinyin(name: str) -> str:
    """
    Normalize stock name to avoid special prefixes and full-width characters polluting pinyin index

    Args:
        name: Original stock name

    Returns:
        Normalized name for pinyin generation
    """
    normalized = unicodedata.normalize('NFKC', name).strip()

    # Strip common A-share prefixes while preserving the core name.
    normalized = re.sub(r'^(?:\*?ST|N)+', '', normalized, flags=re.IGNORECASE)

    return normalized.strip() or unicodedata.normalize('NFKC', name).strip()


def normalize_stock_name_for_index(name: str, market: str) -> str:
    """
    Normalize stock names before writing the long-lived autocomplete index.

    For A-shares (including BSE), ``XD``/``XR``/``DR`` are
    ex-dividend/ex-rights trading-day prefixes. They should not be stored in
    the official static index because they can become stale almost immediately.
    New-stock prefixes such as ``N``/``C`` and risk-warning prefixes such as
    ``ST``/``*ST`` are preserved; they should be refreshed by the next
    stock-list update.
    """
    normalized = unicodedata.normalize('NFKC', str(name or '')).strip()
    if market in {'CN', 'BSE'}:
        normalized = re.sub(r'^(?:XD|XR|DR)\s*', '', normalized, flags=re.IGNORECASE)
    return normalized.strip()


def extract_symbol_from_ts_code(ts_code: str, market: str) -> Optional[str]:
    """
    Extract display code from ts_code.

    - A-share: 000001.SZ -> 000001
    - Hong Kong: 00700.HK -> 00700
    - US stocks: AAPL -> AAPL
    - Japanese/Korean stocks: 7203.T / 005930.KS -> Keep suffix, code

    Args:
        ts_code: TScode
        market: market code

    Returns:
        displayCode or None
    """
    if not ts_code:
        return None

    if market in {'US', 'JP', 'KR'}:
        # US stocks, Japanese/Korean stocks: class/share suffix and Yahoo suffixes are part of the code identity.
        return ts_code

    if '.' in ts_code:
        # A-shares and Hong Kong: remove suffix
        return ts_code.split('.')[0]

    return ts_code


def get_stock_name(row: Dict[str, str], market: str) -> Optional[str]:
    """
    Get stock name

    - A-share / Hong Kong / Japanese / Korean: use name field
    - US stocks: use enname field (English name)

    Args:
        row: CSV row data
        market: market code

    Returns:
        stock name or None
    """
    if market == 'US':
        # U.S. stocks use English names
        name = row.get('enname', '').strip()
        return name if name else None
    else:
        # AStocks and Hong Kong stocks use Chinese names
        name = row.get('name', '').strip()
        name = normalize_stock_name_for_index(name, market)
        return name if name else None


def parse_aliases(row: Dict[str, str]) -> List[str]:
    """Parse optional seed aliases from a CSV row."""
    raw_aliases = (row.get('aliases') or row.get('alias') or '').strip()
    if not raw_aliases:
        return []

    aliases: List[str] = []
    for alias in re.split(r'[|;,，、]+', raw_aliases):
        normalized = unicodedata.normalize('NFKC', alias).strip()
        if normalized and normalized not in aliases:
            aliases.append(normalized)
    return aliases


def parse_stock_row(row: Dict[str, str], preferred_market: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Parse single line stock data

    - US stocks: strict DUMMY filtering
    - Null value check
    - Auto-detect market type (used when preferred_market is unavailable)
    - Returns a uniformly formatted dictionary

    Args:
        row: CSV row data
        preferred_market: when ts_code Used when unable to judge the market（Such as US stocks DUMMY Record）

    Returns:
        Parsed stock dictionary; returns None for invalid data
    """
    ts_code = row.get('ts_code', '').strip()

    if not ts_code:
        return None

    # Auto-detect market type
    market = determine_market(ts_code)

    # If ts_code has no suffix (can't determine accurately), and preferred_market is provided, use it.
    # This is mainly for US stock special formats (e.g., DUMMY records).
    if '.' not in ts_code and preferred_market:
        market = preferred_market

    # Special handling for US stocks: strict DUMMY record filtering
    if market == 'US':
        enname = row.get('enname', '').strip()
        if not enname or 'DUMMY' in enname.upper():
            return None

    # Get stock name
    name = get_stock_name(row, market)
    if not name:
        return None

    # Extract display code
    display_code = extract_symbol_from_ts_code(ts_code, market)
    if not display_code:
        return None

    return {
        'ts_code': ts_code,
        'symbol': display_code,
        'name': name,
        'market': market,
        'aliases': parse_aliases(row),
    }


def determine_market(ts_code: str) -> str:
    """
    Determine market based on code

    Args:
        ts_code: Trading code (e.g., 000001.SZ, AAPL, BRK.B, 7203.T, 005930.KS)

    Returns:
        Market code (CN, HK, US, BSE, JP, KR)
    """
    if '.' in ts_code:
        # Check if it is a Chinese market suffix
        suffix = ts_code.split('.')[1]
        # Check if it is a Chinese market suffix
        if suffix in ['SH', 'SZ']:
            return 'CN'
        elif suffix == 'HK':
            return 'HK'
        elif suffix == 'BJ':
            return 'BSE'
        elif suffix == 'T':
            return 'JP'
        elif suffix in ['KS', 'KQ']:
            return 'KR'
        # There is a suffix but it's not a Chinese market suffix; check if it's a US stock.
        # US stocks may have dot suffixes (e.g., BRK.B, GOOG.A, AAPL.U)
        prefix = ts_code.split('.')[0]
        if prefix.isalpha():
            return 'US'
    else:
        # No suffix
        # Pure alphabetical codes for US stocks
        if ts_code.isalpha():
            return 'US'

    # Default is A-share
    return 'CN'


def generate_aliases(name: str, market: str) -> List[str]:
    """
    Generate stock aliases

    Args:
        name: Stock name
        market: Market code

    Returns:
        List of aliases
    """
    aliases = []

    # Common A-share aliases
    cn_alias_map = {
        'Kweichow Moutai': ['Moutai'],
        'Ping An of China': ['Peace'],
        'Ping An Bank': ['flat silver'],
        'China Merchants Bank': ['China Merchants Bank'],
        'Wuliangye': ['Wuliang'],
        'Ningde era': ['Ningde'],
        'BYD': ['Biya'],
        'ICBC': ['ICBC'],
        'China Construction Bank': ['China Construction Bank'],
        'Agricultural Bank of China': ['Agricultural Bank of China'],
        'Bank of China': ['Bank of China'],
        'Bank of Communications': ['Bank of Communications'],
        'Industrial Bank': ['Prosperity'],
        'Shanghai Pudong Development Bank': ['Pufa'],
        'China Minsheng Bank': ["people's livelihood"],
        'CITIC Securities': ['CITIC'],
        'Oriental Fortune': ['Dongcai'],
        'Hikvision': ['Hikvision'],
        'Longi Green Energy': ['Longi'],
        'China Shenhua': ['Shenhua'],
        'Yangtze Power': ['Long battery'],
        'Sinopec': ['petrochemical'],
        'PetroChina': ['oil'],
    }

    # Common aliases for Hong Kong stocks
    hk_alias_map = {
        'Tencent Holdings': ['Tencent', 'Tencent'],
        'Alibaba-SW': ['Ali', 'Alibaba', 'Alibaba'],
        'Meituan-W': ['Meituan', 'Meituan'],
        'Xiaomi Group-W': ['Millet', 'Xiaomi'],
        'JD Group-SW': ['Jingdong', 'JD'],
        'Baidu Group-S': ['Baidu Group', 'NetEase'],
        'Baidu Group-SW': ['Baidu', 'Baidu'],
        'SMIC': ['SMIC', 'SMIC'],
        'China Mobile': ['China Mobile', 'China Mobile'],
        'China National Offshore Oil Corporation': ['CNOOC', 'CNOOC'],
    }

    # Common aliases for US stocks
    us_alias_map = {
        'Apple Inc.': ['Apple', 'AAPL'],
        'Microsoft Corporation': ['Microsoft', 'MSFT'],
        'Amazon.com, Inc.': ['Amazon', 'AMZN'],
        'Tesla Inc.': ['Tesla', 'TSLA'],
        'Meta Platforms, Inc.': ['Meta', 'Facebook', 'META'],
        'Alphabet Inc.': ['Google', 'Alphabet', 'GOOGL'],
        'NVIDIA Corporation': ['NVIDIA', 'NVDA'],
        'Netflix Inc.': ['Netflix', 'NFLX'],
        'Intel Corporation': ['Intel', 'INTC'],
        'Advanced Micro Devices': ['AMD', 'AMD'],
    }

    # Select alias map by market
    if market == 'CN':
        alias_map = cn_alias_map
    elif market == 'HK':
        alias_map = hk_alias_map
    elif market == 'US':
        alias_map = us_alias_map
    else:
        alias_map = {}

    if name in alias_map:
        aliases.extend(alias_map[name])

    return aliases


def build_stock_index(stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build the stock index.

    Args:
        stocks: Raw stock rows (already include market field)

    Returns:
        Stock index entries
    """
    index = []

    for stock in stocks:
        ts_code = stock['ts_code']
        symbol = stock['symbol']
        name = stock['name']
        market = stock.get('market', 'CN')  # Prefer parsed market, otherwise determine from ts_code

        # If no market field, determine from ts_code
        if market == 'CN' and '.' not in ts_code:
            market = determine_market(ts_code)

        # Generate pinyin fields.
        pinyin_full, pinyin_abbr = generate_pinyin(name)

        # Generate aliases.
        aliases = generate_aliases(name, market)
        for alias in stock.get('aliases', []):
            if alias != name and alias not in aliases:
                aliases.append(alias)

        index.append({
            "canonicalCode": ts_code,    # Example: 000001.SZ, AAPL
            "displayCode": symbol,       # Example: 000001, AAPL
            "nameZh": name,
            "pinyinFull": pinyin_full,
            "pinyinAbbr": pinyin_abbr,
            "aliases": aliases,
            "market": market,
            "assetType": "stock",
            "active": True,
            "popularity": 100,
        })

    return index


def compress_index(index: List[Dict[str, Any]]) -> List[List]:
    """
    Compress index into array format to reduce file size

    Args:
        index: original index

    Returns:
        Compressed index
    """
    compressed = []
    for item in index:
        compressed.append([
            item["canonicalCode"],
            item["displayCode"],
            item["nameZh"],
            item.get("pinyinFull"),
            item.get("pinyinAbbr"),
            item.get("aliases", []),
            item["market"],
            item["assetType"],
            item["active"],
            item.get("popularity", 0),
        ])
    return compressed


def main():
    """main function"""
    parser = argparse.ArgumentParser(description='Generate stock autocomplete index from CSV')
    parser.add_argument(
        '--source',
        choices=['tushare', 'akshare'],
        default='tushare',
        help='Data source selection (default: tushare)'
    )
    parser.add_argument(
        '--test', '-t',
        action='store_true',
        help='Test mode: validate only, do not write to file'
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Stock Index Generation Tool (from CSV)")
    print("=" * 60)
    print(f"Data source: {args.source}")

    if not require_pypinyin():
        return 1

    # Load data
    print("\n[1/5] Reading CSV data...")
    if args.source == 'tushare':
        data_dir = Path(__file__).parent.parent / 'data'
        stocks = load_tushare_data(data_dir)
    elif args.source == 'akshare':
        logs_dir = Path(__file__).parent.parent / 'logs'
        stocks = load_akshare_data(logs_dir)
    else:
        print(f"[Error] Unsupported data source: {args.source}")
        return 1

    if not stocks:
        print("[Error] No stock data loaded")
        return 1

    print(f"      Total loaded: {len(stocks)} stocks")

    print("\n[2/5] Generating index data...")
    index = build_stock_index(stocks)

    # Output path
    output_path = (
        Path(__file__).parent.parent / "apps" / "dsa-web" / "public" / "stocks.index.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("\n[3/5] Compressing index data...")
    compressed = compress_index(index)

    if args.test:
        print("\n[4/5] Test mode: skipping file write")
        print(f"      Output path: {output_path}")

        # Validate data
        print("\n[5/5] Validating data...")
        print(f"      Before compression: {len(index)} records")
        print(f"      After compression: {len(compressed)} records")

        # Show first 5 examples
        if compressed:
            print("\n      First 5 examples:")
            for i, item in enumerate(compressed[:5]):
                print(f"        {i + 1}. {item}")
    else:
        print(f"\n[4/5] Writing file: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('[\n')
            for i, item in enumerate(compressed):
                json.dump(item, f, ensure_ascii=False, separators=(',', ':'))
                if i < len(compressed) - 1:
                    f.write(',\n')
                else:
                    f.write('\n')
            f.write(']\n')

        file_size = output_path.stat().st_size
        print(f"      File size: {file_size / 1024:.2f} KB")

        # Verify file
        print("\n[5/5] Verifying file...")
        with open(output_path, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
            print(f"      Verification passed: {len(test_data)} records")

    # Statistics
    market_stats = {}
    for item in index:
        market = item['market']
        market_stats[market] = market_stats.get(market, 0) + 1

    print(f"\n{'=' * 60}")
    print("Generation complete! Market distribution:")
    for market, count in sorted(market_stats.items()):
        print(f"  - {market}: {count} stocks")
    print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
