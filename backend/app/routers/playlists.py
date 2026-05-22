"""Playlist management endpoints."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.playlist import Playlist, PlaylistTrack
from app.models.download_queue import DownloadQueue
from app.schemas.playlist import (
    PlaylistCreate, PlaylistResponse, PlaylistDetailResponse,
    TrackResponse, PlaylistStatusResponse,
)
from app.services.spotify import extract_playlist_id, sync_playlist

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/playlists", tags=["playlists"])


@router.get("", response_model=list[PlaylistResponse])
async def list_playlists(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Playlist).order_by(Playlist.name))
    playlists = result.scalars().all()
    return playlists


@router.post("", response_model=PlaylistResponse, status_code=201)
async def add_playlist(body: PlaylistCreate, db: AsyncSession = Depends(get_db)):
    playlist_id = extract_playlist_id(body.url)
    if not playlist_id:
        raise HTTPException(status_code=400, detail="Invalid Spotify playlist URL")

    # Check if already exists
    existing = await db.execute(select(Playlist).where(Playlist.spotify_id == playlist_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Playlist already monitored")

    # Fetch metadata and tracks
    metadata, tracks = await sync_playlist(playlist_id)
    if not tracks and not metadata:
        raise HTTPException(status_code=400, detail="Could not fetch playlist data. Is it public?")

    playlist = Playlist(
        spotify_id=playlist_id,
        name=(metadata or {}).get("name", "Unknown Playlist"),
        description=(metadata or {}).get("description"),
        image_url=(metadata or {}).get("image_url") or (metadata or {}).get("image", ""),
        owner_name=(metadata or {}).get("owner_name") or (metadata or {}).get("owner", {}).get("display_name", "unknown"),
        track_count=len(tracks),
        last_synced=datetime.now(timezone.utc),
        enabled=True,
    )
    db.add(playlist)
    await db.flush()

    for t in tracks:
        track = PlaylistTrack(
            playlist_id=playlist.id,
            spotify_track_id=t["spotify_track_id"],
            title=t["title"],
            artist=t["artist"],
            album=t.get("album"),
            duration_ms=t.get("duration_ms"),
            position=t.get("position", 0),
            is_available=t.get("is_available", True),
            added_at_spotify=datetime.fromisoformat(t["added_at_spotify"].replace("Z", "+00:00")) if t.get("added_at_spotify") else datetime.now(timezone.utc),
        )
        db.add(track)

    await db.commit()
    await db.refresh(playlist)
    return playlist


@router.get("/{playlist_id}", response_model=PlaylistDetailResponse)
async def get_playlist_detail(playlist_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Playlist).where(Playlist.id == playlist_id))
    playlist = result.scalar_one_or_none()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    track_result = await db.execute(
        select(PlaylistTrack)
        .where(PlaylistTrack.playlist_id == playlist_id)
        .order_by(PlaylistTrack.position)
    )
    tracks = track_result.scalars().all()

    # Get download status for each track
    track_responses = []
    for t in tracks:
        dq_result = await db.execute(
            select(DownloadQueue).where(DownloadQueue.playlist_track_id == t.id).order_by(DownloadQueue.created_at.desc())
        )
        dq = dq_result.scalar_one_or_none()
        track_responses.append(TrackResponse(
            id=t.id,
            playlist_id=t.playlist_id,
            spotify_track_id=t.spotify_track_id,
            title=t.title,
            artist=t.artist,
            album=t.album,
            duration_ms=t.duration_ms,
            position=t.position,
            is_available=t.is_available,
            removed_from_spotify=t.removed_from_spotify,
            download_status=dq.status if dq else None,
        ))

    return PlaylistDetailResponse(
        playlist=PlaylistResponse.model_validate(playlist),
        tracks=track_responses,
    )


@router.delete("/{playlist_id}", status_code=204)
async def delete_playlist(playlist_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Playlist).where(Playlist.id == playlist_id))
    playlist = result.scalar_one_or_none()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    await db.delete(playlist)
    await db.commit()


async def _sync_playlist_tracks(db: AsyncSession, playlist: Playlist):
    """Internal sync logic: fetch from Spotify and update DB."""
    metadata, tracks = await sync_playlist(playlist.spotify_id)

    if metadata:
        playlist.name = metadata.get("name", playlist.name)
        playlist.description = metadata.get("description", playlist.description)
        if metadata.get("image_url") or metadata.get("image"):
            playlist.image_url = metadata.get("image_url") or metadata.get("image", "")
        if metadata.get("owner_name") or metadata.get("owner"):
            playlist.owner_name = metadata.get("owner_name") or metadata.get("owner", {}).get("display_name", playlist.owner_name)
    playlist.track_count = len(tracks)
    playlist.last_synced = datetime.now(timezone.utc)

    existing_tracks_result = await db.execute(
        select(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist.id)
    )
    existing_tracks = {t.spotify_track_id: t for t in existing_tracks_result.scalars().all()}

    new_ids = {t["spotify_track_id"] for t in tracks}
    current_ids = set(existing_tracks.keys())

    for i, t in enumerate(tracks):
        t["position"] = i
        if t["spotify_track_id"] in existing_tracks:
            existing = existing_tracks[t["spotify_track_id"]]
            if existing.removed_from_spotify:
                existing.removed_from_spotify = False
            if existing.position != i:
                existing.position = i
        else:
            new_track = PlaylistTrack(
                playlist_id=playlist.id,
                spotify_track_id=t["spotify_track_id"],
                title=t["title"],
                artist=t["artist"],
                album=t.get("album"),
                duration_ms=t.get("duration_ms"),
                position=i,
                is_available=t.get("is_available", True),
                added_at_spotify=datetime.fromisoformat(t["added_at_spotify"].replace("Z", "+00:00")) if t.get("added_at_spotify") else datetime.now(timezone.utc),
            )
            db.add(new_track)

    for tid in current_ids - new_ids:
        if tid in existing_tracks:
            existing_tracks[tid].removed_from_spotify = True
            existing_tracks[tid].is_available = False

    await db.commit()


@router.post("/{playlist_id}/sync", response_model=PlaylistStatusResponse)
async def sync_playlist_endpoint(playlist_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Playlist).where(Playlist.id == playlist_id))
    playlist = result.scalar_one_or_none()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    try:
        await _sync_playlist_tracks(db, playlist)
        return PlaylistStatusResponse(
            id=playlist.id,
            name=playlist.name,
            track_count=playlist.track_count,
            downloaded_count=playlist.downloaded_count,
            last_synced=playlist.last_synced,
            status="synced",
        )
    except Exception as e:
        logger.error("Sync error for playlist %s: %s", playlist_id, e)
        return PlaylistStatusResponse(
            id=playlist.id,
            name=playlist.name,
            track_count=playlist.track_count,
            downloaded_count=playlist.downloaded_count,
            last_synced=playlist.last_synced,
            status="error",
        )
