"""
TalentOps AI - Person Identity Resolution Engine
Multi-signal weighted identity matching with non-destructive candidate queues.
Never overwrites uncertain identities: AUTO_MERGE (>= 0.90), REVIEW (0.60-0.89), REJECT (< 0.60).
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from ..models.data_quality_models import (
    PersonIdentity,
    CandidateIdentityMatch,
    PersonContactHistory,
    FieldObservation,
)
from .email_quality_engine import EmailQualityEngine

logger = logging.getLogger("talentops.person_resolver")


@dataclass
class IdentityMatchEvaluation:
    match_score: float              # 0.0 - 1.0
    decision: str                   # AUTO_MERGE, REVIEW, REJECT
    matched_person: Optional[PersonIdentity] = None
    evidence: list[dict[str, Any]] = field(default_factory=list)
    confidence_breakdown: dict[str, float] = field(default_factory=dict)
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_score": round(self.match_score, 2),
            "decision": self.decision,
            "matched_person_id": self.matched_person.id if self.matched_person else None,
            "evidence": self.evidence,
            "confidence_breakdown": self.confidence_breakdown,
            "rationale": self.rationale,
        }


class PersonIdentityResolver:
    """
    Resolves incoming person observations against canonical database entities.
    Safely clusters and queues candidates without destroying data.
    """

    AUTO_MERGE_THRESHOLD = 0.90
    REVIEW_THRESHOLD = 0.60

    def __init__(self, db: Session) -> None:
        self.db = db

    def resolve(
        self,
        candidate_data: dict[str, Any],
        owner_user_id: int,
        source: str = "scout_edge",
    ) -> Tuple[PersonIdentity, IdentityMatchEvaluation]:
        """
        Main entry point: Evaluates candidate against existing canonical identities.
        - If AUTO_MERGE: updates existing PersonIdentity.
        - If REVIEW: links to existing but creates CandidateIdentityMatch review item.
        - If REJECT: creates a brand new PersonIdentity.
        """
        eval_res = self.evaluate_match(candidate_data, owner_user_id)

        if eval_res.decision == "AUTO_MERGE" and eval_res.matched_person:
            person = self._merge_person(eval_res.matched_person, candidate_data, eval_res, source)
            return person, eval_res
        elif eval_res.decision == "REVIEW" and eval_res.matched_person:
            # Non-destructive queue: Create CandidateIdentityMatch record
            match_record = CandidateIdentityMatch(
                canonical_person_id=eval_res.matched_person.id,
                candidate_name=candidate_data.get("name") or candidate_data.get("canonical_name", "Unknown"),
                candidate_title=candidate_data.get("title"),
                candidate_company=candidate_data.get("company"),
                candidate_email=candidate_data.get("email"),
                candidate_profile_url=candidate_data.get("linkedin_url") or candidate_data.get("source_url"),
                source=source,
                match_score=eval_res.match_score,
                evidence_json=json.dumps(eval_res.evidence),
                status="REVIEW",
            )
            self.db.add(match_record)
            self.db.commit()
            return eval_res.matched_person, eval_res
        else:
            # Brand new identity
            person = self._create_new_person(candidate_data, owner_user_id, source)
            return person, eval_res

    def evaluate_match(
        self,
        candidate_data: dict[str, Any],
        owner_user_id: int,
    ) -> IdentityMatchEvaluation:
        """
        Compares candidate against all existing PersonIdentity records for user.
        Calculates weighted match points.
        """
        c_name = (candidate_data.get("name") or candidate_data.get("canonical_name") or "").strip()
        c_email = (candidate_data.get("email") or "").strip().lower()
        c_url = (candidate_data.get("linkedin_url") or candidate_data.get("source_url") or "").strip().lower()
        c_comp = (candidate_data.get("company") or candidate_data.get("company_name") or "").strip().lower()
        c_title = (candidate_data.get("title") or "").strip().lower()

        # Query potential matches (filter by user)
        query = self.db.query(PersonIdentity).filter(PersonIdentity.owner_user_id == owner_user_id)

        best_score = 0.0
        best_person: Optional[PersonIdentity] = None
        best_evidence: list[dict[str, Any]] = []
        best_breakdown: dict[str, float] = {}

        for person in query.limit(200).all():
            points = 0.0
            evidence = []
            breakdown = {}

            # 1. Corporate Email Match (+35 pts)
            p_email = (person.primary_email or "").strip().lower()
            if c_email and p_email and c_email == p_email:
                points += 35.0
                breakdown["email_match"] = 35.0
                evidence.append({"signal": "VERIFIED_EMAIL_EXACT_MATCH", "weight": 35.0, "value": c_email})

            # 2. Canonical Profile URL Slug Match (+35 pts)
            p_url = (person.canonical_profile_url or "").strip().lower()
            if c_url and p_url:
                c_slug = c_url.split("?")[0].rstrip("/").split("/")[-1]
                p_slug = p_url.split("?")[0].rstrip("/").split("/")[-1]
                if c_slug and p_slug and c_slug == p_slug:
                    points += 35.0
                    breakdown["profile_url_match"] = 35.0
                    evidence.append({"signal": "PROFILE_SLUG_MATCH", "weight": 35.0, "value": c_slug})

            # 3. Direct Phone Line Match (+25 pts)
            c_phone = (candidate_data.get("phone") or candidate_data.get("primary_phone") or "").strip()
            p_phone = (person.primary_phone or "").strip()
            if c_phone and p_phone:
                c_clean_phone = re.sub(r"[^\d]", "", c_phone)
                p_clean_phone = re.sub(r"[^\d]", "", p_phone)
                if c_clean_phone and p_clean_phone and (c_clean_phone == p_clean_phone or c_clean_phone.endswith(p_clean_phone[-7:]) or p_clean_phone.endswith(c_clean_phone[-7:])):
                    points += 25.0
                    breakdown["phone_match"] = 25.0
                    evidence.append({"signal": "PHONE_MATCH", "weight": 25.0, "value": c_phone})

            # 4. Canonical Company Match (+20 pts)
            p_comp = (person.current_company or "").strip().lower()
            if c_comp and p_comp:
                if c_comp == p_comp or c_comp in p_comp or p_comp in c_comp:
                    points += 20.0
                    breakdown["company_match"] = 20.0
                    evidence.append({"signal": "COMPANY_MATCH", "weight": 20.0, "value": person.current_company})

            # 5. Name Compatibility Check (+25 pts)
            p_name = (person.canonical_name or "").strip().lower()
            if c_name and p_name:
                name_sim = self._calculate_name_similarity(c_name.lower(), p_name)
                if name_sim >= 0.85:
                    points += 25.0
                    breakdown["name_match"] = 25.0
                    evidence.append({"signal": "NAME_COMPATIBLE", "weight": 25.0, "value": person.canonical_name})
                elif name_sim < 0.30:
                    # Incompatible name strongly downgrades score to prevent false collision
                    points -= 40.0
                    evidence.append({"signal": "NAME_CONFLICT", "weight": -40.0, "value": f"{c_name} != {p_name}"})

            # 6. Secondary Email Name Correlation (+15 pts)
            if c_email and "@" in c_email and (not p_email or c_email != p_email):
                local_part = c_email.split("@")[0].lower()
                local_sim = self._calculate_name_similarity(local_part, p_name)
                if local_sim >= 0.50 or any(part in local_part for part in p_name.split() if len(part) > 2):
                    points += 15.0
                    breakdown["email_username_match"] = 15.0
                    evidence.append({"signal": "EMAIL_USERNAME_NAME_MATCH", "weight": 15.0, "value": c_email})

            # 7. Job Title Match (+10 pts)
            p_title = (person.current_title or "").strip().lower()
            if c_title and p_title:
                if c_title == p_title or c_title in p_title or p_title in c_title:
                    points += 10.0
                    breakdown["title_match"] = 10.0
                    evidence.append({"signal": "TITLE_MATCH", "weight": 10.0, "value": person.current_title})

            norm_score = max(0.0, min(1.0, points / 100.0))
            if norm_score > best_score:
                best_score = norm_score
                best_person = person
                best_evidence = evidence
                best_breakdown = breakdown

        # Decision based on threshold
        if best_score >= self.AUTO_MERGE_THRESHOLD:
            decision = "AUTO_MERGE"
            rationale = f"High confidence match ({best_score:.2f}) exceeds auto-merge floor (0.90)"
        elif best_score >= self.REVIEW_THRESHOLD:
            decision = "REVIEW"
            rationale = f"Moderate match ({best_score:.2f}) requires human confirmation (0.60-0.89)"
        else:
            decision = "REJECT"
            rationale = "No compatible existing identity found (distinct person)"

        return IdentityMatchEvaluation(
            match_score=best_score,
            decision=decision,
            matched_person=best_person,
            evidence=best_evidence,
            confidence_breakdown=best_breakdown,
            rationale=rationale,
        )

    def _create_new_person(
        self,
        data: dict[str, Any],
        owner_user_id: int,
        source: str,
    ) -> PersonIdentity:
        """Create new canonical PersonIdentity with initial contact history and observations."""
        canonical_id = f"PER-{uuid.uuid4().hex[:8].upper()}"
        name = data.get("name") or data.get("canonical_name", "Unknown Lead")
        email = data.get("email")
        company = data.get("company") or data.get("company_name")
        title = data.get("title")
        url = data.get("linkedin_url") or data.get("source_url")

        # Evaluate email quality
        eq_res = EmailQualityEngine.evaluate(
            email=email or "",
            person_name=name,
            company_name=company,
        ) if email else None

        person = PersonIdentity(
            canonical_id=canonical_id,
            canonical_name=name,
            current_title=title,
            current_company=company,
            canonical_profile_url=url,
            primary_email=email,
            primary_phone=data.get("phone"),
            location=data.get("location"),
            email_status=eq_res.mailbox_status if eq_res else "UNKNOWN",
            email_syntax_valid=eq_res.syntax_valid if eq_res else False,
            email_domain_valid=eq_res.domain_valid if eq_res else False,
            email_mx_valid=eq_res.mx_valid if eq_res else False,
            email_role_type=eq_res.role_type if eq_res else "individual",
            email_quality_score=eq_res.quality_score if eq_res else 0.0,
            identity_confidence=0.85 if url else 0.70,
            freshness_score=100.0,
            overall_quality_score=80.0 if email and eq_res.syntax_valid else 65.0,
            owner_user_id=owner_user_id,
        )
        self.db.add(person)
        self.db.commit()
        self.db.refresh(person)

        # Record Initial Contact History
        if email:
            self.db.add(PersonContactHistory(
                person_identity_id=person.id,
                contact_type="email",
                contact_value=email,
                status="current",
                reason="Initial observation",
            ))
        if company:
            self.db.add(PersonContactHistory(
                person_identity_id=person.id,
                contact_type="company",
                contact_value=company,
                status="current",
                reason="Initial employer affiliation",
            ))

        # Record Field Observations
        for f_name, f_val in [("name", name), ("title", title), ("company", company), ("email", email)]:
            if f_val:
                self.db.add(FieldObservation(
                    entity_type="PERSON",
                    entity_id=person.id,
                    field_name=f_name,
                    field_value=str(f_val),
                    source=source,
                    confidence=0.90,
                ))

        self.db.commit()
        return person

    def _merge_person(
        self,
        person: PersonIdentity,
        new_data: dict[str, Any],
        eval_res: IdentityMatchEvaluation,
        source: str,
    ) -> PersonIdentity:
        """Enrich existing canonical person and record contact history deltas."""
        new_title = new_data.get("title")
        new_company = new_data.get("company") or new_data.get("company_name")
        new_email = new_data.get("email")

        # Check for company transition
        if new_company and person.current_company and new_company.lower() != person.current_company.lower():
            # Old company becomes historical
            self.db.add(PersonContactHistory(
                person_identity_id=person.id,
                contact_type="company",
                contact_value=person.current_company,
                status="historical",
                reason="Company transition observed",
            ))
            # If email domain belonged to old company, mark email historical too!
            if person.primary_email and not any(d in person.primary_email for d in ["gmail", "yahoo", "outlook"]):
                self.db.add(PersonContactHistory(
                    person_identity_id=person.id,
                    contact_type="email",
                    contact_value=person.primary_email,
                    status="historical",
                    reason="Previous corporate email invalidated by company change",
                ))
            person.current_company = new_company

        # Check for role promotion
        if new_title and new_title != person.current_title:
            self.db.add(PersonContactHistory(
                person_identity_id=person.id,
                contact_type="title",
                contact_value=person.current_title or "Unknown",
                status="historical",
                reason="Role transition observed",
            ))
            person.current_title = new_title

        # Check for email update
        if new_email and new_email != person.primary_email:
            self.db.add(PersonContactHistory(
                person_identity_id=person.id,
                contact_type="email",
                contact_value=new_email,
                status="current",
                reason="New primary email discovered",
            ))
            person.primary_email = new_email

        person.identity_confidence = min(0.99, person.identity_confidence + 0.05)
        person.overall_quality_score = min(100.0, person.overall_quality_score + 5.0)

        self.db.commit()
        self.db.refresh(person)
        return person

    @classmethod
    def _calculate_name_similarity(cls, name_a: str, name_b: str) -> float:
        """Compares two names for fuzzy matching."""
        if name_a == name_b:
            return 1.0
        parts_a = set(name_a.split())
        parts_b = set(name_b.split())
        intersection = parts_a.intersection(parts_b)
        if len(intersection) >= 2:
            return 0.95
        if len(intersection) == 1 and (len(parts_a) == 1 or len(parts_b) == 1):
            return 0.80
        return len(intersection) / max(len(parts_a), len(parts_b), 1)

    def generate_identity_card(self, person: PersonIdentity) -> dict[str, Any]:
        """
        Produces the Person Identity Card detailing multi-dimension scores,
        currentness, deliverability, and audit evidence.
        """
        contacts = self.db.query(PersonContactHistory).filter(
            PersonContactHistory.person_identity_id == person.id
        ).order_by(PersonContactHistory.created_at.desc()).all()

        observations = self.db.query(FieldObservation).filter(
            FieldObservation.entity_type == "PERSON",
            FieldObservation.entity_id == person.id,
        ).order_by(FieldObservation.observed_at.desc()).limit(20).all()

        history_items = [
            {
                "type": c.contact_type,
                "value": c.contact_value,
                "status": c.status,
                "valid_from": c.valid_from.isoformat() if c.valid_from else None,
                "valid_to": c.valid_to.isoformat() if c.valid_to else None,
                "reason": c.reason,
            }
            for c in contacts
        ]

        evidence_items = [
            {
                "field": o.field_name,
                "value": o.field_value,
                "source": o.source,
                "confidence": o.confidence,
                "observed_at": o.observed_at.isoformat() if o.observed_at else None,
            }
            for o in observations
        ]

        return {
            "person_id": person.id,
            "canonical_id": person.canonical_id,
            "canonical_name": person.canonical_name,
            "current_title": person.current_title or "Unspecified Role",
            "current_company": person.current_company or "Unspecified Company",
            "canonical_profile_url": person.canonical_profile_url,
            "linkedin_url": person.canonical_profile_url,
            "primary_email": person.primary_email,
            "email_status": person.email_status,
            "email_deliverability": person.email_status,
            "email_quality_score": round(person.email_quality_score, 1),
            "identity_confidence": round(person.identity_confidence, 2),
            "freshness_score": round(person.freshness_score, 1),
            "observations_count": len(observations) or 1,
            "quality_dimensions": {
                "person_quality": round(person.person_quality_score, 1),
                "email_quality": round(person.email_quality_score, 1),
                "company_quality": round(person.company_quality_score, 1),
                "domain_quality": round(person.domain_quality_score, 1),
                "identity_confidence": round(person.identity_confidence * 100, 1),
                "freshness_score": round(person.freshness_score, 1),
                "overall_quality": round(person.overall_quality_score, 1),
            },
            "contact_history": history_items,
            "field_observations": evidence_items,
            "field_provenance_evidence": evidence_items,
            "created_at": person.created_at.isoformat() if person.created_at else None,
            "last_verified_at": person.verified_at.isoformat() if person.verified_at else None,
        }
