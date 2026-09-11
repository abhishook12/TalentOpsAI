"""
extractor/field_classifier.py — Field-Specific Semantic Extraction & Validation Engine

Enforces strict boundaries on every candidate field:
1. Name: Must possess human name characteristics, occur strictly in PROFILE_HEADER,
   and reject UI actions, navigation items, and window notification prefixes ("54 | ").
2. Title: Job headline recognition; rejects section headings ("Experience", "Overview").
3. Company: Resolves employer entities and strips noise.
4. Profile URL: First-class identity key extracted from browser context.
"""

from __future__ import annotations
import re
import urllib.parse
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

from scout_desktop.extractor.patterns import (
    is_valid_person_name,
    clean_person_name,
    is_plausible_title,
    is_valid_company_name,
    clean_company_name,
    clean_title_and_company,
)


@dataclass
class ExtractedFields:
    canonical_name: Optional[str] = None
    name_confidence: float = 0.0
    current_title: Optional[str] = None
    title_confidence: float = 0.0
    current_company: Optional[str] = None
    company_confidence: float = 0.0
    canonical_profile_url: Optional[str] = None
    url_confidence: float = 0.0
    field_evidence: Dict[str, str] = None


class FieldClassifier:
    """
    Dedicated classifier extracting and corroborating individual fields.
    """

    UI_ACTION_WORDS = {
        "overview", "about", "people", "experience", "education", "skills",
        "activity", "connect", "message", "follow", "home", "search",
        "notifications", "settings", "jobs", "more", "save", "share",
        "active window", "skip to", "view profile", "send message"
    }

    @classmethod
    def sanitize_window_title_name(cls, raw_title: str) -> Optional[str]:
        """
        Cleans notification badges and browser suffixes from window title.
        Example: '(54) Ritik Sharma | LinkedIn - Google Chrome' -> 'Ritik Sharma'
        Example: '54 | Ritik Sharma | LinkedIn' -> 'Ritik Sharma'
        """
        if not raw_title:
            return None

        # 1. Strip browser suffix
        t = re.sub(
            r"\s*[-—|]\s*(?:Google Chrome|Microsoft Edge|Mozilla Firefox|Brave|Opera)\s*$",
            "",
            raw_title.strip(),
            flags=re.IGNORECASE,
        )

        # 2. Match LinkedIn pattern
        # Handles (54), [54], 54 |, or other notification prefixes
        m = re.match(r"^(?:[\(\[]?\d+\+?[\)\]]?\s*[|•·–—\-]?\s*)?(.*?)\s*[|•·–—\-]\s*LinkedIn", t, flags=re.IGNORECASE)
        if m:
            cand = m.group(1).strip()
            # Double check for leftover leading digit fragments like "54 | Ritik"
            cand = re.sub(r"^\d+\s*[|•·–—\-]\s*", "", cand).strip()
            cand_clean = clean_person_name(cand)
            if cand_clean and not cls.is_ui_noise(cand_clean):
                return cand_clean

        # 3. Match ZoomInfo or Apollo pattern
        m_zi = re.match(r"^(?:ZoomInfo\s*(?:Lite)?\s*[-–|]\s*)?([^|•·–\n]+?)(?:\s*[|•·–]\s*ZoomInfo.*)?$", t, flags=re.IGNORECASE)
        if m_zi:
            cand = m_zi.group(1).strip()
            cand = re.sub(r"^\d+\s*[|•·–—\-]\s*", "", cand).strip()
            cand_clean = clean_person_name(cand)
            if cand_clean and not cls.is_ui_noise(cand_clean):
                return cand_clean

        return None

    @classmethod
    def is_ui_noise(cls, text: Optional[str]) -> bool:
        """Determines if a string is a known UI button, navigation word, or action."""
        if not text:
            return True
        t_low = text.strip().lower()
        if t_low in cls.UI_ACTION_WORDS:
            return True
        if any(w == t_low for w in ["overview", "connect", "message", "more", "save", "active window"]):
            return True
        # Check if contains phrases like "REASON: Overview"
        if "reason:" in t_low or "overview" in t_low and len(t_low) < 15:
            return True
        return False

    @classmethod
    def extract_name_from_header(cls, header_lines: List[str], window_title: str = "") -> Tuple[Optional[str], float, str]:
        """
        Extracts candidate name strictly from PROFILE_HEADER lines.
        Returns: (canonical_name, confidence, evidence)
        """
        # First priority: Title-corroborated name if window title has high confidence
        title_name = cls.sanitize_window_title_name(window_title)

        if header_lines:
            for idx, line in enumerate(header_lines[:6]):
                if cls.is_ui_noise(line):
                    continue

                cleaned = clean_person_name(line)
                if cleaned and is_valid_person_name(cleaned):
                    # Check if matches window title
                    if title_name and cleaned.lower() == title_name.lower():
                        return cleaned, 0.99, f"Profile header line #{idx+1} corroborated by window title"
                    # Even without title match, high confidence if in top 2 lines of header
                    conf = 0.94 if idx <= 1 else 0.85
                    return cleaned, conf, f"Profile header line #{idx+1}"

        if title_name and is_valid_person_name(title_name):
            return title_name, 0.90, "Window title pattern match"

        return None, 0.0, "No valid candidate name found in header"

    @classmethod
    def extract_title_and_company(
        cls,
        headline_lines: List[str],
        header_lines: List[str],
        experience_lines: List[str]
    ) -> Tuple[Optional[str], float, Optional[str], float]:
        """
        Extracts current job title and employer with confidence scores.
        """
        best_title = None
        title_conf = 0.0
        best_company = None
        comp_conf = 0.0

        # Pass 1: Parse headline lines (e.g. "Senior Technical Recruiter at Amazon")
        search_lines = headline_lines if headline_lines else header_lines[1:5]
        for line in search_lines:
            if cls.is_ui_noise(line):
                continue

            t, c = clean_title_and_company(line)
            if t and is_plausible_title(t):
                best_title = t
                title_conf = 0.95
            if c and is_valid_company_name(c):
                best_company = c
                comp_conf = 0.90
            if best_title and best_company:
                return best_title, title_conf, best_company, comp_conf

        # Pass 2: Inspect Experience section for current position
        if experience_lines and (not best_title or not best_company):
            for i, line in enumerate(experience_lines[:8]):
                if not best_title and is_plausible_title(line):
                    best_title = line
                    title_conf = 0.88
                    # Next line is often the company
                    if i + 1 < len(experience_lines):
                        nxt = experience_lines[i + 1]
                        if is_valid_company_name(nxt):
                            best_company = clean_company_name(nxt)
                            comp_conf = 0.85
                    break

        return best_title, title_conf, best_company, comp_conf

    @classmethod
    def extract_canonical_profile_url(cls, raw_url: Optional[str], platform: str = "LINKEDIN") -> Tuple[Optional[str], float]:
        """
        Normalizes candidate profile URL into a canonical identifier.
        """
        if not raw_url:
            return None, 0.0

        u = raw_url.strip()
        parsed = urllib.parse.urlparse(u)
        path = parsed.path

        if "linkedin.com" in parsed.netloc or platform == "LINKEDIN":
            m = re.search(r"^/in/([a-zA-Z0-9_\-\u00C0-\u017F%]+)", path)
            if m:
                slug = m.group(1).rstrip("/")
                return f"https://www.linkedin.com/in/{slug}", 1.0

        if "github.com" in parsed.netloc:
            parts = [p for p in path.split("/") if p]
            if len(parts) == 1:
                return f"https://github.com/{parts[0]}", 0.98

        if "zoominfo.com" in parsed.netloc:
            clean = u.split("?")[0].rstrip("/")
            return clean, 0.95

        if "apollo.io" in parsed.netloc:
            clean = u.split("?")[0].rstrip("/")
            return clean, 0.95

        return None, 0.0
