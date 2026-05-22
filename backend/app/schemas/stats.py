from pydantic import BaseModel


class StatsResponse(BaseModel):
    total_playlists: int = 0
    total_tracks_spotify: int = 0
    total_tracks_downloaded: int = 0
    active_downloads: int = 0
    pending_downloads: int = 0
    failed_downloads: int = 0
    local_tracks: int = 0
    disk_usage_bytes: int = 0