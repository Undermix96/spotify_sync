"""Playlist builder — generates .m3u8 files from matched local tracks."""
import logging
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.models.playlist import Playlist, PlaylistTrack
from app.models.local_track import LocalTrack

logger = logging.getLogger(__name__)


async def build_playlists(db: AsyncSession) -> dict:
    """Generate .m3u8 playlist files for all enabled playlists."""
    stats = {"generated": 0, "skipped": 0, "errors": 0, "total_tracks": 0}

    playlists_path = Path(config.playlists_path)
    playlists_path.mkdir(parents=True, exist_ok=True)

    # Get all enabled playlists
    result = await db.execute(select(Playlist).where(Playlist.enabled == True))  # noqa: E712
    playlists = result.scalars().all()

    for playlist in playlists:
        try:
            # Get tracks still on Spotify, ordered by position
            track_result = await db.execute(
                select(PlaylistTrack)
                .where(
                    PlaylistTrack.playlist_id == playlist.id,
                    PlaylistTrack.removed_from_spotify == False,  # noqa: E712
                    PlaylistTrack.is_available == True,  # noqa: E712
                )
                .order_by(PlaylistTrack.position)
            )
            spotify_tracks = track_result.scalars().all()

            # Match each track to local files
            m3u8_lines = [
                "#EXTM3U",
                "#EXTENC: UTF-8",
                f"#PLAYLIST: {playlist.name}",
            ]

            matched_count = 0
            for track in spotify_tracks:
                # Find matching local track by artist + title
                local_result = await db.execute(
                    select(LocalTrack).where(
                        LocalTrack.artist.ilike(track.artist),
                        LocalTrack.title.ilike(track.title),
                    )
                )
                local_track = local_result.scalar_one_or_none()

                if local_track:
                    # Generate relative path from playlists file to music file
                    music_path = Path(config.music_path)
                    file_path = Path(local_track.file_path)
                    try:
                        relative_path = file_path.relative_to(music_path)
                    except ValueError:
                        # If not under music_path, use absolute path
                        relative_path = file_path

                    duration_sec = (local_track.duration_ms or 0) // 1000
                    m3u8_lines.append(
                        f"#EXTINF:{duration_sec},{local_track.artist} - {local_track.title}"
                    )
                    # Use relative path from music directory perspective
                    # Navidrome expects paths relative to its MusicFolder
                    m3u8_lines.append(str(relative_path))
                    matched_count += 1

            # Write .m3u8 file
            safe_name = "".join(c for c in playlist.name if c.isalnum() or c in " _-").strip() or "playlist"
            m3u8_path = playlists_path / f"{safe_name}.m3u8"

            with open(m3u8_path, "w", encoding="utf-8") as f:
                f.write("\n".join(m3u8_lines))

            # Update downloaded_count
            playlist.downloaded_count = matched_count
            stats["generated"] += 1
            stats["total_tracks"] += matched_count
            logger.info("Generated playlist '%s' with %d/%d tracks", playlist.name, matched_count, len(spotify_tracks))

        except Exception as e:
            logger.error("Error building playlist '%s': %s", playlist.name, e)
            stats["errors"] += 1

    await db.commit()
    return stats