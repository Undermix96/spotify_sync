# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /build/frontend

COPY frontend/package.json ./
RUN yarn install

COPY frontend/ .
RUN yarn build

# Stage 2: Build backend + serve static
FROM python:3.12-slim

LABEL org.opencontainers.image.title="Spotify Sync"
LABEL org.opencontainers.image.description="Sync Spotify playlists locally as lossless audio files with Navidrome-compatible M3U8 playlists"
LABEL org.opencontainers.image.source="https://github.com/undermix/spotify_sync"
LABEL org.opencontainers.image.authors="undermix"
LABEL org.opencontainers.image.vendor="undermix"
LABEL org.opencontainers.image.licenses="MIT"

ARG BUILD_DATE
ARG VCS_REF
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.revision="${VCS_REF}"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

COPY --from=frontend-builder /build/frontend/dist /app/static

RUN mkdir -p /music /playlists /app/data

VOLUME ["/music", "/playlists", "/app/data"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

ENTRYPOINT ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=${FORWARDED_ALLOW_IPS:-172.17.0.1}"]
