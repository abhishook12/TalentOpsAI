"""
ai_models.py — SQLAlchemy Models for TalentOps AI Operating System & Governance.

Provides enterprise-grade AI governance, audit logging, human feedback collection,
evidence provenance trails, and calibrated autonomy configurations in compliance
with Google PAIR, IBM Explainability, and NIST Trustworthy AI standards.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Text,
    Float,
    TIMESTAMP,
    ForeignKey,
)
from sqlalchemy.sql import func
from ..database import Base


class AIAuditLog(Base):
    """Forensic log of all AI inferences, actions, and model routing decisions."""
    __tablename__ = "ai_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action_type = Column(String(64), nullable=False, index=True)       # e.g., NATURAL_LANGUAGE_QUERY, MATCH_EXPLANATION
    model_name = Column(String(64), default="gemini-2.5-flash", index=True)
    model_version = Column(String(32), default="2026.09.1", index=True)
    prompt_hash = Column(String(64), nullable=True, index=True)
    input_payload = Column(Text, nullable=True)                        # Truncated or structured JSON input
    output_payload = Column(Text, nullable=True)                       # Structured JSON output
    confidence_score = Column(Float, default=1.0)
    latency_ms = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)


class AIFeedback(Base):
    """Human-in-the-loop recruiter feedback on AI decisions for supervised alignment."""
    __tablename__ = "ai_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    entity_type = Column(String(32), nullable=False, index=True)       # candidate, company, search, recommendation
    entity_id = Column(String(64), nullable=False, index=True)
    is_positive = Column(Boolean, nullable=False)                      # True = Useful, False = Incorrect
    feedback_category = Column(String(64), nullable=True)              # WRONG_SENIORITY, WRONG_COMPANY, OUTDATED, etc.
    user_notes = Column(Text, nullable=True)
    original_data = Column(Text, nullable=True)                        # Snapshot of what AI claimed
    corrected_data = Column(Text, nullable=True)                       # Recruiter's corrected values
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)


class AIEvidenceRecord(Base):
    """Structured evidence and provenance grounding for every AI conclusion."""
    __tablename__ = "ai_evidence_records"

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(String(64), nullable=False, index=True)
    claim_type = Column(String(64), nullable=False, index=True)        # HIRING_EXPANSION, CAREER_VELOCITY, TECH_STACK
    claim_text = Column(Text, nullable=False)
    confidence = Column(Float, default=0.85)                           # 0.0 - 1.0 calibrated confidence
    provenance_status = Column(String(32), default="OBSERVED")         # VERIFIED, OBSERVED, INFERRED, DERIVED, PREDICTED
    evidence_json = Column(Text, default="[]")                         # JSON array of timestamped corroborating facts
    source_platform = Column(String(64), default="TalentOps Scout")    # LinkedIn, ZoomInfo, Apollo, Desktop Scout
    observed_at = Column(TIMESTAMP, server_default=func.now(), index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


class AIPreference(Base):
    """User and tenant autonomy level configuration and agent permission gates."""
    __tablename__ = "ai_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    autonomy_level = Column(Integer, default=3)                        # 1: Assist, 2: Prepare, 3: Approve, 4: Autonomous
    response_style = Column(String(32), default="concise")             # concise, detailed
    proactive_insights_enabled = Column(Boolean, default=True)
    confidence_threshold = Column(Float, default=0.70)
    permissions_json = Column(Text, default='{"read":true,"analyze":true,"propose":true,"write":false,"enrich":false,"export":true,"message":false}')
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
