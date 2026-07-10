# -*- coding: utf-8 -*-
"""
===================================
Bot Message Models
===================================

Unified message and response models that abstract away platform differences.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List


class ChatType(str, Enum):
    """Chat type"""
    GROUP = "group"      # Group chat
    PRIVATE = "private"  # Private chat
    UNKNOWN = "unknown"  # Unknown


class Platform(str, Enum):
    """Platform type"""
    FEISHU = "feishu"        # Feishu
    DINGTALK = "dingtalk"    # DingTalk
    WECOM = "wecom"          # WeCom (Enterprise WeChat)
    TELEGRAM = "telegram"    # Telegram
    UNKNOWN = "unknown"      # Unknown


@dataclass
class BotMessage:
    """
    Unified bot message model.

    Normalizes all platform message formats into this model
    for easy processing by command handlers.

    Attributes:
        platform: Platform identifier
        message_id: Message ID (platform-native ID)
        user_id: Sender ID
        user_name: Sender name
        chat_id: Chat ID (group ID or private chat ID)
        chat_type: Chat type
        content: Message text (bot @mention removed)
        raw_content: Raw message content
        mentioned: Whether the bot was @mentioned
        mentions: List of @mentioned users
        timestamp: Message timestamp
        raw_data: Raw request data (platform-specific, for debugging)
    """
    platform: str
    message_id: str
    user_id: str
    user_name: str
    chat_id: str
    chat_type: ChatType
    content: str
    raw_content: str = ""
    mentioned: bool = False
    mentions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def get_command_and_args(self, prefix: str = "/") -> tuple:
        """
        Parse command and arguments.

        Args:
            prefix: Command prefix, defaults to "/"

        Returns:
            (command, args) tuple, e.g. ("analyze", ["600519"])
            Returns (None, []) if not a command.
        """
        text = self.content.strip()

        # Check if text starts with the command prefix
        if not text.startswith(prefix):
            # Try matching text-based commands (no prefix)
            text_commands = {
                'analyze': 'analyze',
                'market': 'market',
                'batch': 'batch',
                'help': 'help',
                'status': 'status',
            }
            for cn_cmd, en_cmd in text_commands.items():
                if text.startswith(cn_cmd):
                    args = text[len(cn_cmd):].strip().split()
                    return en_cmd, args
            return None, []

        # Strip prefix
        text = text[len(prefix):]

        # Split command and arguments
        parts = text.split()
        if not parts:
            return None, []

        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        return command, args

    def is_command(self, prefix: str = "/") -> bool:
        """Check if the message is a command"""
        cmd, _ = self.get_command_and_args(prefix)
        return cmd is not None


@dataclass
class BotResponse:
    """
    Unified bot response model.

    Command handlers return this model, which is then converted
    to platform-specific format by the platform adapter.

    Attributes:
        text: Reply text
        markdown: Whether the text is Markdown formatted
        at_user: Whether to @mention the sender
        reply_to_message: Whether to reply to the original message
        extra: Additional data (platform-specific)
    """
    text: str
    markdown: bool = False
    at_user: bool = True
    reply_to_message: bool = True
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def text_response(cls, text: str, at_user: bool = True) -> 'BotResponse':
        """Create a plain text response"""
        return cls(text=text, markdown=False, at_user=at_user)

    @classmethod
    def markdown_response(cls, text: str, at_user: bool = True) -> 'BotResponse':
        """Create a Markdown response"""
        return cls(text=text, markdown=True, at_user=at_user)

    @classmethod
    def error_response(cls, message: str) -> 'BotResponse':
        """Create an error response"""
        return cls(text=f"❌ Error: {message}", markdown=False, at_user=True)


@dataclass
class WebhookResponse:
    """
    Webhook response model.

    Platform adapters return this model, containing the HTTP response content.

    Attributes:
        status_code: HTTP status code
        body: Response body (dict, will be JSON-serialized)
        headers: Additional response headers
    """
    status_code: int = 200
    body: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def success(cls, body: Optional[Dict] = None) -> 'WebhookResponse':
        """Create a success response"""
        return cls(status_code=200, body=body or {})

    @classmethod
    def challenge(cls, challenge: str) -> 'WebhookResponse':
        """Create a verification response (for platform URL verification)"""
        return cls(status_code=200, body={"challenge": challenge})

    @classmethod
    def error(cls, message: str, status_code: int = 400) -> 'WebhookResponse':
        """Create an error response"""
        return cls(status_code=status_code, body={"error": message})
