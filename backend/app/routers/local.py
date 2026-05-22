"""Local tracks and playlists endpoints."""
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.local_track import LocalTrack
from app.models.playlist import Playlist
from app.config import config

router = APIRouter(prefix="/api/local", tags=["local"])


@router.get("/tracks")
async def list_local_tracks(
    artist: str | None = None,
    album: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(LocalTrack).order_by(LocalTrack.artist, LocalTrack.album, LocalTrack.track_number)
    if artist:
        query = query.where(LocalTrack.artist.ilike(f"%{artist}%"))
    if album:
        query = query.where(LocalTrack.album.ilike(f"%{album}%"))
    result = await db.execute(query)
    tracks = result.scalars().all()
    return [
        {
            "id": t.id,
            "file_path": t.file_path,
            "artist": t.artist,
            "album": t.album,
            "title": t.title,
            "track_number": t.track_number,
            "duration_ms": t.duration_ms,
            "format": t.format,
            "file_size": t.file_size,
        }
        for t in tracks
    ]


@router.get("/playlists")
async def list_local_playlists():
    """List generated .m3u8 playlist files on disk."""
    playlists_path = Path(config.playlists_path)
    if not playlists_path.exists():
        return []

    m3u8_files = list(playlists_path.glob("*.m3u8"))
    result = []
    for f in sorted(m3u8_files):
        result.append({
            "name": f.stem,
            "file_path": str(f),
            "size_bytes": f.stat().st_size,
            "modified_at": f.stat().st_mtime,
        })
    return result


@router.get("/playlists/{playlist_name}")
async def get_local_playlist_content(playlist_name: str):
    """Return the content of a specific .m3u8 file."""
    playlists_path = Path(config.playlists_path)
    m3u8_path = playlists_path / f"{playlist_name}.m3u8"
    if not m3u8_path.exists():
        raise HTTPException(status_code=404, detail="Playlist file not found")

    with open(m3u8_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.strip().split("\n")
    entries = []
    current_extinf = None
    for line in lines:
        if line.startswith("#EXTINF:"):
            current_extinf = line
        elif not line.startswith("#") and line.strip():
            entries.append({
                "extinf": current_extinf,
                "file_path": line.strip(),
            })
            current_extinf = None

    return {
        "name": playlist_name,
        "file_path": str(m3u8_path),
        "tracks": entries,
    }