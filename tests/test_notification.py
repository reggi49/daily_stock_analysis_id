# -*- coding: utf-8 -*-
"""
===================================
A-Share Stock Analysis System - Notification Service Unit Tests
===================================

Responsibilities:
1. Verify notification service config detection logic
2. Verify notification service channel detection logic
3. Verify notification service message sending logic

TODO: 
1. Add tests beyond sending channels, e.g.:
    - Generate daily report
2. Add tests for send_to_context
"""
import os
import sys
import unittest
from unittest import mock
from typing import Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Keep this test runnable when optional LLM/runtime deps are not installed.
for optional_module in ("litellm", "json_repair"):
    try:
        __import__(optional_module)
    except ModuleNotFoundError:
        sys.modules[optional_module] = mock.MagicMock()

from src.config import Config
from src.notification import NotificationService, NotificationChannel
from src.notification_noise import reset_notification_noise_state
from src.analyzer import AnalysisResult
from bot.models import BotMessage, ChatType
import requests


def _make_config(**overrides) -> Config:
    """Create a Config instance overriding only notification-related fields."""
    return Config(stock_list=[], **overrides)


def _make_response(status_code: int, json: Optional[dict] = None) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    if json:
        response.json = lambda: json
    return response


def _attach_decision_signal_summary(result: AnalysisResult) -> AnalysisResult:
    result.decision_signal_summary = {
        "action": "sell",
        "action_label": "sell",
        "horizon": "1d",
        "reason": "Technical weakness",
    }
    return result


def _make_feishu_message() -> BotMessage:
    return BotMessage(
        platform="feishu",
        message_id="msg-1",
        user_id="user-1",
        user_name="tester",
        chat_id="chat-1",
        chat_type=ChatType.GROUP,
        content="/a 600519",
    )


def _make_dingtalk_message() -> BotMessage:
    return BotMessage(
        platform="dingtalk",
        message_id="msg-2",
        user_id="user-2",
        user_name="tester",
        chat_id="dingtalk-chat",
        chat_type=ChatType.GROUP,
        content="/a 600519",
        raw_data={
            "sessionWebhook": "https://oapi.dingtalk.com/robot/sendBySession?session=abc123",
        },
    )


def _make_telegram_message() -> BotMessage:
    return BotMessage(
        platform="telegram",
        message_id="msg-3",
        user_id="user-3",
        user_name="tester",
        chat_id="100200300",
        chat_type=ChatType.PRIVATE,
        content="/a 600519",
        raw_data={"chat_id": "100200300"},
    )


class TestNotificationServiceSendToMethods(unittest.TestCase):
    """Test the notification-sending service

    Test design:

    Tests are arranged alphabetically by channel; insert new tests in the appropriate position.
    If long-message chunking is used, the chunking logic must be tested separately,
        e.g. test_send_to_discord_via_notification_service_with_bot_requires_chunking

    1. Add mock config:
    Use mock.patch decorator to mock get_config function,
    use _make_config function to add config and return Config instance.

    2. Verify config correctness:
    Use assertIn to check whether NotificationChannel.xxxx is in
    the return value of `NotificationService.get_available_channels()`.

    3. Mock request/response:
    Use mock.patch decorator to mock requests.post function,
    use _make_response function to mock request response and return Response instance.
    If using another function to mock the response, use mock.patch decorator for that function.

    4. Use assertTrue to check the return value of send.

    5. Use assert_called_once to check the request function was called once.
    For chunking tests, use assertAlmostEqual(mock_post.call_count, ...) to check call count.

    """

    def setUp(self):
        reset_notification_noise_state()

    @mock.patch("src.notification.get_config")
    def test_no_channels_service_unavailable_and_send_returns_false(self, mock_get_config):
        mock_get_config.return_value = _make_config()

        service = NotificationService()

        self.assertFalse(service.is_available())
        result = service.send("test content")
        self.assertFalse(result)

    @mock.patch("src.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_astrbot_via_notification_service(self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock):
        cfg = _make_config(astrbot_url="https://astrbot.example")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200)

        service = NotificationService()
        self.assertIn(NotificationChannel.ASTRBOT, service.get_available_channels())

        ok = service.send("astrbot content")

        self.assertTrue(ok)
        mock_post.assert_called_once()

    @mock.patch("src.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_custom_webhook_via_notification_service(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(custom_webhook_urls=["https://example.com/webhook"])
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200)

        service = NotificationService()
        self.assertIn(NotificationChannel.CUSTOM, service.get_available_channels())

        ok = service.send("custom content")

        self.assertTrue(ok)
        mock_post.assert_called_once()

    @mock.patch("src.notification.get_config")
    def test_send_isolates_channel_exceptions(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            wechat_webhook_url="https://wechat.example/hook",
            custom_webhook_urls=["https://example.com/webhook"],
        )
        mock_get_config.return_value = cfg

        service = NotificationService()
        self.assertIn(NotificationChannel.WECHAT, service.get_available_channels())
        self.assertIn(NotificationChannel.CUSTOM, service.get_available_channels())

        with mock.patch.object(service, "send_to_wechat", side_effect=RuntimeError("boom")), \
             mock.patch.object(service, "send_to_custom", return_value=True) as mock_custom:
            ok = service.send("content")

        self.assertTrue(ok)
        mock_custom.assert_called_once_with("content")

    @mock.patch("src.notification.get_config")
    def test_send_with_results_reports_per_channel_attempts(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            wechat_webhook_url="https://wechat.example/hook",
            custom_webhook_urls=["https://example.com/webhook"],
        )
        mock_get_config.return_value = cfg

        service = NotificationService()

        with mock.patch.object(service, "send_to_wechat", side_effect=RuntimeError("token=secret-token failed")), \
             mock.patch.object(service, "send_to_custom", return_value=True):
            result = service.send_with_results("content")

        self.assertTrue(result.dispatched)
        self.assertTrue(result.success)
        self.assertEqual(result.status, "partial_failed")
        by_channel = {item.channel: item for item in result.channel_results}
        self.assertFalse(by_channel["wechat"].success)
        self.assertEqual(by_channel["wechat"].error_code, "exception")
        self.assertNotIn("secret-token", by_channel["wechat"].diagnostics)
        self.assertTrue(by_channel["custom"].success)

    @mock.patch("src.notification.get_config")
    def test_send_with_results_reports_route_no_channel(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            custom_webhook_urls=["https://example.com/webhook"],
            notification_report_channels=["unknown-route-channel"],
        )
        mock_get_config.return_value = cfg

        service = NotificationService()

        with mock.patch.object(service, "send_to_custom", return_value=True) as mock_custom:
            result = service.send_with_results("content", route_type="report")

        self.assertFalse(result.dispatched)
        self.assertFalse(result.success)
        self.assertEqual(result.status, "no_channel")
        self.assertEqual(result.channel_results, [])
        mock_custom.assert_not_called()

    @mock.patch("src.notification.get_config")
    def test_send_route_empty_keeps_all_configured_channels(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            wechat_webhook_url="https://wechat.example/hook",
            custom_webhook_urls=["https://example.com/webhook"],
        )
        mock_get_config.return_value = cfg

        service = NotificationService()

        with mock.patch.object(service, "send_to_wechat", return_value=True) as mock_wechat, \
             mock.patch.object(service, "send_to_custom", return_value=True) as mock_custom:
            ok = service.send("content", route_type="report")

        self.assertTrue(ok)
        mock_wechat.assert_called_once_with("content")
        mock_custom.assert_called_once_with("content")

    @mock.patch("src.notification.get_config")
    def test_send_report_route_filters_static_channels(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            wechat_webhook_url="https://wechat.example/hook",
            custom_webhook_urls=["https://example.com/webhook"],
            notification_report_channels=["custom"],
        )
        mock_get_config.return_value = cfg

        service = NotificationService()

        with mock.patch.object(service, "send_to_wechat", return_value=True) as mock_wechat, \
             mock.patch.object(service, "send_to_custom", return_value=True) as mock_custom:
            ok = service.send("content", route_type="report")

        self.assertTrue(ok)
        mock_wechat.assert_not_called()
        mock_custom.assert_called_once_with("content")

    @mock.patch("src.notification.get_config")
    def test_send_alert_and_system_error_routes_filter_independently(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            wechat_webhook_url="https://wechat.example/hook",
            custom_webhook_urls=["https://example.com/webhook"],
            notification_alert_channels=["wechat"],
            notification_system_error_channels=["custom"],
        )
        mock_get_config.return_value = cfg

        service = NotificationService()

        with mock.patch.object(service, "send_to_wechat", return_value=True) as mock_wechat, \
             mock.patch.object(service, "send_to_custom", return_value=True) as mock_custom:
            self.assertTrue(service.send("alert", route_type="alert"))
            self.assertTrue(service.send("system", route_type="system_error"))

        mock_wechat.assert_called_once_with("alert")
        mock_custom.assert_called_once_with("system")

    @mock.patch("src.notification.get_config")
    def test_send_route_with_no_matching_channel_does_not_fallback(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            custom_webhook_urls=["https://example.com/webhook"],
            notification_report_channels=["unknown-route-channel"],
        )
        mock_get_config.return_value = cfg

        service = NotificationService()

        with mock.patch.object(service, "send_to_custom", return_value=True) as mock_custom:
            ok = service.send("content", route_type="report")

        self.assertFalse(ok)
        mock_custom.assert_not_called()

    @mock.patch("src.notification.get_config")
    def test_send_to_context_is_not_limited_by_route(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            custom_webhook_urls=["https://example.com/webhook"],
            notification_report_channels=["telegram"],
        )
        mock_get_config.return_value = cfg

        service = NotificationService()

        with mock.patch.object(service, "send_to_context", return_value=True) as mock_context, \
             mock.patch.object(service, "send_to_custom", return_value=True) as mock_custom:
            ok = service.send("content", route_type="report")

        self.assertTrue(ok)
        mock_context.assert_called_once_with("content")
        mock_custom.assert_not_called()

    @mock.patch("src.notification.get_config")
    def test_feishu_context_response_skips_static_webhook(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            feishu_webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/test-token",
            feishu_app_id="cli_test",
            feishu_app_secret="app-secret",
        )
        mock_get_config.return_value = cfg
        service = NotificationService(source_message=_make_feishu_message())

        with mock.patch.object(service, "_send_feishu_stream_reply", return_value=True) as mock_reply, \
             mock.patch.object(service, "send_to_feishu", return_value=True) as mock_webhook:
            result = service.send_with_results("content", route_type="report")

        self.assertTrue(result.dispatched)
        self.assertTrue(result.success)
        self.assertEqual(result.status, "sent")
        self.assertEqual([item.channel for item in result.channel_results], ["__context__"])
        mock_reply.assert_called_once_with("chat-1", "content")
        mock_webhook.assert_not_called()

    @mock.patch("src.notification.get_config")
    def test_feishu_context_failure_does_not_fallback_to_static_webhook(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            feishu_webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/test-token",
            feishu_app_id="cli_test",
            feishu_app_secret="app-secret",
        )
        mock_get_config.return_value = cfg
        service = NotificationService(source_message=_make_feishu_message())

        with mock.patch.object(service, "_send_feishu_stream_reply", return_value=False), \
             mock.patch.object(service, "send_to_feishu", return_value=True) as mock_webhook:
            result = service.send_with_results("content", route_type="report")

        self.assertTrue(result.dispatched)
        self.assertFalse(result.success)
        self.assertEqual(result.status, "all_failed")
        self.assertEqual([item.channel for item in result.channel_results], ["__context__"])
        mock_webhook.assert_not_called()

    @mock.patch("src.notification.get_config")
    def test_dingtalk_context_response_skips_static_webhook(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            feishu_webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/test-token",
            dingtalk_app_key="dingtalk-key",
            dingtalk_app_secret="dingtalk-secret",
            wechat_webhook_url="https://wechat.example/hook",
        )
        mock_get_config.return_value = cfg
        service = NotificationService(source_message=_make_dingtalk_message())

        with mock.patch.object(service, "_send_dingtalk_chunked", return_value=True) as mock_dingtalk, \
             mock.patch.object(service, "send_to_wechat", return_value=True) as mock_wechat:
            result = service.send_with_results("content", route_type="report")

        self.assertTrue(result.dispatched)
        self.assertTrue(result.success)
        self.assertEqual([item.channel for item in result.channel_results], ["__context__"])
        mock_dingtalk.assert_called_once_with("https://oapi.dingtalk.com/robot/sendBySession?session=abc123", "content", max_bytes=20000)
        mock_wechat.assert_not_called()

    @mock.patch("src.notification.get_config")
    def test_telegram_context_response_skips_static_webhook(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            telegram_bot_token="TOKEN",
            telegram_chat_id="123456",
            wechat_webhook_url="https://wechat.example/hook",
        )
        mock_get_config.return_value = cfg
        service = NotificationService(source_message=_make_telegram_message())

        with mock.patch.object(service, "send_to_telegram", return_value=True) as mock_telegram, \
             mock.patch.object(service, "send_to_wechat", return_value=True) as mock_wechat:
            result = service.send_with_results("content", route_type="report")

        self.assertTrue(result.dispatched)
        self.assertTrue(result.success)
        self.assertEqual([item.channel for item in result.channel_results], ["__context__"])
        mock_telegram.assert_called_once_with("content", chat_id="100200300")
        mock_wechat.assert_not_called()

    @mock.patch("src.notification.get_config")
    def test_feishu_webhook_still_sends_without_source_context(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            feishu_webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/test-token",
            feishu_app_id="cli_test",
            feishu_app_secret="app-secret",
        )
        mock_get_config.return_value = cfg
        service = NotificationService()

        with mock.patch.object(service, "send_to_feishu", return_value=True) as mock_webhook:
            result = service.send_with_results("content", route_type="report")

        self.assertTrue(result.dispatched)
        self.assertTrue(result.success)
        self.assertEqual([item.channel for item in result.channel_results], ["feishu"])
        mock_webhook.assert_called_once_with("content")

    @mock.patch("src.notification.get_config")
    def test_feishu_send_as_file_route_report_calls_send_feishu_file(self, mock_get_config):
        """When FEISHU_SEND_AS_FILE=true and route_type=report, use file sending."""
        cfg = _make_config(
            feishu_webhook_url="https://feishu.example/hook",
            feishu_send_as_file=True,
        )
        mock_get_config.return_value = cfg
        service = NotificationService()
        with mock.patch.object(service, "send_feishu_file", return_value=True) as mock_file, \
             mock.patch.object(service, "save_report_to_file", return_value="/tmp/report.md"):
            result = service.send_with_results("report content", route_type="report")
        self.assertTrue(result.success)
        mock_file.assert_called_once()

    @mock.patch("src.notification.get_config")
    def test_feishu_send_as_file_route_alert_calls_send_to_feishu(self, mock_get_config):
        """When FEISHU_SEND_AS_FILE=true but route_type=alert, use text sending."""
        cfg = _make_config(
            feishu_webhook_url="https://feishu.example/hook",
            feishu_send_as_file=True,
        )
        mock_get_config.return_value = cfg
        service = NotificationService()
        with mock.patch.object(service, "send_to_feishu", return_value=True) as mock_text, \
             mock.patch.object(service, "save_report_to_file") as mock_save:
            result = service.send_with_results("alert content", route_type="alert")
        self.assertTrue(result.success)
        mock_text.assert_called_once_with("alert content")
        mock_save.assert_not_called()

    @mock.patch("src.notification.get_config")
    def test_feishu_send_as_file_route_none_uses_text(self, mock_get_config):
        """When FEISHU_SEND_AS_FILE=true and route_type=None, use text (not file)."""
        cfg = _make_config(
            feishu_webhook_url="https://feishu.example/hook",
            feishu_send_as_file=True,
        )
        mock_get_config.return_value = cfg
        service = NotificationService()
        with mock.patch.object(service, "send_to_feishu", return_value=True) as mock_text, \
             mock.patch.object(service, "save_report_to_file") as mock_save:
            result = service.send_with_results("report content")
        self.assertTrue(result.success)
        mock_text.assert_called_once_with("report content")
        mock_save.assert_not_called()

    @mock.patch("src.notification.get_config")
    def test_feishu_send_as_file_false_uses_text_even_for_report(self, mock_get_config):
        """When FEISHU_SEND_AS_FILE=false (default), report still uses text."""
        cfg = _make_config(
            feishu_webhook_url="https://feishu.example/hook",
            feishu_send_as_file=False,
        )
        mock_get_config.return_value = cfg
        service = NotificationService()
        with mock.patch.object(service, "send_to_feishu", return_value=True) as mock_text, \
             mock.patch.object(service, "save_report_to_file") as mock_save:
            result = service.send_with_results("report content", route_type="report")
        self.assertTrue(result.success)
        mock_text.assert_called_once_with("report content")
        mock_save.assert_not_called()

    @mock.patch("src.notification.get_config")
    def test_feishu_send_as_file_alert_does_not_leak_into_other_channels(self, mock_get_config):
        """FEISHU_SEND_AS_FILE only affects Feishu, not other channels."""
        cfg = _make_config(
            feishu_webhook_url="https://feishu.example/hook",
            custom_webhook_urls=["https://example.com/hook"],
            feishu_send_as_file=True,
        )
        mock_get_config.return_value = cfg
        service = NotificationService()
        with mock.patch.object(service, "send_feishu_file", return_value=True) as mock_file, \
             mock.patch.object(service, "send_to_custom", return_value=True) as mock_custom, \
             mock.patch.object(service, "save_report_to_file", return_value="/tmp/report.md"):
            result = service.send_with_results("content", route_type="report")
        self.assertTrue(result.success)
        mock_file.assert_called_once()
        mock_custom.assert_called_once_with("content")

    @mock.patch("src.notification.get_config")
    def test_feishu_send_as_file_system_error_uses_text(self, mock_get_config):
        """FEISHU_SEND_AS_FILE does not activate for system_error routes."""
        cfg = _make_config(
            feishu_webhook_url="https://feishu.example/hook",
            feishu_send_as_file=True,
        )
        mock_get_config.return_value = cfg
        service = NotificationService()
        with mock.patch.object(service, "send_to_feishu", return_value=True) as mock_text, \
             mock.patch.object(service, "save_report_to_file") as mock_save:
            result = service.send_with_results("error", route_type="system_error")
        self.assertTrue(result.success)
        mock_text.assert_called_once_with("error")
        mock_save.assert_not_called()

    @mock.patch("src.notification.get_config")
    def test_send_dedup_suppresses_static_channels_after_success(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            custom_webhook_urls=["https://example.com/webhook"],
            notification_dedup_ttl_seconds=60,
        )
        mock_get_config.return_value = cfg

        service = NotificationService()

        with mock.patch.object(service, "send_to_custom", return_value=True) as mock_custom:
            self.assertTrue(service.send("content at 12:00", route_type="report", dedup_key="report:aggregate:simple:600519"))
            self.assertFalse(service.send("content at 12:01", route_type="report", dedup_key="report:aggregate:simple:600519"))

        mock_custom.assert_called_once_with("content at 12:00")

    @mock.patch("src.notification.get_config")
    def test_send_releases_noise_reservation_when_static_channels_fail(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            custom_webhook_urls=["https://example.com/webhook"],
            notification_dedup_ttl_seconds=60,
        )
        mock_get_config.return_value = cfg

        service = NotificationService()

        with mock.patch.object(service, "send_to_custom", side_effect=[False, True]) as mock_custom:
            self.assertFalse(
                service.send(
                    "content at 12:00",
                    route_type="report",
                    dedup_key="report:aggregate:simple:600519",
                )
            )
            self.assertTrue(
                service.send(
                    "content at 12:01",
                    route_type="report",
                    dedup_key="report:aggregate:simple:600519",
                )
            )

        self.assertEqual(mock_custom.call_count, 2)

    @mock.patch("src.notification.get_config")
    def test_send_to_context_is_not_limited_by_noise_controls(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(
            custom_webhook_urls=["https://example.com/webhook"],
            notification_dedup_ttl_seconds=60,
        )
        mock_get_config.return_value = cfg

        service = NotificationService()

        with mock.patch.object(service, "send_to_context", return_value=True) as mock_context, \
             mock.patch.object(service, "send_to_custom", return_value=True) as mock_custom:
            self.assertTrue(service.send("content at 12:00", route_type="report", dedup_key="report:aggregate:simple:600519"))
            self.assertTrue(service.send("content at 12:01", route_type="report", dedup_key="report:aggregate:simple:600519"))

        self.assertEqual(mock_context.call_count, 2)
        mock_custom.assert_called_once_with("content at 12:00")

    @mock.patch("src.notification.get_config")
    def test_noise_check_failure_does_not_block_static_send(self, mock_get_config: mock.MagicMock):
        cfg = _make_config(custom_webhook_urls=["https://example.com/webhook"])
        mock_get_config.return_value = cfg

        service = NotificationService()

        with mock.patch("src.notification_noise._evaluate_notification_noise", side_effect=RuntimeError("boom")), \
             mock.patch.object(service, "send_to_custom", return_value=True) as mock_custom:
            ok = service.send("content", route_type="report")

        self.assertTrue(ok)
        mock_custom.assert_called_once_with("content")

    @mock.patch("src.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_discord_via_notification_service_with_webhook(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(discord_webhook_url="https://discord.example/webhook")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(204)

        service = NotificationService()
        self.assertIn(NotificationChannel.DISCORD, service.get_available_channels())

        ok = service.send("discord content")

        self.assertTrue(ok)
        mock_post.assert_called_once()

    @mock.patch("src.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_discord_via_notification_service_with_bot(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(discord_bot_token="TOKEN", discord_main_channel_id="123")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200)

        service = NotificationService()
        self.assertIn(NotificationChannel.DISCORD, service.get_available_channels())

        ok = service.send("discord content")

        self.assertTrue(ok)
        mock_post.assert_called_once()
        
    @mock.patch("src.notification.get_config")
    @mock.patch("src.notification_sender.discord_sender.time.sleep", return_value=None)
    @mock.patch("requests.post")
    def test_send_to_discord_via_notification_service_with_bot_requires_chunking(
        self,
        mock_post: mock.MagicMock,
        _mock_sleep: mock.MagicMock,
        mock_get_config: mock.MagicMock,
    ):
        cfg = _make_config(
            discord_bot_token="TOKEN",
            discord_main_channel_id="123",
            discord_max_words=2000,
        )
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200)

        service = NotificationService()
        self.assertIn(NotificationChannel.DISCORD, service.get_available_channels())

        ok = service.send("A" * 6000)

        self.assertTrue(ok)
        self.assertAlmostEqual(mock_post.call_count, 4, delta=1)


class TestNotificationServiceReportGeneration(unittest.TestCase):
    """Tests related to report generation and routing."""

    @mock.patch("src.notification.get_config")
    def test_generate_aggregate_report_routes_by_report_type(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config()
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
        )

        with mock.patch.object(service, "generate_dashboard_report", return_value="dashboard") as mock_dashboard, mock.patch.object(
            service, "generate_brief_report", return_value="brief"
        ) as mock_brief:
            self.assertEqual(service.generate_aggregate_report([result], "simple"), "dashboard")
            self.assertEqual(service.generate_aggregate_report([result], "full"), "dashboard")
            self.assertEqual(service.generate_aggregate_report([result], "detailed"), "dashboard")
            self.assertEqual(service.generate_aggregate_report([result], "brief"), "brief")

        self.assertEqual(mock_dashboard.call_count, 3)
        mock_brief.assert_called_once()

    @mock.patch("src.notification.get_config")
    def test_generate_single_stock_report_keeps_legacy_simple_format(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(report_renderer_enabled=True)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
        )

        with mock.patch("src.services.report_renderer.render") as mock_render:
            out = service.generate_single_stock_report(result)

        mock_render.assert_not_called()
        self.assertIn("Kweichow Moutai", out)
        self.assertIn("600519", out)

    @mock.patch("src.notification.get_config")
    def test_generate_brief_report_shows_model_by_default(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
            model_used="gemini/gemini-2.5-flash",
        )

        out = service.generate_brief_report([result], report_date="2026-02-01")

        self.assertIn("*Analytical model: gemini/gemini-2.5-flash*", out)

    @mock.patch("src.notification.get_config")
    def test_generate_dashboard_report_shows_model_by_default(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
            model_used="gemini/gemini-2.5-flash",
        )

        out = service.generate_dashboard_report([result], report_date="2026-02-01")

        self.assertIn("*Analytical model：gemini/gemini-2.5-flash*", out)

    @mock.patch("src.notification.get_config")
    def test_generate_dashboard_report_shows_phase_decision_in_default_renderer(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Waiting for confirmation",
            dashboard={
                "core_conclusion": {"one_sentence": "Waiting for confirmation"},
                "phase_decision": {
                    "action_window": "intraday tracking",
                    "immediate_action": "Waiting for confirmation",
                    "watch_conditions": ["Heavy volume breakthrough"],
                    "next_check_time": "14:30",
                    "confidence_reason": "Data quality available",
                    "data_limitations": ["quote: stale"],
                },
            },
        )

        out = service.generate_dashboard_report([result], report_date="2026-02-01")

        self.assertIn("Intraday Decision Guardrails", out)
        self.assertIn("intraday tracking", out)
        self.assertIn("Waiting for confirmation", out)
        self.assertIn("Heavy volume breakthrough", out)
        self.assertIn("quote: stale", out)

    @mock.patch("src.notification.get_config")
    def test_generate_dashboard_report_skips_context_only_phase_decision_default_renderer(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Waiting for confirmation",
            dashboard={
                "core_conclusion": {"one_sentence": "Waiting for confirmation"},
                "phase_decision": {
                    "phase_context": {"phase": "intraday", "market": "cn"},
                    "watch_conditions": [],
                    "data_limitations": [],
                },
            },
        )

        out = service.generate_dashboard_report([result], report_date="2026-02-01")

        self.assertNotIn("Intraday Decision Guardrails", out)

    @mock.patch("src.notification.get_config")
    def test_generate_dashboard_report_appends_decision_signal_excerpt_fallback(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = _attach_decision_signal_summary(AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
        ))

        out = service.generate_dashboard_report([result], report_date="2026-02-01")

        summary_section, detail_section = out.split("---", 1)
        self.assertNotIn("AI decision signal", summary_section)
        self.assertIn("AI decision signal", detail_section)
        self.assertIn("action: sell", detail_section)
        self.assertIn("cycle: 1d", detail_section)
        self.assertIn("Reason: Technical weakness", detail_section)

    @mock.patch("src.notification.get_config")
    def test_generate_daily_report_appends_decision_signal_excerpt_fallback(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        result = _attach_decision_signal_summary(AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
        ))

        for summary_only in (True, False):
            service = NotificationService()
            service._report_summary_only = summary_only
            out = service.generate_daily_report([result], report_date="2026-02-01")
            self.assertEqual(out.count("AI decision signal"), 0 if summary_only else 1)
            if summary_only:
                self.assertNotIn("action: sell", out)
            else:
                self.assertIn("action: sell", out)
                self.assertIn("cycle: 1d", out)
                self.assertIn("Reason: Technical weakness", out)

    @mock.patch("src.notification.get_config")
    def test_generate_wechat_dashboard_appends_decision_signal_excerpt_fallback(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        result = _attach_decision_signal_summary(AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
        ))

        for summary_only in (True, False):
            service = NotificationService()
            service._report_summary_only = summary_only
            out = service.generate_wechat_dashboard([result])
            self.assertEqual(out.count("AI decision signal"), 0 if summary_only else 1)
            if summary_only:
                self.assertNotIn("action: sell", out)
            else:
                self.assertIn("action: sell", out)
                self.assertIn("cycle: 1d", out)
                self.assertIn("Reason: Technical weakness", out)

    @mock.patch("src.notification.get_config")
    def test_generate_wechat_summary_omits_decision_signal_excerpt(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = _attach_decision_signal_summary(AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
        ))

        out = service.generate_wechat_summary([result])

        self.assertNotIn("AI decision signal", out)
        self.assertNotIn("action: sell", out)

    @mock.patch("src.notification.get_config")
    def test_generate_dashboard_report_appends_decision_signal_excerpt_with_renderer(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=True)
        service = NotificationService()
        result = _attach_decision_signal_summary(AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
        ))

        out = service.generate_dashboard_report([result], report_date="2026-02-01")

        summary_section, detail_section = out.split("---", 1)
        self.assertNotIn("AI decision signal", summary_section)
        self.assertIn("AI decision signal", detail_section)
        self.assertIn("action: sell", detail_section)
        self.assertIn("cycle: 1d", detail_section)
        self.assertIn("Reason: Technical weakness", detail_section)

    @mock.patch("src.notification.get_config")
    def test_aggregate_reports_show_compact_market_status_only(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
        )
        result.market_phase_summary = {
            "phase": "intraday",
            "market": "cn",
            "trigger_source": "portfolio",
            "is_partial_bar": True,
        }
        result.analysis_context_pack_overview = {
            "data_quality": {
                "level": "limited",
                "limitations": ["quote: stale", "news: missing", "portfolio_context: hidden"],
            }
        }
        result.raw_response = "raw context pack and prompt should not appear"

        out = service.generate_brief_report([result], report_date="2026-02-01")

        self.assertIn("market status：Ashares · intraday", out)
        self.assertNotIn("stage：intraday", out)
        self.assertNotIn("trigger source：portfolio", out)
        self.assertNotIn("Intraday data tips", out)
        self.assertNotIn("Data quality: limited", out)
        self.assertNotIn("Limit: quote: stale", out)
        self.assertNotIn("Limit: news: missing", out)
        self.assertNotIn("portfolio_context: hidden", out)
        self.assertNotIn("raw context pack", out)
        self.assertNotIn("prompt", out.lower())

    @mock.patch("src.notification.get_config")
    def test_template_dashboard_report_uses_single_market_status_line(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(report_renderer_enabled=True)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
        )
        result.market_phase_summary = {
            "phase": "postmarket",
            "market": "cn",
            "trigger_source": "cli",
        }
        result.analysis_context_pack_overview = {
            "data_quality": {
                "level": "good",
                "limitations": ["technical: partial"],
            }
        }

        out = service.generate_dashboard_report([result], report_date="2026-02-01")

        self.assertIn("market status：Ashares · after hours", out)
        self.assertEqual(out.count("market status："), 1)
        self.assertNotIn("stage：postmarket", out)
        self.assertNotIn("trigger source：cli", out)
        self.assertNotIn("Data quality: good", out)
        self.assertNotIn("technical: partial", out)

    @mock.patch("src.notification.get_config")
    def test_generated_reports_skip_phase_pack_excerpt_when_summary_missing(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
        )

        out = service.generate_brief_report([result], report_date="2026-02-01")

        self.assertNotIn("Summary source", out)
        self.assertNotIn("evaluator snapshot", out)

    @mock.patch("src.notification.get_config")
    def test_generate_dashboard_report_collapses_unavailable_chip_structure(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
            dashboard={
                "data_perspective": {
                    "chip_structure": {
                        "profit_ratio": "missing data，Unable to judge",
                        "avg_cost": "missing data，Unable to judge",
                        "concentration": "missing data，Unable to judge",
                        "chip_health": "missing data，Unable to judge",
                    }
                }
            },
        )

        out = service.generate_dashboard_report([result], report_date="2026-02-01")

        self.assertIn("**chips**: Chip distribution is not enabled or the data source is temporarily unavailable，Not included in chip judgment。", out)
        self.assertEqual(out.count("missing data，Unable to judge"), 0)

    @mock.patch("src.notification.get_config")
    def test_generate_reports_hide_model_when_disabled(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(
            report_renderer_enabled=False,
            report_show_llm_model=False,
        )
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
            model_used="gemini/gemini-2.5-flash",
        )

        dashboard = service.generate_dashboard_report([result], report_date="2026-02-01")
        single = service.generate_single_stock_report(result)

        self.assertNotIn("Analytical model", dashboard)
        self.assertNotIn("gemini/gemini-2.5-flash", dashboard)
        self.assertNotIn("Analytical model", single)
        self.assertNotIn("gemini/gemini-2.5-flash", single)

    @mock.patch("src.notification.get_config")
    def test_generate_dashboard_report_localizes_english_fallback(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False, report_language="en")
        service = NotificationService()
        result = AnalysisResult(
            code="AAPL",
            name="Apple",
            sentiment_score=78,
            trend_prediction="Bullish",
            operation_advice="Buy",
            analysis_summary="Momentum remains constructive.",
            decision_type="buy",
            report_language="en",
            dashboard={
                "core_conclusion": {
                    "one_sentence": "Favor buying on pullbacks.",
                    "position_advice": {
                        "no_position": "Open a starter position.",
                        "has_position": "Hold and trail the stop.",
                    },
                },
                "battle_plan": {
                    "sniper_points": {
                        "ideal_buy": "180-182",
                        "stop_loss": "172",
                        "take_profit": "195",
                    }
                },
            },
        )

        out = service.generate_dashboard_report([result], report_date="2026-03-18")

        self.assertIn("Decision Dashboard", out)
        self.assertIn("Summary", out)
        self.assertIn("Action Levels", out)
        self.assertIn("Buy", out)

    @mock.patch("src.notification.get_config")
    def test_generate_dashboard_report_localizes_english_no_dashboard_fallback(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False, report_language="en")
        service = NotificationService()
        result = AnalysisResult(
            code="AAPL",
            name="Apple",
            sentiment_score=61,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Wait for confirmation.",
            report_language="en",
            buy_reason="Momentum remains constructive.",
            risk_warning="Watch for a failed breakout.",
            ma_analysis="Price remains above MA20.",
            volume_analysis="Volume is steady.",
            news_summary="Product cycle remains supportive.",
        )

        out = service.generate_dashboard_report([result], report_date="2026-03-19")

        self.assertIn("Rationale", out)
        self.assertIn("Risk Warning", out)
        self.assertIn("Technicals", out)
        self.assertIn("Moving Averages", out)
        self.assertIn("Volume", out)
        self.assertIn("News Flow", out)
        self.assertNotIn("Reason for operation", out)
        self.assertNotIn("Risk warning", out)
        self.assertNotIn("technical aspect", out)
        self.assertNotIn("news side", out)

    @mock.patch("src.notification.get_config")
    def test_generate_single_stock_report_localizes_english_fallback(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False, report_language="en")
        service = NotificationService()
        result = AnalysisResult(
            code="AAPL",
            name="Apple",
            sentiment_score=65,
            trend_prediction="Sideways",
            operation_advice="Hold",
            analysis_summary="Wait for a cleaner breakout.",
            report_language="en",
            dashboard={
                "core_conclusion": {"one_sentence": "Wait for confirmation."},
                "battle_plan": {
                    "sniper_points": {
                        "ideal_buy": "190",
                        "stop_loss": "182",
                        "take_profit": "205",
                    }
                },
            },
        )

        out = service.generate_single_stock_report(result)

        self.assertIn("Core Conclusion", out)
        self.assertIn("Action Levels", out)
        self.assertIn("Hold", out)

    def _make_fundamental_context(self) -> dict:
        return {
            "earnings": {
                "status": "ok",
                "data": {
                    "financial_report": {
                        "report_date": "2024-09-30",
                        "revenue": 1_236_000_000_000.0,  # 1.236 trillions -> 12360.00 billion
                        "net_profit_parent": 60_800_000_000.0,
                        "operating_cash_flow": 72_500_000_000.0,
                        "roe": 22.45,
                    },
                    "dividend": {
                        "events": [
                            {
                                "event_date": "2024-06-26",
                                "ex_dividend_date": "2024-06-26",
                                "cash_dividend_per_share": 30.876,
                                "is_pre_tax": True,
                            }
                        ],
                        "ttm_event_count": 1,
                        "ttm_cash_dividend_per_share": 30.876,
                        "ttm_dividend_yield_pct": 1.85,
                    },
                },
            },
            "growth": {
                "status": "ok",
                "data": {
                    "revenue_yoy": 15.23,
                    "net_profit_yoy": 19.87,
                    "roe": 22.45,
                    "gross_margin": 91.55,
                },
            },
            "boards": {
                "status": "ok",
                "data": {
                    "top": [
                        {"name": "Liquor", "change_pct": 3.42},
                        {"name": "food and beverage", "change_pct": 2.10},
                    ],
                    "bottom": [
                        {"name": "Photovoltaic equipment", "change_pct": -2.65},
                    ],
                },
            },
            "concept_boards": {
                "status": "ok",
                "data": {
                    "top": [
                        {"name": "MSCIChina", "change_pct": 1.23},
                    ],
                    "bottom": [],
                },
            },
            "belong_boards": [
                {"name": "Liquor", "code": "BK0596", "type": "Industry"},
                {"name": "MSCIChina", "code": "BK0805", "type": "concept"},
            ],
        }

    @mock.patch("src.notification.get_config")
    def test_generate_single_stock_report_appends_fundamental_blocks(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
        )
        result.fundamental_context = self._make_fundamental_context()

        out = service.generate_single_stock_report(result)

        # Financial summary
        self.assertIn("financial summary", out)
        self.assertIn("2024-09-30", out)
        self.assertIn("12360.00 billion", out)
        self.assertIn("22.45%", out)
        self.assertIn("15.23%", out)
        self.assertIn("91.55%", out)
        # Shareholder returns
        self.assertIn("shareholder return", out)
        self.assertIn("30.8760 Yuan", out)
        self.assertIn("1.85%", out)
        self.assertIn("2024-06-26", out)
        # Related sectors (liquor carries an industry signal; MSCI China carries a concept signal)
        self.assertIn("Related sections", out)
        self.assertIn("Liquor", out)
        self.assertIn("Leading the gains", out)
        self.assertIn("+3.42%", out)
        self.assertIn("MSCIChina", out)
        self.assertIn("- Liquor (Industry sector Leading the gains +3.42%)", out)
        self.assertIn("- MSCIChina (Concept section Leading the gains +1.23%)", out)
        self.assertIn("+1.23%", out)
        self.assertNotIn("| plate | Type | Sector performance | Sector rise and fall |", out)

    @mock.patch("src.notification.get_config")
    def test_related_boards_uses_concept_rankings_for_concept_boards(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
        )
        result.fundamental_context = {
            "boards": {"status": "ok", "data": {
                "top": [{"name": "Liquor", "change_pct": 2.31}],
                "bottom": [],
            }},
            "concept_boards": {"status": "ok", "data": {
                "top": [],
                "bottom": [{"name": "Liquor", "change_pct": -3.2}],
            }},
            "belong_boards": [{"name": "Liquor", "type": "concept"}],
        }

        out = service.generate_single_stock_report(result)

        self.assertIn("Related sections", out)
        self.assertIn("- Liquor (Concept section Lead the decline -3.20%)", out)
        self.assertNotIn("| Liquor | concept |", out)
        self.assertNotIn("+2.31%", out)

    @mock.patch("src.notification.get_config")
    def test_generate_single_stock_report_skips_fundamental_blocks_when_missing(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
        )

        out = service.generate_single_stock_report(result)

        self.assertNotIn("financial summary", out)
        self.assertNotIn("shareholder return", out)
        self.assertNotIn("Related sections", out)

    @mock.patch("src.notification.get_config")
    def test_generate_single_stock_report_handles_partial_fundamental_context(
        self, mock_get_config: mock.MagicMock
    ):
        """Only dividend data present — render shareholder return, skip the other two."""
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
        )
        result.fundamental_context = {
            "earnings": {
                "status": "partial",
                "data": {
                    "dividend": {
                        "events": [],
                        "ttm_event_count": 0,
                        "ttm_cash_dividend_per_share": 0.5,
                    }
                },
            },
        }

        out = service.generate_single_stock_report(result)

        self.assertNotIn("financial summary", out)
        self.assertIn("shareholder return", out)
        self.assertIn("0.5000 Yuan", out)
        self.assertNotIn("Related sections", out)

    @mock.patch("src.notification.get_config")
    def test_generate_single_stock_report_uses_currency_for_us(
        self, mock_get_config: mock.MagicMock
    ):
        """USD currency on financial_report yields billion-USD suffix instead of billion-CNY."""
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="AAPL",
            name="Apple Inc.",
            sentiment_score=64,
            trend_prediction="shock",
            operation_advice="wait and see",
            analysis_summary="wait and see AI deliver rhythm。",
        )
        result.fundamental_context = {
            "earnings": {
                "status": "ok",
                "data": {
                    "financial_report": {
                        "report_date": "2026-03-31",
                        "revenue": 1.11e11,
                        "net_profit_parent": 2.95e10,
                        "operating_cash_flow": 2.87e10,
                        "roe": 141.47,
                        "currency": "USD",
                    },
                    "dividend": {
                        "events": [{
                            "event_date": "2026-05-11",
                            "ex_dividend_date": "2026-05-11",
                            "cash_dividend_per_share": 0.27,
                            "is_pre_tax": True,
                        }],
                        "ttm_event_count": 4,
                        "ttm_cash_dividend_per_share": 1.05,
                        "ttm_dividend_yield_pct": 0.36,
                    },
                },
            },
            "growth": {"status": "ok", "data": {"revenue_yoy": 16.60, "roe": 141.47, "gross_margin": 47.86}},
            "belong_boards": [
                {"name": "Technology", "type": "Industry"},
                {"name": "Consumer Electronics", "type": "concept"},
            ],
        }

        out = service.generate_single_stock_report(result)

        self.assertIn("financial summary", out)
        self.assertIn("billion US dollars", out)
        self.assertNotIn("12360.00 billion", out)
        # Sample expected formatted values
        self.assertIn("1110.00 billion US dollars", out)
        self.assertIn("141.47%", out)
        # Dividend per share also picks up currency suffix
        self.assertIn("1.0500 US dollars", out)
        # Sector + industry render as belong_boards
        self.assertIn("Technology", out)
        self.assertIn("Consumer Electronics", out)

    @mock.patch("src.notification.get_config")
    def test_related_boards_drops_signal_columns_when_no_sector_data(
        self, mock_get_config: mock.MagicMock
    ):
        """HK/US lack sector ranking board -- drop status / change_pct columns entirely."""
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="AAPL",
            name="Apple Inc.",
            sentiment_score=64,
            trend_prediction="shock",
            operation_advice="wait and see",
            analysis_summary="wait and see AI deliver rhythm。",
        )
        result.fundamental_context = {
            "earnings": {"status": "ok", "data": {
                "financial_report": {
                    "report_date": "2026-03-31",
                    "revenue": 1.11e11,
                    "currency": "USD",
                },
            }},
            "growth": {"status": "ok", "data": {"revenue_yoy": 16.60}},
            "belong_boards": [
                {"name": "Technology", "type": "Industry"},
                {"name": "Consumer Electronics", "type": "concept"},
            ],
        }

        out = service.generate_single_stock_report(result)

        self.assertIn("Related sections", out)
        self.assertIn("Technology / Consumer Electronics", out)
        self.assertIn("Technology", out)
        self.assertIn("Consumer Electronics", out)
        # When no sector ranking data is available, drop the 4-col layout.
        self.assertNotIn("Sector performance", out)
        self.assertNotIn("Sector rise and fall", out)
        # And no table/type noise either.
        self.assertNotIn("| plate | Type |", out)
        self.assertNotIn("| -- | -- |", out)

    @mock.patch("src.notification.get_config")
    def test_related_boards_without_type_infers_concepts_and_keeps_unknowns(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
        )
        result.fundamental_context = {
            "earnings": {"status": "ok", "data": {}},
            "growth": {"status": "ok", "data": {}},
            "belong_boards": [
                {"name": "LiquorⅢ"},
                {"name": "LiquorⅡ"},
                {"name": "food and beverage"},
                {"name": "Guizhou plate"},
                {"name": "winemaking concept"},
            ],
        }

        out = service.generate_single_stock_report(result)

        self.assertIn("Related sections", out)
        self.assertIn("LiquorⅢ / LiquorⅡ / food and beverage / Guizhou plate / winemaking concept", out)
        self.assertNotIn("| plate | Type |", out)
        self.assertNotIn("| LiquorⅢ | N/A |", out)

    @mock.patch("src.notification.get_config")
    def test_related_boards_renders_each_board_signal_without_placeholder(
        self, mock_get_config: mock.MagicMock
    ):
        """Rows without a matching change_pct stay as plain board entries."""
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
        )
        result.fundamental_context = {
            "earnings": {"status": "ok", "data": {}},
            "growth": {"status": "ok", "data": {}},
            "boards": {"status": "ok", "data": {
                "top": [{"name": "Liquor", "change_pct": 3.42}],
                "bottom": [],
            }},
            "belong_boards": [
                {"name": "Liquor", "code": "BK0596", "type": "Industry"},
                {"name": "MSCIChina", "code": "BK0805", "type": "concept"},
            ],
        }

        out = service.generate_single_stock_report(result)

        self.assertNotIn("Sector performance", out)
        self.assertNotIn("Sector rise and fall", out)
        self.assertIn("Leading the gains", out)
        self.assertIn("+3.42%", out)
        self.assertIn("- Liquor (Industry sector Leading the gains +3.42%)", out)
        self.assertIn("MSCIChina", out)
        self.assertIn("- MSCIChina", out)
        self.assertNotIn("- MSCIChina (", out)
        self.assertNotIn("| MSCIChina | concept | -- | -- |", out)

    @mock.patch("src.notification.get_config")
    def test_related_boards_ignores_matching_signal_without_change_pct(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
        )
        result.fundamental_context = {
            "earnings": {"status": "ok", "data": {}},
            "growth": {"status": "ok", "data": {}},
            "boards": {"status": "ok", "data": {
                "top": [{"name": "Liquor"}],
                "bottom": [],
            }},
            "belong_boards": [
                {"name": "Liquor", "code": "BK0596", "type": "Industry"},
            ],
        }

        out = service.generate_single_stock_report(result)

        self.assertIn("Related sections", out)
        self.assertIn("Liquor", out)
        self.assertNotIn("| Liquor | Industry |", out)
        self.assertNotIn("Leading the gains", out)
        self.assertNotIn("Sector rise and fall", out)

    @mock.patch("src.notification.get_config")
    def test_generate_single_stock_report_uses_currency_for_hk(
        self, mock_get_config: mock.MagicMock
    ):
        """HK ADRs have financialCurrency=CNY but trade/pay dividends in HKD.

        The financial summary must render in CNY (income statement) while
        dividends must render in HKD -- they are NOT the same currency on
        yfinance HK payloads, so the renderer must read each block's own
        ``currency`` field rather than assuming a single global currency.
        """
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="HK09988",
            name="Alibaba-W",
            sentiment_score=68,
            trend_prediction="long",
            operation_advice="buy on dips",
            analysis_summary="Cloud business returns to normal，Buyback continues。",
        )
        result.fundamental_context = {
            "earnings": {
                "status": "ok",
                "data": {
                    "financial_report": {
                        "report_date": "2026-03-31",
                        "revenue": 1.02e12,
                        "net_profit_parent": 1.04e11,
                        "operating_cash_flow": 3.6e10,
                        "roe": 9.22,
                        "currency": "CNY",
                    },
                    "dividend": {
                        "events": [{
                            "event_date": "2025-06-11",
                            "ex_dividend_date": "2025-06-11",
                            "cash_dividend_per_share": 1.95812,
                            "is_pre_tax": True,
                        }],
                        "ttm_event_count": 1,
                        "ttm_cash_dividend_per_share": 1.95812,
                        "ttm_dividend_yield_pct": 1.75,
                        "currency": "HKD",
                    },
                },
            },
            "growth": {"status": "ok", "data": {"revenue_yoy": 2.9, "roe": 9.22, "gross_margin": 39.81}},
            "belong_boards": [
                {"name": "Consumer Cyclical", "type": "Industry"},
                {"name": "Internet Retail", "type": "concept"},
            ],
        }

        out = service.generate_single_stock_report(result)

        # Income statement still rendered in CNY (financialCurrency).
        self.assertIn("10200.00 billion", out)
        # Dividend per share follows the dividend currency, NOT the financial currency.
        self.assertIn("1.9581 Hong Kong dollar", out)
        self.assertNotIn("1.9581 Yuan ", out)
        self.assertIn("Consumer Cyclical", out)

    @mock.patch("src.notification.get_config")
    def test_dividend_currency_falls_back_to_financial_when_missing(
        self, mock_get_config: mock.MagicMock
    ):
        """A-share AkShare payload has no dividend.currency — fall back to financial_report.currency."""
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
        )
        result.fundamental_context = {
            "earnings": {
                "status": "ok",
                "data": {
                    "financial_report": {"report_date": "2026-03-31", "revenue": 4.5e10},
                    "dividend": {
                        "events": [{"event_date": "2025-06-20", "ex_dividend_date": "2025-06-20"}],
                        "ttm_event_count": 1,
                        "ttm_cash_dividend_per_share": 27.6,
                    },
                },
            },
        }

        out = service.generate_single_stock_report(result)

        # Without explicit dividend currency, default to CNY (matches AkShare A-share semantics).
        self.assertIn("27.6000 Yuan", out)

    @mock.patch("src.notification.get_config")
    def test_generate_dashboard_report_appends_fundamental_blocks(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(report_renderer_enabled=False)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
            dashboard={
                "core_conclusion": {"one_sentence": "Steady hold"},
                "battle_plan": {
                    "sniper_points": {
                        "ideal_buy": "1600",
                        "stop_loss": "1500",
                        "take_profit": "1800",
                    }
                },
            },
        )
        result.fundamental_context = self._make_fundamental_context()

        out = service.generate_dashboard_report([result], report_date="2026-05-20")

        self.assertIn("financial summary", out)
        self.assertIn("shareholder return", out)
        self.assertIn("Related sections", out)
        self.assertIn("Liquor", out)
        self.assertIn("Leading the gains", out)

    @mock.patch("src.notification.get_config")
    def test_history_compare_context_uses_cache(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(report_history_compare_n=3)
        service = NotificationService()
        result = AnalysisResult(
            code="600519",
            name="Kweichow Moutai",
            sentiment_score=72,
            trend_prediction="long",
            operation_advice="hold",
            analysis_summary="Robust",
            query_id="q-1",
        )

        with mock.patch(
            "src.services.history_comparison_service.get_signal_changes_batch",
            return_value={"600519": []},
        ) as mock_batch:
            first = service._get_history_compare_context([result])
            second = service._get_history_compare_context([result])

        self.assertEqual(first, {"history_by_code": {"600519": []}})
        self.assertEqual(second, {"history_by_code": {"600519": []}})
        mock_batch.assert_called_once()

    @mock.patch("src.notification.get_config")
    @mock.patch("smtplib.SMTP_SSL")
    def test_send_to_email_via_notification_service(
        self, mock_smtp_ssl: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(
            email_sender="user@qq.com",
            email_password="PASS",
            email_receivers=["default@example.com"],
        )
        mock_get_config.return_value = cfg

        service = NotificationService()
        self.assertIn(NotificationChannel.EMAIL, service.get_available_channels())

        ok = service.send("email content")

        self.assertTrue(ok)
        mock_smtp_ssl.assert_called_once()
        mock_smtp_ssl.return_value.send_message.assert_called_once()

    @mock.patch("src.notification.get_config")
    @mock.patch("smtplib.SMTP_SSL")
    def test_send_to_email_with_stock_group_routing(
        self, mock_smtp_ssl: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(
            email_sender="user@qq.com",
            email_password="PASS",
            email_receivers=["default@example.com"],
            stock_email_groups=[(["000001", "600519"], ["group@example.com"])],
        )
        mock_get_config.return_value = cfg

        service = NotificationService()
        self.assertIn(NotificationChannel.EMAIL, service.get_available_channels())

        server = mock_smtp_ssl.return_value

        ok = service.send("content", email_stock_codes=["000001"])

        self.assertTrue(ok)
        mock_smtp_ssl.assert_called_once()
        server.send_message.assert_called_once()
        msg = server.send_message.call_args[0][0]
        self.assertIn("group@example.com", msg["To"])

    @mock.patch("src.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_feishu_via_notification_service(self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock):
        cfg = _make_config(feishu_webhook_url="https://feishu.example")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200, {"code": 0})

        service = NotificationService()
        self.assertIn(NotificationChannel.FEISHU, service.get_available_channels())

        ok = service.send("hello feishu")

        self.assertTrue(ok)
        mock_post.assert_called_once()
        
    @mock.patch("src.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_feishu_via_notification_service_requires_chunking(self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock):
        cfg = _make_config(feishu_webhook_url="https://feishu.example", feishu_max_bytes=2000)
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200, {"code": 0})

        service = NotificationService()
        self.assertIn(NotificationChannel.FEISHU, service.get_available_channels())

        ok = service.send("A" * 6000)

        self.assertTrue(ok)
        self.assertAlmostEqual(mock_post.call_count, 4, delta=1)

    @mock.patch("src.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_gotify_via_notification_service(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(gotify_url="https://gotify.example", gotify_token="secret-token")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200)

        service = NotificationService()
        self.assertIn(NotificationChannel.GOTIFY, service.get_available_channels())

        ok = service.send("gotify content")

        self.assertTrue(ok)
        mock_post.assert_called_once()
        self.assertEqual(mock_post.call_args.args[0], "https://gotify.example/message")
        self.assertEqual(mock_post.call_args.kwargs["headers"]["X-Gotify-Key"], "secret-token")
        self.assertEqual(mock_post.call_args.kwargs["json"]["message"], "gotify content")
        self.assertEqual(
            mock_post.call_args.kwargs["json"]["extras"]["client::display"]["contentType"],
            "text/markdown",
        )

    @mock.patch("src.notification.get_config")
    def test_gotify_without_token_is_not_available(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(gotify_url="https://gotify.example")

        service = NotificationService()

        self.assertNotIn(NotificationChannel.GOTIFY, service.get_available_channels())
        self.assertFalse(service.is_available())

    @mock.patch("src.notification.get_config")
    def test_gotify_blank_token_is_not_available(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(
            gotify_url="https://gotify.example",
            gotify_token="   ",
        )

        service = NotificationService()

        self.assertNotIn(NotificationChannel.GOTIFY, service.get_available_channels())
        self.assertFalse(service.is_available())

    @mock.patch("src.notification.get_config")
    def test_gotify_message_endpoint_is_not_available(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(
            gotify_url="https://gotify.example/message",
            gotify_token="secret-token",
        )

        service = NotificationService()

        self.assertNotIn(NotificationChannel.GOTIFY, service.get_available_channels())
        self.assertFalse(service.is_available())

    @mock.patch("src.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_gotify_does_not_trigger_markdown_to_image(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(
            gotify_url="https://gotify.example",
            gotify_token="secret-token",
            markdown_to_image_channels=["gotify"],
        )
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200)

        service = NotificationService()
        with mock.patch("src.md2img.markdown_to_image", return_value=b"png") as mock_md2img:
            ok = service.send("gotify content")

        self.assertTrue(ok)
        mock_md2img.assert_not_called()
        mock_post.assert_called_once()

    @mock.patch("src.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_ntfy_via_notification_service(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(ntfy_url="https://ntfy.sh/dsa-topic")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200)

        service = NotificationService()
        self.assertIn(NotificationChannel.NTFY, service.get_available_channels())

        ok = service.send("ntfy content")

        self.assertTrue(ok)
        mock_post.assert_called_once()
        self.assertEqual(mock_post.call_args.args[0], "https://ntfy.sh")
        self.assertEqual(mock_post.call_args.kwargs["json"]["topic"], "dsa-topic")

    @mock.patch("src.notification.get_config")
    def test_ntfy_url_without_topic_is_not_available(self, mock_get_config: mock.MagicMock):
        mock_get_config.return_value = _make_config(ntfy_url="https://ntfy.sh")

        service = NotificationService()

        self.assertNotIn(NotificationChannel.NTFY, service.get_available_channels())
        self.assertFalse(service.is_available())

    @mock.patch("src.notification.get_config")
    def test_ntfy_url_with_unsupported_scheme_is_not_available(
        self, mock_get_config: mock.MagicMock
    ):
        mock_get_config.return_value = _make_config(ntfy_url="ntfy://ntfy.sh/dsa-topic")

        service = NotificationService()

        self.assertNotIn(NotificationChannel.NTFY, service.get_available_channels())
        self.assertFalse(service.is_available())

    @mock.patch("src.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_ntfy_does_not_trigger_markdown_to_image(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(
            ntfy_url="https://ntfy.sh/dsa-topic",
            markdown_to_image_channels=["ntfy"],
        )
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200)

        service = NotificationService()
        with mock.patch("src.md2img.markdown_to_image", return_value=b"png") as mock_md2img:
            ok = service.send("ntfy content")

        self.assertTrue(ok)
        mock_md2img.assert_not_called()
        mock_post.assert_called_once()

    @mock.patch("src.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_pushover_via_notification_service(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(
            pushover_user_key="USER",
            pushover_api_token="TOKEN",
        )
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200, {"status": 1})

        service = NotificationService()
        self.assertIn(NotificationChannel.PUSHOVER, service.get_available_channels())

        ok = service.send("pushover content")

        self.assertTrue(ok)
        mock_post.assert_called_once()

    @mock.patch("src.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_pushplus_via_notification_service(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(pushplus_token="TOKEN")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200, {"code": 200})

        service = NotificationService()
        self.assertIn(NotificationChannel.PUSHPLUS, service.get_available_channels())

        ok = service.send("pushplus content")

        self.assertTrue(ok)
        mock_post.assert_called_once()

    @mock.patch("src.notification_sender.pushplus_sender.time.sleep")
    @mock.patch("src.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_pushplus_via_notification_service_requires_chunking(
        self,
        mock_post: mock.MagicMock,
        mock_get_config: mock.MagicMock,
        _mock_sleep: mock.MagicMock,
    ):
        cfg = _make_config(pushplus_token="TOKEN")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200, {"code": 200})

        service = NotificationService()
        self.assertIn(NotificationChannel.PUSHPLUS, service.get_available_channels())

        ok = service.send("A" * 25000)

        self.assertTrue(ok)
        self.assertGreaterEqual(mock_post.call_count, 2)

    @mock.patch("src.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_slack_via_notification_service_with_webhook(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(slack_webhook_url="https://hooks.slack.com/services/T/B/xxx")
        mock_get_config.return_value = cfg
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.text = "ok"
        mock_post.return_value = resp

        service = NotificationService()
        self.assertIn(NotificationChannel.SLACK, service.get_available_channels())

        ok = service.send("slack content")

        self.assertTrue(ok)
        mock_post.assert_called_once()

    @mock.patch("src.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_slack_via_notification_service_with_bot(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(slack_bot_token="xoxb-test", slack_channel_id="C123")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200, {"ok": True})

        service = NotificationService()
        self.assertIn(NotificationChannel.SLACK, service.get_available_channels())

        ok = service.send("slack bot content")

        self.assertTrue(ok)
        mock_post.assert_called_once()

    @mock.patch("src.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_serverchan3_via_notification_service(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(serverchan3_sendkey="SCTKEY")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200, {"code": 0})

        service = NotificationService()
        self.assertIn(NotificationChannel.SERVERCHAN3, service.get_available_channels())

        ok = service.send("serverchan content")

        self.assertTrue(ok)
        mock_post.assert_called_once()

    @mock.patch("src.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_telegram_via_notification_service(
        self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock
    ):
        cfg = _make_config(telegram_bot_token="TOKEN", telegram_chat_id="123")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200, {"ok": True})

        service = NotificationService()
        self.assertIn(NotificationChannel.TELEGRAM, service.get_available_channels())

        ok = service.send("hello telegram")

        self.assertTrue(ok)
        mock_post.assert_called_once()

    @mock.patch("src.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_wechat_via_notification_service(self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock):
        cfg = _make_config(wechat_webhook_url="https://wechat.example")
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200, {"errcode": 0})

        service = NotificationService()
        self.assertIn(NotificationChannel.WECHAT, service.get_available_channels())

        ok = service.send("hello wechat")

        self.assertTrue(ok)
        mock_post.assert_called_once()

    @mock.patch("src.notification.get_config")
    @mock.patch("requests.post")
    def test_send_to_wechat_via_notification_service_requires_chunking(self, mock_post: mock.MagicMock, mock_get_config: mock.MagicMock):
        cfg = _make_config(wechat_webhook_url="https://wechat.example", wechat_max_bytes=2000)
        mock_get_config.return_value = cfg
        mock_post.return_value = _make_response(200, {"errcode": 0})

        service = NotificationService()
        self.assertIn(NotificationChannel.WECHAT, service.get_available_channels())

        ok = service.send("A" * 6000)

        self.assertTrue(ok)
        self.assertAlmostEqual(mock_post.call_count, 4, delta=1)


if __name__ == "__main__":
    unittest.main()
