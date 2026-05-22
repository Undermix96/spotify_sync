"""Prowlarr REST API client for searching torrents."""
import logging
from typing import Optional

import httpx
from app.config import config

logger = logging.getLogger(__name__)


class ProwlarrClient:
    def __init__(self):
        self.base_url = config.prowlarr_url.rstrip("/")
        self.api_key = config.prowlarr_api_key

    @property
    def _headers(self) -> dict:
        return {"X-Api-Key": self.api_key, "Content-Type": "application/json"}

    async def test_connection(self) -> tuple[bool, str]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.base_url}/api/v1/indexer",
                    headers=self._headers,
                )
                if resp.status_code == 200:
                    return True, "Connected to Prowlarr"
                return False, f"Prowlarr returned status {resp.status_code}"
        except Exception as e:
            return False, f"Prowlarr connection failed: {e}"

    async def search(self, artist: str, title: str, album: Optional[str] = None) -> list[dict]:
        """Search Prowlarr indexers for lossless releases."""
        try:
            query = f"{artist} {title}"
            if album:
                query = f"{query} {album}"

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{self.base_url}/api/v1/search",
                    headers=self._headers,
                    params={"query": query, "type": "search", "limit": 20},
                )

                if resp.status_code != 200:
                    logger.warning("Prowlarr search returned %s", resp.status_code)
                    return []

                results = resp.json()
                lossless = []
                for r in results:
                    title_lower = r.get("title", "").lower()
                    # Filter for lossless formats in torrent name
                    if any(x in title_lower for x in ("flac", "lossless", "alac")):
                        lossless.append({
                            "title": r.get("title"),
                            "guid": r.get("guid"),
                            "info_url": r.get("infoUrl", ""),
                            "download_url": r.get("downloadUrl", "") or r.get("magnetUrl", ""),
                            "size": r.get("size", 0),
                            "seeders": r.get("seeders", 0),
                            "indexer": r.get("indexer", ""),
                            "age": r.get("age", 0),
                        })

                return sorted(lossless, key=lambda x: x.get("seeders", 0), reverse=True)
        except Exception as e:
            logger.error("Prowlarr search error for %s - %s: %s", artist, title, e)
            return []


prowlarr_client = ProwlarrClient()