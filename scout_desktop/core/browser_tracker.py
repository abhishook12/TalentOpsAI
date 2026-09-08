"""
core/browser_tracker.py — Browser Context & URL Detection

Inspects foreground browser windows (Chrome, Edge, Firefox) using
Windows UI Automation and Window Title heuristics to extract
active URL, domain, and page context without requiring browser extension popups.
"""

import re
import urllib.parse
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("scout.browser_tracker")

# Domain classification heuristics
KNOWN_PLATFORMS = {
    "linkedin.com": "LINKEDIN",
    "indeed.com": "INDEED",
    "simplyhired.com": "SIMPLYHIRED",
    "glassdoor.com": "GLASSDOOR",
    "ziprecruiter.com": "ZIPRECRUITER",
    "greenhouse.io": "ATS_GREENHOUSE",
    "lever.co": "ATS_LEVER",
    "workday.com": "ATS_WORKDAY",
    "icims.com": "ATS_ICIMS",
    "smartrecruiters.com": "ATS_SMARTRECRUITERS",
}


class BrowserTracker:
    def __init__(self):
        self._uia = None
        self._cached_url = None
        self._last_hwnd = None
        self._init_uia()

    def _init_uia(self):
        """Initializes UIAutomation client via comtypes if available."""
        try:
            import comtypes.client
            comtypes.client.GetModule("UIAutomationCore.dll")
            from comtypes.gen.UIAutomationClient import CUIAutomation, IUIAutomation
            self._uia = comtypes.client.CreateObject(CUIAutomation, interface=IUIAutomation)
        except Exception as e:
            logger.debug("UIA COM initialization deferred: %s", e)
            self._uia = None

    def get_url_from_window_uia(self, hwnd: int) -> Optional[str]:
        """Attempts to read URL from address bar edit control via UIA with multi-tier targeting."""
        if not self._uia or not hwnd:
            return None
        try:
            from comtypes.gen.UIAutomationClient import (
                TreeScope_Descendants,
                UIA_EditControlTypeId,
                UIA_ValuePatternId,
                IUIAutomationValuePattern,
            )
            el = self._uia.ElementFromHandle(hwnd)
            if not el:
                return None

            # Tier 1: Target by known AutomationId or Name first
            # Chrome/Edge: AutomationId='addressEditBox' or Name='Address and search bar'
            # Firefox: AutomationId='urlbar-input'
            known_auto_ids = ["addressEditBox", "view_1020", "urlbar-input", "AddressBar"]
            for auto_id in known_auto_ids:
                try:
                    cond_id = self._uia.CreatePropertyCondition(30011, auto_id) # 30011 = UIA_AutomationIdPropertyId
                    target = el.FindFirst(TreeScope_Descendants, cond_id)
                    if target:
                        pat = target.GetCurrentPattern(UIA_ValuePatternId)
                        if pat:
                            val_pat = pat.QueryInterface(IUIAutomationValuePattern)
                            val = val_pat.CurrentValue
                            if val and ("." in val or "://" in val):
                                if not val.startswith("http://") and not val.startswith("https://"):
                                    val = f"https://{val}"
                                return val
                except Exception:
                    pass

            # Tier 2: Search Edit controls and match candidate URL patterns
            cond = self._uia.CreatePropertyCondition(30003, UIA_EditControlTypeId)
            edits = el.FindAll(TreeScope_Descendants, cond)
            if edits:
                for i in range(min(edits.Length, 10)):
                    edit = edits.GetElement(i)
                    pat = edit.GetCurrentPattern(UIA_ValuePatternId)
                    if pat:
                        val_pat = pat.QueryInterface(IUIAutomationValuePattern)
                        val = val_pat.CurrentValue
                        if val and ("." in val or "://" in val) and not val.startswith(" "):
                            # Heuristic: address bar contains domain or path
                            if any(d in val.lower() for d in [".com", ".org", ".io", ".net", ".co", "http", "www."]):
                                if not val.startswith("http://") and not val.startswith("https://"):
                                    val = f"https://{val}"
                                return val
        except Exception as e:
            logger.debug("UIA address bar read failed: %s", e)
        return None

    def classify_page_type(self, url: Optional[str], title: str, platform: str) -> str:
        """
        Classifies the active webpage into structural recruiter workflow categories:
        - PROFILE: Individual candidate profile page
        - COMPANY_PEOPLE: Company directory or employees list
        - SEARCH_RESULTS: Multi-candidate search listing
        - JOB_POSTING: Job description / requisition
        - FEED: Timeline or social feed
        - OTHER: Catch-all
        """
        url_lower = (url or "").lower()
        title_lower = title.lower()

        # LinkedIn classification
        if platform == "LINKEDIN" or "linkedin.com" in url_lower:
            if "/in/" in url_lower:
                return "PROFILE"
            if "/company/" in url_lower and ("/people" in url_lower or "/about" in url_lower):
                return "COMPANY_PEOPLE"
            if "/search/results/people" in url_lower or "people" in title_lower and "search" in title_lower:
                return "SEARCH_RESULTS"
            if "/jobs/view" in url_lower or "/jobs/collections" in url_lower:
                return "JOB_POSTING"
            if "/feed" in url_lower or "feed" in title_lower:
                return "FEED"
            # Title-based profile detection: "Name | LinkedIn"
            if " | linkedin" in title_lower and not any(k in title_lower for k in ["feed", "jobs", "search", "notifications"]):
                return "PROFILE"

        # General ATS / Job boards
        if platform in ["ATS_GREENHOUSE", "ATS_LEVER", "ATS_WORKDAY", "ATS_ICIMS", "ATS_SMARTRECRUITERS"]:
            if any(k in url_lower for k in ["/jobs/", "/careers/", "/requisition/", "/job/"]):
                return "JOB_POSTING"
            return "JOB_POSTING"

        if platform in ["INDEED", "SIMPLYHIRED", "ZIPRECRUITER", "GLASSDOOR"]:
            if any(k in url_lower for k in ["/viewjob", "/job/", "/rc/clk"]):
                return "JOB_POSTING"
            if any(k in url_lower for k in ["/jobs", "/search", "/q-"]):
                return "SEARCH_RESULTS"
            return "JOB_POSTING"

        # GitHub Profile
        if "github.com" in url_lower:
            parts = [p for p in urllib.parse.urlparse(url_lower).path.split("/") if p]
            if len(parts) == 1 and parts[0] not in ["features", "pricing", "explore", "topics", "trending", "collections"]:
                return "PROFILE"

        # Title-based general fallback
        if any(w in title_lower for w in ["search results", "results for", "search |"]):
            return "SEARCH_RESULTS"
        if any(w in title_lower for w in ["job opening", "job detail", "job description", "career opportunities"]):
            return "JOB_POSTING"

        return "OTHER"

    def infer_context_from_title(self, window_title: str) -> Dict[str, Any]:
        """
        Extracts candidate name, platform, and probable URL domain from window title.
        Examples:
          'Tony Vitulli | LinkedIn - Google Chrome' -> Person: Tony Vitulli, Platform: LinkedIn
          'Top 3646 Jobs in United States | SimplyHired - Google Chrome' -> Platform: SimplyHired
          'Director of Talent - Cyberdyne Systems | Indeed.com' -> Platform: Indeed
        """
        title = window_title.strip()
        # Strip browser suffixes
        title_clean = re.sub(
            r"\s*[-—|]\s*(?:Google Chrome|Microsoft Edge|Mozilla Firefox|Brave|Opera)\s*$",
            "",
            title,
            flags=re.IGNORECASE,
        ).strip()

        platform = "GENERIC_WEB"
        probable_domain = ""
        candidate_name = None

        # Check known platforms
        title_lower = title_clean.lower()
        if "linkedin" in title_lower:
            platform = "LINKEDIN"
            probable_domain = "linkedin.com"
            # LinkedIn profile title: 'Name | LinkedIn' or '(14) Name | LinkedIn'
            m = re.match(r"^(?:\(\d+\)\s*)?([^|•·\n]+?)\s*[|•·]\s*LinkedIn", title_clean, flags=re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                if not any(w in cand.lower() for w in ["search", "feed", "notifications", "jobs", "messaging"]):
                    candidate_name = cand
        elif "simplyhired" in title_lower:
            platform = "SIMPLYHIRED"
            probable_domain = "simplyhired.com"
        elif "indeed" in title_lower:
            platform = "INDEED"
            probable_domain = "indeed.com"
        elif "glassdoor" in title_lower:
            platform = "GLASSDOOR"
            probable_domain = "glassdoor.com"
        elif "ziprecruiter" in title_lower:
            platform = "ZIPRECRUITER"
            probable_domain = "ziprecruiter.com"
        elif "greenhouse" in title_lower:
            platform = "ATS_GREENHOUSE"
            probable_domain = "greenhouse.io"
        elif "lever" in title_lower:
            platform = "ATS_LEVER"
            probable_domain = "lever.co"
        elif "workday" in title_lower:
            platform = "ATS_WORKDAY"
            probable_domain = "myworkdayjobs.com"

        return {
            "platform": platform,
            "clean_title": title_clean,
            "probable_domain": probable_domain,
            "candidate_name": candidate_name,
        }

    def resolve_browser_context(self, hwnd: int, window_title: str) -> Dict[str, Any]:
        """
        Resolves the comprehensive browser context using UIA + Title heuristics and page type classification.
        """
        inferred = self.infer_context_from_title(window_title)
        
        # Try reading UIA address bar
        active_url = self.get_url_from_window_uia(hwnd)
        domain = inferred["probable_domain"]

        if active_url:
            try:
                parsed = urllib.parse.urlparse(active_url)
                domain = parsed.hostname or domain
                for kp, plat in KNOWN_PLATFORMS.items():
                    if kp in domain.lower():
                        inferred["platform"] = plat
                        break
            except Exception:
                pass

        page_type = self.classify_page_type(active_url, inferred["clean_title"], inferred["platform"])

        return {
            "url": active_url,
            "domain": domain,
            "platform": inferred["platform"],
            "page_type": page_type,
            "title": inferred["clean_title"],
            "candidate_name": inferred["candidate_name"],
        }
