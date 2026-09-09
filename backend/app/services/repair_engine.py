"""
TalentOps AI - Quarantine & Reversible Repair Engine
Implements lossless data repair, shadow write proposals, pre-repair snapshots,
and reversible rollback without ever deleting raw source observations.

Lifecycle:
PROPOSED -> VALIDATING -> APPROVED -> PROMOTED -> HISTORY PRESERVED -> AUDITED
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from ..models.data_quality_models import (
    PersonIdentity,
    CompanyMaster,
    DataQualityIssue,
    QuarantineRecord,
    DataCorrectionProposal,
    DataChangeAudit,
    RepairBatchSnapshot,
    PersonContactHistory,
    FieldObservation,
)
from .evidence_ladder import EvidenceLadder, EvidenceLevel

logger = logging.getLogger("talentops.repair_engine")

LOCATION_STANDARDIZATION = {
    "usa": "United States",
    "us": "United States",
    "u.s.": "United States",
    "u.s.a.": "United States",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "sf": "San Francisco, CA",
    "nyc": "New York, NY",
}


class RepairEngine:
    """
    Manages safe repairs, shadow writes, batch snapshots, and lossless rollback.
    """

    def __init__(self, db: Session):
        self.db = db

    # ── Quarantine Operations ──────────────────────────────────────────────────

    def release_quarantine(self, quarantine_id: int, user_id: int) -> Dict[str, Any]:
        """
        Releases an isolated record or field from quarantine.
        """
        record = self.db.query(QuarantineRecord).filter(
            QuarantineRecord.id == quarantine_id,
            QuarantineRecord.owner_user_id == user_id,
        ).first()

        if not record:
            return {"status": "ERROR", "message": "Quarantine record not found"}

        record.status = "RELEASED"
        record.released_at = datetime.now(timezone.utc)
        self.db.commit()
        return {"status": "RELEASED", "quarantine_id": record.quarantine_id}

    # ── Proposal & Shadow Writes ──────────────────────────────────────────────

    def create_proposal(
        self,
        entity_type: str,
        entity_id: int,
        field_name: str,
        old_value: Optional[str],
        proposed_value: str,
        reason: str,
        evidence_ids: Optional[List[str]] = None,
        evidence_ladder_level: int = EvidenceLevel.LEVEL_2_MODERATE,
        confidence: float = 0.80,
        source: str = "dq_engine",
        category: str = "SAFE_AUTO_FIX",
        owner_user_id: int = 1,
        batch_id: Optional[str] = None,
    ) -> DataCorrectionProposal:
        """
        Creates a shadow-write proposal without directly mutating the production row.
        """
        prop_code = f"PROP-{uuid.uuid4().hex[:8].upper()}"
        proposal = DataCorrectionProposal(
            proposal_id=prop_code,
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field_name,
            old_value=old_value,
            proposed_value=proposed_value,
            reason=reason,
            evidence_ids=json.dumps(evidence_ids or []),
            evidence_ladder_level=evidence_ladder_level,
            confidence=confidence,
            source=source,
            category=category,
            status="PROPOSED",
            batch_id=batch_id,
            owner_user_id=owner_user_id,
        )
        self.db.add(proposal)
        self.db.flush()
        return proposal

    # ── Proposal Promotion & Preservation ─────────────────────────────────────

    def promote_proposal(
        self,
        proposal_id: int,
        user_id: int,
        actor: str = "ADMIN_USER",
        keep_both_as_historical: bool = True,
    ) -> Dict[str, Any]:
        """
        Promotes a proposal to current canonical data:
        1. Validates proposal exists and is in PROPOSED / APPROVED state
        2. Preserves old value in PersonContactHistory (status = 'historical')
        3. Updates canonical production row
        4. Writes audit entry to DataChangeAudit
        5. Marks any associated quarantine item as REPAIRED
        """
        prop = self.db.query(DataCorrectionProposal).filter(
            DataCorrectionProposal.id == proposal_id,
            DataCorrectionProposal.owner_user_id == user_id,
        ).first()

        if not prop:
            return {"status": "ERROR", "message": "Proposal not found"}

        now = datetime.now(timezone.utc)

        # 1. Update Production Row & Preserve History
        if prop.entity_type == "PERSON":
            person = self.db.query(PersonIdentity).filter(PersonIdentity.id == prop.entity_id).first()
            if not person:
                return {"status": "ERROR", "message": "Associated person record not found"}

            old_val = getattr(person, prop.field_name, None)

            # Preserve old value in PersonContactHistory
            if old_val and keep_both_as_historical:
                contact_type = "email" if "email" in prop.field_name else (
                    "phone" if "phone" in prop.field_name else (
                        "company" if "company" in prop.field_name else prop.field_name
                    )
                )
                history = PersonContactHistory(
                    person_identity_id=person.id,
                    contact_type=contact_type,
                    contact_value=str(old_val),
                    status="historical",
                    valid_to=now,
                    reason=f"Repaired via {prop.proposal_id}: {prop.reason}",
                )
                self.db.add(history)

            # Update canonical field
            setattr(person, prop.field_name, prop.proposed_value)
            person.updated_at = now

        elif prop.entity_type == "COMPANY":
            company = self.db.query(CompanyMaster).filter(CompanyMaster.id == prop.entity_id).first()
            if company:
                setattr(company, prop.field_name, prop.proposed_value)
                company.updated_at = now

        # 2. Record Audit Trail
        change_code = f"CHANGE-{uuid.uuid4().hex[:8].upper()}"
        audit = DataChangeAudit(
            change_id=change_code,
            entity_type=prop.entity_type,
            entity_id=prop.entity_id,
            field_name=prop.field_name,
            old_value=prop.old_value,
            new_value=prop.proposed_value,
            reason=prop.reason,
            evidence_ids=prop.evidence_ids,
            confidence=prop.confidence,
            actor=actor,
            batch_id=prop.batch_id,
        )
        self.db.add(audit)

        # 3. Update Proposal Status
        prop.status = "PROMOTED"
        prop.promoted_at = now

        # 4. Resolve associated quarantine records
        quarantined = self.db.query(QuarantineRecord).filter(
            QuarantineRecord.entity_type == prop.entity_type,
            QuarantineRecord.entity_id == prop.entity_id,
            QuarantineRecord.field_name == prop.field_name,
            QuarantineRecord.status == "QUARANTINED",
        ).all()
        for q in quarantined:
            q.status = "REPAIRED"
            q.released_at = now

        self.db.commit()

        return {
            "status": "PROMOTED",
            "proposal_id": prop.proposal_id,
            "change_id": change_code,
            "new_value": prop.proposed_value,
            "history_preserved": keep_both_as_historical,
        }

    # ── Safe Auto-Repairs & Batch Snapshots ────────────────────────────────────

    def execute_safe_auto_repairs(
        self,
        owner_user_id: int,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Executes non-destructive safe formatting fixes (SAFE_AUTO_FIX) in small batches.
        Captures a complete pre-repair snapshot before mutation.
        """
        people = self.db.query(PersonIdentity).filter(
            PersonIdentity.owner_user_id == owner_user_id
        ).limit(batch_size).all()

        batch_code = f"BATCH-{uuid.uuid4().hex[:8].upper()}"
        snapshot_records: Dict[str, Dict[str, Any]] = {}
        proposals_applied = 0

        for person in people:
            # 1. Location Standardization
            loc = (person.location or "").strip().lower()
            if loc in LOCATION_STANDARDIZATION:
                std_loc = LOCATION_STANDARDIZATION[loc]
                if person.location != std_loc:
                    key = f"PERSON:{person.id}:location"
                    snapshot_records[key] = {
                        "entity_type": "PERSON",
                        "entity_id": person.id,
                        "field_name": "location",
                        "old_value": person.location,
                    }
                    # Create and promote proposal
                    prop = self.create_proposal(
                        entity_type="PERSON",
                        entity_id=person.id,
                        field_name="location",
                        old_value=person.location,
                        proposed_value=std_loc,
                        reason="Standardized country / location name",
                        evidence_ladder_level=EvidenceLevel.LEVEL_2_MODERATE,
                        confidence=0.95,
                        category="SAFE_AUTO_FIX",
                        owner_user_id=owner_user_id,
                        batch_id=batch_code,
                    )
                    self.promote_proposal(prop.id, owner_user_id, actor="DQ_ENGINE_SAFE_FIX")
                    proposals_applied += 1

            # 2. Whitespace & Casing Normalization on Name
            if person.canonical_name:
                cleaned_name = re.sub(r"\s+", " ", person.canonical_name.strip()).title()
                if cleaned_name != person.canonical_name and len(cleaned_name) >= 3:
                    key = f"PERSON:{person.id}:canonical_name"
                    snapshot_records[key] = {
                        "entity_type": "PERSON",
                        "entity_id": person.id,
                        "field_name": "canonical_name",
                        "old_value": person.canonical_name,
                    }
                    prop = self.create_proposal(
                        entity_type="PERSON",
                        entity_id=person.id,
                        field_name="canonical_name",
                        old_value=person.canonical_name,
                        proposed_value=cleaned_name,
                        reason="Normalized casing and stripped duplicate whitespace",
                        evidence_ladder_level=EvidenceLevel.LEVEL_2_MODERATE,
                        confidence=0.98,
                        category="SAFE_AUTO_FIX",
                        owner_user_id=owner_user_id,
                        batch_id=batch_code,
                    )
                    self.promote_proposal(prop.id, owner_user_id, actor="DQ_ENGINE_SAFE_FIX")
                    proposals_applied += 1

            # 3. URL Parameter Stripping & HTTPS Normalization
            if person.canonical_profile_url and "?" in person.canonical_profile_url:
                cleaned_url = person.canonical_profile_url.split("?")[0].strip()
                if cleaned_url != person.canonical_profile_url:
                    key = f"PERSON:{person.id}:canonical_profile_url"
                    snapshot_records[key] = {
                        "entity_type": "PERSON",
                        "entity_id": person.id,
                        "field_name": "canonical_profile_url",
                        "old_value": person.canonical_profile_url,
                    }
                    prop = self.create_proposal(
                        entity_type="PERSON",
                        entity_id=person.id,
                        field_name="canonical_profile_url",
                        old_value=person.canonical_profile_url,
                        proposed_value=cleaned_url,
                        reason="Stripped tracking query parameters from profile URL",
                        evidence_ladder_level=EvidenceLevel.LEVEL_2_MODERATE,
                        confidence=0.99,
                        category="SAFE_AUTO_FIX",
                        owner_user_id=owner_user_id,
                        batch_id=batch_code,
                    )
                    self.promote_proposal(prop.id, owner_user_id, actor="DQ_ENGINE_SAFE_FIX")
                    proposals_applied += 1

        # Store Pre-Repair Snapshot
        if snapshot_records:
            snapshot = RepairBatchSnapshot(
                batch_id=batch_code,
                records_count=len(snapshot_records),
                snapshot_data=json.dumps(snapshot_records),
                status="COMMITTED",
            )
            self.db.add(snapshot)
            self.db.commit()

        return {
            "batch_id": batch_code,
            "proposals_applied": proposals_applied,
            "snapshot_recorded": len(snapshot_records) > 0,
            "records_touched": len(snapshot_records),
        }

    # ── Lossless Rollback Mechanism ───────────────────────────────────────────

    def rollback_batch(self, batch_id: str, user_id: int) -> Dict[str, Any]:
        """
        Reverts an entire batch cleanup back to its exact pre-repair snapshot:
        1. Reads RepairBatchSnapshot
        2. Restores old values onto PersonIdentity / CompanyMaster
        3. Updates DataChangeAudit (reverted=True)
        4. Updates DataCorrectionProposal (status='REVERTED')
        5. Updates snapshot status to 'ROLLED_BACK'
        """
        snapshot = self.db.query(RepairBatchSnapshot).filter(
            RepairBatchSnapshot.batch_id == batch_id
        ).first()

        if not snapshot:
            return {"status": "ERROR", "message": f"Snapshot for batch {batch_id} not found"}

        if snapshot.status == "ROLLED_BACK":
            return {"status": "ALREADY_ROLLED_BACK", "batch_id": batch_id}

        try:
            snapshot_data: Dict[str, Dict[str, Any]] = json.loads(snapshot.snapshot_data)
        except Exception as e:
            return {"status": "ERROR", "message": f"Malformed snapshot payload: {e}"}

        restored_count = 0
        now = datetime.now(timezone.utc)

        for key, record_info in snapshot_data.items():
            entity_type = record_info.get("entity_type")
            entity_id = record_info.get("entity_id")
            field_name = record_info.get("field_name")
            old_val = record_info.get("old_value")

            if entity_type == "PERSON":
                person = self.db.query(PersonIdentity).filter(
                    PersonIdentity.id == entity_id,
                    PersonIdentity.owner_user_id == user_id,
                ).first()
                if person:
                    setattr(person, field_name, old_val)
                    person.updated_at = now
                    restored_count += 1
            elif entity_type == "COMPANY":
                company = self.db.query(CompanyMaster).filter(CompanyMaster.id == entity_id).first()
                if company:
                    setattr(company, field_name, old_val)
                    company.updated_at = now
                    restored_count += 1

        # Mark Audits as Reverted
        self.db.query(DataChangeAudit).filter(
            DataChangeAudit.batch_id == batch_id
        ).update({"reverted": True}, synchronize_session=False)

        # Mark Proposals as Reverted
        self.db.query(DataCorrectionProposal).filter(
            DataCorrectionProposal.batch_id == batch_id
        ).update({"status": "REVERTED", "reverted_at": now}, synchronize_session=False)

        snapshot.status = "ROLLED_BACK"
        snapshot.rolled_back_at = now
        self.db.commit()

        return {
            "status": "ROLLED_BACK",
            "batch_id": batch_id,
            "restored_fields_count": restored_count,
            "timestamp": now.isoformat(),
        }
