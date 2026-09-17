"""
extractor/parsers/__init__.py — Modular Layout Parser Registry & Dispatcher

Provides modular parsers for each core layout:
- LinkedIn (Standard, Recruiter, Sales Navigator)
- ZoomInfo
- Apollo.io
- GitHub
- Indeed
- Resumes / Local Documents

Enforces:
1. Layout structural fingerprinting before parsing
2. Context distinction (PROFILE_PAGE, SEARCH_RESULTS, JOB_POSTING, COMPANY_PAGE, MESSAGING_THREAD)
3. Unknown platforms treated as observation-only (never auto-promoted).
"""

from typing import Optional, Dict, Any, List
from .base_parser import BasePlatformParser
from .linkedin_parser import LinkedInParser
from .zoominfo_parser import ZoomInfoParser
from .apollo_parser import ApolloParser
from .github_parser import GitHubParser
from .indeed_parser import IndeedParser
from .resume_parser import ResumeParser

PARSERS: List[BasePlatformParser] = [
    LinkedInParser(),
    ZoomInfoParser(),
    ApolloParser(),
    GitHubParser(),
    IndeedParser(),
    ResumeParser(),
]


def get_parser_for_context(
    url: str = "",
    platform_hint: str = "",
    window_title: str = "",
) -> Optional[BasePlatformParser]:
    """Finds the appropriate modular parser for the active layout context."""
    for parser in PARSERS:
        if parser.can_handle(url, platform_hint, window_title):
            return parser
    return None


def classify_layout_type(ocr_text: str, url: str = "", window_title: str = "") -> str:
    """Detects page layout type using structural fingerprints."""
    parser = get_parser_for_context(url, "", window_title)
    if parser:
        return parser.detect_page_type(ocr_text, url, window_title)
    
    text_low = (ocr_text or "").lower()
    if any(k in text_low for k in ("job description", "responsibilities", "requirements", "apply now")):
        return "JOB_POSTING"
    if any(k in text_low for k in ("search results", "filters", "showing 1-")):
        return "SEARCH_RESULTS"
    return "UNKNOWN"


def parse_with_modular_parsers(ocr_text: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Attempts extraction via the matched modular parser.
    If no parser matches (unknown platform), marks observation as OBSERVATION_ONLY.
    """
    url = context.get("source_url", "")
    platform_hint = context.get("platform", "")
    window_title = context.get("window_title", "")

    parser = get_parser_for_context(url, platform_hint, window_title)
    if parser:
        return parser.parse(ocr_text, context)

    # Unknown Platform: Observation-Only Mode (Pillar 4)
    # Never create a verified candidate from an unverified/unknown layout.
    return {
        "recruiter_name": None,
        "title": None,
        "company_name": None,
        "platform": "UNKNOWN",
        "page_type": "UNKNOWN",
        "is_observation_only": True,
        "reasons": ["OBSERVATION_ONLY: Unknown platform layout — candidate creation withheld"],
    }
