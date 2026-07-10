# -*- coding: utf-8 -*-
"""
===================================
Discord Platform Adapter
===================================

Responsibilities:
1. Verify Discord Webhook requests
2. Parse Discord messages into unified format
3. Convert responses to Discord format
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List

import requests
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from bot.platforms.base import BotPlatform
from bot.models import BotMessage, WebhookResponse, ChatType


logger = logging.getLogger(__name__)


class DiscordPlatform(BotPlatform):
    """Discord platform adapter"""

    def __init__(self):
        from src.config import get_config

        config = get_config()
        self._interactions_public_key = (
            getattr(config, "discord_interactions_public_key", None) or ""
        ).strip()

    @property
    def platform_name(self) -> str:
        """Platform identifier name"""
        return "discord"

    def verify_request(self, headers: Dict[str, str], body: bytes) -> bool:
        """Verify Discord Webhook request signature.

        Discord Webhook signature verification:
        1. Get X-Signature-Ed25519 and X-Signature-Timestamp from request headers
        2. Verify signature using public key

        Args:
            headers: HTTP request headers
            body: Raw request body bytes

        Returns:
            Whether the signature is valid
        """
        if not self._interactions_public_key:
            logger.warning("[Discord] interactions public key not configured, rejecting request")
            return False

        normalized_headers = {str(k).lower(): v for k, v in headers.items()}
        signature = normalized_headers.get("x-signature-ed25519", "")
        timestamp = normalized_headers.get("x-signature-timestamp", "")

        if not signature or not timestamp:
            logger.warning("[Discord] Missing signature headers, rejecting request")
            return False

        # Validate timestamp format and freshness to prevent replay attacks
        try:
            ts_int = int(timestamp)
        except (TypeError, ValueError):
            logger.warning("[Discord] Invalid timestamp: must be Unix seconds integer, rejecting request")
            return False

        try:
            now_ts = int(time.time())
        except Exception as exc:
            logger.warning("[Discord] Failed to get current time: %s, rejecting request", exc)
            return False

        # Allowed time window: ±5 minutes
        if abs(now_ts - ts_int) > 300:
            logger.warning(
                "[Discord] Request timestamp outside allowed window, possible replay attack: timestamp=%s, now=%s",
                ts_int,
                now_ts,
            )
            return False

        try:
            verify_key = VerifyKey(bytes.fromhex(self._interactions_public_key))
            signature_bytes = bytes.fromhex(signature)
        except ValueError:
            logger.warning("[Discord] Public key or signature is not valid hexadecimal, rejecting request")
            return False
        except Exception as exc:
            logger.warning("[Discord] Cannot load signature public key: %s", exc)
            return False

        try:
            verify_key.verify(timestamp.encode("utf-8") + body, signature_bytes)
        except BadSignatureError:
            logger.warning("[Discord] Signature verification failed")
            return False
        except Exception as exc:
            logger.warning("[Discord] Signature verification exception: %s", exc)
            return False

        return True

    def handle_webhook(
        self,
        headers: Dict[str, str],
        body: bytes,
        data: Dict[str, Any],
    ) -> Tuple[Optional[BotMessage], Optional[WebhookResponse]]:
        """Discord requires signature verification first, then ping/challenge handling."""
        if not self.verify_request(headers, body):
            return None, WebhookResponse.error("Invalid Discord signature", 401)

        challenge_response = self.handle_challenge(data)
        if challenge_response:
            return None, challenge_response

        message = self.parse_message(data)
        if message is not None and data.get("type") == 2:
            # Discord requires an initial response within 3 s.  Return a
            # deferred acknowledgement (type 5 = DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE)
            # so the handler can dispatch the command in the background and
            # deliver the result via follow-up webhook.
            return message, WebhookResponse.success({"type": 5})

        return message, None

    def parse_message(self, data: Dict[str, Any]) -> Optional[BotMessage]:
        """Parse Discord message into unified format.

        Args:
            data: Parsed JSON data

        Returns:
            BotMessage object, or None (no processing needed)
        """
        interaction_type = data.get("type")
        if interaction_type != 2:
            return None

        interaction_data = data.get("data", {})
        content = self._build_command_content(interaction_data)
        if not content:
            return None

        author = (
            data.get("user")
            or (data.get("member") or {}).get("user")
            or data.get("author", {})
        )
        user_id = str(author.get("id") or "")
        user_name = author.get("username", "unknown")
        channel_id = str(data.get("channel_id") or "")
        guild_id = str(data.get("guild_id") or "")

        if guild_id:
            chat_type = ChatType.GROUP
        elif channel_id:
            chat_type = ChatType.PRIVATE
        else:
            chat_type = ChatType.UNKNOWN

        return BotMessage(
            platform=self.platform_name,
            message_id=str(data.get("id") or ""),
            user_id=user_id,
            user_name=user_name,
            chat_id=channel_id or guild_id or user_id,
            chat_type=chat_type,
            content=content,
            raw_content=content,
            mentioned=False,
            mentions=[],
            timestamp=self._parse_timestamp(data.get("timestamp")),
            raw_data={
                **data,
                "_interaction_name": interaction_data.get("name", ""),
            },
        )

    def format_response(self, response: Any, message: BotMessage) -> WebhookResponse:
        """Convert unified response to Discord format.

        For Interaction (type=2) requests, returns Discord Interaction Response
        callback format (type=4 CHANNEL_MESSAGE_WITH_SOURCE + nested data).

        Args:
            response: Unified response object
            message: Original message object

        Returns:
            WebhookResponse object
        """
        content = response.text if hasattr(response, "text") else str(response)

        message_data = {
            "content": content,
            "tts": False,
            "embeds": [],
            "allowed_mentions": {
                "parse": ["users", "roles", "everyone"]
            },
        }

        # Interaction (slash-command) requires Interaction Response callback format
        if message.raw_data.get("type") == 2:
            discord_response = {
                "type": 4,  # CHANNEL_MESSAGE_WITH_SOURCE
                "data": message_data,
            }
        else:
            discord_response = message_data

        return WebhookResponse.success(discord_response)

    # Discord message content hard limit
    DISCORD_MAX_CONTENT_LENGTH = 2000

    def send_followup(self, response: Any, message: BotMessage) -> bool:
        """Edit the deferred interaction placeholder with the real result.

        Uses ``PATCH /webhooks/{application_id}/{token}/messages/@original``
        to update the original deferred message, then sends additional
        follow-up messages via ``POST`` if the content exceeds Discord's
        2 000-character limit.
        """
        raw = message.raw_data
        application_id = raw.get("application_id", "")
        interaction_token = raw.get("token", "")
        if not application_id or not interaction_token:
            logger.warning(
                "[Discord] Missing application_id or interaction token, cannot send follow-up"
            )
            return False

        content = response.text if hasattr(response, "text") else str(response)

        from src.formatters import chunk_content_by_max_words

        try:
            chunks = chunk_content_by_max_words(
                content, self.DISCORD_MAX_CONTENT_LENGTH
            )
        except (ValueError, Exception) as exc:
            logger.warning("[Discord] Message chunking failed: %s, attempting full send", exc)
            chunks = [content]

        base_url = (
            f"https://discord.com/api/v10/webhooks/"
            f"{application_id}/{interaction_token}"
        )

        success = True
        for idx, chunk in enumerate(chunks):
            try:
                if idx == 0:
                    # PATCH the original deferred message
                    resp = requests.patch(
                        f"{base_url}/messages/@original",
                        json={"content": chunk},
                        timeout=10,
                    )
                else:
                    # POST additional follow-up messages
                    resp = requests.post(
                        base_url,
                        json={"content": chunk},
                        timeout=10,
                    )
                if resp.status_code >= 300:
                    logger.error(
                        "[Discord] follow-up chunk %d/%d send failed: %s %s",
                        idx + 1,
                        len(chunks),
                        resp.status_code,
                        resp.text[:200],
                    )
                    success = False
            except Exception as exc:
                logger.error(
                    "[Discord] follow-up chunk %d/%d request exception: %s",
                    idx + 1,
                    len(chunks),
                    exc,
                )
                success = False

        if success:
            logger.info("[Discord] Follow-up messages sent successfully (%d chunks)", len(chunks))
        return success

    def handle_challenge(self, data: Dict[str, Any]) -> Optional[WebhookResponse]:
        """Handle Discord verification requests.

        Discord sends verification requests when configuring Webhooks.

        Args:
            data: Request data

        Returns:
            Verification response, or None (not a verification request)
        """
        # Discord Webhook verification request type is 1
        if data.get("type") == 1:
            return WebhookResponse.success({
                "type": 1
            })

        # Discord command interaction verification
        if "challenge" in data:
            return WebhookResponse.success({
                "challenge": data["challenge"]
            })

        return None

    def _build_command_content(self, interaction_data: Dict[str, Any]) -> str:
        command_name = str(interaction_data.get("name", "")).strip()
        if not command_name:
            return ""

        parts = [f"/{command_name}"]
        self._append_option_parts(parts, interaction_data.get("options", []))
        return " ".join(parts).strip()

    def _append_option_parts(self, parts: List[str], options: Any) -> None:
        if not isinstance(options, list):
            return

        for option in options:
            if not isinstance(option, dict):
                continue

            nested_options = option.get("options")
            if nested_options:
                nested_name = str(option.get("name", "")).strip()
                if nested_name:
                    parts.append(nested_name)
                self._append_option_parts(parts, nested_options)
                continue

            value = option.get("value")
            if value is None:
                continue
            if isinstance(value, bool):
                # Emit the option name for truthy flags so downstream
                # commands receive a semantic token (e.g. "full") instead
                # of a literal "true"/"false" string.  False flags are
                # simply omitted.
                if value:
                    opt_name = str(option.get("name", "")).strip()
                    if opt_name:
                        parts.append(opt_name)
            else:
                parts.append(str(value))

    def _parse_timestamp(self, value: Any) -> datetime:
        if not value:
            return datetime.now()

        if isinstance(value, datetime):
            return value

        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return datetime.now()
