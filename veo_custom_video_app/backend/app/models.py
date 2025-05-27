from datetime import datetime

from sqlalchemy import (Column, DateTime, ForeignKey, Integer, JSON, String,
                        Text)
# Removed: from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Import Base from database.py
from veo_custom_video_app.backend.database import Base


class Agency(Base):
    __tablename__ = "agencies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Configure cascading deletes: if an Agency is deleted, its Visions are deleted.
    visions = relationship("Vision", back_populates="agency", cascade="all, delete-orphan")


class Vision(Base):
    __tablename__ = "visions"

    id = Column(Integer, primary_key=True, index=True)
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=False) # Implicit ON DELETE RESTRICT by default
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    veo_parameters = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Configure cascading deletes: if a Vision is deleted, its Videos are deleted.
    videos = relationship("Video", back_populates="vision", cascade="all, delete-orphan")
    agency = relationship("Agency", back_populates="visions")


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    vision_id = Column(Integer, ForeignKey("visions.id"), nullable=False) # Implicit ON DELETE RESTRICT by default
    veo_video_id = Column(String, nullable=True)
    status = Column(String, default="pending")
    download_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vision = relationship("Vision", back_populates="videos")
