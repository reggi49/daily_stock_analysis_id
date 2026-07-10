# -*- coding: utf-8 -*-
"""
===================================
Platform Adapter Base Class
===================================

Defines the abstract base class for platform adapters. Each platform must inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple

from bot.models import BotMessage, BotResponse, WebhookResponse


class BotPlatform(ABC):
    """
    Abstract base class for platform adapters.

    Responsibilities:
    1. Verify Webhook request signatures
    2. Parse platform messages into unified format
    3. Convert responses to platform-specific format

    Usage example:
        class MyPlatform(BotPlatform):
            @property
            def platform_name(self) -> str:
                return "myplatform"

            def verify_request(self, headers, body) -> bool:
                # Signature verification logic
                return True

            def parse_message(self, data) -> Optional[BotMessage]:
                # Message parsing logic
                return BotMessage(...)

            def format_response(self, response, message) -> WebhookResponse:
                # Response formatting logic
                return WebhookResponse.success({"text": response.text})
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """
        Platform identifier name.

        Used for routing and log identification, e.g. "feishu", "dingtalk"
        """
        pass

    @abstractmethod
    def verify_request(self, headers: Dict[str, str], body: bytes) -> bool:
        """
        Verify request signature.

        Each platform has a different signature verification mechanism
        and must be implemented individually.

        Args:
            headers: HTTP request headers
            body: Raw request body bytes

        Returns:
            Whether the signature is valid
        """
        pass

    @abstractmethod
    def parse_message(self, data: Dict[str, Any]) -> Optional[BotMessage]:
        """
        Parse platform message into unified format.

        Converts platform-specific message format to BotMessage.
        Returns None if the message type is not one to process (e.g. event callbacks).

        Args:
            data: Parsed JSON data

        Returns:
            BotMessage object, or None (no processing needed)
        """
        pass

    @abstractmethod
    def format_response(
        self,
        response: BotResponse,
        message: BotMessage
    ) -> WebhookResponse:
        """
        Convert unified response to platform format.

        Args:
            response: Unified response object
            message: Original message object (for reply target info, etc.)

        Returns:
            WebhookResponse object
        """
        pass

    def send_followup(
        self,
        response: 'BotResponse',
        message: 'BotMessage',
    ) -> bool:
        """Send a follow-up message after a deferred webhook response.

        Override in platforms that return a deferred acknowledgement
        (e.g. Discord type 5) so the final command result can be delivered
        asynchronously.  The default implementation is a no-op.

        Returns:
            ``True`` if the follow-up was sent successfully.
        """
        return False

    def handle_challenge(self, data: Dict[str, Any]) -> Optional[WebhookResponse]:
        """
        Handle platform verification requests.

        Some platforms send verification requests when configuring Webhooks
        and require a specific response. Subclasses can override this method.

        Args:
            data: Request data

        Returns:
            Verification response, or None (not a verification request)
        """
        return None

    def handle_webhook(
        self,
        headers: Dict[str, str],
        body: bytes,
        data: Dict[str, Any]
    ) -> Tuple[Optional[BotMessage], Optional[WebhookResponse]]:
        """
        Handle Webhook requests.

        This is the main entry point method, coordinating verification, parsing, etc.

        Args:
            headers: HTTP request headers
            body: Raw request body bytes
            data: Parsed JSON data

        Returns:
            (BotMessage, WebhookResponse) tuple
            - Verification request: (None, challenge_response)
            - Normal message: (message, None) — response will be generated after command processing
            - Verification failed or no processing needed: (None, error_response or None)
        """
        # 1. Check if it's a verification request
        challenge_response = self.handle_challenge(data)
        if challenge_response:
            return None, challenge_response

        # 2. Verify request signature
        if not self.verify_request(headers, body):
            return None, WebhookResponse.error("Invalid signature", 403)

        # 3. Parse message
        message = self.parse_message(data)

        return message, None
