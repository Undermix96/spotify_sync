"""Searcher orchestrator — tries slskd first, falls back to Prowlarr+qBittorrent."""
import logging
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.playlist import PlaylistTrack
from app.models.local_track import LocalTrack
from app.models.download_queue import DownloadQueue
from app.services.slskd import slskd_client
from app.services.prowlarr import prowlarr_client
from app.services.qbittorrent import qbittorrent_client

logger = logging.getLogger(__name__)


async def search_missing_tracks(db: AsyncSession) -> dict:
    """Find tracks not yet downloaded and create download queue entries.
    Priority: slskd → Prowlarr+qBittorrent
    """
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

    # Check if already in download_queue
    existing_queue = await db.execute(select(DownloadQueue.playlist_track_id))
    queued_ids = {row[0] for row in existing_queue.fetchall() if row[0]}

    # Check local_tracks match (simple fuzzy by normalized artist+title)
    local_result = await db.execute(select(LocalTrack.artist, LocalTrack.title))
    local_pairs = set()
    for artist, title in local_result.fetchall():
        if artist and title:
            key = (artist.lower().strip(), title.lower().strip())
            local_pairs.add(key)

    for track in tracks:
        if track.id in queued_ids:
            stats["skipped_existing"] += 1
            continue

        # Skip if already on disk
        track_key = (track.artist.lower().strip(), track.title.lower().strip())
        if track_key in local_pairs:
            stats["skipped_existing"] += 1
            continue

        # Step 1: Try slskd
        slskd_results = await slskd_client.search(track.artist, track.title, track.album)
        if slskd_results:
            best = slskd_results[0]
            download_id = await slskd_client.download(
                best.get("user", ""),
                best.get("filename", ""),
            )
            if download_id:
                queue_entry = DownloadQueue(
                    playlist_track_id=track.id,
                    source="slskd",
                    status="queued",
                    external_id=str(download_id),
                )
                db.add(queue_entry)
                stats["slskd_found"] += 1
                continue

        # Step 2: Fallback to Prowlarr
        prowlarr_results = await prowlarr_client.search(track.artist, track.title, track.album)
        if prowlarr_results:
            best = prowlarr_results[0]
            download_url = best.get("download_url", "") or best.get("info_url", "")
            if download_url:
                torrent_hash = await qbittorrent_client.add_magnet(download_url, category="music")
                if torrent_hash:
                    queue_entry = DownloadQueue(
                        playlist_track_id=track.id,
                        source="torrent",
                        status="downloading",
                        external_id=torrent_hash,
                    )
                    db.add(queue_entry)
                    stats["torrent_found"] += 1
                    continue

        # Step 3: Not found
        queue_entry = DownloadQueue(
            playlist_track_id=track.id,
            source=None,
            status="not_found",
            error_message="No lossless source found on slskd or Prowlarr",
        )
        db.add(queue_entry)
        stats["not_found"] += 1

    await db.commit()
    logger.info("Search complete: %s", stats)
    return stats