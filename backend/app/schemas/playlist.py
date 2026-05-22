from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PlaylistCreate(BaseModel):
    url: str


class PlaylistResponse(BaseModel):
    id: int
    spotify_id: str
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    owner_name: Optional[str] = None
    track_count: int = 0
    downloaded_count: int = 0
    last_synced: Optional[datetime] = None
    enabled: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TrackResponse(BaseModel):
    id: int
    playlist_id: int
    spotify_track_id: str
    title: str
    artist: str
    album: Optional[str] = None
    duration_ms: Optional[int] = None
    position: int
    is_available: bool = True
    removed_from_spotify: bool = False
    download_status: Optional[str] = None

    model_config = {"from_attributes": True}


class PlaylistDetailResponse(BaseModel):
    playlist: PlaylistResponse
    tracks: list[TrackResponse]


class PlaylistStatusResponse(BaseModel):
    id: int
    name: str
    track_count: int
    downloaded_count: int
    last_synced: Optional[datetime] = None
    status: str