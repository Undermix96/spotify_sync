"""Download monitor — checks status of queued/downloading entries and imports completed files."""
import logging
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.download_queue import DownloadQueue
from app.models.playlist import PlaylistTrack
from app.models.local_track import LocalTrack
from app.services.slskd import slskd_client
from app.services.qbittorrent import qbittorrent_client
from app.services.organizer import import_file
from app.utils.audio import extract_metadata_mutagen, compute_checksum

logger = logging.getLogger(__name__)


async def monitor_downloads(db: AsyncSession) -> dict:
    """Check status of all active downloads and process completed ones."""
    stats = {"completed": 0, "still_active": 0, "failed": 0, "retrying": 0, "errors": 0}

    # Get all active download entries
    result = await db.execute(
        select(DownloadQueue).where(
            DownloadQueue.status.in_(["queued", "downloading"])
        )
    )
    entries = result.scalars().all()

    for entry in entries:
        try:
            if entry.source == "slskd" and entry.external_id:
                status_data = await slskd_client.get_download_status(entry.external_id)
                if status_data is None:
                    # slskd might have cleared the download, mark for retry
                    await _handle_failure(entry, db, "slskd status check returned None")
                    stats["errors"] += 1
                    continue

                # Check if completed (status varies by slskd-api version)
                state = status_data.get("state", "").lower()
                progress = status_data.get("progress", 0)
                entry.progress = float(progress) * 100 if isinstance(progress, float) else 0.0

                if state == "completed" or state == "finished":
                    # Get file path from slskd download directory
                    file_path = status_data.get("filename") or status_data.get("filePath")
                    if file_path:
                        source_path = Path(file_path)
                        import_result = await import_file(source_path, db)
                        if import_result["success"]:
                            entry.status = "completed"
                            entry.progress = 100.0
                            # Add to local_tracks
                            meta = import_result["metadata"]
                            new_local = LocalTrack(
                                file_path=import_result["dest_path"],
                                artist=meta.get("artist"),
                                album=meta.get("album"),
                                title=meta.get("title"),
                                track_number=meta.get("track_number"),
                                duration_ms=meta.get("duration_ms"),
                                format=meta.get("format"),
                                file_size=Path(import_result["dest_path"]).stat().st_size,
                                checksum=compute_checksum(Path(import_result["dest_path"])),
                            )
                            db.add(new_local)
                            stats["completed"] += 1
                        else:
                            await _handle_failure(entry, db, f"Import failed: {import_result.get('error')}")
                            stats["errors"] += 1
                    else:
                        await _handle_failure(entry, db, "Completed download has no file path")
                        stats["errors"] += 1
                elif state in ("failed", "cancelled", "timedout"):
                    await _handle_failure(entry, db, f"slskd state: {state}")
                    stats["failed"] += 1
                else:
                    stats["still_active"] += 1

            elif entry.source == "torrent" and entry.external_id:
                tor_info = await qbittorrent_client.get_torrent_info(entry.external_id)
                if tor_info is None:
                    # Torrent might have been removed manually
                    await _handle_failure(entry, db, "Torrent not found in qBittorrent (removed manually?)")
                    stats["errors"] += 1
                    continue

                entry.progress = tor_info.get("progress", 0)
                state = tor_info.get("state", "").lower()

                if entry.progress >= 100 or state == "completed":
                    # Find the downloaded file
                    save_path = Path(tor_info.get("save_path", ""))
                    torrent_name = tor_info.get("name", "")
                    torrent_dir = save_path / torrent_name if torrent_name else save_path

                    # Search for audio files in the torrent directory
                    audio_files = list(torrent_dir.rglob("*.flac")) if torrent_dir.exists() else []
                    if audio_files:
                        for af in audio_files:
                            import_result = await import_file(af, db)
                            if import_result["success"]:
                                meta = import_result["metadata"]
                                new_local = LocalTrack(
                                    file_path=import_result["dest_path"],
                                    artist=meta.get("artist"),
                                    album=meta.get("album"),
                                    title=meta.get("title"),
                                    track_number=meta.get("track_number"),
                                    duration_ms=meta.get("duration_ms"),
                                    format=meta.get("format"),
                                    file_size=Path(import_result["dest_path"]).stat().st_size,
                                    checksum=compute_checksum(Path(import_result["dest_path"])),
                                )
                                db.add(new_local)
                        entry.status = "completed"
                        entry.progress = 100.0
                        stats["completed"] += 1
                        # Remove torrent from qBittorrent without deleting files
                        await qbittorrent_client.remove_torrent(entry.external_id, delete_files=False)
                    else:
                        # Torrent completed but no audio files found
                        entry.status = "completed"
                        entry.progress = 100.0
                        entry.error_message = "Torrent completed but no FLAC files found"
                        stats["completed"] += 1
                elif state in ("failed", "cancelled", "error"):
                    await _handle_failure(entry, db, f"qBittorrent state: {state}")
                    stats["failed"] += 1
                else:
                    stats["still_active"] += 1

        except Exception as e:
            logger.error("Error monitoring download %s: %s", entry.id, e)
            stats["errors"] += 1

    await db.commit()
    return stats


async def _handle_failure(entry: DownloadQueue, db: AsyncSession, reason: str):
    """Handle a failed download entry with retry logic."""
    entry.retry_count += 1
    if entry.retry_count >= entry.max_retries:
        entry.status = "failed"
        entry.error_message = reason
    else:
        entry.status = "not_found"
        entry.error_message = f"Retry {entry.retry_count}/{entry.max_retries}: {reason}"