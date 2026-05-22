"""APScheduler task scheduler for periodic operations."""
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, get_db
from app.models.settings import Setting

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# Default intervals (in seconds)
DEFAULT_INTERVALS = {
    "sync_playlists": 21600,
    "scan_disk": 43200,
    "search_missing": 1800,
    "monitor_downloads": 300,
    "build_playlists": 900,
    "cleanup_queue": 3600,
}


async def get_interval(db: AsyncSession, key: str) -> int:
    """Get interval from settings, fallback to default."""
    result = await db.execute(select(Setting.value).where(Setting.key == f"interval_{key}"))
    val = result.scalar_one_or_none()
    if val:
        try:
            return int(val)
        except (ValueError, TypeError):
            pass
    return DEFAULT_INTERVALS[key]


async def sync_playlists_job():
    logger.info("Scheduler: sync_playlists started")
    async with async_session() as db:
        from app.models.playlist import Playlist
        from app.routers.playlists import _sync_playlist_tracks

        result = await db.execute(select(Playlist).where(Playlist.enabled == True))
        playlists = result.scalars().all()
        for playlist in playlists:
            try:
                await _sync_playlist_tracks(db, playlist)
            except Exception as e:
                logger.error("Error syncing playlist %s: %s", playlist.id, e)
    logger.info("Scheduler: sync_playlists completed")


async def scan_disk_job():
    logger.info("Scheduler: scan_disk started")
    async with async_session() as db:
        from app.services.scanner import scan_disk
        stats = await scan_disk(db)
        logger.info("Scheduler: scan_disk completed: %s", stats)


async def search_missing_job():
    logger.info("Scheduler: search_missing started")
    async with async_session() as db:
        from app.services.searcher import search_missing_tracks
        stats = await search_missing_tracks(db)
        logger.info("Scheduler: search_missing completed: %s", stats)


async def monitor_downloads_job():
    logger.info("Scheduler: monitor_downloads started")
    async with async_session() as db:
        from app.services.downloader import monitor_downloads
        stats = await monitor_downloads(db)
        logger.info("Scheduler: monitor_downloads completed: %s", stats)


async def build_playlists_job():
    logger.info("Scheduler: build_playlists started")
    async with async_session() as db:
        from app.services.playlist_builder import build_playlists
        stats = await build_playlists(db)
        logger.info("Scheduler: build_playlists completed: %s", stats)


async def cleanup_queue_job():
    logger.info("Scheduler: cleanup_queue started")
    from datetime import datetime, timedelta, timezone
    async with async_session() as db:
        from app.models.download_queue import DownloadQueue
        from sqlalchemy import delete

        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        result = await db.execute(
            delete(DownloadQueue).where(
                DownloadQueue.status == "not_found",
                DownloadQueue.created_at < cutoff,
            )
        )
        deleted = result.rowcount
        logger.info("Scheduler: cleanup_queue completed, deleted %s entries", deleted)


async def setup_scheduler():
    """Initialize and start the scheduler with intervals from DB."""
    intervals = dict(DEFAULT_INTERVALS)
    try:
        async with async_session() as db:
            for key in DEFAULT_INTERVALS:
                intervals[key] = await get_interval(db, key)
    except Exception as e:
        logger.warning("Could not load intervals from DB, using defaults: %s", e)

    jobs = {
        "sync_playlists": (sync_playlists_job, intervals["sync_playlists"]),
        "scan_disk": (scan_disk_job, intervals["scan_disk"]),
        "search_missing": (search_missing_job, intervals["search_missing"]),
        "monitor_downloads": (monitor_downloads_job, intervals["monitor_downloads"]),
        "build_playlists": (build_playlists_job, intervals["build_playlists"]),
        "cleanup_queue": (cleanup_queue_job, intervals["cleanup_queue"]),
    }

    for job_id, (func, interval) in jobs.items():
        scheduler.add_job(
            func,
            trigger=IntervalTrigger(seconds=interval),
            id=job_id,
            replace_existing=True,
            name=f"Job: {job_id}",
        )
        logger.info("Scheduled job '%s' with interval %ss", job_id, interval)

    scheduler.start()
    logger.info("Scheduler started with %d jobs", len(jobs))


async def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


async def reschedule_job(job_id: str, new_interval: int):
    """Reschedule a specific job with a new interval."""
    if job_id not in DEFAULT_INTERVALS:
        logger.warning("Unknown job: %s", job_id)
        return
    scheduler.reschedule_job(
        job_id,
        trigger=IntervalTrigger(seconds=new_interval),
    )
    logger.info("Rescheduled job '%s' to %ss", job_id, new_interval)