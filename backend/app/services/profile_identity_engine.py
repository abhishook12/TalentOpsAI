"""
profile_identity_engine.py — Cross-Platform Profile Identity & Canonical Slug Engine.

Features:
1. Canonical Profile URL Normalization (LinkedIn, GitHub, X/Twitter)
2. Slug Extraction (strips URL tracking, locale codes, trailing slashes)
3. Vanity Handle vs Numeric URN Disambiguation
4. Cross-Platform Handle Matching
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse, parse_qs


class ProfileIdentityEngine:
    """
    Standardizes profile links across platforms into unique canonical identity keys.
    Prevents duplicate entity creation from localized or tracked URLs.
    """

    @classmethod
    def normalize_profile_url(cls, raw_url: Optional[str]) -> Dict[str, Any]:
        """
        Parses, strips tracking parameters, and canonicalizes a social profile URL.
        """
        result: Dict[str, Any] = {
            "raw": raw_url or "",
            "canonical_url": None,
            "platform": "UNKNOWN",
            "slug": None,
            "is_vanity": True,
            "is_valid": False,
        }

        if not raw_url or not str(raw_url).strip():
            return result

        url = str(raw_url).strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"

        try:
            parsed = urlparse(url)
            hostname = parsed.hostname.lower() if parsed.hostname else ""
            path = parsed.path.strip("/")
        except Exception:
            return result

        # ── 1. LinkedIn ──────────────────────────────────────────────────────
        if "linkedin.com" in hostname:
            result["platform"] = "LINKEDIN"
            # Normalize paths: in/john-doe, pub/john-doe, es.linkedin.com/in/john-doe
            match = re.search(r"(?:in|pub)/([a-zA-Z0-9_\-%]+)", path, re.IGNORECASE)
            if match:
                slug = match.group(1).lower().rstrip("/")
                # Check if it's a numeric/internal URN like ACoAAB...
                is_vanity = not bool(slug.startswith("acoaab") or slug.startswith("acobaa"))
                result.update({
                    "canonical_url": f"https://www.linkedin.com/in/{slug}",
                    "slug": slug,
                    "is_vanity": is_vanity,
                    "is_valid": True,
                })
                return result

            # Company page
            comp_match = re.search(r"company/([a-zA-Z0-9_\-%]+)", path, re.IGNORECASE)
            if comp_match:
                slug = comp_match.group(1).lower().rstrip("/")
                result.update({
                    "platform": "LINKEDIN_COMPANY",
                    "canonical_url": f"https://www.linkedin.com/company/{slug}",
                    "slug": slug,
                    "is_vanity": True,
                    "is_valid": True,
                })
                return result

        # ── 2. GitHub ────────────────────────────────────────────────────────
        elif "github.com" in hostname:
            result["platform"] = "GITHUB"
            parts = [p for p in path.split("/") if p]
            if parts:
                slug = parts[0].lower()
                result.update({
                    "canonical_url": f"https://github.com/{slug}",
                    "slug": slug,
                    "is_vanity": True,
                    "is_valid": True,
                })
                return result

        # ── 3. X / Twitter ───────────────────────────────────────────────────
        elif "twitter.com" in hostname or "x.com" in hostname:
            result["platform"] = "TWITTER"
            parts = [p for p in path.split("/") if p]
            if parts:
                slug = parts[0].lower().lstrip("@")
                result.update({
                    "canonical_url": f"https://x.com/{slug}",
                    "slug": slug,
                    "is_vanity": True,
                    "is_valid": True,
                })
                return result

        # ── 4. Fallback Generic Web URL ──────────────────────────────────────
        else:
            result["platform"] = "GENERIC_WEB"
            canonical = f"https://{hostname}/{path}".rstrip("/")
            result.update({
                "canonical_url": canonical,
                "slug": path or hostname,
                "is_vanity": True,
                "is_valid": True,
            })
            return result

        return result

    @classmethod
    def are_slugs_compatible(cls, slug_a: Optional[str], slug_b: Optional[str]) -> bool:
        """
        Determines whether two profile slugs likely belong to the same person.
        e.g., 'john-doe-1234' vs 'john-doe', or 'johndoe' vs 'john-doe'.
        """
        if not slug_a or not slug_b:
            return False
        a = re.sub(r"[\W_]+", "", slug_a.lower())
        b = re.sub(r"[\W_]+", "", slug_b.lower())
        if a == b:
            return True
        # Strip trailing numbers
        a_no_num = re.sub(r"\d+$", "", a)
        b_no_num = re.sub(r"\d+$", "", b)
        if len(a_no_num) >= 4 and a_no_num == b_no_num:
            return True
        return False
