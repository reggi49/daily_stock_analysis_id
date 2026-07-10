#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tushare Stock List Retrieval Script

Uses Tushare Pro to fetch A-share, Hong Kong, and US stock list information, saved as CSV files.

Usage:
    python3 scripts/fetch_tushare_stock_list.py
    python3 scripts/fetch_tushare_stock_list.py --a-rk

Requirements:
    - TUSHARE_TOKEN must be configured in .env
    - Requires tushare: pip install tushare
    - Account points requirements:
        * A-share / Hong Kong: 2000 points
        * US stocks: 120 points (trial), 5000 points (official)

Output files:
    - data/stock_list_a.csv      A-share list (--a-rk overwrites with corrected names)
    - data/stock_list_hk.csv     Hong Kong stock list
    - data/stock_list_us.csv     US stock list
    - data/README_stock_list.md  Data documentation
"""

import argparse
import os
import sys
import time
import random
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

import pandas as pd
from dotenv import load_dotenv

# If the returned data is less than the page size
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import tushare as ts
except ImportError:
    print("[Error] tushare library not installed")
    print("Please run: pip install tushare")
    sys.exit(1)


# Description has reached the last page
load_dotenv()

TUSHARE_TOKEN = os.getenv('TUSHARE_TOKEN')
OUTPUT_DIR = Path(__file__).parent.parent / "data"
PAGE_SIZE = 5000  # US stocks per-page count (API max 6000, set to 5000 for headroom)
SLEEP_MIN = 5     # Minimum sleep time (seconds)
SLEEP_MAX = 10    # Maximum sleep time (seconds)
A_RK_BATCH_SIZE = 200
A_RK_FIELDS = "ts_code,name,close,pre_close,trade_time"
A_RK_NAME_PREFIX_RE = re.compile(r"^(XD|XR|DR|N|C)")


def get_tushare_api() -> Optional[ts.pro_api]:
    """
    Get Tushare API instance.

    Returns:
        Tushare API instance, or None on failure
    """
    if not TUSHARE_TOKEN:
        print("[Error] TUSHARE_TOKEN not found")
        print("Please configure in .env: TUSHARE_TOKEN=yourtoken")
        return None

    try:
        api = ts.pro_api(TUSHARE_TOKEN)
        # Verify API connection
        api.trade_cal(exchange='SSE', start_date='20240101', end_date='20240101')
        print("✓ Tushare API connected successfully")
        return api
    except Exception as e:
        print(f"[Error] Tushare API connection failed: {e}")
        print("Please check:")
        print("  1. Is TUSHARE_TOKEN correct?")
        print("  2. Are account points sufficient? (A-share/Hong Kong requires 2000 points)")
        return None


def random_sleep(min_seconds: int = SLEEP_MIN, max_seconds: int = SLEEP_MAX):
    """
    Random sleep to avoid frequent requests.

    Args:
        min_seconds: Minimum sleep time
        max_seconds: Maximum sleep time
    """
    sleep_time = random.uniform(min_seconds, max_seconds)
    print(f"  ⏱  Resting {sleep_time:.1f}s...")
    time.sleep(sleep_time)


def fetch_a_stock_list(api: ts.pro_api) -> Optional[pd.DataFrame]:
    """
    Fetch A-share stock list.

    Endpoint: stock_basic
    Limit: Max 6000 records (covers entire A-share market)

    Args:
        api: Tushare API instance

    Returns:
        DataFrame with A-share data, or None on failure
    """
    print("\n[1/3] Fetching A-share stock list...")

    try:
        df = api.stock_basic(
            exchange='',        # All exchanges
            list_status='L',    # L: Listed, D: Delisted, P: Suspended
            fields='ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,curr_type,list_status,list_date,delist_date,is_hs,act_name,act_ent_type'
        )

        if df is not None and len(df) > 0:
            print(f"✓ A-share list fetched successfully, total {len(df)} stocks")
            print("  - Exchange distribution:")
            for exchange, count in df['exchange'].value_counts().items():
                print(f"    {exchange}: {count} stocks")
            return df
        else:
            print("[Error] Failed to fetch A-share list")
            return None

    except Exception as e:
        print(f"[Error] Failed to fetch A-share list: {e}")
        return None


def should_fix_a_stock_name(name: str) -> bool:
    """
    Check if an A-share stock name belongs to a status prefix that needs correction.

    Covers new stocks and ex-rights/ex-dividend prefixes:
    XD / XR / DR / N / C
    """
    if name is None:
        return False

    text = str(name).strip()
    if not text or text.lower() in {"nan", "none"}:
        return False

    return bool(A_RK_NAME_PREFIX_RE.match(text))


def chunk_list(items: List[str], chunk_size: int) -> List[List[str]]:
    """Chunk a list into fixed-size sublists."""
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def fetch_rt_k_names(api: ts.pro_api, ts_codes: List[str]) -> Dict[str, str]:
    """
    Fetch stock names in batches via rt_k.

    Reference: https://tushare.pro/wctapi/documents/372.md

    rt_k is A-share real-time daily K-line interface. This script only uses it as a
    secondary source for name backfilling, to correct temporary trading status
    prefix names returned by stock_basic.
    """
    if not ts_codes:
        return {}

    name_map: Dict[str, str] = {}
    batches = chunk_list(ts_codes, A_RK_BATCH_SIZE)

    print(f"\n[rt_k] Stocks to be corrected: {len(ts_codes)}, in {len(batches)} batches...")

    for index, batch in enumerate(batches, start=1):
        ts_code_param = ",".join(batch)
        print(f"  [rt_k] Batch {index}/{len(batches)}: {len(batch)} stocks")

        try:
            df = api.rt_k(ts_code=ts_code_param, fields=A_RK_FIELDS)
        except Exception as e:
            print(f"  [warn] rt_k batch {index} fetch failed: {e}")
            continue

        if df is None or len(df) == 0:
            print(f"  [warn] rt_k batch {index} No data returned")
            continue

        for _, row in df.iterrows():
            code_value = row.get("ts_code", "")
            name_value = row.get("name", "")

            if pd.isna(code_value) or pd.isna(name_value):
                continue

            code = str(code_value).strip()
            name = str(name_value).strip()
            if code and name and code.lower() not in {"nan", "none"} and name.lower() not in {"nan", "none"}:
                name_map[code] = name

        if index < len(batches):
            random_sleep(1, 2)

    print(f"[rt_k] Successfully fetched {len(name_map)} name mappings")
    return name_map


def fix_a_stock_names_with_rt_k(api: ts.pro_api, df: pd.DataFrame) -> pd.DataFrame:
    """
    Use rt_k to correct A-share stock names.

    Only corrects stocks with XD / XR / DR / N / C prefixes.
    """
    if df is None or len(df) == 0:
        return df

    if "name" not in df.columns or "ts_code" not in df.columns:
        print("[warn] A-share data missing ts_code/name columns, skipping rt_k name correction")
        return df

    fix_mask = df["name"].astype(str).map(should_fix_a_stock_name)
    fix_df = df.loc[fix_mask, ["ts_code", "name"]].copy()

    if fix_df.empty:
        print("[rt_k] No A-share names needing correction found")
        return df

    ts_codes = fix_df["ts_code"].astype(str).tolist()
    print(f"[rt_k] Found {len(ts_codes)} A-shares needing correction:")
    print("  " + ", ".join(ts_codes[:20]) + (" ..." if len(ts_codes) > 20 else ""))

    name_map = fetch_rt_k_names(api, ts_codes)
    if not name_map:
        print("[warn] rt_k returned no usable names, keeping original A-share names")
        return df

    fixed_df = df.copy()
    fixed_count = 0
    for code, new_name in name_map.items():
        if not new_name:
            continue
        match_index = fixed_df.index[fixed_df["ts_code"].astype(str) == code]
        if len(match_index) == 0:
            continue

        old_name = str(fixed_df.loc[match_index[0], "name"])
        if old_name != new_name:
            fixed_df.loc[match_index[0], "name"] = new_name
            fixed_count += 1
            print(f"  ✓ {code}: {old_name} -> {new_name}")

    print(f"[rt_k] A-share name correction complete, corrected {fixed_count} stocks")
    return fixed_df


def fetch_hk_stock_list(api: ts.pro_api) -> Optional[pd.DataFrame]:
    """
    Fetch Hong Kong stock list.

    Endpoint: hk_basic
    Limit: All currently listed Hong Kong stocks in one call

    Args:
        api: Tushare API instance

    Returns:
        DataFrame with Hong Kong stock data, or None on failure
    """
    print("\n[2/3] Retrieving Hong Kong stock list...")

    try:
        # Description has reached the last page
        df = api.hk_basic(
            list_status='L'    # L: Listed, D: Delisted
        )

        if df is not None and len(df) > 0:
            print(f"✓ Hong Kong stock list fetched successfully, total {len(df)} stocks")
            return df
        else:
            print("[Error] Hong Kong stock data is empty")
            return None

    except Exception as e:
        print(f"[Error] Failed to fetch Hong Kong stock list: {e}")
        return None


def fetch_us_stock_list(api: ts.pro_api) -> Optional[pd.DataFrame]:
    """
    Fetch US stock list (paginated reading).

    Endpoint: us_basic
    Limit: Max 6000 per page, requires pagination

    Args:
        api: Tushare API instance

    Returns:
        DataFrame with US stock data, or None on failure
    """
    print("\n[3/3] Fetching US stock list (paginated)...")

    all_data = []
    offset = 0
    page = 1

    try:
        while True:
            print(f"  Page {offset // PAGE_SIZE + 1} (offset={offset})...")

            df = api.us_basic(
                offset=offset,
                limit=PAGE_SIZE
            )

            if df is None or len(df) == 0:
                print(f"  ✓ Page {offset // PAGE_SIZE + 1}: no data, done")
                break

            all_data.append(df)
            print(f"  ✓ Page {offset // PAGE_SIZE + 1}: fetched {len(df)} stocks")

            # If returned data is less than page size, we've reached the last page
            if len(df) < PAGE_SIZE:
                break

            offset += PAGE_SIZE
            page += 1

            # Random sleep between pages (not needed on last page)
            random_sleep()

        if all_data:
            result_df = pd.concat(all_data, ignore_index=True)
            print(f"✓ US stock list fetched successfully, total {len(result_df)} stocks ({page} pages)")

            # Stats by category
            if 'classify' in result_df.columns:
                print("  - Classification distribution:")
                for classify, count in result_df['classify'].value_counts().items():
                    print(f"    {classify}: {count} stocks")

            return result_df
        else:
            print("[Error] US stock data is empty")
            return None

    except Exception as e:
        print(f"[Error] Failed to fetch US stock list: {e}")
        return None


def save_to_csv(df: pd.DataFrame, filename: str, market_name: str) -> bool:
    """
    Save data to CSV file.

    Args:
        df: Data DataFrame
        filename: File name
        market_name: Market name (for logging)

    Returns:
        Whether save was successful
    """
    if df is None or len(df) == 0:
        print(f"[skip] {market_name} data is empty, skipping file save")
        return False

    try:
        output_path = OUTPUT_DIR / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        df.to_csv(output_path, index=False, encoding='utf-8-sig')

        file_size = output_path.stat().st_size / 1024  # KB
        print(f"✓ {market_name} data saved: {output_path} ({file_size:.2f} KB)")
        return True

    except Exception as e:
        print(f"[Error] Failed to save {market_name} data: {e}")
        return False


def generate_data_documentation(
    a_df: Optional[pd.DataFrame],
    hk_df: Optional[pd.DataFrame],
    us_df: Optional[pd.DataFrame],
    a_filename: str = "stock_list_a.csv",
    a_title: str = "A-share List"
):
    """
    Generate data documentation.

    Args:
        a_df: A-share data
        hk_df: Hong Kong stock data
        us_df: US stock data
    """
    doc_path = OUTPUT_DIR / "README_stock_list.md"

    content = f"""# Tushare Stock List Data Documentation

> Generated by [Tushare Pro](https://tushare.pro)
> Generation time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## File Description

| File | Description | Record Count |
|------|------|--------|
| `{a_filename}` | {a_title} | {len(a_df) if a_df is not None else 0} |
| `stock_list_hk.csv` | Hong Kong stock list | {len(hk_df) if hk_df is not None else 0} |
| `stock_list_us.csv` | US stock list | {len(us_df) if us_df is not None else 0} |

---

## A-share Data ({a_filename})

### Endpoint
- **Endpoint name**: `stock_basic`
- **Data access**: Requires 2000+ points, 50 requests/minute rate limit
- **Data limit**: Max 6000 records (covers entire A-share market)

### Field Description

| Field Name | Type | Description | Example |
|--------|------|------|------|
| ts_code | str | TS code | 000001.SZ |
| symbol | str | Stock code | 000001 |
| name | str | Stock name | Ping An |
| area | str | Region | Shenzhen |
| industry | str | Industry | Banking |
| fullname | str | Full stock name | Ping An Bank Co., Ltd. |
| enname | str | Full English name | Ping An Bank Co., Ltd. |
| cnspell | str | Pinyin abbreviation | PAYH |
| market | str | Market type | Main board / GEM / STAR / CDR |
| exchange | str | Exchange code | SSE / SZSE / BSE |
| curr_type | str | Trading currency | CNY |
| list_status | str | Listing status | L: Listed / D: Delisted / P: Suspended |
| list_date | str | Listing date | 19910403 |
| delist_date | str | Delisting date | - |
| is_hs | str | Stock Connect eligibility | N: No / H: Shanghai Connect / S: Shenzhen Connect |
| act_name | str | Actual controller name | - |
| act_ent_type | str | Actual controller entity type | - |

### Data Sample
```csv
ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,curr_type,list_status,list_date,delist_date,is_hs,act_name,act_ent_type
000001.SZ,000001,area,Shenzhen,bank,Ping An Bank Co., Ltd.,Ping An Bank Co., Ltd.,PAYH,motherboard,SZSE,CNY,L,19910403,,S,,
000002.SZ,000002,VankeA,Shenzhen,Nationwide Real Estate,Vanke Enterprise Co., Ltd.,China Vanke Co., Ltd.,ZKA,motherboard,SZSE,CNY,L,19910129,,S,,
```

---

## Hong Kong Stock Data (stock_list_hk.csv)

### Endpoint
- **Endpoint name**: `hk_basic`
- **Data access**: Requires 2000+ points minimum
- **Data limit**: All listed Hong Kong stocks can be fetched at once

### Field Description

| Field Name | Type | Description | Example |
|--------|------|------|------|
| ts_code | str | TS code | 00001.HK |
| name | str | Stock abbreviation | Cheung Kong |
| fullname | str | Full company name | Cheung Kong Hutchison Industrial Co., Ltd. |
| enname | str | English name | CK Hutchison Holdings Ltd. |
| cn_spell | str | Pinyin | ZH |
| market | str | Market category | Main board / GEM |
| list_status | str | Listing status | L: Listed / D: Delisted / P: Suspended |
| list_date | str | Listing date | 19720731 |
| delist_date | str | Delisting date | - |
| trade_unit | float | Trading unit | 1000 |
| isin | str | ISIN code | KYG217651051 |
| curr_type | str | Currency code | HKD |

### Data Sample
```csv
ts_code,name,fullname,enname,cn_spell,market,list_status,list_date,delist_date,trade_unit,isin,curr_type
00001.HK,Changhe,Cheung Kong Hutchison Industrial Co., Ltd.,CK Hutchison Holdings Ltd.,ZH,motherboard,L,19720731,,1000,KYG217651051,HKD
00002.HK,CLP Holdings,CLP Power Corporation Limited,CLP Holdings Ltd.,ZDKG,motherboard,L,19860125,,1000,HK0002007356,HKD
```

---

## US Stock Data (stock_list_us.csv)

### Endpoint
- **Endpoint name**: `us_basic`
- **Data access**: 120 points for trial, 5000 points for official access
- **Data limit**: Max 6000 per page, paginated retrieval

### Field Description

| Field Name | Type | Description | Example |
|--------|------|------|------|
| ts_code | str | US stock code | AAPL |
| name | str | Chinese name | Apple |
| enname | str | English name | Apple Inc. |
| classify | str | Classification | ADR/GDR/EQT |
| list_date | str | Listing date | 19801212 |
| delist_date | str | Delisting date | - |

### Classification Description
- **ADR**: American Depositary Receipts
- **GDR**: Global Depositary Receipts
- **EQT**: Common Stock (Equity)

### Data Sample
```csv
ts_code,name,enname,classify,list_date,delist_date
AAPL,apple,Apple Inc.,EQT,19801212,
TSLA,Tesla,Tesla Inc.,EQT,20100629,
BABA,Alibaba,Alibaba Group Holding Ltd.,ADR,20140919,
```

---

## Usage Instructions

### Reading Data

```python
import pandas as pd

# Read A-share data
a_stocks = pd.read_csv('data/{a_filename}')

# Read Hong Kong stock data
hk_stocks = pd.read_csv('data/stock_list_hk.csv')

# Read US stock data
us_stocks = pd.read_csv('data/stock_list_us.csv')
```

### Code Format Description

**A-share Code Format**:
- Shanghai Stock Exchange: `600000.SH` (Main board), `688xxx.SH` (STAR Market), `900xxx.SH` (B-shares)
- Shenzhen Stock Exchange: `000001.SZ` (Main board), `300xxx.SZ` (ChiNext), `200xxx.SZ` (B-shares)
- Beijing Stock Exchange: `8xxxxx.BJ`, `4xxxxx.BJ`, `920xxx.BJ`

**Hong Kong Stock Code Format**:
- Format: `xxxxx.HK` (5 digits + .HK)
- Example: `00700.HK` (Tencent Holdings)

**US Stock Code Format**:
- Format: Letter code (no suffix)
- Example: `AAPL` (Apple), `TSLA` (Tesla)

---

## Notes

1. **Data updates**: It is recommended to update data regularly (e.g., once a month)
2. **Points requirements**:
   - A-share / Hong Kong: Requires 2000 points
   - US stocks: 120 points (trial), 5000 points (official)
3. **Request limits**: Please note the API per-minute request limit
4. **Data completeness**: This data only contains basic information; for more data please refer to Tushare official documentation

---

## Related Links

- [Tushare Official Website](https://tushare.pro)
- [Tushare Documentation](https://tushare.pro/document/2)
- [How to Get Points](https://tushare.pro/document/1)
- [API Build command line parameters](https://tushare.pro/document/2)
"""

    try:
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Data documentation generated: {doc_path}")
    except Exception as e:
        print(f"[Error] Failed to generate documentation: {e}")


def build_arg_parser() -> argparse.ArgumentParser:
    """Build command line arguments."""
    parser = argparse.ArgumentParser(description="Tushare Stock List Fetch Tool")
    parser.add_argument(
        "--a-rk",
        action="store_true",
        help="Use rt_k to correct A-share names with XD/XR/DR/N/C prefixes, and overwrite stock_list_a.csv",
    )
    return parser


def main(argv: Optional[List[str]] = None):
    """Main function"""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    print("=" * 60)
    print("Tushare Stock List Fetch Tool")
    print("=" * 60)
    print(f"[info] A-rk mode: {'enabled' if args.a_rk else 'disabled'}")

    # 1. Get API instance
    api = get_tushare_api()
    if not api:
        return 1

    # 2. Get A-share data
    a_df = fetch_a_stock_list(api)
    if a_df is not None:
        a_filename = 'stock_list_a.csv'
        a_title = 'A-share List'
        a_market_name = 'A-share'

        if args.a_rk:
            a_df = fix_a_stock_names_with_rt_k(api, a_df)
            a_title = 'A-share List (corrected)'

        save_to_csv(a_df, a_filename, a_market_name)

    # 3. Get Hong Kong stock data
    random_sleep()  # Rest before fetching Hong Kong stocks
    hk_df = fetch_hk_stock_list(api)
    if hk_df is not None:
        save_to_csv(hk_df, 'stock_list_hk.csv', 'Hong Kong')

    # 4. Get US stock data (paginated)
    random_sleep()  # Rest before fetching US stocks
    us_df = fetch_us_stock_list(api)
    if us_df is not None:
        save_to_csv(us_df, 'stock_list_us.csv', 'US')

    # 5. Generate data documentation
    print("\nGenerating data documentation...")
    a_filename = 'stock_list_a.csv'
    a_title = 'A-share List (corrected)' if args.a_rk else 'A-share List'
    generate_data_documentation(a_df, hk_df, us_df, a_filename=a_filename, a_title=a_title)

    # 6. Summary
    print("\n" + "=" * 60)
    print("Mission accomplished!")
    print("=" * 60)

    total_count = 0
    if a_df is not None:
        total_count += len(a_df)
        print(f"  ✓ A-share: {len(a_df)} stocks")
    if hk_df is not None:
        total_count += len(hk_df)
        print(f"  ✓ Hong Kong: {len(hk_df)} stocks")
    if us_df is not None:
        total_count += len(us_df)
        print(f"  ✓ US: {len(us_df)} stocks")

    print(f"\nTotal: {total_count} stocks")
    print(f"Output directory: {OUTPUT_DIR}")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[Interrupt] User cancelled operation")
        sys.exit(1)
    except Exception as e:
        print(f"\n[Error] Unexpected exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
