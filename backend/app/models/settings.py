from sqlalchemy import Column, String, Text
from app.database import Base


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(128), primary_key=True)
    value = Column(Text, nullable=True)