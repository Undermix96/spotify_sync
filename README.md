# Spotify Sync 🎵

![GitHub release (latest by date)](https://img.shields.io/github/v/release/undermix/spotify_sync)
![License](https://img.shields.io/github/license/undermix/spotify_sync)
![Docker Pulls](https://img.shields.io/docker/pulls/undermix/spotify_sync)

**Spotify Sync** is a self-hosted Docker container that syncs your public Spotify playlists locally as **lossless audio files** and generates Navidrome-compatible `.m3u8` playlist files.

It integrates with **slskd** (Soulseek), **Prowlarr** and **qBittorrent** to automatically search, download, and organize your music in a structured library — all managed through a clean web UI.

---

## Architecture Overview

```
Spotify (public playlist)
        │
        ▼
  ┌─────────────────┐
  │   Spotify Sync  │  ── SQLite DB
  │  (FastAPI/Python)│
  └────────┬────────┘
           │
     ┌─────┴──────┬──────────┐
     ▼            ▼          ▼
   slskd     Prowlarr      Navidrome
  (Soulseek)  + qBittorrent  (music player)
     │            │
     └─────┬──────┘
           ▼
    /music/{Artist}/{Album}/
     + /playlists/{name}.m3u8
```

---

## Features

- **Automatic sync** — scheduled sync of Spotify playlists at configurable intervals
- **Lossless only** — searches and downloads FLAC, ALAC, WAV, AIFF files
- **Dual search engine** — slskd (primary) → Prowlarr + qBittorrent (fallback)
- **Smart deduplication** — checks disk before downloading, never redownloads existing tracks
- **Playlist preservation** — maintains Spotify track order in generated `.m3u8` files
- **Track removal awareness** — tracks removed from Spotify are kept on disk but removed from playlists
- **Organized library** — `/music/{Artist}/{Album}/{TrackNumber} - {Title}.{ext}`
- **Web UI** — manage everything from a clean *arr-style interface (no login required for LAN use)
- **Navidrome compatible** — point Navidrome to `/music` and `/playlists` for instant playback
- **Reverse proxy ready** — supports `X-Forwarded-*` headers for HTTPS setups

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) + [Portainer](https://www.portainer.io/) (or Docker Compose)
- Running container: [slskd](https://github.com/slskd/slskd) (Soulseek client with API enabled)
- Running container: [Prowlarr](https://github.com/Prowlarr/Prowlarr) + [qBittorrent](https://www.qbittorrent.org/)
- (Optional) [Navidrome](https://www.navidrome.org/) for music playback

---

## Quick Start

### 1. Pull the image

```bash
docker pull undermix/spotify_sync:latest
```

### 2. Create `docker-compose.yml`

```yaml
version: "3.8"

services:
  spotify-sync:
    image: undermix/spotify_sync:latest
    container_name: spotify-sync
    ports:
      - "8000:8000"
    volumes:
      - /path/to/music:/music
      - /path/to/playlists:/playlists
      - /path/to/db:/app/data
    environment:
      - TZ=Europe/Rome
      - SPM_SLSKD_URL=http://192.168.1.100:5030
      - SPM_SLSKD_API_KEY=your-slskd-api-key
      - SPM_PROWLARR_URL=http://192.168.1.100:9696
      - SPM_PROWLARR_API_KEY=your-prowlarr-api-key
      - SPM_QBITTORRENT_URL=http://192.168.1.100:8080
      - SPM_QBITTORRENT_USERNAME=admin
      - SPM_QBITTORRENT_PASSWORD=adminadmin
      - SPM_MUSIC_PATH=/music
      - SPM_PLAYLISTS_PATH=/playlists
      - SPM_DB_PATH=/app/data/spm.db
    restart: unless-stopped
```

### 3. Deploy in Portainer

- Go to **Stacks → Add Stack**
- Name: `spotify-sync`
- Paste the `docker-compose.yml` content
- Adjust volume paths and environment variables
- Click **Deploy**

### 4. Access the Web UI

Open `http://your-host-ip:8000` in your browser.

### 5. First-time setup

1. Go to **Settings** → configure slskd, Prowlarr, and qBittorrent URLs and API keys
2. Click **Test Connection** for each service to verify connectivity
3. Go back to **Dashboard** → click **Add Playlist** → paste a Spotify playlist URL
4. Wait for the scheduled sync to run, or click **Sync Now**

---

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SPM_MUSIC_PATH` | `/music` | Path to music library inside container |
| `SPM_PLAYLISTS_PATH` | `/playlists` | Path to generated playlists |
| `SPM_DB_PATH` | `/app/data/spm.db` | SQLite database path |
| `SPM_SLSKD_URL` | `http://slskd:5030` | slskd API base URL |
| `SPM_SLSKD_API_KEY` | — | slskd API key |
| `SPM_PROWLARR_URL` | `http://prowlarr:9696` | Prowlarr API base URL |
| `SPM_PROWLARR_API_KEY` | — | Prowlarr API key |
| `SPM_QBITTORRENT_URL` | `http://qbittorrent:8080` | qBittorrent Web UI URL |
| `SPM_QBITTORRENT_USERNAME` | `admin` | qBittorrent username |
| `SPM_QBITTORRENT_PASSWORD` | `adminadmin` | qBittorrent password |
| `SPM_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Configurable Intervals (via Settings UI)

| Task | Default | Description |
|---|---|---|
| Sync playlists | 6 hours | Refresh playlist data from Spotify |
| Scan disk | 12 hours | Rescan `/music` for new/removed files |
| Search missing | 30 minutes | Search for undownloaded tracks |
| Monitor downloads | 5 minutes | Check progress of active downloads |
| Build playlists | 15 minutes | Regenerate `.m3u8` files |
| Cleanup queue | 1 hour | Remove stale download entries |

---

## Navidrome Integration

To use Navidrome with Spotify Sync:

1. Point Navidrome's `MusicFolder` to the same `/music` volume
2. Point Navidrome's playlists path to the same `/playlists` volume (or configure a symlink)
3. Navidrome will automatically pick up new `.m3u8` files within minutes

---

## Supported Audio Formats

Spotify Sync only searches for **lossless** formats:

- FLAC (`.flac`)
- ALAC (`.m4a`)
- WAV (`.wav`)
- AIFF (`.aiff`)

---

## Development

### Build from source

```bash
git clone https://github.com/undermix/spotify_sync.git
cd spotify_sync
./build.sh          # Build latest
./build.sh v1.0.0   # Tagged release
```

### Project structure

```
spotify_sync/
├── backend/            # Python FastAPI application
│   ├── app/
│   │   ├── main.py     # Application entrypoint
│   │   ├── config.py   # Configuration via env vars
│   │   ├── database.py # SQLAlchemy async setup
│   │   ├── models/     # ORM models
│   │   ├── schemas/    # Pydantic schemas
│   │   ├── routers/    # API endpoints
│   │   ├── services/   # Business logic
│   │   ├── scheduler.py# Task scheduler
│   │   └── utils/      # Helpers
│   └── requirements.txt
├── frontend/           # React + Mantine UI
│   └── src/
│       ├── pages/      # Page components
│       ├── components/ # Reusable components
│       ├── hooks/      # React hooks
│       └── api/        # API client
├── Dockerfile
├── docker-compose.yml
├── build.sh
├── .env.example
└── README.md
```

---

## Troubleshooting

### "No tracks found" after adding a playlist
- Ensure the Spotify playlist is **public** (not private, not unlisted)
- Check the Spotify embed API is reachable from inside the container

### Downloads stuck
- Verify slskd is running and accessible at the configured URL
- Check qBittorrent Web UI is enabled and credentials are correct
- Look at the container logs: `docker logs spotify-sync`

### Empty playlists in Navidrome
- Ensure Navidrome has read access to the `/playlists` volume
- Check that the playlist files have `.m3u8` extension and valid content

---

## License

MIT License — see [LICENSE](LICENSE).

---

## Credits

Built with [FastAPI](https://fastapi.tiangolo.com/), [React](https://react.dev/), [Mantine](https://mantine.dev/), [SQLAlchemy](https://www.sqlalchemy.org/), and lots of ☕.