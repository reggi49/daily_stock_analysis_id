#!/bin/bash
# ===================================
# A-share/HK-share/US-share intelligent analysis system - test script
# ===================================
#
# Usage:
#   ./scripts/test.sh [test scenario]
#
# Test scenarios:
#   market      - market review only
#   a-stock     - A-share stock analysis (Moutai, Ping An Bank)
#   etf         - ETF analysis (satellite ETF 563230)
#   hk-stock    - HK-share analysis (Tencent, Alibaba)
#   us-stock    - US-share analysis (Apple, Tesla)
#   mixed       - mixed market analysis
#   single      - single-stock push mode test
#   dry-run     - fetch data only, no analysis
#   full        - full pipeline test
#   quick       - quick test (single stock)
#   all         - run all tests
#
# Examples:
#   ./scripts/test.sh market      # test market review
#   ./scripts/test.sh us-stock    # test US-share analysis
#   ./scripts/test.sh quick       # quick test
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored messages
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

header() {
    echo ""
    echo "=============================================="
    echo -e "${GREEN}$1${NC}"
    echo "=============================================="
    echo ""
}

# Check Python environment
check_python() {
    if ! command -v python3 &> /dev/null; then
        error "Python3 not installed"
        exit 1
    fi
    info "Python version: $(python3 --version)"
}

# Check dependencies
check_deps() {
    info "Checking dependencies..."
    python3 -c "import yfinance" 2>/dev/null || { warn "yfinance not installed, US-share tests may fail"; }
    python3 -c "import akshare" 2>/dev/null || { warn "akshare not installed, A-share/HK-share tests may fail"; }
    success "Dependency check complete"
}

# ==================== Test scenarios ====================

# Test 1: Market review
test_market() {
    header "Test scenario: Market review"
    info "Running market review analysis..."
    python3 main.py --market-review "$@"
    success "Market review test complete"
}

# Test 2: A-share analysis
test_a_stock() {
    header "Test scenario: A-share analysis"
    info "Analyzing A-shares: 600519 (Moutai), 000001 (Ping An Bank)"
    python3 main.py --stocks 600519,000001  --no-market-review "$@"
    success "A-share analysis test complete"
}

# Test 2.5: ETF analysis
test_etf() {
    header "Test scenario: ETF analysis"
    info "Analyzing ETF: 563230 (Satellite ETF)"
    python3 main.py --stocks 563230,512400 --no-market-review "$@"
    success "ETF analysis test complete"
}

# Test 3: HK-share analysis
test_hk_stock() {
    header "Test scenario: HK-share analysis"
    info "Analyzing HK-shares: hk00700 (Tencent), hk09988 (Alibaba)"
    python3 main.py --stocks hk00700,hk09988 --no-market-review "$@"
    success "HK-share analysis test complete"
}

# Test 4: US-share analysis
test_us_stock() {
    header "Test scenario: US-share analysis"
    info "Analyzing US-shares: AAPL (Apple), TSLA (Tesla)"
    # Allow passing through args; by default without --no-notify
    python3 main.py --stocks AAPL --no-market-review "$@"
    success "US-share analysis test complete"
}

# Test 5: Mixed market
test_mixed() {
    header "Test scenario: Mixed market analysis"
    info "Analyzing mixed market: 600519 (A-share), hk00700 (HK-share), AAPL (US-share)"
    python3 main.py --stocks 600519,hk00700,AAPL --no-market-review
    success "Mixed market test complete"
}

# Test 6: Single-stock push mode
test_single() {
    header "Test scenario: Single-stock push mode"
    info "Testing single-stock push mode..."
    python3 main.py --stocks 600519 --single-notify --no-market-review
    success "Single-stock push mode test complete"
}

# Test 7: dry-run mode
test_dry_run() {
    header "Test scenario: Dry-Run mode"
    info "Fetch data only, no AI analysis..."
    python3 main.py --stocks 600519,AAPL --dry-run --no-notify
    success "Dry-Run test complete"
}

# Test 8: Full pipeline
test_full() {
    header "Test scenario: Full pipeline"
    info "Running full analysis pipeline (stocks + market)..."
    python3 main.py --stocks 600519 --no-notify
    success "Full pipeline test complete"
}

# Test 9: Quick test
test_quick() {
    header "Test scenario: Quick test"
    info "Single-stock quick test..."
    python3 main.py --stocks 600519 --no-market-review --no-notify "$@"
    success "Quick test complete"
}

# Test 10: Code recognition test
test_code_recognition() {
    header "Test scenario: Code recognition"
    info "Testing stock code recognition logic..."

    python3 << 'PYTEST'
import sys
sys.path.insert(0, '.')
from data_provider.akshare_fetcher import _is_hk_code, _is_us_code

test_cases = [
    # (code, expected HK, expected US, description)
    ("AAPL", False, True, "US-share - Apple"),
    ("TSLA", False, True, "US-share - Tesla"),
    ("BRK.B", False, True, "US-share - Berkshire B"),
    ("hk00700", True, False, "HK-share - Tencent"),
    ("HK09988", True, False, "HK-share - Alibaba"),
    ("600519", False, False, "A-share - Moutai"),
    ("000001", False, False, "A-share - Ping An"),
]

print("\nStock code recognition test:")
print("-" * 60)
all_pass = True
for code, exp_hk, exp_us, desc in test_cases:
    is_hk = _is_hk_code(code)
    is_us = _is_us_code(code)
    hk_ok = is_hk == exp_hk
    us_ok = is_us == exp_us
    status = "✅" if (hk_ok and us_ok) else "❌"
    all_pass = all_pass and hk_ok and us_ok
    print(f"{status} {code:10} | HK:{is_hk:5} US:{is_us:5} | {desc}")

print("-" * 60)
print(f"{'✅ All tests passed!' if all_pass else '❌ Some tests failed!'}")
sys.exit(0 if all_pass else 1)
PYTEST

    success "Code recognition test complete"
}

# Test 11: YFinance code conversion test
test_yfinance_convert() {
    header "Test scenario: YFinance code conversion"
    info "Testing YFinance code conversion logic..."

    python3 << 'PYTEST'
import sys
sys.path.insert(0, '.')
from data_provider.yfinance_fetcher import YfinanceFetcher

fetcher = YfinanceFetcher()

test_cases = [
    ("AAPL", "AAPL", "US-share"),
    ("tsla", "TSLA", "US-share lowercase"),
    ("BRK.B", "BRK.B", "US-share special"),
    ("hk00700", "0700.HK", "HK-share"),
    ("HK09988", "9988.HK", "HK-share uppercase"),
    ("600519", "600519.SS", "A-share Shanghai"),
    ("000001", "000001.SZ", "A-share Shenzhen"),
    ("300750", "300750.SZ", "A-share ChiNext"),
]

print("\nYFinance code conversion test:")
print("-" * 60)
all_pass = True
for input_code, expected, desc in test_cases:
    result = fetcher._convert_stock_code(input_code)
    status = "✅" if result == expected else "❌"
    all_pass = all_pass and (result == expected)
    print(f"{status} {input_code:10} -> {result:12} (expected: {expected:12}) | {desc}")

print("-" * 60)
print(f"{'✅ All tests passed!' if all_pass else '❌ Some tests failed!'}")
sys.exit(0 if all_pass else 1)
PYTEST

    success "YFinance code conversion test complete"
}

# Test 12: Syntax check
test_syntax() {
    header "Test scenario: Python syntax check"
    info "Checking syntax of all Python files..."

    python3 -m py_compile main.py src/config.py src/notification.py \
        data_provider/akshare_fetcher.py \
        data_provider/yfinance_fetcher.py \
        bot/commands/analyze.py

    success "Syntax check passed"
}

# Test 13: Flake8 static check
test_flake8() {
    header "Test scenario: Flake8 static check"
    info "Running Flake8 to check for critical errors..."

    if command -v flake8 &> /dev/null; then
        flake8 main.py src/config.py src/notification.py --select=F821,E999 --max-line-length=120
        success "Flake8 check passed"
    else
        warn "Flake8 not installed, skipping check"
    fi
}

# Run all tests
test_all() {
    header "Running all tests"

    test_syntax
    test_code_recognition
    test_yfinance_convert
    test_flake8

    echo ""
    info "The following tests require network and API config and may fail:"
    echo ""

    test_dry_run || warn "Dry-Run test failed (possible network issue)"
    test_quick || warn "Quick test failed (possible API issue)"

    success "All tests complete!"
}

# ==================== Main program ====================

main() {
    header "A-share/HK-share/US-share intelligent analysis system - test"

    check_python
    check_deps

    case "${1:-help}" in
        market)
            shift
            test_market "$@"
            ;;
        a-stock|a_stock|astock)
            shift
            test_a_stock "$@"
            ;;
        etf)
            shift
            test_etf "$@"
            ;;
        hk-stock|hk_stock|hkstock|hk)
            shift
            test_hk_stock "$@"
            ;;
        us-stock|us_stock|usstock|us)
            shift
            test_us_stock "$@"
            ;;
        mixed|mix)
            shift
            test_mixed "$@"
            ;;
        single)
            shift
            test_single "$@"
            ;;
        dry-run|dryrun|dry)
            shift
            test_dry_run "$@"
            ;;
        full)
            shift
            test_full "$@"
            ;;
        quick|q)
            shift
            test_quick "$@"
            ;;
        code|recognition)
            shift
            test_code_recognition "$@"
            ;;
        yfinance|yf)
            shift
            test_yfinance_convert "$@"
            ;;
        syntax)
            shift
            test_syntax "$@"
            ;;
        flake8|lint)
            shift
            test_flake8 "$@"
            ;;
        all)
            shift
            test_all "$@"
            ;;
        help|--help|-h|*)
            echo "Usage: $0 [test scenario]"
            echo ""
            echo "Test scenarios:"
            echo "  market      - market review only"
            echo "  a-stock     - A-share stock analysis"
            echo "  etf         - ETF analysis"
            echo "  hk-stock    - HK-share analysis"
            echo "  us-stock    - US-share analysis"
            echo "  mixed       - mixed market analysis"
            echo "  single      - single-stock push mode"
            echo "  dry-run     - fetch data only"
            echo "  full        - full pipeline"
            echo "  quick       - quick test (recommended)"
            echo "  code        - code recognition test"
            echo "  yfinance    - YFinance conversion test"
            echo "  syntax      - syntax check"
            echo "  flake8      - static check"
            echo "  all         - run all tests"
            echo ""
            echo "Examples:"
            echo "  $0 quick     # quick test"
            echo "  $0 us-stock  # test US-share"
            echo "  $0 code      # test code recognition"
            echo "  $0 all       # run all tests"
            ;;
    esac
}

main "$@"
