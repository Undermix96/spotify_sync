import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from app.database import Base


class DownloadQueue(Base):
    __tablename__ = "download_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    playlist_track_id = Column(Integer, ForeignKey("playlist_tracks.id", ondelete="SET NULL"), nullable=True)
    source = Column(String(32), nullable=True)
    status = Column(String(32), nullable=False, default="pending", index=True)
    external_id = Column(String(512), nullable=True)
    progress = Column(Float, default=0.0)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)