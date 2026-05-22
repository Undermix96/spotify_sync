"""Settings management endpoints."""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.database import get_db
from app.models.settings import Setting
from app.schemas.settings import SettingUpdate, SettingsResponse, ConnectionTestResponse
from app.services.slskd import slskd_client
from app.services.prowlarr import prowlarr_client
from app.services.qbittorrent import qbittorrent_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])

DEFAULT_SETTINGS = {
    "slskd_url": "",
    "slskd_api_key": "",
    "prowlarr_url": "",
    "prowlarr_api_key": "",
    "qbittorrent_url": "",
    "qbittorrent_username": "",
    "qbittorrent_password": "",
    "music_path": "/music",
    "playlists_path": "/playlists",
    "db_path": "/app/data/spm.db",
    "log_level": "INFO",
    "interval_sync_playlists": "21600",
    "interval_scan_disk": "43200",
    "interval_search_missing": "1800",
    "interval_monitor_downloads": "300",
    "interval_build_playlists": "900",
    "interval_cleanup_queue": "3600",
}


async def _get_setting(db: AsyncSession, key: str) -> str:
    result = await db.execute(select(Setting.value).where(Setting.key == key))
    val = result.scalar_one_or_none()
    return val if val is not None else DEFAULT_SETTINGS.get(key, "")


async def _set_setting(db: AsyncSession, key: str, value: str):
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = str(value)
    else:
        db.add(Setting(key=key, value=str(value)))


@router.get("", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    data = {}
    for key in DEFAULT_SETTINGS:
        data[key] = await _get_setting(db, key)
    return SettingsResponse(**data)


@router.put("", response_model=SettingsResponse)
async def update_settings(body: SettingUpdate, db: AsyncSession = Depends(get_db)):
    update_data = body.model_dump(exclude_none=True)
    for key, value in update_data.items():
        await _set_setting(db, key, str(value))
    await db.commit()

    # Return updated settings
    data = {}
    for key in DEFAULT_SETTINGS:
        data[key] = await _get_setting(db, key)
    return SettingsResponse(**data)


@router.post("/test-slskd", response_model=ConnectionTestResponse)
async def test_slskd(db: AsyncSession = Depends(get_db)):
    url = await _get_setting(db, "slskd_url")
    key = await _get_setting(db, "slskd_api_key")
    if url:
        slskd_client.base_url = url
    if key:
        slskd_client.api_key = key
    success, message = await slskd_client.test_connection()
    return ConnectionTestResponse(success=success, message=message)


@router.post("/test-prowlarr", response_model=ConnectionTestResponse)
async def test_prowlarr(db: AsyncSession = Depends(get_db)):
    url = await _get_setting(db, "prowlarr_url")
    key = await _get_setting(db, "prowlarr_api_key")
    if url:
        prowlarr_client.base_url = url
    if key:
        prowlarr_client.api_key = key
    success, message = await prowlarr_client.test_connection()
    return ConnectionTestResponse(success=success, message=message)


@router.post("/test-qbittorrent", response_model=ConnectionTestResponse)
async def test_qbittorrent(db: AsyncSession = Depends(get_db)):
    url = await _get_setting(db, "qbittorrent_url")
    user = await _get_setting(db, "qbittorrent_username")
    pw = await _get_setting(db, "qbittorrent_password")
    if url:
        qbittorrent_client.base_url = url
    if user:
        qbittorrent_client.username = user
    if pw:
        qbittorrent_client.password = pw
    success, message = await qbittorrent_client.test_connection()
    return ConnectionTestResponse(success=success, message=message)