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
    issue_code = Column(String(64), unique=True, index=True, nullable=True)  # DQ-xxxxx
    issue_type = Column(String(50), nullable=False, index=True)  # INVALID_EMAIL, COMPANY_EMAIL_MISMATCH, TIMELINE_CONFLICT, etc.
    problem_type = Column(String(30), default="BAD", index=True)  # BAD, MISSING, SUSPICIOUS, CONFLICTING, STALE, DUPLICATE
    severity = Column(String(20), default="MEDIUM")  # CRITICAL, HIGH, MEDIUM, LOW
    entity_type = Column(String(30), nullable=False)  # PERSON, COMPANY
    entity_id = Column(Integer, nullable=False, index=True)
    field_name = Column(String(50), nullable=True)
    raw_value = Column(Text, nullable=True)
    description = Column(Text, nullable=False)
    remediation_action = Column(String(100), nullable=True)
    evidence_ladder_level = Column(Integer, default=1)  # 1 to 5
    quarantine_id = Column(Integer, nullable=True, index=True)
    status = Column(String(30), default="OPEN", index=True)  # OPEN, QUARANTINED, IN_REPAIR, RESOLVED, DISMISSED
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime, nullable=True)


class QuarantineRecord(Base):
    """
    Hospital isolation room for bad, suspicious, or disputed data.
    Isolates records from downstream production intelligence without destroying data.
    """
    __tablename__ = "quarantine_records"

    id = Column(Integer, primary_key=True, index=True)
    quarantine_id = Column(String(64), unique=True, index=True, nullable=False)  # QRN-xxxxx
    entity_type = Column(String(30), nullable=False, index=True)  # PERSON, COMPANY
    entity_id = Column(Integer, nullable=False, index=True)
    field_name = Column(String(50), default="__RECORD__", nullable=False)
    raw_value = Column(Text, nullable=True)
    quarantine_reason = Column(Text, nullable=False)
    problem_type = Column(String(30), default="BAD", index=True)  # BAD, MISSING, SUSPICIOUS, CONFLICTING, STALE, DUPLICATE
    severity = Column(String(20), default="HIGH")  # CRITICAL, HIGH, MEDIUM, LOW
    status = Column(String(30), default="QUARANTINED", index=True)  # QUARANTINED, UNDER_INVESTIGATION, RELEASED, REPAIRED
    quarantined_at = Column(DateTime, server_default=func.now())
    released_at = Column(DateTime, nullable=True)
    metadata_json = Column(Text, nullable=True)
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)


class DataCorrectionProposal(Base):
    """
    Shadow writes layer. Proposals are generated, validated, and approved
    before ever mutating canonical production rows.
    """
    __tablename__ = "data_correction_proposals"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(String(64), unique=True, index=True, nullable=False)  # PROP-xxxxx
    entity_type = Column(String(30), nullable=False, index=True)  # PERSON, COMPANY
    entity_id = Column(Integer, nullable=False, index=True)
    field_name = Column(String(50), nullable=False, index=True)
    old_value = Column(Text, nullable=True)
    proposed_value = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    evidence_ids = Column(Text, nullable=True)  # JSON array of observation/evidence IDs
    evidence_ladder_level = Column(Integer, default=2)  # 1 to 5
    confidence = Column(Float, default=0.80)  # 0.0 to 1.0
    source = Column(String(100), default="dq_engine")
    category = Column(String(50), default="SAFE_AUTO_FIX", index=True)  # SAFE_AUTO_FIX, VALIDATED_AUTO_FIX, HUMAN_REVIEW
    status = Column(String(30), default="PROPOSED", index=True)  # PROPOSED, VALIDATING, APPROVED, PROMOTED, REJECTED, REVERTED
    batch_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now())
    promoted_at = Column(DateTime, nullable=True)
    reverted_at = Column(DateTime, nullable=True)
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)


class DataChangeAudit(Base):
    """
    Immutable audit ledger answering: Who changed this, why, and what evidence was used?
    """
    __tablename__ = "data_change_audits"

    id = Column(Integer, primary_key=True, index=True)
    change_id = Column(String(64), unique=True, index=True, nullable=False)  # CHANGE-xxxxx
    entity_type = Column(String(30), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    field_name = Column(String(50), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    reason = Column(Text, nullable=False)
    evidence_ids = Column(Text, nullable=True)  # JSON array
    confidence = Column(Float, default=0.90)
    model_version = Column(String(50), default="dq_engine_v3.4")
    rule_version = Column(String(50), default="rule_v1.0")
    actor = Column(String(100), default="DQ_ENGINE")
    reverted = Column(Boolean, default=False)
    batch_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now())


class RepairBatchSnapshot(Base):
    """
    Pre-repair database snapshot enabling safe, lossless rollback of batch cleanups.
    """
    __tablename__ = "repair_batch_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String(64), unique=True, index=True, nullable=False)  # BATCH-xxxxx
    records_count = Column(Integer, default=0)
    snapshot_data = Column(Text, nullable=False)  # JSON map of pre-repair values per record/field
    status = Column(String(30), default="COMMITTED", index=True)  # COMMITTED, ROLLED_BACK
    created_at = Column(DateTime, server_default=func.now())
    rolled_back_at = Column(DateTime, nullable=True)


class DissimilarityBlocklist(Base):
    """
    Dissimilarity Blocklist for Active Learning.
    Stores pairs of entity IDs that human reviewers or system consensus
    have confirmed are distinct individuals/companies, preventing repetitive
    false-positive duplicate proposals.
    """
    __tablename__ = "dissimilarity_blocklist"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(30), default="PERSON", nullable=False, index=True)
    entity_a_id = Column(Integer, nullable=False, index=True)
    entity_b_id = Column(Integer, nullable=False, index=True)
    reason = Column(String(255), default="HUMAN_REJECTED_MERGE")
    created_at = Column(DateTime, server_default=func.now())


class SLAHealthAlert(Base):
    """
    Data Quality SLA Health Alerts and Guardrail Trips.
    Records delivery degradation, quarantine spikes, and campaign auto-pause events.
    """
    __tablename__ = "sla_health_alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_code = Column(String(64), unique=True, index=True, nullable=False)
    tenant_id = Column(Integer, nullable=True, index=True)
    alert_type = Column(String(50), nullable=False, index=True)  # DELIVERABILITY_DROP, QUARANTINE_SPIKE, CAMPAIGN_AUTO_PAUSED
    metric_name = Column(String(50), nullable=False)
    metric_value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    status = Column(String(30), default="TRIGGERED", index=True)  # TRIGGERED, ACKNOWLEDGED, RESOLVED
    message = Column(Text, nullable=False)
    payload_json = Column(Text, nullable=True)
    triggered_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime, nullable=True)


