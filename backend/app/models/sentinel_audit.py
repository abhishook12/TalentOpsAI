from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base

class SentinelAuditLog(Base):
    __tablename__ = "sentinel_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    recruiter_id = Column(Integer, ForeignKey('recruiters.recruiter_id', ondelete='CASCADE'), nullable=False, index=True)
    field_changed = Column(String(100), nullable=False)
    previous_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    reason = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0)
    timestamp = Column(DateTime, server_default=func.now(), index=True)
