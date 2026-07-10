# Tushare Stock List Retrieval Tool Guide

## Overview

Retrieves A-share, Hong Kong stock, and US stock list information from Tushare Pro and saves them as CSV files locally.

## Quick Start

### 1. Configure Token

Add the Tushare Token to the `.env` file in the project root directory:

```bash
TUSHARE_TOKEN=your_tushare_token
```

> Get your Token: Visit [Tushare Pro](https://tushare.pro/weborder/#/login) to register and obtain one.

### 2. Run the Script

```bash
python3 scripts/fetch_tushare_stock_list.py
```

To correct A-share name statuses, add `--a-rk`. The script will keep `stock_basic` as the base source, then use `rt_k` to backfill names with `XD`, `XR`, `DR`, `N`, `C` prefixes and overwrite the output to `data/stock_list_a.csv`:

```bash
python3 scripts/fetch_tushare_stock_list.py --a-rk
```

### 3. View Output

Data will be saved to the `data/` directory:

```
data/
├── stock_list_a.csv       # A-share list (--a-rk produces corrected names)
├── stock_list_hk.csv      # Hong Kong stock list
├── stock_list_us.csv      # US stock list
└── README_stock_list.md   # Data documentation
```

## Features

✅ **Auto-pagination**: US stock data is read with automatic pagination (5000 records per page)
✅ **Smart rate limiting**: Random 5-10 second pauses between requests
✅ **Error handling**: Failure in one market does not affect other markets
✅ **Progress display**: Real-time read progress
✅ **Auto-documentation**: Generates detailed data documentation

## Market Notes

| Market | API Endpoint | Points Required | Data Volume |
|------|------|----------|--------|
| A-shares | stock_basic | 2000 points | ~5000 stocks |
| Hong Kong | hk_basic | 2000 points | ~2000 stocks |
| US | us_basic | 120 trial / 5000 official | ~10000 stocks |

## Output File Format

### A-shares (stock_list_a.csv)

When `--a-rk` is executed, this file contains corrected A-share names.

```csv
ts_code,symbol,name,area,industry,market,exchange,list_date,...
000001.SZ,000001,Ping An Bank,Shenzhen,Banking,Main Board,SZSE,19910403,...
600519.SH,600519,Kweichow Moutai,Guizhou,Liquor,Main Board,SSE,20010827,...
```

### Hong Kong (stock_list_hk.csv)

```csv
ts_code,name,fullname,market,list_date,trade_unit,curr_type,...
00700.HK,Tencent Holdings,Tencent Holdings Ltd.,Main Board,20040616,100,HKD,...
00005.HK,HSBC Holdings,HSBC Holdings plc,Main Board,19750401,100,HKD,...
```

### US (stock_list_us.csv)

```csv
ts_code,name,enname,classify,list_date,...
AAPL,Apple,Apple Inc.,EQT,19801212,...
TSLA,Tesla,Tesla Inc.,EQT,20100629,...
BABA,Alibaba,Alibaba Group,ADR,20140919,...
```

## Usage Examples

### Reading Data with Python

```python
import pandas as pd

# Read A-shares
a_stocks = pd.read_csv('data/stock_list_a.csv')
print(f"A-share count: {len(a_stocks)}")

# Filter main board stocks
main_board = a_stocks[a_stocks['market'] == 'Main Board']
print(f"Main board count: {len(main_board)}")

# Find a specific stock
stock = a_stocks[a_stocks['ts_code'] == '600519.SH']
print(stock[['name', 'industry', 'list_date']])
```

### Refreshing Stock Autocomplete Index

It is recommended to use the one-click refresh script, which defaults to using `--a-rk` when fetching A-shares and then generates and syncs the autocomplete index:

```bash
pip install -r requirements.txt
python3 scripts/refresh_stock_index.py
```

Generating the autocomplete index depends on `pypinyin` for writing full pinyin and initial pinyin fields for Chinese stock names; without this dependency the script fails directly, avoiding generation of degraded indexes that cannot support pinyin search.

If you only want to update the CSV, fetch data first:

```bash
python3 scripts/fetch_tushare_stock_list.py --a-rk
```

If you already have new CSVs and only want to regenerate the index:

```bash
python3 scripts/generate_index_from_csv.py --test  # Test first
python3 scripts/generate_index_from_csv.py         # Generate after confirmation
```

### Local Client Auto-Retrieval of Latest Index

Newer clients default to reading the latest `apps/dsa-web/public/stocks.index.json` from the project's GitHub `main` branch, caching it locally at `data/cache/stocks.index.json`. The frontend still accesses the local `/stocks.index.json` without making cross-origin requests to GitHub.

Remote index address, check frequency, and network timeout are built-in system values with no user configuration; users only need to decide whether to enable:

```bash
STOCK_INDEX_REMOTE_UPDATE_ENABLED=true
```

When enabled by default, the system checks for updates at most every 48 hours. If the runtime cannot access GitHub raw, requests timeout, or the returned content is not a valid stock index, the app retains the existing cache; if there is no remote cache, it continues using the built-in index bundled with the application. Remote update failures do not block WebUI startup, stock autocomplete, or analysis flow; after consecutive failures reach the built-in threshold, retries are paused within the current process until the next 48-hour window.

## Notes

1. **Points requirement**: Ensure your account has sufficient points (A-shares/Hong Kong: 2000, US: 120 trial)
2. **Request limits**: Be aware of API per-minute request limits
3. **Data updates**: Maintainers are advised to refresh every three days and commit to the repository; local clients default to checking for index updates on GitHub `main` at most every 48 hours. Future automation via GitHub Actions workflow for refresh and PR submission is planned.
4. **Network connection**: Requires a stable network connection

## FAQ

### Q: "TUSHARE_TOKEN not found" message?
**A**: Configure `TUSHARE_TOKEN=your_token` in the `.env` file.

### Q: "Insufficient account points" message?
**A**:
- A-shares/Hong Kong require 2000 points
- US requires 120 trial points, 5000 for official access
- Visit https://tushare.pro to check how to earn points

### Q: What if retrieval fails?
**A**:
1. Check network connection
2. Check Token is correct
3. Check account points are sufficient
4. The current script does not retry automatically; on a single request failure, it outputs an error and exits. Investigate the cause and re-run.

### Q: Data update frequency?
**A**: For maintainers, local CSVs and repository indexes should be updated every three days and committed to the repository; high-impact events like delisting/name changes may warrant a temporary refresh. Future automation via GitHub Actions workflow for refresh and PR submission is planned. For ordinary local clients, the system defaults to checking GitHub `main` for the latest index at most every 48 hours.

### Q: Does inability to access GitHub raw affect usage?
**A**: No. Remote index updates are best-effort: on failure, it continues using existing remote caches or the built-in index bundled with the application; if the index is completely unavailable, Web autocomplete enters the existing fallback and stock codes can still be entered manually.

## Related Links

- [Tushare Official Site](https://tushare.pro)
- [Tushare Documentation](https://tushare.pro/document/2)
- [Points Acquisition Guide](https://tushare.pro/document/1)
- [API Data Debugging](https://tushare.pro/document/2)
