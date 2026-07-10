# -*- coding: utf-8 -*-
"""
Pushover notification sender service.

Responsibilities:
1. Send messages via the Pushover API
"""
import logging
from typing import Optional
from datetime import datetime
import requests

from src.config import Config
from src.formatters import markdown_to_plain_text


logger = logging.getLogger(__name__)


class PushoverSender:
    
    def __init__(self, config: Config):
        """
        Initialize Pushover configuration.

        Args:
            config: Configuration object
        """
        self._pushover_config = {
            'user_key': getattr(config, 'pushover_user_key', None),
            'api_token': getattr(config, 'pushover_api_token', None),
        }
        
    def _is_pushover_configured(self) -> bool:
        """Check whether Pushover configuration is complete."""
        return bool(self._pushover_config['user_key'] and self._pushover_config['api_token'])

    def send_to_pushover(
        self,
        content: str,
        title: Optional[str] = None,
        *,
        timeout_seconds: Optional[float] = None,
    ) -> bool:
        """
        Push a message to Pushover.

        Pushover API format:
        POST https://api.pushover.net/1/messages.json
        {
            "token": "App API Token",
            "user": "User Key",
            "message": "Message content",
            "title": "Title (optional)"
        }

        Pushover features:
        - Multi-platform push: iOS / Android / Desktop
        - Message limit: 1024 characters
        - Priority settings supported
        - HTML format supported

        Args:
            content: Message content (Markdown format, converted to plain text)
            title: Message title (optional, defaults to "Stock Analysis Report")

        Returns:
            Whether the send succeeded
        """
        if not self._is_pushover_configured():
            logger.warning("Pushover configuration incomplete, skipping push")
            return False
        
        user_key = self._pushover_config['user_key']
        api_token = self._pushover_config['api_token']
        
        # Pushover API endpoint
        api_url = "https://api.pushover.net/1/messages.json"
        
        # Handle message title
        if title is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
            title = f"📈 Stock Analysis Report - {date_str}"
        
        # Pushover message limit: 1024 characters
        max_length = 1024
        
        # Convert Markdown to plain text (Pushover supports HTML, but plain text is more universal)
        plain_content = markdown_to_plain_text(content)
        
        if len(plain_content) <= max_length:
            # Single message send
            return self._send_pushover_message(api_url, user_key, api_token, plain_content, title, timeout_seconds=timeout_seconds)
        else:
            # Chunked send for long messages
            return self._send_pushover_chunked(
                api_url,
                user_key,
                api_token,
                plain_content,
                title,
                max_length,
                timeout_seconds=timeout_seconds,
            )
      
    def _send_pushover_message(
        self, 
        api_url: str, 
        user_key: str, 
        api_token: str, 
        message: str, 
        title: str,
        priority: int = 0,
        *,
        timeout_seconds: Optional[float] = None,
    ) -> bool:
        """
        Send a single Pushover message.

        Args:
            api_url: Pushover API endpoint
            user_key: User Key
            api_token: App API Token
            message: Message content
            title: Message title
            priority: Priority (-2 to 2, default 0)
        """
        try:
            payload = {
                "token": api_token,
                "user": user_key,
                "message": message,
                "title": title,
                "priority": priority,
            }
            
            response = requests.post(api_url, data=payload, timeout=timeout_seconds or 30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 1:
                    logger.info("Pushover message sent successfully")
                    return True
                else:
                    errors = result.get('errors', ['Unknown error'])
                    logger.error(f"Pushover returned error: {errors}")
                    return False
            else:
                logger.error(f"Pushover request failed: HTTP {response.status_code}")
                logger.debug(f"Response content: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send Pushover message: {e}")
            return False
    
    def _send_pushover_chunked(
        self, 
        api_url: str, 
        user_key: str, 
        api_token: str, 
        content: str, 
        title: str,
        max_length: int,
        *,
        timeout_seconds: Optional[float] = None,
    ) -> bool:
        """
        Send long Pushover messages in chunks.

        Splits by section separators to ensure each chunk stays within the limit.
        """
        import time
        
        # Split by section separators (horizontal rule or double newline)
        if "────────" in content:
            sections = content.split("────────")
            separator = "────────"
        else:
            sections = content.split("\n\n")
            separator = "\n\n"
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for section in sections:
            # Calculate the actual length after adding this section.
            # join() places separators between elements, not after each one.
            # So: the first element needs no separator, subsequent elements need one separator.
            if current_chunk:
                # Already has elements; adding a new element costs: current length + separator + new section
                new_length = current_length + len(separator) + len(section)
            else:
                # First element, no separator needed
                new_length = len(section)
            
            if new_length > max_length:
                if current_chunk:
                    chunks.append(separator.join(current_chunk))
                current_chunk = [section]
                current_length = len(section)
            else:
                current_chunk.append(section)
                current_length = new_length
        
        if current_chunk:
            chunks.append(separator.join(current_chunk))
        
        total_chunks = len(chunks)
        success_count = 0
        
        logger.info(f"Pushover chunked send: {total_chunks} chunks total")
        
        for i, chunk in enumerate(chunks):
            # Add page marker to title
            chunk_title = f"{title} ({i+1}/{total_chunks})" if total_chunks > 1 else title
            
            if self._send_pushover_message(
                api_url,
                user_key,
                api_token,
                chunk,
                chunk_title,
                timeout_seconds=timeout_seconds,
            ):
                success_count += 1
                logger.info(f"Pushover chunk {i+1}/{total_chunks} sent successfully")
            else:
                logger.error(f"Pushover chunk {i+1}/{total_chunks} failed")
            
            # Interval between chunks to avoid rate limiting
            if i < total_chunks - 1:
                time.sleep(1)

        return success_count == total_chunks
