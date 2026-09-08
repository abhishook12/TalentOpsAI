"""
extractor/entity_extractor.py — Multi-Entity Intelligence Extractor & Profile Context Manager

Implements:
1. Multi-Entity Enumeration: Discovers all relevant people, companies, and jobs on screen.
2. Search & Company Grid Segmentation: Accurately segments multiple candidate cards on one screen.
3. Job vs Person Discrimination: Extracts Job entity while isolating Hiring Managers with true titles.
4. Active Profile Context Tracking: As user scrolls through About, Experience, Education,
   enriches the SAME person rather than creating duplicates.
5. Current vs Previous Employment distinction via date ranges and employer matching.
6. Small Text inspection (location, degree, school, skills).
7. Evidence Grounding Gate: Enforces evidence string on all observations.
"""

import re
import time
import logging
from typing import Optional, List, Dict, Any, Tuple

from .models import Observation, EntityCluster
from .patterns import (
    is_valid_location,
    clean_location_text,
    extract_connection_degree,
    clean_title_and_company,
    clean_company_name,
    is_valid_company_name,
    is_valid_person_name,
    is_plausible_title,
    is_plausible_school,
    is_plausible_degree,
    is_valid_skill,
    DATE_RANGE_PATTERN,
    DEGREE_KEYWORDS,
    WORKPLACE_TYPES,
    SCHOOL_KEYWORDS,
    is_noise_text,
    clean_person_name,
    EMAIL_REGEX,
    PHONE_REGEX,
)
from .timeline_parser import TimelineParser
from scout_desktop.extractor.semantic_factorizer import ProfileJudge, SemanticFactorizer

logger = logging.getLogger("scout.entity_extractor")


class EntityExtractor:
    def __init__(self):
        self.active_context_name: Optional[str] = None
        self.active_context_cluster: Optional[EntityCluster] = None
        self.last_context_update_time: float = 0.0
        self.timeline_parser = TimelineParser()

    def reset_context(self):
        """Resets active context when switching to a completely new page/window."""
        self.active_context_name = None
        self.active_context_cluster = None
        self.last_context_update_time = 0.0

    def _segment_profile_zones(self, clean_lines: List[str]) -> Dict[str, List[str]]:
        """
        Segments profile text lines into logical semantic zones:
        header, about, experience, education, skills, and other.
        """
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

        for line in clean_lines:
            matched_zone = None
            for zone_name, pat in section_patterns:
                if pat.match(line.strip()):
                    matched_zone = zone_name
                    break
            if matched_zone:
                current_zone = matched_zone
                continue
            zones[current_zone].append(line)

        return zones

    def extract_from_lines(
        self,
        lines: List[str],
        capture_id: str,
        source_url: str = "",
        window_title: str = "",
        inferred_candidate: Optional[str] = None,
    ) -> List[EntityCluster]:
        """
        Extracts open-ended entity clusters from structured text lines.
        Handles:
        - Job Postings vs People
        - Multiple candidate cards (Search / Company People listings)
        - Single candidate profiles across scrolls
        """
        clean_lines = [l.strip() for l in lines if l and l.strip()]
        if not clean_lines:
            return []

        # 0. Intelligent AI Triage: Judge if frame is a valid candidate profile vs system noise
        judgment = ProfileJudge.judge_frame(clean_lines, window_title, source_url)
        if not judgment.is_candidate_profile:
            logger.info("ProfileJudge: Frame rejected as %s (%s)", judgment.category, judgment.rejection_reason)
            return []

        # Case A: Job Posting Page
        if self._is_job_page(clean_lines, window_title, source_url):
            return self._extract_job_page(clean_lines, capture_id, source_url, window_title)

        # Case B: Multi-Person Grid / Search Results Listing
        card_boundaries = self._find_card_boundaries(clean_lines, window_title, source_url)
        if len(card_boundaries) >= 2:
            logger.info("Detected multi-person card layout with %d candidates", len(card_boundaries))
            clusters: List[EntityCluster] = []
            for i in range(len(card_boundaries)):
                start_idx = card_boundaries[i]
                end_idx = card_boundaries[i + 1] if i + 1 < len(card_boundaries) else len(clean_lines)
                card_chunk = clean_lines[start_idx:end_idx]
                c = self._extract_single_person_block(card_chunk, capture_id, source_url)
                if c and c.canonical_name:
                    clusters.append(c)
            if clusters:
                return clusters

        # Case C: Single Person Profile Page (With Multi-Scroll Context)
        zones = self._segment_profile_zones(clean_lines)
        header_lines = zones["header"]

        target_name = inferred_candidate
        name_line_idx = -1
        pronouns_found = None

        if target_name:
            pro_m = re.search(r"\b(she/her|he/him|they/them|she/they|he/they)\b", target_name, re.IGNORECASE)
            if pro_m:
                pronouns_found = pro_m.group(1).lower()
            cand_cleaned = clean_person_name(target_name)
            if cand_cleaned:
                target_name = cand_cleaned
            else:
                sans_p = re.sub(r"\s*[\(\[]?\b(?:she/her|he/him|they/them|she/they|he/they)\b[\)\]]?", "", target_name, flags=re.IGNORECASE).strip()
                if sans_p and is_valid_person_name(sans_p):
                    target_name = sans_p

        if not target_name:
            if " | LinkedIn" in window_title or " - LinkedIn" in window_title or window_title.endswith("LinkedIn"):
                m = re.match(r"^(?:\(\d+\+?\)\s*)?(.*?)\s*[|–—\-]\s*LinkedIn", window_title, re.IGNORECASE)
                if m:
                    raw_extracted = m.group(1).strip()
                    pro_m = re.search(r"\b(she/her|he/him|they/them|she/they|he/they)\b", raw_extracted, re.IGNORECASE)
                    if pro_m:
                        pronouns_found = pro_m.group(1).lower()
                    cand_cleaned = clean_person_name(raw_extracted)
                    if cand_cleaned:
                        target_name = cand_cleaned
                    else:
                        sans_pronoun = re.sub(r"\s*[\(\[]?\b(?:she/her|he/him|they/them|she/they|he/they)\b[\)\]]?", "", raw_extracted, flags=re.IGNORECASE).strip()
                        if is_valid_person_name(sans_pronoun):
                            target_name = sans_pronoun

        if not target_name:
            # First search header zone
            search_pool = header_lines if header_lines else clean_lines[:15]
            for idx, line in enumerate(search_pool[:15]):
                cand_clean = clean_person_name(line)
                if cand_clean:
                    pro_m = re.search(r"\b(she/her|he/him|they/them|she/they|he/they)\b", line, re.IGNORECASE)
                    if pro_m:
                        pronouns_found = pro_m.group(1).lower()
                    target_name = cand_clean
                    name_line_idx = idx
                    break

        if not target_name:
            return []

        if name_line_idx == -1:
            for idx, line in enumerate(clean_lines):
                if target_name.lower() in line.strip().lower():
                    name_line_idx = idx
                    break

        now = time.time()
        is_same_person = (
            self.active_context_name
            and target_name.lower() == self.active_context_name.lower()
            and (now - self.last_context_update_time) < 180.0
        )

        if is_same_person and self.active_context_cluster:
            cluster = self.active_context_cluster
            if pronouns_found and "pronouns" not in cluster.metadata:
                cluster.metadata["pronouns"] = pronouns_found
            logger.info("Enriching active profile context: '%s'", target_name)
        else:
            cluster = EntityCluster(canonical_name=target_name, entity_type="PERSON")
            if pronouns_found:
                cluster.metadata["pronouns"] = pronouns_found
            self.active_context_name = target_name
            self.active_context_cluster = cluster
            logger.info("New profile context locked: '%s'", target_name)

        self.last_context_update_time = now

        # Add Name observation (prevent duplicate on scroll)
        if not any(obs.predicate == "IDENTIFIED_AS" and obs.object_value == target_name for obs in cluster.observations):
            cluster.add_observation(Observation(
                semantic_type="PERSON",
                subject=target_name,
                predicate="IDENTIFIED_AS",
                object_value=target_name,
                confidence=0.98,
                evidence=target_name,
                capture_id=capture_id,
                source_url=source_url,
            ))

        # Connection Degree Scan (check header zone first)
        if not cluster.connection_degree:
            degree_pool = header_lines if header_lines else clean_lines[:10]
            for line in degree_pool[:10]:
                deg = extract_connection_degree(line)
                if deg and len(line) < 15 and not is_valid_location(line):
                    cluster.add_observation(Observation(
                        semantic_type="PERSON",
                        subject=target_name,
                        predicate="HAS_CONNECTION_DEGREE",
                        object_value=deg,
                        confidence=0.95,
                        evidence=line,
                        capture_id=capture_id,
                        source_url=source_url,
                    ))
                    break

        # Headline / Title / Current Company (Priority: header zone lines following candidate name)
        if not cluster.current_title or not cluster.current_company:
            candidate_pool = header_lines if header_lines else clean_lines
            candidate_range = (
                range(name_line_idx + 1, min(name_line_idx + 6, len(candidate_pool)))
                if name_line_idx >= 0
                else range(0, min(5, len(candidate_pool)))
            )
            for idx in candidate_range:
                if idx >= len(candidate_pool):
                    break
                line = candidate_pool[idx]
                if is_noise_text(line) or line.strip().lower() == target_name.lower():
                    continue
                if extract_connection_degree(line) and len(line) < 15:
                    continue
                if is_valid_location(line) or SCHOOL_KEYWORDS.search(line) or EMAIL_REGEX.search(line):
                    continue
                if re.match(r"^(?:experience|education|skills|licenses|about)\b", line, re.IGNORECASE):
                    continue

                if target_name.lower() in line.lower():
                    continue
                if clean_person_name(line) and clean_person_name(line).lower() == target_name.lower():
                    continue
                if len(line) >= 5:
                    title, comp = clean_title_and_company(line)
                    if title and title.lower() != target_name.lower() and is_plausible_title(title):
                        if not cluster.current_title:
                            cluster.add_observation(Observation(
                                semantic_type="PERSON",
                                subject=target_name,
                                predicate="HAS_TITLE",
                                object_value=title,
                                confidence=0.90,
                                evidence=line,
                                capture_id=capture_id,
                                source_url=source_url,
                            ))
                    if comp and is_valid_company_name(comp):
                        if not cluster.current_company:
                            cluster.add_observation(Observation(
                                semantic_type="PERSON",
                                subject=target_name,
                                predicate="WORKS_AT",
                                object_value=comp,
                                confidence=0.90,
                                evidence=line,
                                capture_id=capture_id,
                                source_url=source_url,
                            ))
                    if cluster.current_title and cluster.current_company:
                        break

        # Explicit Company Scan if not in headline (Strictly within header zone to prevent distractor capture)
        if not cluster.current_company and header_lines:
            for line in header_lines:
                if is_noise_text(line) or is_valid_location(line) or SCHOOL_KEYWORDS.search(line):
                    continue
                if line.lower() in (target_name.lower(), (cluster.current_title or "").lower()):
                    continue
                if target_name.lower() in line.lower() or "linkedin" in line.lower():
                    continue
                if extract_connection_degree(line):
                    continue
                if is_valid_company_name(line):
                    cluster.add_observation(Observation(
                        semantic_type="COMPANY",
                        subject=target_name,
                        predicate="WORKS_AT",
                        object_value=line,
                        confidence=0.85,
                        evidence=line,
                        capture_id=capture_id,
                        source_url=source_url,
                    ))
                    break

        # Primary Personal Location (Strictly from Header Zone with highest priority)
        if not cluster.location:
            loc_found = False
            if header_lines:
                for line in header_lines:
                    loc_candidate = clean_location_text(line)
                    if loc_candidate and is_valid_location(loc_candidate):
                        cluster.add_observation(Observation(
                            semantic_type="PERSON",
                            subject=target_name,
                            predicate="LOCATED_IN",
                            object_value=loc_candidate,
                            confidence=0.95,
                            evidence=line,
                            capture_id=capture_id,
                            source_url=source_url,
                        ))
                        loc_found = True
                        break

            # Fallback: if header was not in current scrolled frame, check lines before Experience
            if not loc_found and not header_lines:
                for line in clean_lines:
                    if re.match(r"^(?:experience|education|skills|licenses)\b", line, re.IGNORECASE):
                        break
                    loc_candidate = clean_location_text(line)
                    if loc_candidate and is_valid_location(loc_candidate):
                        cluster.add_observation(Observation(
                            semantic_type="PERSON",
                            subject=target_name,
                            predicate="LOCATED_IN",
                            object_value=loc_candidate,
                            confidence=0.90,
                            evidence=line,
                            capture_id=capture_id,
                            source_url=source_url,
                        ))
                        break

        # Employment History (Robust Experience Parser)
        self._parse_experience_section(clean_lines, cluster, target_name, capture_id, source_url)

        # Education Section (Dedicated multi-line college & degree parser)
        self._parse_education_section(clean_lines, cluster, target_name, capture_id, source_url)

        # Skills Section (Dedicated skills parser)
        self._parse_skills_section(clean_lines, cluster, target_name, capture_id, source_url)

        # About / Summary Intelligence Processing (Section 21 of Spec)
        self._parse_about_section(clean_lines, cluster, target_name, capture_id, source_url)

        # Email & Phone Scan
        for line in clean_lines:
            m_email = EMAIL_REGEX.search(line)
            if m_email and not any(o.predicate == "HAS_EMAIL" for o in cluster.observations):
                email_val = m_email.group(0).lower()
                cluster.add_observation(Observation(
                    semantic_type="PERSON",
                    subject=target_name,
                    predicate="HAS_EMAIL",
                    object_value=email_val,
                    confidence=0.96,
                    evidence=line,
                    capture_id=capture_id,
                    source_url=source_url,
                ))
            m_phone = PHONE_REGEX.search(line)
            if m_phone and not any(o.predicate == "HAS_PHONE" for o in cluster.observations):
                phone_val = m_phone.group(0).strip()
                cluster.add_observation(Observation(
                    semantic_type="PERSON",
                    subject=target_name,
                    predicate="HAS_PHONE",
                    object_value=phone_val,
                    confidence=0.90,
                    evidence=line,
                    capture_id=capture_id,
                    source_url=source_url,
                ))

        # Signals
        full_text = " ".join(clean_lines).lower()
        if "open to work" in full_text or "#opentowork" in full_text:
            cluster.add_observation(Observation(
                semantic_type="PERSON",
                subject=target_name,
                predicate="HAS_HIRING_SIGNAL",
                object_value="Open to work",
                confidence=0.95,
                evidence="#OpenToWork badge",
                capture_id=capture_id,
                source_url=source_url,
            ))

        return [cluster]

    def _parse_about_section(
        self,
        clean_lines: List[str],
        cluster: EntityCluster,
        target_name: str,
        capture_id: str,
        source_url: str,
    ):
        """
        Extracts structured intelligence from the About / Summary section (Section 21 of Spec).
        Parses:
        - Full contextual About paragraph
        - Years of recruiting / professional experience (e.g. '15+ years in recruitment')
        - Sourcing & functional specializations (e.g. 'sourcing software engineers')
        - Industry experience (e.g. 'finance, healthcare and marketing')
        """
        in_about = False
        about_lines = []
        for line in clean_lines:
            if re.match(r"^About\b", line, re.IGNORECASE):
                in_about = True
                continue
            if in_about and re.match(r"^(?:Experience|Education|Skills|Activity|Featured|Licenses|Recommendations)\b", line, re.IGNORECASE):
                break
            if in_about:
                if not is_noise_text(line) and len(line) > 3:
                    about_lines.append(line)

        if not about_lines:
            return

        about_text = " ".join(about_lines)
        if len(about_text) < 10:
            return

        # 1. Base About Summary observation
        cluster.add_observation(Observation(
            semantic_type="PERSON",
            subject=target_name,
            predicate="HAS_ABOUT_SUMMARY",
            object_value=about_text[:400],
            confidence=0.92,
            evidence=about_text[:120],
            capture_id=capture_id,
            source_url=source_url,
        ))

        # 2. Years of Experience (e.g., '15+ years in recruitment', '8 years of experience')
        exp_match = re.search(r"\b(\d+\+?\s*(?:years?|yrs?)(?:\s+(?:in|of)\s+[a-zA-Z\s]+)?)\b", about_text, re.IGNORECASE)
        if exp_match:
            val = exp_match.group(1).strip()
            cluster.add_observation(Observation(
                semantic_type="PROFESSIONAL_SIGNAL",
                subject=target_name,
                predicate="HAS_YEARS_EXPERIENCE",
                object_value=val,
                confidence=0.90,
                evidence=exp_match.group(0),
                capture_id=capture_id,
                source_url=source_url,
            ))

        # 3. Specialization (e.g. 'specialized in sourcing software engineers', 'focus on technical recruiting')
        for spec_m in re.finditer(r"\b(?:specializ(?:ed|ing|ation)(?:\s+in)?|focus(?:ed|ing)?\s+on|expert(?:ise)?\s+in)\s+([a-zA-Z\s,/-]{4,50}?(?=\s+across|\s+for|\s+within|[.;\n]|$))", about_text, re.IGNORECASE):
            spec_val = spec_m.group(1).strip()
            if len(spec_val) >= 4:
                cluster.add_observation(Observation(
                    semantic_type="SPECIALIZATION",
                    subject=target_name,
                    predicate="SPECIALIZED_IN",
                    object_value=spec_val,
                    confidence=0.88,
                    evidence=spec_m.group(0),
                    capture_id=capture_id,
                    source_url=source_url,
                ))

        # 4. Industry Experience (e.g. finance, healthcare, marketing)
        COMMON_INDUSTRIES = [
            "finance", "healthcare", "marketing", "technology", "fintech",
            "cybersecurity", "aerospace", "defense", "telecom", "manufacturing",
            "biotech", "retail", "energy", "e-commerce", "cloud computing"
        ]
        for ind in COMMON_INDUSTRIES:
            if re.search(rf"\b{ind}\b", about_text, re.IGNORECASE):
                cluster.add_observation(Observation(
                    semantic_type="INDUSTRY",
                    subject=target_name,
                    predicate="HAS_INDUSTRY_EXPERIENCE",
                    object_value=ind.capitalize(),
                    confidence=0.85,
                    evidence=f"Mentioned {ind} in profile About section",
                    capture_id=capture_id,
                    source_url=source_url,
                ))

    def _parse_experience_section(
        self,
        clean_lines: List[str],
        cluster: EntityCluster,
        target_name: str,
        capture_id: str,
        source_url: str,
    ):
        """
        Parses multi-role experience listings from the Experience section.
        Distinguishes current company (Present) from previous employers.
        """
        in_experience = False
        exp_lines = []
        for line in clean_lines:
            if re.match(r"^Experience\b", line, re.IGNORECASE):
                in_experience = True
                continue
            if in_experience and re.match(r"^(?:Education|Skills|Licenses|Interests|Recommendations)\b", line, re.IGNORECASE):
                break
            if in_experience:
                exp_lines.append(line)

        if not exp_lines:
            return

        i = 0
        while i < len(exp_lines):
            line = exp_lines[i]

            # Skip locations, date lines, noise, or pure employment types
            if (
                is_valid_location(clean_location_text(line))
                or DATE_RANGE_PATTERN.search(line)
                or is_noise_text(line)
                or WORKPLACE_TYPES.fullmatch(line.strip().lower())
            ):
                i += 1
                continue

            # Format 1: Inline "Title at Company"
            if re.search(r"\s+(?:at|@)\s+", line, re.IGNORECASE):
                t, c = clean_title_and_company(line)
                if t and c and is_valid_company_name(c):
                    if not cluster.current_company:
                        cluster.add_observation(Observation(
                            semantic_type="PERSON",
                            subject=target_name,
                            predicate="WORKS_AT",
                            object_value=c,
                            confidence=0.90,
                            evidence=line,
                            capture_id=capture_id,
                            source_url=source_url,
                        ))
                    elif c.lower() != cluster.current_company.lower():
                        cluster.add_observation(Observation(
                            semantic_type="PERSON",
                            subject=target_name,
                            predicate="PREVIOUSLY_WORKED_AT",
                            object_value=c,
                            confidence=0.88,
                            evidence=line,
                            capture_id=capture_id,
                            source_url=source_url,
                            attributes={"title": t},
                        ))
                i += 1
                continue

            # Format 2: Multi-line entry (Title + Company or Company + Title):
            if i + 1 < len(exp_lines):
                l1 = line
                l2 = exp_lines[i + 1]

                # Determine which line is Title vs Company using is_plausible_title
                if is_plausible_title(l1) and not is_plausible_title(l2):
                    title_candidate = l1
                    comp_candidate = l2
                elif not is_plausible_title(l1) and is_plausible_title(l2):
                    title_candidate = l2
                    comp_candidate = l1
                else:
                    title_candidate = l1
                    comp_candidate = l2

                comp_cleaned = clean_company_name(comp_candidate)

                if is_valid_company_name(comp_cleaned):
                    # Check date range line if present
                    date_line = exp_lines[i + 2] if i + 2 < len(exp_lines) else ""
                    start_iso, end_iso = self.timeline_parser.parse_date_range(date_line)
                    tenure_mos = self.timeline_parser.calculate_tenure_months(start_iso, end_iso) if start_iso else None
                    is_present = bool(re.search(r"\bpresent\b", date_line, re.IGNORECASE)) or (start_iso and not end_iso and "present" in date_line.lower())

                    role_attrs = {
                        "title": title_candidate,
                        "start_date": start_iso,
                        "end_date": end_iso,
                        "tenure_months": tenure_mos,
                        "date_text": date_line if date_line else None,
                    }

                    if is_present:
                        # Confirmed CURRENT employer
                        cluster.add_observation(Observation(
                            semantic_type="PERSON",
                            subject=target_name,
                            predicate="WORKS_AT",
                            object_value=comp_cleaned,
                            confidence=0.95,
                            evidence=f"{title_candidate} | {comp_candidate} | {date_line}",
                            capture_id=capture_id,
                            source_url=source_url,
                            attributes=role_attrs,
                        ))
                        if not cluster.current_title or len(title_candidate) > len(cluster.current_title):
                            cluster.add_observation(Observation(
                                semantic_type="PERSON",
                                subject=target_name,
                                predicate="HAS_TITLE",
                                object_value=title_candidate,
                                confidence=0.92,
                                evidence=f"{title_candidate} | {comp_candidate}",
                                capture_id=capture_id,
                                source_url=source_url,
                                attributes={"start_date": start_iso, "end_date": end_iso},
                            ))
                    else:
                        # Confirmed PREVIOUS employer
                        if not cluster.current_company or comp_cleaned.lower() != cluster.current_company.lower():
                            cluster.add_observation(Observation(
                                semantic_type="PERSON",
                                subject=target_name,
                                predicate="PREVIOUSLY_WORKED_AT",
                                object_value=comp_cleaned,
                                confidence=0.88,
                                evidence=f"{title_candidate} | {comp_candidate} | {date_line}",
                                capture_id=capture_id,
                                source_url=source_url,
                                attributes=role_attrs,
                            ))
                    i += 2
                    continue

            i += 1

    def _parse_education_section(
        self,
        clean_lines: List[str],
        cluster: EntityCluster,
        target_name: str,
        capture_id: str,
        source_url: str,
    ):
        """
        Parses structured education entries from the Education section and header widgets.
        Extracts:
        - Institution name (College / University / School)
        - Degree & Field of Study (e.g. 'Bachelor of Science - BS, Computer Science')
        - Attendance / Graduation date range (e.g. '2014 - 2018')
        """
        in_edu = False
        edu_lines = []
        for line in clean_lines:
            if re.match(r"^Education\b", line, re.IGNORECASE):
                in_edu = True
                continue
            if in_edu and re.match(r"^(?:Skills|Experience|Licenses|Activities|Interests|Recommendations|Languages|About|Volunteer)\b", line, re.IGNORECASE):
                break
            if in_edu:
                edu_lines.append(line)

        if edu_lines:
            i = 0
            while i < len(edu_lines):
                line = edu_lines[i]
                if is_noise_text(line):
                    i += 1
                    continue

                # Check if this line is an educational institution
                school_match = is_plausible_school(line) or bool(SCHOOL_KEYWORDS.search(line))
                if school_match and not is_plausible_degree(line):
                    cleaned_school = re.sub(r"^Education:\s*", "", line, flags=re.IGNORECASE)
                    cleaned_school = re.sub(r"\. Click to skip.*$", "", cleaned_school, flags=re.IGNORECASE).strip()
                    cleaned_school = re.sub(r"[·•|].*$", "", cleaned_school).strip()

                    degree_val = None
                    dates_val = None
                    lines_consumed = 0

                    # Look ahead up to 3 lines for degree and dates
                    look_ahead = edu_lines[i + 1 : min(i + 4, len(edu_lines))]
                    for la_idx, la_line in enumerate(look_ahead):
                        if is_noise_text(la_line):
                            continue
                        if not degree_val and (is_plausible_degree(la_line) or bool(DEGREE_KEYWORDS.search(la_line))):
                            degree_val = la_line.strip()
                            lines_consumed = max(lines_consumed, la_idx + 1)
                            continue
                        if not dates_val and re.search(r"\b(?:\d{4}|\d{4}\s*[-–—]\s*(?:\d{4}|present))\b", la_line, re.IGNORECASE):
                            dates_val = la_line.strip()
                            lines_consumed = max(lines_consumed, la_idx + 1)
                            continue

                    # Add atomic observations
                    cluster.add_observation(Observation(
                        semantic_type="PERSON",
                        subject=target_name,
                        predicate="STUDIED_AT",
                        object_value=cleaned_school,
                        confidence=0.95,
                        evidence=line,
                        capture_id=capture_id,
                        source_url=source_url,
                        attributes={"degree": degree_val, "dates": dates_val} if degree_val or dates_val else None,
                    ))

                    if degree_val:
                        cluster.add_observation(Observation(
                            semantic_type="PERSON",
                            subject=target_name,
                            predicate="HAS_DEGREE",
                            object_value=degree_val,
                            confidence=0.92,
                            evidence=f"{cleaned_school} | {degree_val}",
                            capture_id=capture_id,
                            source_url=source_url,
                        ))

                    i += 1 + lines_consumed
                    continue
                elif is_plausible_degree(line):
                    cluster.add_observation(Observation(
                        semantic_type="PERSON",
                        subject=target_name,
                        predicate="HAS_DEGREE",
                        object_value=line.strip(),
                        confidence=0.88,
                        evidence=line,
                        capture_id=capture_id,
                        source_url=source_url,
                    ))

                i += 1
            return

        # Fallback: Compact education widget in header
        if not cluster.education:
            for line in clean_lines:
                if (is_plausible_school(line) or SCHOOL_KEYWORDS.search(line)) and not is_noise_text(line):
                    if is_valid_location(line) or (is_valid_company_name(line) and not SCHOOL_KEYWORDS.search(line)):
                        continue
                    cleaned_edu = re.sub(r"^Education:\s*", "", line, flags=re.IGNORECASE)
                    cleaned_edu = re.sub(r"\. Click to skip.*$", "", cleaned_edu, flags=re.IGNORECASE).strip()
                    cleaned_edu = re.sub(r"[·•|].*$", "", cleaned_edu).strip()
                    if len(cleaned_edu) >= 3:
                        cluster.add_observation(Observation(
                            semantic_type="PERSON",
                            subject=target_name,
                            predicate="STUDIED_AT",
                            object_value=cleaned_edu,
                            confidence=0.92,
                            evidence=line,
                            capture_id=capture_id,
                            source_url=source_url,
                        ))
                        break

    def _parse_skills_section(
        self,
        clean_lines: List[str],
        cluster: EntityCluster,
        target_name: str,
        capture_id: str,
        source_url: str,
    ):
        """
        Parses skills from the Skills section.
        Extracts clean skill names while rejecting UI boilerplate ('Show all', etc.).
        """
        in_skills = False
        skill_lines = []
        for line in clean_lines:
            if re.match(r"^Skills\b", line, re.IGNORECASE):
                in_skills = True
                continue
            if in_skills and re.match(r"^(?:Experience|Education|About|Activity|Featured|Licenses|Recommendations|Interests|Languages|Volunteer)\b", line, re.IGNORECASE):
                break
            if in_skills:
                skill_lines.append(line)

        if not skill_lines:
            return

        for line in skill_lines:
            # Handle bullet-separated or newline-separated skills: e.g. "PyTorch · Reinforcement Learning · Distributed Systems"
            parts = re.split(r"\s*[·•|]\s*", line)
            for part in parts:
                p = part.strip()
                if is_valid_skill(p):
                    cluster.add_observation(Observation(
                        semantic_type="SKILL",
                        subject=target_name,
                        predicate="HAS_SKILL",
                        object_value=p,
                        confidence=0.90,
                        evidence=line[:80],
                        capture_id=capture_id,
                        source_url=source_url,
                    ))

    def _is_job_page(self, clean_lines: List[str], window_title: str, source_url: str) -> bool:
        if "/jobs/" in source_url or "job" in window_title.lower():
            return True
        full_text = " ".join(clean_lines[:15]).lower()
        if any(trigger in full_text for trigger in ["about the job", "apply on company website", "easy apply", "meet the hiring team", "job description"]):
            return True
        return False

    def _extract_job_page(
        self,
        clean_lines: List[str],
        capture_id: str,
        source_url: str,
        window_title: str,
    ) -> List[EntityCluster]:
        clusters: List[EntityCluster] = []
        job_title = None
        company_name = None
        job_location = None

        for idx, line in enumerate(clean_lines[:8]):
            if is_noise_text(line):
                continue
            if not job_title and len(line) >= 4 and not is_valid_location(line) and not SCHOOL_KEYWORDS.search(line):
                t, c = clean_title_and_company(line)
                job_title = t or line
                if c and is_valid_company_name(c):
                    company_name = c
                continue
            if job_title and not company_name and len(line) >= 2 and not is_valid_location(line) and not extract_connection_degree(line):
                if is_valid_company_name(line):
                    company_name = line
                continue
            if not job_location and is_valid_location(clean_location_text(line)):
                job_location = clean_location_text(line)
                continue

        if job_title:
            job_cluster = EntityCluster(canonical_name=job_title, entity_type="JOB")
            job_cluster.current_title = job_title
            job_cluster.current_company = company_name
            job_cluster.location = job_location
            job_cluster.add_observation(Observation(
                semantic_type="JOB",
                subject=job_title,
                predicate="OFFERED_BY",
                object_value=company_name or "Unknown Company",
                confidence=0.95,
                evidence=f"{job_title} at {company_name}",
                capture_id=capture_id,
                source_url=source_url,
            ))
            if job_location:
                job_cluster.add_observation(Observation(
                    semantic_type="JOB",
                    subject=job_title,
                    predicate="LOCATED_IN",
                    object_value=job_location,
                    confidence=0.95,
                    evidence=job_location,
                    capture_id=capture_id,
                    source_url=source_url,
                ))
            clusters.append(job_cluster)

        hiring_person_idx = -1
        for idx, line in enumerate(clean_lines):
            if re.search(r"\b(meet the hiring team|job poster|hiring manager)\b", line, re.IGNORECASE):
                hiring_person_idx = idx + 1
                break

        if hiring_person_idx != -1 and hiring_person_idx < len(clean_lines):
            person_name = None
            person_title = None
            person_comp = company_name

            for line in clean_lines[hiring_person_idx : hiring_person_idx + 5]:
                if is_noise_text(line) or is_valid_location(line):
                    continue
                if not person_name and is_valid_person_name(line):
                    person_name = line
                    continue
                if person_name and not person_title and len(line) >= 4:
                    t, c = clean_title_and_company(line)
                    person_title = t or line
                    if c and is_valid_company_name(c):
                        person_comp = c
                    break

            if person_name:
                person_cluster = EntityCluster(canonical_name=person_name, entity_type="PERSON")
                person_cluster.current_title = person_title
                person_cluster.current_company = person_comp
                person_cluster.location = job_location
                person_cluster.add_observation(Observation(
                    semantic_type="PERSON",
                    subject=person_name,
                    predicate="IDENTIFIED_AS",
                    object_value=person_name,
                    confidence=0.98,
                    evidence=person_name,
                    capture_id=capture_id,
                    source_url=source_url,
                ))
                if person_title:
                    person_cluster.add_observation(Observation(
                        semantic_type="PERSON",
                        subject=person_name,
                        predicate="HAS_TITLE",
                        object_value=person_title,
                        confidence=0.92,
                        evidence=person_title,
                        capture_id=capture_id,
                        source_url=source_url,
                    ))
                if person_comp:
                    person_cluster.add_observation(Observation(
                        semantic_type="PERSON",
                        subject=person_name,
                        predicate="WORKS_AT",
                        object_value=person_comp,
                        confidence=0.92,
                        evidence=person_comp,
                        capture_id=capture_id,
                        source_url=source_url,
                    ))
                if job_title:
                    person_cluster.add_observation(Observation(
                        semantic_type="PERSON",
                        subject=person_name,
                        predicate="HIRING_FOR",
                        object_value=job_title,
                        confidence=0.95,
                        evidence="Meet the hiring team card",
                        capture_id=capture_id,
                        source_url=source_url,
                    ))
                clusters.append(person_cluster)

        return clusters

    def _find_card_boundaries(self, clean_lines: List[str], window_title: str, source_url: str) -> List[int]:
        if " | LinkedIn" in window_title and not any(term in window_title.lower() for term in ["search", "people"]):
            return []

        boundaries = []
        for idx, line in enumerate(clean_lines):
            if not is_valid_person_name(line):
                continue
            has_card_follower = False
            for follower in clean_lines[idx + 1 : min(idx + 5, len(clean_lines))]:
                if (
                    extract_connection_degree(follower)
                    or " at " in follower
                    or " @ " in follower
                    or is_valid_location(clean_location_text(follower))
                    or is_plausible_title(follower)
                    or any(kw in follower.lower() for kw in ["recruiter", "sourcer", "engineer", "director", "manager", "lead", "specialist"])
                ):
                    has_card_follower = True
                    break
            if has_card_follower:
                boundaries.append(idx)
        return boundaries

    def _extract_single_person_block(
        self,
        card_lines: List[str],
        capture_id: str,
        source_url: str,
    ) -> Optional[EntityCluster]:
        if not card_lines:
            return None
        candidate_name = card_lines[0]
        cluster = EntityCluster(canonical_name=candidate_name, entity_type="PERSON")
        cluster.add_observation(Observation(
            semantic_type="PERSON",
            subject=candidate_name,
            predicate="IDENTIFIED_AS",
            object_value=candidate_name,
            confidence=0.98,
            evidence=candidate_name,
            capture_id=capture_id,
            source_url=source_url,
        ))

        for line in card_lines[1:]:
            if is_noise_text(line):
                continue

            deg = extract_connection_degree(line)
            if deg and len(line) < 15 and not cluster.connection_degree:
                cluster.add_observation(Observation(
                    semantic_type="PERSON",
                    subject=candidate_name,
                    predicate="HAS_CONNECTION_DEGREE",
                    object_value=deg,
                    confidence=0.95,
                    evidence=line,
                    capture_id=capture_id,
                    source_url=source_url,
                ))
                continue

            if not cluster.current_title and len(line) >= 4 and not is_valid_location(line) and not SCHOOL_KEYWORDS.search(line):
                t, c = clean_title_and_company(line)
                if t:
                    cluster.add_observation(Observation(
                        semantic_type="PERSON",
                        subject=candidate_name,
                        predicate="HAS_TITLE",
                        object_value=t,
                        confidence=0.90,
                        evidence=line,
                        capture_id=capture_id,
                        source_url=source_url,
                    ))
                if c and is_valid_company_name(c):
                    cluster.add_observation(Observation(
                        semantic_type="PERSON",
                        subject=candidate_name,
                        predicate="WORKS_AT",
                        object_value=c,
                        confidence=0.90,
                        evidence=line,
                        capture_id=capture_id,
                        source_url=source_url,
                    ))
                continue

            if cluster.current_title and not cluster.current_company and is_valid_company_name(line):
                cluster.add_observation(Observation(
                    semantic_type="PERSON",
                    subject=candidate_name,
                    predicate="WORKS_AT",
                    object_value=line,
                    confidence=0.90,
                    evidence=line,
                    capture_id=capture_id,
                    source_url=source_url,
                ))
                continue

            if not cluster.location:
                loc = clean_location_text(line)
                if loc and is_valid_location(loc):
                    cluster.add_observation(Observation(
                        semantic_type="PERSON",
                        subject=candidate_name,
                        predicate="LOCATED_IN",
                        object_value=loc,
                        confidence=0.95,
                        evidence=line,
                        capture_id=capture_id,
                        source_url=source_url,
                    ))

        return cluster
