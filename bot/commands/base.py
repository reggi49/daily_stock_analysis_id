# -*- coding: utf-8 -*-
"""
===================================
Command Base Class
===================================

Defines the abstract base class for command handlers. All commands must inherit from this class.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional

from bot.models import BotMessage, BotResponse


class BotCommand(ABC):
    """
    Abstract base class for command handlers.

    All commands must inherit from this class and implement the abstract methods.

    Usage example:
        class MyCommand(BotCommand):
            @property
            def name(self) -> str:
                return "mycommand"

            @property
            def aliases(self) -> List[str]:
                return ["mc", "my command"]

            @property
            def description(self) -> str:
                return "This is my command"

            @property
            def usage(self) -> str:
                return "/mycommand [args]"

            def execute(self, message: BotMessage, args: List[str]) -> BotResponse:
                return BotResponse.text_response("Command executed successfully")
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Command name (without prefix).

        E.g. "analyze" — triggered by user input "/analyze"
        """
        pass

    @property
    @abstractmethod
    def aliases(self) -> List[str]:
        """
        List of command aliases.

        E.g. ["a", "analyze"] — triggered by "/a" or "analyze"
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Command description (used in help information)"""
        pass

    @property
    @abstractmethod
    def usage(self) -> str:
        """
        Usage instructions (used in help information).

        E.g. "/analyze <stock_code>"
        """
        pass

    @property
    def hidden(self) -> bool:
        """
        Whether to hide from the help list.

        Defaults to False; set to True to exclude from /help listing.
        """
        return False

    @property
    def admin_only(self) -> bool:
        """
        Whether admin-only.

        Defaults to False; set to True to require admin privileges.
        """
        return False

    @abstractmethod
    def execute(self, message: BotMessage, args: List[str]) -> BotResponse:
        """
        Execute the command.

        Args:
            message: Original message object
            args: Command argument list (already split)

        Returns:
            BotResponse object
        """
        pass

    async def execute_async(self, message: BotMessage, args: List[str]) -> BotResponse:
        """Asynchronously execute the command.

        By default offloads the synchronous `execute()` to a thread pool
        to avoid blocking the event loop in async dispatch chains.
        """
        return await asyncio.to_thread(self.execute, message, args)

    def validate_args(self, args: List[str]) -> Optional[str]:
        """
        Validate arguments.

        Subclasses can override this method for argument validation.

        Args:
            args: Command argument list

        Returns:
            None if arguments are valid, otherwise an error message
        """
        return None

    def get_help_text(self) -> str:
        """Get help text"""
        return f"**{self.name}** - {self.description}\nUsage: `{self.usage}`"
