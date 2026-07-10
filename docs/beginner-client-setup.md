# Beginner Client Installation and Configuration Guide

This document is written for users who don't code and just want to download the client and use it directly. The goal is simple: download the client, fill in a model service key, enter stock codes, and generate your first analysis report.

> This project generates supplementary analysis reports and does not constitute investment advice. Please assess risks yourself for actual trading.

## Prerequisites

1. A Windows or macOS computer.
2. A model service key (Key); choose any one from the following:
   - [Anspire Open](https://open.anspire.cn/?share_code=QFBC0FYC): Supports mainstream global models; one Key can be used for both model and news search, making first-time configuration easiest.
   - [AIHubMix](https://aihubmix.com/?aff=CfMq): Supports mainstream global models; suitable for users who want to switch between multiple models on one platform.
3. The stock codes you want to analyze, e.g., `600519,hk00700,AAPL`.

## 1. Download the Client

Open the releases page:

<https://github.com/ZhuLinsen/daily_stock_analysis/releases/latest>

Download from the `Assets` section at the bottom of the page:

| Computer | Download |
| --- | --- |
| Windows | `daily-stock-analysis-windows-installer-<version>.exe` |
| Windows (no install) | `daily-stock-analysis-windows-noinstall-<version>.zip` |
| macOS Apple Silicon | `daily-stock-analysis-macos-arm64-<version>.dmg` |
| macOS Intel | `daily-stock-analysis-macos-x64-<version>.dmg` |

You don't need to download `latest.yml` or `*.blockmap`; they are not client installation packages.

Don't know which Mac chip you have: Click the Apple icon in the top left corner > About This Mac; if you see M1/M2/M3/M4, choose `arm64`; if you see Intel, choose `x64`.

## 2. Install and Open

- Windows installer: Double-click the `.exe`, follow the prompts to install; the default location is fine.
- Windows no-install package: Extract the `.zip`, double-click `Daily Stock Analysis.exe`.
- macOS: Double-click the `.dmg`, drag the app to `Applications`. If it says it's from an unverified developer, allow it to open in System Settings > Privacy & Security.

macOS users are recommended to export a configuration backup from client settings before upgrading.

## 3. Configure AI Model

Open the client and go to:

`System Settings -> AI Model`

Only choose one of the following options.

> Important: After changing any setting, click the save button on the page; wait for the save success message before switching pages or returning to the home page.

### Option A: Anspire Open

1. Open [Anspire Open](https://open.anspire.cn/?share_code=QFBC0FYC), register/log in and create an API Key.
2. Return to the client and select `Anspire Open` in the quick channel setup.
3. Paste the API Key.
4. Select a model name for a model enabled in the console; if unsure, select the console's recommended or lightweight model.
5. Click Save; after seeing save success, click Test Connection.

### Option B: AIHubMix

1. Open [AIHubMix](https://aihubmix.com/?aff=CfMq), register/log in and create an API Key.
2. Return to the client and select `AIHubmix (Aggregation Platform)` in the quick channel setup.
3. Paste the API Key.
4. Select a model name for a model enabled in the console; if unsure, select the console's recommended model.
5. Click Save; after seeing save success, click Test Connection.

When you see test success, proceed to the next step.

## 4. Fill in Your Watchlist

Go to:

`System Settings -> Basic Settings`

Find `Watchlist` and enter:

`600519,hk00700,AAPL`

Separate multiple stocks with commas. Common formats:

- A-shares: `600519`, `300750`, `000001`
- HK stocks: `hk00700`, `hk09988`
- US stocks: `AAPL`, `TSLA`, `NVDA`

After filling in, click Save; wait for save success before returning to the home page.

## 5. Recommended: Configure News Sources

News sources are optional but recommended. They affect recent news, announcements, event-driven analysis, hot topics, and risk alerts.

Go to:

`System Settings -> Data Source`

Choose based on your model service:

1. Using Anspire Open: Find `Anspire API Keys`, enter the same Anspire Key, and save successfully.
2. Using AIHubMix: It's recommended to also apply for a [SerpAPI](https://serpapi.com/baidu-search-api?utm_source=github_daily_stock_analysis) or [Tavily](https://tavily.com/) Key, enter it in `SerpAPI API Keys` or `Tavily API Keys`, and save successfully.

You can skip news sources if you want to try it out first; the client can still generate basic analysis.

## 6. Start Analyzing

Return to the home page:

1. Enter a stock code, e.g., `600519`.
2. Click Analyze.
3. Wait for the task to go from queuing, analyzing, to analysis complete.
4. View the report in history.

## FAQ

### There are many files on the download page; which one should I download?

Regular Windows users should download the `.exe` installer. Do not download `latest.yml` or `*.blockmap`.

### I entered the API Key but it still doesn't work?

Check the following:

1. Is the key copied completely, without extra spaces?
2. Does the platform account have balance or quota?
3. Is the current model enabled?
4. Does the test connection show that the model doesn't exist, insufficient permissions, or insufficient balance?

### My configuration is messed up; what should I do?

Export a configuration backup from client settings. When something goes wrong, you can import a previous backup, or just keep these three items and reconfigure: AI Model, Watchlist, News Source.
