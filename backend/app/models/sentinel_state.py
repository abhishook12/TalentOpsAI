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

class SentinelPhase4State(Base):
    __tablename__ = "sentinel_phase4_state"
    
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(50), default="Initializing")
    
    # Overall Database Health
    total_recruiters = Column(Integer, default=0)
    total_companies = Column(Integer, default=0)
    unknown_companies = Column(Integer, default=0)
    missing_emails = Column(Integer, default=0)
    missing_phones = Column(Integer, default=0)
    missing_linkedin = Column(Integer, default=0)
    missing_logos = Column(Integer, default=0)
    profiles_below_50 = Column(Integer, default=0)
    profiles_above_90 = Column(Integer, default=0)
    
    # Averages
    avg_confidence = Column(Integer, default=0)
    avg_completeness = Column(Integer, default=0)
    
    # Processing Metrics
    companies_completed = Column(Integer, default=0)
    recruiters_completed = Column(Integer, default=0)
    
    # Current Target
    current_company_name = Column(String, nullable=True)
    current_company_id = Column(Integer, nullable=True)
    current_state = Column(String(50), nullable=True)
    current_batch_count = Column(Integer, default=0)
    
    # Timing
    estimated_completion_hours = Column(Integer, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

