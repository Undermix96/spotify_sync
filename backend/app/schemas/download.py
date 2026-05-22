from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DownloadResponse(BaseModel):
    id: int
    playlist_track_id: Optional[int] = None
    source: Optional[str] = None
    status: str
    external_id: Optional[str] = None
    progress: float = 0.0
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    track_title: Optional[str] = None
    track_artist: Optional[str] = None
    playlist_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DownloadRetryRequest(BaseModel):
    pass


class DownloadActionResponse(BaseModel):
    success: bool
    message: str