"""slskd API wrapper using slskd-api package."""
import asyncio
import logging
import random
from typing import Optional

import slskd_api

from app.config import config

logger = logging.getLogger(__name__)

# Search timeouts
_SEARCH_TIMEOUT = 35      # seconds — safety net for the entire search operation
_SEARCH_TIMEOUT_MS = 30_000  # milliseconds sent to slskd API (searchTimeout param)
_BATCH_POLL_INTERVAL = 1   # seconds between poll iterations

# Retry settings for HTTP 429 rate limiting
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 5   # seconds — first retry wait
_RETRY_MAX_DELAY = 20     # seconds — cap for exponential backoff
_RETRY_JITTER_MAX = 3     # seconds — random jitter added to backoff

# Stagger range for parallel searches
_STAGGER_MAX = 3.0        # seconds — max random delay before starting a search


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
        Wrapped in asyncio.wait_for to prevent hanging on unresponsive slskd.
        Automatically retries up to _MAX_RETRIES times on HTTP 429 (rate limiting)
        with exponential backoff + jitter.
        """
        for attempt in range(_MAX_RETRIES + 1):
            try:
                return await asyncio.wait_for(
                    self._search_impl(artist, title, album),
                    timeout=_SEARCH_TIMEOUT,
                )
            except asyncio.TimeoutError:
                logger.warning("slskd search timed out after %ss for %s - %s", _SEARCH_TIMEOUT, artist, title)
                return []
            except Exception as e:
                # Detect HTTP 429 (rate limiting) by checking the exception
                is_429 = self._is_rate_limited(e)
                if is_429 and attempt < _MAX_RETRIES:
                    delay = min(
                        _RETRY_BACKOFF_BASE * (2 ** attempt) + random.uniform(0, _RETRY_JITTER_MAX),
                        _RETRY_MAX_DELAY,
                    )
                    logger.warning(
                        "slskd rate limited (429) for %s - %s, retrying in %ds (attempt %d/%d)",
                        artist, title, int(delay), attempt + 1, _MAX_RETRIES,
                    )
                    await asyncio.sleep(delay)
                    continue
                logger.error("slskd search error for %s - %s: %s", artist, title, e)
                return []
        return []

    @staticmethod
    def _is_rate_limited(exception: Exception) -> bool:
        """Check if the exception indicates HTTP 429 rate limiting."""
        # Check common HTTP client libraries
        if hasattr(exception, "response") and hasattr(exception.response, "status_code"):
            return exception.response.status_code == 429
        # Fallback: check error string
        exc_str = str(exception)
        if "429" in exc_str and ("Too Many Requests" in exc_str or "Rate limit" in exc_str):
            return True
        return False

    async def _search_impl(self, artist: str, title: str, album: Optional[str] = None) -> list[dict]:
        """Internal search implementation (no outer timeout wrapper)."""
        await self._ensure_client()

        # Stagger: random delay to spread out parallel requests from the same batch
        await asyncio.sleep(random.uniform(0, _STAGGER_MAX))

        query = f"{artist} {title}"
        if album:
            query = f"{query} {album}"

        # 1. Start search (non-blocking)
        search_state = await asyncio.to_thread(
            self._client.searches.search_text,
            searchText=query,
            searchTimeout=_SEARCH_TIMEOUT_MS,
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
            await asyncio.sleep(_BATCH_POLL_INTERVAL)

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