# Zeabur Deployment Guide

This guide details how to deploy the AI Stock Analysis System on Zeabur, including WebUI and Discord bot functionality.

## Table of Contents

- [1. Pre-deployment Preparation](#1-pre-deployment-preparation)
- [2. Deploying on Zeabur](#2-deploying-on-zeabur)
- [3. Configuring Startup Command](#3-configuring-startup-command)
- [4. Discord Bot Deployment](#4-discord-bot-deployment)
- [5. Environment Variable Configuration](#5-environment-variable-configuration)
- [6. Mount Configuration](#6-mount-configuration)
- [7. Health Check](#7-health-check)
- [8. FAQ](#8-faq)

## 1. Pre-deployment Preparation

### 1.1 Prerequisites

- Zeabur account
- GitHub account (for connecting repositories)
- Discord developer account (if deploying bot)
- Related API keys (e.g., Gemini API Key, Search Service API Key, etc.)

### 1.2 Repository Preparation

Ensure your repository contains the following files:

- `.github/workflows/docker-publish.yml` (auto-created)
- `docker/Dockerfile` (already exists)
- Complete project code

## 2. Deploying on Zeabur

### 2.1 Connect GitHub Repository

1. Log in to the Zeabur console
2. Click "New Project"
3. Select "Import from GitHub"
4. Select your repository and branch (recommended: `main`)
5. Click "Import"

### 2.2 Configure Build Rules

Zeabur will automatically detect `.github/workflows/docker-publish.yml` and use GitHub Actions to build the image.

If not auto-detected, configure manually:

1. On the project page, click "Build Rules"
2. Select "Dockerfile"
3. Enter the Dockerfile path: `docker/Dockerfile`
4. Click "Save"

### 2.3 Start the Service

1. Wait for the image build to complete
2. Click "Start Service"
3. After the service starts, you can get the access URL from the "Networking" tab

### 2.4 Frontend Build & Static Assets

FastAPI automatically serves frontend resources from the `static/` directory. The frontend build output location is determined by `apps/dsa-web/vite.config.ts`, defaulting to the project root `static/`.

The Dockerfile uses multi-stage builds; the frontend is automatically packaged during image build.
To override default static assets, manually build locally and mount to `/app/static` in the container.

### 2.5 Resource Configuration Recommendations

Zeabur services are recommended to start from `1G` memory; `512M` is only suitable for lightweight Web/API, single-stock, low-concurrency scenarios, with `MAX_WORKERS=1` recommended.

- Minimum to try: `512M`; do not run multiple heavy tasks simultaneously.
- Recommended: `1G`, suitable for single-service regular analysis.
- High load: `2G+`, suitable for running Web/API with scheduled analysis, multiple stocks, market review, news expansion, image reports, or AlphaSift simultaneously.

If limited to `512M`, avoid deploying equivalent to `server + analyzer` multi-service combinations simultaneously, and disable non-essential market review, news expansion, and image report capabilities.

## 3. Configuring Startup Command

### 3.1 Supported Startup Modes

The system supports multiple startup modes; configure different startup commands as needed:

| Mode | Startup Command | Description |
|------|----------|------|
| Scheduled Task Mode (default) | `python main.py --schedule` | Execute stock analysis on schedule |
| FastAPI Mode | `python main.py --serve` | Start FastAPI and execute analysis |
| FastAPI-Only Mode | `python main.py --serve-only` | Start FastAPI only, no analysis |
| Market Review Only | `python main.py --market-review` | Execute market review analysis only |

### 3.2 Configure Startup Command

1. In the Zeabur console, go to the service page
2. Click "Settings"
3. Find the "Startup Command" configuration item
4. Enter your desired startup command, e.g.:
    - Start FastAPI: `python main.py --serve`
    - FastAPI only: `python main.py --serve-only --host 0.0.0.0 --port 8000`
    - Start scheduled tasks: `python main.py --schedule`
5. Click "Save"
6. Restart the service

## 4. Discord Bot Deployment

### 4.1 Preparation

1. Create a Discord application and bot
   - Visit [Discord Developer Portal](https://discord.com/developers/applications)
   - Click "New Application" to create a new application
   - On the "Bot" tab, click "Add Bot" to create the bot
   - Copy the bot token

2. Configure bot permissions
   - On the "Bot" tab, scroll down to "Privileged Gateway Intents"
   - Enable "Server Members Intent" and "Message Content Intent"
   - Under "OAuth2" > "URL Generator", select the "bot" scope
   - Select required permissions (e.g., "Send Messages", "Read Messages/View Channels")
   - Copy the generated invite link and add the bot to your server

### 4.2 Configure Environment Variables

In the Zeabur console's "Environment Variables" configuration, add the following:

| Variable | Description | Example |
|--------|------|--------|
| `DISCORD_BOT_TOKEN` | Discord Bot Token | `MTAxMjM0NTY3ODkwMTEyMzQ1Ng.GhIjKl.MnOpQrStUvWxYz1234567890` |
| `DISCORD_MAIN_CHANNEL_ID` | Main Channel ID | `123456789012345678` |
| `DISCORD_WEBHOOK_URL` | Discord Webhook URL (optional) | `https://discord.com/api/webhooks/...` |

### 4.3 Start the Bot

The bot functionality is enabled by default through configuration and does not require a special startup command. Ensure your configuration file includes bot-related configuration, or set it via environment variables.

## 5. Environment Variable Configuration

### 5.1 Basic Environment Variables

| Variable | Description | Default |
|--------|------|--------|
| `PYTHONUNBUFFERED` | Enable Python unbuffered output | `1` |
| `LOG_DIR` | Log directory | `/app/logs` |
| `DATABASE_PATH` | Database path | `/app/data/stock_analysis.db` |

### 5.2 API Service Configuration

| Variable | Description | Default |
|--------|------|--------|
| `API_HOST` | API service listen address | `0.0.0.0` |
| `API_PORT` | API service port | `8000` |

> Legacy `WEBUI_HOST`/`WEBUI_PORT`/`WEBUI_ENABLED` environment variables remain compatible and are automatically forwarded to the API service.

### 5.3 Analysis Configuration

| Variable | Description |
|--------|------|
| `ANSPIRE_API_KEYS` | Anspire Open API key (shared for LLM and search, recommended) |
| `AIHUBMIX_KEY` | AIHubMix API key (one key for multiple models, recommended) |
| `GEMINI_API_KEY` | Gemini API key |
| `OPENAI_API_KEY` | OpenAI-compatible API key |
| `SERPAPI_API_KEYS` | SerpAPI key (recommended) |
| `TAVILY_API_KEYS` | Tavily API key (comma-separated) |
| `BOCHA_API_KEYS` | Bocha API key (comma-separated) |
| `BRAVE_API_KEYS` | Brave Search API key (comma-separated) |
| `MINIMAX_API_KEYS` | MiniMax API key (comma-separated) |
| `SEARXNG_BASE_URLS` | SearXNG instance URLs (comma-separated, quota-free fallback, requires format: json in settings.yml); when empty, auto-discovers public instances by default |
| `SEARXNG_PUBLIC_INSTANCES_ENABLED` | Auto-discover public instances from `searx.space` when `SEARXNG_BASE_URLS` is empty (default `true`) |

### 5.4 Configuration Method

In the Zeabur console:

1. Go to the service page
2. Click "Environment Variables"
3. Click "Add Environment Variable"
4. Enter variable name and value
5. Click "Save"
6. Restart the service

## 6. Mount Configuration

### 6.1 Supported Mount Directories

| Directory | Description |
|------|------|
| `/app/data` | Database and data files |
| `/app/logs` | Log files |
| `/app/reports` | Analysis reports |

### 6.2 Configure Mounts

1. In the Zeabur console, go to the service page
2. Click "Storage"
3. Click "Add Storage Volume"
4. Select "Persistent Storage"
5. Configure mount paths:
   - Storage volume path: `/app/data`
   - Container path: `/app/data`
6. Click "Save"
7. Repeat for other directories that need mounting

### 6.3 Notes

- After mounting, data is persisted and will not be lost on container restart
- At minimum, mount the `/app/data` directory to preserve the database

## 7. Health Check

The system has built-in health checking, checking by default:

- WebUI mode: Checks `http://localhost:8000/health` endpoint
- FastAPI mode: Checks `http://localhost:8000/api/health` endpoint
- Non-service mode: Always returns healthy status

Health check configuration:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || curl -f http://localhost:8000/health \
    || python -c "import sys; sys.exit(0)"
```

## 8. FAQ

### 8.1 API Service Inaccessible

- Check if the startup command includes `--serve` or `--serve-only` parameter
- Check if a domain is configured in the "Networking" tab
- Check firewall settings

### 8.2 Bot Not Responding

- Check Discord Bot Token is correct
- Check bot has been added to the server
- Check bot permissions are sufficient
- Check log files for error messages

### 8.3 Analysis Tasks Not Executing

- Check scheduled task configuration is correct
- Check API keys are valid
- Check log files for error messages

### 8.4 Data Loss

- Ensure `/app/data` directory is mounted
- Check storage volume configuration is correct

## 9. Advanced Configuration

### 9.1 Multi-instance Deployment

You can deploy multiple instances on Zeabur for different functions:

1. One instance for API service (`python main.py --serve-only`)
2. One instance for scheduled tasks (`python main.py --schedule`)
3. One instance for the bot (`python main.py --discord-bot`)

Ensure they share the same `/app/data` storage volume for shared database access.

### 9.2 Custom Domain

In the Zeabur console's "Networking" tab, you can:

1. Use the auto-generated domain
2. Bind a custom domain
3. Configure HTTPS

## 10. Updating Deployment

### 10.1 Auto Update

When you push new code to the repository:

1. GitHub Actions automatically builds a new image
2. Zeabur detects the new image
3. You can choose "Auto Deploy" or manually trigger deployment

### 10.2 Manual Update

1. In the Zeabur console, go to the service page
2. Click "Deployment History"
3. Select "Redeploy"
4. Or click "Update Image"

## 11. Monitoring & Logs

### 11.1 View Logs

In the Zeabur console, go to the service page and click the "Logs" tab to view real-time and historical logs.

### 11.2 Monitoring Metrics

Zeabur provides basic monitoring metrics:

- CPU usage
- Memory usage
- Network traffic
- Disk usage

View detailed metrics in the "Monitoring" tab.

## 12. Troubleshooting

### 12.1 View Detailed Logs

```bash
# Enter container
zeabur exec <service-name> bash

# View log files
cat /app/logs/stock_analysis_20260125.log
```

### 12.2 Check Configuration

```bash
# Enter container
zeabur exec <service-name> bash

# Check environment variables
printenv | grep -i discord
printenv | grep -i webui
```

### 12.3 Test Connection

```bash
# Test network connection
zeabur exec <service-name> curl -I https://api.discord.com

# Test API connection
zeabur exec <service-name> python -c "import requests; print(requests.get('https://api.discord.com').status_code)"
```

## 13. Best Practices

1. **Use persistent storage**: Always mount the `/app/data` directory to preserve the database
2. **Configure reasonable health checks**: Adjust health check parameters based on actual conditions
3. **Use environment variables for sensitive information**: Do not hardcode API keys into code
4. **Regularly back up data**: Periodically download the contents of `/app/data` for backup
5. **Use appropriate startup mode**: Choose the appropriate startup command based on needs
6. **Monitor service status**: Regularly check service status and logs
7. **Configure memory based on load**: Full analysis recommends `1G` minimum; `512M` low-config environments should set `MAX_WORKERS=1`, high-load scenarios use `2G+`

## 14. Contact

If you have questions, feel free to contact the project maintainer or ask in GitHub Issues.
