# -*- coding: utf-8 -*-
"""
Custom Webhook notification sender service.

Responsibilities:
1. Send messages to custom Webhook endpoints
"""
import logging
import json
import time
from string import Template
from typing import Any, Dict, List, Optional, Tuple

import requests

from src.config import Config
from src.formatters import chunk_content_by_max_bytes, slice_at_max_bytes


logger = logging.getLogger(__name__)


class CustomWebhookSender:

    def __init__(self, config: Config):
        """
        Initialize custom Webhook configuration.

        Args:
            config: Configuration object
        """
        self._custom_webhook_urls = getattr(config, 'custom_webhook_urls', []) or []
        self._custom_webhook_bearer_token = getattr(config, 'custom_webhook_bearer_token', None)
        self._custom_webhook_body_template = getattr(config, 'custom_webhook_body_template', None)
        self._webhook_verify_ssl = getattr(config, 'webhook_verify_ssl', True)
 
    def send_to_custom(self, content: str) -> bool:
        """
        Push a message to custom Webhooks.

        Supports any Webhook endpoint that accepts POST JSON.
        Default format: {"text": "message content", "content": "message content"}

        Compatible with:
        - DingTalk bot
        - Discord Webhook
        - Slack Incoming Webhook
        - Custom notification services
        - Other POST JSON services

        Args:
            content: Message content (Markdown format)

        Returns:
            Whether at least one Webhook sent successfully
        """
        if not self._custom_webhook_urls:
            logger.warning("No custom Webhook configured, skipping push")
            return False
        
        success_count = 0
        
        for i, url in enumerate(self._custom_webhook_urls):
            try:
                # Generic JSON format, compatible with most Webhooks
                # DingTalk format: {"msgtype": "text", "text": {"content": "xxx"}}
                # Slack format: {"text": "xxx"}
                # Discord format: {"content": "xxx"}

                # DingTalk bot has a byte limit (~20000 bytes); longer content requires chunking
                if self._is_dingtalk_webhook(url):
                    templated_payload = self._build_custom_webhook_template_payload(content)
                    if templated_payload is not None:
                        if self._post_custom_webhook(url, templated_payload, timeout=30):
                            logger.info(f"Custom Webhook {i+1} (DingTalk template) pushed successfully")
                            success_count += 1
                        elif self._send_dingtalk_chunked(url, content, max_bytes=20000):
                            logger.info(f"Custom Webhook {i+1} (DingTalk template failed, falling back to chunking) pushed successfully")
                            success_count += 1
                        else:
                            logger.error(f"Custom Webhook {i+1} (DingTalk template) push failed")
                    elif self._send_dingtalk_chunked(url, content, max_bytes=20000):
                        logger.info(f"Custom Webhook {i+1} (DingTalk) pushed successfully")
                        success_count += 1
                    else:
                        logger.error(f"Custom Webhook {i+1} (DingTalk) push failed")
                    continue

                # Other Webhooks: send in a single request
                payload = self._build_custom_webhook_payload(url, content)
                if self._post_custom_webhook(url, payload, timeout=30):
                    logger.info(f"Custom Webhook {i+1} pushed successfully")
                    success_count += 1
                else:
                    logger.error(f"Custom Webhook {i+1} push failed")
                    
            except Exception as e:
                logger.error(f"Custom Webhook {i+1} push exception: {e}")
        
        logger.info(f"Custom Webhook push completed: {success_count}/{len(self._custom_webhook_urls)} succeeded")
        return success_count > 0

    
    def _send_custom_webhook_image(
        self, image_bytes: bytes, fallback_content: str = ""
    ) -> bool:
        """Send image to Custom Webhooks; Discord supports file attachment (Issue #289)."""
        if not self._custom_webhook_urls:
            return False
        success_count = 0
        for i, url in enumerate(self._custom_webhook_urls):
            try:
                if self._is_discord_webhook(url):
                    files = {"file": ("report.png", image_bytes, "image/png")}
                    data = {"content": "Stock Analysis Report"}
                    headers = {"User-Agent": "StockAnalysis/1.0"}
                    if self._custom_webhook_bearer_token:
                        headers["Authorization"] = (
                            f"Bearer {self._custom_webhook_bearer_token}"
                        )
                    response = requests.post(
                        url, data=data, files=files, headers=headers, timeout=30,
                        verify=self._webhook_verify_ssl
                    )
                    if response.status_code in (200, 204):
                        logger.info("Custom Webhook %d (Discord image) pushed successfully", i + 1)
                        success_count += 1
                    else:
                        logger.error(
                            "Custom Webhook %d (Discord image) push failed: HTTP %s",
                            i + 1, response.status_code,
                        )
                else:
                    if fallback_content:
                        payload = self._build_custom_webhook_payload(url, fallback_content)
                        if self._post_custom_webhook(url, payload, timeout=30):
                            logger.info(
                                "Custom Webhook %d (image not supported, falling back to text) pushed successfully", i + 1
                            )
                            success_count += 1
                    else:
                        logger.warning(
                            "Custom Webhook %d does not support images and no fallback content, skipping", i + 1
                        )
            except Exception as e:
                logger.error("Custom Webhook %d image push exception: %s", i + 1, e)
        return success_count > 0

    def _post_custom_webhook(self, url: str, payload: dict, timeout: int = 30) -> bool:
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'User-Agent': 'StockAnalysis/1.0',
        }
        # Support Bearer Token authentication (#51)
        if self._custom_webhook_bearer_token:
            headers['Authorization'] = f'Bearer {self._custom_webhook_bearer_token}'
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        response = requests.post(url, data=body, headers=headers, timeout=timeout, verify=self._webhook_verify_ssl)
        if response.status_code == 200:
            return True
        logger.error(f"Custom Webhook push failed: HTTP {response.status_code}")
        logger.debug(f"Response content: {response.text[:200]}")
        return False

    def test_custom_webhooks(self, content: str, *, timeout_seconds: float = 20.0) -> List[Dict[str, Any]]:
        """Send a test message to each custom webhook and return raw per-URL attempts."""
        attempts: List[Dict[str, Any]] = []
        for index, url in enumerate(self._custom_webhook_urls):
            try:
                payload = self._build_custom_webhook_payload(url, content)
                attempts.append(
                    self._post_custom_webhook_attempt(
                        url=url,
                        payload=payload,
                        timeout_seconds=timeout_seconds,
                        index=index,
                    )
                )
            except Exception as exc:
                attempts.append({
                    "channel": "custom",
                    "success": False,
                    "message": f"Custom Webhook {index + 1} test exception: {exc}",
                    "target": url,
                    "error_code": self._classify_custom_webhook_exception(exc)[0],
                    "stage": "notification_send",
                    "retryable": self._classify_custom_webhook_exception(exc)[1],
                    "latency_ms": None,
                    "http_status": None,
                })
        return attempts

    def _post_custom_webhook_attempt(
        self,
        *,
        url: str,
        payload: dict,
        timeout_seconds: float,
        index: int,
    ) -> Dict[str, Any]:
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'User-Agent': 'StockAnalysis/1.0',
        }
        if self._custom_webhook_bearer_token:
            headers['Authorization'] = f'Bearer {self._custom_webhook_bearer_token}'

        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        started_at = time.perf_counter()
        try:
            response = requests.post(
                url,
                data=body,
                headers=headers,
                timeout=timeout_seconds,
                verify=self._webhook_verify_ssl,
            )
        except Exception as exc:
            error_code, retryable = self._classify_custom_webhook_exception(exc)
            return {
                "channel": "custom",
                "success": False,
                "message": f"Custom Webhook {index + 1} test failed: {exc}",
                "target": url,
                "error_code": error_code,
                "stage": "notification_send",
                "retryable": retryable,
                "latency_ms": int((time.perf_counter() - started_at) * 1000),
                "http_status": None,
            }

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        if response.status_code == 200:
            return {
                "channel": "custom",
                "success": True,
                "message": f"Custom Webhook {index + 1} test succeeded",
                "target": url,
                "error_code": None,
                "stage": "notification_send",
                "retryable": False,
                "latency_ms": latency_ms,
                "http_status": response.status_code,
            }

        retryable = response.status_code == 429 or response.status_code >= 500
        return {
            "channel": "custom",
            "success": False,
            "message": f"Custom Webhook {index + 1} test failed: HTTP {response.status_code}",
            "target": url,
            "error_code": "http_error",
            "stage": "notification_send",
            "retryable": retryable,
            "latency_ms": latency_ms,
            "http_status": response.status_code,
        }

    @staticmethod
    def _classify_custom_webhook_exception(exc: Exception) -> Tuple[str, bool]:
        if isinstance(exc, requests.exceptions.Timeout):
            return "timeout", True
        if isinstance(exc, requests.exceptions.ConnectionError):
            return "network_error", True
        if isinstance(exc, requests.exceptions.RequestException):
            return "network_error", True
        return "unexpected_error", False
    
    def _build_custom_webhook_payload(self, url: str, content: str) -> dict:
        """
        Build the corresponding Webhook payload based on URL.

        Auto-detects common services and uses the matching format.
        """
        templated_payload = self._build_custom_webhook_template_payload(content)
        if templated_payload is not None:
            return templated_payload

        url_lower = url.lower()
        
        # DingTalk bot
        if 'dingtalk' in url_lower or 'oapi.dingtalk.com' in url_lower:
            return {
                "msgtype": "markdown",
                "markdown": {
                    "title": "Stock Analysis Report",
                    "text": content
                }
            }
        
        # Discord Webhook
        if 'discord.com/api/webhooks' in url_lower or 'discordapp.com/api/webhooks' in url_lower:
            # Discord limits to 2000 characters
            truncated = content[:1900] + "..." if len(content) > 1900 else content
            return {
                "content": truncated
            }
        
        # Slack Incoming Webhook
        if 'hooks.slack.com' in url_lower:
            return {
                "text": content,
                "mrkdwn": True
            }
        
        # Bark (iOS push)
        if 'api.day.app' in url_lower:
            return {
                "title": "Stock Analysis Report",
                "body": content[:4000],  # Bark limit
                "group": "stock"
            }
        
        # Generic format (compatible with most services)
        return {
            "text": content,
            "content": content,
            "message": content,
            "body": content
        }

    def _build_custom_webhook_template_payload(self, content: str) -> Optional[dict]:
        """Build payload from CUSTOM_WEBHOOK_BODY_TEMPLATE when configured."""
        template = (self._custom_webhook_body_template or "").strip()
        if not template:
            return None

        title = "Stock Analysis Report"
        variables = {
            "title": title,
            "title_json": json.dumps(title, ensure_ascii=False),
            "content": content,
            "content_json": json.dumps(content, ensure_ascii=False),
        }
        rendered = Template(template).safe_substitute(variables)
        try:
            payload: Any = json.loads(rendered)
        except json.JSONDecodeError as exc:
            logger.error(
                "CUSTOM_WEBHOOK_BODY_TEMPLATE is not valid JSON, falling back to default Webhook payload: %s",
                exc,
            )
            return None
        if not isinstance(payload, dict):
            logger.error(
                "CUSTOM_WEBHOOK_BODY_TEMPLATE must render to a JSON object, falling back to default Webhook payload"
            )
            return None
        return payload
    
    def _send_dingtalk_chunked(self, url: str, content: str, max_bytes: int = 20000) -> bool:
        import time as _time

        # Reserve space for payload overhead to avoid exceeding the body limit
        budget = max(1000, max_bytes - 1500)
        chunks = chunk_content_by_max_bytes(content, budget)
        if not chunks:
            return False

        total = len(chunks)
        ok = 0

        for idx, chunk in enumerate(chunks):
            marker = f"\n\n📄 *({idx+1}/{total})*" if total > 1 else ""
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": "Stock Analysis Report",
                    "text": chunk + marker,
                },
            }

            # If still over the limit (edge case), hard-truncate by bytes
            body_bytes = len(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
            if body_bytes > max_bytes:
                hard_budget = max(200, budget - (body_bytes - max_bytes) - 200)
                payload["markdown"]["text"], _ = slice_at_max_bytes(payload["markdown"]["text"], hard_budget)

            if self._post_custom_webhook(url, payload, timeout=30):
                ok += 1
            else:
                logger.error(f"DingTalk chunked send failed: chunk {idx+1}/{total}")

            if idx < total - 1:
                _time.sleep(1)

        return ok == total

    
    @staticmethod
    def _is_dingtalk_webhook(url: str) -> bool:
        url_lower = (url or "").lower()
        return 'dingtalk' in url_lower or 'oapi.dingtalk.com' in url_lower

    @staticmethod
    def _is_discord_webhook(url: str) -> bool:
        url_lower = (url or "").lower()
        return (
            'discord.com/api/webhooks' in url_lower
            or 'discordapp.com/api/webhooks' in url_lower
        )
