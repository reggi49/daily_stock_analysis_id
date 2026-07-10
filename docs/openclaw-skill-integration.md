# OpenClaw Skill Integration Guide

This document explains how to use the [OpenClaw](https://github.com/openclaw/openclaw) Skill to invoke daily_stock_analysis's REST API, enabling stock analysis from within OpenClaw conversations.

## Overview

- **Integration method**: The OpenClaw Skill calls the daily_stock_analysis (DSA) REST API via HTTP
- **Use case**: DSA API service is deployed and you want to trigger analysis from OpenClaw conversations (e.g., "analyze Moutai", "analyze AAPL")

## Prerequisites

1. **daily_stock_analysis must be running**: Execute `python main.py --serve-only` or deploy via Docker to keep the API available
2. **OpenClaw must have HTTP calling capability**: Such as `system.run` executing curl, or a built-in HTTP tool (e.g., api-tester)
3. **Note**: GitHub Actions only runs scheduled tasks and does not expose a long-running API; you need to run DSA locally or via Docker

## Core API Reference

| Endpoint | Method | Purpose |
|------|------|------|
| `/api/v1/analysis/analyze` | POST | Trigger analysis (main entry point) |
| `/api/v1/analysis/status/{task_id}` | GET | Async task status |
| `/api/v1/agent/chat` | POST | Agent strategy chat (requires `AGENT_MODE=true`) |
| `/api/health` | GET | Health check |

### Trigger Analysis Request Body

```json
{
  "stock_code": "600519",
  "report_type": "detailed",
  "force_refresh": true,
  "async_mode": false
}
```

- `stock_code`: Stock code (required)
- `report_type`: `simple` | `detailed` | `brief`
- `force_refresh`: Boolean, whether to force refresh (ignore cache)
- `async_mode`: Boolean, `false` returns synchronously, `true` returns 202 + `task_id` requiring polling

**Note**: `force_refresh` and `async_mode` are boolean types, not strings.

### Response Example (Synchronous Mode)

```json
{
  "query_id": "abc123def456",
  "stock_code": "600519",
  "stock_name": "Kweichow Moutai",
  "report": {
    "summary": {
      "analysis_summary": "...",
      "operation_advice": "Hold",
      "action": "hold",
      "action_label": "Hold",
      "trend_prediction": "Bullish",
      "sentiment_score": 75
    },
    "strategy": {
      "ideal_buy": "1850",
      "stop_loss": "1780",
      "take_profit": "1950"
    }
  },
  "created_at": "2026-03-13T10:00:00"
}
```

## Important Limitations

- **Stock codes only**: The API does not accept Chinese names (e.g., "Moutai"); the Skill must parse or prompt the user to provide a code (e.g., 600519, AAPL)
- **Synchronous mode timing**: With `async_mode: false`, a single analysis takes approximately 2-5 minutes; ensure the OpenClaw or HTTP client timeout is sufficient
- **Asynchronous mode**: `async_mode: true` returns 202 + `task_id`; poll `GET /api/v1/analysis/status/{task_id}` until `status: completed`

## Stock Code Formats

| Type | Format | Example |
|------|------|------|
| A-shares | 6-digit number | `600519`, `000001`, `300750` |
| Beijing SE | 6 digits starting with 8/4/92, supports `BJ` prefix or `.BJ` suffix | `920748`, `BJ920493`, `920493.BJ` |
| Hong Kong | hk + 5 digits | `hk00700`, `hk09988` |
| US stocks | 1-5 letters (optional .X suffix) | `AAPL`, `TSLA`, `BRK.B` |
| US indices | SPX/DJI/IXIC etc. | `SPX`, `DJI`, `NASDAQ`, `VIX` |

## Configuration

Configure in `~/.openclaw/openclaw.json`:

```json
{
  "skills": {
    "entries": {
      "daily-stock-analysis": {
        "enabled": true,
        "env": {
          "DSA_BASE_URL": "http://localhost:8000"
        }
      }
    }
  }
}
```

- Local deployment: `http://localhost:8000` or `http://127.0.0.1:8000`
- Remote deployment: Replace with the actual URL
- **Recommendation**: `DSA_BASE_URL` should not end with `/`

## Error Response Format

| Status Code | error field | Description |
|--------|-------------|------|
| 400 | `validation_error` | Parameter error (e.g., missing stock_code) |
| 409 | `duplicate_task` | Stock is already being analyzed; duplicate submission rejected |
| 500 | `internal_error` / `analysis_failed` | Error occurred during analysis |

## Complete SKILL.md Example

Save the following to `~/.openclaw/skills/daily-stock-analysis/SKILL.md`:

```markdown
---
name: daily-stock-analysis
description: Call the daily_stock_analysis API for intelligent stock analysis. Use when the user asks to "analyze Moutai", "analyze AAPL", "check 600519", etc. Only stock codes are supported, not Chinese names.
metadata:
  {"openclaw": {"requires": {"env": ["DSA_BASE_URL"]}, "primaryEnv": "DSA_BASE_URL"}}
---

## Trigger

Use this Skill when the user requests analysis of a specific stock (e.g., "analyze Moutai", "analyze AAPL", "check 600519").

## Workflow

1. **Extract stock code**: Identify the stock code from the user message (e.g., 600519, AAPL, hk00700). If the user only provides a Chinese name (e.g., "Moutai"), prompt them for the stock code, or use common mappings (Moutai -> 600519).
2. **Call API**: Send a POST request to `{DSA_BASE_URL}/api/v1/analysis/analyze` with body:
   ```json
   {"stock_code": "<extracted_code>", "report_type": "detailed", "force_refresh": true, "async_mode": false, "skills": ["bull_trend"]}
   ```
   > `skills` is an optional strategy ID array; the legacy field `strategies` is still supported, but `skills` is preferred.
3. **Wait for response**: In synchronous mode, analysis takes approximately 2-5 minutes. Ensure the HTTP client timeout is sufficient (recommended >=300 seconds).
4. **Parse results**: Extract `operation_advice`, `trend_prediction`, `analysis_summary` from `report.summary`, and `ideal_buy`, `stop_loss`, `take_profit` from `report.strategy`. Present the results in a concise format. External integrations can continue reading only the free-text `operation_advice`; for structured display, prefer the optional `action` / `action_label` (eight states: `buy|add|hold|reduce|sell|watch|avoid|alert`). When historical data is missing fields, fall back to `operation_advice` text display, but this fallback is not equivalent to a stable API action; the legacy three-state statistics still use `decision_type`.
5. **Error handling**:
   - Connection failure: Prompt the user to check if DSA is running and if DSA_BASE_URL is correct
   - 400: Check the stock_code format
   - 409: The stock is being analyzed; try again later or check task status
   - 500: Prompt the user to check DSA logs for debugging

## Stock Code Formats

- A-shares: 6-digit number (600519, 000001)
- Beijing SE: 6 digits starting with 8/4/92, supports BJ prefix or .BJ suffix (920748, BJ920493, 920493.BJ)
- Hong Kong: hk + 5 digits (hk00700)
- US stocks: 1-5 letters (AAPL, TSLA, BRK.B)
- US indices: SPX, DJI, IXIC, etc.
```

## Agent Strategy Chat (Optional)

If daily_stock_analysis has `AGENT_MODE=true` enabled, you can call the Agent strategy chat endpoint, which supports multi-turn conversations and multiple strategies (Chan theory, moving-average crossover, etc.):

```bash
# Replace {DSA_BASE_URL} with your configured API address (e.g., http://localhost:8000)
curl -X POST {DSA_BASE_URL}/api/v1/agent/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "Analyze 600519 using Chan theory", "session_id": "optional-session-id"}'
```

The response includes `content` (analysis conclusion) and `session_id` (for multi-turn conversations).

## Troubleshooting

| Symptom | Possible Cause | Recommended Action |
|------|----------|----------|
| Connection failure | DSA not running, wrong port, firewall | Confirm `python main.py --serve-only` is started; check `DSA_BASE_URL` |
| 400 error | Invalid or missing stock_code | Check code format (see table above); ensure the request body contains `stock_code` |
| 500 error | AI configuration, data source, or network issue | Check DSA logs; confirm GEMINI_API_KEY etc. are configured |
| Agent 400 | Agent mode not enabled | Set `AGENT_MODE=true` in DSA's `.env` |
| Analysis timeout | Synchronous mode wait too long | Increase HTTP client timeout, or switch to `async_mode: true` for polling |

## Authentication

By default, the DSA API does not require authentication. If `ADMIN_AUTH_ENABLED=true` is enabled in `.env`, you must include the login cookie in Skill API calls. The exact method depends on OpenClaw's HTTP tool capabilities (the current API only supports cookie authentication, not Bearer tokens).
