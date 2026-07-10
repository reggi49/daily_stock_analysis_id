# -*- coding: utf-8 -*-
"""
WeChat Work notification sender service.

Responsibilities:
1. Send text messages via WeChat Work Webhook
2. Send image messages via WeChat Work Webhook
"""
import logging
import base64
import hashlib
import requests
import time
from typing import Optional

from src.config import Config
from src.formatters import chunk_content_by_max_bytes


logger = logging.getLogger(__name__)


# WeChat Work image msgtype limit ~2MB (base64 payload)
WECHAT_IMAGE_MAX_BYTES = 2 * 1024 * 1024

class WechatSender:
    
    def __init__(self, config: Config):
        """
        Initialize WeChat Work configuration.

        Args:
            config: Configuration object
        """
        self._wechat_url = config.wechat_webhook_url
        self._wechat_max_bytes = getattr(config, 'wechat_max_bytes', 4000)
        self._wechat_msg_type = getattr(config, 'wechat_msg_type', 'markdown')
        self._webhook_verify_ssl = getattr(config, 'webhook_verify_ssl', True)
        
    def send_to_wechat(self, content: str, *, timeout_seconds: Optional[float] = None) -> bool:
        """
        Push a message to a WeChat Work bot.

        WeChat Work Webhook message formats:
        Supports both markdown and text types. Markdown is not rendered in WeChat, so text type can be used instead.
        Markdown type parses markdown formatting; text type sends plain text directly.

        Markdown example:
        {
            "msgtype": "markdown",
            "markdown": {
                "content": "## Title\n\nContent"
            }
        }

        Text example:
        {
            "msgtype": "text",
            "text": {
                "content": "Content"
            }
        }

        Note: WeChat Work Markdown limit is 4096 bytes (not characters), Text type limit is 2048 bytes.
        Long content will be automatically chunked. Adjustable via WECHAT_MAX_BYTES env var.

        Args:
            content: Message content in Markdown format

        Returns:
            Whether the send succeeded
        """
        if not self._wechat_url:
            logger.warning("WeChat Work Webhook not configured, skipping push")
            return False
        
        # Dynamically limit based on message type to avoid text type exceeding WeChat Work's 2048-byte limit
        if self._wechat_msg_type == 'text':
            max_bytes = min(self._wechat_max_bytes, 2000)  # Reserve bytes for system/pagination markers
        else:
            max_bytes = self._wechat_max_bytes  # markdown default 4000 bytes
        
        # Check byte length; chunk if too long
        content_bytes = len(content.encode('utf-8'))
        if content_bytes > max_bytes:
            logger.info(f"Message content too long ({content_bytes} bytes/{len(content)} chars), will chunk")
            return self._send_wechat_chunked(content, max_bytes)
        
        try:
            return self._send_wechat_message(content, timeout_seconds=timeout_seconds)
        except Exception as e:
            logger.error(f"Failed to send WeChat Work message: {e}")
            return False

    def _send_wechat_image(self, image_bytes: bytes) -> bool:
        """Send image via WeChat Work webhook msgtype image (Issue #289)."""
        if not self._wechat_url:
            return False
        if len(image_bytes) > WECHAT_IMAGE_MAX_BYTES:
            logger.warning(
                "WeChat Work image exceeds limit (%d > %d bytes), refusing to send; caller should fall back to text",
                len(image_bytes), WECHAT_IMAGE_MAX_BYTES,
            )
            return False
        try:
            b64 = base64.b64encode(image_bytes).decode("ascii")
            md5_hash = hashlib.md5(image_bytes).hexdigest()
            payload = {
                "msgtype": "image",
                "image": {"base64": b64, "md5": md5_hash},
            }
            response = requests.post(
                self._wechat_url, json=payload, timeout=30, verify=self._webhook_verify_ssl
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("errcode") == 0:
                    logger.info("WeChat Work image sent successfully")
                    return True
                logger.error("WeChat Work image send failed: %s", result.get("errmsg", ""))
            else:
                logger.error("WeChat Work request failed: HTTP %s", response.status_code)
            return False
        except Exception as e:
            logger.error("WeChat Work image send exception: %s", e)
            return False
    
    def _send_wechat_message(self, content: str, *, timeout_seconds: Optional[float] = None) -> bool:
        """Send a WeChat Work message."""
        payload = self._gen_wechat_payload(content)
        
        response = requests.post(
            self._wechat_url,
            json=payload,
            timeout=timeout_seconds or 10,
            verify=self._webhook_verify_ssl
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('errcode') == 0:
                logger.info("WeChat Work message sent successfully")
                return True
            else:
                logger.error(f"WeChat Work returned error: {result}")
                return False
        else:
            logger.error(f"WeChat Work request failed: {response.status_code}")
            return False
        
    def _send_wechat_chunked(self, content: str, max_bytes: int) -> bool:
        """
        Send long messages to WeChat Work in chunks.

        Intelligently splits by stock analysis blocks (separated by --- or ###)
        to ensure each chunk stays within the limit.

        Args:
            content: Full message content
            max_bytes: Maximum bytes per message

        Returns:
            Whether all chunks sent successfully
        """
        chunks = chunk_content_by_max_bytes(content, max_bytes, add_page_marker=True)
        total_chunks = len(chunks)
        success_count = 0
        for i, chunk in enumerate(chunks):
            if self._send_wechat_message(chunk):
                success_count += 1
            else:
                logger.error(f"WeChat Work chunk {i+1}/{total_chunks} failed")
            if i < total_chunks - 1:
                time.sleep(1)
        return success_count == len(chunks)

    def _gen_wechat_payload(self, content: str) -> dict:
        """Generate WeChat Work message payload."""
        if self._wechat_msg_type == 'text':
            return {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }
        else:
            return {
                "msgtype": "markdown",
                "markdown": {
                    "content": content
                }
            }
