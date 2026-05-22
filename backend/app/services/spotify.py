"""Public Spotify playlist extraction (no auth required)."""
import asyncio
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
MAX_PAGES = 100


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


def _parse_embed_data(html: str, playlist_id: str) -> Optional[dict]:
    """Parse the __NEXT_DATA__ JSON from Spotify embed page.
    
    Returns a dict with keys: entity, access_token, settings
    or None if parsing fails.
    """
    soup = BeautifulSoup(html, "html.parser")
    next_data = soup.find("script", id="__NEXT_DATA__", type="application/json")
    if not next_data:
        # Fallback: try the old window.__INITIAL_STATE__ format
        scripts = soup.find_all("script", type="text/javascript")
        for script in scripts:
            text = script.string or ""
            if "window.__INITIAL_STATE__" in text:
                json_str = text.split("window.__INITIAL_STATE__ = ")[1].split(";\n")[0].rstrip(";")
                data = json.loads(json_str)
                playlists = data.get("playlist", {})
                entities = playlists.get("entities", {})
                playlist_data = entities.get(playlist_id)
                if playlist_data:
                    return {
                        "entity": playlist_data,
                        "access_token": None,
                        "settings": {},
                    }
        return None

    try:
        data = json.loads(next_data.string)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error("Failed to parse __NEXT_DATA__ JSON: %s", e)
        return None

    page_props = data.get("props", {}).get("pageProps", {})
    state = page_props.get("state", {})
    entity_data = state.get("data", {}).get("entity")
    if not entity_data:
        logger.warning("No entity data found in __NEXT_DATA__")
        return None

    settings = state.get("settings", {})
    session = settings.get("session", {})
    access_token = session.get("accessToken")

    return {
        "entity": entity_data,
        "access_token": access_token,
        "settings": settings,
    }


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

            parsed = _parse_embed_data(resp.text, playlist_id)
            if not parsed:
                logger.warning("No playlist data found in embed for %s", playlist_id)
                return None

            entity = parsed["entity"]

            # Try multiple possible image sources
            image_url = None
            cover_art = entity.get("coverArt", {})
            if cover_art.get("sources"):
                image_url = cover_art["sources"][0].get("url")
            if not image_url:
                visual_identity = entity.get("visualIdentity", {})
                if visual_identity.get("image"):
                    image_url = visual_identity["image"][0].get("url")

            metadata = {
                "name": entity.get("name", "Unknown Playlist"),
                "description": entity.get("description"),
                "owner_name": entity.get("subtitle", "unknown"),
                "image_url": image_url,
            }
            return metadata

    except Exception as e:
        logger.error("Error fetching playlist metadata for %s: %s", playlist_id, e)
        return None


async def fetch_playlist_tracks(playlist_id: str) -> list[dict]:
    """Fetch all tracks from a public Spotify playlist.
    Uses the embed page __NEXT_DATA__ for track list (no API auth required).
    Falls back to Spotify Web API with the embed's access token if more tracks needed.
    """
    tracks = []
    unplayable_count = 0

    try:
        url = SPOTIFY_EMBED_URL.format(playlist_id=playlist_id)
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            })
            if resp.status_code != 200:
                logger.error("Spotify embed returned %s for playlist %s", resp.status_code, playlist_id)
                return []

            parsed = _parse_embed_data(resp.text, playlist_id)
            if not parsed:
                logger.warning("No playlist data found in embed for %s", playlist_id)
                return []

            entity = parsed["entity"]
            access_token = parsed["access_token"]
            track_list = entity.get("trackList", [])

            # Build tracks from embed data
            for i, item in enumerate(track_list):
                track_uri = item.get("uri", "")
                spotify_track_id = track_uri.split(":")[-1] if ":" in track_uri else ""

                is_playable = item.get("isPlayable", False)
                if not is_playable:
                    unplayable_count += 1

                track = {
                    "spotify_track_id": spotify_track_id,
                    "title": item.get("title", "Unknown"),
                    "artist": item.get("subtitle", "Unknown"),
                    "album": None,  # Embed does not provide album
                    "duration_ms": item.get("duration"),
                    "position": i,
                    "added_at_spotify": None,  # Embed does not provide added_at
                    "is_available": is_playable and not item.get("isNineteenPlus", False),
                }
                tracks.append(track)

            # If the embed only shows partial tracks, try to paginate via API
            # using the embed's access token
            embed_track_count = len(track_list)
            if embed_track_count >= 50 and access_token:
                logger.info(
                    "Embed shows %d tracks for %s, attempting API pagination with access token",
                    embed_track_count, playlist_id,
                )
                additional_tracks = await _fetch_tracks_via_api(
                    playlist_id, access_token, embed_track_count
                )
                tracks.extend(additional_tracks)

    except Exception as e:
        logger.error("Error fetching tracks for playlist %s: %s", playlist_id, e)

    if unplayable_count > 0:
        logger.info("Excluded %d unplayable tracks from playlist %s", unplayable_count, playlist_id)

    return tracks


async def _fetch_tracks_via_api(
    playlist_id: str, access_token: str, start_offset: int
) -> list[dict]:
    """Fetch additional tracks via Spotify Web API using an access token.
    Implements retry with exponential backoff for rate limiting (429).
    """
    tracks = []
    offset = start_offset
    limit = 50  # Lower limit to reduce chance of rate limiting
    page_count = 0
    max_retries = 3

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            while page_count < MAX_PAGES:
                page_count += 1
                retries = 0

                while retries <= max_retries:
                    resp = await client.get(
                        SPOTIFY_API_URL.format(playlist_id=playlist_id),
                        params={"offset": offset, "limit": limit, "market": "from_token"},
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Accept": "application/json",
                            "Authorization": f"Bearer {access_token}",
                        },
                    )

                    if resp.status_code == 429:
                        retries += 1
                        if retries > max_retries:
                            logger.warning(
                                "Spotify API rate limited at offset %s for playlist %s, giving up after %d retries",
                                offset, playlist_id, max_retries,
                            )
                            break

                        retry_after = 0
                        retry_header = resp.headers.get("Retry-After")
                        if retry_header:
                            try:
                                retry_after = int(retry_header)
                            except ValueError:
                                retry_after = 0
                        wait = retry_after if retry_after > 0 else 2 ** retries
                        logger.warning(
                            "Spotify API returned 429 at offset %s for playlist %s, "
                            "retrying in %ds (attempt %d/%d)",
                            offset, playlist_id, wait, retries, max_retries,
                        )
                        await asyncio.sleep(wait)
                        continue

                    if resp.status_code != 200:
                        logger.warning(
                            "Spotify API returned %s at offset %s for playlist %s",
                            resp.status_code, offset, playlist_id,
                        )
                        retries = max_retries + 1  # break out of retry loop
                        break

                    data = resp.json()
                    items = data.get("items", [])
                    if not items:
                        retries = max_retries + 1  # no more pages
                        break

                    for i, item in enumerate(items):
                        track_obj = item.get("track")
                        if not track_obj:
                            continue

                        is_playable = track_obj.get("is_playable", False)

                        track = {
                            "spotify_track_id": track_obj.get("id", ""),
                            "title": track_obj.get("name", "Unknown"),
                            "artist": ", ".join(a.get("name", "") for a in track_obj.get("artists", [])),
                            "album": track_obj.get("album", {}).get("name") if track_obj.get("album") else None,
                            "duration_ms": track_obj.get("duration_ms"),
                            "position": offset + i,
                            "added_at_spotify": item.get("added_at"),
                            "is_available": is_playable and not track_obj.get("is_local", False),
                        }
                        tracks.append(track)

                    offset += limit
                    if offset >= data.get("total", 0):
                        retries = max_retries + 1  # done paginating
                        break

                    # Polite delay between pages to avoid hitting rate limits
                    await asyncio.sleep(1.5)
                    break  # exit retry loop, continue to next page

                if retries > max_retries:
                    break

    except Exception as e:
        logger.error("Error fetching API tracks for playlist %s: %s", playlist_id, e)

    return tracks


async def _fetch_embed(playlist_id: str) -> Optional[tuple[dict, list[dict]]]:
    """Make a single embed request and return (metadata, tracks) or None."""
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

            parsed = _parse_embed_data(resp.text, playlist_id)
            if not parsed:
                logger.warning("No playlist data found in embed for %s", playlist_id)
                return None

            entity = parsed["entity"]

            # Build metadata
            image_url = None
            cover_art = entity.get("coverArt", {})
            if cover_art.get("sources"):
                image_url = cover_art["sources"][0].get("url")
            if not image_url:
                visual_identity = entity.get("visualIdentity", {})
                if visual_identity.get("image"):
                    image_url = visual_identity["image"][0].get("url")

            metadata = {
                "name": entity.get("name", "Unknown Playlist"),
                "description": entity.get("description"),
                "owner_name": entity.get("subtitle", "unknown"),
                "image_url": image_url,
            }

            # Build tracks from embed
            access_token = parsed["access_token"]
            track_list = entity.get("trackList", [])
            tracks = []
            unplayable_count = 0

            for i, item in enumerate(track_list):
                track_uri = item.get("uri", "")
                spotify_track_id = track_uri.split(":")[-1] if ":" in track_uri else ""

                is_playable = item.get("isPlayable", False)
                if not is_playable:
                    unplayable_count += 1

                track = {
                    "spotify_track_id": spotify_track_id,
                    "title": item.get("title", "Unknown"),
                    "artist": item.get("subtitle", "Unknown"),
                    "album": None,
                    "duration_ms": item.get("duration"),
                    "position": i,
                    "added_at_spotify": None,
                    "is_available": is_playable and not item.get("isNineteenPlus", False),
                }
                tracks.append(track)

            if unplayable_count > 0:
                logger.info(
                    "Excluded %d unplayable tracks from playlist %s", unplayable_count, playlist_id
                )

            # Paginate via API if the embed only shows partial tracks
            embed_track_count = len(track_list)
            if embed_track_count >= 50 and access_token:
                logger.info(
                    "Embed shows %d tracks for %s, attempting API pagination with access token",
                    embed_track_count, playlist_id,
                )
                additional_tracks = await _fetch_tracks_via_api(
                    playlist_id, access_token, embed_track_count
                )
                tracks.extend(additional_tracks)

            return metadata, tracks

    except Exception as e:
        logger.error("Error fetching embed data for playlist %s: %s", playlist_id, e)
        return None


async def sync_playlist(playlist_id: str) -> tuple[Optional[dict], list[dict]]:
    """Sync a playlist: returns (metadata, tracks).
    Makes a single embed request to get both metadata and tracks.
    """
    result = await _fetch_embed(playlist_id)
    if result:
        metadata, tracks = result
    else:
        metadata = None
        tracks = []

    # Build fallback metadata if embed succeeded for tracks but not metadata
    if metadata is None and tracks:
        metadata = {
            "name": f"Playlist {playlist_id[:8]}",
            "description": None,
            "owner_name": "unknown",
            "image_url": None,
        }

    return metadata, tracks
