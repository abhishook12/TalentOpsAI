"""
extractor/parsers/resume_parser.py — Document / Resume Layout Parser
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


class ResumeParser(BasePlatformParser):
    @property
    def platform_name(self) -> str:
        return "Resume Document"

    def can_handle(self, url: str, platform_hint: str, window_title: str) -> bool:
        u = (url or "").lower()
        t = (window_title or "").lower()
        p = (platform_hint or "").lower()
        is_doc = any(ext in t for ext in (".pdf", ".docx", ".doc", "acrobat", "word", "reader"))
        return is_doc or "resume" in t or "curriculum vitae" in t or "cv" in t or "resume" in p

    def detect_page_type(self, ocr_text: str, url: str, window_title: str) -> str:
        return "DOCUMENT_RESUME"

    def parse(self, ocr_text: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        lines = [ln.strip() for ln in (ocr_text or "").split("\n") if ln.strip()]
        if not lines:
            return None

        name = None
        title = None
        company = None
        location = None
        email = None
        phone = None

        # Resumes almost universally have candidate name at line 0 or 1
        for line in lines[:4]:
            cand = clean_person_name(line)
            if cand and is_valid_person_name(cand) and not any(k in line.lower() for k in ("resume", "curriculum", "page 1", "confidential")):
                name = cand
                break

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
            if not title and is_plausible_title(line):
                title = line

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
            "platform": "Resume Document",
            "page_type": "DOCUMENT_RESUME",
            "canonical_profile_url": None,
            "source_url": context.get("source_url", ""),
        }
