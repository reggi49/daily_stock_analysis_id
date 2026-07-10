---
name: "stock_analyzer"
description: "Analyze stocks and markets. Called when the user wants to analyze one or more stocks, or perform a market review."
---

# Stock Analyzer

This skill provides stock and overall market analysis functionality, based on the logic in `src/services/analyzer_service.py`.

## Output Structure (`AnalysisResult`)

The analysis function returns an `AnalysisResult` object (or a list of them), which has a rich structure. Below is a brief overview of its key components, along with real output examples:

The `dashboard` attribute contains the core analysis, divided into four main sections:
1.  **`core_conclusion`**: One-line summary, signal type, and position recommendation.
2.  **`data_perspective`**: Technical data, including trend status, price position, volume analysis, and chip structure.
3.  **`intelligence`**: Qualitative information such as news, risk alerts, and positive catalysts.
4.  **`battle_plan`**: Actionable strategies, including sniper points (buy/sell targets), position strategy, and risk control checklist.

## Configuration (`Config`)

All analysis functions accept an optional `config` object. This object contains all application configuration, such as API keys, notification settings, and analysis parameters.

If no `config` object is provided, the function automatically uses the global singleton instance loaded from the `.env` file.

**Reference:** [`Config`](src/config.py)

## Functions

### 1. Analyze a Single Stock

**Description:** Analyzes a single stock and returns the analysis result.

**When to use:** When the user requests analysis of a specific stock.

**Input:**
- `stock_code` (str): The stock code to analyze.
- `config` (Config, optional): Configuration object. Defaults to `None`.
- `full_report` (bool, optional): Whether to generate a full report. Defaults to `False`.
- `notifier` (NotificationService, optional): Notification service object. Defaults to `None`.

**Output:** `Optional[AnalysisResult]`
An `AnalysisResult` object containing the analysis result, or `None` if the analysis failed.

**Example:**

```python
from src.services.analyzer_service import analyze_stock

# Analyze a single stock
result = analyze_stock("600989")
if result:
    print(f"Stock: {result.name} ({result.code})")
    print(f"Sentiment score: {result.sentiment_score}")
    print(f"Operation advice: {result.operation_advice}")
```

**Reference:** [`analyze_stock`](src/services/analyzer_service.py)

### 2. Analyze Multiple Stocks

**Description:** Analyzes a list of stocks and returns a list of analysis results.

**When to use:** When the user wants to analyze multiple stocks at once.

**Input:**
- `stock_codes` (List[str]): List of stock codes to analyze.
- `config` (Config, optional): Configuration object. Defaults to `None`.
- `full_report` (bool, optional): Whether to generate a full report for each stock. Defaults to `False`.
- `notifier` (NotificationService, optional): Notification service object. Defaults to `None`.

**Output:** `List[AnalysisResult]`
A list of `AnalysisResult` objects.

**Example:**

```python
from src.services.analyzer_service import analyze_stocks

# Analyze multiple stocks
results = analyze_stocks(["600989", "000001"])
for result in results:
    print(f"Stock: {result.name}, Operation advice: {result.operation_advice}")
```

**Reference:** [`analyze_stocks`](src/services/analyzer_service.py)


### 3. Perform Market Review

**Description:** Performs a review of the overall market and returns a report.

**When to use:** When the user requests a market overview, summary, or review.

**Input:**
- `config` (Config, optional): Configuration object. Defaults to `None`.
- `notifier` (NotificationService, optional): Notification service object. Defaults to `None`.

**Output:** `Optional[str]`
A string containing the market review report, or `None` if the operation failed.

**Example:**

```python
from src.services.analyzer_service import perform_market_review

# Perform market review
report = perform_market_review()
if report:
    print(report)
```

**Reference:** [`perform_market_review`](src/services/analyzer_service.py)
