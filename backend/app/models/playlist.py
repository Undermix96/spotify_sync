import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    spotify_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(512), nullable=False)
    description = Column(String(2048), nullable=True)
    image_url = Column(String(2048), nullable=True)
    owner_name = Column(String(255), nullable=True)
    track_count = Column(Integer, default=0)
    downloaded_count = Column(Integer, default=0)
    last_synced = Column(DateTime, nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    tracks = relationship("PlaylistTrack", back_populates="playlist", cascade="all, delete-orphan")


class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False)
    spotify_track_id = Column(String(255), nullable=False)
    title = Column(String(512), nullable=False)
    artist = Column(String(512), nullable=False)
    album = Column(String(512), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    position = Column(Integer, nullable=False)
    is_available = Column(Boolean, default=True)
    added_at_spotify = Column(DateTime, nullable=True)
    removed_from_spotify = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    playlist = relationship("Playlist", back_populates="tracks")

    __table_args__ = (
        UniqueConstraint("playlist_id", "spotify_track_id", "position", name="uq_playlist_track_pos"),
    )