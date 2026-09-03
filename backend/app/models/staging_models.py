"""
Discovery Staging & Batch Intelligence Layer — Database Models.

- DiscoveryStaging: Raw observation bucket. Every scraper result enters here first.
- ResolvedPerson: Identity resolution output. Accumulated observations merged into one person.

Flow: Extension -> DiscoveryStaging (pending) -> Batch Processor -> ResolvedPerson -> Master recruiters table
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, TIMESTAMP, Float, ForeignKey
from sqlalchemy.sql import func
from ..database import Base


class DiscoveryStaging(Base):
    """
    Raw observation bucket. Every scraper result enters here first.
    """
    __tablename__ = "discovery_staging"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String(64), index=True, nullable=False)
    discovery_id = Column(String(64), unique=True, index=True, nullable=False)
    session_id = Column(String(64), index=True, nullable=True)
    device_id = Column(String(64), index=True, nullable=False)
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    raw_name = Column(String(200), nullable=True)
    raw_title = Column(String(200), nullable=True)
    raw_company = Column(String(255), nullable=True)
    raw_email = Column(String(200), nullable=True)
    raw_phone = Column(String(50), nullable=True)
    raw_linkedin = Column(String(300), nullable=True)
    raw_location = Column(String(255), nullable=True)
    source_url = Column(String(500), nullable=True)
    source_page_title = Column(String(255), nullable=True)
    capture_id = Column(String(64), nullable=True)
    extraction_source = Column(String(50), default='visual_dom_fusion')
    visual_change_score = Column(String(20), nullable=True)
    dom_confidence = Column(Integer, default=0)
    processing_status = Column(String(30), default='pending', index=True)
    resolved_person_id = Column(Integer, ForeignKey("resolved_persons.id", ondelete="SET NULL"), nullable=True, index=True)
    decision = Column(String(30), nullable=True)
    decision_reason = Column(Text, nullable=True)
    identity_confidence = Column(Float, default=0.0)
    quality_score = Column(Integer, default=0)
    
    # Progressive Profile & Metadata Fields
    education = Column(String(255), nullable=True)
    followers_count = Column(String(50), nullable=True)
    connections_count = Column(String(50), nullable=True)
    about_summary = Column(Text, nullable=True)
    previous_company = Column(String(255), nullable=True)
    experience_history = Column(Text, nullable=True)  # JSON-encoded array of past roles & dates
    skills = Column(Text, nullable=True)  # JSON-encoded array of skills
    field_provenance = Column(Text, nullable=True)  # JSON mapping of field -> capture_id
    metadata_json = Column(Text, nullable=True)  # Badges, signals, firmographics, channels

    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)
    processed_at = Column(TIMESTAMP, nullable=True)


class ResolvedPerson(Base):
    """
    Identity resolution output. Accumulated observations merged into one person.
    """
    __tablename__ = "resolved_persons"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    canonical_name = Column(String(200), nullable=False)
    current_title = Column(String(200), nullable=True)
    current_company = Column(String(255), nullable=True)
    previous_title = Column(String(200), nullable=True)
    previous_company = Column(String(255), nullable=True)
    primary_email = Column(String(200), nullable=True)
    primary_phone = Column(String(50), nullable=True)
    linkedin_url = Column(String(300), nullable=True)
    location = Column(String(255), nullable=True)
    
    # Progressive Profile & Rich Metadata
    education = Column(String(255), nullable=True)
    followers_count = Column(String(50), nullable=True)
    connections_count = Column(String(50), nullable=True)
    about_summary = Column(Text, nullable=True)
    experience_history = Column(Text, nullable=True)  # JSON-encoded array of past roles & dates
    skills = Column(Text, nullable=True)
    field_provenance = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)

    identity_confidence = Column(Float, default=0.0)
    observation_count = Column(Integer, default=1)
    first_seen_at = Column(TIMESTAMP, server_default=func.now())
    last_seen_at = Column(TIMESTAMP, server_default=func.now())
    recruiter_id = Column(Integer, ForeignKey("recruiters.recruiter_id", ondelete="SET NULL"), nullable=True, index=True)
    name_confidence = Column(Integer, default=0)
    title_confidence = Column(Integer, default=0)
    company_confidence = Column(Integer, default=0)
    email_confidence = Column(Integer, default=0)
    phone_confidence = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
