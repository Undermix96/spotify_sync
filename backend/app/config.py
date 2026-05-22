from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SPM_", extra="ignore")

    # Paths
    music_path: str = "/music"
    playlists_path: str = "/playlists"
    db_path: str = "/app/data/spm.db"

    # slskd
    slskd_url: str = "http://slskd:5030"
    slskd_api_key: str = ""

    # Prowlarr
    prowlarr_url: str = "http://prowlarr:9696"
    prowlarr_api_key: str = ""

    # qBittorrent
    qbittorrent_url: str = "http://qbittorrent:8080"
    qbittorrent_username: str = "admin"
    qbittorrent_password: str = "adminadmin"

    # Logging
    log_level: str = "INFO"


config = AppConfig()