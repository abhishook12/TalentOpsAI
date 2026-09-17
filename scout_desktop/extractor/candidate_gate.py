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
import urllib.parse
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
    is_valid_email,
    EMAIL_REGEX,
    PHONE_REGEX,
)

logger = logging.getLogger("scout.candidate_gate")

DISALLOWED_PAGE_TYPES = {
    "HOME", "NAVIGATION", "INBOX", "SETTINGS",
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
    field_evidence: Dict[str, Any] = field(default_factory=dict)
    sanitized_candidate: Optional[Dict[str, Any]] = None

    @property
    def reason_code(self) -> str:
        """Returns decisive reason code (e.g. PROFILE_URL_PRESENT, TITLE_COMPANY_ONLY)."""
        if self.reasons:
            first_r = self.reasons[0]
            if ":" in first_r:
                return first_r.split(":", 1)[0].strip()
            return first_r.strip()
        return self.status

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
            "field_evidence": self.field_evidence,
            "sanitized_candidate": self.sanitized_candidate,
        }


DISALLOWED_URL_SUBSTRINGS = {
    "/company/", "/school/", "/showcase/", "/jobs/", "/job/", "/feed/",
    "/news/", "/pulse/", "/search/", "/mynetwork/", "/messaging/",
    "/notifications/", "/learning/", "/groups/", "/events/"
}


def is_individual_profile_url(url: Optional[str]) -> bool:
    """Checks if a URL points to an individual person profile rather than a company, job, or search page."""
    if not url or not isinstance(url, str):
        return False
    u = url.strip().lower()
    if not u.startswith(("http://", "https://")):
        return False
    if any(dis in u for dis in DISALLOWED_URL_SUBSTRINGS):
        return False
    if "linkedin.com" in u:
        return bool(re.search(r"linkedin\.com/in/[\w\-\%]+", u))
    if "github.com" in u:
        return bool(re.match(r"^https?://(?:www\.)?github\.com/[a-zA-Z0-9_\-]+/?$", u))
    if "zoominfo.com" in u:
        return "/p/" in u or "zi-lite" in u
    if "apollo.io" in u:
        return "/people/" in u
    if "indeed.com" in u:
        return "/r/" in u or "/resume" in u
    return True


def is_url_slug_compatible_with_name(url: Optional[str], name: Optional[str]) -> bool:
    """
    Guards against cross-tab contamination where a candidate seen in chat or feed
    is erroneously attributed to a background browser tab's profile URL.
    Returns True if the LinkedIn slug is plausibly compatible with the person's name.
    """
    if not url or not name:
        return True
    m = re.search(r"linkedin\.com/in/([a-zA-Z0-9_\-%]+)", url.lower())
    if not m:
        return True
    slug = m.group(1).lower()
    name_tokens = [re.sub(r'[^a-z]', '', tok.lower()) for tok in name.split() if len(tok) >= 2]
    if not name_tokens:
        return True
    first = name_tokens[0]
    last = name_tokens[-1]
    # Check if either first name or last name is present in the slug
    if first in slug or last in slug:
        return True
    # Check first initial + last name e.g. "fpocesta" in slug
    if len(name_tokens) >= 2 and (name_tokens[0][0] + name_tokens[-1]) in slug:
        return True
    # Check first name + last initial e.g. "fatjonap" in slug
    if len(name_tokens) >= 2 and (name_tokens[0] + name_tokens[-1][0]) in slug:
        return True
    # If the slug is completely numeric, allow it
    if slug.isdigit():
        return True
    return False


def clean_candidate_url(raw_url: Optional[str], name: str = "", company: str = "") -> str:
    """
    Cleans OCR noise and typos from candidate profile URLs, ensures https:// scheme,
    or falls back to a clean LinkedIn search URL.
    """
    if not raw_url or not isinstance(raw_url, str):
        raw_url = ""
    url = raw_url.strip()

    # Strip common OCR noise prefixes like "2; ", "1. ", "🔗 ", "URL: ", etc.
    url = re.sub(r'^[0-9\s;:\-_/|🔗•\*\#\.]+', '', url)
    url = re.sub(r'\.{2,}$', '', url)  # strip trailing ellipses

    # Fix common OCR typos in linkedin domain
    url = re.sub(r'linke?a?d?i?n?\.com', 'linkedin.com', url, flags=re.IGNORECASE)
    url = re.sub(r'likedin\.com', 'linkedin.com', url, flags=re.IGNORECASE)
    url = re.sub(r'linkdin\.com', 'linkedin.com', url, flags=re.IGNORECASE)
    url = re.sub(r'linkid\.com', 'linkedin.com', url, flags=re.IGNORECASE)

    # Check if it contains linkedin.com
    if "linkedin.com" in url.lower():
        if not url.startswith(("http://", "https://")):
            url = "https://" + url.lstrip("/")
        if "?" in url and "search" not in url.lower():
            url = url.split("?")[0]
        url = url.rstrip("/")
    elif url.startswith(("http://", "https://")):
        if "?" in url and "search" not in url.lower():
            url = url.split("?")[0]
        url = url.rstrip("/")
    elif "." in url and " " not in url:
        url = "https://" + url.lstrip("/")
        if "?" in url and "search" not in url.lower():
            url = url.split("?")[0]
        url = url.rstrip("/")
    else:
        # Fallback to people search by name & company
        clean_name = re.sub(r'[^a-zA-Z\s]', '', name).strip() if name else ""
        clean_comp = re.sub(r'[^a-zA-Z0-9\s]', '', company).strip() if company else ""
        query_terms = [t for t in [clean_name, clean_comp] if t and t != "—" and t != "Professional Profile"]
        if query_terms:
            query = " ".join(query_terms)
            url = f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote_plus(query)}"
        elif url:
            url = f"https://www.google.com/search?q={urllib.parse.quote_plus(url)}"
        else:
            url = "https://www.linkedin.com"
    return url


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
        elif "simplyhired.com" in url_low:
            return "SimplyHired"
        elif "jobright.ai" in url_low:
            return "Jobright"
        elif "glassdoor.com" in url_low:
            return "Glassdoor"
        elif "ziprecruiter.com" in url_low:
            return "ZipRecruiter"
        elif "chat.google.com" in url_low or "teams.microsoft.com" in url_low or "slack.com" in url_low:
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
    elif "simplyhired" in p_low:
        return "SimplyHired"
    elif "jobright" in p_low:
        return "Jobright"
    elif "glassdoor" in p_low:
        return "Glassdoor"
    elif "ziprecruiter" in p_low:
        return "ZipRecruiter"
    elif "chat" in p_low or "teams" in p_low or "slack" in p_low:
        return "Recruiter Chat"
    return p_raw


def sanitize_location(raw_location: Optional[str]) -> Tuple[Optional[str], bool]:
    """
    Validates and cleans location string.
    CRITICAL RULE 21: Corrupted OCR (e.g. 'San ntu', 'D,id - sud') becomes None / needs_review.
    Returns (cleaned_location, is_corrupted).
    """
    if not raw_location or not isinstance(raw_location, str):
        return None, False
    loc = raw_location.strip()
    if not loc:
        return None, False

    # Immediate markers of OCR corruption
    is_corrupted = False
    if (
        "\ufffd" in loc
        or "?" in loc
        or "%" in loc
        or re.search(r"[a-zA-Z],[a-zA-Z]", loc)
        or re.search(r"\b[a-zA-Z],\s*", loc)
        or re.search(r"[-–—]\s*[a-zA-Z]{1,4}\b", loc)
        or any(c in loc for c in [";", ":", "!", "~", "*", "=", "<", ">"])
    ):
        is_corrupted = True

    cleaned = clean_location_text(loc)
    if not cleaned or not is_valid_location(cleaned):
        return None, (True if is_corrupted or bool(loc and len(loc) > 3) else False)
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

    # 1b. Window-Title LinkedIn Platform Inference
    # When source_url is empty (URL not captured from browser address bar), infer LinkedIn
    # platform from the window title. This is the most common failure case: browser URL
    # was not readable via UIA, but the window title clearly shows a LinkedIn profile.
    # e.g. "Elizabeth Bowers | LinkedIn - Google Chrome" → platform = LinkedIn
    wt_lower = window_title.lower()
    if not source_url and platform not in ("LinkedIn", "ZoomInfo", "Apollo", "Indeed", "SimplyHired", "Jobright", "Glassdoor", "ZipRecruiter", "Recruiter Chat"):
        import re as _re
        _li_title_m = _re.match(
            r"^(?:\(\d+\+?\)\s*)?([^|•·\n]+?)\s*[|•·]\s*LinkedIn",
            window_title,
            flags=_re.IGNORECASE,
        )
        if _li_title_m:
            platform = "LinkedIn"
            checklist.append("LinkedIn platform inferred from window title (URL not available)")
        elif "zoominfo" in wt_lower:
            platform = "ZoomInfo"
        elif "apollo" in wt_lower:
            platform = "Apollo"
        elif "simplyhired" in wt_lower:
            platform = "SimplyHired"
        elif "jobright" in wt_lower:
            platform = "Jobright"
        elif "indeed" in wt_lower:
            platform = "Indeed"
        elif "glassdoor" in wt_lower:
            platform = "Glassdoor"
        elif "ziprecruiter" in wt_lower:
            platform = "ZipRecruiter"
        elif any(s in wt_lower for s in ("- chat", "google chat", "teams", "slack")):
            platform = "Recruiter Chat"

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

    # Self-Name / Account Owner Exclusion. The owning Scout session supplies this
    # context; static names caused both false positives and missed other accounts.
    raw_owner_names = ctx.get("owner_names") or []
    if isinstance(raw_owner_names, str):
        raw_owner_names = [raw_owner_names]
    self_names = {
        normalized.lower()
        for owner_name in raw_owner_names
        if (normalized := clean_person_name(str(owner_name)))
    }
    owner_email = str(ctx.get("owner_email") or "").strip().lower()
    if owner_email and "@" in owner_email:
        email_name = clean_person_name(owner_email.split("@", 1)[0].replace(".", " ").replace("_", " "))
        if email_name:
            self_names.add(email_name.lower())
    if cleaned_name.lower() in self_names:
        return CandidateGateResult(
            decision="REJECTED_OBSERVATION",
            is_valid_candidate=False,
            status="REJECTED",
            platform=platform,
            reasons=[f"Candidate name matches logged-in user / scout owner: '{cleaned_name}'"],
            audit_checklist=["Self-name rejection: TRIGGERED"],
        )

    # Chat Conversation Partner Exclusion (Window Title Sender/Receiver)
    if window_title and ("- chat" in window_title.lower() or "chat" in window_title.lower()):
        chat_partner_match = re.match(r"^(?:(?:\(\d+\+?\)\s*)?)([A-Za-z\s]+?)\s*(?:[-–—|]|messaged)\s*Chat", window_title, re.IGNORECASE)
        if chat_partner_match:
            partner_raw = chat_partner_match.group(1).strip()
            partner_clean = clean_person_name(partner_raw)
            if partner_clean and (cleaned_name.lower() == partner_clean.lower() or cleaned_name.lower() in partner_clean.lower() or partner_clean.lower() in cleaned_name.lower()):
                return CandidateGateResult(
                    decision="REJECTED_OBSERVATION",
                    is_valid_candidate=False,
                    status="REJECTED",
                    platform=platform,
                    reasons=[f"Candidate name matches chat conversation partner '{partner_clean}' from window title"],
                    audit_checklist=["Chat partner rejection: TRIGGERED"],
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
            field_conf["company"] = 0.0
            reasons.append(f"Stripped invalid company noise: '{raw_comp}'")
            checklist.append("Company noise filtered")
    else:
        field_conf["company"] = 0.0

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
            field_conf["title"] = 0.0
            reasons.append(f"Discarded implausible title: '{raw_title}'")
    else:
        field_conf["title"] = 0.0

    # 6. Location Validation (Rule 11, 21)
    raw_loc = observation.get("location") or observation.get("raw_location")
    valid_loc, is_loc_corrupted = sanitize_location(raw_loc)
    if is_loc_corrupted:
        field_conf["location"] = 0.0
        reasons.append(f"Corrupted location string neutralized: '{raw_loc}'")
        checklist.append("Corrupted location removed: NEEDS_REVIEW")
    elif valid_loc:
        field_conf["location"] = 0.85
        checklist.append(f"Location normalized: {valid_loc}")
    else:
        field_conf["location"] = 0.0

    # 7. Profile URL & Contact Validation (Rule 6, 7)
    raw_profile_url = (
        observation.get("canonical_profile_url")
        or observation.get("profile_url")
        or observation.get("linkedin_url")
        or observation.get("raw_linkedin")
        or (source_url if "linkedin.com/in/" in source_url else None)
    )
    canonical_url = None
    if raw_profile_url and isinstance(raw_profile_url, str):
        cleaned_url = clean_candidate_url(raw_profile_url, cleaned_name or "", valid_company or "")
        if "linkedin.com/in/" in cleaned_url:
            if is_url_slug_compatible_with_name(cleaned_url, cleaned_name):
                canonical_url = cleaned_url
                field_conf["profile_url"] = 0.99
                checklist.append(f"Canonical LinkedIn URL verified: {canonical_url}")
            else:
                reasons.append(f"CROSS_TAB_MISMATCH: LinkedIn profile URL slug '{cleaned_url}' does not match candidate '{cleaned_name}'")
                checklist.append("CROSS_TAB_MISMATCH: Contaminated profile URL stripped")
        elif is_individual_profile_url(cleaned_url):
            canonical_url = cleaned_url
            field_conf["profile_url"] = 0.90
            checklist.append(f"Source individual profile URL verified: {canonical_url}")
        else:
            reasons.append(f"Filtered non-individual profile URL: '{raw_profile_url}'")
            checklist.append("Non-individual URL rejected")

    # Emails & Phones
    email = observation.get("email") or observation.get("primary_email") or observation.get("raw_email")
    valid_email = email.strip() if (email and is_valid_email(str(email))) else None
    if valid_email:
        field_conf["email"] = 0.95
        checklist.append(f"Contact email verified: {valid_email}")
        # Infer company from corporate email domain if company was not otherwise found
        if not valid_company:
            domain = valid_email.split("@")[-1].lower()
            free_domains = {
                "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
                "icloud.com", "aol.com", "proton.me", "protonmail.com",
                "live.com", "msn.com", "me.com", "mail.com", "zoho.com"
            }
            if domain not in free_domains and "." in domain:
                derived_comp = domain.split(".")[0].capitalize()
                if len(derived_comp) >= 4 and is_valid_company_name(derived_comp):
                    valid_company = derived_comp
                    field_conf["company"] = 0.85
                    checklist.append(f"Company inferred from corporate email domain: {valid_company}")

    phone = observation.get("phone") or observation.get("primary_phone") or observation.get("raw_phone")
    valid_phone = phone.strip() if (phone and PHONE_REGEX.search(str(phone))) else None
    if valid_phone:
        field_conf["phone"] = 0.90
        checklist.append(f"Contact phone verified: {valid_phone}")

    # 8. Minimum Identity Requirement & Stable Identifier Anchor (Rule 6, Pillars 2 & 3)
    # A candidate cannot become VERIFIED on name alone.
    # To be auto-ingested into VERIFIED, must have at least one STABLE IDENTIFIER:
    # (a) Canonical individual profile URL (linkedin.com/in/, etc.), OR
    # (b) Verified deliverable email, OR
    # (c) Verified phone number.
    # Title/company-only discoveries are kept in REVIEW_REQUIRED by default.
    has_strong_profile = bool(canonical_url and ("linkedin.com/in/" in canonical_url or is_individual_profile_url(canonical_url)))
    has_employment = bool(valid_title and valid_company)
    has_verified_contact = bool(valid_email or valid_phone)
    has_partial_employment = bool(valid_title or valid_company)
    has_stable_identifier = bool(has_strong_profile or has_verified_contact)
    has_primary_anchor = bool(has_stable_identifier or has_employment)

    # 9. Garbage & Confidence Scoring (Rule 12)
    # Platform context bonus: a LinkedIn/ZoomInfo/Apollo window title without a URL is still
    # strong evidence this is a real sourcing platform candidate, not UI noise.
    is_verified_sourcing_platform = platform in (
        "LinkedIn", "ZoomInfo", "Apollo", "Indeed", "GitHub",
        "SimplyHired", "Jobright", "Glassdoor", "ZipRecruiter"
    )
    has_platform_context = is_verified_sourcing_platform and not canonical_url

    is_recruiter_chat = (
        page_type in ("CHAT_RECRUITER_STREAM", "MESSAGING")
        or platform in ("Recruiter Chat", "GOOGLE_CHAT", "TEAMS", "SLACK")
    )

    quality_score = 0
    quality_score += 35  # Valid human name
    if has_strong_profile:
        quality_score += 35
    elif canonical_url:
        quality_score += 20
    elif has_platform_context:
        quality_score += 20
        checklist.append(f"Verified sourcing platform context: {platform} (URL not captured)")
    elif is_recruiter_chat and (has_employment or has_verified_contact):
        quality_score += 15
        checklist.append("Recruiter chat stream candidate recommendation context")

    if has_employment:
        quality_score += 25
    elif has_partial_employment:
        quality_score += 15

    if valid_loc:
        quality_score += 10
    if has_verified_contact:
        quality_score += 20

    quality_score = min(100, quality_score)

    identity_conf = (
        (0.35 if cleaned_name else 0.0)
        + (0.40 if has_strong_profile else (0.15 if canonical_url else (0.15 if has_platform_context else 0.0)))
        + (0.20 if has_employment else (0.10 if has_partial_employment else 0.0))
        + (0.10 if valid_loc else 0.0)
        + (0.20 if has_verified_contact else (0.10 if (is_recruiter_chat and has_employment) else 0.0))
    )
    identity_conf = min(1.0, round(identity_conf, 2))

    # 10. Final Gate Decision (Rule 2, 13, 14 & Pillars 2 & 3)
    # Required for auto-ingestion to VERIFIED:
    # 1. Must have a STABLE IDENTIFIER: canonical profile URL OR verified email/phone.
    # 2. Title/company-only discoveries are kept in REVIEW_REQUIRED by default.
    decisive_reasons = []
    if has_strong_profile:
        decisive_reasons.append("PROFILE_URL_PRESENT: Canonical individual profile URL verified")
    if has_verified_contact:
        decisive_reasons.append("VERIFIED_CONTACT_FOUND: Verified deliverable email or phone verified")
    if has_employment:
        decisive_reasons.append("EMPLOYMENT_CORROBORATED: Professional title and company verified")

    verified_standard = (
        has_stable_identifier
        and quality_score >= 70
        and identity_conf >= 0.75
    )
    verified_chat_context = (
        has_stable_identifier
        and quality_score >= 75
        and identity_conf >= 0.75
        and is_recruiter_chat
    )

    if verified_standard or verified_chat_context:
        decision = "CANDIDATE_VERIFIED"
        status = "VERIFIED"
        is_valid = True
        reasons.extend(decisive_reasons)
    elif has_employment and not has_stable_identifier:
        decision = "REVIEW_REQUIRED"
        status = "REVIEW_REQUIRED"
        is_valid = False
        reasons.append("TITLE_COMPANY_ONLY: Corroborated title & company found, but held in Review Queue awaiting stable profile URL or verified contact")
        reasons.append("MISSING_STABLE_ANCHOR: No canonical profile URL, verified email, or verified phone found")
    elif quality_score >= 40 and (has_partial_employment or canonical_url or has_platform_context):
        decision = "REVIEW_REQUIRED"
        status = "REVIEW_REQUIRED"
        is_valid = False
        reasons.append(f"REVIEW_REQUIRED: Partial signals (Score {quality_score}, Conf {identity_conf:.2f}) — held in Review Queue")
        if not has_stable_identifier:
            reasons.append("MISSING_STABLE_ANCHOR: Awaiting human verification of stable identifier")
    else:
        decision = "REJECTED_OBSERVATION"
        status = "REJECTED"
        is_valid = False
        reasons.append("REJECTED: Insufficient identity evidence (Name without corroborating profile or employment signals)")

    # Build field-level source evidence references
    field_evidence = {
        "name": {
            "value": cleaned_name,
            "evidence": observation.get("name_evidence") or f"Extracted candidate name from {platform}",
            "confidence": field_conf.get("name", 0.95),
        }
    }
    if valid_title:
        field_evidence["title"] = {
            "value": valid_title,
            "evidence": observation.get("title_evidence") or f"Title extracted from {platform}",
            "confidence": field_conf.get("title", 0.90),
        }
    if valid_company:
        field_evidence["company"] = {
            "value": valid_company,
            "evidence": observation.get("company_evidence") or f"Company extracted from {platform}",
            "confidence": field_conf.get("company", 0.90),
        }
    if valid_loc:
        field_evidence["location"] = {
            "value": valid_loc,
            "evidence": observation.get("location_evidence") or f"Location normalized from '{raw_loc}'",
            "confidence": field_conf.get("location", 0.85),
        }
    if canonical_url:
        field_evidence["profile_url"] = {
            "value": canonical_url,
            "evidence": observation.get("url_evidence") or f"Canonical individual profile URL: {canonical_url}",
            "confidence": field_conf.get("profile_url", 0.95),
        }
    if valid_email:
        field_evidence["email"] = {
            "value": valid_email,
            "evidence": f"Verified deliverable email address: {valid_email}",
            "confidence": field_conf.get("email", 0.95),
        }
    if valid_phone:
        field_evidence["phone"] = {
            "value": valid_phone,
            "evidence": f"Verified phone number: {valid_phone}",
            "confidence": field_conf.get("phone", 0.90),
        }

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
        "profile_url": canonical_url,
        "linkedin_url": canonical_url if (canonical_url and "linkedin.com/in/" in canonical_url) else None,
        "email": valid_email,
        "phone": valid_phone,
        "quality_score": quality_score,
        "identity_confidence": identity_conf,
        "status": status,
        "decision": decision,
        "evidence_checklist": checklist,
        "field_confidence": field_conf,
        "field_evidence": field_evidence,
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
        field_evidence=field_evidence,
        sanitized_candidate=sanitized,
    )
