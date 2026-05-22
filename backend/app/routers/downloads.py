"""Download queue management endpoints."""
import logging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.models.download_queue import DownloadQueue
from app.models.playlist import PlaylistTrack, Playlist
from app.schemas.download import DownloadResponse, DownloadActionResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/downloads", tags=["downloads"])


@router.get("", response_model=list[DownloadResponse])
async def list_downloads(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(DownloadQueue).order_by(DownloadQueue.created_at.desc())
    if status:
        query = query.where(DownloadQueue.status == status)
    result = await db.execute(query)
    entries = result.scalars().all()

    responses = []
    for entry in entries:
        track_title = None
        track_artist = None
        playlist_name = None
        if entry.playlist_track_id:
            track_result = await db.execute(
                select(PlaylistTrack).where(PlaylistTrack.id == entry.playlist_track_id)
            )
            track = track_result.scalar_one_or_none()
            if track:
                track_title = track.title
                track_artist = track.artist
                playlist_result = await db.execute(
                    select(Playlist.name).where(Playlist.id == track.playlist_id)
                )
                pname = playlist_result.scalar_one_or_none()
                playlist_name = pname

        responses.append(DownloadResponse(
            id=entry.id,
            playlist_track_id=entry.playlist_track_id,
            source=entry.source,
            status=entry.status,
            external_id=entry.external_id,
            progress=entry.progress,
            retry_count=entry.retry_count,
            max_retries=entry.max_retries,
            error_message=entry.error_message,
            track_title=track_title,
            track_artist=track_artist,
            playlist_name=playlist_name,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        ))
    return responses


@router.post("/{download_id}/retry", response_model=DownloadActionResponse)
async def retry_download(download_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DownloadQueue).where(DownloadQueue.id == download_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Download entry not found")

    entry.status = "pending"
    entry.retry_count = 0
    entry.error_message = None
    entry.external_id = None
    entry.progress = 0.0
    await db.commit()
    return DownloadActionResponse(success=True, message="Download reset and will retry")


@router.post("/{download_id}/cancel", response_model=DownloadActionResponse)
async def cancel_download(download_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DownloadQueue).where(DownloadQueue.id == download_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Download entry not found")

    entry.status = "failed"
    entry.error_message = "Cancelled by user"
    await db.commit()
    return DownloadActionResponse(success=True, message="Download cancelled")