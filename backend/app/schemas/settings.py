from typing import Optional
from pydantic import BaseModel


class SettingUpdate(BaseModel):
    slskd_url: Optional[str] = None
    slskd_api_key: Optional[str] = None
    prowlarr_url: Optional[str] = None
    prowlarr_api_key: Optional[str] = None
    qbittorrent_url: Optional[str] = None
    qbittorrent_username: Optional[str] = None
    qbittorrent_password: Optional[str] = None
    music_path: Optional[str] = None
    playlists_path: Optional[str] = None
    db_path: Optional[str] = None
    log_level: Optional[str] = None
    interval_sync_playlists: Optional[int] = None
    interval_scan_disk: Optional[int] = None
    interval_search_missing: Optional[int] = None
    interval_monitor_downloads: Optional[int] = None
    interval_build_playlists: Optional[int] = None
    interval_cleanup_queue: Optional[int] = None


class SettingsResponse(BaseModel):
    slskd_url: str = ""
    slskd_api_key: str = ""
    prowlarr_url: str = ""
    prowlarr_api_key: str = ""
    qbittorrent_url: str = ""
    qbittorrent_username: str = ""
    qbittorrent_password: str = ""
    music_path: str = "/music"
    playlists_path: str = "/playlists"
    db_path: str = "/app/data/spm.db"
    log_level: str = "INFO"
    interval_sync_playlists: int = 21600
    interval_scan_disk: int = 43200
    interval_search_missing: int = 1800
    interval_monitor_downloads: int = 300
    interval_build_playlists: int = 900
    interval_cleanup_queue: int = 3600


class ConnectionTestResponse(BaseModel):
    success: bool
    message: str