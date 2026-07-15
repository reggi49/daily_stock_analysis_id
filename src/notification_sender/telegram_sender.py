# -*- coding: utf-8 -*-
"""
Telegram notification sender service.

Responsibilities:
1. Send text messages via Telegram Bot API
2. Send image messages via Telegram Bot API
"""
import logging
from typing import Optional
import requests
import time
import re

from src.config import Config


logger = logging.getLogger(__name__)


class TelegramSender:

    def __init__(self, config: Config):
        """
        Initialize Telegram configuration.

        Args:
            config: Configuration object
        """
        self._telegram_config = {
            'bot_token': getattr(config, 'telegram_bot_token', None),
            'chat_id': getattr(config, 'telegram_chat_id', None),
            'message_thread_id': getattr(config, 'telegram_message_thread_id', None),
        }

    def _is_telegram_configured(self) -> bool:
        """Check whether Telegram configuration is complete."""
        return bool(self._telegram_config['bot_token'] and self._telegram_config['chat_id'])

    def send_to_telegram(
        self,
        content: str,
        *,
        chat_id: Optional[str] = None,
        message_thread_id: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> bool:
        """
        Push a message to a Telegram bot.

        Telegram Bot API format:
        POST https://api.telegram.org/bot<token>/sendMessage
        {
            "chat_id": "xxx",
            "text": "Message content",
            "parse_mode": "Markdown"
        }

        Args:
            content: Message content in Markdown format

        Returns:
            Whether the send succeeded
        """
        target_chat_id = chat_id if chat_id is not None else self._telegram_config.get("chat_id")
        target_message_thread_id = (
            message_thread_id
            if message_thread_id is not None
            else self._telegram_config.get("message_thread_id")
        )

        if not (self._telegram_config["bot_token"] and target_chat_id):
            logger.warning("Telegram configuration incomplete, skipping push")
            return False

        bot_token = self._telegram_config['bot_token']
        chat_id = target_chat_id
        message_thread_id = target_message_thread_id

        try:
            # Telegram API endpoint
            api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

            # Telegram Bot API message length limit for this sender.
            max_length = 3000
            telegram_text = self._convert_to_telegram_markdown(content)

            if len(telegram_text) <= max_length:
                # Single message send
                return self._send_telegram_message(
                    api_url,
                    chat_id,
                    telegram_text,
                    message_thread_id,
                    timeout_seconds=timeout_seconds,
                    prepared_text=True,
                )
            else:
                # Chunked send for long messages after Telegram-specific formatting.
                return self._send_telegram_chunked(
                    api_url,
                    chat_id,
                    telegram_text,
                    max_length,
                    message_thread_id,
                    timeout_seconds=timeout_seconds,
                )

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    def _send_telegram_message(
        self,
        api_url: str,
        chat_id: str,
        text: str,
        message_thread_id: Optional[str] = None,
        *,
        timeout_seconds: Optional[float] = None,
        prepared_text: bool = False,
    ) -> bool:
        """Send a single Telegram message with exponential backoff retry (Fixes #287)"""
        telegram_text = text if prepared_text else self._convert_to_telegram_markdown(text)
        payload = {
            "chat_id": chat_id,
            "text": telegram_text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }

        if message_thread_id:
            payload['message_thread_id'] = message_thread_id

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(api_url, json=payload, timeout=timeout_seconds or 10)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt < max_retries:
                    delay = 2 ** attempt  # 2s, 4s
                    logger.warning(f"Telegram request failed (attempt {attempt}/{max_retries}): {e}, "
                                   f"retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Telegram request failed after {max_retries} attempts: {e}")
                    return False

            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    logger.info("Telegram message sent successfully")
                    return True
                else:
                    error_desc = result.get('description', 'Unknown error')
                    logger.error(f"Telegram returned error: {error_desc}")

                    # If Markdown parsing failed, fall back to plain text
                    if self._should_fallback_to_plain_text(error_desc=error_desc):
                        if self._send_plain_text_fallback(api_url, payload, text, timeout_seconds=timeout_seconds):
                            return True

                    return False
            elif response.status_code == 429:
                # Rate limited — respect Retry-After header
                retry_after = int(response.headers.get('Retry-After', 2 ** attempt))
                if attempt < max_retries:
                    logger.warning(f"Telegram rate limited, retrying in {retry_after}s "
                                   f"(attempt {attempt}/{max_retries})...")
                    time.sleep(retry_after)
                    continue
                else:
                    logger.error(f"Telegram rate limited after {max_retries} attempts")
                    return False
            else:
                if attempt < max_retries and response.status_code >= 500:
                    delay = 2 ** attempt
                    logger.warning(f"Telegram server error HTTP {response.status_code} "
                                   f"(attempt {attempt}/{max_retries}), retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                if self._should_fallback_to_plain_text(response_text=response.text):
                    if self._send_plain_text_fallback(api_url, payload, text, timeout_seconds=timeout_seconds):
                        return True
                logger.error(f"Telegram request failed: HTTP {response.status_code}")
                logger.error(f"Response content: {response.text}")
                return False

        return False

    @staticmethod
    def _should_fallback_to_plain_text(error_desc: str = "", response_text: str = "") -> bool:
        """Detect Telegram Markdown parsing failures that should retry as plain text."""
        haystack = f"{error_desc}\n{response_text}".lower()
        markers = (
            "can't parse entities",
            "can't parse entity",
            "can't find end of the entity",
            "parse entities",
            "parse_mode",
            "markdown",
        )
        return any(marker in haystack for marker in markers)

    def _send_plain_text_fallback(
        self,
        api_url: str,
        payload: dict,
        text: str,
        *,
        timeout_seconds: Optional[float] = None,
    ) -> bool:
        """Retry Telegram send without parse_mode when Markdown parsing fails."""
        logger.info("Telegram Markdown parsing failed, retrying with plain text format...")
        plain_payload = dict(payload)
        plain_payload.pop('parse_mode', None)
        plain_payload['text'] = text

        try:
            response = requests.post(api_url, json=plain_payload, timeout=timeout_seconds or 10)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.error(f"Telegram plain-text fallback failed: {e}")
            return False

        if response.status_code == 200:
            try:
                result = response.json()
            except ValueError:
                logger.error("Telegram plain-text fallback failed: response is not valid JSON")
                logger.error(f"Response content: {response.text}")
                return False

            if result.get('ok'):
                logger.info("Telegram message sent successfully (plain text)")
                return True

            logger.error("Telegram plain-text fallback failed: Telegram API returned ok=false")
            logger.error(f"Response content: {response.text}")
            return False

        logger.error(f"Telegram plain-text fallback failed: HTTP {response.status_code}")
        logger.error(f"Response content: {response.text}")
        return False

    def _send_telegram_chunked(
        self,
        api_url: str,
        chat_id: str,
        telegram_text: str,
        max_length: int,
        message_thread_id: Optional[str] = None,
        *,
        timeout_seconds: Optional[float] = None,
    ) -> bool:
        """Send long Telegram messages in chunks."""
        chunks = self._split_telegram_text(telegram_text, max_length)
        all_success = True
        chunk_index = 1

        for chunk_content in chunks:
            logger.info(f"Sending Telegram message chunk {chunk_index}...")
            if not self._send_telegram_message(
                api_url,
                chat_id,
                chunk_content,
                message_thread_id,
                timeout_seconds=timeout_seconds,
                prepared_text=True,
            ):
                all_success = False
            chunk_index += 1

        return all_success

    @staticmethod
    def _split_telegram_text(text: str, max_length: int) -> list[str]:
        """Split Telegram text into chunks that never exceed max_length."""
        if not text:
            return [text]

        if len(text) <= max_length:
            return [text]

        chunks = []
        current_chunk = []
        current_length = 0

        for line in text.splitlines(keepends=True):
            if len(line) > max_length:
                if current_chunk:
                    chunks.append("".join(current_chunk))
                    current_chunk = []
                    current_length = 0

                for start in range(0, len(line), max_length):
                    chunks.append(line[start:start + max_length])
                continue

            if current_chunk and current_length + len(line) > max_length:
                chunks.append("".join(current_chunk))
                current_chunk = [line]
                current_length = len(line)
                continue

            current_chunk.append(line)
            current_length += len(line)

        if current_chunk:
            chunks.append("".join(current_chunk))

        return chunks

    def _send_telegram_photo(self, image_bytes: bytes) -> bool:
        """Send image via Telegram sendPhoto API (Issue #289)."""
        if not self._is_telegram_configured():
            return False
        bot_token = self._telegram_config['bot_token']
        chat_id = self._telegram_config['chat_id']
        message_thread_id = self._telegram_config.get('message_thread_id')
        api_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        try:
            data = {"chat_id": chat_id}
            if message_thread_id:
                data['message_thread_id'] = message_thread_id
            files = {"photo": ("report.png", image_bytes, "image/png")}
            response = requests.post(api_url, data=data, files=files, timeout=30)
            if response.status_code == 200 and response.json().get('ok'):
                logger.info("Telegram image sent successfully")
                return True
            logger.error("Telegram image send failed: %s", response.text[:200])
            return False
        except Exception as e:
            logger.error("Telegram image send exception: %s", e)
            return False

    def _convert_to_telegram_markdown(self, text: str) -> str:
        """
        Convert standard Markdown to Telegram-compatible format.

        Telegram Markdown limitations:
        - Does not support # headings
        - Uses *bold* instead of **bold**
        - Uses _italic_
        """
        result = text

        # Remove # heading markers (not supported by Telegram)
        result = re.sub(r'^#{1,6}\s+', '', result, flags=re.MULTILINE)

        # Convert **bold** to *bold*
        result = re.sub(r'\*\*(.+?)\*\*', r'*\1*', result)

        # Escape special characters for Telegram Markdown, but preserve link syntax [text](url)
        # Step 1: temporarily protect markdown links
        import uuid as _uuid
        _link_placeholder = f"__LINK_{_uuid.uuid4().hex[:8]}__"
        _links = []
        def _save_link(m):
            _links.append(m.group(0))
            return f"{_link_placeholder}{len(_links) - 1}"
        result = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', _save_link, result)

        # Step 2: escape remaining special chars
        for char in ['[', ']', '(', ')']:
            result = result.replace(char, f'\\{char}')

        # Step 3: restore links
        for i, link in enumerate(_links):
            result = result.replace(f"{_link_placeholder}{i}", link)

        return result
