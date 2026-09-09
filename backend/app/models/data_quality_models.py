"""
TalentOps AI - Data Quality & Identity Resolution Database Models
Multi-dimension quality scores, non-destructive identity resolution,
company/domain masters, field-level provenance, and contact history.
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Text,
    TIMESTAMP,
    Float,
    ForeignKey,
    DateTime,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class PersonIdentity(Base):
    """
    Canonical person record in the Knowledge Graph with multi-dimension quality scores.
    """
    __tablename__ = "person_identities"

    id = Column(Integer, primary_key=True, index=True)
    canonical_id = Column(String(64), unique=True, index=True, nullable=False)
    canonical_name = Column(String(200), nullable=False, index=True)
    current_title = Column(String(200), nullable=True)
    current_company = Column(String(255), nullable=True, index=True)
    canonical_profile_url = Column(String(500), nullable=True)
    primary_email = Column(String(200), nullable=True, index=True)
    primary_phone = Column(String(50), nullable=True)
    location = Column(String(255), nullable=True)

    # Multi-Stage Email & Contact Status
    email_status = Column(String(50), default="UNKNOWN")  # DELIVERABLE, RISKY, UNDELIVERABLE, UNKNOWN
    email_syntax_valid = Column(Boolean, default=True)
    email_domain_valid = Column(Boolean, default=True)
    email_mx_valid = Column(Boolean, default=False)
    email_role_type = Column(String(30), default="individual")  # individual, role_account, disposable

    # Multi-Dimension Quality Scores (0.0 - 100.0)
    person_quality_score = Column(Float, default=70.0)
    email_quality_score = Column(Float, default=50.0)
    company_quality_score = Column(Float, default=70.0)
    domain_quality_score = Column(Float, default=70.0)
    identity_confidence = Column(Float, default=0.75)  # 0.0 - 1.0
    freshness_score = Column(Float, default=100.0)
    overall_quality_score = Column(Float, default=75.0)

    # Freshness & Confirmation Timestamps
    observed_at = Column(DateTime, server_default=func.now())
    verified_at = Column(DateTime, nullable=True)
    last_seen_at = Column(DateTime, server_default=func.now())
    last_confirmed_at = Column(DateTime, nullable=True)

    # Governance & Multi-Tenancy
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recruiter_id = Column(Integer, nullable=True, index=True)  # link to legacy recruiter table if mapped
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    contact_history = relationship("PersonContactHistory", back_populates="person", cascade="all, delete-orphan")
    matches = relationship("CandidateIdentityMatch", back_populates="person", cascade="all, delete-orphan")


class CandidateIdentityMatch(Base):
    """
    Non-destructive review queue. Preserves potential identity candidates
    for human-in-the-loop review without destroying uncertain identities.
    """
    __tablename__ = "candidate_identity_matches"

    id = Column(Integer, primary_key=True, index=True)
    canonical_person_id = Column(Integer, ForeignKey("person_identities.id", ondelete="CASCADE"), nullable=False)
    candidate_name = Column(String(200), nullable=False)
    candidate_title = Column(String(200), nullable=True)
    candidate_company = Column(String(255), nullable=True)
    candidate_email = Column(String(200), nullable=True)
    candidate_profile_url = Column(String(500), nullable=True)
    source = Column(String(100), default="scout_edge")
    match_score = Column(Float, default=0.0)  # 0.0 - 1.0
    evidence_json = Column(Text, nullable=True)  # JSON array of matching factors & point values
    status = Column(String(30), default="REVIEW", index=True)  # REVIEW, AUTO_MERGED, APPROVED, REJECTED
    created_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime, nullable=True)

    person = relationship("PersonIdentity", back_populates="matches")


class CompanyMaster(Base):
    """
    Canonical enterprise entity resolving corporate aliases and verified domains.
    """
    __tablename__ = "company_masters"

    id = Column(Integer, primary_key=True, index=True)
    canonical_id = Column(String(64), unique=True, index=True, nullable=False)
    canonical_name = Column(String(255), unique=True, index=True, nullable=False)
    primary_domain = Column(String(255), nullable=True, index=True)
    alternate_domains = Column(Text, nullable=True)  # JSON array of alternate/redirect domains
    email_domains = Column(Text, nullable=True)      # JSON array of corporate email domains
    domain_confidence = Column(Float, default=0.70)
    dns_verified = Column(Boolean, default=False)
    mx_verified = Column(Boolean, default=False)
    industry = Column(String(100), nullable=True)
    employee_count_range = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    aliases = relationship("CompanyAlias", back_populates="company", cascade="all, delete-orphan")


class CompanyAlias(Base):
    """
    Known aliases mapping variant names to the canonical company master.
    """
    __tablename__ = "company_aliases"

    id = Column(Integer, primary_key=True, index=True)
    company_master_id = Column(Integer, ForeignKey("company_masters.id", ondelete="CASCADE"), nullable=False)
    alias_name = Column(String(255), nullable=False, index=True)
    source = Column(String(100), default="system")
    confidence = Column(Float, default=0.90)
    created_at = Column(DateTime, server_default=func.now())

    company = relationship("CompanyMaster", back_populates="aliases")


class PersonContactHistory(Base):
    """
    Temporal contact history. Never deletes old contact info; records valid_from / valid_to.
    """
    __tablename__ = "person_contact_history"

    id = Column(Integer, primary_key=True, index=True)
    person_identity_id = Column(Integer, ForeignKey("person_identities.id", ondelete="CASCADE"), nullable=False)
    contact_type = Column(String(30), nullable=False)  # email, phone, company, title
    contact_value = Column(String(300), nullable=False)
    status = Column(String(30), default="current", index=True)  # current, historical, stale, undeliverable
    valid_from = Column(DateTime, server_default=func.now())
    valid_to = Column(DateTime, nullable=True)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    person = relationship("PersonIdentity", back_populates="contact_history")


class FieldObservation(Base):
    """
    Field-level provenance ledger. Records source, timestamp, and confidence per field.
    """
    __tablename__ = "field_observations"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(30), nullable=False, index=True)  # PERSON, COMPANY
    entity_id = Column(Integer, nullable=False, index=True)
    field_name = Column(String(50), nullable=False, index=True)
    field_value = Column(Text, nullable=True)
    source = Column(String(100), nullable=False)
    confidence = Column(Float, default=0.85)
    observed_at = Column(DateTime, server_default=func.now())


class DataQualityIssue(Base):
    """
    Operational issues surfaced for the Data Quality Center & Remediation Queue.
    """
    __tablename__ = "data_quality_issues"

    id = Column(Integer, primary_key=True, index=True)
    issue_type = Column(String(50), nullable=False, index=True)  # UNDELIVERABLE_EMAIL, STALE_PROFILE, UNCERTAIN_IDENTITY, COMPANY_MISMATCH, DUPLICATE_PERSON
    severity = Column(String(20), default="MEDIUM")  # HIGH, MEDIUM, LOW
    entity_type = Column(String(30), nullable=False)
    entity_id = Column(Integer, nullable=False, index=True)
    description = Column(Text, nullable=False)
    remediation_action = Column(String(100), nullable=True)
    status = Column(String(30), default="OPEN", index=True)  # OPEN, RESOLVED, IGNORED
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime, nullable=True)
