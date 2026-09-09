"""
TalentOps AI - Proactive Self-Healing Contact Probes (SelfHealingProbe 2.0)
Automatically resolves contact gaps when job shifts occur:
- Detects employment transitions via TemporalReconciler and PersonContactHistory.
- Retrieves canonical corporate domain and email syntax patterns.
- Synthesizes candidate email options and evaluates them via EmailQualityEngine.
- Stages ready-to-approve Level 3 DataCorrectionProposals in the Before/After review queue.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..models.data_quality_models import (
    PersonIdentity,
    CompanyMaster,
    DataCorrectionProposal,
    PersonContactHistory,
)
from .email_quality_engine import EmailQualityEngine
from .temporal_reconciler import TemporalReconciler

logger = logging.getLogger("talentops.self_healing_probe")


class SelfHealingProbe:
    """
    Proactive Self-Healing Contact Probing Engine.
    """

    def __init__(self, db: Session):
        self.db = db
        self.reconciler = TemporalReconciler()

    def probe_and_heal_person(
        self,
        person_id: int,
        new_company: Optional[str] = None,
        person_obj: Optional[PersonIdentity] = None,
        company_cache: Optional[Dict[str, Any]] = None,
        existing_props_set: Optional[set] = None,
        auto_commit: bool = True,
    ) -> Dict[str, Any]:
        """
        Runs proactive probe for a person experiencing a career shift or missing contact info.
        Supports caching and batch commits for ultra-low latency.
        """
        person = person_obj or self.db.query(PersonIdentity).filter(PersonIdentity.id == person_id).first()
        if not person:
            return {"status": "ERROR", "message": "Person not found"}

        target_company_name = (new_company or person.current_company or "").strip()
        if not target_company_name:
            return {"status": "SKIPPED", "reason": "No target company available to probe"}

        # 1. Identify canonical company & domain (with cache support)
        comp_key = target_company_name.lower()
        company = None
        if company_cache is not None and comp_key in company_cache:
            company = company_cache[comp_key]
        else:
            company = self.db.query(CompanyMaster).filter(
                CompanyMaster.canonical_name.ilike(target_company_name)
            ).first()
            if company_cache is not None:
                company_cache[comp_key] = company

        domain = None
        known_pattern = None

        if company:
            domain = company.primary_domain
            if company.email_domains:
                try:
                    domains_meta = json.loads(company.email_domains)
                    if isinstance(domains_meta, dict):
                        known_pattern = domains_meta.get(domain)
                except Exception:
                    pass

        # Fallback domain generation if not registered
        if not domain:
            cleaned_comp = target_company_name.lower().replace(" ", "").replace(",", "").replace(".", "")
            domain = f"{cleaned_comp}.com"

        # 2. Parse person name
        name = (person.canonical_name or "").strip().lower()
        parts = name.split()
        if not parts:
            return {"status": "SKIPPED", "reason": "Person has no name to generate patterns"}

        first = parts[0]
        last = parts[-1] if len(parts) > 1 else "candidate"

        # 3. Generate Candidate Email Patterns
        candidate_patterns: List[str] = []
        if known_pattern:
            synth = known_pattern.replace("{first}", first).replace("{last}", last).replace("{f}", first[0]).replace("{l}", last[0]).replace("{domain}", domain)
            if "@" not in synth:
                synth = f"{synth}@{domain}"
            candidate_patterns.append(synth)

        # Standard industry patterns in order of popularity
        candidate_patterns.extend([
            f"{first}.{last}@{domain}",
            f"{first[0]}{last}@{domain}",
            f"{first}@{domain}",
            f"{first}{last[0]}@{domain}",
        ])

        # Deduplicate preserving order
        candidate_patterns = list(dict.fromkeys(candidate_patterns))

        proposals_generated: List[Dict[str, Any]] = []

        # 4. Probe each candidate email via EmailQualityEngine (fast-path)
        best_candidate = None
        best_result = None

        for email_addr in candidate_patterns:
            eval_res = EmailQualityEngine.evaluate(
                email=email_addr,
                person_name=person.canonical_name,
                company_name=target_company_name,
                company_domain=domain,
                skip_live_dns=True,  # fast-path validation for internal probing
            )

            if eval_res.syntax_valid and eval_res.domain_valid:
                best_candidate = email_addr
                best_result = eval_res
                break

        # 5. Stage DataCorrectionProposal if high confidence candidate found
        if best_candidate and best_result:
            already_exists = False
            if existing_props_set is not None:
                already_exists = (person.id, best_candidate) in existing_props_set
            else:
                existing_prop = self.db.query(DataCorrectionProposal).filter(
                    DataCorrectionProposal.entity_type == "PERSON",
                    DataCorrectionProposal.entity_id == person.id,
                    DataCorrectionProposal.field_name == "primary_email",
                    DataCorrectionProposal.proposed_value == best_candidate,
                    DataCorrectionProposal.status.in_(["PROPOSED", "APPROVED", "PROMOTED"]),
                ).first()
                already_exists = existing_prop is not None

            if not already_exists:
                prop_code = f"PROP-HEAL-{uuid.uuid4().hex[:6].upper()}"
                prop = DataCorrectionProposal(
                    proposal_id=prop_code,
                    entity_type="PERSON",
                    entity_id=person.id,
                    field_name="primary_email",
                    old_value=person.primary_email,
                    proposed_value=best_candidate,
                    reason=(
                        f"Proactive self-healing probe: Synthesized corporate email for career transition "
                        f"to '{target_company_name}' at domain '{domain}'. Quality score: {best_result.quality_score}/100."
                    ),
                    evidence_ids=json.dumps([f"domain:{domain}", f"pattern:{best_candidate}"]),
                    evidence_ladder_level=3,  # Level 3 Domain Pattern Derivation
                    confidence=0.88,
                    source="self_healing_probe_2.0",
                    category="VALIDATED_AUTO_FIX",
                    status="PROPOSED",
                    owner_user_id=person.owner_user_id,
                )
                self.db.add(prop)
                if auto_commit:
                    self.db.commit()

                if existing_props_set is not None:
                    existing_props_set.add((person.id, best_candidate))

                proposals_generated.append({
                    "proposal_id": prop_code,
                    "synthesized_email": best_candidate,
                    "confidence": 0.88,
                    "quality_score": best_result.quality_score,
                })

        return {
            "status": "COMPLETED",
            "person_id": person.id,
            "target_company": target_company_name,
            "domain": domain,
            "probed_patterns_count": len(candidate_patterns),
            "proposals_generated": proposals_generated,
        }

    def scan_and_heal_transitions(
        self, owner_user_id: int = 1, limit: int = 50
    ) -> Dict[str, Any]:
        """
        Scans candidates with detected career transitions or missing work emails
        and runs proactive self-healing probes using high-performance batch operations.
        """
        # Find candidates who have a current company but missing/undeliverable email
        candidates = self.db.query(PersonIdentity).filter(
            PersonIdentity.owner_user_id == owner_user_id,
            PersonIdentity.current_company.isnot(None),
            (
                (PersonIdentity.primary_email.is_(None)) |
                (PersonIdentity.email_status.in_(["UNDELIVERABLE", "RISKY", "UNKNOWN"]))
            ),
        ).limit(limit).all()

        if not candidates:
            return {
                "candidates_evaluated": 0,
                "proposals_staged": 0,
                "details": [],
            }

        # Preload existing proposals into a memory set for O(1) duplicate checks
        candidate_ids = [c.id for c in candidates]
        existing_props = self.db.query(
            DataCorrectionProposal.entity_id, DataCorrectionProposal.proposed_value
        ).filter(
            DataCorrectionProposal.entity_type == "PERSON",
            DataCorrectionProposal.entity_id.in_(candidate_ids),
            DataCorrectionProposal.field_name == "primary_email",
            DataCorrectionProposal.status.in_(["PROPOSED", "APPROVED", "PROMOTED"]),
        ).all()
        existing_props_set = {(p.entity_id, p.proposed_value) for p in existing_props}

        # Company cache to eliminate redundant ILIKE searches
        company_cache: Dict[str, Any] = {}

        healed_count = 0
        details = []

        for p in candidates:
            res = self.probe_and_heal_person(
                person_id=p.id,
                person_obj=p,
                company_cache=company_cache,
                existing_props_set=existing_props_set,
                auto_commit=False,
            )
            if res.get("proposals_generated"):
                healed_count += len(res["proposals_generated"])
                details.append(res)

        # Single batch commit for all staged proposals
        if healed_count > 0:
            self.db.commit()

        return {
            "candidates_evaluated": len(candidates),
            "proposals_staged": healed_count,
            "details": details,
        }
