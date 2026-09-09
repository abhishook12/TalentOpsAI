"""
intelligence_models.py — 4-Tier Knowledge Graph & Intelligence Database Models.

Layer 0 — Source & Authorization Metadata (sources, connectors, oauth_connections, permission_scopes)
Layer 1 — Immutable Raw Signals Lake (raw_signals with SHA-256 idempotency)
Layer 2 — Canonical Knowledge Graph (entity_registry, persons, companies_v2, jobs_v2, posts_v2, relationships)
Layer 3 — Intelligence & Intent Signals (signal_events, derived_intents, evidence_ledger, career_velocities)
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Float,
    Text,
    TIMESTAMP,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.sql import func
from ..database import Base


# ── Layer 0: Source & Authorization Registry ─────────────────────────────────

class SourceConnector(Base):
    __tablename__ = "source_connectors"

    id = Column(Integer, primary_key=True, index=True)
    connector_key = Column(String(64), unique=True, index=True, nullable=False) # e.g. LINKEDIN-OAUTH-PROD
    source_type = Column(String(64), index=True, nullable=False)               # LINKEDIN_OAUTH, ATS_GREENHOUSE, SCOUT_DESKTOP
    name = Column(String(150), nullable=False)
    auth_type = Column(String(32), default="OAUTH2")                          # OAUTH2, API_KEY, DESKTOP_PAIRING, PUBLIC
    is_active = Column(Boolean, default=True, index=True)
    config_json = Column(Text, default="{}")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class OAuthScopeRegistry(Base):
    __tablename__ = "oauth_scope_registry"

    id = Column(Integer, primary_key=True, index=True)
    connector_id = Column(Integer, ForeignKey("source_connectors.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True)
    scopes_granted = Column(Text, nullable=False)                               # JSON array of granted permission scopes
    token_status = Column(String(32), default="ACTIVE")                         # ACTIVE, EXPIRED, REVOKED
    expires_at = Column(TIMESTAMP, nullable=True)
    last_authorized_at = Column(TIMESTAMP, server_default=func.now())


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_uuid = Column(String(64), unique=True, index=True, nullable=False)
    connector_id = Column(Integer, ForeignKey("source_connectors.id", ondelete="CASCADE"), index=True, nullable=False)
    status = Column(String(32), default="RUNNING", index=True)                 # RUNNING, COMPLETED, FAILED
    records_observed = Column(Integer, default=0)
    records_staged = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(TIMESTAMP, server_default=func.now(), index=True)
    completed_at = Column(TIMESTAMP, nullable=True)


# ── Layer 1: Immutable Raw Signals Lake ──────────────────────────────────────

class RawSignal(Base):
    """
    Immutable Raw Observation Store.
    Stores the exact verbatim payload received from any source.
    SHA-256 content hash guarantees zero duplicate raw payloads.
    """
    __tablename__ = "raw_signals"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(64), index=True, nullable=False)
    source_object_type = Column(String(64), index=True, nullable=False)         # person, company, job, post, profile
    source_object_id = Column(String(255), index=True, nullable=False)
    content_hash = Column(String(64), index=True, nullable=False)               # SHA-256 hash
    authorization_scope = Column(String(100), default="authorized")
    raw_payload = Column(Text, nullable=False)                                  # Exact verbatim JSON
    provenance_json = Column(Text, nullable=True)                               # Connector info, IP, device headers
    ingested_at = Column(TIMESTAMP, server_default=func.now(), index=True)

    __table_args__ = (
        UniqueConstraint("source_type", "source_object_type", "content_hash", name="uq_raw_signal_hash"),
    )


# ── Layer 2: Canonical Knowledge Graph & Dedicated Fact Tables ───────────────

class EntityRegistry(Base):
    """
    Universal registry of all canonical entities in the TalentOps Knowledge Graph.
    Decouples raw observations from clean canonical identities.
    """
    __tablename__ = "entity_registry"

    id = Column(Integer, primary_key=True, index=True)
    canonical_key = Column(String(128), unique=True, index=True, nullable=False) # e.g. PER-38A91F, CMP-MSFT
    entity_type = Column(String(32), index=True, nullable=False)                # PERSON, COMPANY, JOB, POST, SKILL, TECH, TOPIC
    primary_source = Column(String(64), default="SYSTEM")
    status = Column(String(32), default="ACTIVE", index=True)                   # ACTIVE, MERGED, ARCHIVED
    merged_into_key = Column(String(128), nullable=True, index=True)
    first_seen_at = Column(TIMESTAMP, server_default=func.now())
    last_seen_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class PersonEntity(Base):
    """Dedicated relational fact table for people."""
    __tablename__ = "persons"

    id = Column(Integer, primary_key=True, index=True)
    canonical_key = Column(String(128), ForeignKey("entity_registry.canonical_key", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    full_name = Column(String(200), nullable=False, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    headline = Column(String(300), nullable=True)
    about = Column(Text, nullable=True)
    current_title = Column(String(200), nullable=True, index=True)
    current_company_name = Column(String(255), nullable=True, index=True)
    current_company_canonical_key = Column(String(128), nullable=True, index=True)
    location_city = Column(String(150), nullable=True)
    location_state = Column(String(50), nullable=True, index=True)
    location_country = Column(String(50), default="US", index=True)
    primary_email = Column(String(200), nullable=True, index=True)
    primary_phone = Column(String(50), nullable=True)
    linkedin_url = Column(String(350), nullable=True, index=True)
    seniority_level = Column(String(50), nullable=True, index=True)             # IC, Lead, Manager, Director, VP, CXO
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class CompanyEntity(Base):
    """Dedicated relational fact table for companies."""
    __tablename__ = "companies_v2"

    id = Column(Integer, primary_key=True, index=True)
    canonical_key = Column(String(128), ForeignKey("entity_registry.canonical_key", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    canonical_name = Column(String(255), nullable=False, index=True)
    primary_domain = Column(String(255), nullable=True, index=True)
    industry = Column(String(150), nullable=True, index=True)
    headquarters = Column(String(255), nullable=True)
    headcount_range = Column(String(50), nullable=True)                         # 1-10, 11-50, 51-200, 201-500, 501-1000, 1000+
    linkedin_url = Column(String(350), nullable=True)
    website_url = Column(String(350), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class JobEntity(Base):
    """Dedicated relational fact table for job openings."""
    __tablename__ = "jobs_v2"

    id = Column(Integer, primary_key=True, index=True)
    canonical_key = Column(String(128), ForeignKey("entity_registry.canonical_key", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    company_canonical_key = Column(String(128), index=True, nullable=False)
    title = Column(String(255), nullable=False, index=True)
    seniority = Column(String(50), nullable=True, index=True)
    employment_type = Column(String(50), default="Full-time")
    location = Column(String(255), nullable=True)
    posted_at = Column(TIMESTAMP, nullable=True, index=True)
    status = Column(String(32), default="OPEN", index=True)                     # OPEN, CLOSED, FILLED
    raw_description = Column(Text, nullable=True)
    skills_required_json = Column(Text, default="[]")
    technologies_required_json = Column(Text, default="[]")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class PostEntity(Base):
    """Dedicated relational fact table for published professional posts."""
    __tablename__ = "posts_v2"

    id = Column(Integer, primary_key=True, index=True)
    canonical_key = Column(String(128), ForeignKey("entity_registry.canonical_key", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    author_canonical_key = Column(String(128), index=True, nullable=False)
    author_type = Column(String(32), default="PERSON")                          # PERSON | COMPANY
    content_text = Column(Text, nullable=False)
    published_at = Column(TIMESTAMP, nullable=True, index=True)
    url = Column(String(400), nullable=True)
    topics_json = Column(Text, default="[]")
    technologies_json = Column(Text, default="[]")
    engagement_metrics_json = Column(Text, default="{}")
    created_at = Column(TIMESTAMP, server_default=func.now())


class SkillEntity(Base):
    __tablename__ = "skills_v2"

    id = Column(Integer, primary_key=True, index=True)
    canonical_key = Column(String(128), ForeignKey("entity_registry.canonical_key", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    canonical_name = Column(String(150), unique=True, index=True, nullable=False)
    category = Column(String(100), nullable=True, index=True)


class TechnologyEntity(Base):
    __tablename__ = "technologies_v2"

    id = Column(Integer, primary_key=True, index=True)
    canonical_key = Column(String(128), ForeignKey("entity_registry.canonical_key", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    canonical_name = Column(String(150), unique=True, index=True, nullable=False)
    category = Column(String(100), nullable=True, index=True)                   # Cloud, Database, AI, DevOps, CRM
    ecosystem = Column(String(100), nullable=True, index=True)                  # AWS, Azure, GCP, Modern Data Stack


class RelationshipEdge(Base):
    """
    Typed Knowledge Graph Edges with temporal validity & epistemic status.
    Answers: Who worked where? Who knows what? What company uses what technology?
    """
    __tablename__ = "relationships"

    id = Column(Integer, primary_key=True, index=True)
    source_canonical_key = Column(String(128), index=True, nullable=False)
    target_canonical_key = Column(String(128), index=True, nullable=False)
    relationship_type = Column(String(64), index=True, nullable=False)          # WORKED_AT, USES_TECHNOLOGY, HAS_SKILL, etc.
    valid_from = Column(TIMESTAMP, nullable=True)
    valid_to = Column(TIMESTAMP, nullable=True)
    is_current = Column(Boolean, default=True, index=True)
    epistemic_level = Column(String(32), default="OBSERVED_FACT", index=True)  # OBSERVED_FACT, INFERRED_FACT
    confidence = Column(Float, default=1.0)
    evidence_summary = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


# ── Layer 3: Intelligence, Intent Events & Explainable Provenance ────────────

class SignalEvent(Base):
    """
    Atomic evidence events that feed the Intent Engine.
    Each event has an assigned category and weight.
    """
    __tablename__ = "signal_events"

    id = Column(Integer, primary_key=True, index=True)
    target_canonical_key = Column(String(128), index=True, nullable=False)      # Target company or person
    event_type = Column(String(64), index=True, nullable=False)                 # JOB_POSTED, LEADERSHIP_EXPANSION, etc.
    weight = Column(Float, default=0.25)
    event_timestamp = Column(TIMESTAMP, server_default=func.now(), index=True)
    raw_signal_hash = Column(String(64), index=True, nullable=False)
    metadata_json = Column(Text, default="{}")


class DerivedIntent(Base):
    """
    Composite intent score derived from aggregated, timestamped SignalEvents.
    Provides auditable, reproducible scoring.
    """
    __tablename__ = "derived_intents"

    id = Column(Integer, primary_key=True, index=True)
    target_canonical_key = Column(String(128), index=True, nullable=False)      # Company or Person
    intent_category = Column(String(64), index=True, nullable=False)            # HIRING_INTENT, TECH_ADOPTION, etc.
    score = Column(Integer, nullable=False, index=True)                         # 0 to 100
    confidence = Column(Float, default=1.0)                                     # 0.0 to 1.0
    status = Column(String(32), default="ACTIVE", index=True)
    model_version = Column(String(64), default="v1.0-event-aggregator")
    calculated_at = Column(TIMESTAMP, server_default=func.now(), index=True)


class EvidenceLedger(Base):
    """
    Explainability Ledger: Every score links to exact supporting facts.
    Answers: 'Why did you show me this?'
    """
    __tablename__ = "evidence_ledger"

    id = Column(Integer, primary_key=True, index=True)
    derived_intent_id = Column(Integer, ForeignKey("derived_intents.id", ondelete="CASCADE"), index=True, nullable=False)
    signal_event_id = Column(Integer, ForeignKey("signal_events.id", ondelete="CASCADE"), index=True, nullable=False)
    claim_text = Column(Text, nullable=False)
    evidence_excerpt = Column(Text, nullable=False)
    observed_at = Column(TIMESTAMP, nullable=False)
    confidence = Column(Float, default=1.0)


class CareerVelocityRecord(Base):
    """
    Temporal intelligence tracking a candidate's career progression velocity.
    """
    __tablename__ = "career_velocities"

    id = Column(Integer, primary_key=True, index=True)
    person_canonical_key = Column(String(128), index=True, nullable=False)
    velocity_score = Column(Integer, nullable=False, index=True)                # 0 to 100
    time_in_role_months = Column(Integer, nullable=True)
    avg_promotion_interval_months = Column(Float, nullable=True)
    title_level_progression = Column(String(255), nullable=True)
    skills_velocity = Column(Integer, default=0)
    calculated_at = Column(TIMESTAMP, server_default=func.now(), index=True)
