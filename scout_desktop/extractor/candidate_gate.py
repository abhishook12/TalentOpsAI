"""
scout_desktop/extractor/candidate_gate.py — Centralized Candidate Creation Gate

Enforces the hard architectural rules:
1. RAW SCREEN TEXT IS NOT A CANDIDATE.
2. OBSERVATION != CANDIDATE.
3. Every candidate entering the pipeline MUST pass through create_candidate_if_valid().
4. "Active Window" must never be a platform value.
5. Three distinct layers:
   - RAW OBSERVATIONS (audit only)
   - CAPTURE REVIEW / HYPOTHESES (review required)
   - VERIFIED CANDIDATES (only records that pass this gate)
"""

from __future__ import annotations
import re
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple

from scout_desktop.extractor.patterns import (
    clean_person_name,
    is_valid_person_name,
    clean_company_name,
    is_valid_company_name,
    clean_location_text,
    is_valid_location,
    is_plausible_title,
    EMAIL_REGEX,
    PHONE_REGEX,
)

logger = logging.getLogger("scout.candidate_gate")

# Disallowed page types for person candidate creation
DISALLOWED_PAGE_TYPES = {
    "HOME", "NAVIGATION", "INBOX", "MESSAGING", "SETTINGS",
    "JOB_PAGE", "COMPANY_PAGE", "FEED", "LOADING", "UNKNOWN", "UNCLASSIFIED"
}

# Authoritative platform normalization map
PLATFORM_NORMALIZATION = {
    "active window": "DESKTOP_CAPTURE",
    "window": "DESKTOP_CAPTURE",
    "active": "DESKTOP_CAPTURE",
    "desktop": "DESKTOP_CAPTURE",
}


@dataclass
class CandidateGateResult:
    """Outcome of the Candidate Creation Gate."""
    decision: str  # CANDIDATE_VERIFIED | REVIEW_REQUIRED | REJECTED_OBSERVATION | UNRESOLVED_UI_TEXT
    is_valid_candidate: bool
    canonical_name: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    platform: str = "DESKTOP_CAPTURE"
    canonical_profile_url: Optional[str] = None
    quality_score: int = 0
    identity_confidence: float = 0.0
    status: str = "REJECTED"  # VERIFIED | REVIEW_REQUIRED | REJECTED
    reasons: List[str] = field(default_factory=list)
    audit_checklist: List[str] = field(default_factory=list)
    field_confidence: Dict[str, float] = field(default_factory=dict)
    sanitized_candidate: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "is_valid_candidate": self.is_valid_candidate,
            "canonical_name": self.canonical_name,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "platform": self.platform,
            "canonical_profile_url": self.canonical_profile_url,
            "quality_score": self.quality_score,
            "identity_confidence": self.identity_confidence,
            "status": self.status,
            "reasons": self.reasons,
            "audit_checklist": self.audit_checklist,
            "field_confidence": self.field_confidence,
            "sanitized_candidate": self.sanitized_candidate,
        }


def normalize_platform(platform: Optional[str], source_url: Optional[str] = None) -> str:
    """
    Normalizes platform string.
    CRITICAL RULE 19: 'Active Window' must NEVER be a platform value.
    """
    p_raw = (platform or "").strip()
    p_low = p_raw.lower()

    if p_low in PLATFORM_NORMALIZATION or not p_raw or p_low == "active window":
        # Attempt to infer platform from source URL
        url_low = (source_url or "").lower()
        if "linkedin.com" in url_low:
            return "LinkedIn"
        elif "zoominfo.com" in url_low or "zi-lite" in url_low:
            return "ZoomInfo"
        elif "apollo.io" in url_low:
            return "Apollo"
        elif "indeed.com" in url_low:
            return "Indeed"
        elif "github.com" in url_low:
            return "GitHub"
        elif "chat.google.com" in url_low or "teams.microsoft.com" in url_low:
            return "Recruiter Chat"
        return "DESKTOP_CAPTURE"

    if "linkedin" in p_low:
        return "LinkedIn"
    elif "zoominfo" in p_low:
        return "ZoomInfo"
    elif "apollo" in p_low:
        return "Apollo"
    elif "indeed" in p_low:
        return "Indeed"
    elif "github" in p_low:
        return "GitHub"
    return p_raw


def sanitize_location(raw_location: Optional[str]) -> Tuple[Optional[str], bool]:
    """
    Validates and cleans location string.
    CRITICAL RULE 21: Corrupted OCR (e.g. 'San ntu') becomes None / needs_review.
    Returns (cleaned_location, is_corrupted).
    """
    if not raw_location or not isinstance(raw_location, str):
        return None, False
    loc = raw_location.strip()
    if "\ufffd" in loc or "?" in loc or "%" in loc:
        return None, True
    cleaned = clean_location_text(loc)
    if not cleaned or not is_valid_location(cleaned):
        return None, False
    return cleaned, False


def create_candidate_if_valid(
    observation: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> CandidateGateResult:
    """
    THE CENTRALIZED CANDIDATE CREATION GATE.
    Every candidate entering the system (Desktop Scout and Backend) MUST pass through here.

    Accepts an observation dict (from OCR, cluster, or staging) and validates against
    strict 10-point candidate identity criteria.
    """
    reasons = []
    checklist = []
    field_conf = {}

    ctx = context or {}
    source_url = observation.get("source_url") or ctx.get("source_url") or ""
    window_title = observation.get("window_title") or ctx.get("window_title") or ""
    page_type = observation.get("page_type") or ctx.get("page_type") or ""
    raw_platform = observation.get("platform") or ctx.get("platform") or ""

    # 1. Platform Normalization (Rule 19)
    platform = normalize_platform(raw_platform, source_url)

    # 2. Context & Page Type Gating (Rule 4)
    if page_type and page_type.upper() in DISALLOWED_PAGE_TYPES:
        return CandidateGateResult(
            decision="REJECTED_OBSERVATION",
            is_valid_candidate=False,
            status="REJECTED",
            platform=platform,
            reasons=[f"Disallowed page context for candidate extraction: {page_type}"],
            audit_checklist=["Page type candidate eligible: FAIL"],
        )

    # 3. Person Name Extraction & Validation (Rule 1, 3, 5, 11)
    raw_name = (
        observation.get("recruiter_name")
        or observation.get("canonical_name")
        or observation.get("raw_name")
        or observation.get("name")
        or ""
    ).strip()

    cleaned_name = clean_person_name(raw_name)
    if not cleaned_name or not is_valid_person_name(cleaned_name):
        return CandidateGateResult(
            decision="UNRESOLVED_UI_TEXT",
            is_valid_candidate=False,
            status="REJECTED",
            platform=platform,
            reasons=[f"Invalid or UI noise person name: '{raw_name}'"],
            audit_checklist=["Human person name validation: FAIL"],
        )

    checklist.append(f"Valid candidate name verified: {cleaned_name}")
    field_conf["name"] = 0.95

    # 4. Organization / Company Validation (Rule 11, 20)
    raw_comp = observation.get("company_name") or observation.get("raw_company") or observation.get("company")
    valid_company = None
    if raw_comp and isinstance(raw_comp, str):
        c_clean = clean_company_name(raw_comp)
        if c_clean and is_valid_company_name(c_clean):
            valid_company = c_clean
            field_conf["company"] = 0.90
            checklist.append(f"Plausible company verified: {valid_company}")
        else:
            reasons.append(f"Stripped invalid company noise: '{raw_comp}'")
            checklist.append("Company noise filtered")

    # 5. Professional Title Validation (Rule 10, 11)
    raw_title = observation.get("title") or observation.get("raw_title") or observation.get("current_title")
    valid_title = None
    if raw_title and isinstance(raw_title, str):
        t_clean = raw_title.strip()
        if is_plausible_title(t_clean):
            valid_title = t_clean
            field_conf["title"] = 0.90
            checklist.append(f"Professional title verified: {valid_title}")
        else:
            reasons.append(f"Discarded implausible title: '{raw_title}'")

    # 6. Location Validation (Rule 11, 21)
    raw_loc = observation.get("location") or observation.get("raw_location")
    valid_loc, is_loc_corrupted = sanitize_location(raw_loc)
    if is_loc_corrupted:
        reasons.append(f"Corrupted location string neutralized: '{raw_loc}'")
        checklist.append("Corrupted location removed: NEEDS_REVIEW")
    elif valid_loc:
        field_conf["location"] = 0.85
        checklist.append(f"Location normalized: {valid_loc}")

    # 7. Profile URL & Contact Validation (Rule 6, 7)
    profile_url = (
        observation.get("canonical_profile_url")
        or observation.get("profile_url")
        or observation.get("linkedin_url")
        or observation.get("raw_linkedin")
        or (source_url if "linkedin.com/in/" in source_url else None)
    )
    canonical_url = None
    if profile_url and isinstance(profile_url, str):
        p_clean = profile_url.strip()
        if "linkedin.com/in/" in p_clean:
            canonical_url = p_clean.split("?")[0].rstrip("/")
            field_conf["profile_url"] = 0.99
            checklist.append(f"Canonical LinkedIn URL verified: {canonical_url}")
        elif p_clean.startswith("http"):
            canonical_url = p_clean.split("?")[0]
            field_conf["profile_url"] = 0.90
            checklist.append(f"Source URL verified: {canonical_url}")

    # Emails & Phones
    email = observation.get("email") or observation.get("primary_email") or observation.get("raw_email")
    valid_email = email.strip() if (email and EMAIL_REGEX.search(str(email))) else None
    if valid_email:
        field_conf["email"] = 0.95
        checklist.append(f"Contact email verified: {valid_email}")

    phone = observation.get("phone") or observation.get("primary_phone") or observation.get("raw_phone")
    valid_phone = phone.strip() if (phone and PHONE_REGEX.search(str(phone))) else None
    if valid_phone:
        field_conf["phone"] = 0.90
        checklist.append(f"Contact phone verified: {valid_phone}")

    # 8. Minimum Identity Requirement (Rule 6)
    # A candidate cannot become VERIFIED on name alone.
    # Must have:
    # (a) Canonical profile URL, OR
    # (b) (Plausible title AND Valid company), OR
    # (c) Verified email / phone
    has_strong_profile = bool(canonical_url and "linkedin.com/in/" in canonical_url)
    has_employment = bool(valid_title and valid_company)
    has_verified_contact = bool(valid_email or valid_phone)
    has_partial_employment = bool(valid_title or valid_company)

    # 9. Garbage & Confidence Scoring (Rule 12)
    quality_score = 0
    quality_score += 35  # Valid human name
    if has_strong_profile:
        quality_score += 35
    elif canonical_url:
        quality_score += 20

    if has_employment:
        quality_score += 25
    elif has_partial_employment:
        quality_score += 15

    if valid_loc:
        quality_score += 10
    if has_verified_contact:
        quality_score += 15

    quality_score = min(100, quality_score)

    identity_conf = (
        (0.35 if cleaned_name else 0.0)
        + (0.35 if has_strong_profile else (0.15 if canonical_url else 0.0))
        + (0.20 if has_employment else (0.10 if has_partial_employment else 0.0))
        + (0.10 if valid_loc else 0.0)
    )
    identity_conf = min(1.0, round(identity_conf, 2))

    # 10. Final Gate Decision (Rule 2, 13, 14)
    # Strict Thresholds:
    # VERIFIED: score >= 70 AND confidence >= 0.75 AND (has_strong_profile OR has_employment OR has_verified_contact)
    # REVIEW_REQUIRED: score >= 40 AND (has_partial_employment OR canonical_url)
    # REJECTED: anything below (name alone with 0 corroborating signals)
    if quality_score >= 70 and identity_conf >= 0.75 and (has_strong_profile or has_employment or has_verified_contact):
        decision = "CANDIDATE_VERIFIED"
        status = "VERIFIED"
        is_valid = True
    elif quality_score >= 40 and (has_partial_employment or canonical_url):
        decision = "REVIEW_REQUIRED"
        status = "REVIEW_REQUIRED"
        is_valid = False
        reasons.append(f"Hypothesis has partial signals (Score {quality_score}, Conf {identity_conf:.2f}) — routed to Capture Review")
    else:
        decision = "REJECTED_OBSERVATION"
        status = "REJECTED"
        is_valid = False
        reasons.append("Insufficient identity evidence (Name without corroborating profile or employment signals)")

    sanitized = {
        "recruiter_name": cleaned_name,
        "canonical_name": cleaned_name,
        "raw_name": raw_name,
        "title": valid_title,
        "current_title": valid_title,
        "company_name": valid_company,
        "current_company": valid_company,
        "location": valid_loc,
        "platform": platform,
        "source_url": source_url,
        "canonical_profile_url": canonical_url,
        "linkedin_url": canonical_url if (canonical_url and "linkedin.com" in canonical_url) else None,
        "email": valid_email,
        "phone": valid_phone,
        "quality_score": quality_score,
        "identity_confidence": identity_conf,
        "status": status,
        "decision": decision,
        "evidence_checklist": checklist,
        "field_confidence": field_conf,
        "reasons": reasons,
    }

    return CandidateGateResult(
        decision=decision,
        is_valid_candidate=is_valid,
        canonical_name=cleaned_name,
        title=valid_title,
        company=valid_company,
        location=valid_loc,
        platform=platform,
        canonical_profile_url=canonical_url,
        quality_score=quality_score,
        identity_confidence=identity_conf,
        status=status,
        reasons=reasons,
        audit_checklist=checklist,
        field_confidence=field_conf,
        sanitized_candidate=sanitized,
    )
