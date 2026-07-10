# -*- coding: utf-8 -*-
"""
===================================
Bot Command Trigger System
===================================

Trigger stock analysis and other features by @mentioning the bot or sending commands.
Supports Feishu, DingTalk, WeCom (Enterprise WeChat), Telegram, and more.

Module structure:
- models.py: Unified message/response models
- dispatcher.py: Command dispatcher
- commands/: Command handlers
- platforms/: Platform adapters
- handler.py: Webhook handler

Usage:
1. Configure environment variables (tokens for each platform, etc.)
2. Start the WebUI service
3. Configure Webhook URL on each platform:
   - Feishu: http://your-server/bot/feishu
   - DingTalk: http://your-server/bot/dingtalk
   - WeCom (Enterprise WeChat): http://your-server/bot/wecom
   - Telegram: http://your-server/bot/telegram

Supported commands:
- /analyze <stock_code>  - Analyze a specific stock
- /market               - Market Review
- /batch                - Batch analyze watchlist stocks
- /help                 - Show help
- /status               - System status
"""

from bot.models import BotMessage, BotResponse, ChatType, WebhookResponse
from bot.dispatcher import CommandDispatcher, get_dispatcher

__all__ = [
    'BotMessage',
    'BotResponse',
    'ChatType',
    'WebhookResponse',
    'CommandDispatcher',
    'get_dispatcher',
]
