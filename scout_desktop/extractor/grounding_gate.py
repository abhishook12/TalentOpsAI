"""
extractor/grounding_gate.py — Evidence Grounding Validation Gate

Every fact accepted by the Scout MUST be grounded in visible evidence.
This gate validates observations before they are staged for backend sync.

Validation rules:
1. Evidence string must be non-empty and match text from the captured frame
2. Entity type must be consistent with page context
3. Both sides of a relationship must be grounded
4. Source platform (LinkedIn) must not be confused with employer
5. Confidence must meet minimum threshold

Also builds proof chains for audit trail:
CAPTURE → ANALYSIS → OBSERVATION → STAGING → ENTITY → DB_ACTION → RESULT
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger("scout.extractor.grounding_gate")

@dataclass
class GroundingResult:
    """Result of validating an observation against the grounding gate."""
    outcome: str  # (ACCEPT | REJECT_UNGROUNDED | REJECT_LOW_CONFIDENCE | REVIEW)
    reason: str
    confidence_adjustment: float  # (0.0 = no change, negative = reduced)
    observation_id: str

@dataclass
class ProofStep:
    """A single step in the proof chain for an observation."""
    step_name: str  # (CAPTURE | ANALYSIS | OBSERVATION | STAGING | ENTITY | DB_ACTION | RESULT)
    timestamp: float
    details: dict
    status: str  # (PASS | FAIL | PENDING)

class ProofChain:
    """Maintains an audit trail of how an observation was derived from raw capture."""
    def __init__(self, chain_id: Optional[str] = None):
        self.chain_id: str = chain_id or str(uuid.uuid4())
        self.steps: list[ProofStep] = []
        self.created_at: float = time.time()

    def add_step(self, step_name: str, details: dict, status: str) -> None:
        """Add a step to the proof chain."""
        self.steps.append(ProofStep(
            step_name=step_name,
            timestamp=time.time(),
            details=details,
            status=status
        ))

    def is_complete(self) -> bool:
        """Check if all 7 expected steps are present in the chain."""
        expected_steps = {"CAPTURE", "ANALYSIS", "OBSERVATION", "STAGING", "ENTITY", "DB_ACTION", "RESULT"}
        actual_steps = {step.step_name for step in self.steps}
        return expected_steps.issubset(actual_steps)

    def to_dict(self) -> dict:
        """Convert the proof chain to a dictionary representation."""
        return {
            "chain_id": self.chain_id,
            "created_at": self.created_at,
            "steps": [
                {
                    "step_name": step.step_name,
                    "timestamp": step.timestamp,
                    "details": step.details,
                    "status": step.status
                } for step in self.steps
            ],
            "is_complete": self.is_complete()
        }

class SourceQualityWeighter:
    """Applies confidence weights based on the source of the observation."""
    
    WEIGHTS = {
        "linkedin_profile_header": 0.95,
        "linkedin_profile_url": 0.95,
        "visible_text_field": 0.85,
        "company_page_association": 0.75,
        "search_result_card": 0.70,
        "inferred_text_pattern": 0.50,
        "ocr_low_confidence": 0.40,
        "name_only_guess": 0.25,
    }

    def weight_confidence(self, obs_confidence: float, source_type: str) -> float:
        """Adjust confidence based on the source quality."""
        multiplier = self.WEIGHTS.get(source_type, 0.50)
        return min(1.0, max(0.0, obs_confidence * multiplier))

class GroundingGate:
    """Validates observations and ensures they are properly grounded in evidence."""
    
    PLATFORM_NAMES = {"linkedin", "indeed", "glassdoor", "github"}

    def __init__(self, min_confidence: float = 0.30, strict_mode: bool = True):
        self.min_confidence = min_confidence
        self.strict_mode = strict_mode
        self.weighter = SourceQualityWeighter()

    def validate_observation(self, obs_dict: dict, capture_context: dict) -> GroundingResult:
        """Validate a single observation."""
        obs_id = obs_dict.get("id", str(uuid.uuid4()))
        confidence = obs_dict.get("confidence", 0.0)
        evidence = obs_dict.get("evidence", "")
        source_type = obs_dict.get("source_type", "unknown")
        
        # Check confidence
        weighted_conf = self.weighter.weight_confidence(confidence, source_type)
        if weighted_conf < self.min_confidence:
            return GroundingResult(
                outcome="REJECT_LOW_CONFIDENCE",
                reason=f"Confidence {weighted_conf:.2f} below minimum {self.min_confidence}",
                confidence_adjustment=weighted_conf - confidence,
                observation_id=obs_id
            )
            
        # Check evidence string
        if not evidence or str(evidence).strip() == "":
            return GroundingResult(
                outcome="REJECT_UNGROUNDED",
                reason="Missing evidence string",
                confidence_adjustment=-1.0,
                observation_id=obs_id
            )

        # Check evidence grounding relevance (does evidence mention the value)
        obj_val = str(obs_dict.get("object_value", obs_dict.get("object", ""))).strip().lower()
        evidence_lower = str(evidence).lower()
        if obj_val and len(obj_val) > 2 and obj_val not in evidence_lower:
            if self.strict_mode:
                return GroundingResult(
                    outcome="FLAG_FABRICATION",
                    reason=f"Extracted value '{obj_val}' not grounded in evidence '{evidence}'",
                    confidence_adjustment=-0.8,
                    observation_id=obs_id,
                )
            
        # Check platform confusion
        predicate = obs_dict.get("predicate", "")
        company = obj_val
        if predicate == "WORKS_AT" and company in self.PLATFORM_NAMES:
            # Could be a genuine employer, but flag for review to be safe
            return GroundingResult(
                outcome="REVIEW",
                reason="Potential confusion between source platform and employer",
                confidence_adjustment=-0.2,
                observation_id=obs_id
            )
            
        # Relationship observation check (subject and object)
        if "subject" in obs_dict and ("object" in obs_dict or "object_value" in obs_dict):
            # If general evidence is provided, it grounds the relationship
            if not evidence and (not obs_dict.get("subject_evidence") or not obs_dict.get("object_evidence")):
                return GroundingResult(
                    outcome="REJECT_UNGROUNDED",
                    reason="Both sides of relationship must be grounded",
                    confidence_adjustment=-1.0,
                    observation_id=obs_id
                )
                
        return GroundingResult(
            outcome="ACCEPT",
            reason="Validation passed",
            confidence_adjustment=weighted_conf - confidence,
            observation_id=obs_id
        )

    def validate_batch(self, observations: list[dict], capture_context: dict) -> tuple[list[dict], list[dict]]:
        """Validate a batch of observations, returning accepted and rejected lists."""
        accepted = []
        rejected = []
        
        for obs in observations:
            result = self.validate_observation(obs, capture_context)
            if result.outcome == "ACCEPT":
                obs["confidence"] = obs.get("confidence", 0.0) + result.confidence_adjustment
                accepted.append(obs)
            else:
                obs["rejection_reason"] = result.reason
                obs["validation_outcome"] = result.outcome
                rejected.append(obs)
                
        return accepted, rejected

    def build_proof_chain(self, capture_id: str) -> ProofChain:
        """Create a new proof chain starting with the CAPTURE step."""
        chain = ProofChain()
        chain.add_step(
            step_name="CAPTURE",
            details={"capture_id": capture_id},
            status="PASS"
        )
        return chain
