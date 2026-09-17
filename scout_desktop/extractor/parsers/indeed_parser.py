"""
extractor/parsers/indeed_parser.py — Indeed Resume / Candidate Layout Parser
"""

from __future__ import annotations
import re
from typing import Dict, Any, Optional
from .base_parser import BasePlatformParser
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


class IndeedParser(BasePlatformParser):
    @property
    def platform_name(self) -> str:
        return "Indeed"

    def can_handle(self, url: str, platform_hint: str, window_title: str) -> bool:
        u = (url or "").lower()
        t = (window_title or "").lower()
        return "indeed.com" in u or "indeed" in t

    def detect_page_type(self, ocr_text: str, url: str, window_title: str) -> str:
        u = (url or "").lower()
        text_low = (ocr_text or "").lower()
        if "/jobs" in u or "/viewjob" in u:
            return "JOB_POSTING"
        if "/cmp/" in u or "company reviews" in text_low:
            return "COMPANY_PAGE"
        if "/r/" in u or "/resume" in u or "work experience" in text_low and "education" in text_low:
            return "PROFILE_PAGE"
        return "PROFILE_PAGE"

    def parse(self, ocr_text: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        page_url = context.get("source_url", "")
        win_title = context.get("window_title", "")
        page_type = self.detect_page_type(ocr_text, page_url, win_title)

        if page_type in ("JOB_POSTING", "COMPANY_PAGE"):
            return None

        lines = [ln.strip() for ln in (ocr_text or "").split("\n") if ln.strip()]
        if not lines:
            return None

        name = None
        title = None
        company = None
        location = None
        email = None
        phone = None

        # Indeed resume header: First non-UI line is typically candidate name
        for line in lines[:6]:
            if not name:
                cand = clean_person_name(line)
                if cand and is_valid_person_name(cand) and not any(k in line.lower() for k in ("indeed", "resume", "find resumes", "messages", "notifications")):
                    name = cand
                    continue
            if name and not title and is_plausible_title(line):
                title = line
                continue
            if name and not location:
                loc = clean_location_text(line)
                if loc and is_valid_location(loc):
                    location = loc
                    continue

        for line in lines:
            if not email:
                em = EMAIL_REGEX.search(line)
                if em and is_valid_email(em.group(0)):
                    email = em.group(0).lower()
            if not phone:
                ph = PHONE_REGEX.search(line)
                if ph and len(re.sub(r"\D", "", ph.group(0))) >= 10:
                    phone = ph.group(0).strip()
            if not company and " at " in line:
                parts = line.split(" at ")
                if len(parts) == 2:
                    co = clean_company_name(parts[1])
                    if is_valid_company_name(co):
                        company = co

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
            "platform": "Indeed",
            "page_type": page_type,
            "canonical_profile_url": page_url if "/r/" in page_url else None,
            "source_url": page_url,
        }
