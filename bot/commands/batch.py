# -*- coding: utf-8 -*-
"""
===================================
Batch Analysis Command
===================================

Batch analyze all stocks in the watchlist.
"""

import logging
import threading
import uuid
from typing import List

from bot.commands.base import BotCommand
from bot.models import BotMessage, BotResponse

logger = logging.getLogger(__name__)


class BatchCommand(BotCommand):
    """
    Batch analysis command.

    Batch analyze the watchlist stocks from configuration, generate a summary report.

    Usage:
        /batch      - Analyze all watchlist stocks
        /batch 3    - Analyze only the first 3
    """

    @property
    def name(self) -> str:
        return "batch"

    @property
    def aliases(self) -> List[str]:
        return ["b", "batch", "all"]

    @property
    def description(self) -> str:
        return "Batch analyze watchlist stocks"

    @property
    def usage(self) -> str:
        return "/batch [count]"

    @property
    def admin_only(self) -> bool:
        """Batch analysis requires admin privileges (to prevent abuse)"""
        return False  # Can be set to True as needed

    def execute(self, message: BotMessage, args: List[str]) -> BotResponse:
        """Execute the batch analysis command"""
        from src.config import get_config

        config = get_config()
        config.refresh_stock_list()

        stock_list = config.stock_list

        if not stock_list:
            return BotResponse.error_response(
                "Watchlist is empty, please configure STOCK_LIST first"
            )

        # Parse count argument
        limit = None
        if args:
            try:
                limit = int(args[0])
                if limit <= 0:
                    return BotResponse.error_response("Count must be greater than 0")
            except ValueError:
                return BotResponse.error_response(f"Invalid count: {args[0]}")

        # Limit analysis count
        if limit:
            stock_list = stock_list[:limit]

        logger.info(f"[BatchCommand] Starting batch analysis of {len(stock_list)} stocks")

        # Run analysis in a background thread
        thread = threading.Thread(
            target=self._run_batch_analysis,
            args=(stock_list, message),
            daemon=True
        )
        thread.start()

        return BotResponse.markdown_response(
            f"✅ **Batch analysis task started**\n\n"
            f"• Analysis count: {len(stock_list)} stocks\n"
            f"• Stock list: {', '.join(stock_list[:5])}"
            f"{'...' if len(stock_list) > 5 else ''}\n\n"
            f"Summary report will be pushed automatically upon completion."
        )

    def _run_batch_analysis(self, stock_list: List[str], message: BotMessage) -> None:
        """Run batch analysis in background"""
        try:
            from src.config import get_config
            from main import StockAnalysisPipeline

            config = get_config()

            # Create analysis pipeline
            pipeline = StockAnalysisPipeline(
                config=config,
                source_message=message,
                query_id=uuid.uuid4().hex,
                query_source="bot"
            )

            # Run analysis (auto-pushes summary report)
            results = pipeline.run(
                stock_codes=stock_list,
                dry_run=False,
                send_notification=True
            )

            logger.info(f"[BatchCommand] Batch analysis completed, {len(results)} stocks succeeded")

        except Exception as e:
            logger.error(f"[BatchCommand] Batch analysis failed: {e}")
            logger.exception(e)
