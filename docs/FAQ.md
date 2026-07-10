# ❓ Frequently Asked Questions (FAQ)

This document covers common issues and solutions encountered by users.

---

## 📊 Data

### Q1: US stock tickers (e.g., AMD, AAPL) show incorrect prices during analysis?

**Symptom**: After entering a US stock ticker, the displayed price is clearly wrong (e.g., AMD shows 7.33), or it is misidentified as an A-share.

**Cause**: Earlier versions prioritized domestic A-share code-matching rules, leading to code conflicts.

**Solution**:
1. Fixed in v2.3.0 — the system now auto-identifies US stock tickers.
2. If you still encounter issues, set the following in `.env`:
   ```bash
   YFINANCE_PRIORITY=0
   ```
   This gives priority to Yahoo Finance as the data source for US stocks.

> 📌 Related Issue: [#153](https://github.com/ZhuLinsen/daily_stock_analysis/issues/153)

---

### Q2: The "volume ratio" field in the report shows as empty or N/A?

**Symptom**: The volume ratio data is missing in the analysis report, affecting the AI's judgment on volume contraction.

**Cause**: The default real-time quote sources (e.g., Sina API) do not provide the volume ratio field.

**Solution**:
1. Fixed in v2.3.0 — the Tencent API now supports volume ratio parsing.
2. Recommended real-time quote source priority:
   ```bash
   REALTIME_SOURCE_PRIORITY=tencent,akshare_sina,efinance,akshare_em
   ```
3. The system has a built-in 5-day average volume calculation as a fallback.

> 📌 Related Issue: [#155](https://github.com/ZhuLinsen/daily_stock_analysis/issues/155)

---

### Q3: Tushare data retrieval fails with a token error?

**Symptom**: Logs show `Tushare data retrieval failed: invalid token, please verify`

**Solution**:
1. **No Tushare account**: No need to configure `TUSHARE_TOKEN`; the system will automatically use free data sources (AkShare, Efinance).
2. **Have a Tushare account**: Verify your token is correct by checking your [Tushare Pro](https://tushare.pro/weborder/#/login?reg=834638) profile page.
3. All core features of this project work normally without Tushare.

---

### Q4: Data retrieval is rate-limited or returns empty?

**Symptom**: Logs show `Circuit breaker triggered`, data returns `None`, or `RemoteDisconnected` / `push2his.eastmoney.com` connection closed errors appear.

**Cause**: Free data sources (Eastmoney, Sina, etc.) have anti-scraping mechanisms; rapid requests trigger rate limiting.

**Solution**:
1. The system has built-in multi-source auto-switching and circuit breaker protection.
2. Reduce the number of watchlist stocks, or increase the request interval.
3. Avoid frequent manual analysis triggers.
4. If the Eastmoney API frequently fails, set `ENABLE_EASTMONEY_PATCH=true` to enable the Eastmoney patch (injects NID token and random User-Agent to reduce rate-limiting).
5. Set `MAX_WORKERS=1` for serial fetching to reduce concurrent pressure on Eastmoney.

---

## ⚙️ Configuration

### Q5: GitHub Actions fails with a missing environment variable error?

**Symptom**: Actions logs show `GEMINI_API_KEY` or `STOCK_LIST` is not defined.

**Cause**: GitHub distinguishes between `Secrets` (encrypted) and `Variables` (plain text). Configuring in the wrong location causes read failures.

**Solution**:
1. Go to the repository `Settings` → `Secrets and variables` → `Actions`
2. **Secrets** (click `New repository secret`): Store sensitive information here
   - `GEMINI_API_KEY`
   - `OPENAI_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - Various Webhook URLs
3. **Variables** (click the `Variables` tab): Store non-sensitive configuration
   - `STOCK_LIST`
   - `GEMINI_MODEL`
   - `REPORT_TYPE`

> Compatibility note: The daily analysis workflow also binds to an Environment named `STOCK_LIST`, so placing `STOCK_LIST` in that Environment's variables will also be read. However, the recommended location remains Repository variables. Unless you want the daily task to wait for manual approval, do not configure required reviewers, wait timers, or deployment branch restrictions on that Environment.

---

### Q6: Configuration changes in the .env file didn't take effect?

**Solution**:
1. Ensure the `.env` file is located in the project root directory.
2. **Docker deployment / WebUI system settings**:
   - `--env-file .env` / Compose `env_file` only injects the host `.env` as startup environment variables into the container; it does not automatically create or write back to the container's `/app/.env`.
   - The WebUI settings page displays startup-injected environment variables as fallback when the active `.env` file is missing certain keys; but "Export `.env`" still only exports the current active configuration file content.
   - After WebUI saves, `STOCK_LIST`, `SCHEDULE_ENABLED`, `SCHEDULE_TIME`, `SCHEDULE_TIMES`, `SCHEDULE_RUN_IMMEDIATELY`, and `RUN_IMMEDIATELY` are written back to the container's `.env`.
   - After WebUI saves, it triggers a configuration reload in the current process; the running read path will synchronously use the latest written `.env` — e.g., scheduled tasks will continue hot-reading the saved `STOCK_LIST`.
   - If the container startup command passes these same-name environment variables (e.g., `--env-file .env`, `docker run -e ...`, or Compose `environment:`), subsequent restarts may still prioritize the startup environment variables. To let WebUI saved values take over, update or remove these same-name overrides accordingly.
   - To persist WebUI-saved configuration, point `ENV_FILE` to a writable data volume file like `/app/data/runtime.env` instead of bind-mounting the host's `.env` file to `/app/.env`.
   - `SCHEDULE_ENABLED`, `SCHEDULE_TIME`, and `SCHEDULE_TIMES` after saving will cause WebUI/API/Desktop long-running processes to start, stop, or rebuild the runtime scheduler per the new configuration.
   - `SCHEDULE_RUN_IMMEDIATELY` and `RUN_IMMEDIATELY` are startup/one-time run configurations; saving them does not immediately trigger an analysis run.
3. **Docker manual .env changes**: After modifying, restart the container:
   ```bash
   docker-compose down && docker-compose up -d
   ```
4. **GitHub Actions**: The `.env` file does not apply; you must configure via Secrets/Variables.
5. Check for multiple `.env` files (e.g., `.env.local`) that may be overriding.

---

### Q7: How do I configure a proxy for accessing the Gemini/OpenAI API?

**Solution**:

Configure in `.env`:
```bash
USE_PROXY=true
PROXY_HOST=127.0.0.1
PROXY_PORT=10809
```

> ⚠️ Note: Proxy configuration only applies to local runs. GitHub Actions environments do not need proxy configuration.

---

### Common LLM Configuration Questions

> Full details: [LLM Configuration Guide](LLM_CONFIG_GUIDE.md).

**Q: I configured both GEMINI_API_KEY and LLM_CHANNELS, but it only uses the channel?**

The system takes only one source by priority: Advanced model routing YAML (`LITELLM_CONFIG`) > `LLM_CHANNELS` > legacy keys. YAML only takes effect when the file parses successfully and produces a valid `model_list`; if the YAML path is invalid or the content is empty, the system falls back to `LLM_CHANNELS` or legacy keys. Once a higher-priority layer takes effect, lower-priority configurations do not participate.

**Q: What if check_env reports "No usable AI model configured"?**

By default, select one provider and fill in the corresponding API Key. To pin a primary model, set `LITELLM_MODEL=provider/model`. For multi-model switching, configure `LLM_CHANNELS` or the advanced model routing YAML. Run `python scripts/check_env.py --config` to verify configuration, and `python scripts/check_env.py --llm` to actually call the API.

**Q: How do I use multiple models simultaneously (e.g., AIHubmix + DeepSeek + Gemini)?**

Use channel mode: set `LLM_CHANNELS=aihubmix,deepseek,gemini` and configure each channel's `LLM_{NAME}_BASE_URL`, `LLM_{NAME}_API_KEY`, and `LLM_{NAME}_MODELS`. You can also configure visually in the Web settings page → AI Model → AI Model Integration.

**Q: The stock-ask Agent says no usable LLM is configured, but I only have legacy `GEMINI_*` / `OPENAI_*` / `ANTHROPIC_*` configs — what do I do?**

First check whether `LITELLM_CONFIG` or `LLM_CHANNELS` is enabled; if so, higher-priority config overrides legacy keys. If neither is enabled and `AGENT_LITELLM_MODEL` is empty, the stock-ask Agent will still auto-inherit legacy provider models: `GEMINI_MODEL`, `OPENAI_MODEL`, `ANTHROPIC_MODEL` map to corresponding LiteLLM model names. This fix does not silently migrate or clear old configs; it simply returns the true missing cause to the frontend for easier diagnosis. Full compatibility semantics: see [LLM Configuration Guide](LLM_CONFIG_GUIDE.md) "Stock Ask Agent / LiteLLM Config Compatibility Notes".

---

## 📱 Notifications

### Q8: Bot push fails with a "message too long" error?

**Symptom**: Analysis succeeded but no push was received; logs show a 400 error or `Message too long`.

**Cause**: Different platforms have different message length limits:
- WeChat Work: 4KB
- Feishu: 20KB
- DingTalk: 20KB

**Solution**:
1. **Auto-chunking**: The latest version automatically splits long messages.
2. **Single stock push mode**: Set `SINGLE_STOCK_NOTIFY=true` to push immediately after each stock analysis.
3. **Simplified report**: Set `REPORT_TYPE=simple` for a concise format.

---

### Q9: Telegram push notifications are not received?

**Solution**:
1. Ensure both `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are configured.
2. How to get your Chat ID:
   - Send any message to your bot
   - Visit `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - Find `chat.id` in the returned JSON
3. Make sure the bot has been added to the target group (for group chats).
4. Local runs need access to the Telegram API (may require a proxy).

---

### Q10: WeChat Work Markdown formatting appears broken?

**Solution**:
1. WeChat Work has limited Markdown support; try setting:
   ```bash
   WECHAT_MSG_TYPE=text
   ```
2. This will send messages in plain text format.

---

## 🤖 AI Model

### Q11: Gemini API returns 429 error (too many requests)?

**Symptom**: Logs show `Resource has been exhausted` or `429 Too Many Requests`.

**Solution**:
1. Gemini free tier has rate limits (~15 RPM).
2. Reduce the number of stocks analyzed simultaneously.
3. Increase request delays:
   ```bash
   GEMINI_REQUEST_DELAY=5
   ANALYSIS_DELAY=10
   ```
4. Or switch to an OpenAI-compatible API as a fallback.

---

### Q12: How do I use domestic models like DeepSeek?

**Configuration**:

```bash
# No need to configure GEMINI_API_KEY
OPENAI_API_KEY=sk-xxxxxxxx
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-v4-flash
# deepseek-chat / deepseek-reasoner remain compatible but are deprecated after 2026/07/24
```

Supported model services:
- DeepSeek: `https://api.deepseek.com`
- Tongyi Qianwen: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- Moonshot: `https://api.moonshot.cn/v1`

---

### Q12b: How do I use Ollama local models?

**Configuration**: Use `OLLAMA_API_BASE` + `LITELLM_MODEL`, or channel mode (`LLM_CHANNELS=ollama` + `LLM_OLLAMA_BASE_URL` + `LLM_OLLAMA_MODELS`).

**Pitfall**: Do NOT use `OPENAI_BASE_URL` to configure Ollama, or the system will construct incorrect URLs (e.g., 404, `api/generate/api/show`). See [LLM Configuration Guide](LLM_CONFIG_GUIDE.md) Example 4 and channel examples.

---

### Q12c: What if I get `OllamaException / APIConnectionError` (All LLM models failed) at runtime?

**Symptom**: Logs show `litellm.APIConnectionError: OllamaException` or `Analysis failed: All LLM models failed (tried 1 model(s))`.

Check the following 5 checkpoints:

1. **Is the Ollama service running?**
   ```bash
   # Check process
   pgrep -a ollama
   # If no output, start it first
   ollama serve
   ```
   Verify the service is listening: `curl http://localhost:11434` should return `Ollama is running`.

2. **Is `OLLAMA_API_BASE` configured correctly?**
   - ✅ Correct: `OLLAMA_API_BASE=http://localhost:11434`
   - ❌ Wrong: Putting the Ollama address in `OPENAI_BASE_URL` causes URL path errors (e.g., `…/api/generate/api/show`).

3. **Does the model name have the `ollama/` prefix?**
   - ✅ Correct: `LITELLM_MODEL=ollama/qwen3:8b`
   - ❌ Wrong: `LITELLM_MODEL=qwen3:8b` (missing prefix, litellm cannot route to Ollama)

4. **Is the model downloaded locally?**
   ```bash
   ollama list          # List available models
   ollama pull qwen3:8b # Pull if not present
   ```

5. **Network and firewall for remote / Docker deployment**
   - If Ollama and the application are on different hosts, set `OLLAMA_API_BASE` to the actual IP, e.g., `http://192.168.1.100:11434`.
   - Ensure the firewall allows port 11434 and that Ollama is bound to the correct address (`OLLAMA_HOST=0.0.0.0:11434`).

> Full configuration examples: see [LLM Configuration Guide → Example 4 (Ollama)](LLM_CONFIG_GUIDE.md#example-4-ollama).

---

## 🐳 Docker

### Q13: Docker container exits immediately after starting?

**Solution**:
1. Check container logs:
   ```bash
   docker logs <container_id>
   ```
2. Common causes:
   - Environment variables not configured correctly
   - `.env` file format errors (e.g., extra spaces)
   - Dependency version conflicts

---

### Q14: API service is inaccessible inside Docker?

**Solution**:
1. Ensure the startup command includes `--host 0.0.0.0` (not 127.0.0.1).
2. Check port mapping is correct:
   ```yaml
   ports:
     - "8000:8000"
   ```

---

### Q14.1: DNS resolution fails inside Docker (e.g., api.tushare.pro, searchapi.eastmoney.com cannot be resolved)?

**Symptom**: Logs show `Temporary failure in name resolution` or `NameResolutionError`; stock data APIs and LLM APIs are both inaccessible.

**Cause**: Under a custom bridge network, the container uses Docker's built-in DNS, which may fail to resolve in certain network environments with bypass routers.

**Solution** (try in order):

1. **Explicitly configure DNS**: Add the following under `x-common` in `docker/docker-compose.yml`:
   ```yaml
   dns:
     - 223.5.5.5
     - 119.29.29.29
     - 8.8.8.8
   ```
   Then run `docker-compose down` and `docker-compose up -d --force-recreate` to recreate the container.

2. **Switch to host network mode**: If the above still does not work, add `network_mode: host` under the `server` service and remove `ports` mapping. With host mode, `ports` is ineffective — **the port is determined by `--port` in the `command`**. If the host's default port is occupied, modify it (e.g., set `API_PORT=8080` in `.env`) and access `http://localhost:8080` accordingly.

> 📌 Related Issue: [#372](https://github.com/ZhuLinsen/daily_stock_analysis/issues/372)

---

### Q14.2: During Docker installation, where is the software version number stored?

**Conclusion**: For Docker users, **the most authoritative version is not a Python source file constant but the image tag you are actually using**.

**Why**:
1. Docker releases are triggered by `.github/workflows/docker-publish.yml`; a release image is only generated when a Git tag in the `v*.*.*` format (e.g., `v3.12.0`) is pushed.
2. This means Docker image versions inherently follow **GitHub Releases / Git tags**, not values hardcoded in `main.py`, `server.py`, or other backend source files.
3. The `version` field in `apps/dsa-web/package.json` is currently a placeholder value `0.0.0`. The WebUI "Version Info" card is better suited for checking whether static assets have been rebuilt, not as the Docker release version.
4. The desktop app version is maintained separately in `apps/dsa-desktop/package.json`; it represents only the Electron desktop app, not the Docker image version.

**How to check the current Docker version**:
1. **Check the image tag in your deployment command or Compose file**: e.g., `ghcr.io/zhulinsen/daily_stock_analysis:v3.12.0` — `v3.12.0` is the current deployment version.
2. **If you pulled `latest`**: Review the `docker pull` / `docker-compose.yml` / deployment script from that time, or check [GitHub Releases](https://github.com/ZhuLinsen/daily_stock_analysis/releases) for the corresponding release record.
3. **If you just want to verify the frontend has been rebuilt**: Open the WebUI "System Settings" page to check the `Build ID` / `Build Time`; this confirms whether static assets are refreshed, but does not equal the Docker image release version.

**Recommendation**: To avoid repeated updates, pin a specific version tag (e.g., `v3.12.0`) during deployment rather than relying on `latest` long-term.

---

## 🔧 Other

### Q15: How do I run only the market review without analyzing individual stocks?

**Method**:
```bash
# Local run
python main.py --market-only

# GitHub Actions
# When manually triggered, select mode: market-only
```

---

### Q16: Buy/Watch/Sell count statistics in analysis results are incorrect?

**Cause**: Earlier versions used regex matching for statistics, which could be inconsistent with actual recommendations.

**Solution**: Fixed in the latest version; the AI model now directly outputs a `decision_type` field for accurate statistics.

---

### Q17: Why does manually triggering on GitHub Actions still show "non-trading day, skipped" on weekends?

**Symptom**: `TRADING_DAY_CHECK_ENABLED` is configured or you want to run manually, but logs still show "All relevant markets are non-trading days today, skipping execution."

**Solution**:
1. Open `Actions → Daily Stock Analysis → Run workflow`
2. When manually triggering, set `force_run` to `true` (one-time forced run).
3. To permanently disable trading-day checks, set in `Settings → Secrets and variables → Actions`:
   ```bash
   TRADING_DAY_CHECK_ENABLED=false
   ```

**Rules**:
- `TRADING_DAY_CHECK_ENABLED=true` and `force_run=false`: Skip on non-trading days (default)
- `force_run=true`: Execute even on non-trading days
- `TRADING_DAY_CHECK_ENABLED=false`: No trading-day checks for either scheduled or manual runs

---

## 💬 Still have questions?

If the above did not resolve your issue, feel free to:
1. Check the [Full Configuration Guide](full-guide.md)
2. Search or submit a [GitHub Issue](https://github.com/ZhuLinsen/daily_stock_analysis/issues)
3. Check the [Changelog](CHANGELOG.md) for the latest fixes

---

*Last updated: 2026-04-20*
