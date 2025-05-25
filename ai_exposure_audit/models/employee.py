from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.db import Base

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    profile_url = Column(String, nullable=True, unique=True, index=True)
    full_name = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
    raw_data = Column(JSON, nullable=True) # Using JSON for flexibility
    last_scraped_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client", back_populates="employees")
    audit_findings = relationship("AuditFinding", back_populates="employee")
