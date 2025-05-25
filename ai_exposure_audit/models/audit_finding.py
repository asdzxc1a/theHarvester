import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.db import Base

class FindingSeverity(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class FindingConfidence(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class FindingStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"
    FALSE_POSITIVE = "false_positive"

class AuditFinding(Base):
    __tablename__ = "audit_findings"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    
    finding_type = Column(String, nullable=False, index=True) # e.g., "AI_related_job_title"
    description = Column(Text, nullable=False)
    
    severity = Column(SAEnum(FindingSeverity), nullable=True)
    confidence = Column(SAEnum(FindingConfidence), nullable=True)
    
    details = Column(JSON, nullable=True) # For keywords matched, snippets, etc.
    status = Column(SAEnum(FindingStatus), nullable=False, default=FindingStatus.PENDING, index=True)
    
    auditor_notes = Column(Text, nullable=True)
    found_at = Column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee", back_populates="audit_findings")
