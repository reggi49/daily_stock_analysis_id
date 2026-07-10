# -*- coding: utf-8 -*-
"""
===================================
Market Review Command
===================================

Runs market review analysis and generates a market overview report.
"""

import logging
import threading
from typing import Any, List, Optional

from bot.commands.base import BotCommand
from bot.models import BotMessage, BotResponse

logger = logging.getLogger(__name__)


class MarketCommand(BotCommand):
    """
    Market Review command.

    Runs market review analysis, including:
    - Major index performance
    - Sector hotspots
    - Market sentiment
    - Outlook

    Usage:
        /market - Run market review
    """

    @property
    def name(self) -> str:
        return "market"

    @property
    def aliases(self) -> List[str]:
        return ["m", "market", "review", "quote"]

    @property
    def description(self) -> str:
        return "Market review analysis"

    @property
    def usage(self) -> str:
        return "/market"

    def execute(self, message: BotMessage, args: List[str]) -> BotResponse:
        """Execute the market review command"""
        config = self._get_config()
        lock_token = self._try_acquire_market_review_lock(config)
        if lock_token is None:
            return BotResponse.markdown_response("⚠️ Market review is already running, please try again later.")

        thread = threading.Thread(
            target=self._run_market_review,
            args=(message, config, lock_token),
            daemon=True,
        )
        try:
            thread.start()
        except Exception as exc:
            logger.error(
                "[MarketCommand] Failed to start market review background thread: %s",
                exc,
            )
            self._release_market_review_lock(lock_token)
            return BotResponse.error_response(
                "Market review failed to start, lock released; please try again later"
            )

        return BotResponse.markdown_response(
            "✅ **Market review task started**\n\n"
            "Analyzing:\n"
            "• Major index performance\n"
            "• Sector hotspot analysis\n"
            "• Market sentiment assessment\n"
            "• Outlook\n\n"
            "Results will be pushed automatically upon completion."
        )

    def _get_config(self):
        from src.config import get_config
        return get_config()

    def _try_acquire_market_review_lock(self, config):
        from src.core.market_review_lock import try_acquire_market_review_lock
        return try_acquire_market_review_lock(config)

    def _release_market_review_lock(self, lock_token: Optional[Any]) -> None:
        from src.core.market_review_lock import release_market_review_lock
        release_market_review_lock(lock_token)

    def _compute_market_review_override_region(self, config) -> Optional[str]:
        if not getattr(config, "trading_day_check_enabled", True):
            return None

        try:
            from src.core.trading_calendar import (
                get_open_markets_today,
                compute_effective_region,
            )

            open_markets = get_open_markets_today()
            return compute_effective_region(
                getattr(config, "market_review_region", "cn") or "cn",
                open_markets,
            )
        except Exception as exc:
            logger.warning("Trading day filter failed, continuing market review per config: %s", exc)
            return None

    def _run_market_review(
        self,
        message: BotMessage,
        config,
        lock_token: Optional[Any],
    ) -> None:
        """Run market review in background"""
        try:
            override_region = self._compute_market_review_override_region(config)
            if override_region == "":
                from src.notification import NotificationService
                notifier = NotificationService(source_message=message)
                logger.info("[MarketCommand] Related markets closed today, skipping market review")
                if notifier.is_available():
                    notifier.send(
                        "🎯 Market Review\n\nRelated markets closed today, market review skipped.",
                        email_send_to_all=True,
                        route_type="report",
                    )
                return

            from src.core.market_review_runtime import build_market_review_runtime
            from src.core.market_review import run_market_review

            notifier, analyzer, search_service = build_market_review_runtime(
                config,
                source_message=message,
            )
            review_report = run_market_review(
                notifier=notifier,
                analyzer=analyzer,
                search_service=search_service,
                send_notification=True,
                override_region=override_region,
                trigger_source="bot",
            )
            if review_report:
                logger.info("[MarketCommand] Market review completed and pushed")
            else:
                logger.warning("[MarketCommand] Market review returned empty result")
        except Exception as e:
            logger.error("[MarketCommand] Market review failed: %s", e)
            logger.exception(e)
        finally:
            self._release_market_review_lock(lock_token)
