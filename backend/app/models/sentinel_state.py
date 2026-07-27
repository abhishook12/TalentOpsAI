from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database import Base

class SentinelState(Base):
    __tablename__ = "sentinel_state"
    
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(50), default="Idle") # Idle, Running, Paused
    total_profiles = Column(Integer, default=0)
    profiles_analyzed = Column(Integer, default=0)
    profiles_repaired = Column(Integer, default=0)
    current_task_description = Column(String(255), nullable=True)
    last_processed_id = Column(Integer, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
