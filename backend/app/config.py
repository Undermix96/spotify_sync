from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SPM_", extra="ignore")

    # Paths
    music_path: str = Field(..., min_length=1)
    playlists_path: str = Field(default="/playlists", min_length=1)
    db_path: str = Field(default="/app/data/spm.db", min_length=1)

    # slskd
    slskd_url: str = "http://slskd:5030"
    slskd_api_key: str = Field(..., min_length=1)

    # Prowlarr
    prowlarr_url: str = "http://prowlarr:9696"
    prowlarr_api_key: str = Field(..., min_length=1)

    # qBittorrent
    qbittorrent_url: str = "http://qbittorrent:8080"
    qbittorrent_username: str = "admin"
    qbittorrent_password: str = Field(..., min_length=1)

    # Logging
    log_level: str = "INFO"


config = AppConfig()