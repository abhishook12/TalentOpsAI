"""
TalentOps AI - Company & Domain Resolution Engine
Maps corporate aliases to canonical company masters, discovers and corroborates
corporate domains, and detects temporal PERSON_COMPANY_MISMATCH anomalies.
"""

from __future__ import annotations

import json
import logging
import re
import socket
import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from ..models.data_quality_models import (
    CompanyMaster,
    CompanyAlias,
    DataQualityIssue,
    PersonIdentity,
    PersonContactHistory,
)

logger = logging.getLogger("talentops.company_resolver")

COMMON_COMPANY_SUFFIXES = [
    r"\binc\.?\b", r"\bcorp\.?\b", r"\bcorporation\b", r"\bllc\.?\b",
    r"\bltd\.?\b", r"\bco\.?\b", r"\btechnologies\b", r"\btech\b",
    r"\bsolutions\b", r"\bgroup\b", r"\bholdings\b", r"\bconsulting\b",
]


class CompanyResolver:
    """
    Company and Domain Resolution coordinator.
    Ensures corporate names normalize to canonical entities and corroborates domains.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def resolve_company(
        self,
        raw_company_name: str,
        candidate_domain: Optional[str] = None,
        domain: Optional[str] = None,
        source: str = "scout_edge",
    ) -> CompanyMaster:
        """
        Finds or creates canonical CompanyMaster for a given raw company string.
        Resolves via exact name match, alias lookup, or stem normalization.
        """
        candidate_domain = candidate_domain or domain
        clean_name = (raw_company_name or "").strip()
        if not clean_name:
            clean_name = "Independent / Unknown Enterprise"

        # 1. Direct match on canonical name
        comp = self.db.query(CompanyMaster).filter(
            CompanyMaster.canonical_name.ilike(clean_name)
        ).first()
        if comp:
            return comp

        # 2. Match through CompanyAlias
        alias = self.db.query(CompanyAlias).filter(
            CompanyAlias.alias_name.ilike(clean_name)
        ).first()
        if alias and alias.company:
            return alias.company

        # 3. Stem match: strip suffixes (e.g. IBM Corp -> IBM)
        stem = self._clean_company_stem(clean_name)
        if stem and stem != clean_name:
            stem_comp = self.db.query(CompanyMaster).filter(
                CompanyMaster.canonical_name.ilike(stem)
            ).first()
            if stem_comp:
                # Add current variant as new alias
                new_alias = CompanyAlias(
                    company_master_id=stem_comp.id,
                    alias_name=clean_name,
                    source=source,
                    confidence=0.92,
                )
                self.db.add(new_alias)
                self.db.commit()
                return stem_comp

        # 4. Create new canonical CompanyMaster
        canonical_id = f"CO-{uuid.uuid4().hex[:8].upper()}"
        primary_domain = candidate_domain or self._infer_domain(clean_name)
        dns_ok, mx_ok = self._verify_domain_connectivity(primary_domain)

        canonical_name = stem if stem else clean_name
        new_comp = CompanyMaster(
            canonical_id=canonical_id,
            canonical_name=canonical_name,
            primary_domain=primary_domain,
            alternate_domains=json.dumps([candidate_domain] if candidate_domain and candidate_domain != primary_domain else []),
            email_domains=json.dumps([primary_domain] if primary_domain else []),
            domain_confidence=0.95 if dns_ok and mx_ok else (0.75 if dns_ok else 0.50),
            dns_verified=dns_ok,
            mx_verified=mx_ok,
        )
        self.db.add(new_comp)
        self.db.commit()
        self.db.refresh(new_comp)

        # Add initial aliases
        self.db.add(CompanyAlias(
            company_master_id=new_comp.id,
            alias_name=clean_name,
            source=source,
            confidence=1.0,
        ))
        if canonical_name != clean_name:
            self.db.add(CompanyAlias(
                company_master_id=new_comp.id,
                alias_name=canonical_name,
                source=source,
                confidence=1.0,
            ))
        self.db.commit()
        return new_comp

    def add_alias(
        self,
        company_id: int,
        alias_name: str,
        confidence: float = 0.95,
        source: str = "manual",
    ) -> CompanyAlias:
        """Associates an alternative company name or spelling with a master company."""
        alias = CompanyAlias(
            company_master_id=company_id,
            alias_name=alias_name.strip(),
            source=source,
            confidence=confidence,
        )
        self.db.add(alias)
        self.db.commit()
        self.db.refresh(alias)
        return alias

    def check_person_company_alignment(
        self,
        person_id: int,
        current_company_name: str,
        email: Optional[str] = None,
        owner_user_id: int = 1,
    ) -> bool:
        """Convenience method checking alignment by person ID and email."""
        person = self.db.query(PersonIdentity).filter(PersonIdentity.id == person_id).first()
        if not person:
            return False
        if email:
            person.primary_email = email
        issue = self.detect_person_company_mismatch(person, current_company_name, owner_user_id)
        return issue is not None

    def detect_person_company_mismatch(
        self,
        person: PersonIdentity,
        new_company: str,
        owner_user_id: int,
    ) -> Optional[DataQualityIssue]:
        """
        Detects if an observed job change invalidates their current corporate email.
        e.g. John Smith moves from 'Microsoft' to 'Google', but primary_email is 'john@microsoft.com'.
        """
        old_company = person.current_company or ""
        email = person.primary_email or ""

        if not old_company or not new_company or not email:
            return None

        if old_company.strip().lower() == new_company.strip().lower():
            return None  # Same company, no mismatch

        # Check if email is a free provider (personal email unaffected by company change)
        free_domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"]
        if any(f"@{d}" in email.lower() for d in free_domains):
            return None

        # Check if email domain stems from old company
        email_domain = email.split("@")[-1].lower() if "@" in email else ""
        old_stem = re.sub(r"[^a-z0-9]", "", old_company.lower())

        if old_stem in email_domain or email_domain.split(".")[0] in old_stem:
            # High severity mismatch!
            description = (
                f"Candidate '{person.canonical_name}' transitioned from '{old_company}' to '{new_company}', "
                f"but retain corporate email '{email}' tied to their former employer."
            )
            issue = DataQualityIssue(
                issue_type="PERSON_COMPANY_MISMATCH",
                severity="HIGH",
                entity_type="PERSON",
                entity_id=person.id,
                description=description,
                remediation_action="Inactivate old corporate email; seek new employer email or personal contact.",
                owner_user_id=owner_user_id,
            )
            self.db.add(issue)

            # Demote email status to stale/historical
            person.email_status = "RISKY"
            self.db.add(PersonContactHistory(
                person_identity_id=person.id,
                contact_type="email",
                contact_value=email,
                status="stale",
                reason="Flagged by PERSON_COMPANY_MISMATCH detection engine",
            ))
            self.db.commit()
            return issue

        return None

    @classmethod
    def _clean_company_stem(cls, name: str) -> str:
        """Removes legal suffixes to derive bare corporate stem."""
        res = name.strip()
        for suffix_pat in COMMON_COMPANY_SUFFIXES:
            res = re.sub(suffix_pat, "", res, flags=re.IGNORECASE).strip()
        res = re.sub(r"[,\.-]+$", "", res).strip()
        return res

    @classmethod
    def _infer_domain(cls, company_name: str) -> Optional[str]:
        """Infers standard commercial domain from company name."""
        stem = cls._clean_company_stem(company_name)
        slug = re.sub(r"[^a-z0-9]", "", stem.lower())
        if slug and len(slug) >= 2:
            return f"{slug}.com"
        return None

    @classmethod
    def _verify_domain_connectivity(cls, domain: Optional[str]) -> Tuple[bool, bool]:
        """Fast non-blocking connectivity verification for DNS & MX."""
        if not domain:
            return False, False
        try:
            # Fast DNS lookup
            socket.gethostbyname(domain)
            dns_ok = True
        except Exception:
            dns_ok = False

        mx_ok = False
        if dns_ok:
            try:
                socket.getaddrinfo(domain, 25, socket.AF_UNSPEC, socket.SOCK_STREAM)
                mx_ok = True
            except Exception:
                mx_ok = False

        return dns_ok, mx_ok
