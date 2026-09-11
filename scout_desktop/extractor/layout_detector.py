"""
extractor/layout_detector.py — Spatial & Semantic Layout Detector for Candidate Profiles

Decomposes structured OCR lines and spatial coordinates into semantic profile regions:
- PROFILE_HEADER: Primary card containing candidate photo, name, headline, location, company
- ABOUT_REGION: Narrative summary
- EXPERIENCE_REGION: Career timeline and role history
- EDUCATION_REGION: Degrees and institutions
- SKILLS_REGION: Verified skills list
- UI_ACTION_REGION: Buttons (Connect, Message, Follow, More, Save) and navigation tabs

Enforces strict zoning:
Candidate NAME must originate strictly from PROFILE_HEADER.
Candidate CURRENT_TITLE originates from HEADLINE or primary role in PROFILE_HEADER.
Candidate LOCATION originates from location metadata within PROFILE_HEADER.
"""

from __future__ import annotations
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


REGION_PROFILE_HEADER = "PROFILE_HEADER"
REGION_ABOUT = "ABOUT_REGION"
REGION_EXPERIENCE = "EXPERIENCE_REGION"
REGION_EDUCATION = "EDUCATION_REGION"
REGION_SKILLS = "SKILLS_REGION"
REGION_UI_ACTIONS = "UI_ACTION_REGION"
REGION_OTHER = "OTHER_REGION"


@dataclass
class ProfileLayout:
    """Represents the decomposed semantic regions of a professional profile page."""
    header_lines: List[str] = field(default_factory=list)
    headline_candidates: List[str] = field(default_factory=list)
    location_candidates: List[str] = field(default_factory=list)
    company_candidates: List[str] = field(default_factory=list)
    about_lines: List[str] = field(default_factory=list)
    experience_lines: List[str] = field(default_factory=list)
    education_lines: List[str] = field(default_factory=list)
    skills_lines: List[str] = field(default_factory=list)
    ui_noise_lines: List[str] = field(default_factory=list)
    raw_zones: Dict[str, List[str]] = field(default_factory=dict)


class LayoutDetector:
    """
    Analyzes ordered text lines from an active profile view and partitions them into
    authoritative semantic regions.
    """

    SECTION_HEADERS = [
        (REGION_ABOUT, re.compile(r"^(?:About|Summary|Overview)\b", re.IGNORECASE)),
        (REGION_EXPERIENCE, re.compile(r"^(?:Experience|Work\s*experience|Career\s*history)\b", re.IGNORECASE)),
        (REGION_EDUCATION, re.compile(r"^(?:Education|Academic\s*background)\b", re.IGNORECASE)),
        (REGION_SKILLS, re.compile(r"^(?:Skills|Top\s*skills|Core\s*competencies)\b", re.IGNORECASE)),
        (REGION_UI_ACTIONS, re.compile(r"^(?:Activity|Featured|Licenses|Recommendations|Interests|Languages|Volunteer|Publications|Honors|Courses)\b", re.IGNORECASE)),
    ]

    UI_ACTION_WORDS = {
        "connect", "message", "follow", "more", "save", "share", "pending", "open to",
        "send message", "endorse", "view profile", "contact info", "see all", "show more"
    }

    @classmethod
    def detect_layout(cls, lines: List[str]) -> ProfileLayout:
        """Segments raw line list into structured ProfileLayout."""
        clean_lines = [l.strip() for l in lines if l and l.strip()]
        layout = ProfileLayout()

        current_region = REGION_PROFILE_HEADER
        zones: Dict[str, List[str]] = {
            REGION_PROFILE_HEADER: [],
            REGION_ABOUT: [],
            REGION_EXPERIENCE: [],
            REGION_EDUCATION: [],
            REGION_SKILLS: [],
            REGION_UI_ACTIONS: [],
            REGION_OTHER: [],
        }

        for line in clean_lines:
            matched_region = None
            for region_name, pat in cls.SECTION_HEADERS:
                if pat.match(line):
                    matched_region = region_name
                    break

            if matched_region:
                current_region = matched_region
                # Record the section header itself as UI/section noise
                zones[REGION_UI_ACTIONS].append(line)
                continue

            # Check for inline UI action buttons
            if line.lower() in cls.UI_ACTION_WORDS:
                zones[REGION_UI_ACTIONS].append(line)
                continue

            zones[current_region].append(line)

        layout.header_lines = zones[REGION_PROFILE_HEADER]
        layout.about_lines = zones[REGION_ABOUT]
        layout.experience_lines = zones[REGION_EXPERIENCE]
        layout.education_lines = zones[REGION_EDUCATION]
        layout.skills_lines = zones[REGION_SKILLS]
        layout.ui_noise_lines = zones[REGION_UI_ACTIONS]
        layout.raw_zones = zones

        # Sub-segment header lines into Headline, Location, Company
        cls._subsegment_header(layout)

        return layout

    @classmethod
    def _subsegment_header(cls, layout: ProfileLayout):
        """
        Parses the PROFILE_HEADER lines into:
        - Name candidates (top prominent text)
        - Headline candidates (lines below name)
        - Location candidates (geographic patterns)
        - Current company candidates (company patterns)
        """
        header = layout.header_lines
        if not header:
            return

        for idx, line in enumerate(header):
            t_low = line.lower()

            # Skip UI actions and notifications
            if any(btn in t_low for btn in ["connect", "message", "follow", "share", "more", "save", "contact info"]):
                continue

            # Location indicators: city, state, country, 'greater ... area'
            is_loc = bool(re.search(
                r"\b(?:area|greater|united\s+states|india|canada|united\s+kingdom|germany|france|australia|"
                r"california|texas|new\s+york|florida|washington|ohio|illinois|georgia|north\s+carolina|"
                r"london|berlin|paris|sydney|singapore|bangalore|delhi|mumbai|hyderabad|pune)\b|"
                r",[A-Z\s]{2,}\b|[A-Za-z\s]+,\s*[A-Z]{2}\b",
                line,
                re.IGNORECASE,
            ))
            if is_loc and len(line) < 80:
                layout.location_candidates.append(line)
                continue

            # Company indicators: "at ...", "@ ...", or corporate keywords
            m_comp = re.search(r"\b(?:at|@)\s+([A-Za-z0-9\s\.\-&]+)", line, re.IGNORECASE)
            if m_comp:
                layout.company_candidates.append(m_comp.group(1).strip())

            # Headline candidates: usually 2nd or 3rd line in header
            if idx > 0 and len(line) > 10 and not is_loc:
                layout.headline_candidates.append(line)
