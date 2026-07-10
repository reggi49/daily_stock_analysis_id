# -*- coding: utf-8 -*-
"""
===================================
AStock selection intelligent analysis system - Environmental validation testing
===================================

For verifying whether .env is configured correctly, including:
1. Configure load test
2. Database view
3. Data source testing
4. LLM Call test
5. How to use

Usage:
    python scripts/check_env.py              # Run all tests
    python scripts/check_env.py --db         # View database only
    python scripts/check_env.py --llm        # Test LLM only
    python scripts/check_env.py --fetch      # Test data fetch only
    python scripts/check_env.py --notify     # Test notification only

"""
import os
# Proxy config - controlled by USE_PROXY env var, off by default.
# Set USE_PROXY=true in .env if you need a local proxy (e.g. mainland China).
# GitHub Actions always skips this regardless of USE_PROXY.
if os.getenv("GITHUB_ACTIONS") != "true" and os.getenv("USE_PROXY", "false").lower() == "true":
    proxy_host = os.getenv("PROXY_HOST", "127.0.0.1")
    proxy_port = os.getenv("PROXY_PORT", "10809")
    proxy_url = f"http://{proxy_host}:{proxy_port}"
    os.environ["http_proxy"] = proxy_url
    os.environ["https_proxy"] = proxy_url

import argparse
import logging
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _reconfigure_output_stream(stream):
    """Avoid UnicodeEncodeError on legacy Windows console code pages."""
    reconfigure = getattr(stream, "reconfigure", None)
    if not callable(reconfigure):
        return

    for kwargs in (
        {"encoding": "utf-8", "errors": "replace"},
        {"errors": "replace"},
    ):
        try:
            reconfigure(**kwargs)
            return
        except Exception:
            continue


def configure_console_encoding():
    for stream in (sys.stdout, sys.stderr):
        _reconfigure_output_stream(stream)


# Query recent
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def print_header(title: str):
    """Print title"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_section(title: str):
    """Print section"""
    print(f"\n--- {title} ---")


def check_config():
    """Test configuration loading"""
    print_header("1. Configuration Load Test")
    
    from src.config import get_config
    config = get_config()
    
    print_section("Basic Configuration")
    print(f"  stock list: {config.stock_list}")
    print(f"  Database path: {config.database_path}")
    print(f"  Maximum concurrent workers: {config.max_workers}")
    print(f"  Debug mode: {config.debug}")
    
    print_section("API Configuration")
    print(f"  Tushare Token: {'Configured ✓' if config.tushare_token else 'Not configured ✗'}")
    if config.tushare_token:
        print(f"    Token Bit8Bit: {config.tushare_token[:8]}...")
    
    print(f"  Gemini API Key: {'Configured ✓' if config.gemini_api_key else 'Not configured ✗'}")
    if config.gemini_api_key:
        print(f"    Key Bit8Bit: {config.gemini_api_key[:8]}...")
    print(f"  Gemini primary model: {config.gemini_model}")
    print(f"  Gemini fallback model: {config.gemini_model_fallback}")
    
    print(f"  Enterprise WeChat Webhook: {'Configured ✓' if config.wechat_webhook_url else 'Not configured ✗'}")
    
    print_section("Configuration Validation")
    issues = config.validate_structured()
    _prefix = {"error": "  ✗", "warning": "  ⚠", "info": "  ·"}
    for issue in issues:
        print(f"{_prefix.get(issue.severity, '  ?')} [{issue.severity.upper()}] {issue.message}")
    if not any(i.severity in ("error", "warning") for i in issues):
        print("  ✓ Key configuration items passed verification")
    
    return True


def view_database():
    """View database contents"""
    print_header("2. Database Contents")
    
    from src.storage import get_db
    from sqlalchemy import text
    
    db = get_db()
    
    print_section("Database Connection")
    print(f"  ✓ Connection successful")
    
    # Query recent session Query today's data
    session = db.get_session()
    try:
        # Query data
        result = session.execute(text("""
            SELECT 
                code,
                COUNT(*) as count,
                MIN(date) as min_date,
                MAX(date) as max_date,
                data_source
            FROM stock_daily 
            GROUP BY code
            ORDER BY code
        """))
        stocks = result.fetchall()
        
        print_section(f"Stored Stock Data (total {len(stocks)} stocks)")
        if stocks:
            print(f"  {'Code':<10} {'Records':<8} {'Start Date':<12} {'Latest Date':<12} {'Source'}")
            print("  " + "-" * 60)
            for row in stocks:
                print(f"  {row[0]:<10} {row[1]:<8} {row[2]!s:<12} {row[3]!s:<12} {row[4] or 'Unknown'}")
        else:
            print("  No data yet")
        
        # Query today's data
        today = date.today()
        result = session.execute(text("""
            SELECT code, date, open, high, low, close, pct_chg, volume, ma5, ma10, ma20, volume_ratio
            FROM stock_daily 
            WHERE date = :today
            ORDER BY code
        """), {"today": today})
        today_data = result.fetchall()
        
        print_section(f"Today's Data ({today})")
        if today_data:
            for row in today_data:
                code, dt, open_, high, low, close, pct_chg, volume, ma5, ma10, ma20, vol_ratio = row
                print(f"\n  【{code}】")
                print(f"    Open: {open_:.2f}  High: {high:.2f}  Low: {low:.2f}  Close: {close:.2f}")
                print(f"    Change: {pct_chg:.2f}%  Volume: {volume/10000:.2f} 10k")
                print(f"    MA5: {ma5:.2f}  MA10: {ma10:.2f}  MA20: {ma20:.2f}  Vol Ratio: {vol_ratio:.2f}")
        else:
            print("  No data for today")
        
        # Query most recent 10 records
        result = session.execute(text("""
            SELECT code, date, close, pct_chg, volume, data_source
            FROM stock_daily 
            ORDER BY date DESC, code
            LIMIT 10
        """))
        recent = result.fetchall()
        
        print_section("Recent 10 Records")
        if recent:
            print(f"  {'Code':<10} {'Date':<12} {'Close':<10} {'Chg%':<8} {'Volume':<15} {'Source'}")
            print("  " + "-" * 70)
            for row in recent:
                vol_str = f"{row[4]/10000:.2f} 10k" if row[4] else "N/A"
                print(f"  {row[0]:<10} {row[1]!s:<12} {row[2]:<10.2f} {row[3]:<8.2f} {vol_str:<15} {row[5] or 'Unknown'}")
    finally:
        session.close()
    
    return True


def check_data_fetch(stock_code: str = "600519"):
    """Test data acquisition"""
    print_header("3. Data Fetch Test")
    
    from data_provider import DataFetcherManager
    
    manager = DataFetcherManager()
    
    print_section("Data Source List")
    for i, name in enumerate(manager.available_fetchers, 1):
        print(f"  {i}. {name}")
    
    print_section(f"Fetching {stock_code} data")
    print(f"  Fetching (this may take a few seconds)...")
    
    try:
        df, source = manager.get_daily_data(stock_code, days=5)
        
        print(f"  ✓ Fetch successful")
        print(f"    Data source: {source}")
        print(f"    Record count: {len(df)}")
        
        print_section("Data Preview (last 5 rows)")
        if not df.empty:
            preview_cols = ['date', 'open', 'high', 'low', 'close', 'pct_chg', 'volume']
            existing_cols = [c for c in preview_cols if c in df.columns]
            print(df[existing_cols].tail().to_string(index=False))
        
        return True
        
    except Exception as e:
        print(f"  ✗ Failed to obtain: {e}")
        return False


def check_llm():
    """Test LLM call"""
    print_header("4. LLM (Gemini) Call Test")
    
    from src.analyzer import GeminiAnalyzer
    from src.config import get_config
    import time
    
    config = get_config()
    
    print_section("Model Configuration")
    print(f"  master model: {config.gemini_model}")
    print(f"  alternative model: {config.gemini_model_fallback}")
    
    # Check network connection
    print_section("Network Connection Check")
    try:
        import socket
        socket.setdefaulttimeout(10)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("generativelanguage.googleapis.com", 443))
        print(f"  ✓ Can connect to Google API server")
    except Exception as e:
        print(f"  ✗ Unable to connect to Google API server: {e}")
        print(f"  Hint: Please check network connection or configure proxy")
        print(f"  Hint: Set environment variable HTTPS_PROXY=http://your-proxy:port")
        return False
    
    analyzer = GeminiAnalyzer()
    
    print_section("Model Initialization")
    if analyzer.is_available():
        print(f"  ✓ Model initialized successfully")
    else:
        print(f"  ✗ Model initialization failed (please check API Key)")
        return False
    
    # Construct test context
    test_context = {
        'code': '600519',
        'date': date.today().isoformat(),
        'today': {
            'open': 1420.0,
            'high': 1435.0,
            'low': 1415.0,
            'close': 1428.0,
            'volume': 5000000,
            'amount': 7140000000,
            'pct_chg': 0.56,
            'ma5': 1425.0,
            'ma10': 1418.0,
            'ma20': 1410.0,
            'volume_ratio': 1.1,
        },
        'ma_status': 'multi-head arrangement 📈',
        'volume_change_ratio': 1.05,
        'price_change_ratio': 0.56,
    }
    
    print_section("Send Test Request")
    print(f"  Test stock: Kweichow Moutai (600519)")
    print(f"  Calling Gemini API (timeout: 60s)...")
    
    start_time = time.time()
    
    try:
        result = analyzer.analyze(test_context)
        
        elapsed = time.time() - start_time
        print(f"\n  ✓ API call successful (elapsed: {elapsed:.2f}s)")
        
        print_section("Analysis Results")
        print(f"  Sentiment score: {result.sentiment_score}/100")
        print(f"  Trend prediction: {result.trend_prediction}")
        print(f"  Trading advice: {result.operation_advice}")
        print(f"  Technical analysis: {result.technical_analysis[:80]}..." if len(result.technical_analysis) > 80 else f"  Technical analysis: {result.technical_analysis}")
        print(f"  News summary: {result.news_summary[:80]}..." if len(result.news_summary) > 80 else f"  News summary: {result.news_summary}")
        print(f"  Analysis summary: {result.analysis_summary}")
        
        if not result.success:
            print(f"\n  ⚠ Call failed: {result.error_message}")
        
        return result.success
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n  ✗ API call failed (elapsed: {elapsed:.2f}s)")
        print(f"  Error: {e}")
        
        # Provide more detailed error messages
        error_str = str(e).lower()
        if 'timeout' in error_str or 'unavailable' in error_str:
            print(f"\n  Diagnosis: Network timeout, possible causes:")
            print(f"    1. Network blocked (proxy required to access Google)")
            print(f"    2. API service temporarily unavailable")
            print(f"    3. Request volume too large, rate limited")
        elif 'invalid' in error_str or 'api key' in error_str:
            print(f"\n  Diagnosis: API Key may be invalid")
        elif 'model' in error_str:
            print(f"\n  Diagnosis: Model name may be incorrect, try modifying GEMINI_MODEL in .env")
        
        return False


def check_notification():
    """Test notification push"""
    print_header("5. Notification Push Test")
    
    from src.notification import NotificationService
    from src.config import get_config
    
    config = get_config()
    service = NotificationService()
    
    print_section("Configuration Check")
    if service.is_available():
        print(f"  ✓ Enterprise WeChat Webhook configured")
        webhook_preview = config.wechat_webhook_url[:50] + "..." if len(config.wechat_webhook_url) > 50 else config.wechat_webhook_url
        print(f"    URL: {webhook_preview}")
    else:
        print(f"  ✗ Enterprise WeChat Webhook not configured")
        return False
    
    print_section("Send Test Message")
    
    test_message = f"""## 🧪 System Test Message

This is a test message from **AStock Selection Intelligent Analysis System**.

- Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Test purpose: Verify Enterprise WeChat Webhook configuration

If you receive this message, it means the notification function is configured correctly ✓"""
    
    print(f"  Sending...")
    
    try:
        success = service.send_to_wechat(test_message)
        
        if success:
            print(f"  ✓ Message sent successfully, please check Enterprise WeChat")
        else:
            print(f"  ✗ Message sending failed")
        
        return success
        
    except Exception as e:
        print(f"  ✗ Send exception: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "🚀" * 20)
    print("  AStock Selection Intelligent Analysis System - Environment Verification")
    print("  " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("🚀" * 20)
    
    results = {}
    
    # 1. Configuration test
    try:
        results['Config Load'] = check_config()
    except Exception as e:
        print(f"  ✗ Configuration test failed: {e}")
        results['Config Load'] = False
    
    # 2. Database view
    try:
        results['Database'] = view_database()
    except Exception as e:
        print(f"  ✗ Database test failed: {e}")
        results['Database'] = False
    
    # 3. Data fetch (skipped to avoid being too slow)
    # results['Data Fetch'] = check_data_fetch()
    
    # 4. LLM test (optional)
    # results['LLM Call'] = check_llm()
    
    # Summary
    print_header("Test Results Summary")
    for name, passed in results.items():
        status = "✓ pass" if passed else "✗ fail"
        print(f"  {status}: {name}")
    
    print(f"\nHint: Use --llm to individually test LLM calls")
    print(f"Hint: Use --fetch to individually test data fetching")
    print(f"Hint: Use --notify to individually test notification push")


def query_stock_data(stock_code: str, days: int = 10):
    """Query data for a specified stock"""
    print_header(f"Query Stock Data: {stock_code}")
    
    from src.storage import get_db
    from sqlalchemy import text
    
    db = get_db()
    
    session = db.get_session()
    try:
        result = session.execute(text("""
            SELECT date, open, high, low, close, pct_chg, volume, amount, ma5, ma10, ma20, volume_ratio
            FROM stock_daily 
            WHERE code = :code
            ORDER BY date DESC
            LIMIT :limit
        """), {"code": stock_code, "limit": days})
        
        rows = result.fetchall()
        
        if rows:
            print(f"\n  Most recent {len(rows)} records:\n")
            print(f"  {'Date':<12} {'Open':<10} {'High':<10} {'Low':<10} {'Close':<10} {'Chg%':<8} {'MA5':<10} {'MA10':<10} {'Vol Ratio':<8}")
            print("  " + "-" * 100)
            for row in rows:
                dt, open_, high, low, close, pct_chg, vol, amt, ma5, ma10, ma20, vol_ratio = row
                print(f"  {dt!s:<12} {open_:<10.2f} {high:<10.2f} {low:<10.2f} {close:<10.2f} {pct_chg:<8.2f} {ma5:<10.2f} {ma10:<10.2f} {vol_ratio:<8.2f}")
        else:
            print(f"  No data found for {stock_code}")
    finally:
        session.close()


def main():
    configure_console_encoding()

    parser = argparse.ArgumentParser(
        description='AStock Selection Intelligent Analysis System - Environment Verification',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument('--db', action='store_true', help='View database contents')
    parser.add_argument('--llm', action='store_true', help='Test LLM calls')
    parser.add_argument('--fetch', action='store_true', help='Test data fetching')
    parser.add_argument('--notify', action='store_true', help='Test notification push')
    parser.add_argument('--config', action='store_true', help='View configuration')
    parser.add_argument('--stock', type=str, help='Query specific stock data, e.g. --stock 600519')
    parser.add_argument('--all', action='store_true', help='Run all tests (including LLM)')
    
    args = parser.parse_args()
    
    # If no parameters specified, run basic tests
    if not any([args.db, args.llm, args.fetch, args.notify, args.config, args.stock, args.all]):
        run_all_tests()
        return 0
    
    # Run specified tests based on parameters
    if args.config:
        check_config()
    
    if args.db:
        view_database()
    
    if args.stock:
        query_stock_data(args.stock)
    
    if args.fetch:
        check_data_fetch()
    
    if args.llm:
        check_llm()
    
    if args.notify:
        check_notification()
    
    if args.all:
        check_config()
        view_database()
        check_data_fetch()
        check_llm()
        check_notification()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
