"""Dashboard statistics endpoint."""
import logging
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.database import get_db
from app.models.playlist import Playlist
from app.models.local_track import LocalTrack
from app.models.download_queue import DownloadQueue
from app.schemas.stats import StatsResponse
from app.config import config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    # Playlist counts
    playlist_result = await db.execute(select(func.count(Playlist.id)))
    total_playlists = playlist_result.scalar() or 0

    # Track counts
    track_count_result = await db.execute(select(func.coalesce(func.sum(Playlist.track_count), 0)))
    total_tracks_spotify = track_count_result.scalar() or 0

    download_count_result = await db.execute(select(func.coalesce(func.sum(Playlist.downloaded_count), 0)))
    total_tracks_downloaded = download_count_result.scalar() or 0

    # Download queue stats
    active_result = await db.execute(
        select(func.count(DownloadQueue.id)).where(DownloadQueue.status.in_(["queued", "downloading"]))
    )
    active_downloads = active_result.scalar() or 0

    pending_result = await db.execute(
        select(func.count(DownloadQueue.id)).where(DownloadQueue.status == "pending")
    )
    pending_downloads = pending_result.scalar() or 0

    failed_result = await db.execute(
        select(func.count(DownloadQueue.id)).where(DownloadQueue.status == "failed")
    )
    failed_downloads = failed_result.scalar() or 0

    # Local tracks
    local_result = await db.execute(select(func.count(LocalTrack.id)))
    local_tracks = local_result.scalar() or 0

    # Disk usage
    music_path = Path(config.music_path)
    disk_usage = 0
    if music_path.exists():
        try:
            disk_usage = sum(f.stat().st_size for f in music_path.rglob("*") if f.is_file())
        except Exception:
            pass

    return StatsResponse(
        total_playlists=total_playlists,
        total_tracks_spotify=total_tracks_spotify,
        total_tracks_downloaded=total_tracks_downloaded,
        active_downloads=active_downloads,
        pending_downloads=pending_downloads,
        failed_downloads=failed_downloads,
        local_tracks=local_tracks,
        disk_usage_bytes=disk_usage,
    )