"""
Open-Ended Knowledge Graph & Semantic Intelligence Models.

Represents extensible entities, relationships, signals, and observations
without artificial schema limits.

Entities: PERSON, COMPANY, JOB, LOCATION, EDUCATION, TEAM, DEPARTMENT, SKILL, etc.
Relationships: EMPLOYED_BY, HAS_EMPLOYEE, POSTED_BY, ATTENDED, LOCATED_IN, HAS_SIGNAL, etc.
Signals: HIRING_SIGNAL, STAFFING_SPECIALIZATION, BUSINESS_CERTIFICATION, MARKET_PRESENCE, etc.
Observations: Raw grounded triples before canonical graph promotion.
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, TIMESTAMP, Float, ForeignKey
from sqlalchemy.sql import func
from ..database import Base


class KnowledgeEntity(Base):
    """
    Extensible Canonical Knowledge Entity.
    Can represent a Person, Company, Job, School, Team, Office, or any semantic entity.
    """
    __tablename__ = "knowledge_entities"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type = Column(String(64), nullable=False, index=True)  # PERSON, COMPANY, JOB, EDUCATION, LOCATION, TEAM, etc.
    canonical_name = Column(String(255), nullable=False, index=True)
    primary_identifier = Column(String(255), nullable=True, index=True)  # LinkedIn URL, domain, slug, email
    
    # JSON-encoded dictionary of arbitrary typed attributes (extensible)
    attributes_json = Column(Text, nullable=True)
    aliases_json = Column(Text, nullable=True)  # List of alternate names
    
    # Optional foreign keys to canonical master tables when resolved
    linked_recruiter_id = Column(Integer, ForeignKey("recruiters.recruiter_id", ondelete="SET NULL"), nullable=True, index=True)
    linked_company_id = Column(Integer, ForeignKey("companies.company_id", ondelete="SET NULL"), nullable=True, index=True)

    confidence = Column(Float, default=1.0)
    source_capture_id = Column(String(64), nullable=True)
    source_url = Column(String(500), nullable=True)
    
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class KnowledgeRelationship(Base):
    """
    Extensible Semantic Relationship between two Knowledge Entities.
    e.g. (Subject: Kelsei Martinez) --[EMPLOYED_BY]--> (Object: Premier Staffing Solution LLC)
    """
    __tablename__ = "knowledge_relationships"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    subject_entity_id = Column(Integer, ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False, index=True)
    predicate = Column(String(64), nullable=False, index=True)  # EMPLOYED_BY, HAS_EMPLOYEE, POSTED_BY, ATTENDED, LOCATED_IN, etc.
    object_entity_id = Column(Integer, ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Relationship context / attributes (e.g. title="VP of Staffing", dates="2023-Present", is_current=True)
    attributes_json = Column(Text, nullable=True)
    is_current = Column(Boolean, default=True)
    
    confidence = Column(Float, default=1.0)
    source_capture_id = Column(String(64), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)


class KnowledgeSignal(Base):
    """
    Extensible Staffing, Hiring, or Business Intelligence Signal.
    e.g. "Hiring 15 Java Developers", "Certified Women-Owned Staffing Supplier"
    """
    __tablename__ = "knowledge_signals"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    entity_id = Column(Integer, ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=True, index=True)
    signal_type = Column(String(64), nullable=False, index=True)  # HIRING_SIGNAL, STAFFING_SPECIALIZATION, BUSINESS_CERTIFICATION, etc.
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Flexible payload with arbitrary signal parameters
    payload_json = Column(Text, nullable=True)
    
    confidence = Column(Float, default=1.0)
    source_capture_id = Column(String(64), nullable=True)
    source_url = Column(String(500), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)


class SemanticObservation(Base):
    """
    Raw Extensible Semantic Triple Observation from Visual or DOM capture.
    Stores observations before canonical knowledge graph promotion.
    """
    __tablename__ = "semantic_observations"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String(64), index=True, nullable=False)
    discovery_id = Column(String(64), index=True, nullable=False)
    capture_id = Column(String(64), nullable=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    subject = Column(String(255), nullable=False)
    predicate = Column(String(64), nullable=False, index=True)  # EMPLOYED_BY, LOCATED_IN, HAS_ATTRIBUTE, etc.
    object_val = Column(String(500), nullable=False)
    semantic_type = Column(String(64), default='EXTENSIBLE_TYPED_OBSERVATION', index=True)
    
    context = Column(String(255), nullable=True)
    attributes_json = Column(Text, nullable=True)
    
    confidence = Column(Float, default=1.0)
    processing_status = Column(String(30), default='pending', index=True)  # pending, promoted, rejected
    decision = Column(String(30), nullable=True)
    
    source_url = Column(String(500), nullable=True)
    source_page_title = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)
