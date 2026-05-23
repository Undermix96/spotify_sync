# Spotify Sync — Agents Documentation

## Project Overview

Spotify Sync is a self-hosted Docker container that synchronizes public Spotify playlists with a local lossless audio library. It maintains a SQLite database of playlists, tracks, and local files, and orchestrates downloads via **slskd** (primary) and **Prowlarr + qBittorrent** (fallback). Generated `.m3u8` playlists are compatible with Navidrome.

## Technology Stack

| Layer | Technology | Justification |
|---|---|---|
| **Backend** | Python 3.12 + FastAPI | `slskd-api` is a pip package; mutagen for audio metadata; APScheduler async; mature audio ecosystem |
| **Database** | SQLite via SQLAlchemy 2.0 + aiosqlite | Self-contained, zero external dependencies |
| **Frontend** | React 18 + TypeScript + Mantine UI v7 | *arr-style component library with dark theme |
| **Build tool** | Vite | Fast frontend builds |
| **Task scheduler** | APScheduler (async) | Lightweight, runtime-configurable intervals |
| **Container** | Docker (single-stage Python slim) | Pre-built frontend, deployable via Portainer |

## Project Structure

```
spotify_sync/
├── .gitignore
├── LICENSE
├── .env.example
├── README.md
├── agents.md
├── build.sh
├── Dockerfile
├── docker-compose.yml
├── data/                          # Volume mounts (runtime)
│   ├── music/                     # Organized lossless files
│   ├── playlists/                 # Generated .m3u8 files
│   └── db/                        # SQLite database
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py                # FastAPI app, lifespan, CORS
│       ├── config.py              # Pydantic Settings from env vars
│       ├── database.py            # SQLAlchemy async engine + session
│       ├── models/
│       │   ├── __init__.py
│       │   ├── playlist.py        # Playlist, PlaylistTrack ORM
│       │   ├── local_track.py     # Disk-scanned track ORM
│       │   ├── download_queue.py  # Download queue ORM
│       │   └── settings.py        # Key-value settings ORM
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── playlist.py
│       │   ├── download.py
│       │   ├── settings.py
│       │   └── stats.py
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── playlists.py
│       │   ├── downloads.py
│       │   ├── local.py
│       │   ├── settings.py
│       │   └── stats.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── spotify.py         # Public playlist extraction
│       │   ├── scanner.py         # Disk scan → local_tracks
│       │   ├── searcher.py        # Orchestrator: slskd → prowlarr
│       │   ├── slskd.py           # slskd-api wrapper
│       │   ├── prowlarr.py        # Prowlarr REST client
│       │   ├── qbittorrent.py     # qBittorrent Web API client
│       │   ├── downloader.py      # Download monitor + import
│       │   ├── organizer.py       # File move/rename to /music/
│       │   └── playlist_builder.py# .m3u8 generation
│       ├── scheduler.py           # APScheduler tasks
│       └── utils/
│           ├── __init__.py
│           └── audio.py           # mutagen metadata extraction
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── tsconfig.node.json
    ├── vite.config.ts
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── api/
        │   ├── client.ts
        │   ├── playlists.ts
        │   ├── downloads.ts
        │   ├── local.ts
        │   └── settings.ts
        ├── components/
        │   ├── Layout/
        │   │   ├── AppShell.tsx
        │   │   └── Navbar.tsx
        │   ├── PlaylistCard.tsx
        │   ├── TrackTable.tsx
        │   ├── DownloadBadge.tsx
        │   ├── StatusBadge.tsx
        │   └── AddPlaylistModal.tsx
        ├── pages/
        │   ├── Dashboard.tsx
        │   ├── PlaylistDetail.tsx
        │   ├── LocalPlaylists.tsx
        │   ├── LocalPlaylistDetail.tsx
        │   ├── Downloads.tsx
        │   └── Settings.tsx
        ├── hooks/
        │   ├── usePlaylists.ts
        │   ├── useDownloads.ts
        │   └── useSettings.ts
        └── styles/
            └── theme.ts
```

## Database Schema (SQLite)

### playlists
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-generated |
| spotify_id | TEXT UNIQUE | Spotify playlist ID |
| name | TEXT | Playlist name |
| description | TEXT | Nullable |
| image_url | TEXT | Cover image |
| owner_name | TEXT | Spotify owner |
| track_count | INTEGER | Tracks on Spotify |
| downloaded_count | INTEGER | Tracks successfully downloaded |
| last_synced | DATETIME | Last Spotify sync |
| enabled | BOOLEAN | Monitoring active |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### playlist_tracks
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | |
| playlist_id | FK → playlists.id | |
| spotify_track_id | TEXT | Unique track ID |
| title | TEXT | |
| artist | TEXT | |
| album | TEXT | |
| duration_ms | INTEGER | |
| position | INTEGER | Order in playlist (0-based) |
| is_available | BOOLEAN | Still present on Spotify |
| added_at_spotify | DATETIME | |
| removed_from_spotify | BOOLEAN | Removed from playlist but kept on disk |
| created_at | DATETIME | |
| updated_at | DATETIME | |

UNIQUE(playlist_id, spotify_track_id, position)

### local_tracks
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | |
| file_path | TEXT UNIQUE | Absolute path on disk |
| artist | TEXT | From audio tags |
| album | TEXT | From audio tags |
| title | TEXT | From audio tags |
| track_number | INTEGER | From audio tags |
| duration_ms | INTEGER | |
| format | TEXT | flac, alac, wav, aiff |
| file_size | INTEGER | Bytes |
| checksum | TEXT | SHA256 (first 64KB) |
| last_seen | DATETIME | Last disk scan |
| created_at | DATETIME | |

### download_queue
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | |
| playlist_track_id | FK → playlist_tracks.id | |
| source | TEXT | 'slskd' or 'torrent' |
| status | TEXT | pending, searching, queued, downloading, completed, failed, not_found |
| external_id | TEXT | slskd search ID / torrent hash |
| progress | FLOAT | 0-100 |
| retry_count | INTEGER | |
| max_retries | INTEGER | Default 3 |
| error_message | TEXT | |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### settings
| Column | Type | Description |
|---|---|---|
| key | TEXT PK | |
| value | TEXT | JSON-encoded |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | /api/health | Health check (used by Docker HEALTHCHECK) |
| GET | /api/playlists | List monitored playlists |
| POST | /api/playlists | Add playlist (body: {url}) |
| GET | /api/playlists/{id} | Playlist detail + tracks |
| DELETE | /api/playlists/{id} | Remove from monitoring |
| POST | /api/playlists/{id}/sync | Force sync with Spotify |
| GET | /api/downloads | Download queue (filterable) |
| POST | /api/downloads/{id}/retry | Retry failed download |
| POST | /api/downloads/{id}/cancel | Cancel download |
| GET | /api/local/tracks | Scanned local tracks |
| GET | /api/local/playlists | Generated .m3u8 files |
| GET | /api/local/playlists/{name} | Content of .m3u8 file |
| GET | /api/settings | All settings |
| PUT | /api/settings | Update settings (partial) |
| GET | /api/stats | Dashboard statistics |
| POST | /api/settings/test-slskd | Test slskd connection |
| POST | /api/settings/test-prowlarr | Test Prowlarr connection |
| POST | /api/settings/test-qbittorrent | Test qBittorrent connection |

## Data Flow

```
1. User adds Spotify playlist URL via Web UI
2. POST /api/playlists → spotify.py extracts metadata + tracks
   → INSERT/UPDATE playlists + playlist_tracks
3. Scheduler (search_missing): every 30 min
   a. Query unsynced playlist_tracks (no local_tracks match, no active download)
   b. searcher.py → slskd.py (primary) → if not found → prowlarr.py → qbittorrent.py
   c. INSERT download_queue
4. Scheduler (monitor_downloads): every 5 min
   a. Query download_queue (status=queued/downloading)
   b. downloader.py → check slskd / qBittorrent status
   c. If completed → organizer.py → move to /music/{Artist}/{Album}/
   d. Update download_queue status + local_tracks
5. Scheduler (build_playlists): every 15 min
   a. For each active playlist → match playlist_tracks ⇔ local_tracks
   b. playlist_builder.py → generate /playlists/{name}.m3u8
6. Scheduler (scan_disk): every 12 hours
   a. scanner.py → walk /music/ → upsert local_tracks, purge missing
7. Scheduler (sync_playlists): every 6 hours
   a. spotify.py → re-fetch each playlist → diff additions/removals
8. Scheduler (cleanup_queue): every 1 hour
   a. Remove not_found entries older than 7 days
```

## External Integrations

### Spotify (public, no auth)
- Endpoint: `https://open.spotify.com/embed/playlist/{id}`
- Data: JSON embedded in HTML page with full track list
- No API key required, rate-limited by IP
- Only public playlists supported

### slskd (Soulseek)
- Protocol: REST API (pip package: `slskd-api`)
- Config: URL + API key
- Priority: Primary search source
- Only lossless results (FLAC)
- Endpoints: search, download, status

### Prowlarr
- Protocol: REST API v1
- Config: URL + API key
- Role: Fallback indexer aggregator
- Endpoints: search, indexer list

### qBittorrent
- Protocol: Web API v2
- Config: URL + username + password
- Role: Torrent download client
- Endpoints: login, add torrent, torrent info, delete

## Scheduler Tasks

All intervals are configurable via Settings UI (APScheduler reschedules at runtime).

| Task key | Default | Description |
|---|---|---|
| sync_playlists | 21600s (6h) | Fetch current state from Spotify |
| scan_disk | 43200s (12h) | Rescan /music/ for file changes |
| search_missing | 1800s (30m) | Search for undownloaded tracks |
| monitor_downloads | 300s (5m) | Check active download progress |
| build_playlists | 900s (15m) | Regenerate .m3u8 files |
| cleanup_queue | 3600s (1h) | Remove stale queue entries |

## Reverse Proxy Compatibility

The FastAPI app uses `uvicorn` with `--proxy-headers` enabled (via `--forwarded-allow-ips=${FORWARDED_ALLOW_IPS:-172.17.0.1}`), which respects `X-Forwarded-For`, `X-Forwarded-Proto`, and `X-Forwarded-Host` headers. The default value `172.17.0.1` is the Docker bridge gateway IP; set the `FORWARDED_ALLOW_IPS` environment variable to `*` to trust all IPs (e.g. behind a reverse proxy). The backend also configures `root_path` support for sub-path proxying. No SSL termination inside the container.

## Development Build Process

```bash
# 1. Build frontend
cd frontend && yarn install && yarn build && cd ..

# 2. Build Docker image
docker build -t undermix/spotify_sync:latest .

# 3. Push to Docker Hub
docker push undermix/spotify_sync:latest
```

Alternatively, use `./build.sh [tag]`.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| SPM_MUSIC_PATH | **Yes** | — | Music library root |
| SPM_PLAYLISTS_PATH | No | /playlists | M3U8 output path |
| SPM_DB_PATH | No | /app/data/spm.db | SQLite file path |
| SPM_SLSKD_URL | No | http://slskd:5030 | slskd API base URL |
| SPM_SLSKD_API_KEY | **Yes** | — | slskd API key |
| SPM_PROWLARR_URL | No | http://prowlarr:9696 | Prowlarr API base URL |
| SPM_PROWLARR_API_KEY | **Yes** | — | Prowlarr API key |
| SPM_QBITTORRENT_URL | No | http://qbittorrent:8080 | qBittorrent Web UI URL |
| SPM_QBITTORRENT_USERNAME | No | admin | qBittorrent user |
| SPM_QBITTORRENT_PASSWORD | **Yes** | — | qBittorrent pass |
| FORWARDED_ALLOW_IPS | No | 172.17.0.1 | Comma-separated IPs allowed to set X-Forwarded-* headers |
| SPM_LOG_LEVEL | No | INFO | DEBUG, INFO, WARNING, ERROR |

## Error Handling Strategy

- **Track not found**: `download_queue.status = 'not_found'`, retry via `search_missing` scheduler (re-checked each cycle up to `max_retries`)
- **Slow downloads**: `downloader.py` uses timeout thresholds per source (configurable); marks as `failed` if no progress after threshold
- **Manual torrent removal**: `downloader.py` checks if torrent still exists in qBittorrent; if missing and files not in `/music/`, marks as `failed`
- **Metadata extraction failure**: `organizer.py` falls back to filename parsing; logs warning
- **Disk full**: `organizer.py` catches OSError and leaves entry in `downloading` status for retry
- **API down**: Each service wrapper catches connection errors, logs, and returns empty result (no crash)