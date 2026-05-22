"""Disk scanner service — walks /music directory and maintains local_tracks table."""
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.models.local_track import LocalTrack
from app.utils.audio import extract_metadata_mutagen, compute_checksum, is_lossless

logger = logging.getLogger(__name__)


async def scan_disk(db: AsyncSession) -> dict:
    """Walk the music directory and upsert local_tracks entries.
    Returns scan stats.
    """
    music_path = Path(config.music_path)
    if not music_path.exists():
        logger.warning("Music path does not exist: %s", music_path)
        return {"added": 0, "updated": 0, "removed": 0, "total": 0}

    scan_start = datetime.now(timezone.utc)
    scanned_paths = set()
    added = 0
    updated = 0

    # Recursive walk
    for file_path in music_path.rglob("*"):
        if not file_path.is_file():
            continue
        if not is_lossless(file_path):
            continue

        scanned_paths.add(str(file_path.resolve()))

        metadata = extract_metadata_mutagen(file_path)
        checksum = compute_checksum(file_path)
        file_size = file_path.stat().st_size

        # Check if already in DB
        existing = await db.execute(
            select(LocalTrack).where(LocalTrack.file_path == str(file_path.resolve()))
        )
        existing_track = existing.scalar_one_or_none()

        if existing_track:
            # Update metadata if changed
            existing_track.artist = metadata.get("artist") or existing_track.artist
            existing_track.album = metadata.get("album") or existing_track.album
            existing_track.title = metadata.get("title") or existing_track.title
            existing_track.track_number = metadata.get("track_number") or existing_track.track_number
            existing_track.duration_ms = metadata.get("duration_ms") or existing_track.duration_ms
            existing_track.format = metadata.get("format") or existing_track.format
            existing_track.file_size = file_size or existing_track.file_size
            existing_track.checksum = checksum or existing_track.checksum
            existing_track.last_seen = scan_start
            updated += 1
        else:
            new_track = LocalTrack(
                file_path=str(file_path.resolve()),
                artist=metadata.get("artist"),
                album=metadata.get("album"),
                title=metadata.get("title"),
                track_number=metadata.get("track_number"),
                duration_ms=metadata.get("duration_ms"),
                format=metadata.get("format"),
                file_size=file_size,
                checksum=checksum,
                last_seen=scan_start,
            )
            db.add(new_track)
            added += 1

    # Remove entries that no longer exist on disk
    result = await db.execute(select(LocalTrack).where(LocalTrack.last_seen < scan_start))
    removed_tracks = result.scalars().all()
    removed_count = len(removed_tracks)
    for track in removed_tracks:
        await db.delete(track)

    await db.commit()

    # Count total
    total_result = await db.execute(select(LocalTrack))
    total = len(total_result.scalars().all())

    logger.info(
        "Disk scan complete: %d added, %d updated, %d removed, %d total",
        added, updated, removed_count, total,
    )
    return {"added": added, "updated": updated, "removed": removed_count, "total": total}