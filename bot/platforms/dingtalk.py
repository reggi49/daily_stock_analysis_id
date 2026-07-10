# -*- coding: utf-8 -*-
"""
===================================
DingTalk Platform Adapter
===================================

Handles DingTalk bot Webhook callbacks.

DingTalk bot docs:
https://open.dingtalk.com/document/robots/robot-overview
"""

import hashlib
import hmac
import base64
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import quote_plus

from bot.platforms.base import BotPlatform
from bot.models import BotMessage, BotResponse, WebhookResponse, ChatType

logger = logging.getLogger(__name__)


class DingtalkPlatform(BotPlatform):
    """
    DingTalk platform adapter.

    Supports:
    - Enterprise internal bot callback
    - Group bot Outgoing callback
    - Message signature verification

    Configuration requirements:
    - DINGTALK_APP_KEY: App AppKey
    - DINGTALK_APP_SECRET: App AppSecret (for signature verification)
    """

    def __init__(self):
        from src.config import get_config
        config = get_config()

        self._app_key = getattr(config, 'dingtalk_app_key', None)
        self._app_secret = getattr(config, 'dingtalk_app_secret', None)

    @property
    def platform_name(self) -> str:
        return "dingtalk"

    def verify_request(self, headers: Dict[str, str], body: bytes) -> bool:
        """
        Verify DingTalk request signature.

        DingTalk signature algorithm:
        1. Get timestamp and sign
        2. Calculate: base64(hmac_sha256(timestamp + "\n" + app_secret))
        3. Compare signature
        """
        if not self._app_secret:
            logger.warning("[DingTalk] app_secret not configured, skipping signature verification")
            return True

        timestamp = headers.get('timestamp', '')
        sign = headers.get('sign', '')

        if not timestamp or not sign:
            logger.warning("[DingTalk] Missing signature parameters")
            return True  # May be a request that doesn't require a signature

        # Verify timestamp (valid within 1 hour)
        try:
            request_time = int(timestamp)
            current_time = int(time.time() * 1000)
            if abs(current_time - request_time) > 3600 * 1000:
                logger.warning("[DingTalk] Timestamp expired")
                return False
        except ValueError:
            logger.warning("[DingTalk] Invalid timestamp")
            return False

        # Calculate signature
        string_to_sign = f"{timestamp}\n{self._app_secret}"
        hmac_code = hmac.new(
            self._app_secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        expected_sign = base64.b64encode(hmac_code).decode('utf-8')

        if sign != expected_sign:
            logger.warning(f"[DingTalk] Signature verification failed")
            return False

        return True

    def handle_challenge(self, data: Dict[str, Any]) -> Optional[WebhookResponse]:
        """DingTalk does not require URL verification"""
        return None

    def parse_message(self, data: Dict[str, Any]) -> Optional[BotMessage]:
        """
        Parse DingTalk message.

        DingTalk Outgoing bot message format:
        {
            "msgtype": "text",
            "text": {
                "content": "@bot /analyze 600519"
            },
            "msgId": "xxx",
            "createAt": "1234567890",
            "conversationType": "2",  # 1=private chat, 2=group chat
            "conversationId": "xxx",
            "conversationTitle": "group name",
            "senderId": "xxx",
            "senderNick": "user nickname",
            "senderCorpId": "xxx",
            "senderStaffId": "xxx",
            "chatbotUserId": "xxx",
            "atUsers": [{"dingtalkId": "xxx", "staffId": "xxx"}],
            "isAdmin": false,
            "sessionWebhook": "https://oapi.dingtalk.com/robot/sendBySession?session=xxx",
            "sessionWebhookExpiredTime": 1234567890
        }
        """
        # Check message type
        msg_type = data.get('msgtype', '')
        if msg_type != 'text':
            logger.debug(f"[DingTalk] Ignoring non-text message: {msg_type}")
            return None

        # Get message content
        text_content = data.get('text', {})
        raw_content = text_content.get('content', '')

        # Extract command (remove @bot)
        content = self._extract_command(raw_content)

        # Check if bot was @mentioned
        at_users = data.get('atUsers', [])
        mentioned = len(at_users) > 0

        # Chat type
        conversation_type = data.get('conversationType', '')
        if conversation_type == '1':
            chat_type = ChatType.PRIVATE
        elif conversation_type == '2':
            chat_type = ChatType.GROUP
        else:
            chat_type = ChatType.UNKNOWN

        # Create timestamp
        create_at = data.get('createAt', '')
        try:
            timestamp = datetime.fromtimestamp(int(create_at) / 1000)
        except (ValueError, TypeError):
            timestamp = datetime.now()

        # Save session webhook for replies
        session_webhook = data.get('sessionWebhook', '')

        return BotMessage(
            platform=self.platform_name,
            message_id=data.get('msgId', ''),
            user_id=data.get('senderId', ''),
            user_name=data.get('senderNick', ''),
            chat_id=data.get('conversationId', ''),
            chat_type=chat_type,
            content=content,
            raw_content=raw_content,
            mentioned=mentioned,
            mentions=[u.get('dingtalkId', '') for u in at_users],
            timestamp=timestamp,
            raw_data={
                **data,
                '_session_webhook': session_webhook,
            },
        )

    def _extract_command(self, text: str) -> str:
        """
        Extract command content (remove @bot).

        DingTalk's @user format is typically @nickname followed by a space.
        """
        # Simple handling: remove leading @xxx part
        import re
        # Match leading @xxx (could be Chinese or English)
        text = re.sub(r'^@[\S]+\s*', '', text.strip())
        return text.strip()

    def format_response(
        self,
        response: BotResponse,
        message: BotMessage
    ) -> WebhookResponse:
        """
        Format DingTalk response.

        DingTalk Outgoing bot can return messages directly in the response.
        Can also use sessionWebhook for async sending.

        Response format:
        {
            "msgtype": "text" | "markdown",
            "text": {"content": "xxx"},
            "markdown": {"title": "xxx", "text": "xxx"},
            "at": {"atUserIds": ["xxx"], "isAtAll": false}
        }
        """
        if not response.text:
            return WebhookResponse.success()

        # Build response
        if response.markdown:
            body = {
                "msgtype": "markdown",
                "markdown": {
                    "title": "Stock Analysis Assistant",
                    "text": response.text,
                }
            }
        else:
            body = {
                "msgtype": "text",
                "text": {
                    "content": response.text,
                }
            }

        # @sender
        if response.at_user and message.user_id:
            body["at"] = {
                "atUserIds": [message.user_id],
                "isAtAll": False,
            }

        return WebhookResponse.success(body)

    def send_by_session_webhook(
        self,
        session_webhook: str,
        response: BotResponse,
        message: BotMessage
    ) -> bool:
        """
        Send message via sessionWebhook.

        Suitable for async sending or multi-message scenarios.

        Args:
            session_webhook: DingTalk-provided session Webhook URL
            response: Response object
            message: Original message object

        Returns:
            Whether the send was successful
        """
        if not session_webhook:
            logger.warning("[DingTalk] No available sessionWebhook")
            return False

        import requests

        try:
            # Build message
            if response.markdown:
                payload = {
                    "msgtype": "markdown",
                    "markdown": {
                        "title": "Stock Analysis Assistant",
                        "text": response.text,
                    }
                }
            else:
                payload = {
                    "msgtype": "text",
                    "text": {
                        "content": response.text,
                    }
                }

            # @sender
            if response.at_user and message.user_id:
                payload["at"] = {
                    "atUserIds": [message.user_id],
                    "isAtAll": False,
                }

            # Send request
            resp = requests.post(
                session_webhook,
                json=payload,
                timeout=10
            )

            if resp.status_code == 200:
                result = resp.json()
                if result.get('errcode') == 0:
                    logger.info("[DingTalk] sessionWebhook sent successfully")
                    return True
                else:
                    logger.error(f"[DingTalk] sessionWebhook send failed: {result}")
                    return False
            else:
                logger.error(f"[DingTalk] sessionWebhook request failed: {resp.status_code}")
                return False

        except Exception as e:
            logger.error(f"[DingTalk] sessionWebhook send exception: {e}")
            return False
