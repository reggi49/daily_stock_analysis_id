# Feishu Notification Configuration Guide

This document addresses two common scenarios:

1. Pushing analysis results to a Feishu group
2. Avoiding confusion between Feishu App mode, App Bot proactive push, and group bot Webhook mode

## Distinguish Between Two Modes

### Mode 1: Group Bot Webhook Push

Use cases:
- You only want to push analysis reports to a Feishu group
- You don't need to handle Feishu message callbacks
- You don't need Stream Bot

This is the most recommended and easiest Feishu notification method for this project.

Required variables:

```env
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your_hook_token
# Fill in as needed
FEISHU_WEBHOOK_SECRET=your_sign_secret
FEISHU_WEBHOOK_KEYWORD=Stock Daily Report
```

### Mode 2: Feishu App / App Bot / Stream Bot / Cloud Docs

Use cases:
- You want to use the Feishu App Bot to proactively push notifications to a specific group or user
- You want to build Feishu app bot interactions
- You want to enable Stream mode
- You want to use Feishu cloud doc capabilities

Related variables:

```env
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
# Required for App Bot proactive push
FEISHU_CHAT_ID=oc_xxx
# Set open_id for private chats; group chats use chat_id by default
FEISHU_RECEIVE_ID_TYPE=chat_id
# Only enable for event subscriptions / Stream Bot
FEISHU_STREAM_ENABLED=true
```

Notes:
- `FEISHU_APP_ID` / `FEISHU_APP_SECRET` will NOT enable group Webhook push
- For simple group notifications, configure `FEISHU_WEBHOOK_URL` first
- Without Webhook, App Bot proactive push requires `FEISHU_APP_ID`, `FEISHU_APP_SECRET`, and `FEISHU_CHAT_ID` all configured
- `FEISHU_STREAM_ENABLED` only represents event subscriptions / Stream Bot; it does not factor into whether proactive notifications are configured
- If you are building an app bot / Stream Bot, refer to the original workflow screenshots at the end of this document
- The App Bot send path reuses `lark-oapi>=1.0.0` already in `requirements.txt`; install via `pip install -r requirements.txt`. References: [Feishu message create OpenAPI](https://open.feishu.cn/document/server-docs/im-v1/message/create), [lark-oapi PyPI](https://pypi.org/project/lark-oapi/), and [SDK repo](https://github.com/larksuite/oapi-sdk-python)

### File Send Mode (FEISHU_SEND_AS_FILE)

When enabled, the Feishu App Bot sends reports as `.md` files instead of text/card messages:

```bash
FEISHU_SEND_AS_FILE=true
```

- **Required permissions**: `im:message` (send messages) + `im:file` (upload files)
- **Dependency version**: `lark-oapi>=1.0.0` must include the `im.v1.file.create` API (file upload class)
- **Webhook mode**: Falls back to sending file content as text (Webhook does not support file upload)
- **Scope**: Only applies to `route_type="report"` report pushes; alerts and system notifications are not affected
- **GitHub Actions scheduled tasks**: Already mapped via `.github/workflows/00-daily-analysis.yml`; add the same variable or secret in repo Settings → Secrets and variables → Actions to enable
- **Configuration methods**: Supports `.env` file, GitHub Actions Secret/Variable, or Web/Desktop settings page

## Correct Webhook Configuration Steps

### 1. Create a Custom Bot in a Feishu Group

Typical path:
- Group Chat
- Group Settings
- Group Bots
- Add Bot
- Custom Bot

After creation, copy the Webhook URL provided by the bot.

Example:

```env
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### 2. Check Bot Security Settings

Feishu group bots typically have three security options:

1. No security settings
2. "Keyword" enabled
3. "Signature verification" enabled

If your bot has additional security enabled, the project must also be configured accordingly; otherwise, requests will be rejected by Feishu.

#### Keyword Enabled

Write the same keyword configured in Feishu to:

```env
FEISHU_WEBHOOK_KEYWORD=Stock Daily Report
```

The project will automatically prepend this keyword to every Feishu message; you don't need to manually modify the report template.

#### Signature Verification Enabled

Write the secret shown in Feishu to:

```env
FEISHU_WEBHOOK_SECRET=your_sign_secret
```

The project will automatically add `timestamp` and `sign` to each message as required by Feishu.

### 3. Start and Verify

As long as `FEISHU_WEBHOOK_URL` is configured, notification sending will go through the Webhook channel.

If you also fill in:

```env
FEISHU_APP_ID=...
FEISHU_APP_SECRET=...
```

It will not affect Webhook push; but these alone cannot replace `FEISHU_WEBHOOK_URL`.

If Webhook is not configured, you can also use App Bot proactive push:

```env
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_CHAT_ID=oc_xxx
FEISHU_RECEIVE_ID_TYPE=chat_id
```

In this case, `FEISHU_STREAM_ENABLED` does not need to be enabled; it is only for event subscriptions / Stream Bot.

### 4. Configure Webhook Trigger in Feishu Automation

If you consume card messages pushed by this project in a Feishu automation workflow, configure as follows:

1. When creating the Webhook trigger, enter the following JSON as **parameters** (`content` can retain placeholders as needed):

```json
{
  "msg_type": "interactive",
  "card": {
    "config": { "wide_screen_mode": true },
    "elements": [
      {
        "tag": "div",
        "text": {
          "tag": "lark_md",
          "content": "..."
        }
      }
    ],
    "header": {
      "title": {
        "tag": "plain_text",
        "content": "AI Stock Analysis Report"
      }
    }
  }
}
```

2. In the **Action/Message Content** section, do not manually enter plain text; click the plus sign, select **Webhook Trigger**, and map to:

`card.elements[0].text.content`

![img_11.png](img_11.png)

## Most Common Failure Causes

### 1. Only Configured `FEISHU_APP_ID` / `FEISHU_APP_SECRET`

Symptom:
- You think "Feishu is already configured"
- But you receive no group notifications at all

Cause:
- These two variables are only app credentials; proactive push also needs `FEISHU_CHAT_ID`, and group Webhook push needs `FEISHU_WEBHOOK_URL`

Correct action:
- Simple group push: Add `FEISHU_WEBHOOK_URL`
- App Bot proactive push: Add `FEISHU_CHAT_ID`, and confirm the app has message sending permissions and the bot is in the target group

### 2. Feishu Bot Has Keyword Enabled, but `FEISHU_WEBHOOK_KEYWORD` Is Not Configured Locally

Symptom:
- Other apps can send
- This project cannot send, or Feishu returns a verification failure

Correct action:
- Copy the keyword from the Feishu bot security settings exactly into `FEISHU_WEBHOOK_KEYWORD`

### 3. Feishu Bot Has Signature Verification Enabled, but `FEISHU_WEBHOOK_SECRET` Is Not Configured Locally

Symptom:
- The Webhook URL looks correct
- But Feishu returns a signature-related error

Correct action:
- Enter the bot secret into `FEISHU_WEBHOOK_SECRET`

### 4. Bot Is Not in the Target Group, or Lacks Sending Permissions

Check:
- Whether the bot has actually been added to the target group
- Whether the group admin has restricted the bot's message sending

### 5. Feishu Has IP Whitelist Configured

If you run on a cloud server, Docker, or GitHub Actions, the outbound IP may differ from your local machine.

Check:
- Whether the Feishu bot has IP whitelist enabled
- Whether the current runtime environment's outbound IP is in the whitelist

## Recommended Minimum Viable Configuration

### No Additional Security Restrictions

```env
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your_hook_token
```

### Keyword Enabled

```env
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your_hook_token
FEISHU_WEBHOOK_KEYWORD=Stock Daily Report
```

### Signature Verification Enabled

```env
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your_hook_token
FEISHU_WEBHOOK_SECRET=your_sign_secret
```

### Both Keyword and Signature Enabled

```env
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your_hook_token
FEISHU_WEBHOOK_SECRET=your_sign_secret
FEISHU_WEBHOOK_KEYWORD=Stock Daily Report
```

## Recommended Troubleshooting Order

1. First confirm whether you want "group Webhook push" or "App / Stream Bot"
2. For simple group push, first ensure `FEISHU_WEBHOOK_URL` is configured
3. For App Bot proactive push without Webhook, confirm `FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_CHAT_ID` are all present
4. Return to the Feishu bot security settings to confirm whether keyword or signature is enabled
5. If enabled, fill in `FEISHU_WEBHOOK_KEYWORD` / `FEISHU_WEBHOOK_SECRET`
6. Finally, check if the bot is in the group, has permissions, and is not blocked by IP whitelist

## Appendix: App / Stream Bot Original Workflow Screenshots

If you are not just doing group Webhook push but need to further configure the Feishu app, long-connection bot, or cloud docs, refer to the following screenshots.

### 1. Create Application

https://open.feishu.cn/document/develop-an-echo-bot/introduction

![img_6.png](img_6.png)

![img_8.png](img_8.png)

### 2. Get Credentials

![img_7.png](img_7.png)

### 3. Publish Application

![img_5.png](img_5.png)

### 4. Open the Application in Feishu

![img_9.png](img_9.png)

### 5. Message Interaction

![img_10.png](img_10.png)
