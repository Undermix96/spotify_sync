"""qBittorrent Web API v2 client."""
import logging
from typing import Optional

import httpx
from app.config import config

logger = logging.getLogger(__name__)


class QBittorrentClient:
    def __init__(self):
        self.base_url = config.qbittorrent_url.rstrip("/")
        self.username = config.qbittorrent_username
        self.password = config.qbittorrent_password
        self._client = httpx.AsyncClient(timeout=30, base_url=self.base_url)
        self._authenticated = False

    async def _ensure_auth(self):
        if self._authenticated:
            return
        try:
            resp = await self._client.post(
                "/api/v2/auth/login",
                data={"username": self.username, "password": self.password},
            )
            if resp.status_code == 200 and resp.text == "Ok.":
                self._authenticated = True
            else:
                logger.error("qBittorrent auth failed: %s", resp.text)
                raise ConnectionError(f"Auth failed: {resp.text}")
        except Exception as e:
            logger.error("qBittorrent auth error: %s", e)
            raise

    async def test_connection(self) -> tuple[bool, str]:
        try:
            await self._ensure_auth()
            resp = await self._client.get("/api/v2/app/version")
            if resp.status_code == 200:
                return True, f"Connected to qBittorrent (v{resp.text})"
            return False, f"qBittorrent returned status {resp.status_code}"
        except Exception as e:
            return False, f"qBittorrent connection failed: {e}"

    async def add_magnet(self, magnet: str, category: str = "music", save_path: Optional[str] = None) -> Optional[str]:
        """Add a magnet link to qBittorrent. Returns torrent hash."""
        try:
            await self._ensure_auth()
            data = {"urls": magnet, "category": category}
            if save_path:
                data["savepath"] = save_path
            resp = await self._client.post("/api/v2/torrents/add", data=data)
            if resp.status_code in (200, 201):
                # Fetch the most recent torrent to get its hash
                await self._client.post("/api/v2/torrents/resume", data={"hashes": "all"})
                list_resp = await self._client.get("/api/v2/torrents/info", params={"limit": 1, "sort": "added_on", "reverse": "true"})
                if list_resp.status_code == 200:
                    torrents = list_resp.json()
                    if torrents:
                        return torrents[0].get("hash")
            return None
        except Exception as e:
            logger.error("qBittorrent add_magnet error: %s", e)
            return None

    async def get_torrent_info(self, torrent_hash: str) -> Optional[dict]:
        """Get torrent status information."""
        try:
            await self._ensure_auth()
            resp = await self._client.get("/api/v2/torrents/info", params={"hashes": torrent_hash})
            if resp.status_code == 200:
                torrents = resp.json()
                if torrents:
                    t = torrents[0]
                    return {
                        "hash": t.get("hash"),
                        "name": t.get("name"),
                        "progress": t.get("progress", 0) * 100,
                        "state": t.get("state"),
                        "size": t.get("total_size", 0),
                        "downloaded": t.get("downloaded", 0),
                        "eta": t.get("eta", 0),
                        "save_path": t.get("save_path", ""),
                        "category": t.get("category", ""),
                    }
            return None
        except Exception as e:
            logger.error("qBittorrent get_torrent_info error: %s", e)
            return None

    async def remove_torrent(self, torrent_hash: str, delete_files: bool = False) -> bool:
        """Remove a torrent from qBittorrent."""
        try:
            await self._ensure_auth()
            resp = await self._client.post(
                "/api/v2/torrents/delete",
                data={"hashes": torrent_hash, "deleteFiles": "true" if delete_files else "false"},
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error("qBittorrent remove_torrent error: %s", e)
            return False

    async def close(self):
        await self._client.aclose()


qbittorrent_client = QBittorrentClient()