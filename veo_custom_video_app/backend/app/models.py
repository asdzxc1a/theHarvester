from datetime import datetime

from sqlalchemy import (Column, DateTime, ForeignKey, Integer, JSON, String,
                        Text)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Agency(Base):
    __tablename__ = "agencies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    visions = relationship("Vision", back_populates="agency")


class Vision(Base):
    __tablename__ = "visions"

    id = Column(Integer, primary_key=True, index=True)
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    veo_parameters = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    videos = relationship("Video", back_populates="vision")
    agency = relationship("Agency", back_populates="visions")


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    vision_id = Column(Integer, ForeignKey("visions.id"), nullable=False)
    veo_video_id = Column(String, nullable=True)
    status = Column(String, default="pending")
    download_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vision = relationship("Vision", back_populates="videos")
