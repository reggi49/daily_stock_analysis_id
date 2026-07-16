# 🚀 Deployment Guide

This document describes how to deploy the A-Shares Stock Analysis System to a server.

## 📋 Deployment Options Comparison

| Option | Advantages | Disadvantages | Recommended Scenario |
|------|------|------|----------|
| **Docker Compose** ⭐ | One-click deployment, environment isolation, easy migration, easy upgrades | Requires Docker installation | **Recommended**: Most scenarios |
| **Direct Deployment** | Simple and straightforward, no extra dependencies | Environment dependencies, troublesome migration | Temporary testing |
| **Systemd Service** | System-level management, auto-start on boot | Complex configuration | Long-term stable operation |
| **Supervisor** | Process management, automatic restart | Requires extra installation | Multi-process management |

**Conclusion: Docker Compose is recommended for the fastest and most convenient migration!**

---

## 🐳 Option 1: Docker Compose Deployment (Recommended)

### 1. Install Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# CentOS
sudo yum install -y docker docker-compose
sudo systemctl start docker
sudo systemctl enable docker
```

### 2. Prepare Configuration Files

```bash
# Clone code (or upload code to server)
git clone <your-repo-url> /opt/stock-analyzer
cd /opt/stock-analyzer

# Copy and edit configuration file
cp .env.example .env
vim .env  # Fill in real API Key and other configurations
```

### 3. One-Click Startup

```bash
# Build and start (includes both scheduled analysis and Web UI services)
docker-compose -f ./docker/docker-compose.yml up -d

# View logs
docker-compose -f ./docker/docker-compose.yml logs -f

# View running status
docker-compose -f ./docker/docker-compose.yml ps
```

After successful startup, enter `http://server-public-IP:8000` in your browser to open the Web management interface. If you can't access it, remember to first allow port 8000 in the "Security Group" of your cloud server console.

> Not sure how to access? → [Cloud Server Web Interface Access Guide](deploy-webui-cloud.md)

### 3.1 Resource Recommendations

The default `docker/docker-compose.yml` sets `limits.memory: 1G` and `reservations.memory: 512M` for each service, which is the recommended starting point for full analysis scenarios.

- Minimum: `512M`, suitable only for lightweight Web/API, single stock, low concurrency scenarios; set `MAX_WORKERS=1`.
- Recommended: `1G`, suitable for running `server` or `analyzer` alone for regular analysis.
- High load: `2G+`, suitable for simultaneously running `server + analyzer`, multiple stocks, default `MAX_WORKERS=3`, market review, news expansion, image reports, or AlphaSift.

If you can only use `512M`, avoid running `server` and `analyzer` simultaneously, and disable non-essential market review, news expansion, and image report capabilities.

### 4. Common Management Commands

```bash
# Stop services
docker-compose -f ./docker/docker-compose.yml down

# Restart services
docker-compose -f ./docker/docker-compose.yml restart

# Redeploy after code update
git pull
docker-compose -f ./docker/docker-compose.yml build --no-cache
docker-compose -f ./docker/docker-compose.yml up -d

# Enter container for debugging
docker-compose -f ./docker/docker-compose.yml exec -u dsa stock-analyzer bash

# Manually run one analysis
docker-compose -f ./docker/docker-compose.yml exec -u dsa stock-analyzer python main.py --no-notify
```

### 5. Data Persistence

Data is automatically saved to host directories:
- `./data/` - Database files
- `./logs/` - Log files
- `./reports/` - Analysis reports

### 6. Permission Notes

The Docker image startup entry automatically creates and fixes permissions for the mounted directories corresponding to `./data`, `./logs`, `./reports`, then runs the application as a non-root user (`dsa`, UID 1000). Regular deployments don't need manual `chown` / `chmod`.

If you explicitly specify `--user` / Compose `user:`, or use read-only mounts, rootless Docker, NFS, or other environments that don't allow the container to fix ownership, please ensure the actual running user has write permissions to these directories.

---

## 🖥️ Option 2: Direct Deployment

### 1. Install Python Environment

```bash
# Install Python 3.10+
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip

# Create virtual environment
python3.10 -m venv /opt/stock-analyzer/venv
source /opt/stock-analyzer/venv/bin/activate
```

### 2. Install Dependencies

```bash
cd /opt/stock-analyzer
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
vim .env  # Fill in configuration
```

### 4. Run

```bash
# Single run
python main.py

# Scheduled task mode (foreground)
python main.py --schedule

# Background run (using nohup)
nohup python main.py --schedule > /dev/null 2>&1 &

# Start Web management interface (cloud servers need to first set WEBUI_HOST=0.0.0.0 in .env)
python main.py --webui-only

# Start Web UI (runs one analysis at startup; for daily scheduled analysis, add --schedule or set SCHEDULE_ENABLED=true)
python main.py --webui
```

> Not sure how to access? → [Cloud Server Web Interface Access Guide](deploy-webui-cloud.md)

---

## 🔧 Option 3: Systemd Service

Create a systemd service file for auto-start on boot and automatic restart:

### 1. Create Service File

```bash
sudo vim /etc/systemd/system/stock-analyzer.service
```

Content:
```ini
[Unit]
Description=A-Shares Stock Analysis System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/stock-analyzer
Environment="PATH=/opt/stock-analyzer/venv/bin"
ExecStart=/opt/stock-analyzer/venv/bin/python main.py --schedule
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

### 2. Start Service

```bash
# Reload configuration
sudo systemctl daemon-reload

# Start service
sudo systemctl start stock-analyzer

# Auto-start on boot
sudo systemctl enable stock-analyzer

# View status
sudo systemctl status stock-analyzer

# View logs
journalctl -u stock-analyzer -f
```

---

## ⚙️ Configuration Notes

### Required Configuration

| Config Item | Description | How to Get |
|--------|------|----------|
| `ANSPIRE_API_KEYS` / `AIHUBMIX_KEY` / `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | Configure at least one AI model; Anspire or AIHubMix recommended first | Corresponding provider console |
| `STOCK_LIST` | Watchlist | Comma-separated stock codes |
| Notification Channel | Configure at least one, such as WeCom, Feishu, Telegram, or email | Corresponding notification platform |

### Optional Configuration

| Config Item | Default | Description |
|--------|--------|------|
| `SCHEDULE_ENABLED` | `false` | Whether to enable scheduled tasks |
| `SCHEDULE_TIME` | `18:00` | Daily execution time |
| `MARKET_REVIEW_ENABLED` | `true` | Whether to enable market review |
| `ANSPIRE_API_KEYS` | - | Anspire large model and news search (recommended) |
| `AIHUBMIX_KEY` | - | AIHubMix one key for multiple models (recommended) |
| `SERPAPI_API_KEYS` | - | SerpAPI real-time financial news search (recommended) |
| `TAVILY_API_KEYS` | - | Tavily news search (optional) |
| `MINIMAX_API_KEYS` | - | MiniMax search (optional) |

---

## 🌐 Proxy Configuration

If the server is in mainland China, accessing Gemini API requires a proxy:

### Docker Method

Edit `docker-compose.yml`:
```yaml
environment:
  - http_proxy=http://your-proxy:port
  - https_proxy=http://your-proxy:port
```

### Direct Deployment Method

Edit the top of `main.py`:
```python
os.environ["http_proxy"] = "http://your-proxy:port"
os.environ["https_proxy"] = "http://your-proxy:port"
```

---

## 📊 Monitoring and Maintenance

### Log Viewing

```bash
# Docker method
docker-compose -f ./docker/docker-compose.yml logs -f --tail=100

# Direct deployment
tail -f /opt/stock-analyzer/logs/stock_analysis_*.log
```

### Health Check

```bash
# Check process
ps aux | grep main.py

# Check recent reports
ls -la /opt/stock-analyzer/reports/
```

### Regular Maintenance

```bash
# Clean old logs (keep 7 days)
find /opt/stock-analyzer/logs -mtime +7 -delete

# Clean old reports (keep 30 days)
find /opt/stock-analyzer/reports -mtime +30 -delete
```

---

## ❓ FAQ

### 1. Docker Build Fails

```bash
# Clean cache and rebuild
docker-compose -f ./docker/docker-compose.yml build --no-cache
```

### 2. API Access Timeout

Check proxy configuration to ensure the server can access Gemini API.

### 3. Database Locked

```bash
# Stop service then delete lock file
rm /opt/stock-analyzer/data/*.lock
```

### 4. Insufficient Memory

The default Compose recommends `1G`. If OOM still occurs or the platform kills the container, increase the memory limit in `docker-compose.yml`; running `server + analyzer` simultaneously with multiple stocks, market review, image reports, or AlphaSift recommends `2G+`:
```yaml
deploy:
  resources:
    limits:
      memory: 1G
    reservations:
      memory: 512M
```

Low-spec environments using only `512M` should set `MAX_WORKERS=1`, only start one of `server` or `analyzer`, and reduce non-essential market review, news expansion, and image report tasks.

### 5. UI Elements Abnormally Enlarged / Layout Broken After Opening WebUI

**Symptom**: Port 8000 is accessible, but text, buttons, and cards on the page are abnormally enlarged without proper layout.

**Root Cause**: `static/index.html` exists but CSS/JS resource files are missing (`static/assets/` is empty or doesn't exist), preventing the browser from loading styles and scripts, resulting in bare HTML rendering.

**Solution**:

- **Docker Deployment**: Run the following commands to rebuild the image (ensure the frontend was correctly packaged into the image):
  ```bash
  docker-compose -f ./docker/docker-compose.yml down
  docker-compose -f ./docker/docker-compose.yml build --no-cache
  docker-compose -f ./docker/docker-compose.yml up -d
  ```
  After building, refresh browser cache (`Ctrl+Shift+R`) before accessing.

- **Direct Deployment (pip + python)**: Build the frontend first, then start the service:
  ```bash
  # Install Node.js 18+ (recommended 20+, if not installed)
  # Build frontend
  cd apps/dsa-web
  npm ci
  npm run build
  cd ../..
  # Start service
  python main.py --webui-only
  ```

**Verification**: Use browser developer tools (F12 → Network) to check for 404 errors on `/assets/index-*.js` and `/assets/index-*.css`; if present, resources are missing and rebuilding per the steps above will fix it.

---

## 🔄 Quick Migration

Migrate from one server to another:

```bash
# Source server: Package
cd /opt/stock-analyzer
tar -czvf stock-analyzer-backup.tar.gz .env data/ logs/ reports/

# Target server: Deploy
mkdir -p /opt/stock-analyzer
cd /opt/stock-analyzer
git clone <your-repo-url> .
tar -xzvf stock-analyzer-backup.tar.gz
docker-compose -f ./docker/docker-compose.yml up -d
```

---

## ☁️ Option 4: GitHub Actions Deployment (No Server Needed)

**The simplest option!** No server required; uses GitHub's free compute resources.

### Advantages
- ✅ **Completely free** (2000 minutes per month)
- ✅ **No server required**
- ✅ **Automatic scheduled execution**
- ✅ **Zero maintenance cost**

### Limitations
- ⚠️ Stateless (each run is a new environment)
- ⚠️ Scheduled tasks may have a few minutes delay
- ⚠️ Cannot provide HTTP API

### Deployment Steps

#### 1. Create GitHub Repository

```bash
# Initialize git (if not already done)
cd /path/to/daily_stock_analysis
git init
git add .
git commit -m "Initial commit"

# Create GitHub repository and push
# After creating a new repository on GitHub:
git remote add origin https://github.com/your-username/daily_stock_analysis.git
git branch -M main
git push -u origin main
```

#### 2. Configure Secrets (Important!)

Open repository page → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add the following Secrets:

| Secret Name | Description | Required |
|------------|------|------|
| `ANSPIRE_API_KEYS` | Anspire Open API Key (one key enables model and search) | Recommended |
| `AIHUBMIX_KEY` | AIHubMix API Key (one key for multiple models) | Recommended |
| `ANTHROPIC_API_KEY` | Anthropic API Key | Optional |
| `GEMINI_API_KEY` | Gemini AI API Key | Optional |
| `OPENAI_API_KEY` | OpenAI-compatible API Key | Optional |
| `WECHAT_WEBHOOK_URL` | WeCom bot Webhook | Optional* |
| `FEISHU_WEBHOOK_URL` | Feishu bot Webhook | Optional* |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | Optional* |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | Optional* |
| `TELEGRAM_MESSAGE_THREAD_ID` | Telegram Topic ID | Optional* |
| `EMAIL_SENDER` | Sender email | Optional* |
| `EMAIL_PASSWORD` | Email authorization code | Optional* |
| `SERVERCHAN3_SENDKEY` | ServerSauce³ Sendkey | Optional* |
| `CUSTOM_WEBHOOK_URLS` | Custom Webhook (comma-separated for multiple) | Optional* |
| `STOCK_LIST` | Watchlist, e.g., `600519,300750` | ✅ |
| `SERPAPI_API_KEYS` | SerpAPI Key | Recommended |
| `TAVILY_API_KEYS` | Tavily Search API Key | Optional |
| `BOCHA_API_KEYS` | Bocha Search API Key | Optional |
| `BRAVE_API_KEYS` | Brave Search API Key | Optional |
| `MINIMAX_API_KEYS` | MiniMax Coding Plan Web Search | Optional |
| `SEARXNG_BASE_URLS` | SearXNG self-hosted instance (quota-free fallback, requires format: json in settings.yml); when left empty, automatically discovers public instances by default | Optional |
| `SEARXNG_PUBLIC_INSTANCES_ENABLED` | Whether to automatically fetch public instances from `searx.space` when `SEARXNG_BASE_URLS` is empty (default `true`) | Optional |
| `TUSHARE_TOKEN` | Tushare Token | Optional |
| `GEMINI_MODEL` | Model name (default gemini-2.0-flash) | Optional |

> *Note: At least one notification channel must be configured; multiple channels can push simultaneously

#### 3. Verify Workflow File

Ensure `.github/workflows/00-daily-analysis.yml` exists and has been committed:

```bash
git add .github/workflows/00-daily-analysis.yml
git commit -m "Add GitHub Actions workflow"
git push
```

#### 4. Manual Test Run

1. Open repository page → **Actions** tab
2. Select **"Daily Stock Analysis"** workflow
3. Click **"Run workflow"** button
4. Select execution mode:
   - `full` - Full analysis (stocks + market)
   - `market-only` - Market review only
   - `stocks-only` - Stock analysis only
5. Click the green **"Run workflow"** button

#### 5. View Execution Logs

- The Actions page shows run history
- Click specific run records to view detailed logs
- Analysis reports are saved as Artifacts for 30 days

### Schedule Notes

Default configuration: **Monday to Friday, 18:00 Beijing Time** automatic execution

To change time: Edit the cron expression in `.github/workflows/00-daily-analysis.yml`:

```yaml
schedule:
  - cron: '0 10 * * 1-5'  # UTC time, +8 = Beijing time
```

Common cron examples:
| Expression | Description |
|--------|------|
| `'0 10 * * 1-5'` | Monday to Friday 18:00 (Beijing time) |
| `'30 7 * * 1-5'` | Monday to Friday 15:30 (Beijing time) |
| `'0 10 * * *'` | Every day 18:00 (Beijing time) |
| `'0 2 * * 1-5'` | Monday to Friday 10:00 (Beijing time) |

### Modify Watchlist

Method 1: Modify repository Secret `STOCK_LIST`

Method 2: Directly modify code and push:
```bash
# Modify .env.example or set default values in code
git commit -am "Update stock list"
git push
```

### FAQ

**Q: Why didn't the scheduled task execute?**
A: GitHub Actions scheduled tasks may have 5-15 minutes delay and only trigger when the repository has activity. Long periods without commits may cause the workflow to be disabled.

**Q: How to view historical reports?**
A: Actions → Select run record → Artifacts → Download `analysis-reports-xxx`

**Q: Is the free quota enough?**
A: Each run takes approximately 2-5 minutes, with 22 working days per month = 44-110 minutes, well below the 2000-minute limit.

---

## 🌐 Deployed to cloud server but don't know how to access with a browser?

See → [Cloud Server Web Interface Access Guide](deploy-webui-cloud.md)

Covers: Startup and access for both direct deployment and Docker methods, security group/firewall configuration, common troubleshooting, Nginx reverse proxy (optional).

---

**Happy deploying! 🎉**
