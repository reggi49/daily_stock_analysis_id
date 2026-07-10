# -*- coding: utf-8 -*-
"""
===================================
Feishu Stream Mode Adapter
===================================

Connects to the bot using Feishu's official lark-oapi SDK WebSocket long connection mode,
no public IP or Webhook configuration required.

Advantages:
- No public IP or domain needed
- No Webhook URL configuration needed
- Receives messages via WebSocket long connection
- Simpler integration
- Built-in auto-reconnect and heartbeat keepalive

Dependencies:
pip install lark-oapi

Feishu long connection docs:
https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/server-side-sdk/python--sdk/handle-events
"""

import json
import logging
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, Callable
import time

logger = logging.getLogger(__name__)

# Try to import Feishu SDK
try:
    import lark_oapi as lark
    from lark_oapi import ws
    from lark_oapi.api.im.v1 import (
        P2ImMessageReceiveV1,
        ReplyMessageRequest,
        ReplyMessageRequestBody,
        CreateMessageRequest,
        CreateMessageRequestBody,
    )

    FEISHU_SDK_AVAILABLE = True
except ImportError:
    FEISHU_SDK_AVAILABLE = False
    logger.warning("[Feishu Stream] lark-oapi SDK not installed, Stream mode unavailable")
    logger.warning("[Feishu Stream] Please run: pip install lark-oapi")

from bot.models import BotMessage, BotResponse, ChatType
from src.formatters import format_feishu_markdown, chunk_content_by_max_bytes
from src.config import get_config


class FeishuReplyClient:
    """
    Feishu message reply client.

    Uses Feishu API to send reply messages.
    """

    def __init__(self, app_id: str, app_secret: str):
        """
        Args:
            app_id: Feishu app ID
            app_secret: Feishu app secret
        """
        if not FEISHU_SDK_AVAILABLE:
            raise ImportError("lark-oapi SDK not installed")

        self._client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .log_level(lark.LogLevel.WARNING) \
            .build()

        # Get configured max bytes
        config = get_config()
        self._max_bytes = getattr(config, 'feishu_max_bytes', 20000)

    def _send_interactive_card(self, content: str, message_id: Optional[str] = None,
                               chat_id: Optional[str] = None,
                               receive_id_type: str = "chat_id",
                               at_user: bool = False, user_id: Optional[str] = None) -> bool:
        """
        Send interactive card message (supports Markdown rendering).

        Args:
            content: Markdown-formatted content
            message_id: Original message ID (used when replying)
            chat_id: Chat ID (used for proactive sending)
            receive_id_type: Recipient ID type
            at_user: Whether to @mention the user
            user_id: User open_id (required when at_user=True)

        Returns:
            Whether the send was successful
        """
        try:
            # If @mention is needed, prepend @ marker
            final_content = content
            if at_user and user_id:
                final_content = f"<at user_id=\"{user_id}\"></at> {content}"

            # Build interactive card payload
            card_data = {
                "config": {"wide_screen_mode": True},
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": final_content
                        }
                    }
                ]
            }

            content_json = json.dumps(card_data)

            if message_id:
                # Reply to message
                request = ReplyMessageRequest.builder() \
                    .message_id(message_id) \
                    .request_body(
                    ReplyMessageRequestBody.builder()
                    .content(content_json)
                    .msg_type("interactive")
                    .build()
                ) \
                    .build()
                response = self._client.im.v1.message.reply(request)
            else:
                # Proactive send message
                request = CreateMessageRequest.builder() \
                    .receive_id_type(receive_id_type) \
                    .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(chat_id)
                    .content(content_json)
                    .msg_type("interactive")
                    .build()
                ) \
                    .build()
                response = self._client.im.v1.message.create(request)

            if not response.success():
                logger.error(
                    f"[Feishu Stream] Failed to send interactive card: code={response.code}, "
                    f"msg={response.msg}, log_id={response.get_log_id()}"
                )
                return False

            logger.debug("[Feishu Stream] Interactive card sent successfully")
            return True

        except Exception as e:
            logger.error(f"[Feishu Stream] Exception sending interactive card: {e}")
            return False

    def reply_text(self, message_id: str, text: str, at_user: bool = False,
                   user_id: Optional[str] = None) -> bool:
        """
        Reply with text message (supports interactive cards and chunked sending).

        Args:
            message_id: Original message ID
            text: Reply text
            at_user: Whether to @mention the user
            user_id: User open_id (required when at_user=True)

        Returns:
            Whether the send was successful
        """
        # Convert text to Feishu Markdown format
        formatted_text = format_feishu_markdown(text)

        # Check if chunked sending is needed
        content_bytes = len(formatted_text.encode('utf-8'))
        if content_bytes > self._max_bytes:
            logger.info(
                f"[Feishu Stream] Reply message content too long ({content_bytes} bytes), sending in chunks"
            )
            return self._send_to_chat_chunked(
                formatted_text,
                lambda chunk: self._send_interactive_card(
                    chunk,
                    message_id=message_id,
                    at_user=at_user,
                    user_id=user_id,
                ),
            )

        # Single message, use interactive card
        return self._send_interactive_card(
            formatted_text, message_id=message_id, at_user=at_user, user_id=user_id
        )

    def send_to_chat(self, chat_id: str, text: str,
                     receive_id_type: str = "chat_id") -> bool:
        """
        Send message to a specified chat (supports interactive cards and chunked sending).

        Args:
            chat_id: Chat ID
            text: Message text
            receive_id_type: Recipient ID type, defaults to chat_id

        Returns:
            Whether the send was successful
        """
        # Convert text to Feishu Markdown format
        formatted_text = format_feishu_markdown(text)

        # Check if chunked sending is needed
        content_bytes = len(formatted_text.encode('utf-8'))
        if content_bytes > self._max_bytes:
            logger.info(
                f"[Feishu Stream] Message content too long ({content_bytes} bytes), sending in chunks"
            )
            return self._send_to_chat_chunked(
                formatted_text,
                lambda chunk: self._send_interactive_card(
                    chunk,
                    chat_id=chat_id,
                    receive_id_type=receive_id_type,
                ),
            )

        # Single message, use interactive card
        return self._send_interactive_card(formatted_text, chat_id=chat_id, receive_id_type=receive_id_type)

    def _send_to_chat_chunked(self, content: str, send_func: Callable[[str], bool]) -> bool:
        """
        Send message in chunks (supports interactive cards and chunked sending).

        Args:
            content: Message text
            send_func: Function to send a single chunk, returns whether it was sent successfully

        Returns:
            Whether all chunks were sent successfully
        """
        chunks = chunk_content_by_max_bytes(content, self._max_bytes, add_page_marker=True)
        success_count = 0
        for i, chunk in enumerate(chunks):
            if send_func(chunk):
                success_count += 1
            else:
                logger.error(f"[Feishu Stream] Failed to send message chunk: {chunk}")
            if i < len(chunks) - 1:
                time.sleep(1)
        return success_count == len(chunks)


class FeishuStreamHandler:
    """
    Feishu Stream mode message handler.

    Converts SDK events into unified BotMessage format
    and calls the command dispatcher for processing.
    """

    def __init__(
            self,
            on_message: Callable[[BotMessage], BotResponse],
            reply_client: FeishuReplyClient
    ):
        """
        Args:
            on_message: Message processing callback, receives BotMessage and returns BotResponse
            reply_client: Feishu reply client
        """
        self._on_message = on_message
        self._reply_client = reply_client
        self._logger = logger
        # Different conversations can run in parallel, but one conversation
        # must stay FIFO so multi-turn chat and replies do not get reordered.
        self._executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="feishu-msg")
        self._pending_messages: dict[str, deque[BotMessage]] = {}
        self._active_conversations: set[str] = set()
        self._queue_lock = threading.Lock()
        self._shutdown = False

    def _conversation_key(self, bot_message: BotMessage) -> str:
        """Return the ordering key used for per-conversation FIFO processing."""
        if bot_message.chat_type == ChatType.PRIVATE:
            return bot_message.chat_id or bot_message.user_id or bot_message.message_id

        chat_id = bot_message.chat_id or "unknown-chat"
        user_id = bot_message.user_id or "unknown-user"
        return f"{chat_id}:{user_id}"

    def _enqueue_message(self, bot_message: BotMessage) -> None:
        """Queue a message and start a worker when its conversation is idle."""
        if self._shutdown:
            self._logger.debug("[Feishu Stream] Handler already stopped, dropping message")
            return

        conversation_key = self._conversation_key(bot_message)
        should_start_worker = False

        with self._queue_lock:
            self._pending_messages.setdefault(conversation_key, deque()).append(bot_message)
            if conversation_key not in self._active_conversations:
                self._active_conversations.add(conversation_key)
                should_start_worker = True

        if should_start_worker:
            try:
                self._executor.submit(self._drain_conversation, conversation_key)
            except RuntimeError as exc:
                with self._queue_lock:
                    self._active_conversations.discard(conversation_key)
                    self._pending_messages.pop(conversation_key, None)
                self._logger.error("[Feishu Stream] Failed to start message processing thread: %s", exc)

    def _drain_conversation(self, conversation_key: str) -> None:
        """Drain one conversation queue in FIFO order."""
        while True:
            with self._queue_lock:
                queue = self._pending_messages.get(conversation_key)
                if not queue:
                    self._pending_messages.pop(conversation_key, None)
                    self._active_conversations.discard(conversation_key)
                    return
                bot_message = queue.popleft()

            self._process_message(bot_message)

    def _process_message(self, bot_message: BotMessage) -> None:
        """Execute command handling off the SDK callback thread."""
        try:
            response = self._on_message(bot_message)

            if response and response.text:
                self._reply_client.reply_text(
                    message_id=bot_message.message_id,
                    text=response.text,
                    at_user=response.at_user,
                    user_id=bot_message.user_id if response.at_user else None,
                )
        except Exception as e:
            self._logger.error(f"[Feishu Stream] Async message processing failed: {e}")
            self._logger.exception(e)

    @staticmethod
    def _truncate_log_content(text: str, max_len: int = 200) -> str:
        """Truncate log content"""
        cleaned = text.replace("\n", " ").strip()
        if len(cleaned) > max_len:
            return f"{cleaned[:max_len]}..."
        return cleaned

    def _log_incoming_message(self, message: BotMessage) -> None:
        """Log incoming message"""
        content = message.raw_content or message.content or ""
        summary = self._truncate_log_content(content)
        self._logger.info(
            "[Feishu Stream] Incoming message: msg_id=%s user_id=%s "
            "chat_id=%s chat_type=%s content=%s",
            message.message_id,
            message.user_id,
            message.chat_id,
            getattr(message.chat_type, "value", message.chat_type),
            summary,
        )

    def handle_message(self, event: 'P2ImMessageReceiveV1') -> None:
        """
        Handle received message events.

        Args:
            event: Feishu message receive event
        """
        try:
            # Parse message
            bot_message = self._parse_event_message(event)

            if bot_message is None:
                return

            self._log_incoming_message(bot_message)

            self._enqueue_message(bot_message)

        except Exception as e:
            self._logger.error(f"[Feishu Stream] Message processing failed: {e}")
            self._logger.exception(e)

    def _parse_event_message(self, event: 'P2ImMessageReceiveV1') -> Optional[BotMessage]:
        """
        Parse Feishu event message into unified format.

        Args:
            event: P2ImMessageReceiveV1 event object
        """
        try:
            event_data = event.event
            if event_data is None:
                return None

            message_data = event_data.message
            sender_data = event_data.sender

            if message_data is None:
                return None

            # Only process text messages
            message_type = message_data.message_type or ""
            if message_type != "text":
                self._logger.debug(f"[Feishu Stream] Ignoring non-text message: {message_type}")
                return None

            # Parse message content
            content_str = message_data.content or "{}"
            try:
                content_json = json.loads(content_str)
                raw_content = content_json.get("text", "")
            except json.JSONDecodeError:
                raw_content = content_str

            # Extract command (remove @bot)
            content = self._extract_command(raw_content, message_data.mentions)
            mentioned = "@" in raw_content or bool(message_data.mentions)

            # Get sender info
            user_id = ""
            if sender_data and sender_data.sender_id:
                user_id = sender_data.sender_id.open_id or sender_data.sender_id.user_id or ""

            # Get chat type
            chat_type_str = message_data.chat_type or ""
            if chat_type_str == "group":
                chat_type = ChatType.GROUP
            elif chat_type_str == "p2p":
                chat_type = ChatType.PRIVATE
            else:
                chat_type = ChatType.UNKNOWN

            # Create timestamp
            create_time = message_data.create_time
            try:
                if create_time:
                    timestamp = datetime.fromtimestamp(int(create_time) / 1000)
                else:
                    timestamp = datetime.now()
            except (ValueError, TypeError):
                timestamp = datetime.now()

            # Build raw data
            raw_data = {
                "header": {
                    "event_id": event.header.event_id if event.header else "",
                    "event_type": event.header.event_type if event.header else "",
                    "create_time": event.header.create_time if event.header else "",
                    "token": event.header.token if event.header else "",
                    "app_id": event.header.app_id if event.header else "",
                },
                "event": {
                    "message_id": message_data.message_id,
                    "chat_id": message_data.chat_id,
                    "chat_type": message_data.chat_type,
                    "content": message_data.content,
                }
            }

            return BotMessage(
                platform="feishu",
                message_id=message_data.message_id or "",
                user_id=user_id,
                user_name=user_id,  # Feishu does not directly return user name
                chat_id=message_data.chat_id or "",
                chat_type=chat_type,
                content=content,
                raw_content=raw_content,
                mentioned=mentioned,
                mentions=[m.key or "" for m in (message_data.mentions or [])],
                timestamp=timestamp,
                raw_data=raw_data,
            )

        except Exception as e:
            self._logger.error(f"[Feishu Stream] Message parsing failed: {e}")
            return None

    def _extract_command(self, text: str, mentions: list) -> str:
        """
        Extract command content (remove @bot).

        Feishu's @user format is: @_user_1, @_user_2, etc.

        Args:
            text: Raw message text
            mentions: @mention list
        """
        import re

        # Method 1: Remove via mentions list (exact match)
        for mention in (mentions or []):
            key = getattr(mention, 'key', '') or ''
            if key:
                text = text.replace(key, '')

        # Method 2: Regex fallback, remove Feishu @user format (@_user_N)
        # Takes effect when mentions is empty or not properly passed
        text = re.sub(r'@_user_\d+\s*', '', text)

        # Clean up extra whitespace
        return ' '.join(text.split())

    def shutdown(self, wait: bool = False) -> None:
        """Stop accepting new messages and tear down worker threads."""
        self._shutdown = True
        with self._queue_lock:
            self._pending_messages.clear()
            self._active_conversations.clear()
        self._executor.shutdown(wait=wait)


class FeishuStreamClient:
    """
    Feishu Stream mode client.

    Wraps the lark-oapi SDK WebSocket client with a simple startup interface.

    Usage:
        client = FeishuStreamClient()
        client.start()  # Blocking

        # Or run in background
        client.start_background()
    """

    def __init__(
            self,
            app_id: Optional[str] = None,
            app_secret: Optional[str] = None
    ):
        """
        Args:
            app_id: App ID (reads from config if not provided)
            app_secret: App secret (reads from config if not provided)
        """
        if not FEISHU_SDK_AVAILABLE:
            raise ImportError(
                "lark-oapi SDK not installed.\n"
                "Please run: pip install lark-oapi"
            )

        from src.config import get_config
        config = get_config()

        self._app_id = app_id or getattr(config, 'feishu_app_id', None)
        self._app_secret = app_secret or getattr(config, 'feishu_app_secret', None)

        if not self._app_id or not self._app_secret:
            raise ValueError(
                "Feishu Stream mode requires FEISHU_APP_ID and FEISHU_APP_SECRET to be configured"
            )

        self._ws_client: Optional[ws.Client] = None
        self._reply_client: Optional[FeishuReplyClient] = None
        self._message_handler: Optional[FeishuStreamHandler] = None
        self._background_thread: Optional[threading.Thread] = None
        self._running = False

    def _create_message_handler(self) -> Callable[[BotMessage], BotResponse]:
        """Create message processing function"""

        def handle_message(message: BotMessage) -> BotResponse:
            from bot.dispatcher import get_dispatcher
            dispatcher = get_dispatcher()
            return dispatcher.dispatch(message)

        return handle_message

    def _create_event_handler(self) -> 'lark.EventDispatcherHandler':
        """Create event dispatch handler"""
        # Create reply client
        self._reply_client = FeishuReplyClient(self._app_id, self._app_secret)

        # Create message handler
        handler = FeishuStreamHandler(
            self._create_message_handler(),
            self._reply_client
        )
        self._message_handler = handler

        # Create and register event handler
        # Note: encrypt_key and verification_token are not required in long connection mode
        # but the SDK requires them to be passed (empty string is fine)
        from src.config import get_config
        config = get_config()

        encrypt_key = getattr(config, 'feishu_encrypt_key', '') or ''
        verification_token = getattr(config, 'feishu_verification_token', '') or ''

        event_handler = lark.EventDispatcherHandler.builder(
            encrypt_key=encrypt_key,
            verification_token=verification_token,
            level=lark.LogLevel.WARNING
        ).register_p2_im_message_receive_v1(
            handler.handle_message
        ).build()

        return event_handler

    def start(self) -> None:
        """
        Start the Stream client (blocking).

        This method blocks the current thread until the client stops.
        """
        logger.info("[Feishu Stream] Starting...")

        # Create event handler
        event_handler = self._create_event_handler()

        # Create WebSocket client
        self._ws_client = ws.Client(
            app_id=self._app_id,
            app_secret=self._app_secret,
            event_handler=event_handler,
            log_level=lark.LogLevel.WARNING,
            auto_reconnect=True
        )

        self._running = True
        logger.info("[Feishu Stream] Client started, waiting for messages...")

        # Start (blocking)
        self._ws_client.start()

    def start_background(self) -> None:
        """
        Start the Stream client in a background thread (non-blocking).

        Suitable for running alongside other services (e.g. WebUI).
        """
        if self._background_thread and self._background_thread.is_alive():
            logger.warning("[Feishu Stream] Client already running")
            return

        self._running = True
        self._background_thread = threading.Thread(
            target=self._run_in_background,
            daemon=True,
            name="FeishuStreamClient"
        )
        self._background_thread.start()
        logger.info("[Feishu Stream] Background client started")

    def _run_in_background(self) -> None:
        """Run in background (handle exceptions and reconnect)"""
        import time

        while self._running:
            try:
                self.start()
            except Exception as e:
                logger.error(f"[Feishu Stream] Runtime error: {e}")
                if self._running:
                    logger.info("[Feishu Stream] Reconnecting in 5 seconds...")
                    time.sleep(5)

    def stop(self) -> None:
        """Stop the client"""
        self._running = False
        if self._message_handler is not None:
            self._message_handler.shutdown(wait=False)
        logger.info("[Feishu Stream] Client stopped")

    @property
    def is_running(self) -> bool:
        """Whether the client is running"""
        return self._running


# Global client instance
_stream_client: Optional[FeishuStreamClient] = None


def get_feishu_stream_client() -> Optional[FeishuStreamClient]:
    """Get global Stream client instance"""
    global _stream_client

    if _stream_client is None and FEISHU_SDK_AVAILABLE:
        try:
            _stream_client = FeishuStreamClient()
        except (ImportError, ValueError) as e:
            logger.warning(f"[Feishu Stream] Failed to create client: {e}")
            return None

    return _stream_client


def start_feishu_stream_background() -> bool:
    """
    Start Feishu Stream client in background.

    Returns:
        Whether startup was successful
    """
    client = get_feishu_stream_client()
    if client:
        client.start_background()
        return True
    return False
