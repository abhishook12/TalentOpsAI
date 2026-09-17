"""
extractor/parsers/apollo_parser.py — Apollo.io Layout Parser
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


class ApolloParser(BasePlatformParser):
    @property
    def platform_name(self) -> str:
        return "Apollo"

    def can_handle(self, url: str, platform_hint: str, window_title: str) -> bool:
        u = (url or "").lower()
        p = (platform_hint or "").lower()
        t = (window_title or "").lower()
        return "apollo.io" in u or "apollo" in p or "apollo" in t

    def detect_page_type(self, ocr_text: str, url: str, window_title: str) -> str:
        u = (url or "").lower()
        text_low = (ocr_text or "").lower()
        if "/companies/" in u or "company overview" in text_low:
            return "COMPANY_PAGE"
        if "/search" in u or "search contacts" in text_low and "/people/" not in u:
            return "SEARCH_RESULTS"
        if "/people/" in u or "verified email" in text_low or "view mobile" in text_low:
            return "PROFILE_PAGE"
        return "PROFILE_PAGE"

    def parse(self, ocr_text: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        page_url = context.get("source_url", "")
        win_title = context.get("window_title", "")
        page_type = self.detect_page_type(ocr_text, page_url, win_title)

        if page_type in ("COMPANY_PAGE", "SEARCH_RESULTS"):
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

        # Apollo window title format: "John Smith - VP of Sales at Snowflake | Apollo.io"
        m = re.match(r"^([^|•·\n\-]+?)\s*[-–—|]\s*([^|•·\n]+?)\s*(?:at|@)\s*([^|•·\n]+?)\s*[|•·]\s*Apollo", win_title, re.IGNORECASE)
        if m:
            c_name = clean_person_name(m.group(1).strip())
            if c_name and is_valid_person_name(c_name):
                name = c_name
            t_cand = m.group(2).strip()
            if is_plausible_title(t_cand):
                title = t_cand
            co_cand = clean_company_name(m.group(3).strip())
            if is_valid_company_name(co_cand):
                company = co_cand

        for i, line in enumerate(lines[:10]):
            if not name:
                cand = clean_person_name(line)
                if cand and is_valid_person_name(cand) and not any(k in line.lower() for k in ("apollo", "sequences", "enrich", "export", "signals")):
                    name = cand
                    continue
            if name and not title and is_plausible_title(line):
                title = line
                continue
            if name and not company:
                co = clean_company_name(line)
                if co and is_valid_company_name(co) and co.lower() != "apollo":
                    company = co
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
            if not location:
                loc = clean_location_text(line)
                if loc and is_valid_location(loc):
                    location = loc

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
            "platform": "Apollo",
            "page_type": page_type,
            "canonical_profile_url": page_url if "/people/" in page_url else None,
            "source_url": page_url,
        }
