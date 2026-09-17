"""
extractor/parsers/github_parser.py — GitHub Layout Parser
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
)


class GitHubParser(BasePlatformParser):
    @property
    def platform_name(self) -> str:
        return "GitHub"

    def can_handle(self, url: str, platform_hint: str, window_title: str) -> bool:
        u = (url or "").lower()
        t = (window_title or "").lower()
        return "github.com" in u or "github" in t

    def detect_page_type(self, ocr_text: str, url: str, window_title: str) -> str:
        u = (url or "").lower()
        text_low = (ocr_text or "").lower()
        if "/pull/" in u or "/issues" in u:
            return "CODE_PR_OR_ISSUE"
        if "/commit/" in u or "/blob/" in u:
            return "CODE_VIEW"
        if "repositories" in text_low and ("contributions" in text_low or "overview" in text_low or "followers" in text_low):
            return "PROFILE_PAGE"
        # Profile URL regex: github.com/username
        if re.match(r"^https?://(?:www\.)?github\.com/[a-zA-Z0-9_\-]+/?$", u):
            return "PROFILE_PAGE"
        return "UNKNOWN"

    def parse(self, ocr_text: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        page_url = context.get("source_url", "")
        win_title = context.get("window_title", "")
        page_type = self.detect_page_type(ocr_text, page_url, win_title)

        if page_type != "PROFILE_PAGE":
            return None

        lines = [ln.strip() for ln in (ocr_text or "").split("\n") if ln.strip()]
        if not lines:
            return None

        name = None
        company = None
        location = None
        email = None
        bio = None

        # Window title: "abhishekjadon (Abhishek Jadon) / Repositories" or "torvalds (Linus Torvalds) · GitHub"
        m = re.search(r"\(([^)]+)\)\s*·?\s*GitHub", win_title, re.IGNORECASE)
        if m:
            c_name = clean_person_name(m.group(1).strip())
            if c_name and is_valid_person_name(c_name):
                name = c_name

        for line in lines:
            if not name:
                cand = clean_person_name(line)
                if cand and is_valid_person_name(cand) and not any(k in line.lower() for k in ("github", "pull requests", "issues", "codespaces", "marketplace", "explore")):
                    name = cand
            if "@" in line and not email:
                em = EMAIL_REGEX.search(line)
                if em and is_valid_email(em.group(0)):
                    email = em.group(0).lower()
            if line.startswith("@") and len(line) > 1 and not company:
                co = clean_company_name(line.lstrip("@"))
                if is_valid_company_name(co):
                    company = co
            if any(ico in line.lower() for ico in ("📍", "location:", "based in")) or is_valid_location(clean_location_text(line)):
                loc = clean_location_text(line)
                if loc and is_valid_location(loc) and not location:
                    location = loc

        if not name:
            # Fallback to username from URL
            m_u = re.match(r"^https?://(?:www\.)?github\.com/([a-zA-Z0-9_\-]+)/?$", page_url)
            if m_u:
                name = m_u.group(1)

        if not name:
            return None

        return {
            "recruiter_name": name,
            "canonical_name": name,
            "title": "Software Engineer" if not bio else bio[:60],
            "company_name": company,
            "location": location,
            "email": email,
            "phone": None,
            "platform": "GitHub",
            "page_type": "PROFILE_PAGE",
            "canonical_profile_url": page_url if "github.com/" in page_url else None,
            "source_url": page_url,
        }
