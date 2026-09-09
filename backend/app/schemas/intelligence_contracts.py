"""
intelligence_contracts.py — Universal Source-Agnostic Data Contracts for TalentOpsAI.

Defines:
- Epistemic classification (OBSERVED_FACT vs INFERRED_FACT vs PREDICTED_INTENT)
- Source & Permission scope contracts
- Universal Source Object identity (deduplication across multiple sources)
- Canonical entity fact contracts (Person, Company, Job, Post, Tech, Skill)
- Typed graph edge relationships with temporal validity
- Event-based signal events & explainable intent aggregations
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, ConfigDict


# ── 1. Epistemic Levels (Observed vs Inferred vs Predicted) ──────────────────

class EpistemicLevel(str, Enum):
    """
    Strict epistemic separation:
    - OBSERVED_FACT: Explicitly present in the source data payload (verbatim fact).
    - INFERRED_FACT: Derived by cross-referencing multiple observations (synthesized fact).
    - PREDICTED_INTENT: Statistical/ML projection of upcoming action (probabilistic forecast).
    """
    OBSERVED_FACT = "OBSERVED_FACT"
    INFERRED_FACT = "INFERRED_FACT"
    PREDICTED_INTENT = "PREDICTED_INTENT"


# ── 2. Source Connectors & Authorization Scopes ──────────────────────────────

class SourceType(str, Enum):
    LINKEDIN_OAUTH = "LINKEDIN_OAUTH"
    ATS_GREENHOUSE = "ATS_GREENHOUSE"
    ATS_LEVER = "ATS_LEVER"
    ATS_ASHBY = "ATS_ASHBY"
    ATS_WORKDAY = "ATS_WORKDAY"
    SCOUT_DESKTOP = "SCOUT_DESKTOP"
    JOB_BOARD = "JOB_BOARD"
    COMPANY_API = "COMPANY_API"
    CRM = "CRM"
    PUBLIC_WEB = "PUBLIC_WEB"


class ScopeLevel(str, Enum):
    MEMBER_BASIC_PROFILE = "r_basicprofile"
    MEMBER_FULL_PROFILE = "r_fullprofile"
    ORGANIZATION_READ = "r_organization_social"
    ORGANIZATION_POSTS = "w_organization_social"
    ATS_READ_CANDIDATE = "ats.candidate.read"
    ATS_READ_JOB = "ats.job.read"
    DESKTOP_OBSERVATION = "desktop.active_observation"
    PUBLIC_REGISTRY = "public.registry"


class SourceObjectIdentity(BaseModel):
    """Universal source object identity across all authorized data feeds."""
    model_config = ConfigDict(frozen=True)

    source: SourceType
    source_object_type: str = Field(..., description="E.g. person, company, job, post, comment")
    source_object_id: str = Field(..., description="Unique ID assigned by the source system")
    authorization_scope: str = Field(default="authorized", description="Permission scope under which object was retrieved")
    content_hash: str = Field(..., description="SHA-256 hash of canonical content payload")


# ── 3. Universal Ingestion Envelope (Layer 0 / Layer 1) ──────────────────────

class UniversalSourceObject(BaseModel):
    """Envelope wrapping every raw incoming observation before ingestion."""
    identity: SourceObjectIdentity
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_payload: Dict[str, Any]
    provenance_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


# ── 4. Relationship Types (Knowledge Graph Edges) ────────────────────────────

class RelationshipType(str, Enum):
    WORKED_AT = "WORKED_AT"
    CURRENTLY_WORKS_AT = "CURRENTLY_WORKS_AT"
    HAS_SKILL = "HAS_SKILL"
    USES_TECHNOLOGY = "USES_TECHNOLOGY"
    AUTHORED = "AUTHORED"
    MENTIONS_TECH = "MENTIONS_TECH"
    MENTIONS_COMPANY = "MENTIONS_COMPANY"
    DISCUSSES_TOPIC = "DISCUSSES_TOPIC"
    REPORTS_TO = "REPORTS_TO"
    HIRING_FOR = "HIRING_FOR"
    CONNECTED_TO = "CONNECTED_TO"
    ATTENDED_SCHOOL = "ATTENDED_SCHOOL"


class RelationshipContract(BaseModel):
    """Typed graph edge with temporal validity and epistemic status."""
    source_canonical_key: str
    target_canonical_key: str
    relationship_type: RelationshipType
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    is_current: bool = True
    epistemic_level: EpistemicLevel = EpistemicLevel.OBSERVED_FACT
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_summary: Optional[str] = None


# ── 5. Canonical Entity Contracts (Layer 2) ──────────────────────────────────

class PersonFact(BaseModel):
    canonical_key: str
    full_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    headline: Optional[str] = None
    about: Optional[str] = None
    current_title: Optional[str] = None
    current_company_name: Optional[str] = None
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    location_country: Optional[str] = "US"
    primary_email: Optional[str] = None
    primary_phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    seniority_level: Optional[str] = None  # e.g. IC, Lead, Manager, Director, VP, CXO


class CompanyFact(BaseModel):
    canonical_key: str
    canonical_name: str
    primary_domain: Optional[str] = None
    industry: Optional[str] = None
    headquarters: Optional[str] = None
    headcount_range: Optional[str] = None
    linkedin_url: Optional[str] = None
    website_url: Optional[str] = None


class JobFact(BaseModel):
    canonical_key: str
    company_canonical_key: str
    title: str
    location: Optional[str] = None
    seniority: Optional[str] = None
    employment_type: Optional[str] = "Full-time"
    posted_at: Optional[datetime] = None
    status: str = "OPEN"
    required_skills: List[str] = Field(default_factory=list)
    required_technologies: List[str] = Field(default_factory=list)


class PostFact(BaseModel):
    canonical_key: str
    author_canonical_key: str
    author_type: str = "PERSON"  # PERSON | COMPANY
    content_text: str
    published_at: Optional[datetime] = None
    url: Optional[str] = None
    extracted_topics: List[str] = Field(default_factory=list)
    extracted_technologies: List[str] = Field(default_factory=list)


# ── 6. Signal Events & Intent Engine (Layer 3) ───────────────────────────────

class SignalEventType(str, Enum):
    JOB_POSTED = "JOB_POSTED"
    JOB_CLOSED = "JOB_CLOSED"
    PROMOTION = "PROMOTION"
    ROLE_CHANGE = "ROLE_CHANGE"
    COMPANY_SWITCH = "COMPANY_SWITCH"
    SKILL_ADDED = "SKILL_ADDED"
    TECH_MENTIONED = "TECH_MENTIONED"
    LEADERSHIP_EXPANSION = "LEADERSHIP_EXPANSION"
    HEADCOUNT_GROWTH = "HEADCOUNT_GROWTH"
    POST_PUBLISHED = "POST_PUBLISHED"
    FUNDING_ANNOUNCED = "FUNDING_ANNOUNCED"


class IntentCategory(str, Enum):
    HIRING_INTENT = "HIRING_INTENT"
    BUYING_INTENT = "BUYING_INTENT"
    CAREER_TRANSITION = "CAREER_TRANSITION"
    TECHNOLOGY_ADOPTION = "TECHNOLOGY_ADOPTION"
    GROWTH_EXPANSION = "GROWTH_EXPANSION"
    BUSINESS_DEVELOPMENT = "BUSINESS_DEVELOPMENT"


class SignalEventContract(BaseModel):
    """Discrete, atomic event feeding into the intent aggregator."""
    target_canonical_key: str
    event_type: SignalEventType
    weight: float = Field(default=0.25, ge=0.0, le=1.0)
    event_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_signal_hash: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidenceItem(BaseModel):
    """Explainable audit ledger entry explaining 'Why did you show me this?'."""
    claim_text: str
    source: SourceType
    event_type: SignalEventType
    observed_at: datetime
    confidence: float
    evidence_excerpt: str


class DerivedIntentContract(BaseModel):
    """Composite, explainable intent prediction."""
    target_canonical_key: str
    intent_category: IntentCategory
    score: int = Field(..., ge=0, le=100, description="0-100 composite intent score")
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_chain: List[EvidenceItem] = Field(default_factory=list)
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_version: str = "v1.0-event-aggregator"
