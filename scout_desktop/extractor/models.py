from __future__ import annotations
"""
extractor/models.py — Open-Ended Observation & Entity Graph Models

Defines the flexible observation ontology:
- Entities are not forced into rigid 5-field schemas.
- Supports Person, Company, Job, Skills, Experience History, Signals, Relationships.
- Every observation carries provenance: capture_id, evidence string, confidence, and grounding status.
"""

import time
import uuid
import re
from typing import Optional, Dict, Any, List


class Observation:
    def __init__(
        self,
        semantic_type: str,
        subject: str,
        predicate: str,
        object_value: Any,
        confidence: float = 0.9,
        evidence: str = "",
        source: str = "visual_inspection",
        capture_id: str = "",
        source_url: str = "",
        attributes: Optional[Dict[str, Any]] = None,
        evidence_region: Optional[Dict[str, int]] = None,
    ):
        self.observation_id = f"OBS-{uuid.uuid4().hex[:8].upper()}"
        self.semantic_type = semantic_type  # PERSON | COMPANY | JOB | LOCATION | EDUCATION | SKILL | SIGNAL
        self.subject = subject              # e.g. "David Fitzgerald"
        self.predicate = predicate          # e.g. "WORKS_AT", "HAS_TITLE", "LOCATED_IN", "PREVIOUSLY_WORKED_AT"
        self.object_value = object_value    # e.g. "SkillBridge, Inc."
        self.confidence = float(confidence)
        self.evidence = evidence            # Exact string observed on screen
        self.source = source
        self.capture_id = capture_id
        self.source_url = source_url
        self.attributes = attributes or {}
        self.evidence_region = evidence_region or self.attributes.get("evidence_region")
        if self.evidence_region:
            self.attributes["evidence_region"] = self.evidence_region
        self.timestamp = time.time()
        self.grounding_status = "GROUNDED" if evidence and len(str(evidence).strip()) > 0 else "REJECT_UNGROUNDED"

    def is_grounded(self) -> bool:
        return self.grounding_status == "GROUNDED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "semantic_type": self.semantic_type,
            "subject": self.subject,
            "predicate": self.predicate,
            "object_value": self.object_value,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "evidence_region": self.evidence_region,
            "source": self.source,
            "capture_id": self.capture_id,
            "source_url": self.source_url,
            "attributes": self.attributes,
            "timestamp": self.timestamp,
            "grounding_status": self.grounding_status,
        }

    def __repr__(self):
        return f"<Obs [{self.semantic_type}] {self.subject} -({self.predicate})-> {self.object_value} ({int(self.confidence*100)}%)>"


class CompletenessState:
    """Tracks what is known vs unknown for an entity."""
    def __init__(self):
        self.identity: bool = False
        self.current_employment: bool = False
        self.location: bool = False
        self.education: bool = False
        self.contact: bool = False
        self.employment_history_count: int = 0
        self.skills_count: int = 0

    @property
    def missing_fields(self) -> list[str]:
        missing = []
        if not self.identity:
            missing.append("identity")
        if not self.current_employment:
            missing.append("current_employment")
        if not self.location:
            missing.append("location")
        if not self.education:
            missing.append("education")
        if not self.contact:
            missing.append("contact")
        return missing

    @property
    def score(self) -> float:
        s = 0.0
        if self.identity:
            s += 0.30
        if self.current_employment:
            s += 0.25
        if self.contact:
            s += 0.20
        if self.location:
            s += 0.10
        if self.education:
            s += 0.10
        if self.skills_count > 0:
            s += 0.05
        return min(1.0, s)

    def to_dict(self) -> dict:
        return {
            "identity": self.identity,
            "current_employment": self.current_employment,
            "location": self.location,
            "education": self.education,
            "contact": self.contact,
            "employment_history_count": self.employment_history_count,
            "skills_count": self.skills_count,
            "missing_fields": self.missing_fields,
            "score": self.score
        }


class EntityNode:
    """Flexible entity that can be PERSON, COMPANY, JOB, TEAM, EDUCATION."""
    def __init__(self, canonical_name: str, entity_type: str = "UNKNOWN"):
        self.node_id: str = f"ENT-{uuid.uuid4()}"
        self.entity_type: str = entity_type
        self.canonical_name: str = canonical_name
        self.attributes: dict[str, Any] = {}
        self.observations: list[Observation] = []
        self.completeness: CompletenessState = CompletenessState()
        self.metadata: dict = {}
        self.created_at: float = time.time()

    def add_observation(self, obs: Observation):
        self.observations.append(obs)
        pred = obs.predicate
        if pred in ("HAS_TITLE", "WORKS_AT"):
            self.completeness.current_employment = True
        elif pred in ("HAS_EMAIL", "HAS_PHONE", "HAS_LINKEDIN"):
            self.completeness.contact = True
        elif pred == "LOCATED_IN":
            self.completeness.location = True
        elif pred == "STUDIED_AT":
            self.completeness.education = True
        elif pred == "PREVIOUSLY_WORKED_AT":
            self.completeness.employment_history_count += 1
        elif pred == "HAS_SKILL":
            self.completeness.skills_count += 1
        if self.canonical_name:
            self.completeness.identity = True

    def get_attribute(self, key: str, default: Any = None) -> Any:
        return self.attributes.get(key, default)

    def set_attribute(self, key: str, value: Any):
        self.attributes[key] = value

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "entity_type": self.entity_type,
            "canonical_name": self.canonical_name,
            "attributes": self.attributes,
            "observations": [obs.to_dict() for obs in self.observations],
            "completeness": self.completeness.to_dict(),
            "metadata": self.metadata,
            "created_at": self.created_at
        }

    def __repr__(self) -> str:
        return f"<EntityNode [{self.entity_type}] {self.canonical_name} ({self.node_id})>"


class RelationshipEdge:
    """Typed edge between two EntityNodes."""
    def __init__(self, source_node_id: str, target_node_id: str, relationship_type: str):
        self.edge_id: str = f"REL-{uuid.uuid4()}"
        self.source_node_id: str = source_node_id
        self.target_node_id: str = target_node_id
        self.relationship_type: str = relationship_type
        self.attributes: dict = {}
        self.evidence: list[str] = []
        self.created_at: float = time.time()

    def to_dict(self) -> dict:
        return {
            "edge_id": self.edge_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "relationship_type": self.relationship_type,
            "attributes": self.attributes,
            "evidence": self.evidence,
            "created_at": self.created_at
        }


class GraphContext:
    """Metadata about the observation context."""
    def __init__(self):
        self.page_type: str = "UNKNOWN"
        self.source_url: str = ""
        self.capture_ids: list[str] = []
        self.platform: str = "UNKNOWN"

    def to_dict(self) -> dict:
        return {
            "page_type": self.page_type,
            "source_url": self.source_url,
            "capture_ids": self.capture_ids,
            "platform": self.platform
        }


class ObservationGraph:
    """Container for related entities and relationships."""
    def __init__(self):
        self.graph_id: str = f"GRAPH-{uuid.uuid4()}"
        self.nodes: dict[str, EntityNode] = {}
        self.edges: list[RelationshipEdge] = []
        self.context: GraphContext = GraphContext()
        self.created_at: float = time.time()

    def add_entity(self, node: EntityNode) -> str:
        self.nodes[node.node_id] = node
        return node.node_id

    def add_relationship(self, edge: RelationshipEdge):
        self.edges.append(edge)

    def get_entity(self, node_id: str) -> Optional[EntityNode]:
        return self.nodes.get(node_id)

    def find_entities_by_type(self, entity_type: str) -> list[EntityNode]:
        return [node for node in self.nodes.values() if node.entity_type == entity_type]

    def find_entities_by_name(self, name: str) -> list[EntityNode]:
        return [node for node in self.nodes.values() if node.canonical_name == name]

    def merge_from(self, other: 'ObservationGraph'):
        for node_id, node in other.nodes.items():
            if node_id not in self.nodes:
                self.nodes[node_id] = node
        self.edges.extend(other.edges)
        self.context.capture_ids.extend(other.context.capture_ids)
        self.context.capture_ids = list(set(self.context.capture_ids))

    def to_staged_batch(self) -> list[dict]:
        batch = []
        for node in self.find_entities_by_type("PERSON"):
            title = node.get_attribute("title")
            company = node.get_attribute("company")
            email = node.get_attribute("email")
            phone = node.get_attribute("phone")
            linkedin = node.get_attribute("linkedin")
            location = node.get_attribute("location")
            education = node.get_attribute("education")
            about = node.get_attribute("about")
            
            skills = []
            employment = []
            signals = []
            
            for obs in node.observations:
                if obs.predicate == "HAS_TITLE" and not title:
                    title = obs.object_value
                elif obs.predicate == "WORKS_AT" and not company:
                    company = obs.object_value
                elif obs.predicate == "HAS_EMAIL" and not email:
                    email = obs.object_value
                elif obs.predicate == "HAS_PHONE" and not phone:
                    phone = obs.object_value
                elif obs.predicate == "HAS_LINKEDIN" and not linkedin:
                    linkedin = obs.object_value
                elif obs.predicate == "LOCATED_IN" and not location:
                    location = obs.object_value
                elif obs.predicate == "STUDIED_AT" and not education:
                    education = obs.object_value
                elif obs.predicate in ("HAS_ABOUT", "HAS_ABOUT_SUMMARY") and not about:
                    about = obs.object_value
                elif obs.predicate == "HAS_SKILL" and obs.object_value not in skills:
                    skills.append(str(obs.object_value))
                elif obs.predicate == "PREVIOUSLY_WORKED_AT":
                    prev_record = {"company": str(obs.object_value), "title": obs.attributes.get("title")}
                    if prev_record not in employment:
                        employment.append(prev_record)
                elif obs.predicate in ("HAS_HIRING_SIGNAL", "HAS_STAFFING_SIGNAL"):
                    signals.append(str(obs.object_value))
                    
            batch.append({
                "recruiter_name": node.canonical_name,
                "raw_name": node.canonical_name,
                "title": title,
                "raw_title": title,
                "company_name": company,
                "raw_company": company,
                "email": email,
                "raw_email": email,
                "phone": phone,
                "raw_phone": phone,
                "linkedin_url": linkedin,
                "raw_linkedin": linkedin,
                "location": location,
                "raw_location": location,
                "education": education,
                "about_summary": about,
                "skills": skills,
                "experience_history": employment,
                "is_open_to_work": any("open to work" in s.lower() for s in signals),
                "is_hiring": any("hiring" in s.lower() for s in signals),
                "confidence": 95 if linkedin or email else 85,
                "observations_count": len(node.observations)
            })
        return batch

    def to_dict(self) -> dict:
        return {
            "graph_id": self.graph_id,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
            "context": self.context.to_dict(),
            "created_at": self.created_at
        }


class EntityCluster:
    """
    Accumulates observations for a single entity (e.g. Person, Company, or Job)
    across multiple frames and scrolls into a coherent canonical entity profile.
    """
    def __init__(self, canonical_name: str, entity_type: str = "PERSON"):
        self.canonical_name = canonical_name
        self.entity_type = entity_type
        self.observations: List[Observation] = []

        # Canonical synthesized attributes
        self.current_title: Optional[str] = None
        self.current_company: Optional[str] = None
        self.location: Optional[str] = None
        self.education: Optional[str] = None
        self.email: Optional[str] = None
        self.phone: Optional[str] = None
        self.linkedin_url: Optional[str] = None
        self.connection_degree: Optional[str] = None
        self.skills: List[str] = []
        self.employment_history: List[Dict[str, Any]] = []
        self.about_summary: Optional[str] = None
        self.signals: List[str] = []
        self.metadata: Dict[str, Any] = {}
        self.attribute_confidences: Dict[str, float] = {}

    def add_observation(self, obs: Observation):
        """Adds observation and enriches canonical fields with confidence preservation."""
        if obs.grounding_status == "REJECT_UNGROUNDED":
            return

        self.observations.append(obs)
        pred = obs.predicate

        if pred == "HAS_TITLE":
            if not self.current_title or obs.confidence > self.attribute_confidences.get("current_title", 0.0):
                self.current_title = str(obs.object_value)
                self.attribute_confidences["current_title"] = obs.confidence
        elif pred == "WORKS_AT":
            if not self.current_company or obs.confidence > self.attribute_confidences.get("current_company", 0.0):
                self.current_company = str(obs.object_value)
                self.attribute_confidences["current_company"] = obs.confidence
        elif pred == "PREVIOUSLY_WORKED_AT":
            prev_record = {
                "company": str(obs.object_value),
                "title": obs.attributes.get("title"),
                "start_date": obs.attributes.get("start_date"),
                "end_date": obs.attributes.get("end_date"),
                "tenure_months": obs.attributes.get("tenure_months"),
                "is_current": False,
            }
            # Deduplicate by company and title
            existing = [r for r in self.employment_history if r.get("company") == prev_record["company"] and r.get("title") == prev_record["title"]]
            if not existing:
                self.employment_history.append(prev_record)
        elif pred == "LOCATED_IN":
            if not self.location or obs.confidence > self.attribute_confidences.get("location", 0.0):
                self.location = str(obs.object_value)
                self.attribute_confidences["location"] = obs.confidence
        elif pred == "STUDIED_AT":
            if not self.education or obs.confidence > self.attribute_confidences.get("education", 0.0):
                self.education = str(obs.object_value)
                self.attribute_confidences["education"] = obs.confidence
        elif pred == "HAS_DEGREE":
            degree_val = str(obs.object_value).strip()
            if self.education and degree_val and degree_val not in self.education:
                self.education = f"{self.education} — {degree_val}"
            elif not self.education:
                self.education = degree_val
                self.attribute_confidences["education"] = obs.confidence
        elif pred == "HAS_EMAIL":
            self.email = str(obs.object_value)
        elif pred == "HAS_PHONE":
            self.phone = str(obs.object_value)
        elif pred == "HAS_LINKEDIN":
            self.linkedin_url = str(obs.object_value)
        elif pred == "HAS_CONNECTION_DEGREE":
            self.connection_degree = str(obs.object_value)
        elif pred == "HAS_SKILL":
            skill = str(obs.object_value).strip()
            if skill and skill not in self.skills:
                self.skills.append(skill)
        elif pred in ("HAS_ABOUT", "HAS_ABOUT_SUMMARY"):
            if not self.about_summary or obs.confidence >= self.attribute_confidences.get("about_summary", 0.0):
                self.about_summary = str(obs.object_value)
                self.attribute_confidences["about_summary"] = obs.confidence
        elif pred in ("HAS_HIRING_SIGNAL", "HAS_STAFFING_SIGNAL"):
            sig = str(obs.object_value)
            if sig not in self.signals:
                self.signals.append(sig)

    def to_staged_contact_dict(self) -> Dict[str, Any]:
        """Converts canonical cluster to format accepted by /recruiters/extension/batch."""
        # Include current role in experience history if present
        exp_list = list(self.employment_history)
        if self.current_company:
            has_cur = any(r.get("company") == self.current_company and r.get("is_current") for r in exp_list)
            if not has_cur:
                cur_obs = next(
                    (o for o in self.observations if o.predicate == "WORKS_AT" and str(o.object_value) == self.current_company),
                    None
                )
                cur_attrs = cur_obs.attributes if cur_obs else {}
                cur_entry = {
                    "company": self.current_company,
                    "title": cur_attrs.get("title") or self.current_title,
                    "start_date": cur_attrs.get("start_date"),
                    "end_date": None,
                    "tenure_months": cur_attrs.get("tenure_months"),
                    "is_current": True,
                }
                exp_list.insert(0, cur_entry)

        clean_name = self.canonical_name
        if clean_name:
            clean_name = re.sub(r"\s*[\(\[]?\b(?:she/her|he/him|they/them|she/they|he/they)\b[\)\]]?", "", clean_name, flags=re.IGNORECASE).strip()

        clean_comp = self.current_company
        if clean_comp and (" | linkedin" in clean_comp.lower() or clean_comp.lower().endswith("linkedin")):
            clean_comp = None

        return {
            "recruiter_name": clean_name or self.canonical_name,
            "raw_name": self.canonical_name,
            "title": self.current_title,
            "raw_title": self.current_title,
            "company_name": clean_comp,
            "raw_company": self.current_company,
            "email": self.email,
            "raw_email": self.email,
            "phone": self.phone,
            "raw_phone": self.phone,
            "linkedin_url": self.linkedin_url,
            "raw_linkedin": self.linkedin_url,
            "location": self.location,
            "raw_location": self.location,
            "education": self.education,
            "about_summary": self.about_summary,
            "skills": self.skills,
            "experience_history": exp_list,
            "is_open_to_work": any("open to work" in s.lower() for s in self.signals),
            "is_hiring": any("hiring" in s.lower() for s in self.signals),
            "confidence": 95 if self.linkedin_url or self.email else 85,
            "observations_count": len(self.observations),
        }


class ExtensibleObservation:
    """Information that doesn't fit existing categories."""
    def __init__(
        self,
        semantic_type: str,
        raw_value: str,
        context: str,
        source: str,
        evidence: str,
        confidence: float = 1.0,
    ):
        self.semantic_type = semantic_type
        self.raw_value = raw_value
        self.context = context
        self.source = source
        self.evidence = evidence
        self.confidence = confidence
        self.timestamp = time.time()
        
    def to_dict(self) -> dict:
        return {
            "semantic_type": self.semantic_type,
            "raw_value": self.raw_value,
            "context": self.context,
            "source": self.source,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "timestamp": self.timestamp
        }
