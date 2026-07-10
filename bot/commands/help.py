# -*- coding: utf-8 -*-
"""
===================================
Help Command
===================================

Displays available commands and usage instructions.
"""

from typing import List

from bot.commands.base import BotCommand
from bot.models import BotMessage, BotResponse


class HelpCommand(BotCommand):
    """
    Help command.

    Displays the list of all available commands and usage instructions.
    Can also show detailed help for a specific command.

    Usage:
        /help         - Show all commands
        /help analyze - Show detailed help for the analyze command
    """

    @property
    def name(self) -> str:
        return "help"

    @property
    def aliases(self) -> List[str]:
        return ["h", "help", "?"]

    @property
    def description(self) -> str:
        return "Show help information"

    @property
    def usage(self) -> str:
        return "/help [command_name]"

    def execute(self, message: BotMessage, args: List[str]) -> BotResponse:
        """Execute the help command"""
        # Lazy import to avoid circular dependency
        from bot.dispatcher import get_dispatcher

        dispatcher = get_dispatcher()

        # If a command name is specified, show detailed help for that command
        if args:
            cmd_name = args[0]
            command = dispatcher.get_command(cmd_name)

            if command is None:
                return BotResponse.error_response(f"Unknown command: {cmd_name}")

            # Build detailed help
            help_text = self._format_command_help(command, dispatcher.command_prefix)
            return BotResponse.markdown_response(help_text)

        # Show all commands list
        commands = dispatcher.list_commands(include_hidden=False)
        prefix = dispatcher.command_prefix

        help_text = self._format_help_list(commands, prefix)
        return BotResponse.markdown_response(help_text)

    def _format_help_list(self, commands: List[BotCommand], prefix: str) -> str:
        """Format the command list"""
        lines = [
            "📚 **Stock Analysis Assistant - Command Help**",
            "",
            "Available commands:",
            "",
        ]

        for cmd in commands:
            # Command name and aliases
            aliases_str = ""
            if cmd.aliases:
                # Filter out Chinese aliases, show only English aliases
                en_aliases = [a for a in cmd.aliases if a.isascii()]
                if en_aliases:
                    aliases_str = f" ({', '.join(prefix + a for a in en_aliases[:2])})"

            lines.append(f"• {prefix}{cmd.name}{aliases_str} - {cmd.description}")
            lines.append("")

        lines.extend([
            "",
            "---",
            f"💡 Type {prefix}help <command_name> for detailed usage",
            "",
            "**Examples:**",
            "",
            f"• {prefix}analyze 301023 - Yifan Transmission",
            "",
            f"• {prefix}market - View market review",
            "",
            f"• {prefix}batch - Batch analyze watchlist stocks",
        ])

        return "\n".join(lines)

    def _format_command_help(self, command: BotCommand, prefix: str) -> str:
        """Format detailed help for a single command"""
        lines = [
            f"📖 **{prefix}{command.name}** - {command.description}",
            "",
            f"**Usage:** `{command.usage}`",
            "",
        ]

        # Aliases
        if command.aliases:
            aliases = [f"`{prefix}{a}`" if a.isascii() else f"`{a}`" for a in command.aliases]
            lines.append(f"**Aliases:** {', '.join(aliases)}")
            lines.append("")

        # Permissions
        if command.admin_only:
            lines.append("⚠️ **Requires admin privileges**")
            lines.append("")

        return "\n".join(lines)
