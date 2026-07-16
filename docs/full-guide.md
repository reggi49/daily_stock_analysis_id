# Complete Configuration and Deployment Guide

This document contains the complete configuration guide for the A-share AI Stock Analysis System, intended for users who need advanced features or special deployment methods.

> For quick start, see [README.md](../README.md); this document covers advanced configuration.

## Project Structure

```
daily_stock_analysis/
├── main.py              # Main entry point
├── src/                 # Core business logic
│   ├── analyzer.py      # AI analyzer
│   ├── config.py        # Configuration management
│   ├── notification.py  # Message push notifications
│   └── ...
├── data_provider/       # Multi-source data adapters
├── bot/                 # Bot interaction module
├── api/                 # FastAPI backend service
├── apps/dsa-web/        # React frontend
├── docker/              # Docker configuration
├── docs/                # Project documentation
└── .github/workflows/   # GitHub Actions
```

## Table of Contents

- [Project Structure](#project-structure)
- [GitHub Actions Configuration](#github-actions-configuration)
- [Complete Environment Variables List](#complete-environment-variables-list)
- [Docker Deployment](#docker-deployment)
- [Local Deployment](#local-deployment)
- [Scheduled Task Configuration](#scheduled-task-configuration)
- [Notification Channel Configuration](#notification-channel-configuration)
- [Data Source Configuration](#data-source-configuration)
- [Advanced Features](#advanced-features)
- [Backtesting](#backtesting)
- [Local WebUI Management Interface](#local-webui-management-interface)

---

## GitHub Actions Configuration

### 1. Fork this Repository

Click the `Fork` button in the upper right corner.

### 2. Configure Secrets

Go to your forked repo → `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

<div align="center">
  <img src="assets/secret_config.png" alt="GitHub Secrets Configuration diagram" width="600">
</div>

#### AI Model configuration（Configure at least one）

| Secret Name | Description | Required |
|------------|------|:----:|
| `ANSPIRE_API_KEYS` | [Anspire](https://open.anspire.cn/?share_code=QFBC0FYC) API Key，one Key Enable large models and Chinese optimization network search at the same time，Includes free quota for this project | Recommended |
| `AIHUBMIX_KEY` | [AIHubMix](https://aihubmix.com/?aff=CfMq) API Key，one Key Switch to use the full series model，This project is available 10% Discount | Recommended |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/) Get free Key | Optional |
| `ANTHROPIC_API_KEY` | Anthropic Claude API Key | Optional |
| `OPENAI_API_KEY` | OpenAI Compatible API Key（support DeepSeek、Tongyi Qianwen et al.） | Optional |
| `OPENAI_BASE_URL` | OpenAI Compatible API address（Such as `https://api.deepseek.com`） | Optional |
| `OPENAI_MODEL` | Model name（Such as `gemini-3.1-pro-preview`、`deepseek-v4-flash`、`gpt-5.5`） | Optional |

> *Note：above model Key / Configure at least one channel；Recommend priority from Anspire or AIHubMix This kind of Key Multi-model service starts。Configuration verification at startup will be performed when missing available AI model Key Or give a clear error message when using the model channel。

#### Notification channel configuration（Multiple configurations can be configured at the same time，push all）

> notification channel、minimal/advanced key layered、Actions mapping、`--check-notify` Diagnosis、Web One-click testing and local / Docker / GitHub Actions / Desktop See scene description for details [Notification topic document](notifications.md)。

| Secret Name | Description | Required |
|------------|------|:----:|
| `WECHAT_WEBHOOK_URL` | Enterprise WeChat Webhook URL | Optional |
| `FEISHU_WEBHOOK_URL` | Feishu Webhook URL | Optional |
| `FEISHU_WEBHOOK_SECRET` | Feishu Webhook Signing key（turn on“Signature verification”Required when） | Optional |
| `FEISHU_WEBHOOK_KEYWORD` | Feishu Webhook keywords（turn on“keywords”Required when） | Optional |
| `DINGTALK_WEBHOOK_URL` | DingTalk Group Robot Webhook URL | Optional |
| `DINGTALK_SECRET` | DingTalk group robot signing key (SECBeginning) | Optional |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token（@BotFather Get） | Optional |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | Optional |
| `TELEGRAM_MESSAGE_THREAD_ID` | Telegram Topic ID (For sending to subtopics) | Optional |
| `DISCORD_WEBHOOK_URL` | Discord Webhook URL（[Create method](https://support.discord.com/hc/en-us/articles/228383668)） | Optional |
| `DISCORD_BOT_TOKEN` | Discord Bot Token（with Webhook Choose one） | Optional |
| `DISCORD_MAIN_CHANNEL_ID` | Discord Channel ID（Use Bot when needed） | Optional |
| `DISCORD_INTERACTIONS_PUBLIC_KEY` | Discord Public Key（Inbound only Interaction/Webhook Required when calling back for signature verification） | Optional |
| `SLACK_BOT_TOKEN` | Slack Bot Token（Recommended，Support image upload；When configured at the same time, it takes precedence over Webhook） | Optional |
| `SLACK_CHANNEL_ID` | Slack Channel ID（Use Bot when needed） | Optional |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL（text only，Pictures not supported） | Optional |
| `EMAIL_SENDER` | Sender's email（Such as `xxx@qq.com`） | Optional |
| `EMAIL_PASSWORD` | Email authorization code（Non-login password） | Optional |
| `EMAIL_RECEIVERS` | Recipient email（Multiple separated by commas，Leave blank to send to yourself） | Optional |
| `EMAIL_SENDER_NAME` | Sender display name（Default：daily_stock_analysisStock Analysis Assistant） | Optional |
| `PUSHPLUS_TOKEN` | PushPlus Token（[Get address](https://www.pushplus.plus)，Domestic push service） | Optional |
| `SERVERCHAN3_SENDKEY` | ServerSauce³ Sendkey（[Get address](https://sc3.ft07.com/)，mobile phoneAPPpush service） | Optional |
| `ASTRBOT_URL` | AstrBot Webhook URL | Optional |
| `ASTRBOT_TOKEN` | AstrBot Bearer Token（Optional） | Optional |
| `NTFY_URL` | ntfy complete topic endpoint，must contain topic path，For example `https://ntfy.sh/my-topic` | Optional |
| `NTFY_TOKEN` | ntfy Bearer Token（Optional） | Optional |
| `GOTIFY_URL` | Gotify server base URL，Not included `/message`；The system will automatically splice `/message` | Optional |
| `GOTIFY_TOKEN` | Gotify application token，Pass `X-Gotify-Key` Header send | Optional |
| `CUSTOM_WEBHOOK_URLS` | Customize Webhook（Support DingTalk, etc.，Multiple separated by commas） | Optional |
| `CUSTOM_WEBHOOK_BEARER_TOKEN` | Customize Webhook of Bearer Token（For those requiring certification Webhook） | Optional |
| `CUSTOM_WEBHOOK_BODY_TEMPLATE` | Customize Webhook JSON body Template，adapt AstrBot、NapCat、Self-built services and other special payload | Optional |
| `WEBHOOK_VERIFY_SSL` | Read the configuration webhook-style HTTPS Notification request certificate verification（Default true）。set to false Can support self-signed certificates。warning：Closure poses serious security risk（MITM），Trusted intranet only | Optional |

> *Note：Configure at least one channel，If multiple configurations are configured, they will be pushed simultaneously.。Configuration verification will prompt at startup Telegram / Email paired fields are missing，and common Webhook URL Not with `http://` or `https://` opening question。
>
> Current default `00-daily-analysis.yml` Only explicit mapping fixed Secret / Variable Name，will not automatically `STOCK_GROUP_1`、`EMAIL_GROUP_1` Such arbitrary numbered variables are imported into the running environment，It will not be automatically imported `NEWS_INTEL_AUTO_FETCH_ENABLED` This type of new optional switch。Therefore, the group mailbox function and local information automatic refresh capability are currently not applicable to the warehouse's own default GitHub Actions workflow；They apply locally `.env`、Docker，Or you explicitly expanded it yourself `env:` mapped runtime environment。Actions Explicitly mapped `CUSTOM_WEBHOOK_BODY_TEMPLATE`、`WEBHOOK_VERIFY_SSL`、`FEISHU_WEBHOOK_SECRET`、`FEISHU_WEBHOOK_KEYWORD`、`PUSHPLUS_TOPIC`、`NTFY_URL`、`NTFY_TOKEN`、`GOTIFY_URL`、`GOTIFY_TOKEN`、P3 notification routing keys and P4 Notification noise reduction key；`MARKDOWN_TO_IMAGE_CHANNELS` and `MERGE_EMAIL_NOTIFICATION` Still as a behavior switch and not by default workflow Automatic mapping in。

#### Push behavior configuration

| Secret Name | Description | Required |
|------------|------|:----:|
| `SINGLE_STOCK_NOTIFY` | Single stock push mode：set to `true` Then every time a stock is analyzed, it will be pushed immediately. | Optional |
| `REPORT_TYPE` | report type：`simple`(Streamline)、`full`(complete)、`brief`(3-5sentence summary)，DockerThe environment recommendation is set to `full` | Optional |
| `REPORT_LANGUAGE` | Report output language：`zh`(Default Chinese) / `en`(English) / `ko`(Korean)；will affect simultaneously Prompt、Template、Notification fallback with Web Report page fixed copy。`ko` Reuse the English structural skeleton and constrain the model to output in Korean through output language instructions，Notifications render localized labels by reporting language。Warehouse comes with `00-daily-analysis.yml` The variable is explicitly mapped，directly in Actions Secrets/Variables The configuration will take effect | Optional |
| `REPORT_SUMMARY_ONLY` | Analyze results summary only：set to `true` Only push summary，Does not include individual stock details；Suitable for quick browsing when there are multiple stocks（Default false，Issue #262） | Optional |
| `REPORT_SHOW_LLM_MODEL` | Indicates whether the bottom of the notification report displays the LLM Model name，Default `true`；set to `false` Runtime model information can be hidden。This variable only adjusts impressions，does not affect provider/model/Base URL、LiteLLM Route or runtime model saving/Migrate/Clean up semantics。 | Optional |
| `REPORT_TEMPLATES_DIR` | Jinja2 Template directory（Relative to project root，Default `templates`） | Optional |
| `REPORT_RENDERER_ENABLED` | enable Jinja2 template rendering（Default `false`，Guaranteed zero return） | Optional |
| `REPORT_INTEGRITY_ENABLED` | Enable report integrity check，Retry or placeholder completion when required fields are missing（Default `true`） | Optional |
| `REPORT_INTEGRITY_RETRY` | Integrity check retries（Default `1`，`0` Indicates only occupying space without retrying） | Optional |
| `REPORT_HISTORY_COMPARE_N` | Number of historical signal comparisons，`0` close（Default），`>0` enable | Optional |
| `ANALYSIS_DELAY` | Delay between individual stock analysis and broader market analysis（seconds），avoidAPICurrent limiting，Such as `10` | Optional |
| `SAVE_CONTEXT_SNAPSHOT` | Whether to save analysis history `context_snapshot`，Default `true`；set to `false` or use `--no-context-snapshot` Do not persist the entire context snapshot | Optional |
| `MERGE_EMAIL_NOTIFICATION` | Individual stocks and market review combined push（Default false），Reduce the number of emails、Reduce spam risk；with `SINGLE_STOCK_NOTIFY` mutually exclusive（Merger does not take effect in single-stock mode） | Optional |
| `MARKDOWN_TO_IMAGE_CHANNELS` | will Markdown Switch to a channel for sending pictures（separated by commas）：telegram,wechat,custom,email,slack；Single stock push needs to be configured at the same time and the image transfer tool must be installed. | Optional |
| `NOTIFICATION_REPORT_CHANNELS` | report routing channel（Single stock push、Poly Daily、Market review、Merge push, etc.）；Leave blank for all configured channels | Optional |
| `NOTIFICATION_ALERT_CHANNELS` | alert routing channel（EventMonitor Alarm）；Leave blank for all configured channels | Optional |
| `NOTIFICATION_SYSTEM_ERROR_CHANNELS` | system_error Reserve routing channels；There are currently no new automatic system error producers，Leave blank for all configured channels | Optional |
| `NOTIFICATION_DEDUP_TTL_SECONDS` | Notification to remove duplicates TTL seconds，`0` close；Same and stable deduplication key in TTL Only sent once within | Optional |
| `NOTIFICATION_COOLDOWN_SECONDS` | Notification cool down seconds，`0` close；same cooling key Limit frequency within window | Optional |
| `NOTIFICATION_QUIET_HOURS` | Notification silent period，Format `HH:MM-HH:MM`，Support across midnight；Leave blank to close | Optional |
| `NOTIFICATION_TIMEZONE` | Used during silent period IANA time zone，Such as `Asia/Shanghai`；Leave blank to follow `TZ` or system local time zone | Optional |
| `NOTIFICATION_MIN_SEVERITY` | Minimum notification level：`info`、`warning`、`error`、`critical`；Leave blank to maintain status quo | Optional |
| `NOTIFICATION_DAILY_DIGEST_ENABLED` | Daily summary reserve switch；Digests or persisted digest content are not currently sent | Optional |
| `MARKDOWN_TO_IMAGE_MAX_CHARS` | Images exceeding this length will not be forwarded，Avoid oversized images（Default 15000） | Optional |
| `MD2IMG_ENGINE` | Image transfer engine：`wkhtmltoimage`（Default，Need wkhtmltopdf）or `markdown-to-file`（emoji better，Need `npm i -g markdown-to-file`） | Optional |
| `PREFETCH_REALTIME_QUOTES` | set to `false` Real-time quote prefetching can be disabled，avoid efinance/akshare_em Whole market pull（Default true） | Optional |

> Compatibility Notes：`REPORT_SHOW_LLM_MODEL` Keep default `true` The original display semantics of，When closed, only the bottom model copy output is affected.。This configuration will not change provider/model/Base URL、LiteLLM routing、Model save、Migrate or clean up semantics；The fallback method is to restore or delete the variable，and set to `true`。

> Description：`REPORT_LANGUAGE` Only affects report text and Web Report page fixed copy；WebUI Page language（Navigation、Login page、sidebar、settings page、Common controls）Use independent state，Not linked to it。
> WebUI Language status saved in browser `localStorage` of `dsa.uiLanguage`，The startup sequence is：
> 1) clear choice（`localStorage.dsa.uiLanguage`，Only supports `zh`/`en`）
> 2) Browser language detection（`navigator.languages` / `navigator.language`，`zh-*` or `en-*`）
> 3) Default fallback `zh`。

#### Other configurations

| Secret Name | Description | Required |
|------------|------|:----:|
| `STOCK_LIST` | Optional stock code，Such as `600519,300750,002594,7203.T,005930.KS`；It is recommended to use English commas，Chinese comma、comma、semicolon、Spaces and newlines will be recognized and normalized to English commas | ✅ |
| `ANSPIRE_API_KEYS` | [Anspire AI Search](https://aisearch.anspire.cn/) Specially optimized for Chinese content；same Key Can be used to search with Anspire A low-level example of a large model gateway（Whether it is available depends on the console and account permissions.） | Recommended |
| `SERPAPI_API_KEYS` | [SerpAPI](https://serpapi.com/baidu-search-api?utm_source=github_daily_stock_analysis) Search engine results enhancement，Perfect for real-time financial news | Recommended |
| `TAVILY_API_KEYS` | [Tavily](https://tavily.com/) Search API（News search） | Optional |
| `BOCHA_API_KEYS` | [Bocha search](https://open.bocha.cn/) Web Search API（Chinese search optimization，supportAISummary，multiplekeyseparated by commas） | Optional |
| `BRAVE_API_KEYS` | [Brave Search](https://brave.com/search/api/) API（Privacy first，US stock optimization，multiplekeyseparated by commas） | Optional |
| `MINIMAX_API_KEYS` | [MiniMax](https://platform.minimax.io/) Coding Plan Web Search（Structured search results） | Optional |
| `SEARXNG_BASE_URLS` | SearXNG Self-built instance（No quotas，Need to be in settings.yml enable format: json）；If left blank, public instances will be automatically discovered by default. | Optional |
| `SEARXNG_PUBLIC_INSTANCES_ENABLED` | Is there `SEARXNG_BASE_URLS` When empty, automatically starts from `searx.space` Get public instance（Default `true`） | Optional |
| `TUSHARE_TOKEN` | [Tushare Pro](https://tushare.pro/weborder/#/login?reg=834638 ) Token | Optional |
| `TICKFLOW_API_KEY` | [TickFlow](https://tickflow.org) API Key；Optional，used for A stock day K、Real-time quotes、stock list/Enhanced name and market review；Automatic fallback in case of failure or insufficient permissions。 | Optional |
| `LONGBRIDGE_OAUTH_CLIENT_ID` | [Longbridge OpenAPI](https://open.longbridge.com/) OAuth client_id；Leave blank and none Legacy Access Token will be compatible with `LONGBRIDGE_APP_KEY` | Optional |
| `LONGBRIDGE_OAUTH_TOKEN_CACHE_B64` | OAuth token cached files base64 content，supply GitHub Actions / Docker Wait headless environmental restoration SDK token cache | Optional |
| `LONGBRIDGE_APP_KEY` | Longbridge Legacy App Key；None `LONGBRIDGE_ACCESS_TOKEN` can also be used as OAuth client_id Compatible with aliases | Optional |
| `LONGBRIDGE_APP_SECRET` | Longbridge App Secret | Optional |
| `LONGBRIDGE_ACCESS_TOKEN` | Longbridge Legacy Access Token（No OAuth access token） | Optional |
| `LONGBRIDGE_STATIC_INFO_TTL_SECONDS` | long bridge `static_info` In-process cache seconds（Default 86400，0=Do not cache） | Optional |
| `LONGBRIDGE_CONNECTION_COOLDOWN_SECONDS` | The number of cooling seconds after long bridge connection closing exception（Default 15；Temporarily skipped during the cool-down period Longbridge，Avoid frequent reconnections） | Optional |
| `LONGBRIDGE_HTTP_URL` | HTTP interface address（Default `https://openapi.longbridge.com`） | Optional |
| `LONGBRIDGE_QUOTE_WS_URL` | Quotes WebSocket address（Default `wss://openapi-quote.longbridge.com/v2`） | Optional |
| `LONGBRIDGE_TRADE_WS_URL` | transaction WebSocket address（Default `wss://openapi-trade.longbridge.com/v2`） | Optional |
| `LONGBRIDGE_REGION` | Coverage access point；SDK Will automatically select according to network，Default `hk`，If the judgment is incorrect, you can set（Such as `cn`、`hk`） | Optional |
| `LONGBRIDGE_ENABLE_OVERNIGHT` | Whether to enable night trading market `true` / `false`，Default `false` | Optional |
| `LONGBRIDGE_PUSH_CANDLESTICK_MODE` | K Line push mode：`realtime` or `confirmed`（Default `realtime`） | Optional |
| `LONGBRIDGE_PRINT_QUOTE_PACKAGES` | Whether to print a quote when connecting（Default if not set `false`；set to `1`/`true`/`yes` turn on） | Optional |
| `ENABLE_CHIP_DISTRIBUTION` | Enable chip distribution（Actions Default false；When you need chip data, Variables Set to true，The interface may be unstable） | Optional |

> **GitHub Actions：** Warehouse comes with `00-daily-analysis.yml` Already put `TUSHARE_TOKEN`、`TICKFLOW_API_KEY` / `TICKFLOW_*` and in the table above `LONGBRIDGE_*` Map to task environment。TickFlow of API Key It is recommended to put **Secrets**，priority、Reset and batch switches can be placed in **Variables** or **Secrets**。Longbridge OAuth The method requires a client_id（Priority `LONGBRIDGE_OAUTH_CLIENT_ID`；Leave blank and none Legacy Access Token used when `LONGBRIDGE_APP_KEY` Compatible），and put the machine `~/.longbridge/openapi/tokens/<client_id>` File base64 and then save it as Secret `LONGBRIDGE_OAUTH_TOKEN_CACHE_B64`；Legacy The method is still configurable `LONGBRIDGE_APP_KEY`、`LONGBRIDGE_APP_SECRET`、`LONGBRIDGE_ACCESS_TOKEN`。Optional access point variables（Such as `LONGBRIDGE_REGION`）Can be placed in **Variables** or **Secrets**。

> **Longbridge runtime behavior：** Will not instantiate when credentials are not configured Longbridge This is optional fetcher；If encountered when running `client is closed`、`context closed`、`connection closed` Waiting for connection closed exception，Will enter the cooling period（Default 15 seconds，Available `LONGBRIDGE_CONNECTION_COOLDOWN_SECONDS` adjust），U.S. stocks during the cooling-off period/Real-time and daily requests for Hong Kong stocks will be automatically skipped Longbridge，return YFinance / AkShare Wait for the link。

> Additional information
- TUSHARE_TOKEN，When this parameter is configured，But when you do not have the Hong Kong stock daily interface authority，There may also be situations where the Hong Kong stock data cannot be retrieved or is incorrect.，It has the same effect as the old version’s prompt that Hong Kong stocks are not supported.

#### ✅ Minimal configuration example

If you want to get started quickly，At least the following items need to be configured：

1. **AI model**：`ANSPIRE_API_KEYS`（one Key Enable both large models and search）、`AIHUBMIX_KEY`（[AIHubmix](https://aihubmix.com/?aff=CfMq)，one Key multiple models）、`GEMINI_API_KEY` or `OPENAI_API_KEY`
2. **notification channel**：Configure at least one，Such as `WECHAT_WEBHOOK_URL` or `EMAIL_SENDER` + `EMAIL_PASSWORD`
3. **stock list**：`STOCK_LIST`（Required）
4. **Search API**：`ANSPIRE_API_KEYS` or `SERPAPI_API_KEYS`（Recommended，Used for news and public opinion search）

> 💡 After configuring the above 4 items to start using！

### 3. Enable Actions

1. Go to your forked repository
2. Click the `Actions` tab at the top
3. If prompted, click `I understand my workflows, go ahead and enable them`

### 4. Manual Test

1. Go to the `Actions` tab
2. Select `Daily Stock Analysis` workflow on the left
3. Click the `Run workflow` button on the right
4. Select run mode
5. Click the green `Run workflow` to confirm

### 5. Done!

Default schedule: Every weekday at **18:00 (Beijing Time)** automatic execution.

---

## Complete Environment Variables List

### AI Model Configuration

> For full instructions see [LLM Configuration Guide](LLM_CONFIG_GUIDE.md)（Three-tier configuration、channel model、Vision、Agent、Troubleshooting）；Commonly used service provider defaults、Actions Variable comparison and error troubleshooting see [LLM Service Provider Configuration Guide](llm-providers.md)。
> Compatibility Notes（Issue #1306/#1391，Confirm by the way #1381）：The relevant changes in this section only reuse the existing historical write links to display the results of the large disk review.，No new addition API/API parameters、Web Stage results are displayed independently、Daily four-stage structured persistence or daily status table，Do not modify `provider` / `model` / `base_url` Runtime routing and default model behavior；#1381 Also only for backend runtime Reuse，No new configuration migration/clean up/writeback branch。If Issue #1381 of API/Web/Daily structured acceptance was not implemented simultaneously，Ben PR Should not be closed as a complete delivery，Need to wait for follow-up PR Continue to deliver。The fallback path is release rollback（Can be directly revert current commit，Or fallback link according to existing configuration）。Compatibility verification mainly uses existing constraint checks（`requirements.txt`：`litellm` version constraints）Regression testing with existing configuration：`tests/test_system_config_service.py`、`tests/test_system_config_api.py`、`tests/test_llm_channel_config.py`、`tests/test_market_review_runtime.py`；Official source reference：[LiteLLM OpenAI-compatible](https://docs.litellm.ai/docs/providers/openai_compatible)、[OpenAI Chat Completion API](https://platform.openai.com/docs/api-reference/chat)。
> #1391 Phase 2 The structured detection risk comes from `src/agent/factory.py` of `agent_max_steps` / `agent_orchestrator_timeout_s` int Safe and secure，Type compatibility enhancements belonging to the configuration reading side，Will not rewrite `litellm_model`、`agent_litellm_model`、`openai_base_url` or `LLM_*` routing status；Return can be reviewed `tests/test_agent_pipeline.py::TestAgentConfig::test_build_agent_executor_does_not_mutate_llm_route_config` with `tests/test_agent_pipeline.py::TestAgentConfig::test_build_agent_executor_multi_arch_does_not_mutate_llm_route_config`。When the configuration value is illegal（If not a number）time，`src.agent.factory` Will record warning and fall back to default，To facilitate troubleshooting and avoid misjudgment that the configuration has taken effect。
> #1815 Phase 3 Compatibility boundary description：This round only converges JP/KR with Market Light service boundaries，No new addition LLM provider/model/base_url Migration logic，Do not rewrite `.env` Main routing model persistence semantics。`MarketSymbol`、Alarm enumeration and snapshot `data_quality/limitations` Adjust the existing `.env` atom upsert Semantic write save configuration；Submitted keys that are not shown will not be cleared。
> This section only synchronizes the model/Channel configuration list，No additional external introduction provider / Base URL Compatibility convention；Compatible semantics with the current repository `requirements.txt` Subject to dependency constraints and related tests，The historical rollback path can be found in the above two documents.“rollback/restore”Description。

| variable name | Description | Default value | Required |
|--------|------|--------|:----:|
| `GENERATION_BACKEND` | Common analysis generation backend；support `litellm` or explicitly opt-in of `codex_cli` / `claude_code_cli` / `opencode_cli`（experimental/limited） | `litellm` | No |
| `OPENCODE_CLI_MODEL` | `GENERATION_BACKEND=opencode_cli` optionally passed to OpenCode `--model` model coverage；Leave blank to use local machine OpenCode Default model，Certification and model availability by native OpenCode Responsible for configuration | empty | No |
| `GENERATION_FALLBACK_BACKEND` | backend level fallback；Not configured default `litellm`，Null value disabled，self fallback parsed as no-op | `litellm` | No |
| `GENERATION_BACKEND_TIMEOUT_SECONDS` | Single generation backend Call timeout seconds，Mainly used locally CLI backend；scope `1-3600` | `300` | No |
| `GENERATION_BACKEND_MAX_OUTPUT_BYTES` | Single local CLI backend Diagnosis stdout/stderr Capture total cap with final response；`--output-last-message` Repeat printing to stdout The final response will not be counted twice；scope `1-33554432` | `1048576` | No |
| `GENERATION_BACKEND_MAX_CONCURRENCY` | generation backend Global concurrency limit；scope `1-16`，Do not change LiteLLM Router / `MAX_WORKERS` behavior | `1` | No |
| `LOCAL_CLI_BACKEND_MAX_CONCURRENCY` | local CLI backend Concurrency limit；scope `1-4`，Effective concurrency takes it with `GENERATION_BACKEND_MAX_CONCURRENCY` The smaller value of | `1` | No |
| `AGENT_GENERATION_BACKEND` | Agent Chat Generate backend；Web The settings page is only exposed `auto|litellm`，handwriting local CLI backend will return unsupported tool-calling Diagnosis | `auto` | No |
| `LITELLM_MODEL` | master model，Format `provider/model`（Such as `gemini/gemini-3.1-pro-preview`），Recommended to use first | - | No |
| `AGENT_LITELLM_MODEL` | Agent master model（Optional）；Leave blank to inherit from main model，None provider prefix press `openai/<model>` parse | - | No |
| `AGENT_CONTEXT_COMPRESSION_ENABLED` | Asking stocks visible conversation context compression switch；Off by default，Compress only when turned on `session_id` down user/assistant text history | `false` | No |
| `AGENT_CONTEXT_COMPRESSION_PROFILE` | Stock context compression strategy：`cost` / `balanced` / `long_context_raw_first` | `balanced` | No |
| `AGENT_CONTEXT_COMPRESSION_TRIGGER_TOKENS` | history token Trigger compression when the estimate exceeds this value；Leave blank to follow profile preset | - | No |
| `AGENT_CONTEXT_PROTECTED_TURNS` | most recent when compressed N User rounds and subsequent replies retain the original text；Leave blank to follow profile preset | - | No |
| `LITELLM_FALLBACK_MODELS` | alternative model，comma separated | - | No |
| `LLM_CHANNELS` | Channel name list（comma separated），cooperate `LLM_{NAME}_*` Use，See details [LLM Configuration Guide](LLM_CONFIG_GUIDE.md) | - | No |
| `LLM_HERMES_API_KEY` | Hermes reserved local HTTP generation of single API Key；Should only come from `.env`、runtime configuration or Secrets | - | Hermes Required when using |
| `LLM_HERMES_BASE_URL` | Hermes local loopback `/v1` address；Default `http://127.0.0.1:8642/v1`，Remote addresses are not supported | `http://127.0.0.1:8642/v1` | No |
| `LLM_HERMES_MODELS` | Hermes Original model list；Phase 3 Default `hermes-agent`，runtime route for `openai/hermes-agent`，Not supported Vision / stream / tools / Agent tools | `hermes-agent` | No |
| `LITELLM_CONFIG` | Advanced model routing YAML Configuration file path（Advanced） | - | No |
| `LLM_PROMPT_CACHE_TELEMETRY_ENABLED` | Provider prompt cache usage / diagnostics Telemetry；Not in control provider implicit cache | `true` | No |
| `LLM_PROMPT_CACHE_HINTS_ENABLED` | Whether the main analysis path actively sends verified provider-specific prompt cache hints；Agent The path is currently only logged diagnostics，Not proactively posting hints；Off by default | `false` | No |
| `LLM_PROMPT_CACHE_DIAGNOSTICS_LEVEL` | Prompt cache diagnostic level：`off` / `basic` / `debug`；basic/debug only in debug Desensitization diagnostics available in logs and test observables，inaction publicity Usage API Or normal settings page output | `off` | No |
| `LLM_USAGE_HMAC_SECRET` | LLM Usage telemetry message HMAC key；Automatically uses the local key file in the data directory when left empty | - | No |
| `LLM_USAGE_HMAC_KEY_VERSION` | LLM Usage telemetry HMAC Key version label，Synchronous updates when keys are rotated | `local-v1` | No |
| `ANSPIRE_API_KEYS` | [Anspire](https://open.anspire.cn/?share_code=QFBC0FYC) API Key，one Key Enable both large model gateway and search | - | Optional |
| `AIHUBMIX_KEY` | [AIHubmix](https://aihubmix.com/?aff=CfMq) API Key，one Key Switch to use the full series model，No additional configuration required Base URL | - | Optional |
| `GEMINI_API_KEY` | Google Gemini API Key | - | Optional |
| `GEMINI_MODEL` | Main model name（legacy，`LITELLM_MODEL` Priority） | `gemini-3.1-pro-preview` | No |
| `GEMINI_MODEL_FALLBACK` | alternative model（legacy） | `gemini-3-flash-preview` | No |
| `OPENAI_API_KEY` | OpenAI Compatible API Key | - | Optional |
| `OPENAI_BASE_URL` | OpenAI Compatible API address | - | Optional |
| `OLLAMA_API_BASE` | Ollama local service address（Such as `http://localhost:11434`），See details [LLM Configuration Guide](LLM_CONFIG_GUIDE.md) | - | Optional |
| `OPENAI_MODEL` | OpenAI Model name（legacy，AIHubmix The user can fill in the following `gemini-3.1-pro-preview`、`gpt-5.5`） | `gpt-5.5` | Optional |
| `ANTHROPIC_API_KEY` | Anthropic Claude API Key | - | Optional |
| `ANTHROPIC_MODEL` | Claude Model name | `claude-sonnet-4-6` | Optional |
| `ANTHROPIC_TEMPERATURE` | Claude Temperature parameters（0.0-1.0） | `0.7` | Optional |
| `ANTHROPIC_MAX_TOKENS` | Claude response max token number | `8192` | Optional |

> GitHub Actions Description：Warehouse comes with `00-daily-analysis.yml` in `GENERATION_FALLBACK_BACKEND` Used explicitly when not configured `litellm`，avoid unset Secret/Variable was exported as null and unexpectedly disabled backend fallback。To be in Actions disabled in backend fallback，please change fallback set to primary backend，let resolver go self no-op。

> Generate backend status description：Web The quick check on the settings page only reads saved configurations、Draft not saved，and check local CLI Is the executable file visible?，Do not initiate a real model request；JSON Smoke testing is a separate explicit operation，Will use server side fixed JSON prompt words and schema Make a real request。`health_status` with `last_error_code/message` Only indicates the current status calculation or smoke test results.，Not a historical lasting health state。

> *Note：`ANSPIRE_API_KEYS`、`AIHUBMIX_KEY`、`GEMINI_API_KEY`、`ANTHROPIC_API_KEY`、`OPENAI_API_KEY` or `OLLAMA_API_BASE` Configure at least one。`ANSPIRE_API_KEYS` with `AIHUBMIX_KEY` No configuration required `OPENAI_BASE_URL`，System automatic adaptation。

> Ask about stocks single-agent The path will be in the background as DeepSeek V4 thinking + tool-call Save recent 3 Article provider trace，and play back in original time sequence `reasoning_content` / tool result；This capability does not add new configuration items，Do not enter Web history API，Claude extended thinking Only covers offline plumbing，multi-agent trace Injection reserved for subsequent enhancement。

### Notification channel configuration

More notification configuration baselines、Diagnosis and deployment scenario descriptions see [Notification topic document](notifications.md)。

| variable name | Description | Required |
|--------|------|:----:|
| `WECHAT_WEBHOOK_URL` | Enterprise WeChat robot Webhook URL | Optional |
| `FEISHU_WEBHOOK_URL` | Feishu Robot Webhook URL | Optional |
| `FEISHU_WEBHOOK_SECRET` | Feishu Robot Signature Key（Only enabled in robot security settings“Signature verification”Fill in when） | Optional |
| `FEISHU_WEBHOOK_KEYWORD` | Feishu robot keywords（Only enabled in robot security settings“keywords”Fill in when） | Optional |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | Optional |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | Optional |
| `TELEGRAM_MESSAGE_THREAD_ID` | Telegram Topic ID | Optional |
| `DISCORD_WEBHOOK_URL` | Discord Webhook URL | Optional |
| `DISCORD_BOT_TOKEN` | Discord Bot Token（with Webhook Choose one） | Optional |
| `DISCORD_MAIN_CHANNEL_ID` | Discord Channel ID（Use Bot when needed） | Optional |
| `DISCORD_INTERACTIONS_PUBLIC_KEY` | Discord Public Key（Inbound only Interaction/Webhook Required when calling back for signature verification） | Optional |
| `DISCORD_MAX_WORDS` | Discord single message content upper limit（Default 2000；The run time will not exceed Discord 2000 character limit，Long reports will be automatically fragmented and processed 429 Current limiting and limited retry） | Optional |
| `SLACK_BOT_TOKEN` | Slack Bot Token（Recommended，Support image upload；When configured at the same time, it takes precedence over Webhook） | Optional |
| `SLACK_CHANNEL_ID` | Slack Channel ID（Use Bot when needed） | Optional |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL（text only，Pictures not supported） | Optional |
| `EMAIL_SENDER` | Sender's email | Optional |
| `EMAIL_PASSWORD` | Email authorization code（Non-login password） | Optional |
| `EMAIL_RECEIVERS` | Recipient email（comma separated，Leave blank and send to yourself） | Optional |
| `EMAIL_SENDER_NAME` | Sender display name | Optional |
| `STOCK_GROUP_N` / `EMAIL_GROUP_N` | Mail group routing（Issue #268）：`STOCK_GROUP_N` should be `STOCK_LIST` subset，Only affects email recipients，No changes to the scope of analysis or other notification channels | Optional |
| `CUSTOM_WEBHOOK_URLS` | Customize Webhook（comma separated） | Optional |
| `CUSTOM_WEBHOOK_BEARER_TOKEN` | Customize Webhook Bearer Token | Optional |
| `WEBHOOK_VERIFY_SSL` | Read the configuration webhook-style HTTPS Notification request certificate verification（Default true）。set to false Can support self-signing。warning：Closure poses serious security risk | Optional |
| `PUSHOVER_USER_KEY` | Pushover User Key | Optional |
| `PUSHOVER_API_TOKEN` | Pushover API Token | Optional |
| `NTFY_URL` | ntfy complete topic endpoint，must contain topic path，For example `https://ntfy.sh/my-topic` | Optional |
| `NTFY_TOKEN` | ntfy Bearer Token（Optional） | Optional |
| `GOTIFY_URL` | Gotify server base URL，Not included `/message` | Optional |
| `GOTIFY_TOKEN` | Gotify application token，Pass `X-Gotify-Key` Header send | Optional |
| `PUSHPLUS_TOKEN` | PushPlus Token（Domestic push service） | Optional |
| `SERVERCHAN3_SENDKEY` | ServerSauce³ Sendkey | Optional |
| `ASTRBOT_URL` | AstrBot Webhook URL | Optional |
| `ASTRBOT_TOKEN` | AstrBot Bearer Token（Optional） | Optional |
| `NOTIFICATION_REPORT_CHANNELS` | report routing channel，comma separated；allowed values：wechat,feishu,telegram,email,pushover,ntfy,gotify,pushplus,serverchan3,custom,discord,slack,astrbot | Optional |
| `NOTIFICATION_ALERT_CHANNELS` | alert routing channel，comma separated；Leave blank to maintain omnichannel | Optional |
| `NOTIFICATION_SYSTEM_ERROR_CHANNELS` | system_error Reserve routing channels，comma separated；Leave blank to maintain omnichannel | Optional |
| `NOTIFICATION_DEDUP_TTL_SECONDS` | Notification to remove duplicates TTL seconds，`0` close | Optional |
| `NOTIFICATION_COOLDOWN_SECONDS` | Notification cool down seconds，`0` close | Optional |
| `NOTIFICATION_QUIET_HOURS` | silent period，Format `HH:MM-HH:MM`，Support across midnight | Optional |
| `NOTIFICATION_TIMEZONE` | Quiet period time zone，Such as `Asia/Shanghai`；Leave blank to follow `TZ` or system local time zone | Optional |
| `NOTIFICATION_MIN_SEVERITY` | Minimum notification level：info, warning, error, critical；Leave blank to maintain status quo | Optional |
| `NOTIFICATION_DAILY_DIGEST_ENABLED` | Daily summary reserve switch；Digests are not currently being sent | Optional |

> Description：Default `00-daily-analysis.yml` GitHub Actions workflow Only map fixed variable names，Any numbers will not be automatically imported `STOCK_GROUP_N` / `EMAIL_GROUP_N`。Therefore, group mailboxes are currently only available locally `.env`、Docker Or other running environments that have explicitly injected these environment variables to take effect；If you want to be in your own GitHub Actions used in，Need to be in workflow of job `env:` group-by-group explicit mapping in。

#### Feishu Cloud Document Configuration（Optional，Fix message truncation issue）

| variable name | Description | Required |
|--------|------|:----:|
| `FEISHU_APP_ID` | Feishu application ID | Optional |
| `FEISHU_APP_SECRET` | Feishu application Secret | Optional |
| `FEISHU_FOLDER_TOKEN` | Feishu cloud disk folder Token | Optional |
| `FEISHU_SEND_AS_FILE` | Feishu App Bot Send report as file（Default `false`） | Optional |

> Feishu Cloud Document Configuration Steps：
> 1. in [Feishu Developer Backend](https://open.feishu.cn/app) Create app
> 2. Configuration GitHub Secrets
> 3. Create a group and add app bots
> 4. Add a group as a collaborator in the cloud disk folder（Manageable permissions）
>
> Description：`FEISHU_APP_ID` / `FEISHU_APP_SECRET` For Feishu app、cloud document or Stream Bot mode，The group will not be enabled directly Webhook push。When you just want to simply receive group notifications，Please configure it first `FEISHU_WEBHOOK_URL`。
>
> supplement：If configured at the same time `FEISHU_APP_ID`、`FEISHU_APP_SECRET` and `FEISHU_CHAT_ID`，You can enable Feishu App Bot Proactive notification channels，No need Webhook You can take the initiative to specify chat or user push；`FEISHU_RECEIVE_ID_TYPE` Default `chat_id`，When chatting privately, change it to `open_id`。The way to take Feishu OpenAPI Bot session，With the group Webhook are two independent links。

### Search service configuration

| variable name | Description | Required |
|--------|------|:----:|
| `ANSPIRE_API_KEYS` | Anspire Open API Key（Configuration examples that can be used to search for scenes shared with large model gateways；Availability depends on account permissions and gateway visibility，Can effectively enhance A Stock analysis effect） | Recommended |
| `SERPAPI_API_KEYS` | SerpAPI Search engine results enhancement，Perfect for real-time financial news | Recommended |
| `TAVILY_API_KEYS` | Tavily Search API Key | Optional |
| `BOCHA_API_KEYS` | Bocha search API Key（Chinese optimization） | Optional |
| `BRAVE_API_KEYS` | Brave Search API Key（US stock optimization） | Optional |
| `MINIMAX_API_KEYS` | MiniMax Coding Plan Web Search（Structured search results） | Optional |
| `SOCIAL_SENTIMENT_API_KEY` | Stock Sentiment API Key（Reddit / X / Polymarket，Optional） | Optional |
| `SOCIAL_SENTIMENT_API_URL` | Stock Sentiment API address（Default `https://api.adanos.org`） | Optional |
| `SEARXNG_BASE_URLS` | SearXNG Self-built instance（No quotas，Need to be in settings.yml enable format: json）；If left blank, public instances will be automatically discovered by default. | Optional |
| `SEARXNG_PUBLIC_INSTANCES_ENABLED` | Is there `SEARXNG_BASE_URLS` When empty, automatically starts from `searx.space` Get public instance（Default `true`） | Optional |
| `NEWS_STRATEGY_PROFILE` | News strategy window position：`ultra_short`(1day)/`short`(3day)/`medium`(7day)/`long`(30day)；Actual window fetch and `NEWS_MAX_AGE_DAYS` the minimum value of | Default `short` |
| `NEWS_MAX_AGE_DAYS` | News maximum timeliness（day），Limit results to the near future when searching | Default `3` |
| `BIAS_THRESHOLD` | Deviation rate threshold（%），Do not chase after exceeding the prompt；Strong trend stocks automatically relax to 1.5 times | Default `5.0` |

> behavioral description：Search service and social public opinion service are optional enhanced links.。When any service fails to initialize，The system will record warning and downgrade to skip the service，Only affects the corresponding link，Will not block the main technical link and main task flow。

### News retrieval explainable ranking（Issue #1356）

`search_stock_news` Calculated for each candidate news「Interpretable correlation」and landed as 3 class label：

- `direct_company_news`：hit target code、Company name（Including official/Exchange source weighting）；
- `sector_related_news`：Hit industry sector semantics；
- `macro_market_news`：Macro when the target subject is missed/Market context news。

The sorting strategy is：Prioritize by category first（direct > sector > macro）sort，Press language preference again（Chinese first）Sort by score，Therefore, when there is news with a clear target hit in the same time window, it will be displayed first.。

After sorting, a layer of domain name-independent admission filtering will be performed.：obvious download/Installation package/App rating page、adult/Spam pages for prostitution services will be removed；When there is already a direct target or industry with scores in the same batch/Market candidate，`score=0` The background fill item will not go in `news_context`、Agent Tool output or historical intelligence cache。This rule does not have a built-in blacklist of specific websites，Avoid relying on exhaustive domain name maintenance。

Debug entry：

- Each return will be retained `relevance_score` / `relevance_category` / `relevance_reasons` metadata，eventually `to_text()` There will be correspondence with the intelligence context「Relevance」Description；
- The search link log will output `[news relevance]` Statistics，It is easier to review why this batch was triggered. direct/sector/macro layered。

Compatibility and rollback instructions：This change does not add new/Modify model、provider、Base URL、LiteLLM route、Configure cleanup or writeback logic；If an abnormality occurs，The old sorting behavior can only be restored by rolling back this commit，Does not involve historical configuration migration。

### Data source configuration

| variable name | Description | Default value | Required |
|--------|------|--------|:----:|
| `TUSHARE_TOKEN` | Tushare Pro Token | - | Optional |
| `TICKFLOW_API_KEY` | TickFlow API Key；Optional，used for A stock day K、Real-time quotes、stock list/Enhanced name and market review；Automatic fallback in case of failure or insufficient permissions。 | - | Optional |
| `TICKFLOW_PRIORITY` | TickFlow day K Data source priority；The lower the number, the sooner you try，Default `2`；Not configured API Key Not enabled when；Does not affect real-time market conditions，The real-time market sequence is provided by `REALTIME_SOURCE_PRIORITY` control。 | `2` | Optional |
| `TICKFLOW_KLINE_ADJUST` | TickFlow day K Restoration mode：`none`、`forward`、`backward`、`forward_additive`、`backward_additive`。 | `none` | Optional |
| `TICKFLOW_BATCH_DAILY_ENABLED` | Whether to enable TickFlow batch day K prefetch；Insufficient permissions will cache failure status for a short period of time，and continue with the regular rollback。 | `true` | Optional |
| `TICKFLOW_BATCH_SIZE` | TickFlow day K The maximum number of bids in a single batch for real-time market quotation batch requests。 | `100` | Optional |
| `LONGBRIDGE_OAUTH_CLIENT_ID` | Longbridge OAuth client_id；Leave blank and none Legacy Access Token will be compatible with `LONGBRIDGE_APP_KEY` | - | Optional |
| `LONGBRIDGE_OAUTH_TOKEN_CACHE_B64` | OAuth token cached files base64 content，supply GitHub Actions / Docker Wait headless Environmental use | - | Optional |
| `LONGBRIDGE_APP_KEY` | Longbridge Legacy App Key；None `LONGBRIDGE_ACCESS_TOKEN` can also be used as OAuth client_id Compatible with aliases | - | Optional |
| `LONGBRIDGE_APP_SECRET` | Longbridge App Secret | - | Optional |
| `LONGBRIDGE_ACCESS_TOKEN` | Longbridge Legacy Access Token（No OAuth access token） | - | Optional |
| `LONGBRIDGE_*`（Optional） | See official [environment variables](https://open.longbridge.com/zh-CN/docs/getting-started#environment variables)；Also `LONGBRIDGE_STATIC_INFO_TTL_SECONDS` with `LONGBRIDGE_CONNECTION_COOLDOWN_SECONDS` | - | Optional |
| `ENABLE_REALTIME_QUOTE` | Enable real-time quotes（Use historical closing price analysis after closing） | `true` | Optional |
| `ENABLE_REALTIME_TECHNICAL_INDICATORS` | Live technical intraday：Use real-time price calculation when enabled MA5/MA10/MA20 Arrange with multiple heads（Issue #234）；If closed, use yesterday’s closing price | `true` | Optional |
| `ENABLE_CHIP_DISTRIBUTION` | Enable chip distribution analysis（The interface is unstable，Cloud deployment is recommended to be closed）。GitHub Actions Users need to be in Repository Variables Medium settings `ENABLE_CHIP_DISTRIBUTION=true` can be enabled；workflow Off by default。 | `true` | Optional |
| `ENABLE_EASTMONEY_PATCH` | Dongcai interface patch：Dongcai interface frequently fails（Such as RemoteDisconnected、connection closed）It is recommended to set it to `true`，Inject NID Tokens and Random User-Agent To reduce the probability of being limited | `false` | Optional |
| `REALTIME_SOURCE_PRIORITY` | Real-time market source priority，comma separated，For example `tencent,akshare_sina,efinance,akshare_em`；Need to be explicitly added `tickflow` will use TickFlow Real-time quotes。 | see `.env.example` | Optional |
| `ENABLE_FUNDAMENTAL_PIPELINE` | Fundamental Aggregation Master Switch；Return only when closed `not_supported` block，Do not change the original analysis link | `true` | Optional |
| `FUNDAMENTAL_STAGE_TIMEOUT_SECONDS` | Total delay budget in fundamental stage（seconds） | `8.0` | Optional |
| `FUNDAMENTAL_FETCH_TIMEOUT_SECONDS` | Single capability resource call timeout（seconds） | `3.0` | Optional |
| `FUNDAMENTAL_RETRY_MAX` | Fundamental ability retries（including first time） | `1` | Optional |
| `FUNDAMENTAL_CACHE_TTL_SECONDS` | Fundamental Aggregation Cache TTL（seconds），Short cache mitigates duplicate pulls | `120` | Optional |
| `FUNDAMENTAL_CACHE_MAX_ENTRIES` | Maximum number of entries in the fundamental cache（TTL Eliminate within time） | `256` | Optional |

> behavioral description：
> - A shares：press `valuation/growth/earnings/institution/capital_flow/dragon_tiger/boards` Aggregation ability returns；
> - ETF：Return available items，Missing abilities are marked as `not_supported`，The overall process does not affect the original process；
> - US stocks/Hong Kong stocks：Pass yfinance Adapter returns `valuation/growth/earnings/belong_boards`（Source `info.sector`/`industry`），`institution/capital_flow/dragon_tiger/boards` There is no corresponding data source yet and it is still marked. `not_supported`；yfinance When the field is unavailable or missing, the entire `not_supported`，Still walking fail-open；
> - Japanese stocks/Korean stocks：Currently only going Yfinance Basic path to obtain daily and real-time quotes；`institution`、`capital_flow`、`dragon_tiger`、`boards` Waiting for dependencies A Stock exclusive source/The capabilities of the offshore full version will be downgraded to `not_supported`（See details [Market Support and Boundaries](market-support.md)）；
> - Taiwan stocks：in US stocks/Hong Kong stocks offshore outside base path，`institution` The block additionally displays the original excess net trading amount of the three major legal persons.（TWSE T86 / TPEx，Enabled by default、fail-open，Maintained when data cannot be retrieved `not_supported`）；`capital_flow`、`dragon_tiger`、`boards` still `not_supported`；
> - Any abnormality goes fail-open，Only log errors，Does not affect technical aspects/News/Chip main link。
> - Configuration `TICKFLOW_API_KEY` after，TickFlow will be optional A stock day K Data source and disk review enhanced source instantiation；`TICKFLOW_PRIORITY` Only affects day K/Universal data source fallback chain。Real-time market priority is determined by `REALTIME_SOURCE_PRIORITY` Individual control，Only explicitly include `tickflow` Will be used only when TickFlow Real-time quotes。`REALTIME_SOURCE_PRIORITY` Ranked in the middle `tickflow` The previous data sources will be tried first。
> - TickFlow day K Default `TICKFLOW_KLINE_ADJUST=none`；daily line `volume` Convert from hands to shares，`amount` Keep the meta caliber。
> - TickFlow day K Range requests will be passed in explicitly `start_time` / `end_time` / `count`；official quickstart Explicitly state that time range queries are still subject to `count` Limit。If the return is not empty but the number of rows is full `count` And the first returned transaction date is later than the request starting transaction date，The system will determine it as suspected truncation，Do not write to cache and let manager Continue to roll back。
> - During batch analysis，`prefetch_daily_klines()` Will be stock by stock `get_daily_data()` Warm up in-process cache before，Do not change the external calling path。
> - TickFlow Capabilities are stratified by package permissions：Limited rights packages can still use the main index query；support `CN_Equity_A` Only the package of the target pool query will be enabled. TickFlow market statistics。
> - TickFlow official quickstart provided `quotes.get(universes=["CN_Equity_A"])` Usage，but different API Key You may not have the corresponding permissions；batch day K、Capabilities such as depth and finance are also based on authority fail-open。
> - TickFlow actually returned `change_pct` / `amplitude` is a proportional value；The system has uniformly converted it into a percentage value at the access layer.，Ensure semantic consistency with existing data source fields。
> - A The stock market review report adopts an after-hours workbench structure：Fixed including disk signal、Index details、plate Top table、Market clues in the past three days、Tomorrow’s trading plan and risk warning；The board signal is based on `66/100（warmer，Can attack）` This type of plain text score expression，Avoid inconsistent display of color block progress bars on different terminals；The market clues for the past three days are only listed in titles.、Sources and links，Don't show search snippets anymore；If some data sources are missing，Then keep the available blocks and demote them in the corresponding position.。
> - field contract：
>   - `fundamental_context.belong_boards` = List of related sectors of individual stocks；A stocks from AkShare Writing section list，US stocks/Hong Kong stocks from yfinance `info.sector` / `info.industry` write，When there is no data, it is `[]`；
>   - `fundamental_context.boards.data` = `sector_rankings`（Sector rise and fall list，structure `{top, bottom}`，HK/US Not currently available）；
>   - `fundamental_context.concept_boards.data` = `concept_rankings`（concept/Topic rise and fall list，structure `{top, bottom}`，Currently only A Shares provided；When unavailable fail-open Empty or missing）；
>   - `fundamental_context.earnings.data.financial_report` = financial report summary（reporting period、revenue、Net profit attributable to parent company、operating cash flow、ROE，and `currency` Source `info.financialCurrency`，HK ADR Commonly seen as CNY）；
>   - `fundamental_context.earnings.data.dividend` = Dividend index（Cash dividends before tax only，Contains `events`、`ttm_cash_dividend_per_share`、`ttm_dividend_yield_pct`、`currency`）。`currency` Read independently from `info.currency`，with `financial_report.currency` may be different（HK ADR financial report CNY、dividend HKD）；TTM yield Default press `ttm_cash / latest_price * 100`（Same currency）Instant recalculation，only in TTM cash or latest price Fallback to when missing yfinance `trailingAnnualDividendYield` or `dividendYield`；
>   - `get_stock_info.belong_boards` = List of sectors to which individual stocks belong；
>   - `get_stock_info.boards` Aliases for compatibility，value with `belong_boards` Same（Will only be considered for removal in major versions in the future）；
>   - `get_stock_info.sector_rankings` with `fundamental_context.boards.data` Be consistent。
>   - `AnalysisReport.details.belong_boards` = List of associated sections in structured report details；
>   - `AnalysisReport.details.sector_rankings` = Sector gain and loss lists in structured report details（Used for front-end section linkage display）。
>   - `AnalysisReport.details.concept_rankings` = Concepts in Structured Report Details/Topic rise and fall list（Used for front-end correlation plate signal matching，and notification forms differentiate industries by type/concept）。
> - The order of data sources used in the sector rise and fall list：and global priority consistent。
> - The timeout control is `best-effort` soft timeout：The stage will be quickly degraded and continued execution according to the budget.，But there is no guarantee that hard interrupts the underlying three-party calls。
> - `FUNDAMENTAL_STAGE_TIMEOUT_SECONDS=8.0` Indicates the target budget for the new fundamental stage，Not strictly hard SLA；Windows、Docker Or when the free data source is limited, you can continue to increase it to `12-15s`。
> - To be hard SLA，Please upgrade to child process isolation execution in subsequent versions and force termination after timeout.。

### Other configurations

| variable name | Description | Default value |
|--------|------|--------|
| `STOCK_LIST` | Optional stock code（comma separated） | - |
| `ADMIN_AUTH_ENABLED` | Web Login：set to `true` Enable password protection；Set an initial password on the webpage when visiting for the first time，Available at「System settings > Change password」Modify；Forgot password execution `python -m src.auth reset_password`。Web of `.env` Backup import and export are only available after turning on this switch.（Desktop is not subject to this restriction）。 | `false` |
| `TRUST_X_FORWARDED_FOR` | When deploying a single-layer trusted reverse proxy, set it to `true`，take `X-Forwarded-For` rightmost value as real client IP（Used for login current limiting, etc.）；Maintain when directly connected to the public network `false` Anti-counterfeiting。multi-level agency/CDN Current limiting in scenarios key May degenerate into an edge proxy IP，Requires additional evaluation | `false` |
| `MAX_WORKERS` | Number of concurrent threads | `3` |
| `MARKET_REVIEW_ENABLED` | Enable market review | `true` |
| `DAILY_MARKET_CONTEXT_ENABLED` | Inject a summary of the day's market environment into individual stock analysis Prompt，and at high risk/Aggressive buying recommendations softened in ebbing environment；Enabled by default，set to `false` You can still run a large disk recovery later | `true` |
| `MARKET_REVIEW_REGION` | Market review area：cn(Ashares)、hk(Hong Kong stocks)、us(US stocks)、jp(Japanese stocks)、kr(Korean stocks)、both(five markets)，us/jp/kr Suitable for users who only focus on a single area | `cn` |
| `MARKET_REVIEW_COLOR_SCHEME` | The color of the market review index's rise and fall：`green_up`=Green rises and red falls（Default），`red_up`=Red rises and green falls | `green_up` |
| `TRADING_DAY_CHECK_ENABLED` | Trading Day Check：Default `true`，Skip execution on non-trading days；set to `false` or use `--force-run` enforceable（Issue #373） | `true` |
| `SCHEDULE_ENABLED` | Enable scheduled tasks | `false` |
| `SCHEDULE_TIME` | scheduled execution time | `18:00` |
| `SCHEDULE_TIMES` | Multiple scheduled execution times，comma separated；Used when empty `SCHEDULE_TIME` | empty |
| `LOG_DIR` | Log directory | `./logs` |
| `SAVE_CONTEXT_SNAPSHOT` | Save analysis history `context_snapshot`；set to `false` Current history is not saved enhanced_context、market_phase_summary、AnalysisContextPack overview or diagnostic snapshot，but does not close the current Prompt Hypoallergenic summary | `true` |

---

## Docker Deployment

Dockerfile uses multi-stage builds; the frontend is automatically packaged and built into `static/` during image build.
To override static assets, mount local `static/` to container `/app/static`.
Running `server` containers default to reusing pre-built artifacts in `/app/static` without requiring `apps/dsa-web` source directory or runtime `npm` in the container; if WebUI cannot open, first confirm whether `/app/static/index.html` exists.

Current official image release addresses:

- GHCR: `ghcr.io/zhulinsen/daily_stock_analysis:<tag>`
- Docker Hub: `<DOCKERHUB_USERNAME>/daily_stock_analysis:<tag>` (determined by publisher's `DOCKERHUB_USERNAME` secret; official release is `zhulinsen/daily_stock_analysis`)

### Quick Start

```bash
# 1. Clone repository
git clone https://github.com/ZhuLinsen/daily_stock_analysis.git
cd daily_stock_analysis

# 2. Configure environment variables
cp .env.example .env
vim .env  # fill in API Key and configure

# 3. Start container
docker-compose -f ./docker/docker-compose.yml up -d server     # Web service model（Recommended，provide API with WebUI）
docker-compose -f ./docker/docker-compose.yml up -d analyzer   # Scheduled task mode
docker-compose -f ./docker/docker-compose.yml up -d            # Activate both modes at the same time

# 4. visit WebUI
# http://localhost:8000

# 5. View log
docker-compose -f ./docker/docker-compose.yml logs -f server
```

Default Compose Set for each service `limits.memory: 1G`、`reservations.memory: 512M`。`512M` Recommended for lightweight use only Web/API、single strand、Low concurrency scenario，and will `MAX_WORKERS=1`；General complete analysis recommendations `1G`，start simultaneously `server + analyzer`、Many stocks、Market review、news extension、picture report or AlphaSift Suggestions `2G+`。If you can only use `512M`，Please avoid starting two services at the same time and reduce heavy functions。

### Directly pull the official image and run it

If you do not plan to keep the source code on the target machine，You can directly pull the official image：

```bash
# Web/API mode
docker pull zhulinsen/daily_stock_analysis:latest
docker run -d \
  --name dsa-server \
  --env-file .env \
  -p 8000:8000 \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/logs:/app/logs" \
  -v "$(pwd)/reports:/app/reports" \
  zhulinsen/daily_stock_analysis:latest \
  python main.py --serve-only --host 0.0.0.0 --port 8000

# Scheduled task mode
docker run -d \
  --name dsa-analyzer \
  --env-file .env \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/logs:/app/logs" \
  -v "$(pwd)/reports:/app/reports" \
  zhulinsen/daily_stock_analysis:latest
```

If you need a fixed version or easy rollback，please change `latest` Replace with specific version tag，For example `v3.13.0`。

### Operating mode description

| command | Description | port |
|------|------|------|
| `docker-compose -f ./docker/docker-compose.yml up -d server` | Web service model，provide API with WebUI | 8000 |
| `docker-compose -f ./docker/docker-compose.yml up -d analyzer` | Scheduled task mode，Automatically executed daily | - |
| `docker-compose -f ./docker/docker-compose.yml up -d` | Activate both modes at the same time | 8000 |

### Docker Compose Configuration

`docker-compose.yml` Use YAML Anchor reuse configuration：

```yaml
version: '3.8'

x-common: &common
  build:
    context: ..
    dockerfile: docker/Dockerfile
  restart: unless-stopped
  env_file:
    - ../.env
  environment:
    - TZ=Asia/Shanghai
  volumes:
    - ../data:/app/data
    - ../logs:/app/logs
    - ../reports:/app/reports
    - ../strategies:/app/strategies:ro
  deploy:
    resources:
      limits:
        memory: 1G
      reservations:
        memory: 512M

services:
  # Scheduled task mode
  analyzer:
    <<: *common
    container_name: stock-analyzer

  # FastAPI mode
  server:
    <<: *common
    container_name: stock-server
    command: ["python", "main.py", "--serve-only", "--host", "0.0.0.0", "--port", "${API_PORT:-8000}"]
    ports:
      - "${API_PORT:-8000}:${API_PORT:-8000}"
```

### `.env` Instructions for mapping with data directories

Whatever you use `docker run` Still Compose，Both need to distinguish between startup environment variable injection and runtime file writing.：

- Environment variable injection：`--env-file .env` or Compose of `env_file`
  function：put `.env` The key values in are passed in as environment variables when the container is started. Python process。
- Runtime configuration writing：Don't put the host machine `.env` as single file bind mount Cover the container `.env` path。Docker Will mount the single file target as mount point，When saving the configuration `os.replace()` Atomic updates may fail and report `Device or resource busy`，Rollback writes may also be restricted by permissions。

Default Compose and `docker run` Example only uses `env_file` / `--env-file` Inject startup configuration，No longer the host `.env` Mount a single file into the container。WebUI The settings page will be active in the current `.env` When the file lacks certain keys, the environment variable with the same name injected by startup is displayed as a cover-up.，avoid Docker User mistakenly believes that the configuration is not read at all；But“Export `.env`”Still only exports the contents of the currently active profile。

WebUI The runtime configuration saved in is written to the internal configuration file of the container by default.，Not equivalent to writing back to the host `.env`；After deleting or rebuilding the container, it is still injected at startup. `.env` Subject to。If you need to persist the runtime configuration，Please put the write target into a writable data volume（For example via `ENV_FILE=/app/data/runtime.env` point to `data` volume files in），Do not use `.env` single file bind mount。Note：If at startup `env_file`、`--env-file`、`docker run -e` or Compose `environment:` The old value with the same name is still retained in，These process environment variables may still overwrite the saved values in the runtime file when the container is restarted.；to let WebUI Saved value takes over，Please update or remove the overlay with the same name in the startup environment。

It is recommended to map these directories at the same time：

- `./data:/app/data`：database、Caching and runtime data
- `./logs:/app/logs`：Log output
- `./reports:/app/reports`：Generated analysis report
- `./strategies:/app/strategies:ro`：Custom strategy YAML（read-only mount）

official Docker The image is automatically created and repaired when it starts `/app/data`、`/app/logs`、`/app/reports` Mount directory permissions，Then reduce the weight to non- root User `dsa`（UID/GID `1000:1000`）Run application。Ordinary Docker / Compose No manual deployment required `chown` or `chmod` Host directory。

if you pass `--user` or Compose `user:` A different running user is specified，Or use read-only mount、rootless Docker、NFS etc. restrictions `chown` storage environment，Automatic repair may not take effect。At this time, please make sure that the user actually runs the `data`、`logs`、`reports` Have write permission，Or use a writable volume instead。

If you need to override built-in static resources，You can also mount additional：

- `./static:/app/static:ro`

### Common commands

```bash
# View running status
docker-compose -f ./docker/docker-compose.yml ps

# View log
docker-compose -f ./docker/docker-compose.yml logs -f server

# Stop service
docker-compose -f ./docker/docker-compose.yml down

# Rebuild image（After code update）
docker-compose -f ./docker/docker-compose.yml build --no-cache
docker-compose -f ./docker/docker-compose.yml up -d server
```

### Build the image manually

```bash
docker build -f docker/Dockerfile -t stock-analysis .
docker run -d \
  --name dsa-server-local \
  --env-file .env \
  -p 8000:8000 \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/logs:/app/logs" \
  -v "$(pwd)/reports:/app/reports" \
  stock-analysis \
  python main.py --serve-only --host 0.0.0.0 --port 8000
```

---

## Detailed configuration of local operation

### Install dependencies

```bash
# Python 3.10+ Recommended
pip install -r requirements.txt

# or use conda
conda create -n stock python=3.10
conda activate stock
pip install -r requirements.txt
```

Windows PowerShell If you still use the system default code page，It is recommended to enable it before installing dependencies or running environment checks for the first time. UTF-8，Avoid third-party tools or terminal output failing on Chinese characters：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
python -m pip install -r requirements.txt
python scripts/check_env.py --config
```

**Smart import dependencies**：`pypinyin`（Name→Code pinyin matching）and `openpyxl`（Excel .xlsx parse）Already included in `requirements.txt` in，Execute the above `pip install -r requirements.txt` will be installed automatically。If using smart import（pictures/CSV/Excel/clipboard）Function，Please make sure the dependencies are installed correctly；May be reported when missing `ModuleNotFoundError`。

### Command line parameters

```bash
python main.py                        # full analysis（individual stocks + Market review）
python main.py --market-review        # Only broad market review
python main.py --no-market-review     # Only individual stock analysis
python main.py --stocks 600519,300750 # designated stocks
python main.py --dry-run              # Get data only，No AI analysis
python main.py --no-notify            # Do not send push
python main.py --schedule             # Scheduled task mode
python main.py --force-run            # Also enforced on non-trading days（Issue #373）
python main.py --debug                # debug mode（Detailed log）
python main.py --workers 5            # Specify the number of concurrencies
```

---

## Scheduled task configuration

### GitHub Actions Timing

Edit `.github/workflows/00-daily-analysis.yml`:

```yaml
schedule:
  # UTC time，Beijing time = UTC + 8
  - cron: '0 10 * * 1-5'   # Monday to Friday 18:00（Beijing time）
```

Common time comparison：

| Beijing time | UTC cron expression |
|---------|----------------|
| 09:30 | `'30 1 * * 1-5'` |
| 12:00 | `'0 4 * * 1-5'` |
| 15:00 | `'0 7 * * 1-5'` |
| 18:00 | `'0 10 * * 1-5'` |
| 21:00 | `'0 13 * * 1-5'` |

#### GitHub Actions Run manually on non-trading days（Issue #461 / #466）

`00-daily-analysis.yml` Support two control methods：

- `TRADING_DAY_CHECK_ENABLED`：Warehouse level configuration（`Settings → Secrets and variables → Actions`），Default `true`
- `workflow_dispatch.force_run`：Single switch with manual triggering，Default `false`

Recommended priority understanding：

| Configuration combination | Non-trading day behavior |
|---------|-------------|
| `TRADING_DAY_CHECK_ENABLED=true` + `force_run=false` | Skip execution（Default behavior） |
| `TRADING_DAY_CHECK_ENABLED=true` + `force_run=true` | This enforcement |
| `TRADING_DAY_CHECK_ENABLED=false` + `force_run=false` | Always execute（Both scheduled and manual checks do not check the trading day.） |
| `TRADING_DAY_CHECK_ENABLED=false` + `force_run=true` | Always execute |

Manual trigger steps：

1. open `Actions → Daily stock analysis → Run workflow`
2. Choose `mode`（`full` / `market-only` / `stocks-only`）
3. If today is a non-trading day and you want to still execute，will `force_run` set to `true`
4. Click `Run workflow`

### Local scheduled tasks

The built-in scheduled task scheduler supports running tasks at specified times every day（Default 18:00）Run analysis。

#### Command line mode

```bash
# Start timer mode（Execute once immediately on startup，every day thereafter 18:00 execute）
python main.py --schedule

# Start timer mode（Not executed at startup，Just wait for the next scheduled trigger）
python main.py --schedule --no-run-immediately
```

> Description：Timing mode will re-read the currently saved data before each trigger. `STOCK_LIST`。If passed in at the same time `--stocks`，This parameter will not lock the stock list for subsequent plan execution；When you need to temporarily only run designated stocks，Please use unscheduled single run command。
>
> from `python main.py --schedule` or equivalent pure CLI After the scheduling mode is started，WebUI save new `SCHEDULE_TIME` / `SCHEDULE_TIMES` It will be automatically re-binded in the next round of scheduling checks. daily jobs，No need to restart the process；Old execution times will not be retained。`python main.py --serve --schedule` will consist of Web/API runtime scheduler Take over scheduled tasks，WebUI/API/Desktop Long running process saving `SCHEDULE_ENABLED`、`SCHEDULE_TIME` or `SCHEDULE_TIMES` It will then be started, stopped or rebuilt according to the current configuration. runtime scheduler。
>
> Web/API runtime scheduler The immediate execution entry will only accept requests when no analysis tasks are running.；If an analysis is already running，Will return busy status instead of pretending that the queue is successful。

#### environment variable mode

You can also configure timing behavior through environment variables（Applicable to Docker or .env）：

| variable name | Description | Default value | Example |
|--------|------|:-------:|:-----:|
| `SCHEDULE_ENABLED` | Whether to enable scheduled tasks | `false` | `true` |
| `SCHEDULE_TIME` | Daily execution time (HH:MM) | `18:00` | `09:30` |
| `SCHEDULE_TIMES` | Multiple daily execution times，comma separated；Used when empty `SCHEDULE_TIME` | empty | `09:20,12:30,15:10,18:00` |
| `SCHEDULE_RUN_IMMEDIATELY` | Whether to run once immediately when the scheduled mode is started；Inherited when not explicitly set `RUN_IMMEDIATELY` The runtime coverage semantics of | `true` | `false` |
| `RUN_IMMEDIATELY` | Whether to run immediately when non-scheduled mode is started；Also as not explicitly set `SCHEDULE_RUN_IMMEDIATELY` timely legacy rollback | `true` | `false` |
| `TRADING_DAY_CHECK_ENABLED` | Trading Day Check：Skip execution on non-trading days；set to `false` enforceable | `true` | `false` |

For example in Docker Medium configuration：

```bash
# Set not to analyze immediately at startup
docker run -e SCHEDULE_ENABLED=true -e SCHEDULE_RUN_IMMEDIATELY=false ...
```

> Compatibility instructions：If explicitly passed in at runtime `RUN_IMMEDIATELY`，But not passed separately `SCHEDULE_RUN_IMMEDIATELY`，The built-in scheduling mode will continue to inherit the former，avoid being `.env` medium lasting `SCHEDULE_RUN_IMMEDIATELY` Overwrite old values in reverse。

> Compatibility instructions（Issue #1815）：`MARKET_REVIEW_REGION=cn|hk|us|jp|kr|both` Only expand the large disk review input collection；JP/KR For review context consumption only，won't let go Market Light Alarm。
> - `src/config.py`、`src/core/config_registry.py`、`src/services/system_config_service.py` The changes are only configuration semantic extensions，Don't change `provider`/`model`/`base_url` runtime routing，Doesn't trigger either provider/model/base URL Migrate or clean up logic。
> - Actual controlled configuration items in this round：`MARKET_REVIEW_REGION`、`MARKET_REVIEW_COLOR_SCHEME`；`LITELLM_MODEL`、`AGENT_LITELLM_MODEL`、`LITELLM_FALLBACK_MODELS`、`VISION_MODEL`、`OPENAI_BASE_URL` Wait for old value to remain atomic upsert Semantics，Will not be silently cleared or overwritten when updating other fields。
> - Summary of verifiable evidence：official provider / Base URL / Model naming source inherited [LLM Configuration Guide](LLM_CONFIG_GUIDE.md#Common official documentation sources for checking presets-provider--base-url--Model naming)，Current runtime dependency window inheritance `requirements.txt` in `litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0`；There are no new configuration migration scripts or branch cleaning in this round.，save/The import still only writes the submission key。`tests/test_system_config_service.py::SystemConfigServiceTestCase::test_update_market_review_region_does_not_trigger_runtime_model_cleanup` Overwrite only save `MARKET_REVIEW_REGION` Never clear or rewrite `LITELLM_CONFIG`、`LLM_CHANNELS`、`LLM_OPENAI_*`、`LITELLM_MODEL`、`AGENT_LITELLM_MODEL`、`LITELLM_FALLBACK_MODELS`、`VISION_MODEL`、`OPENAI_*` Wait for old configuration。
> - Old value fallback strategy：Restore backup first `MARKET_REVIEW_REGION` With the configuration file you can return to the old boundary，Uncommitted model/The routing key retains its original value；when necessary `revert` PR and press `.env` Backup complete rollback。
> - Rollback path：Before reverting to submission `.env` / configuration backup `MARKET_REVIEW_REGION` and related runtime variables，or directly revert Ben PR。

#### Trading day judgment（Issue #373）

Default based on self-selected stock market（A shares / Hong Kong stocks / US stocks / Japanese stocks / Korean stocks）and `MARKET_REVIEW_REGION` Determine whether it is a trading day：
- Use `exchange-calendars` distinguish A shares / Hong Kong stocks / US stocks / Japanese stocks / Korean stocks’ respective trading calendars（Including holidays）
- When mixing positions，Each stock is analyzed only on its market open day，Skip stocks on the day they are closed
- All relevant markets are on non-trading days，Skip execution overall（Does not start pipeline、Don't send push）
- Resume transfer from breakpoint and `--dry-run` of“Data already exists”Judgment shares the same set“Latest reusable transaction date”parsing logic，No longer use the server directly for natural days
- `Latest reusable transaction date` Will be parsed according to the local time zone of the market to which the stock belongs.：A Share use `Asia/Shanghai`，Hong Kong stocks use `Asia/Hong_Kong`，US stocks use `America/New_York`，Japanese stocks use `Asia/Tokyo`，Korean stocks use `Asia/Seoul`
- non-trading day（weekend / holidays）runtime，Will go back to the latest trading day to check local data；If the data for this trading day already exists，then skip repeated crawling，Otherwise continue to complement
- When running during the trading day or before the close，The last completed transaction day will be used as the reuse target.；When run after the close of the trading day，If the data for the day already exists, you can skip it directly.，If it does not exist, continue to crawl.
- Coverage method：`TRADING_DAY_CHECK_ENABLED=false` or command line `--force-run`

#### market stage baseline（Issue #1386 P0）

P0 Only the internal market stage inference baseline is added，No changes to the existing daily closing report、Trading day skipped、Resume upload from breakpoint、API、Web、Bot、Agent or GitHub Actions Default behavior。Stage inference is used for subsequent P1+ context contract preparation；Not installed `exchange-calendars` Or when the calendar is abnormal，stage return `unknown`，However, the existing trading day judgment and the latest reusable trading day logic remain the same. fail-open behavior。

The stage enumeration is based on regular session Semantics：

| stage | meaning |
| --- | --- |
| `premarket` | Before the regular trading session opens；It does not mean that the pre-market extended period quotations have been obtained. |
| `intraday` | During regular trading hours，And it is not during the lunch break or near the closing window |
| `lunch_break` | Lunch window provided by the market calendar；The market will not enter this stage without a lunch break |
| `closing_auction` | Close Heuristic Window：A shares 3 minutes、Hong Kong stocks 10 minutes、US stocks 5 minutes、Taiwan stocks 5 minutes（13:25–13:30）；Does not represent the complete exchange bidding system |
| `postmarket` | After the close of regular trading hours；It does not mean that the after-hours extended period quotations have been obtained. |
| `non_trading` | The current market local date is not a trading day |
| `unknown` | unknown market、Calendar is unavailable or calendar is abnormal，Unable to reliably infer stage |

Current entrance status：

- Common stock analysis、Agent analysis、Web Manual analysis、Bot `/analyze` / `/ask`、schedule、GitHub Actions Still using the existing analysis path and after-hours review caliber，not because P0 Phase baseline automatic switching Prompt or output structure。
- The market review still presses `MARKET_REVIEW_REGION` Run with trading day filter，Not consuming market stage label。
- Cross-market mixed self-selected stocks should be divided into symbol Separate inference stages of own market；Aggregation report display“Inconsistency across multiple market stages”leave to P1+。

Known issue baseline：

- When triggered intraday，The report may still write down the intraday quotations that have not yet closed as a complete trading day review.。
- The output may still be biased towards“Today’s trend review / Pay attention tomorrow”，instead of“What to observe next in the current session”。
- Real-time market timestamp、data source、caching and stale The status has not yet uniformly entered the stage context.。
- Market closed at noon、Nearing closing、Scenarios such as forced operation on non-trading days have not yet been Prompt and report structure explicit expression。

P0 Don't do it：Not connected pipeline / Agent / API / Web / Bot，Do not modify the report schema，Do not change the alarm technical indicator of partial bar judge，No new configuration items are added either。

#### Running market stage context（Issue #1386 P1a）

P1a Analysis on common stocks pipeline、legacy Agent context and multi-agent `ctx.meta` constructor and pass inside `market_phase_context`。The context contains the market、stage、Market local date、Latest reusable daily date、trading day/open market/partial bar tri-state flag、Opening and closing minutes best-effort Estimate，and `unknown_market`、`calendar_unavailable`、`calendar_error` Waiting for downgrade warning code。

P1a itself does not change Prompt copywriting、API/Web/Bot parameters、Report structure、history/task status stable metadata or quote freshness/data quality Semantics；General analysis history snapshot and Agent history snapshot The running state field will be stripped。Follow-up P1b Redefining persistence metadata Display contract with task status。

#### Market stage hyposensitivity Metadata（Issue #1386 P1b）

P1b will P1a of runtime `market_phase_context` Projection is stable、hypoallergenic、public `market_phase_summary`，and write `analysis_history.context_snapshot` top level。historical details、Synchronous analysis of responses and completed `/api/v1/analysis/status/{task_id}` All passed `report.meta.market_phase_summary` Returns the same market stage meta information；completed Task status is not added `TaskStatus` Top level fields，only pass `status.result.report.meta.market_phase_summary` indirect exposure。

`market_phase_summary` Includes only markets、stage、market local time、session date、effective daily-bar date、trading day/open market/partial-bar mark、Opening and closing minutes、trigger source、Analyze intent and warning code。it does not expose the complete `market_phase_context`，Don't join either quote freshness、fallback、stale or data_quality scoring Field。`report.details.analysis_context_pack_overview` still express #1389 Input block quality summary；API returned `details.context_snapshot` will peel off the top layer `market_phase_summary` and `analysis_context_pack_overview`，avoid raw snapshot Repeatedly display these stable public fields。`SAVE_CONTEXT_SNAPSHOT=false` Not persisting the entire copy `analysis_history.context_snapshot`，Old history is missing summary When the field is empty，The report still returns normally。

P1b Don't change Prompt、No new addition `analysis_phase` Request parameters、Don't do it Web Stage label or page display，Not covered either pending/processing TaskPanel、SSE ongoing events、Bot、Notification、`market_review` or P3 Intraday data quality field。

#### market stage Prompt Inject（Issue #1386 P2-min）

P2-min Start with obtained `market_phase_context` in the analysis path，Render the running market stage as LLM readable Prompt block。General analysis、single Agent and multi-agent will be in Prompt See the current stage in、market local time、Latest reusable complete daily date and minimum phase constraints：No description allowed before opening“Today’s trend has already occurred”，intraday / noon / Near the close, it needs to be explained that the last daily line may not be completed.，Retain complete trading day review semantics after the market opens，Keep conservative statements on non-trading days or unknown stages。

P2-min Still not adding API/Web/Bot parameters，Do not write history/task status/report metadata，Don't change the report JSON schema，Nor does it introduce complete quote freshness、fallback、stale or data_quality contract。Bot/API direct connection Agent If not passed P1a pipeline build `market_phase_context`，Still maintaining old behavior；The entrance transparent transmission and visible display are left to the follow-up P4+。

#### Intraday packets and real-time quality control（Issue #1386 P3）

P3 Complete the real-time market quality metadata used in the main path of ordinary analysis，But still no new additions `analysis_phase` parameters，Don't change API/Web/Bot stage entrance，Don't change the report JSON schema，Nor do #1389 P5 Data quality score or model confidence limits。real time quote Will bring it `fetched_at`、`provider_timestamp`、`is_stale`、`stale_seconds`、`fallback_from`；Among them `fetched_at` is the system acquisition time，`provider_timestamp` only in provider Fill in when truly providing market time。missing provider Time will not be forged fresh，`stale_seconds` and `is_stale` keep empty。

Whole source fallback The semantics of is fixed as：`source` Keep actual success data sources token，`fallback_from` Record the highest priority source that failed in this round token；If the preferred source is successful and only fields are filled from the subsequent source, it will not be written. `fallback_from`。`AnalysisContextBuilder` Map only these upstreams artifact，No retrieval、No quality rating；quote block Status button `STALE > FALLBACK > AVAILABLE` merge。Intraday real-time price coverage `today` will be marked `is_partial_bar`、`is_estimated`、`estimated_fields`、`realtime_source` and quote metadata；`daily_bars` block still express storage Medium complete daily window，partial/estimated only enter technical block。freshness scoring、intraday cache TTL Grading、Agent Tool level reuse and API/Web Presentation is left to subsequent stages。

#### Analysis phase entrance and task queue transparent transmission（Issue #1386 P4a）

P4a New `analysis_phase=auto|premarket|intraday|postmarket` Request parameters，Default `auto`，used to let API The caller explicitly overrides this analysis phase。This parameter is currently accessed `POST /api/v1/analysis/analyze`、Asynchronous task queue、`AnalysisService`、General analysis pipeline and market stage context；Web frontend type and API mapper This field has been taken over，But no new pages will be added selector，Bot、schedule、GitHub Actions and DB migration It is also not within the scope of this stage。

`analysis_phase` is the requested override value；The final reporting stage is still based on `report.meta.market_phase_summary.phase` Subject to。asynchronous accepted response、Memory tasks status、task list and SSE payload Will echo the request phase；history DB fallback No new persistent fields are added，Old records may still be empty。Same stocks are different phase Still use the same stock task to remove duplicates，Avoid concurrent duplication of analysis。

Internal stage context construction is still compatible with old parameters `analysis_intent`：only if `analysis_phase` keep `auto` time，Not `auto` of `analysis_intent` will be classified as this request stage；External callers should take precedence over `analysis_phase`。

`auto` Keep existing trading calendar extrapolated；Not `auto` only cover phase and recalculate `is_trading_day`、`is_market_open_now`、`is_partial_bar`、`minutes_to_open` and `minutes_to_close`。Covering does not rewrite reality `market_local_time` or `effective_daily_bar_date`；If the current date is not a trading day or the calendar does not support the corresponding session，Minutes field can be empty。

#### Web Stage label display（Issue #1386 P4b）

P4b in Web End completion phase visibility，But no new stage coverage will be added selector。The ongoing tasks panel only displays P4a Echo request phase `analysis_phase`，Among them `auto` Explicitly shown as“automatic phase”，No pretense of final inference stage。The final report page ends with `report.meta.market_phase_summary.phase` Show actual market stage labels，And in `is_partial_bar=true` prompt“The daily line is not completed”。

Data quality summaries continue to be reused `report.details.analysis_context_pack_overview.data_quality` and existing `AnalysisContextSummary`；Web Stage labels will be displayed on the same report details page，and continue to reuse low-sensitivity data quality summaries，not exposed completely `AnalysisContextPack`、Prompt summary、raw payload or stripped snapshot internal fields。History list、Bot、schedule、GitHub Actions、Desktop、Notification summary and advanced stage coverage entrance are still follow-up work。

#### AnalysisContextPack Prompt Summary（Issue #1389 P3）

P3 In ordinary analysis and Agent access in initial context `AnalysisContextPack` Hypoallergenic summary。Pipeline Will use the obtained quotes、daily line、Trend、chips、Fundamentals、News and Market Stage artifacts Assemble pack，again `analysis_context_pack_summary` Insert Prompt；Added in this pack in summary block，LLM only see subject、version、Status of each data block/Source/warning/missing reason and the number of news results，will not be seen in full through this block `news.content`、`trend_result`、chips or fundamentals raw payload。existing `news_context`、Agent pre-fetched JSON and `enhanced_context` Original data channel remains P3 previous behavior，Not replaced or desensitized by this summary。

P3 No new additions were made at that time API/Web/Bot parameters，Do not write history/task status/report metadata，Don't change the report JSON schema，Not complete pack exposed to history、notify or Web。Agent Tool-level reuse pack data and P5 Data quality scoring is left to subsequent stages。

#### AnalysisContextPack Hypoallergenic visibility（Issue #1389 P4）

P4 New `report.details.analysis_context_pack_overview`，historical details and completed `/api/v1/analysis/status/{task_id}` will be removed from the persisted `context_snapshot` Return to the same hypoallergenic overview；The synchronous analysis response will also read the data that has been dropped into the library this time. `analysis_history.context_snapshot` Extract overview，Therefore `SAVE_CONTEXT_SNAPSHOT=false` This field is not guaranteed to be returned for new records。Web The end report page is at“strategic point”and“information”Then display the default collapsed data block summary，Collapse the header to display the available number、Missing number、Non-zero other state counts and trigger sources，Display data block status after expansion、Source、warning、missing reason、Status count and number of news results。API returned `details.context_snapshot` will peel off the top layer `analysis_context_pack_overview`，Avoid repeated display of transparency panels raw snapshot。

the overview Does not contain complete pack、`analysis_context_pack_summary` Prompt string、`items.value`、News text、`trend_result`、chips or fundamentals raw payload。`SAVE_CONTEXT_SNAPSHOT=false` Not persisting the entire copy `analysis_history.context_snapshot`，So will not read from new history overview；Old history is missing overview When the field is empty，The report still returns normally。Not covered at this stage pending/processing TaskPanel、SSE ongoing events、Notification summary、Bot/Desktop Exclusive display、`market_review` overview or data quality score。

#### AnalysisContextPack Data quality score vs. Prompt Data limits（Issue #1389 P5）

P5 Without modification `PACK_VERSION = "1.0"`、No new data sources and no changes to reports JSON schema under the premise，give `AnalysisContextPack` Add lightweight data quality scoring and model-readable data limit blocks。`ContextFieldStatus` New `fetch_failed`，It only means that the field or data block failed to be fetched this time.；The first edition only `fundamental_context.status == "failed"` mapped to `fetch_failed`，empty news、Search not configured、No real time quote or chip Missing items will still be treated as existing `missing` / `not_supported` Process。

`DataQuality` now contains `overall_score`、`level`、`block_scores`、`limitations`，and keep the old `warnings` / `metadata`。Rating fixed coverage `quote`、`daily_bars`、`technical`、`news`、`fundamentals`、`chip` six yuan，No renormalization due to missing auxiliary blocks；Core block downgrade will occur in Prompt of“Data limits”In the block, the model is required not to output high confidence，Missing auxiliary blocks only limit the corresponding analysis paragraphs，Should not be interpreted as positive or negative。the Prompt Block consists of `format_analysis_context_pack_prompt_section()` Unified generation，General analysis、single Agent and multi-agent Use the same hypoallergenic summary，not exposed raw payload、News text、trend raw value、secret、token or webhook。

historical details、Synchronous analysis of responses and completed Task status continues to pass only `report.details.analysis_context_pack_overview` Expose low-sensitivity fields；P5 only in that overview Add under `data_quality`，contains score、level、block_scores and limitations，No repeated disclosure `warnings`。Web Report pages are still collapsed by default to display data block summaries.，Added quality score for folded head/level，Expanded to display restriction description and `fetch_failed` Status；`details.context_snapshot` Continue peeling off the top layer `analysis_context_pack_overview`。

#### AnalysisContextPack Documentation、Migration and rollback（Issue #1389 P6）

P6 Only document and configuration visibility closing，No new addition pack runtime、No new addition pack enable/disable feature flag、Do not modify `PACK_VERSION = "1.0"`、No new addition API parameters、Don't change the report JSON schema，No database migration is done either。complete contract、Field status、Hypoallergenic summary visibility、desensitization boundary、For migration and rollback instructions see [AnalysisContextPack Topic documents](analysis-context-pack.md)。

`SAVE_CONTEXT_SNAPSHOT` is an existing environment variable，P6 Just sync it to `.env.example`、Configure the registry and Web Setup help。Default `true`；set to `false` or CLI Use `--no-context-snapshot` time，New history records are no longer persisted in full `analysis_history.context_snapshot`，include `enhanced_context`、`market_phase_summary`、`analysis_context_pack_overview`、diagnostic snapshots and raw snapshot Field。This setting does not turn off the current `AnalysisContextPack` build，Do not remove Prompt Hypoallergenic `analysis_context_pack_summary`，It does not change the analysis results JSON schema or API Request parameters。

There is currently no runtime pack main switch；Close if needed P3-P5 of pack Prompt Summary、overview or data quality access，Can only be done via release rollback or code rollback。There is no old history `analysis_context_pack_overview` / `data_quality` Continue to return empty fields when，Report reads remain compatible。

#### Intraday decision-making guardrails and quality checks（Issue #1386 P5）

P5 In individual stock analysis reports `dashboard.phase_decision` Add staged decision fields in：`phase_context`、`action_window`、`immediate_action`、`watch_conditions`、`next_check_time`、`confidence_reason` and `data_limitations`。This field is reported only JSON backwards-compatible extensions enter history `raw_result`；No new addition `analysis_phase` API parameters、Do not change Web stage entrance、No new configuration items，It also does not affect the default behavior of daily closing review.。

General analysis and Agent The analysis will be reused before saving the history `market_phase_summary` and `analysis_context_pack_overview.data_quality` Implement lightweight guardrails：core quote / daily_bars / technical data stale、fallback、missing、fetch_failed、partial or estimated time，High confidence conclusions are not allowed；Before the market、High-confidence intraday trades are not allowed on non-trading days or at unknown stages.；intraday、At noon and near the close, the post-market review tone in the main conclusion will be checked.，and put the obvious"The review after today’s close shows""Focus on tomorrow"Class wording changed to Stage Safety Observation/waiting for expression。Guardrail only compensates for hyposensitivity `phase_context` and data limits，Don’t make up observation conditions or next inspection time；Notification summary、Alarm、The linkage between positions and backtesting is left to follow-up P6。

#### Signal attribution analysis（Issue #1742）

Issue #1742 In individual stock analysis reports `dashboard.signal_attribution` New signal attribution analysis field in：`technical_indicators`、`news_sentiment`、`fundamentals`、`market_conditions`（Four degrees of contribution；The effective non-zero contribution is normalized to 100；All zeros means no valid signal）、`strongest_bullish_signal` and `strongest_bearish_signal`。This field explains the composition of the recommendation reason，Help users understand AI Attribution weight for decisions。

Signal attribution analysis is displayed simultaneously in all report rendering paths：
- `generate_dashboard_report()`（Default notification report）
- `generate_single_stock_report()`（Single stock push report）
- `templates/report_markdown.j2`（Jinja2 Template）
- `HistoryService._generate_single_stock_markdown()`（Web history drawer）

The normalization function is in `_parse_response()` and `parse_dashboard_json()` Explicit call in，ensure：
- Convert string percentage to int（Such as `"35%"` → `35`）
- Convert negative numbers to 0
- sum≠100 normalized to the sum=100
- value clipped to [0, 100] scope

`signal_attribution` is an optional display field（Optional）。Missing will not fail the integrity check，Will not write `missing` List or triggered completion prompt；When present, it will be normalized and displayed in supported reporting paths.。

#### Alarm、Position and historical linkage（Issue #1386 P6）

P6 will existing `market_phase_summary` with `analysis_context_pack_overview` Reuse to alarm、Position、history、Backtesting and notification links，No new addition phase/pack agreement，No database migration is done either。Alarm trigger records still use the existing `diagnostics` text field；When diagnostics Yes JSON When，worker will be in `status=triggered` merge write in record `analysis_visibility.market_phase_summary`、`analysis_visibility.analysis_context_pack_overview` and `analysis_visibility.source`。old plain text diagnostics Keep the original text，Alert API The derived field is empty and `analysis_visibility_source=legacy_text`。

Alarm phase Summary from trigger-time context：symbol The target is extrapolated from the stock market，`target_scope=market` Use directly `cn|hk|us|jp|kr` market area，When the account level cannot be uniquely positioned, it is allowed to fall into `unknown`。pack overview Only from the evaluator has been brought overview or recently 30 day history snapshot hyposensitivity overview，Return if missing `null`，Not forged pack，Do not automatically trigger lightweight LLM analysis。public source The value is `alert_trigger_market_context`、`analysis_history_snapshot`、`evaluator_snapshot`、`legacy_text` or `null`。

A new entry for manual single stock analysis has been added to the position page，Correspond `POST /api/v1/portfolio/positions/{symbol}/analysis`。The request fields are `account_id`、`analysis_phase=auto|premarket|intraday|postmarket` and `force`；Only non-zero positions in the current position snapshot can be submitted，Return without position 404，Multiple accounts hold the same stock but are not transferred `account_id` Return `400 ambiguous_position_account`。This entry follows the asynchronous task accepted / duplicate Semantics，`force` Only affects analysis refresh，Do not bypass in-flight duplicate。The backend only treats hypoallergenic `portfolio_context` Incoming internal pipeline and context pack optional `portfolio` block；the block Does not participate in the total quality score of the existing six pieces of data，It will not appear in the task list or SSE payload in。

History list、Single stock history、StockBar and details will be from `context_snapshot` Extract `market_phase_summary`；old record、Missing snapshot Or return if parsing fails `null`。Backtest result items added `market_phase` with `market_phase_summary`，result list and performance/summary Query support `analysis_phase=premarket|intraday|postmarket|unknown`；Unify statistics `intraday`、`lunch_break`、`closing_auction` subsumed intraday，put `non_trading`、Missing and illegal values imputed unknown。bring phase Filtered backtest queries will be in repository Layer button SQL Conditional batch reading results and snapshot，first bucket Paginate again，And in summary diagnostics return in `phase_breakdown` with `raw_phase_counts`。

Notification summary reuse unified public format helper，Only output stage labels、trigger source、partial-bar warning、Data quality level and the first two limitations；Will not output raw context pack、Prompt、News text or position sensitive details。Web Alarm history、Position、History list、StockBar Synchronize the display stage with the backtest page badge、quality summary、phase filter with breakdown。

#### Documentation、Configuration and migration instructions（Issue #1386 P7）

P7 Pre-market only / intraday / User visible instructions for after-hours analysis close，No new runtime capabilities、Configuration items、API parameters、Database migration、Web Stage coverage selector、Bot phase parameters or GitHub Actions intraday workflow。Default daily closing analysis、Default GitHub Actions and existing schedule Behavior remains the same。

Recommended usage：

| scene | Recommended use | Description |
| --- | --- | --- |
| Before the market | Generate opening plan and observation conditions | You cannot write today’s trends that have not yet happened as facts；Focus on the last complete trading day、Overnight information and opening triggers。 |
| intraday / noon / Nearing closing | Make real-time status judgments、Risk and Opportunity Alerts | Pay attention to current price、Real-time market freshness、partial bar、Data limitations and next observation conditions，Does not replace the complete post-market review。 |
| after hours | Keep the complete review and plan for the next day | Use full trading day semantics，is the closest scenario to the default daily analysis。 |

Access and visibility：

| entrance | stage behavior |
| --- | --- |
| `POST /api/v1/analysis/analyze` | support `analysis_phase=auto|premarket|intraday|postmarket`；Default when not transmitting `auto`。 |
| Web main analysis / Reanalyze / Manual analysis of positions | There is currently no stage coverage selector；The front-end call passes the default `auto`。The ongoing task panel shows the request stage，The final report page shows the final stage label。 |
| Bot / CLI / schedule / Default GitHub Actions | Not passed on `analysis_phase`，keep walking `auto` inference；The default closing analysis behavior remains unchanged。 |
| history / backtest / Notification / Alarm | Only consume public `market_phase_summary` and hyposensitivity `analysis_context_pack_overview`；Undisclosed complete pack、Prompt summary、News text or position sensitive details。 |

`analysis_phase` is the requested override value，The final reporting stage is still based on `report.meta.market_phase_summary.phase` Subject to。Old calls are not passed `analysis_phase` remain compatible；old history missing `market_phase_summary` or `analysis_context_pack_overview` returns an empty field，Does not affect report reading。Backtest query support `analysis_phase=premarket|intraday|postmarket|unknown` filter，and press P6 Rules classify midday and near-closing intraday。

`SAVE_CONTEXT_SNAPSHOT=false` or CLI `--no-context-snapshot` Only stop persisting the entire copy of new history `context_snapshot`，Therefore the new history is no longer public phase summary / pack overview / diagnostics snapshot Wait for persistence summary；it does not close when `AnalysisContextPack` build，Do not remove Prompt Hypoallergenic `analysis_context_pack_summary`，Nor does it change the report JSON schema。To temporarily return the caller to an output closer to the old after-hours caliber，Can be fixedly transmitted `analysis_phase=postmarket`；To completely remove P0-P6 stage/pack runtime Access，Release rollback or code rollback required。

#### Use Crontab

If you do not want to use a resident process，You can also use the system Cron：

```bash
crontab -e
# add：0 18 * * 1-5 cd /path/to/project && python main.py
```

---

## Notification channel detailed configuration

Notification channel matrix、minimal/advanced key layered、`--check-notify` For diagnostic caliber and scenario configuration instructions, see [Notification topic document](notifications.md)。

### Enterprise WeChat

1. Add in corporate WeChat group chat"swarm robots"
2. Copy Webhook URL
3. settings `WECHAT_WEBHOOK_URL`

### Feishu

> ⚠️ **key distinction**：`FEISHU_WEBHOOK_SECRET`（Webhook Signing key）and `FEISHU_APP_SECRET`（Feishu application Secret）are two completely different configurations，Not interchangeable。

**Minimum available configuration（No security restrictions）：**

```env
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your_hook_token
```

**Complete steps：**

1. **Create a custom bot in Feishu group chat**：
   - Open target group chat → upper right corner「Group settings」→「swarm robots」→「Add bot」→「Custom robot」
   - Fill in the robot name，Generated by copy **Webhook URL**（Format：`https://open.feishu.cn/open-apis/bot/v2/hook/...`）
2. settings `FEISHU_WEBHOOK_URL`（That is, copied in the previous step URL）。
3. View robots**Security settings**，Determine whether additional configuration is required based on the enabled security items：
   - **No additional security settings**：Just fill in `FEISHU_WEBHOOK_URL` That’s it。
   - **turned on「Signature verification」**：Display Feishu secret Fill in `FEISHU_WEBHOOK_SECRET`。Both ends must be enabled at the same time or left blank at the same time.，Otherwise, Feishu will return signature verification failure.。
   - **turned on「keywords」**：Fill in the same keyword `FEISHU_WEBHOOK_KEYWORD`；The system will automatically add it before each message，No need to manually modify report templates。
   - **turned on IP whitelist**：Ensure the exit of the current running environment IP in whitelist（local/Docker/GitHub Actions export IP different）。
4. `FEISHU_APP_ID` / `FEISHU_APP_SECRET` It’s the Feishu app / Stream Bot / Dedicated to cloud document mode，Will not trigger the group Webhook push，Don't just use them instead `FEISHU_WEBHOOK_URL`。
5. If configured `FEISHU_APP_ID` / `FEISHU_APP_SECRET`，Reconfigure `FEISHU_CHAT_ID`，You can use Feishu App Bot Push notifications directly to designated group chats or users，No need to rely on the group Webhook；`FEISHU_RECEIVE_ID_TYPE` Default `chat_id`，When chatting privately, change it to `open_id`。The way to take Feishu OpenAPI Bot session，With the group Webhook are two independent links。
6. App Bot Send path multiplexing `requirements.txt` existing in `lark-oapi>=1.0.0`，Standard source code installation、Docker、GitHub Actions daily workflow and desktop building links will pass `pip install -r requirements.txt` Installation，No need to install new libraries separately。Reference：[Feishu message create OpenAPI](https://open.feishu.cn/document/server-docs/im-v1/message/create)、[lark-oapi PyPI](https://pypi.org/project/lark-oapi/)、[SDK repo](https://github.com/larksuite/oapi-sdk-python)。

**Common reasons for failure：**
- Just filled in `FEISHU_APP_ID` / `FEISHU_APP_SECRET`，neither configured `FEISHU_WEBHOOK_URL`，There is no configuration App Bot Proactively push what you need `FEISHU_CHAT_ID`
- Feishu robot is activated「Signature verification」，But `FEISHU_WEBHOOK_SECRET` Not configured（or mistakenly filled in as `FEISHU_APP_SECRET`）
- Feishu robot is activated「keywords」，But there is no synchronization configuration locally `FEISHU_WEBHOOK_KEYWORD`
- The robot has not been added to the target group，Or the group administrator has restricted the robot from speaking.
- Feishu side has additional configurations IP whitelist，But the current operating environment IP Not in the whitelist
- Message content is too long：There is a length limit for a single message in Feishu，The system will automatically send in segments；To view the entire content in one document，Configurable Feishu cloud document function（`FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_FOLDER_TOKEN`）

For a more complete graphic review, please see [docs/bot/feishu-bot-config.md](bot/feishu-bot-config.md)。
### Telegram

1. with @BotFather Conversation creation Bot
2. Get Bot Token
3. Get Chat ID（Passable @userinfobot）
4. settings `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
5. (Optional) To send to Topic，settings `TELEGRAM_MESSAGE_THREAD_ID` (from Topic Get at the end of the link)

### Mail

1. open mailbox SMTP service
2. Get authorization code（Non-login password）
3. settings `EMAIL_SENDER`、`EMAIL_PASSWORD`、`EMAIL_RECEIVERS`

Supported emails：
- QQ Email：smtp.qq.com:465
- 163 Email：smtp.163.com:465
- Gmail：smtp.gmail.com:587

**Stock groups are sent to different mailboxes**（Issue #268，Optional）：
Configuration `STOCK_GROUP_N` with `EMAIL_GROUP_N` Reports of different stock groups can be sent to different mailboxes，For example, when multiple people share analysis, they do not interfere with each other.。`STOCK_LIST` Still determines the set of stocks for this actual analysis，`STOCK_GROUP_N` should be written as `STOCK_LIST` subset of；It only affects email recipients，won't change Telegram、Enterprise WeChat、Webhook Wait for the complete report to be received from other channels。The disk review will be sent to all configured mailboxes。

> GitHub Actions Limit：As of 2026-03-29，Warehouse comes with `00-daily-analysis.yml` Any numbers will not be automatically imported `STOCK_GROUP_N` / `EMAIL_GROUP_N`。So if you are only in the warehouse Secrets / Variables Add these variables in，without modification workflow Explicit mapping，They will not enter the running process，looks like“Group configuration does not take effect”。

```bash
STOCK_LIST=600519,300750,002594,AAPL
STOCK_GROUP_1=600519,300750
EMAIL_GROUP_1=user1@example.com
STOCK_GROUP_2=002594,AAPL
EMAIL_GROUP_2=user2@example.com
```

### Customize Webhook

Support any POST JSON of Webhook，include：
- DingTalk Robot
- Discord Webhook
- Slack Webhook
- Bark（iOS push）
- Self-built services

settings `CUSTOM_WEBHOOK_URLS`，Multiple separated by commas。

If necessary AstrBot、NapCat or special self-built services body，Can be set `CUSTOM_WEBHOOK_BODY_TEMPLATE`。This is the global template，will precede Bark、Slack、Discord Wait URL automatic recognition payload Take effect；If after rendering it is not JSON object，The system will fall back to the default payload。Recommended `$content_json` / `$title_json` Avoid line breaks and quote breakage JSON：

```env
CUSTOM_WEBHOOK_BODY_TEMPLATE={"msg_type":"text","content":$content_json}
```

Available placeholders：`$content_json`、`$content`、`$title_json`、`$title`。Among them `$content` / `$title` is a bare string，Don't do it JSON escape；It may be triggered when the text contains double quotes or line breaks. fallback。

Docker Compose Deploying，Pass Web When the settings page is saved, these application placeholders will be written as `$$content_json` / `$$title_json` etc.，avoid Compose Expand it to empty when redeploying；When the app is running, it reverts to a single `$`。If manually edited Docker used `.env`，Please use the same `$$content_json` This kind of writing。

Bark When using global templates, you need to explicitly write Bark body：

```env
CUSTOM_WEBHOOK_BODY_TEMPLATE={"title":$title_json,"body":$content_json,"group":"stock"}
```

NapCat / OneBot Examples must be based on actual endpoint、`user_id` or `group_id` adjust：

```env
CUSTOM_WEBHOOK_BODY_TEMPLATE={"user_id":123456,"message":$content_json}
```

### ntfy / Gotify

ntfy and Gotify They are all first-class notification channels，Send text only / JSON，Not participating Markdown Transfer pictures。

ntfy Use full topic endpoint，the last one path segment will act as topic：

```env
NTFY_URL=https://ntfy.sh/my-topic
NTFY_TOKEN=
```

Gotify Use server base URL，The system will automatically splice and fix `/message` API，and pass `X-Gotify-Key` Header send application token。`GOTIFY_URL` Can include reverse proxy path prefix，but don't include `/message`：

```env
GOTIFY_URL=https://gotify.example
GOTIFY_TOKEN=app-token
```

```env
# Actual requests are sent to https://example.com/gotify/message
GOTIFY_URL=https://example.com/gotify
GOTIFY_TOKEN=app-token
```

`NTFY_URL` with `GOTIFY_URL` The semantics of the two services are different API Deliberate choices resulting from different designs：ntfy by user topic constitute endpoint，Gotify of `/message` It's a fixed service API。

### Discord

Discord Supports two methods of push：

Long report will press Discord Single content 2000 The upper limit of characters is automatically sent in fragments；If you encounter a certain piece 429 Current limiting，The transmitter will press Discord returned `retry_after` or `Retry-After` Do limited retries，and continue to try subsequent shards。`DISCORD_MAX_WORDS` Adjustable length of single piece，But the runtime will not allow more than 2000。

**Method one：Webhook（Recommended，simple）**

1. in Discord Created in channel settings Webhook
2. Copy Webhook URL
3. Configure environment variables：

```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxx/yyy
```

**Method 2：Bot API（Need more permissions）**

1. in [Discord Developer Portal](https://discord.com/developers/applications) Create app
2. create Bot and get Token
3. Invite Bot to server
4. Get channel ID（Right-click the channel to copy in developer mode）
5. Configure environment variables：

```bash
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_MAIN_CHANNEL_ID=your_channel_id
```

if you want to receive Discord Slash Command / Interaction callback，and not just to Discord push message，Still need to be in Discord Developer Portal of `General Information -> Public Key` Copy the public key and configure：

```bash
DISCORD_INTERACTIONS_PUBLIC_KEY=your_public_key
```

When the public key is not configured，The system will reject all Discord Inbound webhook Request。

### Slack

Slack Supports two methods of push，Use priority when configuring at the same time Bot API，Make sure text and images are sent to the same channel：

**Method one：Bot API（Recommended，Support image upload）**

1. create Slack App：https://api.slack.com/apps → Create New App
2. add Bot Token Scopes：`chat:write`、`files:write`
3. Install to workspace and get Bot Token (xoxb-...)
4. Get channel ID：Channel details → Copy channel at bottom ID
5. Configure environment variables：

```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
```

**Method 2：Incoming Webhook（Simple configuration，text only）**

1. in Slack App Management page creation Incoming Webhook
2. Copy Webhook URL
3. Configure environment variables：

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../xxx
```

### Pushover（iOS/Android push）

[Pushover](https://pushover.net/) It is a cross-platform push service，support iOS and Android。

1. Register Pushover account and download App
2. in [Pushover Dashboard](https://pushover.net/) Get User Key
3. create Application Get API Token
4. Configure environment variables：

```bash
PUSHOVER_USER_KEY=your_user_key
PUSHOVER_API_TOKEN=your_api_token
```

Features：
- support iOS/Android Dual platform
- Support notification priority and sound settings
- Free quota is enough for personal use（monthly 10,000 Article）
- Messages can be retained 7 day

### Markdown Transfer pictures（Optional）

Configuration `MARKDOWN_TO_IMAGE_CHANNELS` Reports can be sent as pictures to unsupported Markdown channels（telegram, wechat, custom, email, slack）。

**Depends on installation**：

1. **imgkit**：Already included in `requirements.txt`，execute `pip install -r requirements.txt` will be installed automatically
2. **wkhtmltopdf**（Default engine）：system level dependencies，Requires manual installation：
   - **macOS**：`brew install wkhtmltopdf`
   - **Debian/Ubuntu**：`apt install wkhtmltopdf`
3. **markdown-to-file**（Optional，emoji better support）：`npm i -g markdown-to-file`，and set `MD2IMG_ENGINE=markdown-to-file`

When not installed or failed to install，will automatically fall back to Markdown Text sending。

**Single stock push + Picture sending**（Issue #455）：

Single stock push mode（`SINGLE_STOCK_NOTIFY=true`）down，If you wish Telegram Push through other channels in the form of images，Need to be configured at the same time `MARKDOWN_TO_IMAGE_CHANNELS=telegram` And install the image transfer tool（wkhtmltopdf or markdown-to-file）。The daily summary of individual stocks also supports chart conversion.，No additional configuration required。

**Troubleshooting**：If the log appears「Markdown Failed to transfer picture，Send fallback as text」，please check `MARKDOWN_TO_IMAGE_CHANNELS` Are the configuration and image transfer tools installed correctly?（`which wkhtmltoimage` or `which m2f`）。

---

## Data source configuration

The system uses by default AkShare（free），Other data sources are also supported：

### AkShare（Default）
- free，No configuration required
- Data source：Oriental wealth crawler

### Tushare Pro
- Requires registration to obtain Token
- more stable，More complete data
- settings `TUSHARE_TOKEN`

### Baostock
- free，No configuration required
- as an alternative data source

### YFinance
- free，No configuration required
- Support US stocks/Hong Kong stock data
- U.S. stock historical data and real-time quotes are used uniformly YFinance，to avoid akshare Technical indicator errors caused by abnormal rights restoration of U.S. stocks

### Longbridge（long bridge）
- US stocks/Hong Kong stock data gives the bottom line，supplement YFinance missing ratio、turnover rate、PE etc fields
- Recommended for new users Longbridge official OAuth 2.0：client_id priority use `LONGBRIDGE_OAUTH_CLIENT_ID`，Leave blank and none Legacy Access Token Compatible when used `LONGBRIDGE_APP_KEY`；Execute in interactive environment first `python scripts/generate_longbridge_oauth_token.py --client-id <client_id>` generate SDK token cache
- GitHub Actions / Docker Wait headless The environment cannot wait for browser authorization during the analysis task；This machine can be `~/.longbridge/openapi/tokens/<client_id>` File base64 Later configured as `LONGBRIDGE_OAUTH_TOKEN_CACHE_B64`
- OAuth runtime dependencies SDK provide `OAuthBuilder` / `Config.from_oauth`；If current Linux/Docker The environment can only install old versions SDK，The log will be clearly prompted and automatically skipped Longbridge，does not affect YFinance / AkShare Keep everything in mind
- Legacy API Key Still compatible：settings `LONGBRIDGE_APP_KEY`、`LONGBRIDGE_APP_SECRET`、`LONGBRIDGE_ACCESS_TOKEN`；Among them Access Token It's an old version API Key Voucher，No OAuth access token
- Optional settings `LONGBRIDGE_CONNECTION_COOLDOWN_SECONDS` Controls the number of cool-down seconds after connection closing exceptions（Default 15）
- Access point configurable `LONGBRIDGE_HTTP_URL`、`LONGBRIDGE_QUOTE_WS_URL`、`LONGBRIDGE_TRADE_WS_URL`、`LONGBRIDGE_REGION`
- For the remaining optional parameters, please see the official website [Environment variable description](https://open.longbridge.com/zh-CN/docs/getting-started#environment variables)
- only in YFinance（US stocks）or AkShare（Hong Kong stocks）Automatically triggered when the returned data is incomplete，does not affect A stock link
- The optional data source will not be instantiated when credentials are not configured；If a connection closing exception occurs during runtime，Will be temporarily skipped during the cool-down period Longbridge，Avoid frequent reconnections at the request level

### What to do when Dongcai interface fails frequently

If the log appears `RemoteDisconnected`、`push2his.eastmoney.com` Connection is closed etc.，Most of them are restricted by Dongcai。Suggestions：

1. in `.env` Medium settings `ENABLE_EASTMONEY_PATCH=true`
2. will `MAX_WORKERS=1` Reduce concurrency
3. If configured Tushare，Priority available Tushare data source

---

## Advanced features

### Hong Kong stocks support

Use `hk` Prefix specifies Hong Kong stock code：

```bash
STOCK_LIST=600519,hk00700,hk01810
```

The daily line of Hong Kong stocks will skip efinance、pytdx、baostock Wait for data sources that do not support Hong Kong stock daily lines，Avoid mismatching Hong Kong stock codes to non-Hong Kong stock markets；Default redirection AkShare/Tushare/YFinance/Longbridge Waiting for the path of Hong Kong stocks to continue to bottom out。

### ETF and index analysis

For index tracking ETF and U.S. stock indexes（Such as VOO、QQQ、SPY、510050、SPX、DJI、IXIC），The analysis only focuses on**Index trend、tracking error、market liquidity**，Not included in fund managers/Issuer Company Level Risks（litigation、Reputation、Changes in senior management, etc.）。Risk alerts and performance expectations are based on the overall performance of index constituents，Avoid misjudgment of fund company news as negative for the underlying itself。See details Issue #274。

### Multiple model switching

Configure multiple models，System automatically switches：

```bash
# Gemini（main force）
GEMINI_API_KEY=xxx
GEMINI_MODEL=gemini-3.1-pro-preview

# OpenAI Compatible（alternative）
OPENAI_API_KEY=xxx
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-v4-flash
# deepseek-chat / deepseek-reasoner Still compatible，But it has been officially marked as 2026/07/24 later abandoned
```

### Advanced model routing（The bottom layer consists of LiteLLM drive）

See details [LLM Configuration Guide](LLM_CONFIG_GUIDE.md)。By default you only need to understand the main model、Alternative models and model channels；If you enter this section，Indicates that you want to use the bottom layer directly [LiteLLM](https://github.com/BerriAI/litellm) routing capability，No need to start separately Proxy service。

**Two-tier mechanism**：Many of the same model Key rotation（Router）With cross-model downgrade（Fallback）Layered independent，Do not interfere with each other。

**Much Key + Cross-model downgrade configuration example**：

```env
# master model：3 a Gemini Key rotation，any 429 time Router Automatically switch to next Key
GEMINI_API_KEYS=key1,key2,key3
LITELLM_MODEL=gemini/gemini-3.1-pro-preview

# Cross-model downgrade：All main models Key When both failed，try in order Claude → GPT
# Need to configure the corresponding API Key：ANTHROPIC_API_KEY、OPENAI_API_KEY
LITELLM_FALLBACK_MODELS=anthropic/claude-sonnet-4-6,openai/gpt-5.4-mini
```

**expected behavior**：For first request `key1`；If 429，Router Use it next time `key2`；If 3 a Key None available，then switch to Claude，If it fails again, switch to GPT。

> ⚠️ `LITELLM_MODEL` must contain provider prefix（Such as `gemini/`、`anthropic/`、`openai/`），
> Otherwise the system cannot identify which group should be used API Key。old format `GEMINI_MODEL`（no prefix）Only for unconfigured `LITELLM_MODEL` automatic inference when。

**Dependency description**：`requirements.txt` Reserved `openai>=1.0.0`，Because LiteLLM internal dependencies OpenAI SDK as a unified interface；Explicit retention ensures version compatibility，Users do not need to configure separately。

**visual model（Extract stock code from image）**：See details [LLM Configuration Guide - Vision](LLM_CONFIG_GUIDE.md#41-vision-Model picture to identify stock code)。

Extract stock ticker from image（Such as `/api/v1/stocks/extract-from-image`）Access using the unified vision model，The bottom layer adopts LiteLLM Vision with OpenAI `image_url` Format，support Gemini、Claude、OpenAI、DeepSeek Wait Vision-capable model。Return `items`（code、name、confidence）and compatible `codes` array。

> Compatibility Notes：`/api/v1/stocks/extract-from-image` Respond to the original `codes` Added based on `items` Field。If the downstream client uses strict JSON Schema and does not accept unknown fields，Please update simultaneously schema。

**Smart import**：except pictures，Also supports CSV/Excel File and clipboard pasting（`/api/v1/stocks/parse-import`），Automatically parse code/name column，Name→Code parsing supports local mapping、Pinyin matching and AkShare online fallback。Depend on `pypinyin`（pinyin matching）and `openpyxl`（Excel parse），Already included in `requirements.txt` in。

- **AkShare Name resolution cache**：Name→Code analysis uses AkShare online fallback time，Result caching 1 hours（TTL），Avoid frequent requests；It will be automatically refreshed after the first call or cache expiration.。
- **CSV/Excel List**：support `code`、`Stock code`、`code`、`name`、`Stock name`、`Name` Wait（Not case sensitive）；When there is no header, the default number is 1 Column as code、No. 2 column name。
- **Common parsing failures**：File too large（>2MB）、Coding is not UTF-8/GBK、Excel Worksheet is empty or damaged、CSV delimiter/When the number of columns is inconsistent，API Specific error messages will be returned。

- **Model priority**：`VISION_MODEL` > `LITELLM_MODEL` > According to existing API Key inference（`OPENAI_VISION_MODEL` Deprecated，Please use instead `VISION_MODEL`）
- **Provider rollback**：When the main model fails，press `VISION_PROVIDER_PRIORITY`（Default `gemini,anthropic,openai`）Automatically switch to next available provider
- **The main model does not support Vision time**：If the main model is DeepSeek Wait for non Vision model，Explicitly configurable `VISION_MODEL=openai/gpt-5.5` or `gemini/gemini-3.1-pro-preview` For image extraction
- **Configuration verification**：If configured `VISION_MODEL` But no correspondence is configured provider of API Key，When starting, it will output warning，Image extraction functionality will not be available

### debug mode

```bash
python main.py --debug
```

Log file location：
- General log：`logs/stock_analysis_YYYYMMDD.log`
- debug log：`logs/stock_analysis_debug_YYYYMMDD.log`

The debug log keeps the project itself by default DEBUG information，but will LiteLLM The internal log is pushed down to `WARNING`，Avoid pressing during streaming build token Write large amounts of third-party debug logs；If you need to troubleshoot LiteLLM interior details，Available at `.env` Temporary settings in `LITELLM_LOG_LEVEL=DEBUG`。

### SQLite Write steady state configuration

Default file type SQLite Will be enabled when connection is established `WAL` and set `busy_timeout`，`save_daily_data()` has also been changed to press `(code, date)` batch atomic upsert，To reduce lock contention during batch updates and concurrent writebacks。

If necessary adjustment，Available at `.env` Medium settings：

| variable | Default value | Description |
|------|-------|------|
| `SQLITE_WAL_ENABLED` | `true` | File type SQLite Whether to enable `journal_mode=WAL` |
| `SQLITE_BUSY_TIMEOUT_MS` | `5000` | SQLite Waiting for lock timeout（milliseconds） |
| `SQLITE_WRITE_RETRY_MAX` | `3` | encounter `database is locked` / `database table is locked` The maximum number of retries when |
| `SQLITE_WRITE_RETRY_BASE_DELAY` | `0.1` | Write retry base backoff time（seconds，Increasing by exponential backoff） |

---

## Analyze decision-making operability

The operation recommendations of individual stock reports will be combined with support levels、pressure level、Quantity/chips、Calibrate main capital flows and risk events，Avoid buying or selling stocks just because of a single day's rise or fall or the score crossing the line.“Buy/sell”Switch violently between。If the price is between support and pressure and the flow of funds is unclear，Reports will be given first“hold、Wait and see in shock、Washing dishes and observing”Neutral executable recommendations；Only close support confirmed、Effectively break through pressure and volume and price/The buy-in will only be given when funds are matched，Sell is issued only when it falls below key support or main funds continue to flow out./Reduce positions。
This adjustment will affect the runtime placement of actionable decisions and the prompt word constraint link.，but do not change LLM model、LiteLLM routing、Provider/Key and its compatibility boundaries，Does not affect configuration saving/Clean up semantics。
Compatibility verification conclusion：In addition to configuration and model-side semantics，The decision stability link covers `src/analyzer.py`、`src/core/pipeline.py`、`src/core/backtest_engine.py`、`src/report_language.py` and `src/agent` Runtime behavior of decision paths，It is recommended that the review report decision type mapping be linked to the backtest entrance。
Verification path：The relevant logic is in the above runtime path and corresponding test（`tests/test_backtest_engine.py`、`tests/test_analyzer_news_prompt.py`、`tests/test_decision_stability.py`、`tests/test_agent_pipeline.py` Wait）Effective in；Not here `src/config.py`、`src/report.py`、storage/Added new configuration fields or cleanup logic to the persistence link。

### Recommended action Taxonomy（#1390 P0）

Individual stock reports are on hold `operation_advice` Free text at the same time，Add optional `action` / `action_label` Field，as Web History list、Same stock history、StockBar and structured display assistance for backtest result rows。`decision_type` still keep the old `buy|hold|sell` Three-state statistical caliber；`action` When empty, the existing `decision_type` inference chain。

| `action` | common source text | `decision_type` bridge |
| --- | --- | --- |
| `buy` | `strong_buy`、`Strong buy`、`Buy`、`Layout`、`Open a position` | `buy` |
| `add` | `add`、`Add to position`、`Overweight`、`accumulate` | `buy` |
| `hold` | `hold`、`hold`、`hold observation`、`Washing dishes and observing` | `hold` |
| `watch` | `watch`、`wait and see`、`wait`、`wait` | `hold` |
| `reduce` | `reduce`、`Reduce positions`、`trim` | `sell` |
| `sell` | `sell`、`sell`、`Clearance`、`strong_sell`、`Strong Sell` | `sell` |
| `avoid` | `avoid`、`Avoid`、`avoid`、`Not recommended to buy`、`avoid buying`、`do not buy` | `hold` |
| `alert` | `alert`、`Risk warning`、`Be alert`、`trigger alarm`、`risk alert` | `hold` |

of the above table `decision_type` Bridge only explains eight states action Compatibility with the old three-state statistical caliber；#1390 P0 won't `action` Automatically reverse writing to existing `decision_type`。If the upstream explicitly `action` with `decision_type` exist simultaneously but have inconsistent semantics，three-state statistics、Backtesting and old report calibers are still based on `decision_type` / The original inference chain shall prevail，`action/action_label` Only responsible for structured presentation assistance。

Unknown or ambiguous suggestions will not be answered `watch` or `hold`，Instead it returns empty `action/action_label`。Web history cards、StockBar、Same stock history drawer and backtest results row will be missing in old records `action/action_label` time from `operation_advice` Do demonstration level fallback；the fallback Only affects frontend tags，Not equivalent to stability API action or subsequent signal assets。Web The display layer receives at the same time `action` with `action_label` time，Priority will be given to the current interface language from `action` Generate tags；API in `action_label` Still generated in report language，for non-existence Web client or none `action` Compatible display usage of。Market reviews and other non-individual stock reports will not generate transactions `action`，only keep `operation_advice` text。`dashboard.phase_decision.immediate_action` Belongs to market stage guardrail report field，Not participating #1390 P0 eight states action derived；The final market stage still comes from `report.meta.market_phase_summary.phase`。

#1390 P0 Will not tile subsequent signal asset fields to existing summary、History list、StockBar or backtest response。#1390 P1 start by independence `DecisionSignal` Resource undertaking `horizon`、`plan_quality`、`status` Wait for more fine-grained planning fields，Still do not change the existing reporting master contract、No backfill history、No new configuration items。

### Decision signaling assets（#1390 P1/P2/P3/P4/P5）

`DecisionSignal` Is an independent backend resource，used to put AI It is recommended that precipitation be queryable、Can remove duplicates、Signal assets with updateable state。it does not replace `operation_advice`、Not extended `decision_type=buy|hold|sell`。#1390 P2 start，Common stock analysis and Agent Individual stock analysis after the analysis history is successfully saved，will eventually `AnalysisResult` best-effort Extract one `source_type=analysis` signal；explicit API or service The call remains。

Automatic extraction consumes only structured fields from generated reports，No reparsing Markdown，No backfilling of old history either、No new configuration items、Do not change the reporting master contract。Failed to extract、Suggested action is unknown or ambiguous、Non-individual stock reports、Writing is skipped when market is not recognized，Does not affect the storage of analysis reports。`source_report_id` Use the one you just saved `AnalysisHistory.id`；`trace_id` Prioritize running diagnostics trace，Downgrade to when missing pipeline trace or `query_id`；`stock_name` from `AnalysisResult.name`；`trigger_source` from run entry，When missing, it is `system`。

P2 Automatically extracted market stages are read first in the saved snapshot `market_phase_summary.phase`，Next read `AnalysisResult.market_phase_summary.phase`；Data quality prioritizes reading in saved snapshots `analysis_context_pack_overview.data_quality`，Next read `AnalysisResult.analysis_context_pack_overview.data_quality`。Price plan reuses sniper point analysis rules saved in history，from `dashboard.battle_plan.sniper_points.ideal_buy/secondary_buy/stop_loss/take_profit` mapped to `entry_low/entry_high/stop_loss/target_price`；only `ideal_buy` write when `entry_low`，only `secondary_buy` write when `entry_high`，When both exist at the same time, they are sorted by effective price as `entry_low <= entry_high`。Missing stop loss or price target will only lower service automatically calculated `plan_quality`，Can't make up fields。`watch_conditions` Read first `dashboard.phase_decision.watch_conditions`，Read only if there is none `dashboard.battle_plan.action_checklist`；`catalyst_summary` only in `dashboard.intelligence.positive_catalysts` Write if exists and is a list。`confidence` Conservative mapping from report confidence level：`high/high=0.8`、`in/medium/mid=0.6`、`low/low=0.4`，The original confidence level is retained at `metadata`。

P3 start，The life cycle consists of `DecisionSignalService` Completion in a unified way：passed in explicitly `horizon` / `expires_at` Always priority；Not passed on `horizon` time，`alert` or `premarket/intraday/lunch_break/closing_auction` Default `intraday`，`postmarket/non_trading/unknown` Or default when there is no stage context `3d`；Not passed on `expires_at` time，`intraday` Read first `metadata.market_phase_summary.minutes_to_close/minutes_to_open`，Use determinism without context TTL fallback（A shares 4h、Hong Kong stocks 5.5h、US stocks 6.5h、unknown 4h），`1d/3d/5d/10d` According to calendar day，`swing/long` Does not automatically expire。fallback TTL Just a downgrade strategy when trading calendar context is missing，Not equivalent to the actual exchange closing time。Automatically extract only `market_phase_summary.phase/session_date/minutes_to_open/minutes_to_close` as hypoallergenic hint write `metadata.market_phase_summary`，eventually `horizon/expires_at` still by service Calculate。

Core fields include `stock_code`、`stock_name`、`market`、`source_type`、`source_agent`、`source_report_id`、`trace_id`、`market_phase`、`trigger_source`、`action`、`action_label`、`confidence`、`score`、`horizon`、`entry_low`、`entry_high`、`stop_loss`、`target_price`、`invalidation`、`watch_conditions`、`reason`、`risk_summary`、`catalyst_summary`、`evidence`、`data_quality_summary`、`plan_quality`、`status`、`expires_at`、`created_at`、`updated_at` and `metadata`。`action` Reuse eight-state suggested actions；`market_phase` Reuse market stage enumeration；`source_type` support `analysis|agent|alert|market_review|manual`；`status` support `active|expired|invalidated|closed|archived`；`horizon` support `intraday|1d|3d|5d|10d|swing|long`。

`confidence` for `0.0-1.0`，`score` for `0-100`，with historical reporting `sentiment_score` decoupling。Price Plan Field `entry_low`、`entry_high`、`stop_loss`、`target_price` Must be a finite positive number，and passed in at the same time `entry_low` and `entry_high` time requirements `entry_low <= entry_high`。`plan_quality` support `complete|partial|minimal|unknown`：When the caller explicitly passes in a legal value, it is saved directly.；Unpublished date service Calculate，Entry range（`entry_low` or `entry_high` Any value）Calculate 1 item，`stop_loss`、`target_price`、`invalidation`、`watch_conditions` Each counts 1 item，satisfy 2 The item is `partial`，satisfy 4 Items and above are `complete`，only action/reason for `minimal`。

New API：

- `POST /api/v1/decision-signals`：Create or press the same origin key to remove duplicates，Return `{ item, created }`，HTTP 200。The precise deduplication key is `(source_report_id, source_type, market, stock_code, action, horizon, market_phase)`；No report But there is `trace_id` used when `(trace_id, source_type, market, stock_code, action, horizon, market_phase)`；If you don’t have both, don’t ignore it.。After exact match fails，Will press the same source + `source_type/market/stock_code/action` make narrow relaxed fallback，Only fill old records that are empty `horizon/market_phase`，and `horizon` Only if the new value consists of service By default, it can be filled only when it is generated；Explicitly keep multiple entries with different deadlines or different stages.。If hit the same origin expired record，and the new request is active and carry the future `expires_at`，The record will be refreshed in place and returned `created=false`，This renewal is based on the new active Activate event handling。active Create new or expired after renewal bullish signal（`buy/add`）will be earlier active defensive signal（`reduce/sell/avoid`）marked as `invalidated`，Reverse empathy；active duplicate retry The failure fix will also be rerun.，To restore the last created successfully but failed to write the invalid partial create；plain old duplicate/replay Not used as a new activation event。`hold/watch/alert` Does not trigger automatic invalidation。API response schema unchanged，Refresh or repeated hits will be returned externally. `created=false`；This feature does not provide concurrent uniqueness guarantees。
- `GET /api/v1/decision-signals`：Page query，support `market`、`stock_code`、`action`、`market_phase`、`source_type`、`source_report_id`、`trace_id`、`trigger_source`、`status`、time range、`holding_only`、`account_id`。
- `GET /api/v1/decision-signals/{signal_id}`：Query single item，does not exist return 404。
- `PATCH /api/v1/decision-signals/{signal_id}/status`：Update legal status and optional `metadata`；incoming `metadata` Press the whole package to replace and save。`expired/invalidated/closed/archived` Wait terminal The status cannot be directly PATCH return `active`，expired Renewal can still only be done again `POST` active + future `expires_at`。
- `GET /api/v1/decision-signals/latest/{stock_code}`：Check the latest by stock active signal，Default `limit=1`。

Reading entries will expire lazily：list、details and latest Arrivals will be sent before enquiry. `expires_at` of active The signal is labeled expired；Expired when created active The signal will be saved directly as expired；Homology expired The signal can only be passed through the re- `POST` active + future `expires_at` way to extend，`PATCH /status` Not accepted `expires_at`。`expired|invalidated|closed|archived` will not be PATCH direct resurrection，`closed|invalidated|archived` Nor will it be create path resurrection。On the contrary, the signal will automatically expire and the old signal will be merged and written. `metadata`：`invalidated_by_signal_id`、`invalidated_reason`、`invalidated_at`、`previous_status`；old metadata JSON When damaged, it will be replaced by an invalid one. metadata and write `metadata_replaced_due_to_invalid_json=true`，Do not block new signal creation。time field press UTC Normalize to no time zone `datetime` Save and compare；Input with time zone will first be converted to UTC Remove later `tzinfo`，No time zone input button UTC Process，API The response continues to return without the time zone suffix ISO string。Stock code storage and query button `market` deterministic normalization：A shares `600519`、`SH600519`、`600519.SH` Common variants are matched by the same code；Hong Kong stocks `00700`、`HK00700`、`00700.HK` press `HK00700` match；US stocks ticker Unified capitalization。`holding_only=true` read only active under account `portfolio_positions` in `quantity > 0` Cache positions，and press position `(market, stock_code)` match signal，Optional active `account_id`；This query does not call the combination snapshot replay，Returns empty results when no cache is available，Need to pass first portfolio snapshot API refresh cache。

`source_report_id` Can be empty and does not force verification of the existence of history records；Only explicitly clean up when deleting history `source_type=analysis` and `source_report_id` hit actual delete ID historical binding signal，`manual/agent/alert/market_review` Waiting for a weak reference signal will not occur simply because ID Collisions are removed；The list interface supports pressing `source_report_id` and `trace_id` do typed filter。`task_id`、`alert_trigger_id` Wait for subsequent related fields to be put in first `metadata`，P1 Do not add independent columns，Not available either typed filter，In the subsequent linkage stage, it will be upgraded to an independent contract.。JSON Field、Long text fields and presentational short text fields（`stock_name/source_agent/trigger_source/action_label`）Signal-specific desensitization is performed before writing，coverage sensitive key、Bearer、Authorization/Cookie header or assignment、token-like string、Other sensitive assignments、webhook URL、URL userinfo and sensitive query/fragment parametric URL；ordinary evidence URL Will be retained to ensure traceability of origin，And diagnostic text will not be applied to long text. 300 character truncation。`trace_id` Is the same source deduplication identity field，If it contains sensitivities that will be desensitized credential，API Will reject the request instead of saving lossy redaction value after。

These interfaces inherit the existing `/api/v1/*` Administrator authentication：`ADMIN_AUTH_ENABLED=true` Must carry a valid administrator session when Cookie；This function does not add an independent authentication method。

#1390 P4 in Web End access already exists `DecisionSignal` API，No new backend contract、Database table or configuration item。sidebar“AI Suggestions”entrance `/decision-signals` It is a centralized query entrance for structured decision-making signals.，Default display `status=active` signal，and support by market、Stock code、action、market stage、Source、source report ID and status filter；The page also provides the latest query by stock code active signal entrance。Signal details display action、Confidence/Rating、horizon、plan_quality、market_phase、price plan、risk、Observation conditions、Source reporting and data quality；Web Only signals marked as `closed`、`invalidated` or `archived`，Not available terminal The status is restored to active。

#1390 P5 Added signal level feedback、Posterior evaluation and statistics sidecar，Not extended `decision_signals` main table，No reuse of bindings `analysis_history_id` of `BacktestResult`。`decision_signal_feedback` press `signal_id` Save latest `useful|not_useful` feedback、Optional reason/Notes and sources；`decision_signal_outcomes` press `(signal_id, horizon, engine_version)` Idempotent storage of posterior results，current `engine_version=decision-signal-v1`。Outcome Freeze while evaluating `action/market/market_phase/source_type/source_agent/plan_quality/data_quality_level/holding_state` Equal statistical dimensions，Historical statistics do not rely on follow-up live join rewrite。When deleting historical reports，Will find out first `source_type=analysis` And the binding was deleted history ID signal，Then clean up the correspondence feedback/outcome Subtable。

P5 Posterior evaluation only supports daily verifiable ones. `1d/3d/5d/10d`，The window semantics are anchor after 1/3/5/10 root `StockDaily` transaction bar，Not reused `DecisionSignalService._horizon_days()` Natural day expiration semantics。`anchor_date` Read first `metadata.market_phase_summary.session_date`，Otherwise use `created_at.date()`；anchor Must exist on the day `StockDaily.close`，There will be no rollback to the previous trading day。The action is mapped to `buy/add -> up`、`hold -> not_down`、`reduce/sell/avoid -> not_up`；`watch/alert`、`intraday/swing/long`、missing anchor price、forward bars If it is insufficient, it will be written `eval_status=unable` and clear `unable_reason`。missing anchor price、illegal anchor price、forward bars Insufficient、missing/The illegal window closing price is recoverable unable，Subsequent default reruns will be re-evaluated after the data is completed.；non-directional action、Not supported horizon and lack anchor date Belongs to the final state unable，Keep idempotent skipping by default。Automatic extraction runtime can receive additional `portfolio_context.quantity`，Only treat hypoallergenic `holding_state=holding|empty|unknown` write metadata For use with posterior snapshots，Do not save quantity、account or cost。

P5 in Web `/decision-signals` The current page is displayed below the page filter area. outcome engine overall stat card；The details drawer reads this signal on demand outcomes，and can submit useful/not useful feedback。This page does not add a new navigation page，Do not enter BacktestPage，No new background scheduled tasks are added either.；The posterior calculation is given by `POST /api/v1/decision-signals/outcomes/run` explicit trigger。The default priority of batch running is missing outcome signal，Try again to recover unable，Will not make completed or final state unable The latest signal is long occupied `limit`。

The position page will display AI Recommended as non-blocking enhanced asynchronous loading：The combined snapshot and risk modules are first rendered according to the original logic，Then called by the only position in the current snapshot `GET /api/v1/decision-signals/latest/{stock_code}?market=<market>&limit=1` Query latest active signal；no longer passed `holding_only=true` Generic list paging scan，There is also no fixed page number truncation。single position latest When query fails，Page retains other loaded signals and displays visible degradation prompts；When there is no matching signal, the position line displays an empty space.。Match logic multiplexing Web Terminal stock code equivalence rules，Cover A shares `600519/SH600519/600519.SH`、Hong Kong stocks `00700/HK00700/00700.HK` and U.S. stocks ticker。

#1390 P6 will `DecisionSignal` Reuse to alarm、Notice and Portfolio Risk，No new table、Migrate or configure。When a real stock-level alarm is triggered, it will be associated with the same target first. latest active signal，and treat hyposensitivity `decision_signal_summary` write `alert_triggers.diagnostics`；No active signal time，worker Create only the smallest `source_type=alert`、`action=alert` signal，`trace_id=alert-rule-<hash>` Only used for same-origin retries best-effort Idempotent deduplication，Not covered active Signal ontology，And don’t write `market_phase` Avoid duplication across stages。Alarm notifications and analysis notifications only quote the `action/horizon/reason/watch_conditions/risk_summary/source_report_id` Wait for public fields，Notification failure does not affect trigger or signal write。`GET /api/v1/portfolio/risk` Append `decision_signal_risk` aggregate block，Only counts current positions active `sell/reduce/alert` signal，expressly excluded `avoid/buy/add/hold/watch`；Risk interface when signal query fails fail-open，Web Risk area shows degraded status。

#1390 P7 For the closing document, see [DecisionSignal Special Topic on Decision Signals](decision-signals.md)。P7 No new addition `DECISION_SIGNAL_*` Configuration、database migration、API Field or runtime switch；The current rollback method is revert Corresponding code。Signal extraction and writes stop after rollback，Save existing reports、Alarm trigger、The main process of sending notifications and combining risks continues to run without relying on the signal pool.；history signal、feedback and outcome Data is not automatically cleaned。

The details of ordinary stock historical reports are no longer displayed inline. `source_type=analysis` signal，Nor will it be initiated by opening report details `source_report_id=<recordId>` signal query；Need to see structured AI Unified entry when recommended `/decision-signals` Page Filter Source Report ID、open `/decision-signals?sourceReportId=<recordId>` deep link，Or search by stock。Fill out the source report ID or use this URL parameter，Web Will initiate `source_type=analysis + source_report_id=<recordId>` Exact query，No overlay by default `status=active` Wait for other lists to filter，to keep old reports best-effort Lazy backfill semantics。

## Backtest function

The backtesting module automatically tests history AI Analyze records for post-mortem verification，Evaluate the accuracy of analytical recommendations。

### Working principle

1. Select the cool-down period that has expired（Default 14 day）of `AnalysisHistory` record
2. Get daily data after the analysis day（forward K line）
3. Infer the expected direction based on operational recommendations，Compare with actual trend
4. Evaluate take profit/Stop loss hit situation，Simulated execution income
5. Summarized into performance indicators in two dimensions: overall and individual stocks.

### Action suggestion mapping

| Operation suggestions | Position inference | expected direction | Victory conditions |
|---------|---------|---------|---------|
| Buy/Add to position/strong buy | long | up | Increase ≥ neutral zone |
| sell/Reduce positions/strong sell | cash | down | Decline ≥ neutral zone |
| hold/hold observation/Wait and see in shock/Washing dishes and observing/hold/hold and watch/range-bound watch/shakeout watch | long | not_down | No significant decline |
| wait and see/wait/wait | cash | flat | Price is within the neutral band |

### Configuration

in `.env` Set the following variables in（All have default values，Optional）：

| variable | Default value | Description |
|------|-------|------|
| `BACKTEST_ENABLED` | `true` | Whether to automatically run backtests after daily analysis |
| `BACKTEST_EVAL_WINDOW_DAYS` | `10` | Evaluation window（Trading days） |
| `BACKTEST_MIN_AGE_DAYS` | `14` | Backtesting only N Records from days ago，Avoid incomplete data |
| `BACKTEST_ENGINE_VERSION` | `v1` | Engine version number，Used to differentiate results when upgrading logic |
| `BACKTEST_NEUTRAL_BAND_PCT` | `2.0` | neutral interval threshold（%），±2% internal shock |

### run automatically

Backtesting is automatically triggered after the daily analysis process is completed（non-blocking，Failure does not affect notification push）。Also available via API manual trigger。

### Evaluation indicators

| indicator | Description |
|------|------|
| `direction_accuracy_pct` | Direction prediction accuracy（The expected direction is consistent with the actual） |
| `win_rate_pct` | winning rate（win / (win+Negative)，Does not contain neutral） |
| `avg_stock_return_pct` | average stock return |
| `avg_simulated_return_pct` | Average simulated execution yield（Exit with stop profit and stop loss） |
| `stop_loss_trigger_rate` | Stop loss trigger rate（Only records with stop loss configured are counted.） |
| `take_profit_trigger_rate` | Take profit trigger rate（Only records with take profit configured are counted.） |

---

## local WebUI Management interface

WebUI with FastAPI API Services share the same service process，Configuration management can be completed in the browser after startup、Manual analysis、View task progress、historical report、backtest、Operations such as position management and intelligent import。Certification、Cloud server access and API See the instructions below for calling details.。

### FastAPI API service

FastAPI provide RESTful API service，Support configuration management and trigger analysis。

### Start mode

| command | Description |
|------|------|
| `python main.py --serve` | start API service + Perform a complete analysis |
| `python main.py --serve-only` | Start only API service，Manually trigger analysis |

### Features

- 📝 **Configuration management** - View/Modify self-selected stock list
- 🧭 **Interface language switching** - Both login and exit states support quick switching of interface languages.（`zh` / `en`），independent from `REPORT_LANGUAGE`，for static UI Copywriting and navigation skeleton
- 🚀 **Quick analysis** - Pass API Interface triggers individual stock analysis；Also available on the home page“Market review”button，Available at Docker/server Trigger market review in the background in mode
- 🎯 **Strategy selection** - Home page supports explicit selection of analysis strategies skill；Not passed on `skills` Run according to system default policy，Facilitates maintaining compatibility with historical behavior
- 🧭 **First time configuration tips** - The homepage will read the read-only configuration status，missing LLM main channel、When selecting stocks and other basic items, a gap will be prompted and guided to enter the system settings.
- 📊 **Real-time progress** - Analysis task status updated in real time，Support multi-tasking parallelism；Ordinary analysis link is entering LLM Will give priority to try after the stage LiteLLM Streaming generation，and pass the task SSE Reinjection is more granular `message/progress`
- 🧪 **AlphaSift The stock picking task can be resumed** - The stock selection page polls the status after submitting the background task.，Switching pages and returning will restore the current task progress or final results.，Avoid external snapshots/Quotes/LLM Loss of feedback when slowing down
- 🗂️ **Market review task visibility** - The home page will return after triggering the market review `task_id` and poll `GET /api/v1/analysis/status/{task_id}`，in progress/Complete/Failure scenarios give visible feedback，In case of failure, the error content is directly revealed.
- 🗂️ **Independent entrance to market review history** - The history of market review is separated from the history of ordinary stocks through a dedicated entrance.；Recommend to pass `stock_code=MARKET` + `report_type=market_review` Directly query and playback large disk review records
- 🧾 **Market review history can be reused** - The market review task will be persisted to the analysis history，`report_type` for `market_review`，Directly through the history list/Open the corresponding details Markdown or details page，Analysis recalculation will not be retriggered
- 🧩 **Input data blocks are visible** - Ordinary analysis reports will be in the historical details、synchronous response and completed Return to hyposensitivity in task status `AnalysisContextPack` overview，Web The report page is collapsed by default after the strategic points and information to display the data block status.、Source、Missing reason and downgrade summary
- 💬 **Asking stocks and asking about the context** - After entering the stock inquiry from the historical report，Subsequent questions will continue to carry the current `stock_code/stock_name`；When switching back or reloading an existing stock session，The base current target will be restored from the loaded historical user messages.；Switch context only when the user explicitly switches the target，Contains comparison/Contrast/vs/difference/Questions such as clear comparison intent or multiple non-current clear stock symbols will not contaminate the current underlying
- 📈 **Backtest verification** - Evaluate historical analysis accuracy，Query direction winning rate and simulated income
- 🔗 **API Documentation** - visit `/docs` View Swagger UI

### Product behavior related to this change

- Web Language status adopts a two-layer mechanism：`dsa.uiLanguage`（Browser persistence）with `REPORT_LANGUAGE`（Report output）decoupling。
  - `dsa.uiLanguage` just decide WebUI Copywriting and navigation language（`zh` / `en`），The value priority is the local persistent value -> Browser language -> Default `zh`。
  - `REPORT_LANGUAGE` Control report text、Stock abbreviation localization and report page fixed copywriting（`zh` / `en` / `ko`）。
- Page language switching to enhance user experience，Does not fall within the scope of regression verification evidence recording；For screenshots and commands please click PR The process is PR Maintained separately in description。
- This change only adds request-level reporting language coverage parameters，Do not change `provider`/`model`/`base_url` Configuration migration and cleanup logic。

### API interface

| interface | method | Description |
|------|------|------|
| `/api/v1/analysis/analyze` | POST | Trigger stock analysis |
| `/api/v1/analysis/market-review` | POST | Trigger market review in the background；The request body can be passed `{"send_notification": true}`；with `main.py --market-review` with `bot` Reuse the same set `GeminiAnalyzer/SearchService/NotificationService` assembly semantics |
| `/api/v1/analysis/tasks` | GET | Query task list |
| `/api/v1/analysis/tasks/stream` | GET (SSE) | Subscribe to task real-time status stream；`task_progress` Optional carry `flow_event` Incrementally run stream events |
| `/api/v1/analysis/tasks/{task_id}/flow` | GET | Query active task A snapshot of the running flow |
| `/api/v1/analysis/status/{task_id}` | GET | Query task status |
| `/api/v1/alphasift/screen/tasks` | POST | Background submission AlphaSift stock picking task（Need to be turned on first `ALPHASIFT_ENABLED`） |
| `/api/v1/alphasift/screen/tasks/{task_id}` | GET | Query AlphaSift Stock selection task status and completion results |
| `/api/v1/history` | GET | Query and analyze history |
| `/api/v1/history/{record_id}/diagnostics` | GET | Query history report run diagnostic summary and desensitized copy text |
| `/api/v1/history/{record_id}/flow` | GET | Query History Report Run Stream Snapshot，common stocks and `MARKET/market_review` Large market review reuses the same contract |
| `/api/v1/decision-signals` | POST | Explicitly create or press the same origin key to deduplicate decision signals，Return `{ item, created }` |
| `/api/v1/decision-signals` | GET | Pagination query decision signal，Support stocks、market、action、stage、Source、Status、time range and cache-only Position filter |
| `/api/v1/decision-signals/outcomes/run` | POST | Explicit trigger signal posterior evaluation，Skip by default completed/final state unable、Recalculation is recoverable unable，`force=true` Recalculation coverage |
| `/api/v1/decision-signals/outcomes` | GET | Paging query signal posterior results |
| `/api/v1/decision-signals/outcomes/stats` | GET | Query the current posterior engine statistics，Exclude by default archived signal |
| `/api/v1/decision-signals/{signal_id}/outcomes` | GET | Query the result of a single signal under the current posteriori engine |
| `/api/v1/decision-signals/{signal_id}/feedback` | GET | Query user feedback for a single signal；Return when no feedback `feedback_value=null` |
| `/api/v1/decision-signals/{signal_id}/feedback` | PUT | Write or update a single signal `useful|not_useful` feedback |
| `/api/v1/decision-signals/{signal_id}` | GET | Query a single decision signal，Perform lazy expiration before reading |
| `/api/v1/decision-signals/{signal_id}/status` | PATCH | Update decision signal status and optional metadata |
| `/api/v1/decision-signals/latest/{stock_code}` | GET | Query the latest specified stocks active decision signal |
| `/api/v1/usage/summary?period=today|month|all` | GET | Summary by call type and model dimensions LLM The number of calls and Token Dosage |
| `/api/v1/usage/dashboard?period=today|month|all&limit=50` | GET | Return Token Usage dashboard data：total amount、Prompt/Completion Split、Model usage、Call type distribution and recent call details；Web Side entrance is left navigation“Dosage” |
| `/api/v1/backtest/run` | POST | Trigger backtest |
| `/api/v1/backtest/results` | GET | Query backtest results（Pagination） |
| `/api/v1/backtest/performance` | GET | Get overall backtest performance |
| `/api/v1/backtest/performance/{code}` | GET | Get single stock backtest performance |
| `/api/v1/stocks/extract-from-image` | POST | Extract stock ticker from image（multipart，timeout 60s） |
| `/api/v1/stocks/parse-import` | POST | parse CSV/Excel/clipboard（multipart file or JSON `{"text":"..."}`，File≤2MB，text≤100KB） |
| `/api/health` | GET | health check |
| `/docs` | GET | API Swagger Documentation |

> Description：`POST /api/v1/analysis/analyze` in `async_mode=false` Only single stocks are supported；batch `stock_codes` Need to use `async_mode=true`。asynchronous `202` Response is returned for a single stock `task_id`，Return to batch `accepted` / `duplicates` summary structure。
> Description：`POST /api/v1/analysis/analyze` Support use `skills` Incoming policy skill ID list；If it is not passed, it will be executed according to the default policy of the server.。Called for compatibility history，`strategies` Fields remain as compatible aliases。
> Description：`POST /api/v1/analysis/analyze` support `analysis_phase=auto|premarket|intraday|postmarket`，Default `auto`。Not `auto` Only covers the current analysis stage and derivation stage markers，Does not rewrite the real trading calendar time；accepted response、memory task status、task list and SSE Will echo the request phase，The final reporting stage begins with `report.meta.market_phase_summary.phase` Subject to。
> Description：`POST /api/v1/analysis/analyze` support `report_language=zh|en|ko`，and compatible `reportLanguage` as an alias；Fall back to global when not transmitted `REPORT_LANGUAGE`（or in the environment `Config.report_language`）。This field only affects the report text for this analysis、`report.meta.report_language` and persistent display，Will not be persisted as runtime configuration。
> Description：Web The policy drop-down on the side homepage is an explicit optional policy entry。Will not be carried unless the user manually selects it `skills`，Consistent with historical client behavior；After selecting the strategy, it will be transparently transmitted to the interface and retained in the task status and historical snapshots.。
> Description：`POST /api/v1/analysis/market-review` Using a backend with CLI/Bot shared configuration path（`GeminiAnalyzer(config=...)` Search with same/Prompt word construction entrance）。Provider Compatible routes will be identified and used first `litellm_model`、`llm_model_list`，Fallback if not configured legacy `GEMINI_*`、`OPENAI_*`、`ANTHROPIC_*`、`DEEPSEEK_*` key；Will not be added/adjust provider、Base URL or LiteLLM routing semantics。
> Description：`POST /api/v1/analysis/market-review` additional support `report_language=zh|en|ko`（Support aliases `reportLanguage`）。If it is not transmitted, it will also fall back to the global `REPORT_LANGUAGE`。This parameter only affects the language-related content in the text of this review report and the structured return field.；Bot、schedule、CLI or button triggered `main.py --market-review` Still use global configuration，No new request-level coverage capabilities are added。
> Description：`POST /api/v1/analysis/market-review` Yes Web / Desktop manual trigger entry，After clicking, the task of reviewing the market will be submitted directly.，not because of `TRADING_DAY_CHECK_ENABLED=true` Or the relevant market is closed that day and the short-circuit is skipped.；scheduled tasks、GitHub Actions Manually run and CLI The default entry still follows the trading day check，Available `--force-run` or workflow `force_run` Cover。
> Audit basis：Priority and fallback semantics are based on `src/config.py` of `Config._load_from_env()` Subject to（`LITELLM_CONFIG` > `LLM_CHANNELS` > legacy）。See you when the package comes back `tests/test_llm_channel_config.py`（Configure source resolution）with `tests/test_market_review_runtime.py`（Shared assembly paths）。This interface currently only provides single-process/Single-machine level anti-duplication capability，For multi-instance deployment, global idempotence needs to be completed through external task queues or distributed locks.。
> Description：`POST /api/v1/analysis/market-review` After triggering，The report will be based on `report_type=market_review` Write to history database；You can inquire directly `/api/v1/history` or `/api/v1/history/{record_id}` Get history Markdown，Avoid triggering analysis recalculation again。
> Description：History list added `report_type` query parameters；Pass `stock_code=MARKET&report_type=market_review` Large disk review history collection can be read separately，Completely isolated from the historical logic of ordinary stocks。
> Description：`POST /api/v1/analysis/market-review` The return and historical persistence will include `market_review_payload`：`market_scope`、`sections`、`sectors`、`concepts`、`news`、`market_light`、`indices` Structured fields。Web end Markdown Rendering and history details will reuse this structured field；If the structured field is empty, fall back to the original Markdown。
> Description：Running the stream snapshot interface returns `lanes/nodes/edges/events/summary` unified compact。active task missing diagnostics return when skeleton flow；If the task SSE True received `flow_event`，The snapshot will contain the most recent incremental events。completed history priority use `context_snapshot.diagnostics` with `analysis_context_pack_overview` Build a complete topology。`cancel_requested/cancelled` is legal status，will not be mapped to failed。
> Description：`market_review_payload` in `breadth` It will only be issued when the market width data is actually available.；When US stocks/This field will not be issued when Hong Kong stocks or interfaces are temporarily unavailable.。The front-end display layer needs to press“Field missing”downgraded to“No data yet”instead of showing 0。
> Description：If this endpoint returns `task_id`，WebUI Will poll `GET /api/v1/analysis/status/{task_id}` display status。The status is `completed` Give completion prompt when（Report generated and pushed as configured），The status is `failed` When displayed in the front-end error area `error` Reason。
> Description：`GET /api/v1/history/{record_id}/diagnostics` Support history primary key ID or `query_id`，Return `normal/degraded/failed/unknown` Summary、Critical link components and replicable desensitization `copy_text`；Returned when old reports are missing diagnostic snapshots `unknown`，Does not affect report reading。
> Description：`GET /api/v1/history` The list summary can be pressed `stock_code` Query the same stock history by page，and return to trend judgment、Analysis summary、Model name and price during analysis/Optional fields such as increase or decrease；Returns null when old record is missing snapshot field。Web report page“historical trends”The drawer reuses this interface to load the history of the same stock.。
> Description：`GET /api/v1/usage/dashboard` Reuse `llm_usage` audit table，No new configuration items or database migration。The interface only returns the number of calls that have been dropped into the library、Prompt/Completion/Total Token aggregation、Model dimension usage and recent call records，Do not derive the model context window or provider metadata。
> Description（Issue #1520）：The model name display field in the list only comes from the historical snapshot `model_used`，Only for historical review display，Does not affect runtime model model routing（`litellm_model`、`llm_model_list`）、Provider、Base URL Migrating with configuration/Clean up semantics。The rollback method is to roll back this submission，Current network history query/drawer/Interface link compatibility remains unchanged。
> Description：historical details、Synchronous analysis of responses and completed The task status will be in `report.details.analysis_context_pack_overview` Returns a block of low-sensitivity input data overview；The synchronous analysis response relies on the persistence this time `analysis_history.context_snapshot`，`SAVE_CONTEXT_SNAPSHOT=false` The latest records are not guaranteed to be returned overview。`details.context_snapshot` will strip the top-level field，Do not return complete `AnalysisContextPack` or Prompt summary。
> Description：`POST /api/v1/agent/chat` with `POST /api/v1/agent/chat/stream` The front end will be passed in `context.stock_code` As the baseline for the current target of the stock being asked，But the server will re-determine first stock scope。The front-end will continue to send the information after entering the stock inquiry from the historical report. active stock context；When switching back or reloading an existing session，The basis will be restored based on the loaded historical user messages. `{stock_code, stock_name: null}`。The server will re-determine in each round of messages `maintain` / `switch` / `compare`：When switching is not explicit，bring `stock_code` Stock tool calls can only access the current underlying；Explicit switching will clean up historical summaries and prefetch data for old bids；Contains comparison/Contrast/vs/difference/Questions such as clear comparison intent or multiple non-current clear ticker symbols allow for multiple tickers that are clear to appear in this round，but does not overwrite the current target。If the model mistakenly TTM、PE、MACD、KDJ financial abbreviations、In the context of moving averages `MA` indicator words，or SH/SZ/BJ/HK/SS Wait for the exchange fragment to be used as a stock code calling tool，The backend will return non-retryable `stock_scope_violation` Tool results，The corresponding stock instrument will not be executed。Toolname only resolves the exact name in the registry；any provider namespace or suffix None will be routed to existing tools。
> Description：`POST /api/v1/backtest/run` New `analysis_date_from` / `analysis_date_to`（`YYYY-MM-DD`）Request parameters used to filter candidates by historical analysis date；If `analysis_date_from > analysis_date_to`，interface return 400 `invalid_params`。
> Description：When the backtest is executed successfully but there are no new storage results，`BacktestRunResponse.message` Returns a human-readable diagnostic description，`diagnostics` Return to troubleshooting context（Example：`empty_reason`、`analysis_date_from`、`analysis_date_to`、`eval_window_days`、`min_age_days`、`limit`）。
> Description：`GET /api/v1/backtest/results`、`GET /api/v1/backtest/performance`、`GET /api/v1/backtest/performance/{code}` Sync support `analysis_date_from`、`analysis_date_to`；Keep historical behavior when not passed。

> Compatibility audit evidence：
> - official source：LiteLLM OpenAI-compatible provider Documentation <https://docs.litellm.ai/docs/providers/openai_compatible>；OpenAI Chat API Documentation <https://platform.openai.com/docs/api-reference/chat/create>；DeepSeek API Documentation <https://api-docs.deepseek.com/>。
> - Dependency version：The project constraints are `litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0`（see `requirements.txt`），The above compatible semantic regression tests are executed within this version window。
> - Reviewable testing：
>   - `tests/test_llm_channel_config.py`（Configure source priority and provider/base url mapping）
>   - `tests/test_market_review_runtime.py`（`build_market_review_runtime` Reuse assembly paths）
>   - `tests/test_analysis_api_contract.py`（`/api/v1/analysis/market-review` Contract and task status link）
> - rollback/rollback：If there is a problem with the new path，You can restore history first `LITELLM_MODEL`、`LITELLM_FALLBACK_MODELS` with legacy `GEMINI_*` / `OPENAI_*` / `ANTHROPIC_*` / `DEEPSEEK_*`，Or through desktop backup or with administrator authentication enabled Web end `POST /api/v1/system/config/import` Roll back and restart；Can be temporarily cleared at runtime level `LITELLM_CONFIG` / `LLM_CHANNELS` trigger legacy rollback。

> Progress flow description：`GET /api/v1/analysis/tasks/stream` except `task_created / task_started / task_completed / task_failed` outside，New `task_progress` event。Ordinary analysis links will be in“Quote preparation / news search / Contextualization / LLM generate / report save”Continue to update in stages `progress` with `message`。LiteLLM Streaming returns only accumulate full text on the server side，eventually JSON The historical report will be persisted only after the parsing is successful.；If the stream is in the first chunk Not available before，Will automatically fall back to the original non-streaming call；If part of the chunk failed after，The system first tries the same model non-streaming retry，After failure, press the existing main model again.->Alternate model order to continue trying。  
> If the task progress callback is abnormal，The main link will not be interrupted，The system will raise the alarm to warning level and output the complete exception in the server log，Easy to troubleshoot SSE Push breakpoint。
>  
> Description：This feature belongs to the runtime SSE with fallback link details，Prioritize recording in the complete guide（`full-guide*.md`），Not here `README.md` Expand detailed behavior branches in。

**Call example**：
```bash
# health check
curl http://127.0.0.1:8000/api/health

# Trigger analysis（Ashares）
curl -X POST http://127.0.0.1:8000/api/v1/analysis/analyze \
  -H 'Content-Type: application/json' \
  -d '{"stock_code": "600519"}'

# Transparent transmission strategy（Optional）
curl -X POST http://127.0.0.1:8000/api/v1/analysis/analyze \
  -H 'Content-Type: application/json' \
  -d '{"stock_code": "600519", "skills": ["bull_trend", "growth_quality"]}'

# Query task status
curl http://127.0.0.1:8000/api/v1/analysis/status/<task_id>

# Query today LLM Dosage
curl "http://127.0.0.1:8000/api/v1/usage/summary?period=today"

# Query today LLM Usage board
curl "http://127.0.0.1:8000/api/v1/usage/dashboard?period=today&limit=50"

# Trigger backtest（All stocks）
curl -X POST http://127.0.0.1:8000/api/v1/backtest/run \
  -H 'Content-Type: application/json' \
  -d '{"force": false}'

# Trigger backtest（designated stocks）
curl -X POST http://127.0.0.1:8000/api/v1/backtest/run \
  -H 'Content-Type: application/json' \
  -d '{"code": "600519", "force": false}'

# Trigger backtest（By analysis date range）
curl -X POST http://127.0.0.1:8000/api/v1/backtest/run \
  -H 'Content-Type: application/json' \
  -d '{"analysis_date_from": "2026-05-01", "analysis_date_to": "2026-05-31", "limit": 100}'

# Trigger backtest（designated stocks + date range + Forced rerun）
curl -X POST http://127.0.0.1:8000/api/v1/backtest/run \
  -H 'Content-Type: application/json' \
  -d '{"code": "600519", "force": true, "analysis_date_from": "2026-05-01", "analysis_date_to": "2026-05-31"}'

# Query overall backtest performance
curl http://127.0.0.1:8000/api/v1/backtest/performance

# Query the backtest performance of a single stock
curl http://127.0.0.1:8000/api/v1/backtest/performance/600519

# Query backtest results by page
curl "http://127.0.0.1:8000/api/v1/backtest/results?page=1&limit=20"
```

### Custom configuration

Modify the default port or allow LAN access：

```bash
python main.py --serve-only --host 0.0.0.0 --port 8888
```

### Supported ticker formats

| Type | Format | Example |
|------|------|------|
| Ashares | 6digits | `600519`、`000001`、`300750` |
| Beijing Exchange | 8/4/92 Beginning 6 Bit，support `BJ` prefix or `.BJ` suffix | `920748`、`BJ920493`、`920493.BJ` |
| Hong Kong stocks | hk + 5digits | `hk00700`、`hk09988` |
| US stocks | 1-5 letters（Optional .X suffix） | `AAPL`、`TSLA`、`BRK.B` |
| Japanese stocks | Yahoo suffix `.T` | `7203.T`、`6758.T` |
| Korean stocks | Yahoo suffix `.KS` / `.KQ` | `005930.KS`、`035720.KQ` |
| US stock index | SPX/DJI/IXIC Wait | `SPX`、`DJI`、`NASDAQ`、`VIX` |

### Things to note

- Browser access：`http://127.0.0.1:8000`（or the port you configured）
- After deploying on the cloud server，I don’t know what address to enter in the browser？Please see [cloud server Web Interface Access Guide](deploy-webui-cloud.md)
- Automatically push notifications to configured channels after analysis is completed
- This feature is available in GitHub Actions environment will be automatically disabled
- See also [openclaw Skill Integration Guide](openclaw-skill-integration.md)

---

## FAQ

### Q: Push message is truncated？
A: Enterprise WeChat/Feishu has a message length limit，The system has automatically sent in segments。For full content，Configurable Feishu cloud document function。

### Q: Data acquisition failed？
A: AkShare Use crawler mechanism，May be temporarily restricted。The system has configured a retry mechanism，Generally, you can wait a few minutes and try again.。

### Q: How to add discretionary stocks？
A: Modify `STOCK_LIST` environment variables，It is recommended to separate multiple codes with English commas。The system also recognizes Chinese commas、comma、semicolon、Spaces and line breaks，And in Web After saving or adding or deleting the settings page, the standard is English comma.。

### Q: GitHub Actions Not executed？
A: Check if enabled Actions，and cron Is the expression correct?（Note that UTC time）。

---

More questions please [Submit Issue](https://github.com/ZhuLinsen/daily_stock_analysis/issues)

## Agent Tool data caching and persistence

- `get_daily_history` Will try to reuse local `stock_daily` daily cache；The cache is fresh and at least covers the default on the home page. 30 records，No more repeated requests to external data sources。
- When Agent When the number of days requested exceeds the number of local cache records，The tool returns the actual available records，and pass `partial_cache=true`、`requested_days`、`actual_records` Indicates this is a partial cache hit。
- When cache is missing or expired，The tool will still obtain daily data from the data source according to the original logic.；After successful acquisition, it will best-effort write back `stock_daily`，Failure to save will not block Agent Reply。
- `search_stock_news` with `search_comprehensive_intel` Will return successfully best-effort write `news_intel`，Reuse existing URL / fallback key Deduplication logic。
- `get_realtime_quote` Not reused `stock_daily` As a real-time quotation cache，It will not write real-time intraday market prices into the daily chart.；If you need real-time quotation caching，Real-time market data storage should be designed separately。

## Agent Event alarm monitoring

`AGENT_EVENT_MONITOR_ENABLED=true` after，schedule mode will press `AGENT_EVENT_MONITOR_INTERVAL_MINUTES` Operation alarm worker。worker Read every round Alert API Create and enable persistence rules，while remaining compatible `AGENT_EVENT_ALERT_RULES_JSON` in legacy rules；Still sent to existing notification channels after triggering。Alert API / Web Persistence rules support real-time prices、Increase or decrease、Volume、Daily technical indicators、`watchlist`、`portfolio_holdings`、`portfolio_account`，and `market` Market traffic light target；legacy JSON Still only supports three types of basic rules。

> Compatibility and migration instructions：This section records the current event alarm rules（Contains `price_change_percent`）runtime behavior，The model name has not changed、provider、Base URL、LiteLLM、`OPENAI_*`、`DEEPSEEK_*`、`GEMINI_*` Wait for external model/API Configuration semantics。legacy JSON will not be automatically migrated、Delete or rewrite；If you need to go back，Delete or close `AGENT_EVENT_MONITOR_ENABLED` to stop background alarms worker。

| `alert_type` | direction field | threshold field | Description |
| --- | --- | --- | --- |
| `price_cross` | `above` / `below` | `price` | The current price breaks above or below the specified price |
| `price_change_percent` | `up` / `down` | `change_pct` | The increase or decrease reaches a specified percentage |
| `volume_spike` | - | `multiplier` | The latest trading volume exceeds nearly 20 Specified multiple of daily average volume |
| `ma_price_cross` | `above` / `below` | `window` | daily line close relatively MA(window) Top or bottom edge |
| `rsi_threshold` | `above` / `below` | `period`、`threshold` | RSI Edge crossing above or below threshold |
| `macd_cross` | `bullish_cross` / `bearish_cross` | `fast_period`、`slow_period`、`signal_period` | DIF/DEA Edge golden cross or dead cross |
| `kdj_cross` | `bullish_cross` / `bearish_cross` | `period`、`k_period`、`d_period` | K/D Edge golden cross or dead cross |
| `cci_threshold` | `above` / `below` | `period`、`threshold` | CCI Edge crossing above or below threshold |
| `portfolio_stop_loss` | `mode=near|breach` | - | Account level stop loss is close or triggered |
| `portfolio_concentration` | - | - | Account level symbol Concentration |
| `portfolio_drawdown` | - | - | Account level maximum drawdown alarm |
| `portfolio_price_stale` | - | - | Position price stale or missing |
| `market_light_status` | - | `statuses` | The current traffic light status of the market is hit `red/yellow` list |
| `market_light_score_drop` | - | `min_drop` | Compared to the previous trading day Market Light score drop reaches threshold |

Example：

```env
AGENT_EVENT_MONITOR_ENABLED=true
AGENT_EVENT_MONITOR_INTERVAL_MINUTES=5
AGENT_EVENT_ALERT_RULES_JSON=[{"stock_code":"600519","alert_type":"price_cross","direction":"above","price":1800},{"stock_code":"300750","alert_type":"price_change_percent","direction":"down","change_pct":3.0},{"stock_code":"000858","alert_type":"volume_spike","multiplier":2.5}]
```

worker will `triggered`、`skipped`、`degraded`、`failed` write `alert_triggers` as evaluation history；Normally, no history is written if it is not triggered.。DB persistence rules `triggered` History button `rule_id + target + data_source + data_timestamp` do for the same data point best-effort Remove duplicates，Repeated hits will reuse the earliest trigger record，`data_timestamp` Do not remove duplicates when missing。After actual triggering, each notification channel will attempt write `alert_notifications`，And for Alert API The created persistence rule is written to `alert_cooldowns` Business cooling status；If reading persistence cooling fails，worker will temporarily use in-process fingerprint prevent DB Repeated push during abnormal period。legacy `AGENT_EVENT_ALERT_RULES_JSON` Rules continue to use in-process fingerprint inhibit，Do not write persistent cooling；notification infrastructure `notification_noise.py` Noise reduction still works independently。Web The rule list is returned using the backend `cooldown_active` Determine cooling status，Avoid browser local time zone analysis affecting display。

Technical indicator rules only use daily lines close edge trigger，partial bar Processing is server local time zone + 16:00 heuristic，Do not make accurate judgments on the market calendar。`watchlist` Refresh every round `STOCK_LIST` expand later，`portfolio_holdings` Non-zero position press from position snapshot symbol Remove duplicates and expand，`portfolio_account` Reuse position risk services for account-level aggregate assessment。`market` regular target Only supports `cn|hk|us|jp|kr`，Use structured `MarketLightSnapshot`；`trade_date` from that time market overview，`data_quality=unavailable` Will skip triggering，Non-trading days will be replaced by trading days gate skip，`market_light_score_drop` Compare only across trading days score。WebUI of“Alarm”The page can manage persistence rules、Execute once dry-run test，and view trigger history、Notification of attempt results and read-only cooldown status；The list cooling status of a bulk rule is the summary of the parent rule，The sub-target cooldown is based on the trigger history。For detailed boundaries see [Real-time alarm center](alerts.md)。

## Position management instructions

### `/portfolio` What the page can do

- View full positions or switch to a single account view。
- in `fifo` / `avg` Switch between two cost methods，View snapshot KPI、risk summary and Top Positions concentration chart。
- directly in Web Add new account to the page、Delete mistakenly created account，or enter transaction、cash flow、Corporate actions and other events。
- Pass CSV Import position records，Support first `dry_run` Preview，Then decide whether to formally write。
- By account in event list、Date、direction、Filter by code and other conditions，And delete and correct single account events。

### Related interfaces

| interface | method | Description |
|------|------|------|
| `/api/v1/portfolio/snapshot` | GET | Query position snapshot |
| `/api/v1/portfolio/risk` | GET | Query Risk Summary |
| `/api/v1/portfolio/trades` | GET | Query transaction records by page |
| `/api/v1/portfolio/cash-ledger` | GET | Query cash flow by page |
| `/api/v1/portfolio/corporate-actions` | GET | Query company actions by page |
| `/api/v1/portfolio/imports/csv/brokers` | GET | Query built-in CSV Brokerage parser |
| `/api/v1/portfolio/fx/refresh` | POST | Manually refresh exchange rate cache |
| `/api/v1/portfolio/accounts/{account_id}` | DELETE | Delete/Archive holding accounts |
| `/api/v1/portfolio/trades/{trade_id}` | DELETE | Delete transaction history |
| `/api/v1/portfolio/cash-ledger/{entry_id}` | DELETE | Delete cash flow |
| `/api/v1/portfolio/corporate-actions/{action_id}` | DELETE | Delete corporate action |

> Unified support for query interfaces `account_id`、`date_from`、`date_to`、`page`、`page_size` and other common filtering parameters；The event list will return a unified `items`、`total`、`page`、`page_size` structure。

### Usage behavior description

- CSV Import built-in `huatai`、`citic`、`cmb` parser；If the broker list interface fails，Web The client will automatically fall back to these built-in options。
- The import process will first CSV Parse into standardized records，Then submit them to the position ledger one by one.；Busy rows will be counted `failed_count`，The entire batch of requests will not fail due to a single row conflict.。
- Deleting an account uses soft delete semantics：Default account list、Snapshot、risk、The account will no longer be displayed in the entry portal and event list.，but deal、Cash flows and corporate actions will not be physically cleared；If you need to correct a single flow，You need to use the deletion correction entry in the event list before archiving the account.。
- For transaction deduplication, priority is given to using the only one in the account. `trade_uid`，Fallback to date based when missing、code、direction、Quantity、price、cost、taxes、Deterministic hash of currency。
- When selling, the available quantity will be verified first.，oversold return `409 portfolio_oversell`；May be returned when concurrent writes conflict `409 portfolio_busy`。
- Position snapshot `positions[]` will return `price_source`、`price_date`、`price_stale`、`price_available` Equal price meta information；By default, the snapshot of the day will try real-time quotes first.，Fall back to when the real-time price is unavailable or non-positive. `as_of` The most recent historical closing price on or before that day；incoming `include_realtime=false` will skip the real-time market and directly use the local historical closing price fallback path，Web The position page uses this mode to render the position list first.，Avoid blocking the first screen when external real-time quotation sources slow down。history `as_of` Snapshots will not pull real-time prices，We will no longer treat the cost price as the current price silently.；Short positions will be marked `price_available=false` and excluded from market capitalization and unrealized profit and loss aggregation。
- Exchange rate refresh will try online sources first；If online acquisition fails，Then fall back to the most recent cache and mark `is_stale=true`，Avoid snapshots and the risk of overall page unavailability。
- When `PORTFOLIO_FX_UPDATE_ENABLED=false` time，Manually refreshing the interface will clearly return“Online refresh disabled”，The page does not mislead as“There are currently no exchange rates to refresh”。
- Risk summary includes concentrations、retracement、Stop loss proximity and other information；`sector_concentration` Will give priority to trying to classify by sector，On failure, downgrade to `UNCLASSIFIED`，Will not block risk results from returning。

### Agent Read positions

- Agent Passable `get_portfolio_snapshot` Get a compact account-specific position summary，Contains streamlined risk blocks by default，suitable for control Token overhead。
- Optional parameters include `account_id`、`cost_method`、`as_of`、`include_positions`、`include_risk`。
- If risk block generation fails，Snapshots will still be returned；If the position module is not enabled in the current environment，The tool will return a structured `not_supported`。
