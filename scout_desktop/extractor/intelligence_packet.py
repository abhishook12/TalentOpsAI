"""
TalentOps Scout 2.0 - Intelligence Packet Mode
Structures raw edge observations, field deltas, inferred intent signals,
cryptographic provenance, and explainable decision journals into
cohesive packets for the TalentOps Knowledge Graph.
"""

from __future__ import annotations

import copy
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from scout_desktop.core.provenance import ProvenanceLedger
from scout_desktop.core.change_detector import ChangeResult, ChangeOperation

logger = logging.getLogger("scout.intelligence_packet")


@dataclass
class IntelligencePacket:
    """
    Standard Scout 2.0 Knowledge Graph transmission packet.
    """
    packet_id: str = field(default_factory=lambda: f"PKT-{uuid.uuid4().hex[:10].upper()}")
    scout_node_id: str = field(default_factory=ProvenanceLedger._get_node_identifier)
    version: str = "2.0"
    timestamp: float = field(default_factory=time.time)
    entity: dict[str, Any] = field(default_factory=dict)
    observations: list[dict[str, Any]] = field(default_factory=list)
    changes: list[dict[str, Any]] = field(default_factory=list)
    signals: list[dict[str, Any]] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    decision_journal: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Full serialization for Knowledge Graph ingestion."""
        return {
            "packet_id": self.packet_id,
            "scout_node_id": self.scout_node_id,
            "version": self.version,
            "timestamp": self.timestamp,
            "entity": self.entity,
            "observations": self.observations,
            "changes": self.changes,
            "signals": self.signals,
            "provenance": self.provenance,
            "decision_journal": self.decision_journal,
        }

    def to_legacy_dict(self) -> dict[str, Any]:
        """
        Backward-compatible dictionary format for the legacy staging endpoint.
        """
        ent = self.entity or {}
        return {
            "packet_id": self.packet_id,
            "canonical_name": ent.get("name") or ent.get("canonical_name", ""),
            "recruiter_name": ent.get("name") or ent.get("canonical_name", ""),
            "title": ent.get("title", ""),
            "company_name": ent.get("company", ""),
            "company": ent.get("company", ""),
            "location": ent.get("location", ""),
            "email": ent.get("email", ""),
            "phone": ent.get("phone", ""),
            "linkedin_url": ent.get("linkedin_url") or ent.get("source_url", ""),
            "source_url": ent.get("source_url", ""),
            "confidence": ent.get("confidence", 0.85),
            "observations_count": len(self.observations) or 1,
            "_is_scout_2_packet": True,
        }

    @classmethod
    def create(
        cls,
        entity_data: dict[str, Any],
        change_result: Optional[ChangeResult] = None,
        source_domain: str = "linkedin.com",
        scope_authorization: str = "AUTHORIZED_PROFILE_VIEW",
    ) -> IntelligencePacket:
        """
        Factory to construct a complete Intelligence Packet with derived signals
        and cryptographic provenance.
        """
        packet_id = f"PKT-{uuid.uuid4().hex[:10].upper()}"
        journal: list[str] = []
        journal.append(f"Initialized Scout 2.0 packet {packet_id} for entity {entity_data.get('canonical_id', 'unknown')}")

        # 1. Structure Observations
        observations = []
        if entity_data.get("title"):
            observations.append({
                "type": "ROLE_MENTION",
                "value": entity_data["title"],
                "confidence": 0.90,
            })
        if entity_data.get("company"):
            observations.append({
                "type": "COMPANY_AFFILIATION",
                "value": entity_data["company"],
                "confidence": 0.90,
            })
        for skill in entity_data.get("skills", []):
            observations.append({
                "type": "SKILL_MENTION",
                "value": str(skill),
                "confidence": 0.80,
            })

        # 2. Structure Changes from ChangeResult
        changes = []
        if change_result and change_result.operation != ChangeOperation.IGNORE:
            journal.append(f"Delta engine reported {change_result.operation.value} with priority {change_result.priority.value}")
            for field_name, diff in change_result.delta.items():
                if isinstance(diff, dict) and "new" in diff:
                    changes.append({
                        "field": field_name,
                        "old_value": diff.get("old"),
                        "new_value": diff.get("new"),
                        "operation": change_result.operation.value,
                    })
                else:
                    changes.append({
                        "field": field_name,
                        "new_value": diff,
                        "operation": change_result.operation.value,
                    })

        # 3. Derive Intelligence Signals
        signals = []
        # Signal: Career Velocity if role promotion
        if any(c.get("field") == "title" for c in changes):
            signals.append({
                "signal_type": "CAREER_VELOCITY",
                "score": 0.88,
                "confidence": 0.85,
                "indicators": ["title_transition_observed"],
            })
            journal.append("Derived CAREER_VELOCITY signal (+0.88) due to role change")

        # Signal: Hiring Intent if keywords in title or headline
        title_lower = str(entity_data.get("title", "")).lower()
        if any(kw in title_lower for kw in ["hiring", "talent", "recruiter", "head of", "director", "vp"]):
            signals.append({
                "signal_type": "HIRING_INFLUENCE",
                "score": 0.78,
                "confidence": 0.80,
                "indicators": ["leadership_or_talent_title"],
            })
            journal.append("Derived HIRING_INFLUENCE signal (+0.78)")

        # 4. Generate Cryptographic Provenance
        provenance = ProvenanceLedger.generate_provenance(
            observation_id=packet_id,
            source_domain=source_domain,
            scope_authorization=scope_authorization,
            content_payload=entity_data,
            confidence=entity_data.get("confidence", 0.90),
        )
        journal.append(f"Attached cryptographic provenance with signature {provenance['lineage_signature'][:12]}...")

        return cls(
            packet_id=packet_id,
            version="2.0",
            timestamp=time.time(),
            entity=copy.deepcopy(entity_data),
            observations=observations,
            changes=changes,
            signals=signals,
            provenance=provenance,
            decision_journal=journal,
        )
