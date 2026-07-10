# -*- coding: utf-8 -*-
"""
Slack notification sender service.

Responsibilities:
1. Send Slack messages via Slack Bot API or Incoming Webhook
   (when both are configured, Bot API is preferred to ensure text and images go to the same channel)
"""
import logging
import json
from typing import Optional

import requests

from src.config import Config
from src.formatters import chunk_content_by_max_bytes

logger = logging.getLogger(__name__)

# Slack Block Kit single section block text field limit: 3000 characters
_BLOCK_TEXT_LIMIT = 3000
# Slack chat.postMessage / Webhook text field limit ~40000 chars, conservatively set to 39000
_TEXT_LIMIT = 39000


class SlackSender:

    def __init__(self, config: Config):
        """
        Initialize Slack configuration.

        Args:
            config: Configuration object
        """
        self._slack_webhook_url = getattr(config, 'slack_webhook_url', None)
        self._slack_bot_token = getattr(config, 'slack_bot_token', None)
        self._slack_channel_id = getattr(config, 'slack_channel_id', None)
        self._webhook_verify_ssl = getattr(config, 'webhook_verify_ssl', True)

    @property
    def _use_bot(self) -> bool:
        """When Bot config is complete, prefer Bot API to ensure text and images use the same channel."""
        return bool(self._slack_bot_token and self._slack_channel_id)

    def _is_slack_configured(self) -> bool:
        """Check whether Slack configuration is complete (supports Webhook or Bot API)."""
        return self._use_bot or bool(self._slack_webhook_url)

    def send_to_slack(self, content: str, *, timeout_seconds: Optional[float] = None) -> bool:
        """
        Push a message to Slack (supports Webhook and Bot API).

        Transport priority matches _send_slack_image(): Bot > Webhook,
        to avoid text going via Webhook while images go via Bot, resulting in messages landing in different channels.

        Args:
            content: Message content in Markdown format

        Returns:
            Whether the send succeeded
        """
        # Chunk by byte count to avoid exceeding single message limits
        try:
            chunks = chunk_content_by_max_bytes(content, _TEXT_LIMIT, add_page_marker=True)
        except Exception as e:
            logger.error(f"Failed to split Slack message: {e}, attempting to send as-is.")
            chunks = [content]

        # Prefer Bot API (consistent with _send_slack_image)
        if self._use_bot:
            return all(self._send_slack_bot(chunk, timeout_seconds=timeout_seconds) for chunk in chunks)

        # Fall back to Webhook
        if self._slack_webhook_url:
            return all(self._send_slack_webhook(chunk, timeout_seconds=timeout_seconds) for chunk in chunks)

        logger.warning("Slack configuration incomplete, skipping push")
        return False

    def _build_blocks(self, content: str) -> list:
        """
        Build content as Slack Block Kit format.

        If content exceeds a single section block limit, it will be automatically
        split into multiple blocks.
        """
        blocks = []
        # Split by block text limit
        pos = 0
        while pos < len(content):
            segment = content[pos:pos + _BLOCK_TEXT_LIMIT]
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": segment
                }
            })
            pos += _BLOCK_TEXT_LIMIT
        return blocks

    def _send_slack_webhook(self, content: str, *, timeout_seconds: Optional[float] = None) -> bool:
        """
        Send a message to Slack via Incoming Webhook.

        Args:
            content: Message content

        Returns:
            Whether the send succeeded
        """
        try:
            payload = {
                "text": content,
                "blocks": self._build_blocks(content),
            }
            response = requests.post(
                self._slack_webhook_url,
                data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                headers={'Content-Type': 'application/json; charset=utf-8'},
                timeout=timeout_seconds or 15,
                verify=self._webhook_verify_ssl,
            )
            if response.status_code == 200 and response.text == "ok":
                logger.info("Slack Webhook message sent successfully")
                return True
            logger.error(f"Slack Webhook send failed: HTTP {response.status_code} {response.text[:200]}")
            return False
        except Exception as e:
            logger.error(f"Slack Webhook send exception: {e}")
            return False

    def _send_slack_bot(self, content: str, *, timeout_seconds: Optional[float] = None) -> bool:
        """
        Send a message to Slack via Bot API (chat.postMessage).

        Args:
            content: Message content

        Returns:
            Whether the send succeeded
        """
        try:
            headers = {
                'Authorization': f'Bearer {self._slack_bot_token}',
                'Content-Type': 'application/json; charset=utf-8',
            }
            payload = {
                "channel": self._slack_channel_id,
                "text": content,
                "blocks": self._build_blocks(content),
            }
            response = requests.post(
                'https://slack.com/api/chat.postMessage',
                data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                headers=headers,
                timeout=timeout_seconds or 15,
            )
            result = response.json()
            if result.get("ok"):
                logger.info("Slack Bot message sent successfully")
                return True
            logger.error(f"Slack Bot send failed: {result.get('error', 'unknown')}")
            return False
        except Exception as e:
            logger.error(f"Slack Bot send exception: {e}")
            return False

    def _send_slack_image(self, image_bytes: bytes, fallback_content: str = "") -> bool:
        """
        Send an image to Slack.

        Bot mode uses files.getUploadURLExternal + files.completeUploadExternal
        (Slack's new file upload API); Webhook mode falls back to text.

        Args:
            image_bytes: PNG image bytes
            fallback_content: Fallback text if image send fails

        Returns:
            Whether the send succeeded
        """
        # Bot mode: use new file upload API
        if self._use_bot:
            headers = {'Authorization': f'Bearer {self._slack_bot_token}'}
            try:
                # Step 1: Get upload URL
                resp1 = requests.post(
                    'https://slack.com/api/files.getUploadURLExternal',
                    headers=headers,
                    data={
                        'filename': 'report.png',
                        'length': len(image_bytes),
                    },
                    timeout=30,
                )
                result1 = resp1.json()
                if not result1.get("ok"):
                    logger.error("Slack failed to get upload URL: %s", result1.get('error', 'unknown'))
                    raise RuntimeError(result1.get('error', 'unknown'))

                upload_url = result1['upload_url']
                file_id = result1['file_id']

                # Step 2: Upload file content (raw body, cannot use multipart)
                resp2 = requests.post(
                    upload_url,
                    data=image_bytes,
                    headers={'Content-Type': 'application/octet-stream'},
                    timeout=30,
                )
                if resp2.status_code != 200:
                    logger.error("Slack file upload failed: HTTP %s", resp2.status_code)
                    raise RuntimeError(f"HTTP {resp2.status_code}")

                # Step 3: Complete upload and share to channel
                resp3 = requests.post(
                    'https://slack.com/api/files.completeUploadExternal',
                    headers={**headers, 'Content-Type': 'application/json'},
                    json={
                        'files': [{'id': file_id, 'title': 'Stock Analysis Report'}],
                        'channel_id': self._slack_channel_id,
                    },
                    timeout=30,
                )
                result3 = resp3.json()
                if result3.get("ok"):
                    logger.info("Slack Bot image sent successfully")
                    return True
                logger.error("Slack failed to complete upload: %s", result3.get('error', 'unknown'))
            except Exception as e:
                logger.error("Slack Bot image send exception: %s", e)

        # Webhook mode or Bot upload failed: fall back to text
        if fallback_content:
            logger.info("Slack image not supported or failed, falling back to text")
            return self.send_to_slack(fallback_content)

        logger.warning("Slack image send failed and no fallback content")
        return False
