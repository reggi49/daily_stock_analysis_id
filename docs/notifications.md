# Notification Capabilities Baseline

This document records the notification capability P0-P7 final state: channels, configuration keys, GitHub Actions mapping, Web settings metadata, CLI diagnostic criteria, Web one-click testing, custom Webhook Body template semantics, notification routing strategy, noise reduction, aggregated report failure isolation, ntfy / Gotify first-class channels, WebPush / Apprise evaluation, and local / Docker / GitHub Actions / Desktop scenario-based configuration notes. P0 covers baseline and read-only diagnostics only; P1 adds real Web single-channel testing; P2 productionizes existing Body templates; P3 adds report / alert / system_error routing; P4 adds in-process noise reduction; P5 enhances test diagnostics and per-channel failure isolation for aggregated reports; P6-A adds ntfy; P6-C adds Gotify; P6-D only evaluates WebPush / Apprise; P7 closes documentation and Actions env mapping table automation, adding no new runtime dependencies, configuration entry points, per-URL templates, cross-process persistence, real daily digests, or retry loops.

## Channel Baseline

| Channel | Type | Minimal Key | Advanced Key | Description |
| --- | --- | --- | --- | --- |
| DingTalk Webhook | Static config | `DINGTALK_WEBHOOK_URL` | `DINGTALK_SECRET` | Supports signed security mode. Currently only configurable via environment variables, not yet integrated into the Web UI settings page. |
| WeChat Work | Static config | `WECHAT_WEBHOOK_URL` | `WECHAT_MSG_TYPE` | Participates in batch notification sending once configured |
| Feishu Webhook / App Bot | Static config | `FEISHU_WEBHOOK_URL` or `FEISHU_APP_ID` + `FEISHU_APP_SECRET` + `FEISHU_CHAT_ID` | `FEISHU_WEBHOOK_SECRET`, `FEISHU_WEBHOOK_KEYWORD`, `FEISHU_RECEIVE_ID_TYPE`, `FEISHU_DOMAIN` | Webhook URL takes priority; when Webhook is not configured, the App Bot triplet can proactively push to a specified group/user. `FEISHU_STREAM_ENABLED` only represents event subscription / Stream Bot and does not factor into proactive notification configuration completion judgment |
| Telegram | Static config | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | `TELEGRAM_MESSAGE_THREAD_ID` | Token and chat ID must both be present |
| Email | Static config | `EMAIL_SENDER`, `EMAIL_PASSWORD` | `EMAIL_RECEIVERS`, `EMAIL_SENDER_NAME` | When `EMAIL_RECEIVERS` is empty, sends to self |
| Pushover | Static config | `PUSHOVER_USER_KEY`, `PUSHOVER_API_TOKEN` | - | Both keys must be present |
| ntfy | Static config | `NTFY_URL` | `NTFY_TOKEN`, `WEBHOOK_VERIFY_SSL` | `NTFY_URL` must include the topic path, e.g., `https://ntfy.sh/my-topic` |
| Gotify | Static config | `GOTIFY_URL`, `GOTIFY_TOKEN` | `WEBHOOK_VERIFY_SSL` | `GOTIFY_URL` is the server base URL, excluding `/message`; token is sent via `X-Gotify-Key` header |
| PushPlus | Static config | `PUSHPLUS_TOKEN` | `PUSHPLUS_TOPIC` | `PUSHPLUS_TOPIC` only takes effect when token is present |
| ServerChan3 | Static config | `SERVERCHAN3_SENDKEY` | - | Mobile app push |
| Custom Webhook | Static config | `CUSTOM_WEBHOOK_URLS` | `CUSTOM_WEBHOOK_BEARER_TOKEN`, `CUSTOM_WEBHOOK_BODY_TEMPLATE`, `WEBHOOK_VERIFY_SSL` | Supports multiple URLs, comma-separated |
| Discord | Static config | `DISCORD_WEBHOOK_URL` or `DISCORD_BOT_TOKEN` + `DISCORD_MAIN_CHANNEL_ID` | `DISCORD_INTERACTIONS_PUBLIC_KEY` | Both Webhook and Bot can enable sending |
| Slack | Static config | `SLACK_WEBHOOK_URL` or `SLACK_BOT_TOKEN` + `SLACK_CHANNEL_ID` | - | Bot takes priority for text and image sending in the same channel |
| AstrBot | Static config | `ASTRBOT_URL` | `ASTRBOT_TOKEN`, `WEBHOOK_VERIFY_SSL` | `ASTRBOT_TOKEN` is optional |
| `UNKNOWN` | Fallback enum | - | - | Fallback for unknown channels only, not enabled by static environment variables |
| DingTalk conversation | Runtime context | - | - | Extracted from source message context, cannot be determined solely from `.env` static values |
| Feishu conversation | Runtime context | - | - | Extracted from source message context; interactive command results return to the source conversation |
| Telegram conversation | Runtime context | - | - | Extracted from source message context; interactive command results return to the source conversation |

Discord long report sending reuses the existing sharding path: a single `content` will not exceed Discord's 2000-character limit at runtime; both Webhook and Bot API send piece by piece with brief waits between pieces; on 429 errors, limited retries are performed per Discord's `retry_after` or `Retry-After` to avoid receiving only the first half of the report after rate limiting.

## Minimal / Advanced Key Split

- Minimal key: Minimum configuration needed to enable a notification channel.
- Advanced key: Only affects authentication, security, formatting, threads, groups, certificate verification, or display behavior; cannot independently enable a channel.
- P3's `NOTIFICATION_*_CHANNELS` keys are Advanced keys: they only narrow enabled channels, not independently enable channels.
- P4's `NOTIFICATION_DEDUP_TTL_SECONDS`, `NOTIFICATION_COOLDOWN_SECONDS`, `NOTIFICATION_QUIET_HOURS`, `NOTIFICATION_TIMEZONE`, `NOTIFICATION_MIN_SEVERITY`, `NOTIFICATION_DAILY_DIGEST_ENABLED` are Advanced keys: they only affect sending strategies for enabled static channels, not independently enable channels.
- `REPORT_SHOW_LLM_MODEL` is a report display toggle: when `true` (default), the LLM model used for analysis is shown at the notification report footer; when `false`, it is hidden. This parameter only affects report rendering and does not change runtime provider/model/Base URL, LiteLLM routing, model save, migration, or cleanup logic; rollback is to set it back to `true` or remove the variable.
- `WEBHOOK_VERIFY_SSL` is a shared certificate verification toggle for webhook-style HTTPS notification requests that read this setting.
- WebPush, Apprise, finer-grained routing, cross-process noise reduction, and real daily digests are not yet in the runtime implementation; if introduced in the future, this document, `.env.example`, Web metadata, and regression tests should be updated first.
- Bark remains at the custom webhook baseline; no `BARK_*` first-class configuration is added.
- The Feishu App Bot send path reuses `lark-oapi>=1.0.0` already in `requirements.txt`, not a new dependency; it is installed via `pip install -r requirements.txt` in standard source installs, Docker, GitHub Actions daily workflow, and desktop build paths. Official references: [Feishu message create OpenAPI](https://open.feishu.cn/document/server-docs/im-v1/message/create), [lark-oapi PyPI](https://pypi.org/project/lark-oapi/), [SDK repo](https://github.com/larksuite/oapi-sdk-python). App Bot file upload depends on the same SDK's `im.v1.file.create` API: [Feishu file create OpenAPI](https://open.feishu.cn/document/server-docs/im-v1/file/create).

## Report Rendering and Sharding

The current default report push entry, content source, and overall layout remain unchanged. This phase only converges the technical approach for notification rendering: establishing channel capability profiles, pre-send message structure, and structure-aware sharding capabilities to avoid continuing to stack parallel logic across senders during future channel expansion.

The default send path reuses existing sender behavior without integrating new renderers: Feishu and Telegram continue using existing compatibility conversions; WeChat Work and Slack continue using existing sharding logic, avoiding changes to the live visible report layout. The new channel capability profiles, PreparedMessage, renderer presets, and structure-aware sharding serve as a foundation for future expansion; to enable specialized renderers for WeChat Work, Feishu, Telegram, Slack, and other channels, integration should proceed gradually through explicit configuration, real send verification, and regression testing.

Compatibility exclusions:
- This round does not modify the send paths in `src/notification_sender/wechat_sender.py`, `src/notification_sender/slack_sender.py`, or `src/notification_sender/telegram_sender.py`; `src/notification_sender/feishu_sender.py` adds a `send_feishu_file()` file send path, with Webhook mode falling back to sending file content as text, and the App Bot text send path (`send_to_feishu` → `_send_via_app_bot`) remaining unchanged.
- `model_used` is only displayed at the end of report rendering and does not participate in provider/model/base_url runtime selection, saving, cleanup, or migration. If a CI scan flags "provider/API compatibility migration" keywords, the scope should first regress to `model_used` examples in test fixtures and report snapshot fixtures (`tests/fixtures/notification_reports/*.md`), as well as the display-only toggle logic in `src/notification.py` for `report_show_llm_model`.
- `REPORT_SHOW_LLM_MODEL` and `report_renderer_enabled` are both display/degradation strategy toggles: disabling them only affects report visible structure and does not trigger configuration migration or runtime parameter fallback; rollback is to restore `true` (or remove the item) or restore default configuration.

Related sector rendering remains in the report body generation stage: when there are no industry/concept gain/loss ranking signals, the push report retains the original single-line style, e.g., `Telecom Cable & Accessories / Telecom Equipment / Telecom / Jiangsu Sector / Tech Style`, without an extra "Type" column. The table "Sector / Type / Sector Performance / Sector Gain/Loss" is only used when `fundamental_context.boards.data` / `sector_rankings` or `fundamental_context.concept_boards.data` / `concept_rankings` leader/laggard signals are matched, where the "Type" column indicates "Industry Sector" or "Concept Sector". This logic only affects report display and does not change provider/model/Base URL, LiteLLM routing, model save, migration, or cleanup logic.

## GitHub Actions Mapping

The bundled `.github/workflows/00-daily-analysis.yml` only explicitly imports fixed variable names. P0/P3/P4/P6 have incorporated Body template, security items, PushPlus topic, routing, noise reduction, ntfy, and Gotify notification keys into the default workflow. The table below is generated by `scripts/generate_notification_actions_env_table.py` from the workflow `env:` and notification diagnostic metadata to prevent continued drift between hand-written lookup tables and real Actions mappings.

<!-- notification-actions-env-table:start -->

| Key | Tier | Channel / Feature | Actions Source | Default |
| --- | --- | --- | --- | --- |
| `WECHAT_WEBHOOK_URL` | minimal | wechat | Secret | - |
| `WECHAT_MSG_TYPE` | advanced | wechat | Variable or Secret | `markdown` |
| `FEISHU_WEBHOOK_URL` | minimal | feishu | Secret | - |
| `FEISHU_WEBHOOK_SECRET` | advanced | feishu | Secret | - |
| `FEISHU_WEBHOOK_KEYWORD` | advanced | feishu | Variable or Secret | - |
| `DINGTALK_WEBHOOK_URL` | minimal | dingtalk | Secret | - |
| `DINGTALK_SECRET` | advanced | dingtalk | Secret | - |
| `TELEGRAM_BOT_TOKEN` | minimal | telegram | Secret | - |
| `TELEGRAM_CHAT_ID` | minimal | telegram | Secret | - |
| `TELEGRAM_MESSAGE_THREAD_ID` | advanced | telegram | Secret | - |
| `EMAIL_SENDER` | minimal | email | Variable or Secret | - |
| `EMAIL_PASSWORD` | minimal | email | Secret | - |
| `EMAIL_RECEIVERS` | advanced | email | Variable or Secret | - |
| `EMAIL_SENDER_NAME` | advanced | email | Variable or Secret | `daily_stock_analysis Stock Analysis Assistant` |
| `PUSHOVER_USER_KEY` | minimal | pushover | Secret | - |
| `PUSHOVER_API_TOKEN` | minimal | pushover | Secret | - |
| `NTFY_URL` | minimal | ntfy | Secret | - |
| `NTFY_TOKEN` | advanced | ntfy | Secret | - |
| `GOTIFY_URL` | minimal | gotify | Secret | - |
| `GOTIFY_TOKEN` | minimal | gotify | Secret | - |
| `PUSHPLUS_TOKEN` | minimal | pushplus | Secret | - |
| `PUSHPLUS_TOPIC` | advanced | pushplus | Variable or Secret | - |
| `CUSTOM_WEBHOOK_URLS` | minimal | custom | Secret | - |
| `CUSTOM_WEBHOOK_BEARER_TOKEN` | advanced | custom | Secret | - |
| `CUSTOM_WEBHOOK_BODY_TEMPLATE` | advanced | custom | Variable or Secret | - |
| `WEBHOOK_VERIFY_SSL` | advanced | ntfy, gotify, custom, astrbot | Variable or Secret | `true` |
| `DISCORD_WEBHOOK_URL` | minimal | discord | Secret | - |
| `DISCORD_BOT_TOKEN` | minimal | discord | Secret | - |
| `DISCORD_MAIN_CHANNEL_ID` | minimal | discord | Secret | - |
| `FEISHU_APP_ID` | minimal | feishu | Secret | - |
| `FEISHU_APP_SECRET` | minimal | feishu | Secret | - |
| `FEISHU_CHAT_ID` | minimal | feishu | Variable or Secret | - |
| `FEISHU_RECEIVE_ID_TYPE` | advanced | feishu | Variable or Secret | - |
| `FEISHU_DOMAIN` | advanced | feishu | Variable or Secret | - |
| `FEISHU_SEND_AS_FILE` | advanced | feishu | Variable or Secret | - |
| `ASTRBOT_URL` | minimal | astrbot | Secret | - |
| `ASTRBOT_TOKEN` | advanced | astrbot | Secret | - |
| `SERVERCHAN3_SENDKEY` | minimal | serverchan3 | Secret | - |
| `SLACK_WEBHOOK_URL` | minimal | slack | Secret | - |
| `SLACK_BOT_TOKEN` | minimal | slack | Secret | - |
| `SLACK_CHANNEL_ID` | minimal | slack | Secret | - |
| `NOTIFICATION_REPORT_CHANNELS` | advanced | routing | Variable or Secret | - |
| `NOTIFICATION_ALERT_CHANNELS` | advanced | routing | Variable or Secret | - |
| `NOTIFICATION_SYSTEM_ERROR_CHANNELS` | advanced | routing | Variable or Secret | - |
| `NOTIFICATION_DEDUP_TTL_SECONDS` | advanced | noise | Variable or Secret | `0` |
| `NOTIFICATION_COOLDOWN_SECONDS` | advanced | noise | Variable or Secret | `0` |
| `NOTIFICATION_QUIET_HOURS` | advanced | noise | Variable or Secret | - |
| `NOTIFICATION_TIMEZONE` | advanced | noise | Variable or Secret | - |
| `NOTIFICATION_MIN_SEVERITY` | advanced | noise | Variable or Secret | - |
| `NOTIFICATION_DAILY_DIGEST_ENABLED` | advanced | noise | Variable or Secret | `false` |

<!-- notification-actions-env-table:end -->

The default workflow still does not map `MARKDOWN_TO_IMAGE_CHANNELS` and `MERGE_EMAIL_NOTIFICATION`. They are delivery-format or aggregation-behavior toggles, not channel credentials; auto-reading same-name Secret/Variable in Actions would introduce additional behavior changes.

## CLI Diagnostics

```bash
python main.py --check-notify
```

This command reads configuration only, does not send notifications, and does not write to `.env`. It executes immediately after configuration loading and log initialization, then exits without entering Web, scheduling, market review, or default analysis flows.

- Return code `0`: No error-level diagnostics.
- Return code `1`: Errors exist, e.g., zero static notification channels configured, or paired keys only partially configured.

## Web One-Click Testing

The Web settings page "Notification Channels" section provides single-channel test entry points. The test uses current page draft values to compose a temporary configuration, sends a real test notification, but does not save `.env` or modify the runtime global configuration.

- Test scope: 13 static notification channels, excluding `UNKNOWN` and runtime context channels.
- Regular channels: Returns single-send result, latency, and generic error code.
- Custom Webhook: Returns attempts in URL order, showing success/failure, HTTP status, latency, and error code for each URL; when multiple URLs partially succeed, the top-level message shows success count / total.
- Returned results sanitize tokens, secrets, passwords, Bearer, complete webhook query, and suspected path tokens.
- Missing configuration or send failure returns `success=false` without affecting saved configuration and default analysis flow.

## Custom Webhook Body Template

`CUSTOM_WEBHOOK_BODY_TEMPLATE` is the global JSON body template for custom webhooks. Once configured, it takes precedence over URL auto-detection, overriding auto-generated payloads for Bark, Slack, Discord, DingTalk, etc. When unconfigured, original URL auto-detection is used; when the rendered result is not a valid JSON object, an error is logged and the default payload is used as fallback without interrupting the main notification flow.

Available placeholders:

- `$content_json`: JSON-escaped notification body; recommended for default use.
- `$title_json`: JSON-escaped notification title; recommended for default use.
- `$content` / `$title`: Raw strings without JSON escaping. Body containing double quotes, backslashes, or newlines may cause invalid JSON and trigger fallback.

In Docker Compose deployments, the Web settings page saves these placeholders as `$$content_json`, `$$title_json`, `$$content`, `$$title` to prevent Compose from expanding them as host environment variables; the application runtime restores them to single `$` placeholders. If manually editing Docker's `.env`, also use the `$$content_json` format.

This feature only affects notification body rendering and does not involve LLM `provider` / `model` / `base URL` / LiteLLM routing save, migration, or cleanup semantics.

Generic webhook example:

```env
CUSTOM_WEBHOOK_BODY_TEMPLATE={"title":$title_json,"content":$content_json}
```

When using Bark via custom webhook, place the Bark endpoint in `CUSTOM_WEBHOOK_URLS` without needing additional `BARK_*` configuration. When no global template is configured, the system auto-generates `title` / `body` / `group` per `api.day.app`; if a global template is configured, you must write the Bark body yourself:

```env
CUSTOM_WEBHOOK_URLS=https://api.day.app/YOUR_BARK_KEY
```

```env
CUSTOM_WEBHOOK_BODY_TEMPLATE={"title":$title_json,"body":$content_json,"group":"stock"}
```

AstrBot is a first-class notification channel, prioritizing `ASTRBOT_URL` and optional `ASTRBOT_TOKEN`. Only when you need to put an AstrBot-compatible endpoint into `CUSTOM_WEBHOOK_URLS` should you use the custom webhook template:

```env
CUSTOM_WEBHOOK_BODY_TEMPLATE={"content":$content_json}
```

ntfy is a first-class notification channel, prioritizing `NTFY_URL` and optional `NTFY_TOKEN`. `NTFY_URL` represents a full topic endpoint, e.g., `https://ntfy.sh/my-topic` or `https://self-hosted:port/my-topic`; the system parses the last path segment as the topic and sends a JSON publish to the server root:

```env
NTFY_URL=https://ntfy.sh/my-topic
NTFY_TOKEN=
```

Gotify is a first-class notification channel, prioritizing `GOTIFY_URL` and `GOTIFY_TOKEN`. `GOTIFY_URL` is the Gotify server base URL, which can include a reverse-proxy path prefix but not `/message`; the system appends the fixed `/message` API and sends the application token via the `X-Gotify-Key` header. This deliberate difference between `NTFY_URL` (full topic endpoint) and `GOTIFY_URL` (server base URL) reflects the two services' API design:

```env
GOTIFY_URL=https://gotify.example
GOTIFY_TOKEN=app-token
```

```env
# Reverse-proxy path prefix example; actual request sends to https://example.com/gotify/message
GOTIFY_URL=https://example.com/gotify
GOTIFY_TOKEN=app-token
```

NapCat / OneBot HTTP API requires adjustment per actual endpoint and target type. The following are common body format examples; `user_id`, `group_id`, URL path, and authentication method should all follow your NapCat configuration:

```env
# Private chat: CUSTOM_WEBHOOK_URLS=http://127.0.0.1:3000/send_private_msg
CUSTOM_WEBHOOK_BODY_TEMPLATE={"user_id":123456,"message":$content_json}
```

```env
# Group chat: CUSTOM_WEBHOOK_URLS=http://127.0.0.1:3000/send_group_msg
CUSTOM_WEBHOOK_BODY_TEMPLATE={"group_id":123456789,"message":$content_json}
```

## Notification Routing Strategy

P3 adds three notification routing configuration types:

| Route Type | Config Key | Current Producers |
| --- | --- | --- |
| `report` | `NOTIFICATION_REPORT_CHANNELS` | Single-stock push, aggregated daily report, market review, merged push, Feishu document success link |
| `alert` | `NOTIFICATION_ALERT_CHANNELS` | EventMonitor triggered notifications |
| `system_error` | `NOTIFICATION_SYSTEM_ERROR_CHANNELS` | Reserved capability; no automatic system error producer added currently |

Configuration values are comma-separated channel enums: `wechat,feishu,telegram,email,pushover,ntfy,gotify,pushplus,serverchan3,custom,discord,slack,astrbot`.

- Empty or unconfigured: Retains old behavior, sends to all configured static channels.
- Non-empty: Only sends to the intersection of the routing list and configured channels; when the intersection is empty, it does not fall back to all channels.
- `send_to_context()` is not restricted by routing; bot conversation contexts still receive replies for triggering tasks.
- Interactive commands (DingTalk conversations, Feishu conversations, Telegram) with source context skip static notification channels like `FEISHU_WEBHOOK_URL`; `SCHEDULE`, CLI, API, or sourceless tasks still send per the report route.
- Routing filtering occurs before Markdown-to-image conversion; `MARKDOWN_TO_IMAGE_CHANNELS` only applies to the channel subset after routing.
- `MERGE_EMAIL_NOTIFICATION` requires no additional configuration; as long as `email` remains in the post-routing channel list, existing merged email behavior is preserved.
- `--check-notify` reports unknown channel values as errors and valid but disabled routing targets as warnings.

## Aggregated Report Failure Isolation

P5 strengthens failure boundaries for aggregated report notification paths: `_send_notifications()` sends to each static notification channel individually after report route filtering. An exception thrown by one channel is logged and treated as that channel's failure, but subsequent channels are not skipped and the analysis main flow is not interrupted.

- Emails are isolated by receiver group; when one recipient group fails, subsequent groups continue sending.
- When any static channel sends successfully, the P4 noise reduction reservation writes to the formal record; when all static channels fail or throw exceptions, the reservation is released.
- `send_to_context()` remains independent of static channel routes and noise reduction records, used for replying to the Bot conversation context that triggered the task.

#1390 P6's decision signal summary uses the same failure isolation boundary: analysis report notifications and alert notifications only append low-sensitivity `decision_signal_summary` summaries (action, period, reason, observation conditions, risk, and source report), without outputting signal `metadata`, `evidence`, raw diagnostics, or webhook/tokens. Alert notification send failures only log notification attempts or dispatch fallbacks and do not roll back already-written triggers or DecisionSignals.

DecisionSignal notification summary fields, sensitive information boundaries, migration and rollback notes: see [DecisionSignal Topic](decision-signals.md).

## Notification Noise Reduction Mechanism

P4 adds in-process noise reduction, only affecting statically configured channels and not affecting `send_to_context()` bot-triggered conversation receipts. All configurations default to off; when not set, old behavior is retained.

| Config Key | Default | Description |
| --- | --- | --- |
| `NOTIFICATION_DEDUP_TTL_SECONDS` | `0` | Same stable dedup key sends only once within TTL; `0` disables |
| `NOTIFICATION_COOLDOWN_SECONDS` | `0` | Same cooldown key is rate-limited within window; `0` disables |
| `NOTIFICATION_QUIET_HOURS` | Empty | Quiet hours, format `HH:MM-HH:MM`, supports overnight ranges |
| `NOTIFICATION_TIMEZONE` | Empty | Timezone for quiet hours, e.g., `Asia/Shanghai`; empty uses Python runtime local timezone |
| `NOTIFICATION_MIN_SEVERITY` | Empty | `info`, `warning`, `error`, `critical`; empty does not filter |
| `NOTIFICATION_DAILY_DIGEST_ENABLED` | `false` | Reserved configuration; current implementation does not send daily digests or persist digest content |

Default severity levels:

- `report`: `info`
- `alert`: `warning`
- `system_error`: `error`
- Unknown or unset route: `info`

Implementation boundaries:

- Dedup / cooldown state is a dict in the current Python process, suitable for `main.py` single-process and `--serve` single-worker scenarios.
- Under `uvicorn --workers N`, multi-container, or multi-machine scenarios, state is not shared; noise reduction is approximately effective per-worker.
- Pipeline single-stock and aggregated report paths use stable keys to avoid dedup bypass from report generation time variation; other report notifications without explicitly passed `dedup_key` use content hash dedup.
- Calls without explicitly passed `cooldown_key` share default cooldown slots by route and severity; e.g., report / info normal notifications share the same slot.
- Concurrent sends within the same process for the same key first occupy the short-lived in-flight slot to avoid burst duplicate sends; when all static channels fail, the slot is released without writing to formal dedup / cooldown state.
- On noise reduction judgment exceptions, fail-open: log and continue sending to static channels.
- When `NOTIFICATION_TIMEZONE` is empty, it uses the runtime local timezone parsed by `datetime.now().astimezone()`; for Actions / Docker scenarios, explicitly configuring `NOTIFICATION_TIMEZONE` is recommended to avoid timezone ambiguity.

## WebPush / Apprise Evaluation

P6-D only performs design evaluation, adding no dependencies, `.env` configuration, or runtime notification paths. The conclusion is that neither is suitable for direct channel implementation integration in this round.

If WebPush is to be implemented in the future, subscription lifecycle and security boundaries must first be designed separately:

- Requires Web frontend Service Worker registration; Service Worker / `PushManager.subscribe()` depends on secure context, requiring HTTPS in production and allowing localhost for local development.
- Requires VAPID public/private keys; the public key is distributed during subscription and the private key must be held at send time with a proper key rotation strategy.
- Requires browser permission interaction; subscription must be triggered by user gesture and cannot be silently enabled in the background.
- `PushSubscription` contains endpoint and encryption keys; endpoint is a capability URL that should be treated as a secret with sanitized display.
- Requires persisting subscriptions, handling subscription expiration and device unbinding; the current `.env` / single-process configuration model is not suitable for storing multiple user/device subscriptions.
- APIs for creating, deleting, and updating subscriptions must have authentication and CSRF protection; relying solely on frontend hidden entry points is insufficient.

If Apprise is to be introduced in the future, it should first be evaluated as an optional dependency rather than a default dependency:

- Apprise is a general notification library with broad coverage, but it would overlap with existing first-class channels: WeChat, Telegram, Discord, Slack, ntfy, Gotify, Pushover.
- Dependency size, installation failure paths, Docker image bloat, GitHub Actions dependency caching, and optional extras strategy must be evaluated.
- Secret passing must not expose complete Apprise URLs; unified sanitization, Web test target masking, and error log filtering are required.
- Send failures must be isolated within the Apprise channel without affecting existing channel failure isolation semantics.
- If Apprise is adopted, it is recommended to first add a separate experimental channel or CLI-only spike before deciding whether to include it in the Web settings page and Actions env.

## Local Configuration

Local runs prioritize the project root `.env`. Copy `.env.example` and fill in at least one minimal key to enable the corresponding static notification channel; advanced keys only change authentication, security, formatting, routing, or noise reduction behavior and do not independently enable channels.

```bash
python main.py --check-notify
```

`--check-notify` is read-only diagnostics: no notifications sent, no `.env` written, no analysis flow entered. After configuring WebUI, real test messages can also be sent via single-channel testing in the system settings page; this test only uses page draft temporary configuration and does not save `.env`.

## Docker

Docker scenarios can inject notification-related environment variables via `--env-file .env` / Compose `env_file`. Do not bind-mount the host `.env` as a single file over the container's `/app/.env`, as this may cause atomic replacement or permission issues due to Docker mount point limitations when the Web settings page saves configuration. The newer Web settings page displays startup-injected same-name environment variables as fallback when the active `.env` is missing certain keys; to persist notification configuration across container rebuilds, point `ENV_FILE` to a writable data volume file like `/app/data/runtime.env` and update or remove same-name old values in the startup environment to prevent overwriting on restart.

For noise reduction quiet hours, explicitly configuring `NOTIFICATION_TIMEZONE` is recommended to avoid container default timezone mismatch with expectations. Self-signed intranet webhooks can temporarily use `WEBHOOK_VERIFY_SSL=false`, but do not disable certificate verification on public network links.

## GitHub Actions

The default `00-daily-analysis.yml` only reads Secret / Variable names explicitly mapped in the table. After adding a new repository Secret or Variable, it only enters the runtime process if the variable name appears in the workflow `env:`; arbitrarily numbered variables like `STOCK_GROUP_N` / `EMAIL_GROUP_N` are not auto-imported.

Secrets are suitable for sensitive items like tokens, passwords, webhook URLs; Variables are suitable for non-sensitive behavior configuration like `WECHAT_MSG_TYPE`, `EMAIL_SENDER_NAME`, routing, noise reduction windows, and timezones. `MARKDOWN_TO_IMAGE_CHANNELS` and `MERGE_EMAIL_NOTIFICATION` are not mapped by default; to use them in your own fork, explicitly modify the workflow and add corresponding tests.

## Desktop

The desktop app reuses the Web settings page's notification configuration and single-channel test entry points. Notification tests send real test messages but only use current page draft values and do not auto-save; persistence still requires clicking save configuration.

The desktop app can restore `.env` via configuration export / import. To roll back a notification channel, clear that channel's minimal key and save; advanced keys remain without independently enabling channels, but cleaning them up is recommended to reduce troubleshooting noise later.

## Rollback

- Local / Docker: Restore the old `.env`, or delete the corresponding channel's minimal key and restart the process.
- GitHub Actions: Clear or delete the corresponding Secret / Variable; unmapped keys do not enter the workflow runtime process.
- Desktop: Import the old `.env` via configuration backup, or clear the corresponding channel configuration in the settings page and save.
- Version rollback: P6/P7's new `NTFY_*`, `GOTIFY_*`, routing, and noise reduction keys are ignored in older versions; to avoid confusion, remove them from `.env` or Actions configuration simultaneously.
