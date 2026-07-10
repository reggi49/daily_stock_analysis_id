# Cloud Server Web Interface Access Guide

If you've already deployed the project to a cloud server but don't know what address to enter in the browser to open the Web management interface, this tutorial is for you.

> It's really just two steps: make the service listen on the external network, then enter the address in your browser.

---

## Table of Contents

- [Option 1: Direct Deployment (pip + python)](#option-1-direct-deployment-pip--python)
- [Option 2: Docker Compose](#option-2-docker-compose)
- [How to Open the Interface in Your Browser](#how-to-open-the-interface-in-your-browser)
- [How to Verify Docker Rebuild Was Effective](#how-to-verify-docker-rebuild-was-effective)
- [Can't Access? Check These First](#cant-access-check-these-first)
- [Optional: Nginx Reverse Proxy (Domain Binding / Port 80)](#optional-nginx-reverse-proxy-domain-binding--port-80)
- [Security Recommendations](#security-recommendations)

---

## Option 1: Direct Deployment (pip + python)

### Step 1: Modify the listening address in .env

Open `.env` in the project root (the directory containing `main.py`) with an editor and find this line:

```env
WEBUI_HOST=127.0.0.1
```

Change `127.0.0.1` to `0.0.0.0`:

```env
WEBUI_HOST=0.0.0.0
```

> `127.0.0.1` means only local access; `0.0.0.0` allows access from any source. Cloud servers need to change `WEBUI_HOST` in `.env` to `0.0.0.0`, or explicitly pass `--host 0.0.0.0` in the startup command, to open the interface from the external network.

### Step 2: Start the service

Execute in the project root directory:

```bash
# Start only the Web UI (without automatic analysis)
python main.py --webui-only

# Or: Start the Web UI (runs one analysis at startup; for daily scheduled analysis, add --schedule or set SCHEDULE_ENABLED=true)
python main.py --webui
```

After successful startup, the terminal will output something like:

```
FastAPI service started: http://0.0.0.0:8000
```

If you want the service to continue running after exiting the terminal, use `nohup`:

```bash
nohup python main.py --webui-only > /dev/null 2>&1 &
```

> Log files are automatically written to the `logs/` directory by the program; view with `tail -f logs/stock_analysis_*.log`.

### Change Port (Optional)

The default port is 8000. To use a different port, set in `.env`:

```env
WEBUI_PORT=8888
```

Then restart the service.

---

## Option 2: Docker Compose

### Step 1: Confirm .env configuration

The project's `docker/docker-compose.yml` automatically sets `WEBUI_HOST=0.0.0.0` inside the container, so you don't need to change the listening address in `.env`; Docker handles it automatically.

The `env_file: ../.env` in Docker Compose only injects `.env` as **startup environment variables** into the container; it does not create `/app/.env` inside the container, nor does it allow WebUI to write back to the host's `.env` when saving configuration. The new WebUI displays startup-injected environment variables as fallback when the active `.env` file is missing certain keys, so you can see the Docker-started configuration on the page; but "Export `.env`" still only exports the current active configuration file content.

If you want configuration saved in WebUI to persist after container deletion, rebuild, or upgrade, place the active configuration file on a mounted data volume. For example, add to Compose's `environment`:

```yaml
- ENV_FILE=/app/data/runtime.env
```

Also keep the `../data:/app/data` mount. Note: if the startup `../.env`, `docker run -e`, or Compose `environment:` still contains old same-name values, those startup environment variables may still override saved values in the runtime file after container restart; to let WebUI-saved values take effect, update or remove same-name overrides from the startup environment.

### Step 2: Start the service

Execute in the project root directory:

```bash
# Start both scheduled analysis + Web interface (recommended)
docker-compose -f ./docker/docker-compose.yml up -d

# Or start only the Web interface service
docker-compose -f ./docker/docker-compose.yml up -d server
```

Check status after starting:

```bash
docker-compose -f ./docker/docker-compose.yml ps
```

If the `server` service status shows `running`, the Web interface is running.

### Change Port (Optional)

The default port is 8000. To use a different port, set in `.env`:

```env
API_PORT=8888
```

Then restart the container:

```bash
docker-compose -f ./docker/docker-compose.yml down
docker-compose -f ./docker/docker-compose.yml up -d
```

---

## How to Open the Interface in Your Browser

After starting the service, enter in your browser's address bar:

```
http://your-server-public-IP:8000
```

For example, if your server IP is `1.2.3.4`, enter:

```
http://1.2.3.4:8000
```

If your domain is already pointed to this server, you can also access directly using the domain:

```
http://your-domain.com:8000
```

> **Where to find the public IP?** Log in to your cloud server console (Alibaba Cloud/Tencent Cloud/AWS etc.), and you can see "Public IP" or "Elastic IP" in the instance list.

---

## How to Verify Docker Rebuild Was Effective

First, distinguish between two things:

1. **Docker image release version**: Check the image tag you used when deploying, e.g., `ghcr.io/zhulinsen/daily_stock_analysis:v3.12.0`. Docker releases in this repository are triggered by `.github/workflows/docker-publish.yml` via `v*.*.*` Git tags, so the Docker version should be based on the image tag / GitHub Releases.
2. **Frontend build currently loaded on the page**: Check the version info card on the WebUI "System Settings" page, which confirms whether the browser has fetched updated static assets.

In other words, **the version info in "System Settings" is better suited for verifying whether the frontend was rebuilt successfully, and is not equivalent to the Docker image release version**.

The WebUI now displays a read-only "Version Info" card on the "System Settings" page, including:

- `WebUI Version`
- `Build ID`
- `Build Time`

If the version number in `apps/dsa-web/package.json` is still the placeholder `0.0.0`, the page automatically falls back to showing the `Build ID` generated by the current frontend build, so you don't mistake the placeholder version for a real release version.

When you re-execute `docker-compose -f ./docker/docker-compose.yml up -d --build`, or separately rebuild the frontend with `npm run build`, refresh the browser and open "System Settings" to check whether the `Build Time` has changed; if it has, the currently loaded static assets have typically switched to the latest build.

If you want to confirm "which official version am I actually deploying right now", prefer the following approaches:

```yaml
# Option 1: Check the image tag in docker-compose / deployment script
image: ghcr.io/zhulinsen/daily_stock_analysis:v3.12.0
```

```bash
# Option 2: Review your pull command
docker pull ghcr.io/zhulinsen/daily_stock_analysis:v3.12.0
```

If you've been using `latest`, it's recommended to switch to an explicit version tag; otherwise it's difficult to determine from container page information alone whether you've already updated to the same version.

When verifying the local frontend build pipeline, run the following as a minimal validation loop:

```bash
cd apps/dsa-web
npm ci
npm run lint
npm run build
```

After a successful `build`, the `index.html`/JS/CSS resources generated under `static` will include the current build time and build version info; after refreshing, the "Version Info" card should reflect the changes.

---

## Can't Access? Check These First

### 1. Security group / firewall has not opened the port

This is the most common cause. Cloud servers only open port 22 (SSH) by default; you need to manually open port 8000 (or your configured port).

**How to fix** (using Alibaba Cloud as an example):
1. Log in to the Alibaba Cloud console -> ECS -> find your instance
2. Click "Security Groups" -> "Configure Rules" -> "Add Security Group Rule"
3. Set direction to "Inbound", port range to `8000/8000`, authorization object to `0.0.0.0/0`, then click "OK"

Tencent Cloud, AWS, and other cloud providers have similar operations; find "Security Groups" or "Firewall Rules" and add an inbound rule allowing TCP port 8000.

### 2. Server system firewall is blocking

If your system has `ufw` or `firewalld` enabled, you also need to open the port:

```bash
# Ubuntu / Debian (ufw)
sudo ufw allow 8000

# CentOS / RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

### 3. WEBUI_HOST in .env not changed (direct deployment)

This is the second most common cause. `.env` defaults to `WEBUI_HOST=127.0.0.1`, meaning the service only listens locally and external connections cannot reach it.

Fix: Open `.env`, change `WEBUI_HOST=127.0.0.1` to `WEBUI_HOST=0.0.0.0`, then restart the service; or you can explicitly add `--host 0.0.0.0` to the startup command.

> Docker deployments don't need this change; you can skip it.

### 4. Port number mismatch

Check whether the port in the access URL matches the port set in `.env` / the startup command.

- Direct deployment: default 8000, changeable via `WEBUI_PORT=xxxx`
- Docker: default 8000, changeable via `API_PORT=xxxx`

### 5. Page loads but UI elements are abnormally large / layout is broken

**Symptom**: The browser can reach port 8000, the page has content, but text, buttons, and cards are abnormally large without normal layout or styling.

**Root cause**: `static/index.html` exists but CSS/JS resources are missing (`static/assets/` is empty or nonexistent); the browser loaded the HTML framework but couldn't fetch styles and scripts, degrading to bare HTML rendering.

First check with browser DevTools (F12 -> Network tab) for **404** errors on `/assets/index-*.js` or `/assets/index-*.css`. If found, fix as follows:

**Docker users**:

```bash
docker-compose -f ./docker/docker-compose.yml down
docker-compose -f ./docker/docker-compose.yml build --no-cache
docker-compose -f ./docker/docker-compose.yml up -d
```

After rebuilding, force-refresh the browser cache with `Ctrl+Shift+R`, then visit the page.

**Direct deployment users**: First ensure Node.js 18+ (recommended 20+) is installed, then manually build the frontend:

```bash
cd apps/dsa-web
npm ci
npm run build
cd ../..
python main.py --webui-only
```

---

## Optional: Nginx Reverse Proxy (Domain Binding / Port 80)

If you have a domain or don't want to include `:8000` in the address, you can use Nginx as a reverse proxy to forward port 80/443 traffic to the backend service.

### Install Nginx

```bash
# Ubuntu / Debian
sudo apt update && sudo apt install -y nginx

# CentOS
sudo yum install -y nginx
```

### Configuration file example

Create a new file `/etc/nginx/conf.d/stock-analyzer.conf` with the following content (replace `your-domain.com` with your domain or IP):

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (required for Agent chat page)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Enable configuration and restart Nginx

```bash
sudo nginx -t            # Check for syntax errors in the configuration
sudo systemctl reload nginx
```

After successful configuration, access via `http://your-domain.com` directly without needing to include the port number.

> **Notes after enabling Nginx**:
> - If you've enabled web login authentication (`ADMIN_AUTH_ENABLED=true`), it's recommended to also enable `TRUST_X_FORWARDED_FOR=true` in `.env`; otherwise the system may not correctly identify the real IP. This option is suitable for **single-layer trusted reverse proxy** (Nginx -> App) deployments; if using multi-level proxies or CDN (CDN -> Nginx -> App), the login rate-limiting key may degrade to the edge proxy IP instead of the real client IP, which requires evaluation based on your actual topology.
> - For HTTPS, you can use [Certbot](https://certbot.eff.org/) to automatically request free Let's Encrypt certificates.

---

## Security Recommendations

Before exposing the Web interface to the public network, it's strongly recommended to enable login password protection:

Set in `.env`:

```env
ADMIN_AUTH_ENABLED=true
```

After restarting the service, the first time you visit the page it will prompt you to set an initial password. After setup, every time you open the settings page you'll need to enter the password, preventing sensitive configurations like API Keys from being seen by others.

> If you forget the password, run on the server: `python -m src.auth reset_password`

---

Encountered other issues? Feel free to [submit an Issue](https://github.com/ZhuLinsen/daily_stock_analysis/issues).
