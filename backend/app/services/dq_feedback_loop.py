"""
TalentOps AI - Data Quality Active Learning & Feedback Loop (DQFeedbackLoop 2.0)
Translates human review interactions (approvals, rejections, keep-both)
into continuous model and heuristic improvements:
- Automatically promotes company name variants to canonical CompanyAlias with confidence 1.0.
- Extracts and registers corporate email syntax templates for recognized employer domains.
- Automatically inserts rejected duplicate pairs into DissimilarityBlocklist to prevent repeated false positives.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..models.data_quality_models import (
    DataCorrectionProposal,
    CompanyMaster,
    CompanyAlias,
    DissimilarityBlocklist,
    PersonIdentity,
)

logger = logging.getLogger("talentops.dq_feedback_loop")


class DQFeedbackLoop:
    """
    Active Learning Engine listening to administrative data quality decisions
    to refine knowledge graph heuristics in real-time.
    """

    def __init__(self, db: Session):
        self.db = db

    # ── Approval Signal Processing ────────────────────────────────────────────

    def on_proposal_approved(
        self, proposal: DataCorrectionProposal, actor: str = "ADMIN_USER"
    ) -> Dict[str, Any]:
        """
        Processes human approval of a repair proposal:
        1. If company field was corrected: registers old value as canonical alias.
        2. If email was corrected: derives and registers company email syntax pattern.
        """
        feedback_results: Dict[str, Any] = {
            "proposal_id": proposal.proposal_id,
            "action": "APPROVED",
            "aliases_learned": [],
            "email_patterns_learned": [],
        }

        # 1. Company Name Alias Learning
        if proposal.field_name in ("current_company", "company_name", "canonical_name") and proposal.entity_type in ("PERSON", "COMPANY"):
            old_company = (proposal.old_value or "").strip()
            new_company = (proposal.proposed_value or "").strip()

            if old_company and new_company and old_company.lower() != new_company.lower():
                # Find or create target CompanyMaster
                company_master = self.db.query(CompanyMaster).filter(
                    CompanyMaster.canonical_name.ilike(new_company)
                ).first()

                if not company_master:
                    import uuid
                    company_master = CompanyMaster(
                        canonical_id=f"COMP-{uuid.uuid4().hex[:8].upper()}",
                        canonical_name=new_company,
                        domain_confidence=0.90,
                    )
                    self.db.add(company_master)
                    self.db.flush()

                # Check if alias already registered
                existing_alias = self.db.query(CompanyAlias).filter(
                    CompanyAlias.company_master_id == company_master.id,
                    CompanyAlias.alias_name.ilike(old_company),
                ).first()

                if not existing_alias:
                    alias_entry = CompanyAlias(
                        company_master_id=company_master.id,
                        alias_name=old_company,
                        source=f"active_learning:{actor}",
                        confidence=1.0,
                    )
                    self.db.add(alias_entry)
                    feedback_results["aliases_learned"].append({
                        "canonical": new_company,
                        "alias": old_company,
                        "confidence": 1.0,
                    })
                    logger.info("Active Learning: Promoted alias '%s' -> '%s'", old_company, new_company)

        # 2. Corporate Email Pattern Learning
        if proposal.field_name in ("primary_email", "email") and proposal.proposed_value:
            new_email = proposal.proposed_value.strip().lower()
            if "@" in new_email:
                local_part, domain = new_email.split("@", 1)
                # Find person to match first/last name
                person = self.db.query(PersonIdentity).filter(PersonIdentity.id == proposal.entity_id).first()
                if person and person.canonical_name:
                    name_parts = person.canonical_name.strip().lower().split()
                    if len(name_parts) >= 2:
                        first, last = name_parts[0], name_parts[-1]
                        pattern_detected = None
                        if local_part == f"{first}.{last}":
                            pattern_detected = "{first}.{last}"
                        elif local_part == f"{first[0]}{last}":
                            pattern_detected = "{f}{last}"
                        elif local_part == f"{first}{last[0]}":
                            pattern_detected = "{first}{l}"
                        elif local_part == first:
                            pattern_detected = "{first}"
                        elif local_part == f"{last}.{first}":
                            pattern_detected = "{last}.{first}"

                        if pattern_detected:
                            # Update company master email domains
                            comp = None
                            if person.current_company:
                                comp = self.db.query(CompanyMaster).filter(
                                    CompanyMaster.canonical_name.ilike(person.current_company.strip())
                                ).first()

                            if comp:
                                try:
                                    domains_meta = json.loads(comp.email_domains) if comp.email_domains else {}
                                except Exception:
                                    domains_meta = {}

                                domains_meta[domain] = pattern_detected
                                comp.email_domains = json.dumps(domains_meta)
                                comp.primary_domain = comp.primary_domain or domain
                                feedback_results["email_patterns_learned"].append({
                                    "company": comp.canonical_name,
                                    "domain": domain,
                                    "pattern": pattern_detected,
                                })
                                logger.info("Active Learning: Registered email pattern '%s' for '%s'", pattern_detected, domain)

        self.db.commit()
        return feedback_results

    # ── Rejection Signal Processing ───────────────────────────────────────────

    def on_proposal_rejected(
        self, proposal: DataCorrectionProposal, actor: str = "ADMIN_USER", reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processes human rejection of a repair proposal:
        If proposal was a deduplication merge, blocks the two entities from future merge attempts.
        """
        feedback_results: Dict[str, Any] = {
            "proposal_id": proposal.proposal_id,
            "action": "REJECTED",
            "dissimilarity_blocked": False,
        }

        # Check if this was a deduplication proposal
        is_dedup = "DEDUP" in (proposal.proposal_id or "") or "deduplication" in (proposal.reason or "").lower()

        if is_dedup and proposal.entity_type == "PERSON":
            entity_a = proposal.entity_id
            entity_b = None

            # Attempt to locate entity_b from proposed canonical_id or reason text
            if proposal.field_name == "canonical_id" and proposal.proposed_value:
                target_p = self.db.query(PersonIdentity).filter(
                    PersonIdentity.canonical_id == proposal.proposed_value
                ).first()
                if target_p:
                    entity_b = target_p.id

            if not entity_b:
                match = re.search(r"person #(\d+)", proposal.reason or "")
                if match:
                    entity_b = int(match.group(1))

            if entity_a and entity_b and entity_a != entity_b:
                existing_block = self.db.query(DissimilarityBlocklist).filter(
                    DissimilarityBlocklist.entity_type == "PERSON",
                    DissimilarityBlocklist.entity_a_id == min(entity_a, entity_b),
                    DissimilarityBlocklist.entity_b_id == max(entity_a, entity_b),
                ).first()

                if not existing_block:
                    block = DissimilarityBlocklist(
                        entity_type="PERSON",
                        entity_a_id=min(entity_a, entity_b),
                        entity_b_id=max(entity_a, entity_b),
                        reason=reason or f"Human admin rejected merge proposal {proposal.proposal_id}",
                    )
                    self.db.add(block)
                    self.db.commit()
                    feedback_results["dissimilarity_blocked"] = True
                    feedback_results["entity_a_id"] = entity_a
                    feedback_results["entity_b_id"] = entity_b
                    logger.info("Active Learning: Added permanent dissimilarity block between #%d and #%d", entity_a, entity_b)

        return feedback_results

    # ── Query Helper ──────────────────────────────────────────────────────────

    def is_pair_blocked(self, entity_a_id: int, entity_b_id: int, entity_type: str = "PERSON") -> bool:
        """
        Fast lookup to verify if two entities are blocklisted from merging.
        """
        low_id = min(entity_a_id, entity_b_id)
        high_id = max(entity_a_id, entity_b_id)
        match = self.db.query(DissimilarityBlocklist).filter(
            DissimilarityBlocklist.entity_type == entity_type,
            DissimilarityBlocklist.entity_a_id == low_id,
            DissimilarityBlocklist.entity_b_id == high_id,
        ).first()
        return match is not None

    def get_learning_stats(self) -> Dict[str, Any]:
        """
        Returns aggregate statistics of the active learning engine.
        """
        learned_aliases_count = self.db.query(CompanyAlias).filter(
            CompanyAlias.source.like("active_learning%")
        ).count()

        blocked_pairs_count = self.db.query(DissimilarityBlocklist).count()

        return {
            "learned_company_aliases": learned_aliases_count,
            "blocked_duplicate_pairs": blocked_pairs_count,
            "feedback_active": True,
        }
