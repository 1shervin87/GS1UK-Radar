from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .analysis.pipeline import run_weekly_digest
from .config import Settings

log = logging.getLogger(__name__)

JOB_ID = "weekly-regulatory-digest"


class DigestScheduler:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.scheduler = AsyncIOScheduler(timezone=settings.schedule_timezone)
        self._task: asyncio.Task | None = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def next_run(self) -> datetime | None:
        job = self.scheduler.get_job(JOB_ID) if self.scheduler.running else None
        return job.next_run_time if job else None

    @property
    def cron_description(self) -> str:
        s = self.settings
        return f"{s.schedule_day_of_week} {s.schedule_hour:02d}:{s.schedule_minute:02d} ({s.schedule_timezone})"

    def start(self) -> None:
        if self.settings.schedule_enabled:
            self.scheduler.add_job(
                self._scheduled,
                CronTrigger(
                    day_of_week=self.settings.schedule_day_of_week,
                    hour=self.settings.schedule_hour,
                    minute=self.settings.schedule_minute,
                    timezone=self.settings.schedule_timezone,
                ),
                id=JOB_ID,
                replace_existing=True,
                misfire_grace_time=6 * 3600,  # still run if the server was down at 08:00
                coalesce=True,
            )
        self.scheduler.start()
        log.info("scheduler started; weekly digest at %s; next run %s", self.cron_description, self.next_run)
        if self.settings.run_on_startup:
            self.trigger("startup")

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    async def _scheduled(self) -> None:
        self.trigger("schedule")

    def trigger(self, trigger: str, lookback_days: int | None = None) -> bool:
        """Kick off a run in the background. Returns False if one is already running."""
        if self.running:
            return False
        settings = self.settings
        if lookback_days:
            settings = settings.model_copy(update={"lookback_days": lookback_days})

        async def _job():
            try:
                await run_weekly_digest(settings, trigger=trigger)
            except Exception:  # noqa: BLE001 - already logged/persisted by the pipeline
                pass

        self._task = asyncio.get_event_loop().create_task(_job())
        return True
