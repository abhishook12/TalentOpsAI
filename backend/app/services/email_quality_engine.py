"""
TalentOps AI - Multi-Stage Email Verification & Contact Quality Engine
7-Stage Pipeline: Syntax -> Domain -> MX -> Disposable -> Role -> Deliverability -> Person Match.
Computes multi-dimensional quality scores (0-100) and person-to-email association confidence.
"""

from __future__ import annotations

import logging
import re
import socket
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("talentops.email_quality")

# Comprehensive disposable email providers blocklist
DISPOSABLE_DOMAINS = {
    "mailinator.com", "tempmail.com", "10minutemail.com", "guerrillamail.com",
    "sharklasers.com", "yopmail.com", "trashmail.com", "dispostable.com",
    "maildrop.cc", "temp-mail.org", "throwawaymail.com", "getairmail.com",
    "fakeinbox.com", "burnermail.io", "trashmail.net", "mohmal.com",
    "crazymailing.com", "generator.email", "nada.ltd", "tempmail.net",
}

# Free/consumer email providers (distinguished from corporate domains)
FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "icloud.com", "protonmail.com", "zoho.com", "live.com", "msn.com",
    "me.com", "mail.com", "ymail.com", "att.net", "comcast.net",
}

# Role account prefixes (non-individual mailbox aliases)
ROLE_ACCOUNT_PREFIXES = {
    "info", "sales", "support", "admin", "administrator", "contact", "help",
    "careers", "jobs", "recruiting", "recruiter", "talent", "team", "office",
    "press", "media", "mediarelations", "marketing", "billing", "accounts",
    "compliance", "security", "privacy", "legal", "hr", "operations", "ops",
    "general", "inquiries", "feedback", "postmaster", "hostmaster", "webmaster",
}


@dataclass
class EmailQualityResult:
    email: str
    syntax_valid: bool = False
    domain_valid: bool = False
    mx_valid: bool = False
    is_disposable: bool = False
    is_free_provider: bool = False
    role_type: str = "individual"  # individual, role_account, disposable
    mailbox_status: str = "UNKNOWN"  # DELIVERABLE, RISKY, UNDELIVERABLE, UNKNOWN
    person_match: float = 0.0      # 0.0 - 1.0 (compatibility with person name)
    company_match: float = 0.0     # 0.0 - 1.0 (compatibility with company domain)
    currentness: float = 1.0       # 0.0 - 1.0 (freshness factor)
    quality_score: float = 0.0     # 0.0 - 100.0
    quality_grade: str = "POOR"    # EXCELLENT, HIGH, USABLE, RISKY, POOR
    sub_scores: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)

    @property
    def is_role_account(self) -> bool:
        return self.role_type == "role_account"

    def to_dict(self) -> dict[str, Any]:
        return {
            "email": self.email,
            "syntax_valid": self.syntax_valid,
            "domain_valid": self.domain_valid,
            "mx_valid": self.mx_valid,
            "is_disposable": self.is_disposable,
            "is_free_provider": self.is_free_provider,
            "role_type": self.role_type,
            "is_role_account": self.is_role_account,
            "mailbox_status": self.mailbox_status,
            "person_match": round(self.person_match, 2),
            "company_match": round(self.company_match, 2),
            "currentness": round(self.currentness, 2),
            "currentness_score": round(self.currentness * 100, 1),
            "quality_score": round(self.quality_score, 1),
            "quality_grade": self.quality_grade,
            "sub_scores": {k: round(v, 1) for k, v in self.sub_scores.items()},
            "reasons": self.reasons,
            "last_verified_at": datetime.now(timezone.utc).isoformat(),
        }


class EmailQualityEngine:
    """
    Evaluates emails through the 7-stage quality and person-association pipeline.
    """

    EMAIL_REGEX = re.compile(
        r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
    )

    @classmethod
    def compute_freshness_score(cls, observed_at: Optional[datetime]) -> float:
        """
        Computes 0.0 - 100.0 freshness score based on observation timestamp.
        0-30d: 100.0, 31-90d: 90.0, 91-180d: 75.0, 181-365d: 50.0, >365d: 25.0
        """
        if not observed_at:
            return 80.0
        now = datetime.now(timezone.utc)
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)
        age_days = (now - observed_at).total_seconds() / 86400.0
        if age_days <= 30:
            return 100.0
        elif age_days <= 90:
            return 90.0
        elif age_days <= 180:
            return 75.0
        elif age_days <= 365:
            return 50.0
        else:
            return 25.0

    @classmethod
    def evaluate(
        cls,
        email: str,
        person_name: Optional[str] = None,
        company_name: Optional[str] = None,
        company_domain: Optional[str] = None,
        observed_days_ago: float = 0.0,
        skip_live_dns: bool = False,
    ) -> EmailQualityResult:
        """
        Executes the 7-stage email verification pipeline.
        """
        reasons: list[str] = []
        clean_email = (email or "").strip().lower()

        # ── Stage 1: Syntax Validation ──
        if not clean_email or not cls.EMAIL_REGEX.match(clean_email):
            reasons.append("Invalid email syntax (RFC 5322 violation)")
            return EmailQualityResult(
                email=clean_email,
                syntax_valid=False,
                mailbox_status="UNDELIVERABLE",
                quality_score=0.0,
                quality_grade="POOR",
                reasons=reasons,
            )

        local_part, domain_part = clean_email.split("@", 1)
        syntax_valid = True

        # ── Stage 2: Domain Structure & Resolution ──
        domain_valid = False
        if "." in domain_part and len(domain_part.split(".")[-1]) >= 2:
            domain_valid = True
        else:
            reasons.append("Domain lacks valid top-level extension")

        # ── Stage 3: MX Record Verification ──
        mx_valid = False
        if domain_valid and not skip_live_dns:
            try:
                # Fast socket MX / host check
                socket.getaddrinfo(domain_part, 25, socket.AF_UNSPEC, socket.SOCK_STREAM)
                mx_valid = True
            except Exception:
                # Domain fails direct mail socket resolution
                mx_valid = False
                reasons.append(f"No mail exchange records or unreachable host for {domain_part}")
        elif domain_valid and skip_live_dns:
            mx_valid = True  # In offline test mode, treat structurally valid domains as MX OK

        # ── Stage 4: Disposable / Temporary Email Check ──
        is_disposable = domain_part in DISPOSABLE_DOMAINS
        if is_disposable:
            reasons.append("Domain is a known temporary/disposable email provider")

        # Free consumer provider check
        is_free = domain_part in FREE_EMAIL_DOMAINS

        # ── Stage 5: Role Account vs Individual Mailbox ──
        norm_local = re.sub(r"[^a-z0-9]", "", local_part)
        is_role = local_part in ROLE_ACCOUNT_PREFIXES or norm_local in ROLE_ACCOUNT_PREFIXES
        if is_role:
            role_type = "role_account"
            reasons.append("Address is a generic company role alias, not a personal mailbox")
        elif is_disposable:
            role_type = "disposable"
        else:
            role_type = "individual"

        # ── Stage 6: Mailbox Deliverability Classification ──
        if not domain_valid or is_disposable:
            mailbox_status = "UNDELIVERABLE"
        elif not mx_valid and not skip_live_dns:
            mailbox_status = "UNDELIVERABLE"
        elif is_role or is_free:
            mailbox_status = "RISKY" if is_role else "DELIVERABLE"
        else:
            mailbox_status = "DELIVERABLE"

        # ── Stage 7: Person & Company Association ──
        if is_role:
            person_match = 0.0
        else:
            person_match = cls._compute_person_match(local_part, person_name)
        company_match = cls._compute_company_match(domain_part, company_name, company_domain)

        if person_name and person_match < 0.3:
            reasons.append(f"Low name correlation between '{person_name}' and mailbox '{local_part}'")
        if company_name and not is_free and company_match < 0.4:
            reasons.append(f"Domain '{domain_part}' does not match candidate employer '{company_name}'")

        # ── Freshness Decay (email_age) ──
        # 0-30d: 1.0, 31-90d: 0.9, 91-180d: 0.75, 181-365d: 0.5, >365d: 0.25
        if observed_days_ago <= 30:
            currentness = 1.0
        elif observed_days_ago <= 90:
            currentness = 0.90
        elif observed_days_ago <= 180:
            currentness = 0.75
            reasons.append("Email observation is aging (>90 days)")
        elif observed_days_ago <= 365:
            currentness = 0.50
            reasons.append("Email observation is stale (>180 days)")
        else:
            currentness = 0.25
            reasons.append("Email observation is old (>1 year old)")

        # ── Multi-Dimensional Quality Scoring (0 - 100) ──
        sub_scores = {
            "syntax_score": 10.0 if syntax_valid else 0.0,
            "domain_score": 15.0 if domain_valid else 0.0,
            "mx_score": 20.0 if mx_valid else 0.0,
            "mailbox_score": 25.0 if mailbox_status == "DELIVERABLE" else (12.0 if mailbox_status == "RISKY" else 0.0),
            "person_match_score": person_match * 15.0,
            "company_match_score": company_match * 10.0,
            "freshness_score": currentness * 10.0,
        }

        # Penalties
        penalty = 0.0
        if is_disposable:
            penalty += 80.0
        if is_role:
            penalty += 30.0

        total_score = max(0.0, min(100.0, sum(sub_scores.values()) - penalty))

        # Quality Grade classification
        if total_score >= 95.0:
            quality_grade = "EXCELLENT"
        elif total_score >= 85.0:
            quality_grade = "HIGH"
        elif total_score >= 70.0:
            quality_grade = "USABLE"
        elif total_score >= 50.0:
            quality_grade = "RISKY"
        else:
            quality_grade = "POOR"

        return EmailQualityResult(
            email=clean_email,
            syntax_valid=syntax_valid,
            domain_valid=domain_valid,
            mx_valid=mx_valid,
            is_disposable=is_disposable,
            is_free_provider=is_free,
            role_type=role_type,
            mailbox_status=mailbox_status,
            person_match=person_match,
            company_match=company_match,
            currentness=currentness,
            quality_score=total_score,
            quality_grade=quality_grade,
            sub_scores=sub_scores,
            reasons=reasons,
        )

    @classmethod
    def _compute_person_match(cls, local_part: str, person_name: Optional[str]) -> float:
        """
        Calculates correlation between person's full name and email username.
        e.g. John Smith -> john.smith (1.0), jsmith (0.95), john (0.80), j.smith (0.95)
        """
        if not person_name:
            return 0.70  # neutral if name unknown

        name_clean = re.sub(r"[^a-z\s]", "", person_name.lower()).strip()
        parts = [p for p in name_clean.split() if len(p) > 1]
        if not parts:
            return 0.50

        first = parts[0]
        last = parts[-1] if len(parts) > 1 else ""

        # Common business patterns
        patterns = []
        if last:
            patterns.append(f"{first}.{last}")       # john.smith
            patterns.append(f"{first}_{last}")       # john_smith
            patterns.append(f"{first}{last}")        # johnsmith
            patterns.append(f"{first[0]}.{last}")    # j.smith
            patterns.append(f"{first[0]}{last}")     # jsmith
            patterns.append(f"{first}{last[0]}")     # johns
            patterns.append(f"{last}.{first}")       # smith.john
            patterns.append(f"{last}{first[0]}")     # smithj
        patterns.append(first)                       # john

        # Exact pattern match
        if local_part in patterns:
            return 0.98

        # Substring overlap
        score = 0.0
        if first in local_part:
            score += 0.45
        if last and last in local_part:
            score += 0.45
        if first and local_part.startswith(first[0]):
            score += 0.10

        return min(1.0, max(0.10, score))

    @classmethod
    def _compute_company_match(
        cls,
        email_domain: str,
        company_name: Optional[str],
        known_company_domain: Optional[str] = None,
    ) -> float:
        """
        Calculates correlation between company name/domain and email domain.
        """
        if email_domain.lower() in FREE_EMAIL_DOMAINS:
            return 0.10

        if known_company_domain:
            clean_known = known_company_domain.lower().replace("www.", "")
            clean_dom = email_domain.lower().replace("www.", "")
            if clean_known == clean_dom:
                return 1.0
            if clean_known.split(".")[0] == clean_dom.split(".")[0]:
                return 0.90

        if not company_name:
            return 0.60

        # Strip Inc, Corp, LLC, etc.
        comp_clean = re.sub(r"(?i)\b(inc|corp|corporation|llc|ltd|technologies|tech|solutions|group|holdings)\b", "", company_name)
        comp_slug = re.sub(r"[^a-z0-9]", "", comp_clean.lower())
        domain_stem = email_domain.split(".")[0].lower()

        if comp_slug and (comp_slug == domain_stem or comp_slug in domain_stem or domain_stem in comp_slug):
            return 0.95

        return 0.40
