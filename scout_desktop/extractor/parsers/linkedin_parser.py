"""
extractor/parsers/linkedin_parser.py — LinkedIn Modular Parser (Standard, Recruiter, Sales Nav)
"""

from __future__ import annotations
import re
import urllib.parse
from typing import Dict, Any, Optional, List
from .base_parser import BasePlatformParser
from scout_desktop.extractor.patterns import (
    clean_person_name,
    is_valid_person_name,
    clean_company_name,
    is_valid_company_name,
    clean_title_and_company,
    classify_semantic_entity,
    clean_location_text,
    is_valid_location,
    is_plausible_title,
    is_valid_email,
    EMAIL_REGEX,
    PHONE_REGEX,
)


class LinkedInParser(BasePlatformParser):
    @property
    def platform_name(self) -> str:
        return "LinkedIn"

    def can_handle(self, url: str, platform_hint: str, window_title: str) -> bool:
        u = (url or "").lower()
        p = (platform_hint or "").lower()
        t = (window_title or "").lower()
        if "linkedin.com" in u or "linkedin" in p or "linkedin" in t:
            return True
        return False

    def detect_page_type(self, ocr_text: str, url: str, window_title: str) -> str:
        u = (url or "").lower()
        t = (window_title or "").lower()
        text_low = (ocr_text or "").lower()

        if "/jobs/" in u or "about the job" in text_low or "job details" in text_low:
            return "JOB_POSTING"
        if "/company/" in u or "/school/" in u:
            return "COMPANY_PAGE"
        if "/messaging/" in u or "- messaging" in t:
            return "MESSAGING_THREAD"
        if "/search/results/" in u or "see all results" in text_low or "people who also viewed" in text_low and "/in/" not in u:
            return "SEARCH_RESULTS"
        if "/in/" in u or "sales/lead/" in u or "recruiter/profile/" in u:
            return "PROFILE_PAGE"

        # Content signature detection for profile header
        has_profile_sections = any(sec in text_low for sec in ("experience", "about", "activity", "education", "skills", "contact info"))
        if has_profile_sections and (" | linkedin" in t or "linkedin" in t):
            return "PROFILE_PAGE"

        return "PROFILE_PAGE" if "linkedin" in t else "UNKNOWN"

    def parse(self, ocr_text: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        page_url = context.get("source_url", "")
        win_title = context.get("window_title", "")
        page_type = self.detect_page_type(ocr_text, page_url, win_title)

        if page_type in ("JOB_POSTING", "COMPANY_PAGE", "MESSAGING_THREAD"):
            return None  # Non-candidate contexts

        lines = [ln.strip() for ln in (ocr_text or "").split("\n") if ln.strip()]
        if not lines:
            return None

        name = None
        title = None
        company = None
        location = None
        email = None
        phone = None

        # 1. Try window title extraction for name (e.g. "Elizabeth Bowers | LinkedIn - Google Chrome")
        m_title = re.match(r"^(?:\(\d+\+?\)\s*)?([^|•·\n]+?)\s*[|•·]\s*LinkedIn", win_title, re.IGNORECASE)
        if m_title:
            cand_from_title = clean_person_name(m_title.group(1).strip())
            if cand_from_title and is_valid_person_name(cand_from_title):
                name = cand_from_title

        # 2. Extract from OCR lines (Header block heuristic)
        # In LinkedIn, line 0 or line 1 is usually the name, followed by headline (title at company), then location
        name_idx = -1
        for i, line in enumerate(lines[:8]):
            # Ignore navigation lines
            if any(nav in line.lower() for nav in ("feed", "mynetwork", "jobs", "messaging", "notifications", "search", "skip to")):
                continue
            cleaned = clean_person_name(line)
            if cleaned and is_valid_person_name(cleaned):
                if not name:
                    name = cleaned
                name_idx = i
                break

        # If name found in OCR lines, inspect subsequent lines for Title and Company
        if name_idx >= 0:
            for line in lines[name_idx + 1 : name_idx + 6]:
                # Parse headline (e.g. "Senior Technical Recruiter at Amazon" or "Staff Product Designer | Figma | Design Systems")
                t_cand, c_cand = clean_title_and_company(line)
                if not title and t_cand and is_plausible_title(t_cand):
                    title = t_cand
                if not company and c_cand:
                    c_clean = clean_company_name(c_cand)
                    if c_clean and is_valid_company_name(c_clean) and classify_semantic_entity(c_clean).get("entity_type") == "COMPANY":
                        company = c_clean
                elif not title and is_plausible_title(line):
                    title = line.strip()
                elif not location:
                    loc_cand = clean_location_text(line)
                    if loc_cand and is_valid_location(loc_cand):
                        location = loc_cand
                elif title and not company and not is_plausible_title(line) and not is_valid_location(line):
                    co = clean_company_name(line)
                    if co and is_valid_company_name(co):
                        se = classify_semantic_entity(co)
                        if se.get("entity_type") == "COMPANY" and se.get("confidence", 0) >= 0.90:
                            company = co

        # Regex scan for emails and phones anywhere in profile text
        for line in lines:
            if not email:
                em = EMAIL_REGEX.search(line)
                if em and is_valid_email(em.group(0)):
                    email = em.group(0).lower()
            if not phone:
                ph = PHONE_REGEX.search(line)
                if ph and len(re.sub(r"\D", "", ph.group(0))) >= 10:
                    phone = ph.group(0).strip()

        # Canonical Profile URL
        canonical_url = page_url if "linkedin.com/in/" in page_url else None

        if not name:
            return None

        return {
            "recruiter_name": name,
            "canonical_name": name,
            "title": title,
            "company_name": company,
            "location": location,
            "email": email,
            "phone": phone,
            "platform": "LinkedIn",
            "page_type": page_type,
            "canonical_profile_url": canonical_url,
            "source_url": page_url,
        }
