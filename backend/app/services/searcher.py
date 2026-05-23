"""Searcher orchestrator — tries slskd first, falls back to Prowlarr+qBittorrent."""
import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.playlist import PlaylistTrack
from app.models.local_track import LocalTrack
from app.models.download_queue import DownloadQueue
from app.services.slskd import slskd_client
from app.services.prowlarr import prowlarr_client
from app.services.qbittorrent import qbittorrent_client

logger = logging.getLogger(__name__)

# Lock to prevent overlapping job executions
_search_lock = asyncio.Lock()

# Number of parallel searches per batch
_BATCH_SIZE = 3


async def _upsert_download_entry(db: AsyncSession, track_id: int, **kwargs) -> DownloadQueue:
    """Create or update a DownloadQueue entry for the given track_id."""
    existing = await db.execute(
        select(DownloadQueue).where(DownloadQueue.playlist_track_id == track_id)
    )
    entry = existing.scalar_one_or_none()
    if entry:
        for key, value in kwargs.items():
            setattr(entry, key, value)
        db.add(entry)
    else:
        entry = DownloadQueue(playlist_track_id=track_id, **kwargs)
    return entry


async def search_missing_tracks(db: AsyncSession) -> dict:
    """Find tracks not yet downloaded and create download queue entries.
    Priority: slskd → Prowlarr+qBittorrent.
    Processes tracks in parallel batches to reduce wall-clock time.
    """
    # Prevent overlapping executions
    if _search_lock.locked():
        logger.info("search_missing already running, skipping this execution")
        return {"skipped_due_to_lock": True}

    async with _search_lock:
        stats = {"slskd_found": 0, "torrent_found": 0, "not_found": 0, "skipped_existing": 0}

        # Get tracks that need downloading:
        # - Not removed from Spotify
        # - Not already matched in local_tracks (by artist + title fuzzy match)
        # - Not already in download_queue with status pending/queued/downloading
        result = await db.execute(
            select(PlaylistTrack).where(
                PlaylistTrack.removed_from_spotify == False,  # noqa: E712
                PlaylistTrack.is_available == True,  # noqa: E712
            )
        )
        tracks = result.scalars().all()

        # Check if already in download_queue with an active status
        # Exclude 'not_found' so those tracks can be retried
        existing_queue = await db.execute(
            select(DownloadQueue.playlist_track_id).where(
                DownloadQueue.status.in_(["pending", "queued", "downloading"])
            )
        )
        queued_ids = {row[0] for row in existing_queue.fetchall() if row[0]}

        # Check local_tracks match (simple fuzzy by normalized artist+title)
        local_result = await db.execute(select(LocalTrack.artist, LocalTrack.title))
        local_pairs = set()
        for artist, title in local_result.fetchall():
            if artist and title:
                key = (artist.lower().strip(), title.lower().strip())
                local_pairs.add(key)

        # Process tracks in parallel batches
        for i in range(0, len(tracks), _BATCH_SIZE):
            batch = tracks[i:i + _BATCH_SIZE]
            results = await asyncio.gather(
                *[_search_single_track(t, queued_ids, local_pairs, db) for t in batch]
            )

            for r in results:
                if r["entry"] is not None:
                    db.add(r["entry"])
                stats[r["status"]] += 1

            # Commit each batch to save partial progress
            await db.commit()

        logger.info("Search complete: %s", stats)
        return stats


async def _search_single_track(track: PlaylistTrack, queued_ids: set, local_pairs: set, db: AsyncSession) -> dict:
    """Search for a single track: slskd → Prowlarr fallback.

    Returns a dict with:
      - entry: DownloadQueue model instance (or None if skipped)
      - status: key to increment in stats
    """
    # Skip if already in download_queue (with active status)
    if track.id in queued_ids:
        return {"entry": None, "status": "skipped_existing"}

    # Skip if already on disk
    track_key = (track.artist.lower().strip(), track.title.lower().strip())
    if track_key in local_pairs:
        return {"entry": None, "status": "skipped_existing"}

    # Step 1: Try slskd
    slskd_results = await slskd_client.search(track.artist, track.title, track.album)
    if slskd_results:
        best = slskd_results[0]
        download_id = await slskd_client.download(
            best.get("user", ""),
            best.get("filename", ""),
        )
        if download_id:
            entry = await _upsert_download_entry(
                db, track.id,
                source="slskd",
                status="queued",
                external_id=str(download_id),
            )
            return {"entry": entry, "status": "slskd_found"}

    # Step 2: Fallback to Prowlarr
    prowlarr_results = await prowlarr_client.search(track.artist, track.title, track.album)
    if prowlarr_results:
        best = prowlarr_results[0]
        download_url = best.get("download_url", "") or best.get("info_url", "")
        if download_url:
            torrent_hash = await qbittorrent_client.add_magnet(download_url, category="music")
            if torrent_hash:
                entry = await _upsert_download_entry(
                    db, track.id,
                    source="torrent",
                    status="downloading",
                    external_id=torrent_hash,
                )
                return {"entry": entry, "status": "torrent_found"}

    # Step 3: Not found
    entry = await _upsert_download_entry(
        db, track.id,
        source=None,
        status="not_found",
        error_message="No lossless source found on slskd or Prowlarr",
    )
    return {"entry": entry, "status": "not_found"}