# -*- coding: utf-8 -*-
"""
===================================
Stock Analysis Command
===================================

Analyzes a specified stock and calls AI to generate an analysis report.
"""

import re
import logging
from typing import List, Optional

from bot.commands.base import BotCommand
from bot.models import BotMessage, BotResponse
from src.services.stock_code_utils import resolve_index_stock_code_for_analysis

logger = logging.getLogger(__name__)


class AnalyzeCommand(BotCommand):
    """
    Stock analysis command.

    Analyzes a specified stock code, generates an AI analysis report and pushes it.

    Usage:
        /analyze 600519       - Analyze Kweichow Moutai (concise report)
        /analyze 600519 full  - Analyze and generate a full report
    """

    @property
    def name(self) -> str:
        return "analyze"

    @property
    def aliases(self) -> List[str]:
        return ["a", "analyze", "check"]

    @property
    def description(self) -> str:
        return "Analyze a specific stock"

    @property
    def usage(self) -> str:
        return "/analyze <stock_code> [full]"

    def validate_args(self, args: List[str]) -> Optional[str]:
        """Validate arguments"""
        if not args:
            return "Please enter a stock code"

        code = args[0].upper()

        # Validate stock code format
        # A-share: 6-digit number
        # HK: HK + 5-digit number
        # US: 1-5 uppercase letters + . + 2 suffix letters
        is_a_stock = re.match(r'^\d{6}$', code)
        is_hk_stock = re.match(r'^HK\d{5}$', code)
        is_us_stock = re.match(r'^[A-Z]{1,5}(\.[A-Z]{1,2})?$', code)

        if not (is_a_stock or is_hk_stock or is_us_stock):
            return f"Invalid stock code: {code} (A-share: 6 digits / HK: HK+5 digits / US: 1-5 letters)"

        return None

    def execute(self, message: BotMessage, args: List[str]) -> BotResponse:
        """Execute the analysis command"""
        code = resolve_index_stock_code_for_analysis(args[0])

        # Check if full report is needed (default concise, pass full/detailed/complete to switch)
        report_type = "simple"
        if len(args) > 1 and args[1].lower() in ["full", "detailed", "complete"]:
            report_type = "full"
        logger.info(f"[AnalyzeCommand] Analyzing stock: {code}, report type: {report_type}")

        try:
            # Call analysis service
            from src.services.task_service import get_task_service
            from src.enums import ReportType

            service = get_task_service()

            # Submit async analysis task
            result = service.submit_analysis(
                code=code,
                report_type=ReportType.from_str(report_type),
                source_message=message
            )

            if result.get("success"):
                task_id = result.get("task_id", "")
                return BotResponse.markdown_response(
                    f"✅ **Analysis task submitted**\n\n"
                    f"• Stock code: `{code}`\n"
                    f"• Report type: {ReportType.from_str(report_type).display_name}\n"
                    f"• Task ID: `{task_id[:20]}...`\n\n"
                    f"Results will be pushed automatically upon completion."
                )
            else:
                error = result.get("error", "Unknown error")
                return BotResponse.error_response(f"Failed to submit analysis task: {error}")

        except Exception as e:
            logger.error(f"[AnalyzeCommand] Execution failed: {e}")
            return BotResponse.error_response(f"Analysis failed: {str(e)[:100]}")
