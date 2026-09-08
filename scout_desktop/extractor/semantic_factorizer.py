"""
extractor/semantic_factorizer.py — Intelligent AI Factorization & Semantic Judgment Engine

Provides deep context judgment and structured semantic factorization:
1. ProfileJudge: Determines whether an image/text view is a genuine candidate profile,
   job posting, search grid, or ungrounded system noise (email, chat, browser UI).
2. SemanticFactorizer: Decomposes raw visual/textual evidence into exact, factorized
   attributes (canonical name, current vs. previous employment timeline, education breakdown,
   skills, geographic location, and verified contact channels).
"""

from __future__ import annotations
import re
import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set

from scout_desktop.extractor.patterns import (
    clean_person_name,
    is_valid_person_name,
    clean_company_name,
    is_valid_company_name,
    clean_location_text,
    is_valid_location,
    is_plausible_title,
    is_plausible_school,
    is_plausible_degree,
    is_valid_skill,
    clean_title_and_company,
    DATE_RANGE_PATTERN,
    is_noise_text,
    UI_ACTIONS,
    PRONOUNS,
    GEO_INDICATORS,
    EMAIL_REGEX,
    PHONE_REGEX,
)
from scout_desktop.extractor.title_normalizer import classify_title

logger = logging.getLogger("scout.semantic_factorizer")


# ==============================================================================
# SYSTEM NOISE BLACKLIST (Standalone Non-Talent Apps, Footers, Generic Noise)
# ==============================================================================
SYSTEM_NOISE_TERMS = {
    # Non-browser application windows
    "powershell", "command prompt", "visual studio code", "vscode", "sublime",
    "task manager", "file explorer", "recycle bin",
    # External email client windows
    "thunderbird",
    # Generic Job Board search result footers
    "cookie notice", "privacy policy", "terms of use", "all rights reserved",
    "404 not found", "page not found",
}


@dataclass
class JudgmentResult:
    """Outcome of visual/textual profile triage."""
    category: str  # CANDIDATE_PROFILE | MULTI_CANDIDATE_GRID | JOB_POSTING | SYSTEM_NOISE
    is_candidate_profile: bool
    confidence: float
    rejection_reason: Optional[str] = None
    signals_detected: List[str] = field(default_factory=list)


@dataclass
class FactorizedCandidate:
    """Fully decomposed and structured professional candidate record."""
    canonical_name: str
    pronouns: Optional[str] = None
    current_title: Optional[str] = None
    current_company: Optional[str] = None
    previous_title: Optional[str] = None
    previous_company: Optional[str] = None
    experience_history: List[Dict[str, str]] = field(default_factory=list)
    location: Optional[str] = None
    education: Optional[str] = None
    education_history: List[Dict[str, str]] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    about_summary: Optional[str] = None
    primary_email: Optional[str] = None
    primary_phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    quality_score: int = 0
    identity_confidence: float = 0.0
    field_provenance: Dict[str, str] = field(default_factory=dict)
    factorization_notes: List[str] = field(default_factory=list)
    title_intel: Optional[Dict[str, Any]] = None

    def to_staged_dict(self) -> Dict[str, Any]:
        """Serializes candidate to the format required by /recruiters/extension/batch."""
        meta = {
            "pronouns": self.pronouns,
            "previous_title": self.previous_title,
            "previous_company": self.previous_company,
            "education_history": self.education_history,
            "factorization_notes": self.factorization_notes,
        }
        if self.title_intel:
            meta["title_intel"] = self.title_intel
            meta["seniority_level"] = self.title_intel.get("legacy_seniority")
            meta["granular_seniority"] = self.title_intel.get("seniority_level")
            meta["seniority_score"] = self.title_intel.get("seniority_score")
            meta["domain_specialization"] = self.title_intel.get("domain_specialization")
            meta["specialization_label"] = self.title_intel.get("specialization_label")

        return {
            "recruiter_name": self.canonical_name,
            "raw_name": self.canonical_name,
            "title": self.current_title or "Professional",
            "raw_title": (self.title_intel.get("raw_title") if self.title_intel else None) or self.current_title or "",
            "company_name": self.current_company or "",
            "raw_company": self.current_company or "",
            "previous_company": self.previous_company or "",
            "email": self.primary_email or "",
            "raw_email": self.primary_email or "",
            "phone": self.primary_phone or "",
            "raw_phone": self.primary_phone or "",
            "location": self.location or "",
            "raw_location": self.location or "",
            "education": self.education or "",
            "skills": self.skills,
            "about_summary": self.about_summary or "",
            "experience_history": self.experience_history,
            "linkedin_url": self.linkedin_url or "",
            "raw_linkedin": self.linkedin_url or "",
            "confidence": int(self.identity_confidence * 100),
            "quality_score": self.quality_score,
            "observations_count": max(1, len(self.skills) + len(self.experience_history) + 2),
            "metadata_json": meta
        }


# ==============================================================================
# PROFILE JUDGE (Context Classifier & Noise Rejection Gate)
# ==============================================================================
class ProfileJudge:
    """
    Intelligent context evaluator that classifies captured screen contents.
    Rejects system noise, chat screens, email inboxes, and job listings before candidate extraction.
    """

    @classmethod
    def judge_frame(
        cls,
        lines: List[str],
        window_title: str = "",
        source_url: str = "",
    ) -> JudgmentResult:
        """
        Evaluates lines and metadata to judge the content category.
        """
        clean_lines = [l.strip() for l in lines if l and l.strip()]
        if not clean_lines:
            return JudgmentResult(
                category="SYSTEM_NOISE",
                is_candidate_profile=False,
                confidence=1.0,
                rejection_reason="Empty text capture",
            )

        wt_lower = window_title.lower()
        if any(term in wt_lower for term in ["feed |", "messaging |", "notifications |", "linkedin learning"]):
            return JudgmentResult(
                category="SYSTEM_NOISE",
                is_candidate_profile=False,
                confidence=1.0,
                rejection_reason="Excluded non-talent LinkedIn page (Feed/Messaging/Notifications)",
            )

        is_verified_linkedin = (
            any(k in wt_lower for k in ["| linkedin", "- linkedin", "linkedin recruiter", "sales navigator", "company: people"])
            or "linkedin.com/in/" in source_url.lower()
        )

        combined_context = (window_title + " " + " ".join(clean_lines[:12])).lower()

        # 1. NOISE KEYWORD ANALYSIS: Only applies if NOT on a verified LinkedIn profile window
        if not is_verified_linkedin:
            noise_hits = []
            for noise in SYSTEM_NOISE_TERMS:
                if re.search(rf"\b{re.escape(noise)}\b", combined_context):
                    noise_hits.append(noise)

            if noise_hits:
                has_profile_section = any(
                    re.match(r"^(?:Experience|Work\s*experience|Education|Skills|About|Activity|Featured)\b", l, re.IGNORECASE)
                    for l in clean_lines
                )
                has_connections = any(re.search(r"\b(?:followers?|connections?|mutual connections?)\b", l, re.IGNORECASE) for l in clean_lines[:10])
                has_linkedin_url = any("linkedin.com/in/" in l.lower() for l in clean_lines)

                if not (has_profile_section or has_connections or has_linkedin_url):
                    return JudgmentResult(
                        category="SYSTEM_NOISE",
                        is_candidate_profile=False,
                        confidence=0.95,
                        rejection_reason=f"Matched noise keywords {noise_hits[:3]} without any profile sections",
                    )

        # 2. JOB POSTING CLASSIFICATION
        job_signals = 0
        for l in clean_lines[:20]:
            if re.search(r"\b(?:about the job|job description|qualifications|responsibilities|requirements|what you'll do|role overview)\b", l, re.IGNORECASE):
                job_signals += 2
            if re.search(r"\b(?:easy apply|apply on company website|apply now|posted \d+ (?:days|hours) ago)\b", l, re.IGNORECASE):
                job_signals += 1

        if job_signals >= 3:
            return JudgmentResult(
                category="JOB_POSTING",
                is_candidate_profile=False,
                confidence=0.90,
                rejection_reason="Detected job description/posting layout",
                signals_detected=["job_description_headers", "apply_buttons"],
            )

        # 3. MULTI-CANDIDATE GRID / SEARCH LISTING
        card_indicators = 0
        for l in clean_lines:
            if re.search(r"\b(?:view full profile|connect|message|mutual connections?)\b", l, re.IGNORECASE):
                card_indicators += 1
        if card_indicators >= 4 and len(clean_lines) > 25:
            return JudgmentResult(
                category="MULTI_CANDIDATE_GRID",
                is_candidate_profile=True,
                confidence=0.85,
                signals_detected=[f"{card_indicators}_profile_action_cards"],
            )

        # 4. CANDIDATE PROFILE CHECK (Header + Sections + Career Signals)
        profile_signals = []
        for l in clean_lines:
            if re.match(r"^(?:Experience|Work\s*experience)\b", l, re.IGNORECASE):
                if "experience_section" not in profile_signals:
                    profile_signals.append("experience_section")
            elif re.match(r"^(?:Education)\b", l, re.IGNORECASE):
                if "education_section" not in profile_signals:
                    profile_signals.append("education_section")
            elif re.match(r"^(?:Skills)\b", l, re.IGNORECASE):
                if "skills_section" not in profile_signals:
                    profile_signals.append("skills_section")
            elif re.match(r"^(?:About)\b", l, re.IGNORECASE):
                if "about_section" not in profile_signals:
                    profile_signals.append("about_section")
            elif re.search(r"\b(?:followers?|connections?|mutual connections?)\b", l, re.IGNORECASE):
                if "network_metrics" not in profile_signals:
                    profile_signals.append("network_metrics")
            elif re.search(r"\b\d+\+?\s+endorsements?\b", l, re.IGNORECASE):
                if "endorsements_signal" not in profile_signals:
                    profile_signals.append("endorsements_signal")
            elif DATE_RANGE_PATTERN.search(l) or re.search(r"\b(?:present|\d{4}\s*[-–—]\s*(?:\d{4}|present))\b", l, re.IGNORECASE):
                if "employment_dates" not in profile_signals:
                    profile_signals.append("employment_dates")
            elif is_valid_location(l):
                if "location_signal" not in profile_signals:
                    profile_signals.append("location_signal")
            elif is_plausible_title(l) and not is_noise_text(l):
                if "job_title_signal" not in profile_signals:
                    profile_signals.append("job_title_signal")

        if "skills_section" in profile_signals:
            skills_count = sum(1 for l in clean_lines if is_valid_skill(l) and l.lower() != "skills")
            if skills_count >= 2 and "skills_detected" not in profile_signals:
                profile_signals.append("skills_detected")

        # Check URL or window title
        if is_verified_linkedin:
            profile_signals.append("linkedin_profile_context")

        # Candidate profile accepted if verified LinkedIn context OR at least 2 profile signals
        if is_verified_linkedin or len(profile_signals) >= 2 or "linkedin.com/in/" in source_url.lower():
            return JudgmentResult(
                category="CANDIDATE_PROFILE",
                is_candidate_profile=True,
                confidence=min(1.0, 0.6 + (len(profile_signals) * 0.1)),
                signals_detected=profile_signals,
            )

        # If only 1 signal and short text -> ungrounded noise
        return JudgmentResult(
            category="SYSTEM_NOISE",
            is_candidate_profile=False,
            confidence=0.80,
            rejection_reason="Insufficient profile structural signals (failed to find Experience, Education, or Network headers)",
            signals_detected=profile_signals,
        )


# ==============================================================================
# SEMANTIC FACTORIZER (Structured Attribute Decomposition)
# ==============================================================================
class SemanticFactorizer:
    """
    Decomposes unstructured screen lines into cleanly factorized candidate attributes.
    """

    def __init__(self):
        pass

    def factorize(
        self,
        lines: List[str],
        window_title: str = "",
        source_url: str = "",
        capture_id: str = "cap_live",
    ) -> Optional[FactorizedCandidate]:
        """
        Executes end-to-end factorization on the input lines.
        Returns a validated FactorizedCandidate or None if data is ungrounded.
        """
        clean_lines = [l.strip() for l in lines if l and l.strip()]
        if not clean_lines:
            return None

        # 1. Run Judge first
        judgment = ProfileJudge.judge_frame(clean_lines, window_title, source_url)
        if not judgment.is_candidate_profile:
            logger.info("SemanticFactorizer: Frame rejected as %s (%s)", judgment.category, judgment.rejection_reason)
            return None

        # 2. Segment Semantic Zones
        zones = self._segment_zones(clean_lines)

        # 3. Factorize Identity
        candidate_name, pronouns = self._factorize_name(zones["header"], clean_lines, window_title)
        if not candidate_name or not is_valid_person_name(candidate_name):
            logger.debug("SemanticFactorizer: No valid person name factorized")
            return None

        # 4. Factorize Contact Channels & Social Presence
        email, phone, linkedin = self._factorize_contact(clean_lines, source_url)

        # 5. Factorize Employment Timeline (Current vs. Past)
        cur_title, cur_comp, prev_title, prev_comp, exp_history = self._factorize_experience(
            header_lines=zones["header"],
            exp_lines=zones["experience"],
            window_title=window_title,
        )

        # Semantic Title Canonicalization & Seniority Classification
        title_intel = None
        if cur_title:
            title_intel = classify_title(cur_title)
            cur_title = title_intel["canonical_title"]
        if prev_title:
            prev_intel = classify_title(prev_title)
            prev_title = prev_intel["canonical_title"]

        # 6. Factorize Location
        location = self._factorize_location(zones["header"], clean_lines)

        # 7. Factorize Education
        primary_edu, edu_history = self._factorize_education(zones["education"], clean_lines)

        # 8. Factorize Skills
        skills = self._factorize_skills(zones["skills"], clean_lines)

        # 9. Factorize About / Bio Summary
        about = self._factorize_about(zones["about"])

        # 10. Compute Quality and Grounding Scores
        quality_score, identity_confidence = self._compute_scores(
            candidate_name=candidate_name,
            current_title=cur_title,
            current_company=cur_comp,
            location=location,
            education=primary_edu,
            skills=skills,
            email=email,
            phone=phone,
            linkedin=linkedin,
            exp_history=exp_history,
        )

        if quality_score < 30 and not (cur_comp or cur_title):
            logger.debug("SemanticFactorizer: Factorized candidate below minimum quality threshold (score: %d)", quality_score)
            return None

        notes = [f"Judgment: {judgment.category} ({judgment.confidence:.2f})"]
        if pronouns:
            notes.append(f"Pronouns: {pronouns}")
        if prev_comp:
            notes.append(f"Career progression: {prev_comp} -> {cur_comp}")
        if title_intel:
            notes.append(f"Level: {title_intel['seniority_level']} | Spec: {title_intel['domain_specialization']}")

        return FactorizedCandidate(
            canonical_name=candidate_name,
            pronouns=pronouns,
            current_title=cur_title,
            current_company=cur_comp,
            previous_title=prev_title,
            previous_company=prev_comp,
            experience_history=exp_history,
            location=location,
            education=primary_edu,
            education_history=edu_history,
            skills=skills,
            about_summary=about,
            primary_email=email,
            primary_phone=phone,
            linkedin_url=linkedin,
            quality_score=quality_score,
            identity_confidence=identity_confidence,
            field_provenance={"capture_id": capture_id},
            factorization_notes=notes,
            title_intel=title_intel,
        )

    def _segment_zones(self, lines: List[str]) -> Dict[str, List[str]]:
        """Segments lines into semantic zones based on profile headers."""
        zones = {
            "header": [],
            "about": [],
            "experience": [],
            "education": [],
            "skills": [],
            "other": [],
        }
        current_zone = "header"
        section_patterns = [
            ("about", re.compile(r"^About\b", re.IGNORECASE)),
            ("experience", re.compile(r"^(?:Experience|Work\s*experience)\b", re.IGNORECASE)),
            ("education", re.compile(r"^Education\b", re.IGNORECASE)),
            ("skills", re.compile(r"^Skills\b", re.IGNORECASE)),
            ("other", re.compile(r"^(?:Activity|Featured|Licenses|Recommendations|Interests|Languages|Volunteer|Publications|Honors|Courses)\b", re.IGNORECASE)),
        ]

        for line in lines:
            matched_zone = None
            for z_name, pat in section_patterns:
                if pat.match(line.strip()):
                    matched_zone = z_name
                    break
            if matched_zone:
                current_zone = matched_zone
                continue
            zones[current_zone].append(line)

        return zones

    def _factorize_name(
        self,
        header_lines: List[str],
        all_lines: List[str],
        window_title: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Factorizes verified person name and pronouns."""
        target_name = None
        pronouns = None

        # Check window title first if LinkedIn profile
        if " | LinkedIn" in window_title or " - LinkedIn" in window_title:
            m = re.match(r"^(?:\(\d+\+?\)\s*)?(.*?)\s*[|–—\-]\s*LinkedIn", window_title, re.IGNORECASE)
            if m:
                raw_title_name = m.group(1).strip()
                pro_m = re.search(r"\b(she/her|he/him|they/them|she/they|he/they)\b", raw_title_name, re.IGNORECASE)
                if pro_m:
                    pronouns = pro_m.group(1).lower()
                cleaned = clean_person_name(raw_title_name)
                if cleaned and is_valid_person_name(cleaned):
                    target_name = cleaned

        # Search header zone for name if not found in window title
        search_pool = header_lines if header_lines else all_lines[:10]
        if not target_name:
            for line in search_pool:
                cleaned = clean_person_name(line)
                if cleaned and is_valid_person_name(cleaned):
                    target_name = cleaned
                    break

        # Always scan for pronouns across header lines
        if not pronouns:
            for line in search_pool:
                pro_m = re.search(r"\b(she/her|he/him|they/them|she/they|he/they)\b", line, re.IGNORECASE)
                if pro_m:
                    pronouns = pro_m.group(1).lower()
                    break

        return target_name, pronouns

    def _factorize_experience(
        self,
        header_lines: List[str],
        exp_lines: List[str],
        window_title: str,
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], List[Dict[str, str]]]:
        """
        Factorizes career history into:
        current_title, current_company, previous_title, previous_company, structured history.
        """
        cur_title = None
        cur_comp = None
        prev_title = None
        prev_comp = None
        exp_history = []

        # 1. Look in header lines for headline / active position
        for line in header_lines:
            t, c = clean_title_and_company(line)
            if t and not cur_title and is_plausible_title(t):
                cur_title = t
            if c and not cur_comp and is_valid_company_name(c):
                cur_comp = c

        # 2. Parse Experience Section for chronological roles
        if exp_lines:
            parsed_roles = []
            i = 0
            while i < len(exp_lines):
                line = exp_lines[i].strip()
                if DATE_RANGE_PATTERN.search(line) or is_noise_text(line) or not line:
                    i += 1
                    continue

                # Case 1: Line has title + company combined (e.g., 'VP of Engineering at Stripe')
                t_split, c_split = clean_title_and_company(line)
                if t_split and c_split and is_valid_company_name(c_split):
                    title_candidate = t_split
                    comp_candidate = c_split
                elif is_plausible_title(line):
                    title_candidate = line
                    comp_candidate = None
                    if i + 1 < len(exp_lines) and is_valid_company_name(exp_lines[i + 1]):
                        comp_candidate = exp_lines[i + 1].strip()
                        i += 1
                elif is_valid_company_name(line):
                    comp_candidate = line
                    title_candidate = None
                    if i + 1 < len(exp_lines) and is_plausible_title(exp_lines[i + 1]):
                        title_candidate = exp_lines[i + 1].strip()
                        i += 1
                else:
                    i += 1
                    continue

                # Look ahead for date range
                dates = None
                for offset in range(1, 3):
                    if i + offset < len(exp_lines):
                        l_ahead = exp_lines[i + offset]
                        if re.search(r"\b(?:present|\d{4})\b", l_ahead, re.IGNORECASE):
                            dates = l_ahead.strip()
                            break

                if title_candidate or comp_candidate:
                    parsed_roles.append({
                        "title": title_candidate or "",
                        "company": comp_candidate or "",
                        "dates": dates or "",
                    })
                i += 1

            if parsed_roles:
                exp_history = parsed_roles
                # Most recent role is current if not already found
                if not cur_title and parsed_roles[0].get("title"):
                    cur_title = parsed_roles[0]["title"]
                if not cur_comp and parsed_roles[0].get("company"):
                    cur_comp = parsed_roles[0]["company"]

                # Previous role if distinct
                if len(parsed_roles) > 1:
                    prev_title = parsed_roles[1].get("title")
                    prev_comp = parsed_roles[1].get("company")
                    if prev_comp and cur_comp and prev_comp.lower() == cur_comp.lower():
                        prev_comp = None

        return cur_title, cur_comp, prev_title, prev_comp, exp_history

    def _factorize_location(self, header_lines: List[str], all_lines: List[str]) -> Optional[str]:
        """Extracts and validates clean geographic location."""
        # Prefer header location
        for line in header_lines:
            if is_valid_location(line):
                cleaned = clean_location_text(line)
                if cleaned:
                    return cleaned

        # Fallback to general scan
        for line in all_lines[:15]:
            if is_valid_location(line):
                cleaned = clean_location_text(line)
                if cleaned:
                    return cleaned

        return None

    def _factorize_education(
        self,
        edu_lines: List[str],
        all_lines: List[str],
    ) -> Tuple[Optional[str], List[Dict[str, str]]]:
        """Factorizes primary educational credential and history."""
        history = []
        pool = edu_lines if edu_lines else all_lines

        i = 0
        while i < len(pool):
            line = pool[i].strip()
            if is_plausible_school(line):
                school = line
                degree = None
                if i + 1 < len(pool) and (is_plausible_degree(pool[i + 1]) or len(pool[i + 1].split()) <= 6):
                    degree = pool[i + 1].strip()
                    i += 1
                history.append({"school": school, "degree": degree or ""})
            i += 1

        primary = None
        if history:
            first = history[0]
            if first["degree"]:
                primary = f"{first['school']} — {first['degree']}"
            else:
                primary = first["school"]

        return primary, history

    def _factorize_skills(self, skill_lines: List[str], all_lines: List[str]) -> List[str]:
        """Extracts, cleans, and deduplicates verified technical/domain skills."""
        raw_skills = []
        source_pool = skill_lines if skill_lines else []

        for line in source_pool:
            parts = re.split(r"[,·•|\t]", line)
            for p in parts:
                s = p.strip()
                if is_valid_skill(s):
                    raw_skills.append(s)

        # Deduplicate preserving order
        seen = set()
        deduped = []
        for s in raw_skills:
            lower = s.lower()
            if lower not in seen:
                seen.add(lower)
                deduped.append(s)

        return deduped[:25]

    def _factorize_about(self, about_lines: List[str]) -> Optional[str]:
        """Cleans and consolidates the candidate's about/bio section."""
        if not about_lines:
            return None
        valid_lines = [l.strip() for l in about_lines if l.strip() and not is_noise_text(l)]
        if not valid_lines:
            return None
        combined = " ".join(valid_lines)
        # Limit to 600 characters
        return combined[:600]

    def _factorize_contact(
        self,
        lines: List[str],
        source_url: str,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Extracts email, phone, and LinkedIn URL."""
        email = None
        phone = None
        linkedin = None

        if "linkedin.com/in/" in source_url:
            linkedin = source_url

        for line in lines:
            if not email:
                em = EMAIL_REGEX.search(line)
                if em and "noemail" not in em.group(0):
                    email = em.group(0).lower()
            if not phone:
                ph = PHONE_REGEX.search(line)
                if ph:
                    phone = ph.group(0)
            if not linkedin:
                if "linkedin.com/in/" in line:
                    m = re.search(r"https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+/?", line)
                    if m:
                        linkedin = m.group(0)

        return email, phone, linkedin

    def _compute_scores(
        self,
        candidate_name: str,
        current_title: Optional[str],
        current_company: Optional[str],
        location: Optional[str],
        education: Optional[str],
        skills: List[str],
        email: Optional[str],
        phone: Optional[str],
        linkedin: Optional[str],
        exp_history: List[Dict[str, str]],
    ) -> Tuple[int, float]:
        """Calculates completeness score (0-100) and identity confidence (0.0-1.0)."""
        score = 0
        if candidate_name:
            score += 25
        if current_title:
            score += 20
        if current_company:
            score += 20
        if location:
            score += 10
        if education:
            score += 10
        if skills:
            score += min(10, len(skills) * 2)
        if email or phone or linkedin:
            score += 5

        conf = 0.0
        if candidate_name:
            conf += 0.30
        if current_company:
            conf += 0.20
        if current_title:
            conf += 0.15
        if linkedin:
            conf += 0.20
        elif email:
            conf += 0.15
        if location:
            conf += 0.05
        if education:
            conf += 0.05
        if exp_history:
            conf += 0.05

        return min(100, score), min(1.0, conf)
