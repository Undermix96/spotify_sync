"""slskd API wrapper using slskd-api package."""
import asyncio
import logging
from typing import Optional

import slskd_api

from app.config import config

logger = logging.getLogger(__name__)


class SlskdClient:
    def __init__(self):
        self._client: Optional[slskd_api.SlskdClient] = None
        self.base_url = config.slskd_url
        self.api_key = config.slskd_api_key

    async def _ensure_client(self):
        if self._client is None:
            try:
                self._client = slskd_api.SlskdClient(
                    host=self.base_url,
                    api_key=self.api_key,
                    url_base="/",
                    verify_ssl=True,
                    timeout=30.0,
                )
            except Exception as e:
                logger.error("Failed to initialize slskd client: %s", e)
                raise

    async def test_connection(self) -> tuple[bool, str]:
        try:
            await self._ensure_client()
            status = await asyncio.to_thread(self._client.application.state)
            if status:
                return True, "Connected to slskd"
            return False, "slskd returned empty response"
        except Exception as e:
            return False, f"slskd connection failed: {e}"

    async def search(self, artist: str, title: str, album: Optional[str] = None) -> list[dict]:
        """Search for lossless files matching the track.

        Uses search_text (non-blocking) + polling + search_responses.
        Returns sorted list of FLAC files by size descending.
        """
        try:
            await self._ensure_client()
            query = f"{artist} {title}"
            if album:
                query = f"{query} {album}"

            # 1. Start search (non-blocking)
            search_state = await asyncio.to_thread(
                self._client.searches.search_text,
                searchText=query,
                searchTimeout=15000,
            )
            search_id = search_state["id"]

            # 2. Poll until search is complete
            while True:
                state = await asyncio.to_thread(
                    self._client.searches.state,
                    search_id,
                    includeResponses=False,
                )
                if state["isComplete"]:
                    break
                await asyncio.sleep(1)

            # 3. Retrieve results
            responses = await asyncio.to_thread(
                self._client.searches.search_responses,
                search_id,
            )

            # 4. Filter FLAC files
            lossless_files = []
            for response in responses:
                username = response.get("username", "")
                has_free_slot = response.get("hasFreeUploadSlot", False)
                for file_info in response.get("files", []):
                    ext = file_info.get("extension", "").lower()
                    if ext == "flac":
                        lossless_files.append({
                            "filename": file_info.get("filename", ""),
                            "size": file_info.get("size", 0),
                            "user": username,
                            "bitrate": file_info.get("bitRate", 0),
                            "has_free_slot": has_free_slot,
                        })

            return sorted(lossless_files, key=lambda x: x.get("size", 0), reverse=True)
        except Exception as e:
            logger.error("slskd search error for %s - %s: %s", artist, title, e)
            return []

    async def download(self, username: str, filename: str) -> Optional[str]:
        """Request a download from slskd.

        Builds a minimal SearchFile dict and enqueues the transfer.
        Returns the filename as identifier (enqueue returns bool, not a queue ID).
        """
        try:
            await self._ensure_client()
            ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
            file_obj = {
                "filename": filename,
                "size": 0,
                "extension": ext,
            }
            success = await asyncio.to_thread(
                self._client.transfers.enqueue,
                username=username,
                files=[file_obj],
            )
            if success:
                logger.info("Download enqueued for %s from %s", filename, username)
                return filename
            logger.warning("slskd enqueue returned False for %s from %s", filename, username)
            return None
        except Exception as e:
            logger.error("slskd download error for %s: %s", filename, e)
            return None

    async def get_download_status(self, download_id: str) -> Optional[dict]:
        """Check download progress by iterating all transfers.

        Matches by file id or filename (since enqueue returns bool, we fall back to filename).
        Normalizes API fields for consumer compatibility:
          - percentComplete → progress
          - state: Errored → failed, Cancelled → cancelled, TimedOut → timedout
        """
        try:
            await self._ensure_client()
            all_downloads = await asyncio.to_thread(
                self._client.transfers.get_all_downloads,
                includeRemoved=False,
            )
            for transfer in all_downloads:
                for directory in transfer.get("directories", []):
                    for file_entry in directory.get("files", []):
                        if file_entry.get("id") == download_id or file_entry.get("filename") == download_id:
                            # Normalize field names for consumer compatibility
                            normalized = dict(file_entry)
                            if "percentComplete" in normalized:
                                normalized["progress"] = normalized.pop("percentComplete")
                            # Normalize state values
                            raw_state = normalized.get("state", "")
                            state_map = {
                                "Errored": "failed",
                                "Cancelled": "cancelled",
                                "TimedOut": "timedout",
                            }
                            normalized["state"] = state_map.get(raw_state, raw_state)
                            return normalized
            return None
        except Exception as e:
            logger.error("slskd status error for %s: %s", download_id, e)
            return None


slskd_client = SlskdClient()