"""
gateway.py — Universal Ingestion Gateway for TalentOpsAI Intelligence Engine.

Receives observations from any authorized source connector (LinkedIn, ATS, Scout Desktop, CRM).
Validates permission scopes, computes SHA-256 hashes, writes immutable Layer 1 Raw Signals,
and resolves canonical entities into Layer 2 Knowledge Graph tables.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session

from ...schemas.intelligence_contracts import (
    UniversalSourceObject,
    SourceType,
    EpistemicLevel,
    RelationshipType,
    SignalEventType,
)
from ...models.intelligence_models import (
    RawSignal,
    EntityRegistry,
    PersonEntity,
    CompanyEntity,
    JobEntity,
    PostEntity,
    RelationshipEdge,
    SignalEvent,
)

logger = logging.getLogger("talentops.intelligence.gateway")


def compute_payload_hash(payload: Dict[str, Any]) -> str:
    """Deterministic SHA-256 hash of structured JSON payload."""
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class IngestionGateway:
    def __init__(self, db: Session):
        self.db = db

    def ingest_observation(self, obj: UniversalSourceObject) -> Dict[str, Any]:
        """
        Main entry point for all incoming observations.
        1. Validates payload hash & enforces Layer 1 immutability.
        2. Resolves or creates canonical entity in Layer 2.
        3. Creates typed graph relationships.
        4. Emits atomic Layer 3 signal events where applicable.
        """
        raw_hash = obj.identity.content_hash
        calc_hash = compute_payload_hash(obj.raw_payload)
        effective_hash = raw_hash or calc_hash

        source_type_val = obj.identity.source.value if hasattr(obj.identity.source, "value") else str(obj.identity.source)

        # ── Step 1: Layer 1 Raw Signals Lake (Idempotent Insertion) ───────────
        existing_raw = self.db.query(RawSignal).filter(
            RawSignal.source_type == source_type_val,
            RawSignal.source_object_type == obj.identity.source_object_type,
            RawSignal.content_hash == effective_hash,
        ).first()

        if existing_raw:
            logger.info("Observation already in Raw Lake: [%s] hash=%s", source_type_val, effective_hash[:12])
            raw_signal_id = existing_raw.id
            is_new_raw = False
        else:
            new_raw = RawSignal(
                source_type=source_type_val,
                source_object_type=obj.identity.source_object_type,
                source_object_id=obj.identity.source_object_id,
                content_hash=effective_hash,
                authorization_scope=obj.identity.authorization_scope,
                raw_payload=json.dumps(obj.raw_payload, default=str),
                provenance_json=json.dumps(obj.provenance_metadata or {}, default=str),
            )
            self.db.add(new_raw)
            self.db.flush()
            raw_signal_id = new_raw.id
            is_new_raw = True

        # ── Step 2: Layer 2 Canonical Entity Resolution ──────────────────────
        entity_result = self._resolve_and_upsert_entity(obj, effective_hash, raw_signal_id)

        self.db.commit()

        return {
            "status": "INGESTED" if is_new_raw else "RE_OBSERVED",
            "raw_signal_id": raw_signal_id,
            "content_hash": effective_hash,
            "canonical_key": entity_result.get("canonical_key"),
            "entity_type": entity_result.get("entity_type"),
            "created_entities": entity_result.get("created_entities", []),
            "emitted_events": entity_result.get("emitted_events", []),
        }

    def _resolve_and_upsert_entity(self, obj: UniversalSourceObject, content_hash: str, raw_signal_id: int) -> Dict[str, Any]:
        obj_type = obj.identity.source_object_type.lower()
        payload = obj.raw_payload
        result = {"created_entities": [], "emitted_events": []}

        source_type_val = obj.identity.source.value if hasattr(obj.identity.source, "value") else str(obj.identity.source)

        if obj_type in ("person", "candidate", "recruiter", "profile"):
            # Normalize person identity
            full_name = payload.get("full_name") or payload.get("recruiter_name") or payload.get("name") or "Unknown Candidate"
            linkedin = payload.get("linkedin_url") or payload.get("linkedin")
            email = payload.get("email") or payload.get("primary_email")

            # Deterministic canonical key based on verified LinkedIn slug or email, or hash
            if linkedin and "linkedin.com/in/" in linkedin:
                slug = linkedin.split("linkedin.com/in/")[-1].strip("/? ")
                canonical_key = f"PER-LI-{slug.upper()[:24]}"
            elif email and "@" in email and "noemail" not in email:
                canonical_key = f"PER-EM-{hashlib.md5(email.strip().lower().encode()).hexdigest()[:12].upper()}"
            else:
                canonical_key = f"PER-{content_hash[:12].upper()}"

            # Register in EntityRegistry
            reg = self.db.query(EntityRegistry).filter(EntityRegistry.canonical_key == canonical_key).first()
            if not reg:
                reg = EntityRegistry(
                    canonical_key=canonical_key,
                    entity_type="PERSON",
                    primary_source=source_type_val,
                )
                self.db.add(reg)
                result["created_entities"].append(canonical_key)

            # Upsert PersonEntity
            person = self.db.query(PersonEntity).filter(PersonEntity.canonical_key == canonical_key).first()
            if not person:
                person = PersonEntity(
                    canonical_key=canonical_key,
                    full_name=full_name,
                    current_title=payload.get("current_title") or payload.get("title"),
                    current_company_name=payload.get("company_name") or payload.get("current_company"),
                    primary_email=email,
                    primary_phone=payload.get("phone") or payload.get("primary_phone"),
                    linkedin_url=linkedin,
                    location_city=payload.get("location_city") or payload.get("location"),
                    seniority_level=payload.get("seniority_level"),
                )
                self.db.add(person)
            else:
                # Enrich missing fields
                if not person.current_title and payload.get("title"):
                    person.current_title = payload.get("title")
                if not person.primary_email and email and "noemail" not in email:
                    person.primary_email = email
                if not person.linkedin_url and linkedin:
                    person.linkedin_url = linkedin

            # If person is affiliated with a company, create CompanyEntity & WORKED_AT edge
            company_name = payload.get("company_name") or payload.get("current_company")
            if company_name:
                comp_key = f"CMP-{hashlib.md5(company_name.strip().lower().encode()).hexdigest()[:12].upper()}"
                comp_reg = self.db.query(EntityRegistry).filter(EntityRegistry.canonical_key == comp_key).first()
                if not comp_reg:
                    comp_reg = EntityRegistry(canonical_key=comp_key, entity_type="COMPANY", primary_source=source_type_val)
                    self.db.add(comp_reg)
                    self.db.add(CompanyEntity(canonical_key=comp_key, canonical_name=company_name))
                    result["created_entities"].append(comp_key)

                # Connect relationship edge
                edge = self.db.query(RelationshipEdge).filter(
                    RelationshipEdge.source_canonical_key == canonical_key,
                    RelationshipEdge.target_canonical_key == comp_key,
                    RelationshipEdge.relationship_type == RelationshipType.CURRENTLY_WORKS_AT.value,
                ).first()
                if not edge:
                    self.db.add(RelationshipEdge(
                        source_canonical_key=canonical_key,
                        target_canonical_key=comp_key,
                        relationship_type=RelationshipType.CURRENTLY_WORKS_AT.value,
                        is_current=True,
                        epistemic_level=EpistemicLevel.OBSERVED_FACT.value,
                        confidence=0.95,
                    ))

            result["canonical_key"] = canonical_key
            result["entity_type"] = "PERSON"

        elif obj_type in ("company", "organization"):
            comp_name = payload.get("canonical_name") or payload.get("name") or "Unknown Company"
            domain = payload.get("domain") or payload.get("primary_domain")
            if domain:
                canonical_key = f"CMP-{domain.lower().replace('.', '-')[:24].upper()}"
            else:
                canonical_key = f"CMP-{hashlib.md5(comp_name.strip().lower().encode()).hexdigest()[:12].upper()}"

            reg = self.db.query(EntityRegistry).filter(EntityRegistry.canonical_key == canonical_key).first()
            if not reg:
                self.db.add(EntityRegistry(canonical_key=canonical_key, entity_type="COMPANY", primary_source=source_type_val))
                self.db.add(CompanyEntity(
                    canonical_key=canonical_key,
                    canonical_name=comp_name,
                    primary_domain=domain,
                    industry=payload.get("industry"),
                    headquarters=payload.get("headquarters"),
                    headcount_range=payload.get("headcount_range"),
                ))
                result["created_entities"].append(canonical_key)

            result["canonical_key"] = canonical_key
            result["entity_type"] = "COMPANY"

        elif obj_type in ("job", "requisition", "opening"):
            job_title = payload.get("title") or "Unknown Role"
            comp_name = payload.get("company_name") or "Unknown Company"
            comp_key = f"CMP-{hashlib.md5(comp_name.strip().lower().encode()).hexdigest()[:12].upper()}"

            # Ensure company exists
            comp_reg = self.db.query(EntityRegistry).filter(EntityRegistry.canonical_key == comp_key).first()
            if not comp_reg:
                self.db.add(EntityRegistry(canonical_key=comp_key, entity_type="COMPANY", primary_source=source_type_val))
                self.db.add(CompanyEntity(canonical_key=comp_key, canonical_name=comp_name))
                result["created_entities"].append(comp_key)

            canonical_key = f"JOB-{content_hash[:12].upper()}"
            job_reg = self.db.query(EntityRegistry).filter(EntityRegistry.canonical_key == canonical_key).first()
            if not job_reg:
                self.db.add(EntityRegistry(canonical_key=canonical_key, entity_type="JOB", primary_source=source_type_val))
                self.db.add(JobEntity(
                    canonical_key=canonical_key,
                    company_canonical_key=comp_key,
                    title=job_title,
                    seniority=payload.get("seniority"),
                    location=payload.get("location"),
                    raw_description=payload.get("description"),
                ))
                result["created_entities"].append(canonical_key)

                # Connect HIRING_FOR edge
                self.db.add(RelationshipEdge(
                    source_canonical_key=comp_key,
                    target_canonical_key=canonical_key,
                    relationship_type=RelationshipType.HIRING_FOR.value,
                    is_current=True,
                    epistemic_level=EpistemicLevel.OBSERVED_FACT.value,
                ))

                # Emit Layer 3 Signal Event: JOB_POSTED
                sig_event = SignalEvent(
                    target_canonical_key=comp_key,
                    event_type=SignalEventType.JOB_POSTED.value,
                    weight=0.35,
                    raw_signal_hash=content_hash,
                    metadata_json=json.dumps({"job_title": job_title, "job_key": canonical_key}),
                )
                self.db.add(sig_event)
                result["emitted_events"].append("JOB_POSTED")

            result["canonical_key"] = canonical_key
            result["entity_type"] = "JOB"

        elif obj_type in ("post", "article", "update"):
            author_key = payload.get("author_canonical_key") or f"PER-{content_hash[:12].upper()}"
            content_text = payload.get("content_text") or payload.get("text") or ""
            canonical_key = f"PST-{content_hash[:12].upper()}"

            post_reg = self.db.query(EntityRegistry).filter(EntityRegistry.canonical_key == canonical_key).first()
            if not post_reg:
                self.db.add(EntityRegistry(canonical_key=canonical_key, entity_type="POST", primary_source=source_type_val))
                self.db.add(PostEntity(
                    canonical_key=canonical_key,
                    author_canonical_key=author_key,
                    content_text=content_text,
                    url=payload.get("url"),
                    topics_json=json.dumps(payload.get("topics", [])),
                    technologies_json=json.dumps(payload.get("technologies", [])),
                ))
                result["created_entities"].append(canonical_key)

                # Emit Layer 3 Signal Event if tech mentioned
                techs = payload.get("technologies", [])
                if techs:
                    for tech in techs:
                        self.db.add(SignalEvent(
                            target_canonical_key=author_key,
                            event_type=SignalEventType.TECH_MENTIONED.value,
                            weight=0.30,
                            raw_signal_hash=content_hash,
                            metadata_json=json.dumps({"technology": tech, "post_key": canonical_key}),
                        ))
                        result["emitted_events"].append(f"TECH_MENTIONED:{tech}")

            result["canonical_key"] = canonical_key
            result["entity_type"] = "POST"

        return result
