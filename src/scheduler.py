# -*- coding: utf-8 -*-
"""
===================================
Handle signals gracefully
===================================

Handle signals gracefully:
1. Handle signals gracefully
2. Handle signals gracefully
3. Handle signals gracefully, ensure reliable exit

Lightweight scheduled task library:
- schedule: Lightweight scheduled task library
"""

import logging
import re
import signal
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

logger = logging.getLogger(__name__)


def normalize_schedule_times(
    schedule_times: Optional[Union[Sequence[str], str]],
    *,
    fallback_time: str = "18:00",
) -> List[str]:
    """Return sorted unique HH:MM schedule times with SCHEDULE_TIME fallback."""
    if isinstance(schedule_times, str):
        raw_items = [item.strip() for item in schedule_times.split(",")]
    elif schedule_times is None:
        raw_items = []
    else:
        raw_items = [str(item).strip() for item in schedule_times]

    valid = {
        item
        for item in raw_items
        if item and re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", item)
    }
    if not valid:
        fallback = (fallback_time or "18:00").strip() or "18:00"
        valid.add(fallback if re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", fallback) else "18:00")
    return sorted(valid)


class GracefulShutdown:
    """
    Exit the handler gracefully

    capture SIGTERM/SIGINT Signal，Make sure the task is completed before exiting
    """

    def __init__(self, register_signals: bool = True):
        self.shutdown_requested = False
        self._lock = threading.Lock()
        if not register_signals:
            return

        # Handle signals gracefully
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """signal processing function"""
        with self._lock:
            if not self.shutdown_requested:
                logger.info(f"Exit signal received ({signum}), waiting for current task to complete...")
                self.shutdown_requested = True

    @property
    def should_shutdown(self) -> bool:
        """Check if it should exit"""
        with self._lock:
            return self.shutdown_requested


class Scheduler:
    """
    Scheduler of scheduled tasks

    based on schedule Library implementation，support：
    - Daily scheduled execution
    - Execute immediately on startup
    - Exit gracefully
    """

    def __init__(
        self,
        schedule_time: str = "18:00",
        schedule_time_provider: Optional[Callable[[], str]] = None,
        schedule_times: Optional[Sequence[str]] = None,
        schedule_times_provider: Optional[Callable[[], Union[Sequence[str], str]]] = None,
        register_signals: bool = True,
    ):
        """
        Initialize scheduler

        Args:
            schedule_time: Daily execution time，Format "HH:MM"
        """
        try:
            import schedule
            self.schedule = schedule
        except ImportError:
            logger.error("schedule Library not installed，Please execute: pip install schedule")
            raise ImportError("Please install schedule Library: pip install schedule")

        self.schedule_time = schedule_time
        self.schedule_times = (
            normalize_schedule_times(schedule_times, fallback_time=schedule_time)
            if schedule_times is not None
            else [(schedule_time or "").strip()]
        )
        self._schedule_time_provider = schedule_time_provider
        self._schedule_times_provider = schedule_times_provider
        self.shutdown_handler = GracefulShutdown(register_signals=register_signals)
        self._task_callback: Optional[Callable] = None
        self._daily_job: Optional[Any] = None
        self._daily_jobs: List[Any] = []
        self._background_tasks: List[Dict[str, Any]] = []
        self._running = False

    def set_daily_task(self, task: Callable, run_immediately: bool = True):
        """
        Set daily scheduled tasks

        Args:
            task: no parameters（no parameters）
            run_immediately: Whether to execute once immediately after setting
        """
        self._task_callback = task
        if not self._configure_daily_tasks(self.schedule_times):
            raise ValueError(f"Invalid scheduled execution time: {self.schedule_time!r}")

        if run_immediately:
            logger.info("Execute a task immediately...")
            self._safe_run_task()

    @staticmethod
    def _is_valid_schedule_time(schedule_time: str) -> bool:
        """Validate time string in HH:MM 24-hour format."""
        candidate = (schedule_time or "").strip()
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", candidate):
            return False
        return True

    def _cancel_daily_job(self) -> None:
        """Remove the currently registered daily job if one exists."""
        if self._daily_job is None and not self._daily_jobs:
            return

        for job in list(self._daily_jobs or [self._daily_job]):
            if job is None:
                continue
            if hasattr(self.schedule, "cancel_job"):
                self.schedule.cancel_job(job)
            else:  # pragma: no cover - compatibility fallback
                jobs = getattr(self.schedule, "jobs", None)
                if isinstance(jobs, list) and job in jobs:
                    jobs.remove(job)

        self._daily_job = None
        self._daily_jobs = []

    def _configure_daily_task(self, schedule_time: str) -> bool:
        """(Re)register the daily job at the requested time."""
        candidate = (schedule_time or "").strip()
        if not self._is_valid_schedule_time(candidate):
            logger.warning(
                "Invalid scheduled execution time detected %r, daily scheduled tasks have been set %s",
                schedule_time,
                self.schedule_time,
            )
            return False

        previous_time = self.schedule_time
        self._cancel_daily_job()
        self._daily_job = self.schedule.every().day.at(candidate).do(self._safe_run_task)
        self.schedule_time = candidate

        if previous_time == candidate:
            logger.info("Daily scheduled tasks have been set, execution time: %s", self.schedule_time)
        else:
            logger.info(
                "Detected SCHEDULE_TIME change, daily scheduled tasks have been updated from %s to %s",
                previous_time,
                self.schedule_time,
            )
        return True

    def _refresh_daily_schedule_if_needed(self) -> None:
        """Reload daily schedule time from the latest runtime config if needed."""
        if self._task_callback is None or self._schedule_time_provider is None:
            return

        try:
            latest_schedule_time = (self._schedule_time_provider() or "").strip()
        except Exception as exc:  # pragma: no cover - defensive branch
            logger.warning("Failed to read latest SCHEDULE_TIME, continuing to use %s: %s", self.schedule_time, exc)
            return

        if not latest_schedule_time or latest_schedule_time == self.schedule_time:
            return

        if self._configure_daily_task(latest_schedule_time):
            logger.info("The updated next execution time: %s", self._get_next_run_time())

    def _configure_daily_tasks(self, schedule_times: Union[Sequence[str], str]) -> bool:
        """(Re)register daily jobs at the requested times."""
        raw_items = (
            [item.strip() for item in schedule_times.split(",")]
            if isinstance(schedule_times, str)
            else [str(item).strip() for item in schedule_times]
        )
        invalid_items = [item for item in raw_items if item and not self._is_valid_schedule_time(item)]
        if invalid_items:
            logger.warning(
                "Invalid schedule time values %r; keeping current times %s",
                invalid_items,
                ",".join(self.schedule_times),
            )
            return False

        candidates = normalize_schedule_times(raw_items, fallback_time=self.schedule_time)
        previous_times = list(self.schedule_times)
        self._cancel_daily_job()
        self._daily_jobs = [
            self.schedule.every().day.at(candidate).do(self._safe_run_task)
            for candidate in candidates
        ]
        self._daily_job = self._daily_jobs[0] if self._daily_jobs else None
        self.schedule_times = candidates
        self.schedule_time = candidates[0] if candidates else "18:00"

        if previous_times == candidates:
            logger.info("Daily scheduled jobs configured at: %s", ",".join(self.schedule_times))
        else:
            logger.info(
                "Schedule times changed from %s to %s",
                ",".join(previous_times),
                ",".join(self.schedule_times),
            )
        return True

    def _refresh_daily_schedule_if_needed(self) -> None:
        """Reload daily schedule times from the latest runtime config if needed."""
        if self._task_callback is None:
            return

        try:
            if self._schedule_times_provider is not None:
                latest_schedule_times = self._schedule_times_provider()
            elif self._schedule_time_provider is not None:
                latest_schedule_times = [(self._schedule_time_provider() or "").strip()]
            else:
                return
        except Exception as exc:  # pragma: no cover - defensive branch
            logger.warning(
                "Failed to read latest schedule times; keeping %s: %s",
                ",".join(self.schedule_times),
                exc,
            )
            return

        latest = normalize_schedule_times(latest_schedule_times, fallback_time=self.schedule_time)
        if latest == self.schedule_times:
            return

        if self._configure_daily_tasks(latest):
            logger.info("Schedule refreshed; next run: %s", self._get_next_run_time())

    def refresh_daily_schedule_if_needed(self) -> None:
        """Public wrapper for runtime scheduler reconciliation."""
        self._refresh_daily_schedule_if_needed()

    def _safe_run_task(self):
        """Perform tasks safely（With exception catching）"""
        if self._task_callback is None:
            return

        try:
            logger.info("=" * 50)
            logger.info(f"Scheduled task starts execution - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 50)

            self._task_callback()

            logger.info(f"Scheduled task execution completed - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        except Exception as e:
            logger.exception(f"Scheduled task execution failed: {e}")

    def add_background_task(
        self,
        task: Callable,
        interval_seconds: int,
        run_immediately: bool = False,
        name: Optional[str] = None,
    ) -> None:
        """Register a periodic background task executed inside the scheduler loop.

        Note: The scheduler loop polls every 30 seconds, so *interval_seconds*
        below 30 will be clamped to 30 to avoid promising unreachable precision.
        """
        clamped_interval = max(30, int(interval_seconds))
        if int(interval_seconds) < 30:
            logger.warning(
                "Background task %s requested interval %ds, but scheduler loop polls every 30s; automatically adjusted to 30s",
                name or getattr(task, "__name__", "background_task"),
                interval_seconds,
            )
        entry = {
            "task": task,
            "interval_seconds": clamped_interval,
            "last_run": 0.0,
            "name": name or getattr(task, "__name__", "background_task"),
            "thread": None,
            "running": False,
        }
        if not run_immediately:
            entry["last_run"] = time.time()
        self._background_tasks.append(entry)
        logger.info(
            "Registered background task: %s (interval %s seconds, execute immediately=%s)",
            entry["name"],
            entry["interval_seconds"],
            run_immediately,
        )
        if run_immediately:
            self._start_background_task(entry)

    def _start_background_task(self, entry: Dict[str, Any]) -> bool:
        """Start one background task in a dedicated daemon thread."""
        worker = entry.get("thread")
        if worker is not None and worker.is_alive():
            return False

        def _runner() -> None:
            try:
                logger.info("Background task starts execution: %s", entry["name"])
                entry["task"]()
            except Exception as exc:
                logger.exception("Background task execution failed [%s]: %s", entry["name"], exc)
            finally:
                entry["running"] = False
                entry["thread"] = None

        entry["last_run"] = time.time()
        entry["running"] = True
        worker = threading.Thread(
            target=_runner,
            daemon=True,
            name=f"scheduler-bg-{entry['name']}",
        )
        entry["thread"] = worker
        worker.start()
        return True

    def _run_background_tasks(self) -> None:
        """Execute any background tasks whose interval has elapsed."""
        if not self._background_tasks:
            return

        now = time.time()
        for entry in self._background_tasks:
            worker = entry.get("thread")
            if worker is not None and worker.is_alive():
                continue
            if entry.get("running"):
                entry["running"] = False
                entry["thread"] = None
            if now - entry["last_run"] < entry["interval_seconds"]:
                continue
            self._start_background_task(entry)

    def run(self):
        """
        Run scheduler main loop

        blocking run, until exit signal is received
        """
        self._running = True
        logger.info("The scheduler starts running...")
        logger.info(f"Next execution time: {self._get_next_run_time()}")

        while self._running and not self.shutdown_handler.should_shutdown:
            self._refresh_daily_schedule_if_needed()
            self.schedule.run_pending()
            self._run_background_tasks()
            time.sleep(30)  # Check every 30 seconds

            # Handle signals gracefully
            if datetime.now().minute == 0 and datetime.now().second < 30:
                logger.info(f"Scheduler is running... Execute next time: {self._get_next_run_time()}")

        logger.info("Scheduler has stopped")

    def _get_next_run_time(self) -> str:
        """Get the next execution time"""
        jobs = self.schedule.get_jobs()
        if jobs:
            next_run = min(job.next_run for job in jobs)
            return next_run.strftime('%Y-%m-%d %H:%M:%S')
        return "Not set"

    def stop(self):
        """Convenience function"""
        self._running = False
        self._cancel_daily_job()


def run_with_schedule(
    task: Callable,
    schedule_time: str = "18:00",
    run_immediately: bool = True,
    background_tasks: Optional[List[Dict[str, Any]]] = None,
    schedule_time_provider: Optional[Callable[[], str]] = None,
    schedule_times: Optional[Sequence[str]] = None,
    schedule_times_provider: Optional[Callable[[], Union[Sequence[str], str]]] = None,
):
    """
    Convenience function：Run tasks using scheduled schedules

    Args:
        task: no parameters
        schedule_time: Daily execution time
        run_immediately: Whether to execute it immediately
        background_tasks: Optional list of background task definitions。Each item is a dictionary，
            Need to include `task` and `interval_seconds`，Optional include `name`
            and `run_immediately`。`interval_seconds` Unit is seconds。
        schedule_time_provider: Optional time provider；The scheduler will read before each round of checking，
            Automatically rebuild when return value changes daily job。
    """
    scheduler_kwargs: Dict[str, Any] = {
        "schedule_time": schedule_time,
        "schedule_time_provider": schedule_time_provider,
    }
    if schedule_times is not None:
        scheduler_kwargs["schedule_times"] = schedule_times
    if schedule_times_provider is not None:
        scheduler_kwargs["schedule_times_provider"] = schedule_times_provider
    scheduler = Scheduler(**scheduler_kwargs)
    for entry in background_tasks or []:
        scheduler.add_background_task(
            task=entry["task"],
            interval_seconds=entry["interval_seconds"],
            run_immediately=entry.get("run_immediately", False),
            name=entry.get("name"),
        )
    scheduler.set_daily_task(task, run_immediately=run_immediately)
    scheduler.run()


if __name__ == "__main__":
    # Handle signals gracefully
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    )

    def test_task():
        print(f"Task in progress... {datetime.now()}")
        time.sleep(2)
        print("Mission accomplished!")

    print("Starting test scheduler (press Ctrl+C to quit)")
    run_with_schedule(test_task, schedule_time="23:59", run_immediately=True)
