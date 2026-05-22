"""FastAPI application entrypoint."""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import config
from app.database import init_db
from app.scheduler import setup_scheduler, stop_scheduler

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup/shutdown."""
    logger.info("Starting Spotify Sync...")
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.exception("Failed to initialize database: %s", e)
        sys.exit(1)

    try:
        await setup_scheduler()
        logger.info("Scheduler started")
    except Exception as e:
        logger.exception("Failed to setup scheduler: %s", e)
        sys.exit(1)

    yield

    try:
        await stop_scheduler()
        logger.info("Spotify Sync shutdown complete")
    except Exception as e:
        logger.exception("Error during scheduler shutdown: %s", e)


app = FastAPI(
    title="Spotify Sync",
    description="Sync Spotify playlists locally as lossless audio with Navidrome-compatible M3U8 playlists",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for LAN use
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
from app.routers import playlists, downloads, local, settings, stats

app.include_router(playlists.router)
app.include_router(downloads.router)
app.include_router(local.router)
app.include_router(settings.router)
app.include_router(stats.router)


# Health endpoint
@app.get("/api/health")
async def health():
    return {"status": "ok"}


# Serve frontend static files
try:
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
    logger.info("Frontend static files mounted at /")
except Exception as e:
    logger.warning("Could not mount static files: %s. Frontend will not be served.", e)