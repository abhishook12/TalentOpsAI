"""
company_domain_engine.py — Enterprise Company Normalization & Corporate Domain Resolution.

Features:
1. Legal suffix normalization (Inc, LLC, Corp, Ltd, GmbH, SA, etc.)
2. Corporate Domain vs Public Webmail Detection
3. Email Pattern Synthesis ({first}.{last}@{domain}, {first}{l}@{domain})
4. Company Master & Alias Registry Integration
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

LEGAL_END_SUFFIX = re.compile(
    r"[\s,\.\-_]+(?:inc(?:\.|\b)|llc(?:\.|\b)|corp(?:\.|\b)|corporation|ltd(?:\.|\b)|limited|gmbh|s\.?a\.?|pvt(?:\.|\b)|co(?:\.|\b))[\s,\.\-_]*$",
    re.IGNORECASE,
)

PUBLIC_MAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "yahoo.com", "ymail.com", "hotmail.com",
    "outlook.com", "live.com", "msn.com", "icloud.com", "me.com", "aol.com",
    "protonmail.com", "proton.me", "zoho.com", "mail.com", "gmx.com",
    "comcast.net", "sbcglobal.net", "verizon.net", "att.net",
}


class CompanyDomainEngine:
    """
    Standardizes enterprise entities, resolves their primary domains,
    and classifies email addresses into corporate vs personal.
    """

    @classmethod
    def clean_company_name(cls, raw_name: Optional[str]) -> str:
        """
        Normalizes company name by stripping legal designations and punctuation from the end.
        'Microsoft Corporation, Inc.' -> 'Microsoft'
        'Amazon Web Services Ltd.' -> 'Amazon Web Services'
        """
        if not raw_name:
            return ""
        name = str(raw_name).strip()
        # Remove parentheses content e.g. "Datadog (US)"
        name = re.sub(r"\(.*?\)", "", name).strip()
        # Repeatedly strip trailing legal suffixes from the end of the string
        prev = None
        while prev != name:
            prev = name
            name = LEGAL_END_SUFFIX.sub("", name).strip()
        # Strip trailing commas, periods, hyphens
        name = re.sub(r"[\s,\.\-_]+$", "", name).strip()
        # Clean extra internal whitespace
        name = re.sub(r"\s+", " ", name)
        return name or str(raw_name).strip()

    @classmethod
    def extract_domain_from_email(cls, email: Optional[str]) -> Optional[str]:
        """Extracts and normalizes the lowercase domain from an email address."""
        if not email or "@" not in email:
            return None
        parts = email.strip().split("@")
        if len(parts) == 2 and "." in parts[1]:
            return parts[1].lower().strip()
        return None

    @classmethod
    def is_corporate_domain(cls, domain: Optional[str]) -> bool:
        """Determines whether a domain belongs to a business rather than a public webmail."""
        if not domain:
            return False
        clean_domain = domain.lower().strip()
        return clean_domain not in PUBLIC_MAIL_DOMAINS and "." in clean_domain

    @classmethod
    def derive_candidate_email(
        cls,
        first_name: str,
        last_name: str,
        domain: str,
        pattern: str = "{first}.{last}",
    ) -> Optional[str]:
        """
        Synthesizes a probable corporate email using standard enterprise formulas.
        Supported patterns:
        - '{first}.{last}' -> john.doe@company.com
        - '{first}{l}'     -> johnd@company.com
        - '{f}{last}'      -> jdoe@company.com
        - '{first}'        -> john@company.com
        - '{last}'         -> doe@company.com
        """
        if not first_name or not last_name or not domain or not cls.is_corporate_domain(domain):
            return None

        fn = re.sub(r"[^a-zA-Z0-9]", "", first_name.lower().strip())
        ln = re.sub(r"[^a-zA-Z0-9]", "", last_name.lower().strip())

        if not fn or not ln:
            return None

        f = fn[0]
        l = ln[0]

        replacements = {
            "{first}": fn,
            "{last}": ln,
            "{f}": f,
            "{l}": l,
        }

        local_part = pattern
        for placeholder, val in replacements.items():
            local_part = local_part.replace(placeholder, val)

        return f"{local_part}@{domain.lower().strip()}"
