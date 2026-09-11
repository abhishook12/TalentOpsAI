"""
extractor/extraction_engine.py — High-Precision Semantic Extraction Pipeline

Replaces:
  SCREEN -> OCR -> CANDIDATE
With:
  WINDOW CONTEXT
  -> SOURCE IDENTIFICATION
  -> PAGE CLASSIFICATION
  -> SCREEN STABILITY
  -> LAYOUT DETECTION
  -> REGION EXTRACTION
  -> MULTI-FRAME OCR / STRUCTURED DATA
  -> FIELD CLASSIFICATION
  -> NORMALIZATION
  -> ENTITY RESOLUTION
  -> FIELD VALIDATION
  -> CONFIDENCE
  -> DEDUPLICATION
  -> STAGING / VERIFIED
"""

from __future__ import annotations
import logging
import time
from typing import Optional, List, Dict, Any, Tuple
from PIL import Image

from .page_classifier import PageClassifier, PAGE_TYPE_PERSON_PROFILE, PAGE_TYPE_PEOPLE_SEARCH
from .stability_detector import ScreenStabilityDetector
from .layout_detector import LayoutDetector, ProfileLayout
from .field_classifier import FieldClassifier
from .location_resolver import LocationResolver, ResolvedLocation
from .confidence_engine import ConfidenceEngine, ConfidenceReport, STATUS_VERIFIED, STATUS_DUPLICATE
from .evidence_manager import EvidenceManager, ExtractionAuditTrail, FieldEvidenceItem, ENGINE_VERSION
from .models import Observation, EntityCluster

logger = logging.getLogger("scout.extraction_engine")


class CanonicalCandidate:
    """Represents a fully resolved, validated, and confidence-scored talent profile."""

    def __init__(
        self,
        candidate_id: str,
        canonical_name: str,
        current_title: Optional[str] = None,
        current_company: Optional[str] = None,
        location: Optional[str] = None,
        canonical_profile_url: Optional[str] = None,
        platform: str = "LinkedIn",
        confidence_report: Optional[ConfidenceReport] = None,
        audit_trail: Optional[ExtractionAuditTrail] = None,
        raw_cluster: Optional[EntityCluster] = None,
    ):
        self.candidate_id = candidate_id
        self.canonical_name = canonical_name
        self.current_title = current_title or ""
        self.current_company = current_company or ""
        self.location = location or ""
        self.canonical_profile_url = canonical_profile_url or ""
        self.platform = platform
        self.confidence_report = confidence_report or ConfidenceReport()
        self.audit_trail = audit_trail
        self.raw_cluster = raw_cluster
        self.last_seen_at = time.time()

    @property
    def status(self) -> str:
        return self.confidence_report.candidate_status

    @property
    def overall_confidence(self) -> float:
        return self.confidence_report.overall_confidence

    def to_staged_dict(self) -> Dict[str, Any]:
        """Serializes candidate for SQLite queue and backend synchronization."""
        return {
            "recruiter_name": self.canonical_name,
            "raw_name": self.canonical_name,
            "title": self.current_title,
            "raw_title": self.current_title,
            "company_name": self.current_company,
            "raw_company": self.current_company,
            "location": self.location,
            "raw_location": self.location,
            "linkedin_url": self.canonical_profile_url,
            "raw_linkedin": self.canonical_profile_url,
            "confidence": int(self.overall_confidence * 100),
            "status": self.status,
            "extractor_version": ENGINE_VERSION,
            "field_confidence": self.confidence_report.to_dict(),
            "checklist": self.audit_trail.checklist if self.audit_trail else [],
        }


class ScoutExtractionEngine:
    """
    Master Semantic Extraction Engine.
    Enforces all 32 quality gates from the architectural specification.
    """

    def __init__(self):
        self.stability_detector = ScreenStabilityDetector(settling_window_sec=0.5)
        # In-memory deduplication registry keyed by canonical profile URL or Name+Company
        self._identity_registry: Dict[str, CanonicalCandidate] = {}

    def reset_stability(self):
        """Resets stability state when user switches active windows."""
        self.stability_detector.reset()

    def process_frame(
        self,
        img: Optional[Image.Image],
        delta: float,
        ocr_lines: List[str],
        window_title: str = "",
        source_url: str = "",
        platform: str = "",
        capture_id: str = "",
        force_process: bool = False,
    ) -> Tuple[List[CanonicalCandidate], Dict[str, Any]]:
        """
        Executes the full semantic extraction pipeline on the frame.

        Returns:
            (candidates: List[CanonicalCandidate], telemetry: Dict[str, Any])
        """
        telemetry = {
            "page_type": "UNKNOWN",
            "is_stable": False,
            "stability_state": "WAIT",
            "candidates_extracted": 0,
            "reason": "",
            "audit": None,
        }

        # Step 1: Page Classification Gate
        p_class = PageClassifier.classify(
            url=source_url,
            window_title=window_title,
            platform=platform,
            visible_lines=ocr_lines,
        )
        page_type = p_class["page_type"]
        telemetry["page_type"] = page_type

        # GATING: If page is NOT candidate eligible (e.g. FEED, HOME, JOB_PAGE, MESSAGING, UNKNOWN), ABORT immediately!
        if not p_class["is_candidate_eligible"]:
            telemetry["reason"] = f"Frame rejected by PageClassifier: {page_type} ({p_class['reason']})"
            logger.debug(telemetry["reason"])
            return [], telemetry

        # Step 2: Screen Stability Gate (if img provided)
        if img and not force_process:
            is_ready, state, f_hash = self.stability_detector.update_frame(img, delta, window_title)
            telemetry["stability_state"] = state
            telemetry["is_stable"] = is_ready
            if not is_ready:
                telemetry["reason"] = f"Frame deferred by ScreenStabilityDetector ({state})"
                logger.debug(telemetry["reason"])
                return [], telemetry
        else:
            telemetry["is_stable"] = True
            telemetry["stability_state"] = "STABLE_READY"

        # Step 3: Layout & Region Decomposition
        layout: ProfileLayout = LayoutDetector.detect_layout(ocr_lines)

        # Step 4: Field-Specific Classification & Validation
        name, name_conf, name_ev = FieldClassifier.extract_name_from_header(
            layout.header_lines, window_title=window_title
        )

        # GATING: If candidate name could not be found with confidence, ABORT!
        # Prevents "REASON: Overview", "Active Window", etc. from becoming candidates
        if not name or name_conf < 0.75:
            telemetry["reason"] = "No valid human candidate name found in PROFILE_HEADER"
            logger.info("Quality Gate: Rejected frame — %s", telemetry["reason"])
            return [], telemetry

        # Current Title & Company
        title, title_conf, company, company_conf = FieldClassifier.extract_title_and_company(
            layout.headline_candidates, layout.header_lines, layout.experience_lines
        )

        # Location with corruption detection
        raw_loc_str = layout.location_candidates[0] if layout.location_candidates else None
        loc_resolved: ResolvedLocation = LocationResolver.resolve(raw_loc_str)
        clean_location = loc_resolved.display_name if not loc_resolved.is_corrupted else None
        loc_conf = loc_resolved.confidence

        # Canonical Profile URL
        canonical_url, url_conf = FieldClassifier.extract_canonical_profile_url(source_url, platform=p_class["platform"])
        if not canonical_url and p_class.get("canonical_url"):
            canonical_url = p_class["canonical_url"]
            url_conf = p_class["confidence"]

        # Step 5: Entity Resolution & Deduplication
        # Build deduplication key: canonical profile URL if available, else name+company
        dedup_key = canonical_url if canonical_url else f"{name.lower()}::{company.lower() if company else ''}"
        is_duplicate = False

        if dedup_key in self._identity_registry:
            existing = self._identity_registry[dedup_key]
            existing.last_seen_at = time.time()
            # Enrich missing fields if existing candidate was incomplete
            if not existing.current_title and title:
                existing.current_title = title
            if not existing.current_company and company:
                existing.current_company = company
            if not existing.location and clean_location:
                existing.location = clean_location
            is_duplicate = True
            logger.info("Deduplication: Matched existing candidate '%s' (%s), updated last_seen", name, dedup_key)

        # Step 6: Confidence Scoring & Candidate State Machine
        conf_report: ConfidenceReport = ConfidenceEngine.evaluate(
            name=name,
            name_conf=name_conf,
            title=title,
            title_conf=title_conf,
            company=company,
            company_conf=company_conf,
            location=clean_location,
            loc_conf=loc_conf,
            profile_url=canonical_url,
            url_conf=url_conf,
            is_duplicate=is_duplicate,
        )

        # Step 7: Explainable Evidence & Audit Trail
        checklist = EvidenceManager.generate_checklist(
            page_type=page_type,
            name=name,
            name_conf=name_conf,
            title=title,
            title_conf=title_conf,
            company=company,
            company_conf=company_conf,
            location=clean_location,
            loc_conf=loc_conf,
            profile_url=canonical_url,
        )

        cand_id = f"CAND-{hash(dedup_key) & 0xFFFFFF:06X}"
        audit = ExtractionAuditTrail(
            candidate_id=cand_id,
            capture_id=capture_id,
            page_type=page_type,
            source_url=source_url,
            checklist=checklist,
            field_items=[
                FieldEvidenceItem("NAME", name, "PROFILE_HEADER", name_conf),
                FieldEvidenceItem("TITLE", title or "", "HEADLINE", title_conf),
                FieldEvidenceItem("COMPANY", company or "", "EXPERIENCE/HEADER", company_conf),
                FieldEvidenceItem("LOCATION", clean_location or "", "METADATA", loc_conf),
                FieldEvidenceItem("PROFILE_URL", canonical_url or "", "BROWSER_CONTEXT", url_conf),
            ],
        )

        # Build raw EntityCluster for backward compatibility with existing pipelines
        cluster = EntityCluster(canonical_name=name, entity_type="PERSON")
        cluster.cluster_id = cand_id
        cluster.current_title = title
        cluster.current_company = company
        cluster.location = clean_location
        cluster.linkedin_url = canonical_url
        cluster.confidence = conf_report.overall_confidence

        candidate = CanonicalCandidate(
            candidate_id=cand_id,
            canonical_name=name,
            current_title=title,
            current_company=company,
            location=clean_location,
            canonical_profile_url=canonical_url,
            platform=p_class["platform"],
            confidence_report=conf_report,
            audit_trail=audit,
            raw_cluster=cluster,
        )

        if not is_duplicate:
            self._identity_registry[dedup_key] = candidate

        telemetry["candidates_extracted"] = 1
        telemetry["audit"] = audit
        telemetry["reason"] = f"Successfully resolved {name} ({conf_report.candidate_status}, {int(conf_report.overall_confidence*100)}%)"

        return [candidate], telemetry
