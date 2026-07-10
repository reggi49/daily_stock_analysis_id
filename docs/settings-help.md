# Settings Page Configuration Help Maintenance Guide

Settings page configuration help places key configuration descriptions inside the WebUI, reducing the need for users to switch back and forth between the settings page and documentation. Short descriptions remain on the page; detailed descriptions are accessible via the help icon next to the configuration item title.

This document only covers help system maintenance rules and does not replace complete configuration documentation. Configuration semantics, defaults, runtime priorities, and troubleshooting details still use `.env.example`, `docs/full-guide.md`, and corresponding topic documents as the source of truth.

## Data Structure

The backend configuration registry in `src/core/config_registry.py` adds help metadata to fields:

- `help_key`: Stable key for frontend multi-language help text.
- `examples`: Configuration samples that can be displayed directly. Sensitive fields can only use placeholders, e.g., `sk-xxxx`, `your_token`.
- `docs`: Related documentation links, prioritizing existing topic documents or complete guides within the repository.
- `warning_codes`: Stable warning codes for frontend or subsequent validation extensions.

Frontend long-form text is maintained in `apps/dsa-web/src/locales/settingsHelp.ts`:

- Default display is in Chinese.
- English text maintains the same structure for future language-switching expansion.
- Text should explain purpose, value description, scope of impact, precautions, and related documentation; it should not copy complete topic documents.

## WebUI Language Note (Not a Configuration Item)

This project adds an independent WebUI interface language capability (`zh` / `en`) for static page text, navigation, and shared control text. This state is decoupled from `REPORT_LANGUAGE` and does not rewrite report language semantics.

- State key: `dsa.uiLanguage` (`localStorage`, browser-side persistence).
- Initialization priority: valid `localStorage` value first, then browser language detection (`zh-*` / `en-*`), finally falling back to `zh`.
- This language toggle is not a `.env` configuration field and does not appear in the `system/config` configurable field list.
- Interface switching synchronizes `document.documentElement.lang` (`zh-CN` or `en`) for accessibility and semantics.

## Coverage Scope

PR1 covers infrastructure and the first batch of representative configuration items:

- `STOCK_LIST`
- `LITELLM_MODEL`
- `LLM_CHANNELS`
- `FEISHU_WEBHOOK_URL`
- `WEBUI_HOST`

PR2 continues covering high-frequency, error-prone configuration items:

- AI model runtime: Agent primary model, fallback model, advanced YAML routing, temperature, provider API Key, OpenAI-compatible Base URL.
- LLM Channels editor internal fields: channel name, protocol, Base URL, API Key, model list, runtime capability detection, primary model, Agent primary model, fallback, Vision, and temperature.
- Data sources and search: Tushare, stock index remote update toggle, realtime quote priority, realtime technical indicators, search API Key, SearXNG, chip distribution, news window.
- Notifications: Webhook, Telegram, email, Discord/Slack and other chat platforms, report output, Webhook SSL verification.
- WebUI / auth / schedule / proxy: Host, Port, login protection, trusted reverse proxy, scheduled tasks, trading-day check, network proxy.

PR3 registered-field slice / phased completion: Focuses on Help completion for fields actually displayed/configurable on the Web settings page, including common configuration card currently visible fields and AI legacy conditionally visible fields:

- Agent configuration (21 fields): Agent mode, maximum reasoning steps, strategy list, strategy directory, natural language routing, architecture, orchestrator mode, timeout, risk veto, Deep Research budget/timeout, memory, strategy auto-weighting, strategy routing, stock-ask visible conversation context compression, event monitoring toggle/interval, alert rule JSON.
- Backtest configuration (5 fields): Backtest toggle, evaluation window, minimum record age, engine version, neutral return band.
- Report configuration (9 fields): Summary-only push, show model name, template directory, rendering engine, integrity check/retry, history signal comparison, per-stock push, merged email.
- Notification routing configuration (9 fields): Report/alert/system-error channel routing, dedup/cooldown, quiet hours/timezone, minimum severity, daily digest (reserved).
- System runtime (7 fields): Log level, debug mode, max concurrency, analysis interval, market analysis toggle/market/color scheme.
- AI legacy and Anspire configuration: Provider-specific multi-Key, model name, temperature, Vision model, max tokens, and Anspire LLM gateway fields.
- Data sources and search: TickFlow, SerpAPI, Brave, Bocha, MiniMax, SearXNG public instances, BIAS threshold, and Pytdx server fields.
- Notification advanced fields: Feishu advanced security/app fields, Telegram topic, Discord/Slack advanced fields, Pushover, ntfy, Gotify, PushPlus, ServerChan3, AstrBot, and custom Webhook advanced template/auth fields.

After Issue #1512, the Web settings page only displays formally registered fields from the backend configuration registry. Unregistered `.env` keys are no longer displayed as ordinary editable settings items, preventing raw keys, `Auto-inferred field metadata.`, and configuration items without help buttons from appearing in the Chinese interface; these keys can still be maintained via `.env` files or import/export capabilities.

Exception: Dynamic channel detail keys declared by `LLM_CHANNELS` (e.g., `LLM_DEEPSEEK_API_KEY`, `LLM_MY_PROXY_MODELS`) remain in the configuration API response for the "AI Model Integration" editor to read and save; they are not displayed as ordinary configuration cards and do not reuse `WEB_SETTINGS_HIDDEN_FROM_UI` operational hiding semantics.

Low-frequency/operational `.env` variables not yet included in Web settings page display include `DATABASE_PATH`, `SQLITE_*`, `USE_PROXY`, `PROXY_HOST`, `PROXY_PORT`, etc. If these fields need to be editable in the Web in the future, they should first be formally registered in `src/core/config_registry.py` with help metadata, rather than relying on auto-inference.

### Coverage Boundaries

- The `settings.llm_channel.*` series in `settingsHelp.ts` are LLM channel editor internal field descriptions, used only for frontend rendering and not corresponding to separate `.env` configuration items; this is a deliberate "built-in extension" design from PR2 to improve editor usability.
- All other help text should be mappable from a field's `help_key` in `src/core/config_registry.py` to backend registry metadata, for unified maintenance alongside documentation sources and `warning_codes`.

## Source of Truth Priority

When adding or modifying help text, prioritize verifying from the following locations:

1. `.env.example`: Configuration key names, default values, sample formats, and sensitive placeholders.
2. `docs/full-guide.md`: Main configuration descriptions, run entry points, and deployment context.
3. `docs/LLM_CONFIG_GUIDE.md`, `docs/llm-providers.md`: LLM priorities, Channels, provider/model, compatibility boundaries, and troubleshooting.
4. Topic documents: e.g., `docs/bot/feishu-bot-config.md`, `docs/deploy-webui-cloud.md`, `docs/desktop-package.md`.
5. Code implementation and tests: When documentation and code are inconsistent, prioritize the executable implementation and update documentation accordingly.

## Maintenance Boundaries

- Help text cannot change configuration saving, validation, runtime priority, `.env` writeback, or environment variable override semantics.
- Real secrets, accounts, tokens, complete Webhook values, or local absolute paths must not be displayed.
- If LLM-related examples include specific provider prefixes, model names, or Base URLs, they must be traceable to current repository documentation or official sources; otherwise, use placeholders or link to the source of truth.
- For third-party model/API availability, LiteLLM compatibility windows, or provider fallback rules, the settings help should not make standalone commitments; changes must be synchronized with topic documents and PR compatibility notes.
- Bilingual (Chinese/English) text should maintain the same semantic scope. If only one language is updated, the reason must be stated in the delivery notes.
- Short descriptions on the first screen should remain concise; detailed descriptions go in the help dialog to avoid duplication between hover tooltips and persistent short descriptions.

## Restart Semantics

Settings page saves typically only write to `.env` and trigger a runtime-reloadable configuration refresh. Help text and `warning_codes` must explicitly distinguish the following cases:

- `WEBUI_HOST`, `WEBUI_PORT`: Listening address and port are only bound at process startup; saving requires restarting the current process, Docker container, or service manager to take effect.
- `RUN_IMMEDIATELY`: Non-schedule mode startup one-time run configuration; saving does not trigger immediate analysis in a running WebUI/API process.
- Web settings page does not directly expose internal keys like `SCHEDULE_TIME` / `SCHEDULE_TIMES` / `SCHEDULE_RUN_IMMEDIATELY`; users maintain enable status, multiple execution times, and immediate one-time execution via the "Scheduled Tasks" card.
- `SCHEDULE_ENABLED`: WebUI/API/Desktop long-running processes (including `python main.py --serve --schedule`) start or stop the runtime scheduler per the new value after saving; pure CLI schedule mode (`python main.py --schedule`) still runs per startup arguments and configuration.
- `SCHEDULE_TIME`, `SCHEDULE_TIMES`: Not required for restart. When `SCHEDULE_TIMES` is empty, `SCHEDULE_TIME` is used; running schedulers rebuild daily jobs per the new time.
- `SCHEDULE_RUN_IMMEDIATELY`: Schedule mode startup behavior; saving does not trigger an immediate analysis run in the current process; use the runtime scheduler's run-now API for manual execution.
- The runtime scheduler's run-now API only accepts requests when no analysis task is running; if analysis is already in progress, it returns a busy status, and the Web settings page prompts to try later.
