#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test generate_index_from_csv.py
"""

import csv
import json
import pytest
from pathlib import Path
from typing import Dict, List

# Add scripts directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from generate_index_from_csv import (
    extract_symbol_from_ts_code,
    get_stock_name,
    get_us_delist_priority,
    parse_stock_row,
    determine_market,
    generate_aliases,
    normalize_name_for_pinyin,
    normalize_stock_name_for_index,
    generate_pinyin,
    main,
    compress_index,
    build_stock_index,
    load_tushare_data,
    load_akshare_data,
)


class TestExtractSymbol:
    """Test the Symbol extraction function"""

    def test_a_stock_sz(self):
        """Test A-share Shenzhen"""
        result = extract_symbol_from_ts_code("000001.SZ", "CN")
        assert result == "000001"

    def test_a_stock_sh(self):
        """Test A-share Shanghai"""
        result = extract_symbol_from_ts_code("600519.SH", "CN")
        assert result == "600519"

    def test_hk_stock(self):
        """Test Hong Kong stocks"""
        result = extract_symbol_from_ts_code("00700.HK", "HK")
        assert result == "00700"

    def test_us_stock(self):
        """Test US stocks"""
        result = extract_symbol_from_ts_code("AAPL", "US")
        assert result == "AAPL"

    def test_jp_stock_preserves_suffix(self):
        """Test JP stocks keep the Yahoo suffix to avoid bare-code collisions"""
        result = extract_symbol_from_ts_code("7203.T", "JP")
        assert result == "7203.T"

    def test_kr_stock_preserves_suffix(self):
        """Test KR stocks keep the Yahoo suffix to avoid bare-code collisions"""
        result = extract_symbol_from_ts_code("005930.KS", "KR")
        assert result == "005930.KS"

    def test_empty_ts_code(self):
        """Test empty ts_code"""
        result = extract_symbol_from_ts_code("", "CN")
        assert result is None

    def test_none_ts_code(self):
        """Test None ts_code"""
        result = extract_symbol_from_ts_code(None, "CN")
        assert result is None


class TestDetermineMarket:
    """Test the market-judgment function"""

    def test_a_stock_sz(self):
        """Test A-share Shenzhen"""
        result = determine_market("000001.SZ")
        assert result == "CN"

    def test_a_stock_sh(self):
        """Test A-share Shanghai"""
        result = determine_market("600519.SH")
        assert result == "CN"

    def test_hk_stock(self):
        """Test Hong Kong stocks"""
        result = determine_market("00700.HK")
        assert result == "HK"

    def test_bse_stock(self):
        """Test Beijing Stock Exchange"""
        result = determine_market("832566.BJ")
        assert result == "BSE"

    def test_us_stock(self):
        """Test US stocks"""
        result = determine_market("AAPL")
        assert result == "US"

    def test_us_stock_tesla(self):
        """Test US stock Tesla"""
        result = determine_market("TSLA")
        assert result == "US"

    def test_us_stock_with_dot_suffix(self):
        """Test US stock with dotted suffix (BRK.B)"""
        result = determine_market("BRK.B")
        assert result == "US"

    def test_us_stock_class_a(self):
        """Test US class-A share (GOOG.A)"""
        result = determine_market("GOOG.A")
        assert result == "US"

    def test_us_stock_units(self):
        """Test US Unit (AAPL.U)"""
        result = determine_market("AAPL.U")
        assert result == "US"

    def test_jp_stock_with_yahoo_suffix(self):
        """Test JP stock Yahoo suffix"""
        result = determine_market("7203.T")
        assert result == "JP"

    def test_kr_kospi_stock_with_yahoo_suffix(self):
        """Test KR KOSPI Yahoo suffix"""
        result = determine_market("005930.KS")
        assert result == "KR"

    def test_kr_kosdaq_stock_with_yahoo_suffix(self):
        """Test KR KOSDAQ Yahoo suffix"""
        result = determine_market("035720.KQ")
        assert result == "KR"


class TestGetStockName:
    """Test the stock-name getter function"""

    def test_cn_stock_name(self):
        """Test A-share uses the name field"""
        row = {'name': 'Ping An Bank', 'enname': 'Ping An Bank'}
        result = get_stock_name(row, 'CN')
        assert result == 'Ping An Bank'

    def test_hk_stock_name(self):
        """Test HK stock uses the name field"""
        row = {'name': 'Tencent Holdings', 'enname': 'Tencent'}
        result = get_stock_name(row, 'HK')
        assert result == 'Tencent Holdings'

    def test_us_stock_name(self):
        """Test US stock uses the enname field"""
        row = {'name': 'apple', 'enname': 'Apple Inc.'}
        result = get_stock_name(row, 'US')
        assert result == 'Apple Inc.'

    def test_empty_name(self):
        """Test empty name"""
        row = {'name': '', 'enname': ''}
        result = get_stock_name(row, 'CN')
        assert result is None

    def test_cn_stock_name_strips_ex_rights_prefix(self):
        """Test A-share ex-rights/ex-dividend short prefixes are not written into the long-term index name"""
        row = {'name': 'XDtibetan medicine', 'enname': ''}
        result = get_stock_name(row, 'CN')
        assert result == 'tibetan medicine'

    def test_cn_stock_name_preserves_new_stock_prefix(self):
        """Test A-share new-stock prefix is retained, then naturally disappears when later data refreshes"""
        row = {'name': 'NWellcome', 'enname': ''}
        result = get_stock_name(row, 'CN')
        assert result == 'NWellcome'


class TestDataCleaning:
    """Test the data-cleaning logic"""

    def test_valid_cn_stock(self):
        """Test a valid A-share record"""
        row = {
            'ts_code': '000001.SZ',
            'symbol': '000001',
            'name': 'Ping An Bank'
        }
        result = parse_stock_row(row, 'CN')
        assert result is not None
        assert result['ts_code'] == '000001.SZ'
        assert result['symbol'] == '000001'
        assert result['name'] == 'Ping An Bank'
        assert result['market'] == 'CN'

    def test_valid_hk_stock(self):
        """Test a valid HK stock record"""
        row = {
            'ts_code': '00700.HK',
            'name': 'Tencent Holdings',
            'enname': 'Tencent'
        }
        result = parse_stock_row(row, 'HK')
        assert result is not None
        assert result['ts_code'] == '00700.HK'
        assert result['symbol'] == '00700'
        assert result['name'] == 'Tencent Holdings'
        assert result['market'] == 'HK'

    def test_valid_us_stock(self):
        """Test a valid US stock record"""
        row = {
            'ts_code': 'AAPL',
            'name': 'apple',
            'enname': 'Apple Inc.'
        }
        result = parse_stock_row(row, 'US')
        assert result is not None
        assert result['ts_code'] == 'AAPL'
        assert result['symbol'] == 'AAPL'
        assert result['name'] == 'Apple Inc.'
        assert result['market'] == 'US'

    def test_valid_us_stock_with_dot_suffix(self):
        """Test a valid US stock record (with dotted suffix, e.g. BRK.B)"""
        row = {
            'ts_code': 'BRK.B',
            'name': '',
            'enname': "BERKSHIRE HATHAWAY 'B'"
        }
        result = parse_stock_row(row, None)
        assert result is not None
        assert result['ts_code'] == 'BRK.B'
        assert result['symbol'] == 'BRK.B'
        assert result['name'] == "BERKSHIRE HATHAWAY 'B'"
        assert result['market'] == 'US'

    def test_valid_jp_stock_with_seed_aliases(self):
        """Test a valid JP seed record"""
        row = {
            'ts_code': '7203.T',
            'name': 'Toyota Motor',
            'enname': 'Toyota Motor Corporation',
            'aliases': 'Toyota|Toyota Motor|toyota'
        }
        result = parse_stock_row(row, 'JP')
        assert result is not None
        assert result['ts_code'] == '7203.T'
        assert result['symbol'] == '7203.T'
        assert result['name'] == 'Toyota Motor'
        assert result['market'] == 'JP'
        assert result['aliases'] == ['Toyota', 'Toyota Motor', 'toyota']

    def test_valid_kr_stock_with_seed_aliases(self):
        """Test a valid KR seed record"""
        row = {
            'ts_code': '005930.KS',
            'name': 'Samsung Electronics',
            'enname': 'Samsung Electronics',
            'aliases': 'Samsung|Samsung Electronics|Samsung'
        }
        result = parse_stock_row(row, 'KR')
        assert result is not None
        assert result['ts_code'] == '005930.KS'
        assert result['symbol'] == '005930.KS'
        assert result['name'] == 'Samsung Electronics'
        assert result['market'] == 'KR'
        assert result['aliases'] == ['Samsung', 'Samsung Electronics', 'Samsung']

    def test_us_dummy_filtered(self):
        """Test US DUMMY record is filtered out"""
        row = {
            'ts_code': 'DUMMY001',
            'name': 'test',
            'enname': 'DUMMY Test Stock'
        }
        result = parse_stock_row(row, 'US')
        assert result is None

    def test_us_dummy_case_insensitive(self):
        """Test DUMMY filtering is case-insensitive"""
        row = {
            'ts_code': 'DUMMY002',
            'name': 'test',
            'enname': 'dummy test stock'
        }
        result = parse_stock_row(row, 'US')
        assert result is None

    def test_empty_ts_code(self):
        """Test empty ts_code is filtered out"""
        row = {
            'ts_code': '',
            'symbol': '000001',
            'name': 'Ping An Bank'
        }
        result = parse_stock_row(row, 'CN')
        assert result is None

    def test_empty_name(self):
        """Test empty name is filtered out"""
        row = {
            'ts_code': '000001.SZ',
            'symbol': '000001',
            'name': ''
        }
        result = parse_stock_row(row, 'CN')
        assert result is None

    def test_us_empty_enname(self):
        """Test US empty enname is filtered out"""
        row = {
            'ts_code': 'AAPL',
            'name': 'apple',
            'enname': ''
        }
        result = parse_stock_row(row, 'US')
        assert result is None

    def test_us_delist_priority_prefers_blank_over_nat(self):
        """Test US dedup priority: empty delist_date takes precedence over NaT"""
        assert get_us_delist_priority({'delist_date': ''}) == 2
        assert get_us_delist_priority({'delist_date': 'NaT'}) == 1
        assert get_us_delist_priority({'delist_date': '20250131'}) == 0


class TestNormalizeStockNameForIndex:
    """Test index-name normalization"""

    def test_strips_a_share_ex_rights_prefixes(self):
        assert normalize_stock_name_for_index('XDtibetan medicine', 'CN') == 'tibetan medicine'
        assert normalize_stock_name_for_index('XRExample stocks', 'CN') == 'Example stocks'
        assert normalize_stock_name_for_index('DRRoman shares', 'CN') == 'Roman shares'
        assert normalize_stock_name_for_index('XDZhu Laoliu', 'BSE') == 'Zhu Laoliu'

    def test_preserves_a_share_new_stock_and_st_prefixes(self):
        assert normalize_stock_name_for_index('NWellcome', 'CN') == 'NWellcome'
        assert normalize_stock_name_for_index('CTianhai', 'CN') == 'CTianhai'
        assert normalize_stock_name_for_index('STNeptune', 'CN') == 'STNeptune'
        assert normalize_stock_name_for_index('*STbeauty', 'CN') == '*STbeauty'

    def test_does_not_strip_other_markets(self):
        assert normalize_stock_name_for_index('DRAGONFLY ENERGY', 'US') == 'DRAGONFLY ENERGY'
        assert normalize_stock_name_for_index('XDHong Kong Stock Example', 'HK') == 'XDHong Kong Stock Example'


class TestAliases:
    """Test the alias-generation function"""

    def test_cn_aliases(self):
        """Test A-share alias"""
        result = generate_aliases('Kweichow Moutai', 'CN')
        assert 'Moutai' in result

    def test_hk_aliases(self):
        """Test HK stock alias"""
        result = generate_aliases('Tencent Holdings', 'HK')
        assert 'Tencent' in result or 'Tencent' in result

    def test_us_aliases(self):
        """Test US stock alias"""
        result = generate_aliases('Apple Inc.', 'US')
        assert 'Apple' in result or 'AAPL' in result

    def test_no_aliases(self):
        """Test the no-alias case"""
        result = generate_aliases('unknown stock', 'CN')
        assert result == []


class TestOutputFormat:
    """Test output format"""

    def test_compress_index_field_order(self):
        """Test the field order of the compressed format"""
        index = [{
            "canonicalCode": "000001.SZ",
            "displayCode": "000001",
            "nameZh": "Ping An Bank",
            "pinyinFull": "pinganyinhang",
            "pinyinAbbr": "pyyh",
            "aliases": ["flat silver"],
            "market": "CN",
            "assetType": "stock",
            "active": True,
            "popularity": 100,
        }]

        compressed = compress_index(index)

        assert len(compressed) == 1
        item = compressed[0]

        # Verify field order
        assert item[0] == "000001.SZ"      # canonicalCode
        assert item[1] == "000001"         # displayCode
        assert item[2] == "Ping An Bank"       # nameZh
        assert item[3] == "pinganyinhang"  # pinyinFull
        assert item[4] == "pyyh"           # pinyinAbbr
        assert item[5] == ["flat silver"]         # aliases
        assert item[6] == "CN"             # market
        assert item[7] == "stock"          # assetType
        assert item[8] == True             # active
        assert item[9] == 100              # popularity

    def test_compress_index_field_count(self):
        """Test the field count of the compressed format"""
        index = [{
            "canonicalCode": "AAPL",
            "displayCode": "AAPL",
            "nameZh": "Apple Inc.",
            "pinyinFull": None,
            "pinyinAbbr": None,
            "aliases": [],
            "market": "US",
            "assetType": "stock",
            "active": True,
            "popularity": 100,
        }]

        compressed = compress_index(index)
        assert len(compressed[0]) == 10  # 10fields

    def test_json_serialization(self):
        """Test JSON serialization"""
        index = [{
            "canonicalCode": "00700.HK",
            "displayCode": "00700",
            "nameZh": "Tencent Holdings",
            "pinyinFull": "xunxiongkonggu",
            "pinyinAbbr": "xxkg",
            "aliases": ["Tencent"],
            "market": "HK",
            "assetType": "stock",
            "active": True,
            "popularity": 100,
        }]

        compressed = compress_index(index)

        # Should serialize to JSON successfully
        json_str = json.dumps(compressed, ensure_ascii=False)
        assert json_str is not None

        # Should deserialize successfully
        loaded = json.loads(json_str)
        assert len(loaded) == 1


class TestIntegration:
    """Integration tests"""

    def test_full_workflow_tushare(self, tmp_path):
        """Test the complete Tushare workflow"""
        # Create the test CSV file
        a_csv = tmp_path / 'stock_list_a.csv'
        with open(a_csv, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['ts_code', 'symbol', 'name'])
            writer.writeheader()
            writer.writerow({
                'ts_code': '000001.SZ',
                'symbol': '000001',
                'name': 'Ping An Bank'
            })

        hk_csv = tmp_path / 'stock_list_hk.csv'
        with open(hk_csv, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['ts_code', 'name', 'enname'])
            writer.writeheader()
            writer.writerow({
                'ts_code': '00700.HK',
                'name': 'Tencent Holdings',
                'enname': 'Tencent'
            })

        us_csv = tmp_path / 'stock_list_us.csv'
        with open(us_csv, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['ts_code', 'name', 'enname'])
            writer.writeheader()
            writer.writerow({
                'ts_code': 'AAPL',
                'name': 'apple',
                'enname': 'Apple Inc.'
            })

        jp_csv = tmp_path / 'stock_list_jp.csv'
        with open(jp_csv, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['ts_code', 'name', 'enname', 'aliases'])
            writer.writeheader()
            writer.writerow({
                'ts_code': '7203.T',
                'name': 'Toyota Motor',
                'enname': 'Toyota Motor Corporation',
                'aliases': 'Toyota|toyota'
            })

        kr_csv = tmp_path / 'stock_list_kr.csv'
        with open(kr_csv, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['ts_code', 'name', 'enname', 'aliases'])
            writer.writeheader()
            writer.writerow({
                'ts_code': '005930.KS',
                'name': 'Samsung Electronics',
                'enname': 'Samsung Electronics',
                'aliases': 'Samsung|Samsung'
            })

        # Load data
        stocks = load_tushare_data(tmp_path)

        # Verify data
        assert len(stocks) == 5

        # Build the index
        index = build_stock_index(stocks)

        # Verify the index
        assert len(index) == 5
        assert next(item for item in index if item['canonicalCode'] == '7203.T')['aliases'] == ['Toyota', 'toyota']
        assert next(item for item in index if item['canonicalCode'] == '005930.KS')['aliases'] == ['Samsung', 'Samsung']

        # Compress the index
        compressed = compress_index(index)

        # Verify the compression
        assert len(compressed) == 5

        # Verify the field count
        for item in compressed:
            assert len(item) == 10

    def test_market_distribution(self, tmp_path):
        """Test market-distribution statistics"""
        # Create test data
        csv_file = tmp_path / 'stock_list_a.csv'
        with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['ts_code', 'symbol', 'name'])
            writer.writeheader()
            writer.writerow({'ts_code': '000001.SZ', 'symbol': '000001', 'name': 'Ping An Bank'})
            writer.writerow({'ts_code': '600519.SH', 'symbol': '600519', 'name': 'Kweichow Moutai'})
            writer.writerow({'ts_code': '832566.BJ', 'symbol': '832566', 'name': 'Zicheng Technology'})

        stocks = load_tushare_data(tmp_path)
        index = build_stock_index(stocks)

        # Tally the market distribution
        market_stats = {}
        for item in index:
            market = item['market']
            market_stats[market] = market_stats.get(market, 0) + 1

        # Verify the statistics
        assert market_stats.get('CN', 0) == 2  # SZ, SH
        assert market_stats.get('BSE', 0) == 1  # BJ

    def test_us_reused_symbols_are_deduplicated(self, tmp_path):
        """Test that US reused tickers are deduplicated first when loaded"""
        us_csv = tmp_path / 'stock_list_us.csv'
        with open(us_csv, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['ts_code', 'name', 'enname', 'list_date', 'delist_date']
            )
            writer.writeheader()
            writer.writerow({
                'ts_code': 'B',
                'name': '',
                'enname': 'BARNES GROUP',
                'list_date': '19631014',
                'delist_date': 'NaT',
            })
            writer.writerow({
                'ts_code': 'B',
                'name': '',
                'enname': 'BARRICK MINING (NYS)',
                'list_date': '19850213',
                'delist_date': '',
            })
            writer.writerow({
                'ts_code': 'DOC',
                'name': '',
                'enname': 'HEALTHPEAK PROPERTIES',
                'list_date': '19850523',
                'delist_date': '',
            })
            writer.writerow({
                'ts_code': 'DOC',
                'name': '',
                'enname': 'PHYSICIANS REALTY TST.',
                'list_date': '20130719',
                'delist_date': '',
            })
            writer.writerow({
                'ts_code': 'SPWR',
                'name': '',
                'enname': 'COMPLETE SOLARIA',
                'list_date': '20210419',
                'delist_date': '',
            })
            writer.writerow({
                'ts_code': 'SPWR',
                'name': '',
                'enname': 'SUNPOWER',
                'list_date': '20051109',
                'delist_date': 'NaT',
            })

        stocks = load_tushare_data(tmp_path)

        assert len(stocks) == 3
        assert {stock['ts_code'] for stock in stocks} == {'B', 'DOC', 'SPWR'}
        assert next(stock for stock in stocks if stock['ts_code'] == 'B')['name'] == 'BARRICK MINING (NYS)'
        assert next(stock for stock in stocks if stock['ts_code'] == 'DOC')['name'] == 'HEALTHPEAK PROPERTIES'
        assert next(stock for stock in stocks if stock['ts_code'] == 'SPWR')['name'] == 'COMPLETE SOLARIA'


class TestPinyin:
    """Test pinyin generation"""

    def test_normalize_name(self):
        """Test name normalization"""
        # Test ST prefix removal
        result = normalize_name_for_pinyin('*STSafety')
        assert 'ST' not in result

        # Test N prefix removal
        result = normalize_name_for_pinyin('NPing An Bank')
        assert 'N' not in result

    def test_generate_pinyin(self):
        """Test pinyin generation"""
        pinyin_full, pinyin_abbr = generate_pinyin('Ping An Bank')
        assert pinyin_full == 'pinganyinhang'
        assert pinyin_abbr == 'payh'

    def test_generate_pinyin_requires_dependency(self, monkeypatch):
        """Test that no degraded pinyin field is generated when pypinyin is missing"""
        import generate_index_from_csv

        monkeypatch.setattr(generate_index_from_csv, 'PYPINYIN_AVAILABLE', False)

        with pytest.raises(RuntimeError, match='pypinyin is required'):
            generate_index_from_csv.generate_pinyin('Ping An Bank')

    def test_main_fails_without_pypinyin(self, monkeypatch):
        """Test that pypinyin is required before formally generating the index"""
        import generate_index_from_csv

        monkeypatch.setattr(generate_index_from_csv, 'PYPINYIN_AVAILABLE', False)
        monkeypatch.setattr(sys, 'argv', ['generate_index_from_csv.py'])

        assert main() == 1
