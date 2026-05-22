"""Public Spotify playlist extraction (no auth required)."""
import json
import logging
import re
from datetime import datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SPOTIFY_EMBED_URL = "https://open.spotify.com/embed/playlist/{playlist_id}"
SPOTIFY_API_URL = "https://api.spotify.com/v1/playlists/{playlist_id}/tracks"


def extract_playlist_id(url: str) -> Optional[str]:
    """Extract Spotify playlist ID from various URL formats."""
    patterns = [
        r"spotify\.com/playlist/([a-zA-Z0-9]+)",
        r"open\.spotify\.com/playlist/([a-zA-Z0-9]+)",
        r"playlist/([a-zA-Z0-9]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


async def fetch_playlist_metadata(playlist_id: str) -> Optional[dict]:
    """Fetch playlist metadata from Spotify embed page (no auth)."""
    try:
        url = SPOTIFY_EMBED_URL.format(playlist_id=playlist_id)
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            })
            if resp.status_code != 200:
                logger.error("Spotify embed returned %s for playlist %s", resp.status_code, playlist_id)
                return None

            soup = BeautifulSoup(resp.text, "html.parser")
            # Find the script tag containing JSON data
            scripts = soup.find_all("script", type="text/javascript")
            for script in scripts:
                text = script.string or ""
                if "window.__INITIAL_STATE__" in text:
                    json_str = text.split("window.__INITIAL_STATE__ = ")[1].split(";\n")[0].rstrip(";")
                    data = json.loads(json_str)
                    # Navigate to playlist data
                    playlists = data.get("playlist", {})
                    entities = playlists.get("entities", {})
                    playlist_data = entities.get(playlist_id)
                    if playlist_data:
                        return playlist_data

            logger.warning("No playlist data found in embed for %s", playlist_id)
            return None
    except Exception as e:
        logger.error("Error fetching playlist metadata for %s: %s", playlist_id, e)
        return None


async def fetch_playlist_tracks(playlist_id: str) -> list[dict]:
    """Fetch all tracks from a public Spotify playlist.
    Uses Spotify Web API public endpoints (no auth required for public playlists).
    """
    tracks = []
    offset = 0
    limit = 100

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            while True:
                resp = await client.get(
                    SPOTIFY_API_URL.format(playlist_id=playlist_id),
                    params={"offset": offset, "limit": limit, "market": "from_token"},
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "application/json",
                    },
                )

                if resp.status_code != 200:
                    logger.warning("Spotify API returned %s at offset %s", resp.status_code, offset)
                    break

                data = resp.json()
                items = data.get("items", [])
                if not items:
                    break

                for item in items:
                    track_obj = item.get("track")
                    if not track_obj:
                        continue

                    track = {
                        "spotify_track_id": track_obj.get("id", ""),
                        "title": track_obj.get("name", "Unknown"),
                        "artist": ", ".join(a.get("name", "") for a in track_obj.get("artists", [])),
                        "album": track_obj.get("album", {}).get("name") if track_obj.get("album") else None,
                        "duration_ms": track_obj.get("duration_ms"),
                        "position": offset + len(tracks),
                        "added_at_spotify": item.get("added_at"),
                        "is_available": track_obj.get("is_playable", True) and not track_obj.get("is_local", False),
                    }
                    tracks.append(track)

                offset += limit
                if offset >= data.get("total", 0):
                    break

    except Exception as e:
        logger.error("Error fetching tracks for playlist %s: %s", playlist_id, e)

    return tracks


async def sync_playlist(playlist_id: str) -> tuple[Optional[dict], list[dict]]:
    """Sync a playlist: returns (metadata, tracks)."""
    metadata = await fetch_playlist_metadata(playlist_id)
    tracks = await fetch_playlist_tracks(playlist_id)

    # Build metadata from track data if embed fails
    if metadata is None and tracks:
        metadata = {
            "name": f"Playlist {playlist_id[:8]}",
            "description": None,
            "owner_name": "unknown",
            "image_url": None,
        }

    return metadata, tracks