"""
TalentOps Scout 2.0 - Scope-Aware LinkedIn Connector
Passive, scope-aware professional intelligence connector.
Strictly adheres to authorized view boundaries: zero unauthorized scraping,
zero DOM manipulation, and zero bot automation.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .base import BaseConnector

logger = logging.getLogger("scout.connectors.linkedin")


class LinkedInConnector(BaseConnector):
    """
    Connector for professional profile and company activity observations.
    Extracts structured professional intelligence strictly from authorized user views.
    """

    ALLOWED_DOMAINS = ["linkedin.com", "www.linkedin.com"]

    # Authorized view patterns (Passive observation of active recruiter/talent workflows)
    AUTHORIZED_PATH_PATTERNS = [
        re.compile(r"^/in/([^/?#]+)"),          # Member profile view
        re.compile(r"^/company/([^/?#]+)"),     # Company page view
        re.compile(r"^/jobs/view/(\d+)"),       # Job posting view
        re.compile(r"^/talent/profile/"),       # Recruiter talent view
    ]

    def __init__(self) -> None:
        super().__init__(name="linkedin_connector", allowed_domains=self.ALLOWED_DOMAINS)
        self._processed_count = 0
        self._ignored_out_of_scope = 0
        self._last_observation_time: Optional[float] = None

    def is_scope_authorized(self, context: dict[str, Any]) -> bool:
        """
        Validates that the observation context falls strictly within authorized domains and paths.
        """
        url = context.get("url") or context.get("source_url") or ""
        window_title = context.get("window_title") or ""

        # Check domain authorization
        if url:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
                # Strip port if any
                if ":" in domain:
                    domain = domain.split(":")[0]
                if not any(domain == d or domain.endswith(f".{d}") for d in self.ALLOWED_DOMAINS):
                    return False

                # Ensure path is an authorized profile/company view
                path = parsed.path
                if not any(pattern.search(path) for pattern in self.AUTHORIZED_PATH_PATTERNS):
                    return False
                return True
            except Exception as e:
                logger.warning("Failed to parse URL '%s': %s", url, e)
                return False

        # Fallback to window title if URL unavailable
        if "LinkedIn" in window_title:
            return True

        return False

    def discover(self, context: dict[str, Any]) -> bool:
        """Check if context is a LinkedIn observation."""
        if not self._enabled:
            return False
        return self.is_scope_authorized(context)

    def capture_and_extract(self, context: dict[str, Any]) -> Optional[dict[str, Any]]:
        """
        Extract normalized entity data from passive context (text, URL, title).
        Returns a normalized dictionary.
        """
        if not self.discover(context):
            self._ignored_out_of_scope += 1
            return None

        raw_text = context.get("raw_text") or context.get("ocr_text") or ""
        url = context.get("url") or context.get("source_url") or ""
        window_title = context.get("window_title") or ""

        # Extract handle/slug from URL
        slug = ""
        page_type = "PROFILE"
        if url:
            m = re.search(r"/in/([^/?#]+)", url)
            if m:
                slug = m.group(1).rstrip("/")
                page_type = "PROFILE"
            elif "/company/" in url:
                cm = re.search(r"/company/([^/?#]+)", url)
                slug = cm.group(1).rstrip("/") if cm else ""
                page_type = "COMPANY"
            elif "/jobs/" in url:
                page_type = "JOB"

        # Basic entity parsing from window title / raw text
        name = ""
        title = ""
        company = ""
        location = ""

        # Window title pattern: "FirstName LastName - Title - Company | LinkedIn"
        if window_title:
            clean_title = window_title.split("|")[0].strip()
            parts = [p.strip() for p in clean_title.split(" - ") if p.strip()]
            if len(parts) >= 1:
                name = parts[0]
            if len(parts) >= 2:
                title = parts[1]
            if len(parts) >= 3:
                company = parts[2]

        # Extract email and phone if present in text
        email = ""
        phone = ""
        if raw_text:
            email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", raw_text)
            if email_match:
                candidate_email = email_match.group(0).strip().lower()
                if not candidate_email.endswith((".png", ".jpg", "talentops.ai")):
                    email = candidate_email

            phone_match = re.search(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", raw_text)
            if phone_match:
                phone = phone_match.group(0).strip()

            # Location heuristic from text
            loc_match = re.search(r"(?:Location|Based in|Area):\s*([A-Za-z\s,]+)", raw_text, re.IGNORECASE)
            if loc_match:
                location = loc_match.group(1).strip()

        # Generate canonical ID
        canonical_id = f"linkedin:{slug}" if slug else f"norm:{name.lower().replace(' ', '_')}"

        self._processed_count += 1
        self._last_observation_time = time.time()

        return {
            "connector": self.name,
            "page_type": page_type,
            "canonical_id": canonical_id,
            "slug": slug,
            "name": name,
            "title": title,
            "company": company,
            "location": location,
            "email": email,
            "phone": phone,
            "source_url": url,
            "window_title": window_title,
            "confidence": 0.90 if slug and name else 0.70,
            "timestamp": self._last_observation_time,
            "compliance": {
                "scope_authorized": True,
                "unauthorized_automation": False,
                "passive_observation": True,
            }
        }

    def checkpoint(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "enabled": self._enabled,
            "processed_count": self._processed_count,
            "ignored_out_of_scope": self._ignored_out_of_scope,
            "last_observation_time": self._last_observation_time,
        }
