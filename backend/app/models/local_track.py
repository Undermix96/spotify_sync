import datetime
from sqlalchemy import Column, Integer, String, DateTime, BigInteger
from app.database import Base


class LocalTrack(Base):
    __tablename__ = "local_tracks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_path = Column(String(2048), unique=True, nullable=False)
    artist = Column(String(512), nullable=True)
    album = Column(String(512), nullable=True)
    title = Column(String(512), nullable=True)
    track_number = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    format = Column(String(16), nullable=True)
    file_size = Column(BigInteger, nullable=True)
    checksum = Column(String(64), nullable=True)
    last_seen = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)