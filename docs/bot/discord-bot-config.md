# Discord Bot Configuration

## Discord Bot
Discord bot message receiving requires creating a bot application via the Discord Developer Portal
https://discord.com/developers/applications

Discord bot supports two message delivery methods:
1. **Webhook mode**: Simple configuration, low permissions, suitable for send-only scenarios
2. **Bot API mode**: Higher permissions, supports receiving commands, requires Bot Token and Channel ID

## Creating a Discord Bot

### 1. Log in to Discord Developer Portal
Visit https://discord.com/developers/applications and log in with your Discord account.

### 2. Create an Application
Click the "New Application" button, enter an application name (e.g., AI Stock Analysis Bot), then click "Create".

### 3. Configure the Bot
In the left navigation bar, click "Bot", then click "Add Bot" and confirm.

### 4. Get Bot Token
On the Bot page, click "Reset Token", then copy the generated token (this is your `DISCORD_BOT_TOKEN`).

### 5. Configure Permissions
On the Bot page, under "Privileged Gateway Intents", enable the following:
- Presence Intent
- Server Members Intent
- Message Content Intent

### 6. Add to Server
1. In the left navigation bar, click "OAuth2" > "URL Generator"
2. Under "Scopes", select:
   - `bot`
   - `applications.commands`
3. Under "Bot Permissions", select:
   - Send Messages
   - Embed Links
   - Attach Files
   - Read Message History
   - Use Slash Commands
4. Copy the generated URL, open it in a browser, and select the server to add the bot to.

### 7. Get Channel ID
1. In the Discord client, enable Developer Mode: Settings > Advanced > Developer Mode
2. Right-click the channel where you want the bot to send messages and select "Copy ID" (this is your `DISCORD_MAIN_CHANNEL_ID`).

## Environment Variable Configuration

Add the following to your `.env` file:

```env
# Discord Bot Configuration
DISCORD_BOT_TOKEN=your-discord-bot-token
DISCORD_MAIN_CHANNEL_ID=your-channel-id
DISCORD_WEBHOOK_URL=your-webhook-url (optional)
DISCORD_INTERACTIONS_PUBLIC_KEY=your-public-key (only required for inbound Interaction/Webhook callbacks)
DISCORD_BOT_STATUS=AI Stock Analysis | /help
```

If you have configured Discord Interaction / Webhook inbound callbacks, you must copy the public key from the Discord Developer Portal's `General Information -> Public Key` and enter it in `DISCORD_INTERACTIONS_PUBLIC_KEY`. The system uses this key to verify the Ed25519 signature of each inbound request; requests that fail verification are rejected.

## Webhook Mode Configuration (Optional)

If you only want to use Webhook mode for sending messages and don't need a Bot Token, follow these steps:

1. Right-click a channel and select "Edit Channel"
2. Click "Integrations" > "Webhooks" > "New Webhook"
3. Configure the webhook name and avatar
4. Copy the Webhook URL (this is your `DISCORD_WEBHOOK_URL`)

## Supported Commands

Discord bot supports the following slash commands:

1. `/analyze <stock_code> [full_report]` - Analyze a specific stock code
   - `stock_code`: Stock code, e.g., 600519
   - `full_report`: Optional, whether to generate a full report (including market review)

2. `/market_review` - Get the market review report

3. `/help` - Show help information

## Testing the Bot

1. Ensure the bot has been successfully added to your server
2. Type `/help` in a channel; the bot should return help information
3. Type `/analyze 600519` to test stock analysis
4. Type `/market_review` to test market review

## Important Notes

1. Ensure your bot has sufficient permissions to send messages and use slash commands in channels
2. Regularly update your Bot Token for security
3. Never share your Bot Token with anyone
4. If the bot is not responding, check:
   - Whether the Bot Token is correct
   - Whether the Channel ID is correct
   - Whether the bot is online
   - Whether the bot has message sending permissions

## Troubleshooting

- **Bot does not respond to commands**: Check Bot Token and Channel ID are correct; ensure the bot has been added to the server
- **Slash commands not showing**: Wait a while (Discord needs to sync commands), or re-add the bot
- **Message sending failed**: Check channel permissions; ensure the bot has message sending permissions

## Related Links

- [Discord Developer Portal](https://discord.com/developers/applications)
- [Discord Bot Documentation](https://discordpy.readthedocs.io/en/stable/)
- [Discord Slash Commands](https://discord.com/developers/docs/interactions/application-commands)
