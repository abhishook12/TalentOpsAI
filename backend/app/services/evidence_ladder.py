"""
TalentOps AI - Evidence Ladder & Quality Gating Engine
Classifies evidence strength into 5 deterministic tiers and enforces minimum
confidence gating before corrections can be proposed or promoted.

LEVEL 5 - Authoritative: Verified authoritative source (authenticated API, corporate SSO, DNS/MX)
LEVEL 4 - Very Strong: Multiple independent sources agree (>= 2 corroborated observations)
LEVEL 3 - Strong: One trusted source + supporting contextual evidence
LEVEL 2 - Moderate: Pattern + contextual evidence (syntax pattern, directory listing)
LEVEL 1 - Weak: Inference heuristic only (NLP model guess or unstructured text)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("talentops.evidence_ladder")


class EvidenceLevel:
    LEVEL_1_WEAK = 1
    LEVEL_2_MODERATE = 2
    LEVEL_3_STRONG = 3
    LEVEL_4_VERY_STRONG = 4
    LEVEL_5_AUTHORITATIVE = 5

    DESCRIPTIONS = {
        1: "LEVEL 1 — Weak (Inference heuristic only)",
        2: "LEVEL 2 — Moderate (Pattern + contextual evidence)",
        3: "LEVEL 3 — Strong (One trusted source + supporting evidence)",
        4: "LEVEL 4 — Very Strong (Multiple independent sources agree)",
        5: "LEVEL 5 — Authoritative (Verified authoritative source)",
    }


# Minimum Evidence Ladder Level required per field type
FIELD_EVIDENCE_REQUIREMENTS: Dict[str, Tuple[int, float]] = {
    # field_name -> (min_ladder_level, min_confidence)
    "primary_email": (EvidenceLevel.LEVEL_4_VERY_STRONG, 0.85),
    "current_company": (EvidenceLevel.LEVEL_3_STRONG, 0.75),
    "current_title": (EvidenceLevel.LEVEL_3_STRONG, 0.75),
    "primary_phone": (EvidenceLevel.LEVEL_3_STRONG, 0.75),
    "canonical_profile_url": (EvidenceLevel.LEVEL_2_MODERATE, 0.70),
    "location": (EvidenceLevel.LEVEL_2_MODERATE, 0.60),
    "canonical_name": (EvidenceLevel.LEVEL_3_STRONG, 0.80),
}


@dataclass
class EvidenceEvaluation:
    ladder_level: int
    level_name: str
    confidence: float
    meets_requirement: bool
    required_level: int
    required_confidence: float
    reason: str
    corroborating_sources: List[str] = field(default_factory=list)
    evidence_items: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ladder_level": self.ladder_level,
            "level_name": self.level_name,
            "confidence": round(self.confidence, 3),
            "meets_requirement": self.meets_requirement,
            "required_level": self.required_level,
            "required_confidence": round(self.required_confidence, 2),
            "reason": self.reason,
            "corroborating_sources": self.corroborating_sources,
            "evidence_items": self.evidence_items,
        }


class EvidenceLadder:
    """
    Evaluates evidence points, calculates Ladder Tier (1-5), and enforces gating rules.
    """

    @classmethod
    def evaluate(
        cls,
        field_name: str,
        sources: List[str],
        observations: Optional[List[Dict[str, Any]]] = None,
        is_verified_source: bool = False,
        has_contextual_support: bool = False,
        is_pattern_derived: bool = False,
        is_model_inference: bool = False,
    ) -> EvidenceEvaluation:
        """
        Calculates ladder level based on source reliability, multiplicity, and context.
        """
        obs = observations or []
        unique_sources = list(set(s for s in sources if s))
        evidence_items = []

        # Determine level based on evidence strength
        if is_verified_source:
            ladder_level = EvidenceLevel.LEVEL_5_AUTHORITATIVE
            base_conf = 0.98
            reason = "Directly verified via authoritative primary source (API/SSO/DNS)"
            evidence_items.append({"type": "AUTHORITATIVE_SOURCE", "detail": "Direct verified system of record"})
        elif len(unique_sources) >= 2:
            ladder_level = EvidenceLevel.LEVEL_4_VERY_STRONG
            base_conf = 0.90 + min(0.08, (len(unique_sources) - 2) * 0.03)
            reason = f"Confirmed across {len(unique_sources)} independent sources: {', '.join(unique_sources[:3])}"
            evidence_items.append({"type": "MULTI_SOURCE_AGREEMENT", "detail": f"Independent agreement across {len(unique_sources)} sources"})
        elif len(unique_sources) == 1 and has_contextual_support:
            ladder_level = EvidenceLevel.LEVEL_3_STRONG
            base_conf = 0.80
            reason = f"Single trusted source ({unique_sources[0]}) corroborated by contextual evidence"
            evidence_items.append({"type": "CONTEXTUAL_CORROBORATION", "detail": "Corroborated by domain/title context"})
        elif is_pattern_derived or has_contextual_support:
            ladder_level = EvidenceLevel.LEVEL_2_MODERATE
            base_conf = 0.65
            reason = "Derived from contextual pattern matching or directory structure"
            evidence_items.append({"type": "PATTERN_DERIVATION", "detail": "Pattern or format heuristic"})
        else:
            ladder_level = EvidenceLevel.LEVEL_1_WEAK
            base_conf = 0.40
            reason = "Single unverified observation or ungrounded model inference"
            evidence_items.append({"type": "UNGROUNDED_INFERENCE", "detail": "Low-confidence inference"})

        req_level, req_conf = FIELD_EVIDENCE_REQUIREMENTS.get(
            field_name,
            (EvidenceLevel.LEVEL_2_MODERATE, 0.60),
        )

        meets = (ladder_level >= req_level) and (base_conf >= req_conf)

        return EvidenceEvaluation(
            ladder_level=ladder_level,
            level_name=EvidenceLevel.DESCRIPTIONS.get(ladder_level, f"LEVEL {ladder_level}"),
            confidence=base_conf,
            meets_requirement=meets,
            required_level=req_level,
            required_confidence=req_conf,
            reason=reason,
            corroborating_sources=unique_sources,
            evidence_items=evidence_items,
        )

    @classmethod
    def can_auto_promote(cls, field_name: str, ladder_level: int, confidence: float) -> bool:
        """
        Determines whether a proposed change can be auto-promoted without human review.
        """
        req_level, req_conf = FIELD_EVIDENCE_REQUIREMENTS.get(
            field_name,
            (EvidenceLevel.LEVEL_2_MODERATE, 0.60),
        )
        return (ladder_level >= req_level) and (confidence >= req_conf)
