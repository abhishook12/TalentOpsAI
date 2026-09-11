"""
extractor/page_classifier.py — Scout Page & Context Classification Engine

Identifies whether the active browser/source window is:
- PERSON_PROFILE: Individual candidate profile page (LinkedIn /in/, ZoomInfo /profile/, Apollo /people/, etc.)
- PEOPLE_SEARCH: Multi-candidate search listing or company directory (/search/results/people, etc.)
- COMPANY_PAGE: Company overview/about page
- JOB_PAGE: Job description / requisition page
- MESSAGING: Chat, inbox, or direct messaging
- FEED: Home feed or social stream
- HOME: Platform homepage or portal landing
- UNKNOWN: Catch-all for non-recruiting / general web pages

Strict Gating Rule: Only PERSON_PROFILE and PEOPLE_SEARCH are processed for candidate profiles.
All other page types produce zero candidate records.
"""

from __future__ import annotations
import re
import urllib.parse
from typing import Optional, Dict, Any


PAGE_TYPE_PERSON_PROFILE = "PERSON_PROFILE"
PAGE_TYPE_PEOPLE_SEARCH = "PEOPLE_SEARCH"
PAGE_TYPE_COMPANY_PAGE = "COMPANY_PAGE"
PAGE_TYPE_JOB_PAGE = "JOB_PAGE"
PAGE_TYPE_MESSAGING = "MESSAGING"
PAGE_TYPE_FEED = "FEED"
PAGE_TYPE_HOME = "HOME"
PAGE_TYPE_UNKNOWN = "UNKNOWN"

VALID_CANDIDATE_PAGE_TYPES = {PAGE_TYPE_PERSON_PROFILE, PAGE_TYPE_PEOPLE_SEARCH}


class PageClassifier:
    """
    Classifies active web and desktop application views into authoritative page types.
    Combines URL structure, Window Title heuristics, and visible text cues.
    """

    @staticmethod
    def classify(
        url: Optional[str] = None,
        window_title: Optional[str] = None,
        platform: Optional[str] = None,
        visible_lines: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        """
        Returns a classification dict:
        {
            "page_type": str,
            "platform": str,
            "is_candidate_eligible": bool,
            "confidence": float,
            "canonical_url": Optional[str],
            "reason": str
        }
        """
        raw_url = (url or "").strip()
        raw_title = (window_title or "").strip()
        title_lower = raw_title.lower()
        url_lower = raw_url.lower()
        plat = (platform or "").upper()

        # 0. Check for desktop application / system noise
        if not raw_url and not raw_title:
            return {
                "page_type": PAGE_TYPE_UNKNOWN,
                "platform": "DESKTOP",
                "is_candidate_eligible": False,
                "confidence": 1.0,
                "canonical_url": None,
                "reason": "Empty URL and Window Title",
            }

        # Check for window titles that represent UI navigation or diagnostic labels
        if any(term in title_lower for term in [": people", ": overview", "reason:", "active window", "latest capture", "mailings - overview", "inbox ("]):
            return {
                "page_type": PAGE_TYPE_UNKNOWN,
                "platform": "DESKTOP_CAPTURE",
                "is_candidate_eligible": False,
                "confidence": 1.0,
                "canonical_url": None,
                "reason": "Window title represents UI navigation, inbox, or diagnostic label",
            }

        # 1. LinkedIn Classification
        if "linkedin.com" in url_lower or "linkedin" in title_lower or plat == "LINKEDIN":
            resolved_plat = "LINKEDIN"

            # Profile: /in/slug
            if "/in/" in url_lower:
                canonical = PageClassifier._clean_linkedin_profile_url(raw_url)
                return {
                    "page_type": PAGE_TYPE_PERSON_PROFILE,
                    "platform": resolved_plat,
                    "is_candidate_eligible": True,
                    "confidence": 0.98,
                    "canonical_url": canonical,
                    "reason": "LinkedIn /in/ profile URL detected",
                }

            # Search results: /search/results/people
            if "/search/results/people" in url_lower or ("/search/results/" in url_lower and "people" in url_lower):
                return {
                    "page_type": PAGE_TYPE_PEOPLE_SEARCH,
                    "platform": resolved_plat,
                    "is_candidate_eligible": True,
                    "confidence": 0.95,
                    "canonical_url": raw_url.split("?")[0] if raw_url else None,
                    "reason": "LinkedIn people search results URL detected",
                }

            # Company directory: /company/...
            if "/company/" in url_lower:
                return {
                    "page_type": PAGE_TYPE_COMPANY_PAGE,
                    "platform": resolved_plat,
                    "is_candidate_eligible": False,
                    "confidence": 0.95,
                    "canonical_url": raw_url.split("?")[0] if raw_url else None,
                    "reason": "LinkedIn company page / directory view (not a single candidate profile)",
                }

            # Company page general
            if "/company/" in url_lower:
                return {
                    "page_type": PAGE_TYPE_COMPANY_PAGE,
                    "platform": resolved_plat,
                    "is_candidate_eligible": False,
                    "confidence": 0.92,
                    "canonical_url": raw_url.split("?")[0] if raw_url else None,
                    "reason": "LinkedIn company page",
                }

            # Job posting: /jobs/view/ or /jobs/collections/
            if "/jobs/view" in url_lower or "/jobs/collections" in url_lower or "/jobs/" in url_lower:
                return {
                    "page_type": PAGE_TYPE_JOB_PAGE,
                    "platform": resolved_plat,
                    "is_candidate_eligible": False,
                    "confidence": 0.95,
                    "canonical_url": raw_url.split("?")[0] if raw_url else None,
                    "reason": "LinkedIn job posting view",
                }

            # Messaging
            if "/messaging" in url_lower or "messaging" in title_lower:
                return {
                    "page_type": PAGE_TYPE_MESSAGING,
                    "platform": resolved_plat,
                    "is_candidate_eligible": False,
                    "confidence": 0.95,
                    "canonical_url": None,
                    "reason": "LinkedIn direct messaging",
                }

            # Feed
            if "/feed" in url_lower or (title_lower.startswith("feed |") or "feed | linkedin" in title_lower):
                return {
                    "page_type": PAGE_TYPE_FEED,
                    "platform": resolved_plat,
                    "is_candidate_eligible": False,
                    "confidence": 0.95,
                    "canonical_url": None,
                    "reason": "LinkedIn home feed",
                }

            # Title fallback for LinkedIn Profile: "Name | LinkedIn"
            # Explicitly guard against "(54) Notifications | LinkedIn", "Feed | LinkedIn", etc.
            non_profile_keywords = [
                "feed", "jobs", "job", "search", "notifications", "messaging",
                "network", "home", "learning", "my network", "post", "invitations"
            ]
            m_title = re.match(r"^(?:\(\d+\+?\)\s*)?([^|•·\n]+?)\s*[|•·]\s*LinkedIn", raw_title, flags=re.IGNORECASE)
            if m_title:
                cand_segment = m_title.group(1).strip().lower()
                if not any(k in cand_segment for k in non_profile_keywords) and len(cand_segment) >= 3:
                    return {
                        "page_type": PAGE_TYPE_PERSON_PROFILE,
                        "platform": resolved_plat,
                        "is_candidate_eligible": True,
                        "confidence": 0.88,
                        "canonical_url": raw_url if raw_url else None,
                        "reason": f"LinkedIn profile window title pattern '{m_title.group(1).strip()}'",
                    }

            # Generic LinkedIn page
            if url_lower == "https://www.linkedin.com" or url_lower == "https://www.linkedin.com/" or title_lower == "linkedin":
                return {
                    "page_type": PAGE_TYPE_HOME,
                    "platform": resolved_plat,
                    "is_candidate_eligible": False,
                    "confidence": 0.90,
                    "canonical_url": None,
                    "reason": "LinkedIn landing / home",
                }

        # 2. ZoomInfo Classification
        if "zoominfo.com" in url_lower or "zi-lite" in url_lower or "zoominfo" in title_lower or plat == "ZOOMINFO":
            resolved_plat = "ZOOMINFO"
            if any(k in url_lower for k in ["/profile/person/", "/contact-profile", "/profile/"]):
                return {
                    "page_type": PAGE_TYPE_PERSON_PROFILE,
                    "platform": resolved_plat,
                    "is_candidate_eligible": True,
                    "confidence": 0.95,
                    "canonical_url": raw_url.split("?")[0] if raw_url else None,
                    "reason": "ZoomInfo person profile URL",
                }
            if any(k in url_lower for k in ["/search", "/contacts", "/advanced-search"]):
                return {
                    "page_type": PAGE_TYPE_PEOPLE_SEARCH,
                    "platform": resolved_plat,
                    "is_candidate_eligible": True,
                    "confidence": 0.92,
                    "canonical_url": raw_url.split("?")[0] if raw_url else None,
                    "reason": "ZoomInfo contacts search listing",
                }
            if any(k in url_lower for k in ["/companies", "/company/"]):
                return {
                    "page_type": PAGE_TYPE_COMPANY_PAGE,
                    "platform": resolved_plat,
                    "is_candidate_eligible": False,
                    "confidence": 0.90,
                    "canonical_url": raw_url.split("?")[0] if raw_url else None,
                    "reason": "ZoomInfo company profile",
                }
            if "zoominfo" in title_lower and not any(k in title_lower for k in ["login", "pricing", "search", "navigation"]):
                return {
                    "page_type": PAGE_TYPE_PERSON_PROFILE,
                    "platform": resolved_plat,
                    "is_candidate_eligible": True,
                    "confidence": 0.85,
                    "canonical_url": raw_url if raw_url else None,
                    "reason": "ZoomInfo person profile title",
                }

        # 3. Apollo.io Classification
        if "apollo.io" in url_lower or "apollo" in title_lower or plat == "APOLLO":
            resolved_plat = "APOLLO"
            if any(k in url_lower for k in ["/people/", "/contacts/"]):
                return {
                    "page_type": PAGE_TYPE_PERSON_PROFILE,
                    "platform": resolved_plat,
                    "is_candidate_eligible": True,
                    "confidence": 0.95,
                    "canonical_url": raw_url.split("?")[0] if raw_url else None,
                    "reason": "Apollo contact profile URL",
                }
            if any(k in url_lower for k in ["/search", "/sequences", "/tasks"]):
                return {
                    "page_type": PAGE_TYPE_PEOPLE_SEARCH,
                    "platform": resolved_plat,
                    "is_candidate_eligible": True,
                    "confidence": 0.90,
                    "canonical_url": raw_url.split("?")[0] if raw_url else None,
                    "reason": "Apollo search / leads view",
                }

        # 4. GitHub Profile Classification
        if "github.com" in url_lower or plat == "GITHUB":
            resolved_plat = "GITHUB"
            path = urllib.parse.urlparse(raw_url).path.strip("/")
            parts = [p for p in path.split("/") if p]
            reserved_gh = {"features", "pricing", "explore", "topics", "trending", "collections", "login", "signup", "settings", "notifications", "search"}
            if len(parts) == 1 and parts[0] not in reserved_gh:
                return {
                    "page_type": PAGE_TYPE_PERSON_PROFILE,
                    "platform": resolved_plat,
                    "is_candidate_eligible": True,
                    "confidence": 0.92,
                    "canonical_url": f"https://github.com/{parts[0]}",
                    "reason": "GitHub user profile page",
                }

        # 5. ATS & Job Boards
        ats_domains = ["greenhouse.io", "lever.co", "ashbyhq.com", "myworkday.com", "workday.com", "icims.com", "smartrecruiters.com", "indeed.com", "simplyhired.com", "dice.com"]
        if any(d in url_lower for d in ats_domains) or "ATS_" in plat:
            if any(k in url_lower for k in ["/candidate", "/application", "/applicant"]):
                return {
                    "page_type": PAGE_TYPE_PERSON_PROFILE,
                    "platform": "ATS",
                    "is_candidate_eligible": True,
                    "confidence": 0.88,
                    "canonical_url": raw_url.split("?")[0] if raw_url else None,
                    "reason": "ATS applicant view",
                }
            return {
                "page_type": PAGE_TYPE_JOB_PAGE,
                "platform": "ATS",
                "is_candidate_eligible": False,
                "confidence": 0.90,
                "canonical_url": raw_url.split("?")[0] if raw_url else None,
                "reason": "ATS job posting",
            }

        # 6. Messaging & Chat Tools (Slack, Teams, WhatsApp, Gmail, Outlook)
        chat_domains = ["chat.google.com", "teams.microsoft.com", "teams.live.com", "app.slack.com", "slack.com", "web.whatsapp.com", "web.telegram.org", "mail.google.com", "outlook.live.com", "outlook.office.com"]
        if any(cd in url_lower for cd in chat_domains) or any(w in title_lower for w in ["google chat", "microsoft teams", "slack |", "whatsapp", "telegram", "outlook", "gmail"]):
            return {
                "page_type": PAGE_TYPE_MESSAGING,
                "platform": "MESSAGING",
                "is_candidate_eligible": False,
                "confidence": 0.95,
                "canonical_url": None,
                "reason": "Chat / Email messaging application",
            }

        # Default Catch-all: UNKNOWN
        return {
            "page_type": PAGE_TYPE_UNKNOWN,
            "platform": plat or "GENERIC_WEB",
            "is_candidate_eligible": False,
            "confidence": 0.50,
            "canonical_url": None,
            "reason": "Unsupported or unrecognized page context",
        }

    @staticmethod
    def _clean_linkedin_profile_url(raw_url: str) -> str:
        """Extracts canonical profile URL e.g. https://www.linkedin.com/in/username/"""
        if not raw_url:
            return ""
        parsed = urllib.parse.urlparse(raw_url)
        match = re.search(r"^/in/([a-zA-Z0-9_\-\u00C0-\u017F%]+)", parsed.path)
        if match:
            slug = match.group(1).rstrip("/")
            return f"https://www.linkedin.com/in/{slug}"
        return raw_url.split("?")[0].rstrip("/")
