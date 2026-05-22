"""slskd API wrapper using slskd-api package."""
import logging
from typing import Optional

from app.config import config

logger = logging.getLogger(__name__)


class SlskdClient:
    def __init__(self):
        self._client = None
        self.base_url = config.slskd_url
        self.api_key = config.slskd_api_key

    async def _ensure_client(self):
        if self._client is None:
            try:
                # Dynamic import to avoid crash if package missing
                from slskd_api import SlskdAPI
                self._client = SlskdAPI(base_url=self.base_url, api_key=self.api_key)
            except ImportError:
                logger.error("slskd-api package not installed")
                raise
            except Exception as e:
                logger.error("Failed to initialize slskd client: %s", e)
                raise

    async def test_connection(self) -> tuple[bool, str]:
        try:
            await self._ensure_client()
            # Simple ping/status call
            response = await self._client.get_application_state()
            if response:
                return True, "Connected to slskd"
            return False, "slskd returned empty response"
        except Exception as e:
            return False, f"slskd connection failed: {e}"

    async def search(self, artist: str, title: str, album: Optional[str] = None) -> list[dict]:
        """Search for lossless files matching the track."""
        try:
            await self._ensure_client()
            query = f"{artist} {title}"
            if album:
                query = f"{query} {album}"

            results = await self._client.search(query)
            lossless_files = []
            if not results or not isinstance(results, list):
                return lossless_files

            for file_info in results:
                filename = file_info.get("filename", "")
                ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
                if ext in ("flac",):
                    lossless_files.append({
                        "filename": filename,
                        "size": file_info.get("size", 0),
                        "file_id": file_info.get("id", ""),
                        "user": file_info.get("username", ""),
                        "bitrate": file_info.get("bitrate", 0),
                    })

            return sorted(lossless_files, key=lambda x: x.get("size", 0), reverse=True)
        except Exception as e:
            logger.error("slskd search error for %s - %s: %s", artist, title, e)
            return []

    async def download(self, username: str, filename: str) -> Optional[str]:
        """Request a download from slskd. Returns queue ID if successful."""
        try:
            await self._ensure_client()
            result = await self._client.enqueue_download(username, filename)
            if result and isinstance(result, dict):
                return result.get("id")
            return str(result) if result else None
        except Exception as e:
            logger.error("slskd download error for %s: %s", filename, e)
            return None

    async def get_download_status(self, download_id: str) -> Optional[dict]:
        """Check download progress."""
        try:
            await self._ensure_client()
            status = await self._client.get_download(download_id)
            return status
        except Exception as e:
            logger.error("slskd status error for %s: %s", download_id, e)
            return None


slskd_client = SlskdClient()