"""Simple scheduler for daily pipeline execution.

Uses APScheduler for lightweight scheduling without Celery overhead.
Can also be triggered manually via API.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.tasks.daily_pipeline import run_daily_pipeline

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def setup_scheduler():
    """Configure and start the daily scheduler.

    Runs pipeline every day at 6:00 AM EST (prime time for US morning content).
    """
    scheduler.add_job(
        run_daily_pipeline,
        trigger=CronTrigger(hour=6, minute=0, timezone="US/Eastern"),
        id="daily_pipeline",
        name="Daily Video Generation Pipeline",
        replace_existing=True,
        kwargs={"max_videos": 100, "concurrency": 3},
    )
    scheduler.start()
    logger.info("Scheduler started: daily pipeline at 6:00 AM EST")


def shutdown_scheduler():
    """Gracefully shutdown the scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
