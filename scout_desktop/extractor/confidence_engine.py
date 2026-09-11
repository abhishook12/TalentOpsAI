"""
extractor/confidence_engine.py — Granular Field Confidence & Candidate State Machine

Implements:
1. Per-field confidence scoring (Name, Title, Company, Location, Profile URL)
2. Weighted composite identity confidence
3. Candidate State Transitions:
   DETECTED -> STAGING -> PARSING -> VALIDATING -> MATCHING -> VERIFIED -> SYNC_READY -> SYNCED
   With branches for REVIEW_REQUIRED, DUPLICATE, and REJECTED.
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


STATUS_DETECTED = "DETECTED"
STATUS_STAGING = "STAGING"
STATUS_PARSING = "PARSING"
STATUS_VALIDATING = "VALIDATING"
STATUS_MATCHING = "MATCHING"
STATUS_VERIFIED = "VERIFIED"
STATUS_SYNC_READY = "SYNC_READY"
STATUS_SYNCED = "SYNCED"
STATUS_REVIEW_REQUIRED = "REVIEW_REQUIRED"
STATUS_DUPLICATE = "DUPLICATE"
STATUS_REJECTED = "REJECTED"


@dataclass
class ConfidenceReport:
    name_confidence: float = 0.0
    title_confidence: float = 0.0
    company_confidence: float = 0.0
    location_confidence: float = 0.0
    profile_url_confidence: float = 0.0
    overall_confidence: float = 0.0
    candidate_status: str = STATUS_STAGING
    quality_gates_passed: bool = False
    status_explanation: str = ""
    field_breakdown: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": round(self.name_confidence, 2),
            "title": round(self.title_confidence, 2),
            "company": round(self.company_confidence, 2),
            "location": round(self.location_confidence, 2),
            "profile_url": round(self.profile_url_confidence, 2),
            "overall": round(self.overall_confidence, 2),
            "status": self.candidate_status,
            "explanation": self.status_explanation,
        }


class ConfidenceEngine:
    """
    Evaluates extracted candidate attributes and assigns a deterministic confidence
    and pipeline state.
    """

    # Quality Gate Weights
    WEIGHT_NAME = 0.35
    WEIGHT_TITLE = 0.20
    WEIGHT_COMPANY = 0.20
    WEIGHT_LOCATION = 0.10
    WEIGHT_PROFILE_URL = 0.15

    # Thresholds
    THRESHOLD_VERIFIED = 0.88
    THRESHOLD_REVIEW = 0.70

    @classmethod
    def evaluate(
        cls,
        name: Optional[str],
        name_conf: float,
        title: Optional[str],
        title_conf: float,
        company: Optional[str],
        company_conf: float,
        location: Optional[str],
        loc_conf: float,
        profile_url: Optional[str],
        url_conf: float,
        is_duplicate: bool = False,
        is_synced: bool = False,
    ) -> ConfidenceReport:
        """
        Computes composite confidence and maps to verified candidate states.
        """
        # Calculate weighted overall score
        score = (
            (name_conf * cls.WEIGHT_NAME) +
            (title_conf * cls.WEIGHT_TITLE) +
            (company_conf * cls.WEIGHT_COMPANY) +
            (loc_conf * cls.WEIGHT_LOCATION) +
            (url_conf * cls.WEIGHT_PROFILE_URL)
        )
        score = round(float(score), 4)

        breakdown = {
            "name": name_conf,
            "title": title_conf,
            "company": company_conf,
            "location": loc_conf,
            "profile_url": url_conf,
        }

        # Check duplicate first
        if is_duplicate:
            return ConfidenceReport(
                name_confidence=name_conf,
                title_confidence=title_conf,
                company_confidence=company_conf,
                location_confidence=loc_conf,
                profile_url_confidence=url_conf,
                overall_confidence=score,
                candidate_status=STATUS_DUPLICATE,
                quality_gates_passed=False,
                status_explanation="Existing profile found in database (last seen updated)",
                field_breakdown=breakdown,
            )

        # If already synced to cloud
        if is_synced:
            return ConfidenceReport(
                name_confidence=name_conf,
                title_confidence=title_conf,
                company_confidence=company_conf,
                location_confidence=loc_conf,
                profile_url_confidence=url_conf,
                overall_confidence=score,
                candidate_status=STATUS_SYNCED,
                quality_gates_passed=True,
                status_explanation="Successfully synchronized to cloud database",
                field_breakdown=breakdown,
            )

        # Gate 1: Candidate Name is strictly required
        if not name or name_conf < 0.75:
            return ConfidenceReport(
                name_confidence=name_conf,
                title_confidence=title_conf,
                company_confidence=company_conf,
                location_confidence=loc_conf,
                profile_url_confidence=url_conf,
                overall_confidence=score,
                candidate_status=STATUS_REJECTED,
                quality_gates_passed=False,
                status_explanation="Candidate name missing or below confidence threshold",
                field_breakdown=breakdown,
            )

        # Gate 2: Location Corruption Alert
        if location and loc_conf < 0.40:
            return ConfidenceReport(
                name_confidence=name_conf,
                title_confidence=title_conf,
                company_confidence=company_conf,
                location_confidence=loc_conf,
                profile_url_confidence=score,
                overall_confidence=score,
                candidate_status=STATUS_REVIEW_REQUIRED,
                quality_gates_passed=False,
                status_explanation="Location OCR corrupted or uncertain — requires verification",
                field_breakdown=breakdown,
            )

        # Gate 3: VERIFIED Condition
        # High confidence name + at least title or company + profile URL
        has_core_fields = bool(title and company)
        if score >= cls.THRESHOLD_VERIFIED and name_conf >= 0.90 and has_core_fields and profile_url:
            return ConfidenceReport(
                name_confidence=name_conf,
                title_confidence=title_conf,
                company_confidence=company_conf,
                location_confidence=loc_conf,
                profile_url_confidence=url_conf,
                overall_confidence=score,
                candidate_status=STATUS_VERIFIED,
                quality_gates_passed=True,
                status_explanation="All core profile signals corroborated and verified",
                field_breakdown=breakdown,
            )

        # Gate 4: REVIEW_REQUIRED Condition
        if score >= cls.THRESHOLD_REVIEW:
            return ConfidenceReport(
                name_confidence=name_conf,
                title_confidence=title_conf,
                company_confidence=company_conf,
                location_confidence=loc_conf,
                profile_url_confidence=url_conf,
                overall_confidence=score,
                candidate_status=STATUS_REVIEW_REQUIRED,
                quality_gates_passed=False,
                status_explanation="Moderate confidence — missing one core attribute",
                field_breakdown=breakdown,
            )

        # Default: STAGING (Accumulating scroll observations)
        return ConfidenceReport(
            name_confidence=name_conf,
            title_confidence=title_conf,
            company_confidence=company_conf,
            location_confidence=loc_conf,
            profile_url_confidence=url_conf,
            overall_confidence=score,
            candidate_status=STATUS_STAGING,
            quality_gates_passed=False,
            status_explanation="Identity incomplete — awaiting scroll enrichment",
            field_breakdown=breakdown,
        )
