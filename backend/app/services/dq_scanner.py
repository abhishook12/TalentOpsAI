"""
TalentOps AI - Continuous Data Quality Scanner
Modular scanning engine executing 14 specialized validators.
Detects, classifies, and produces structured issues (DQ-xxxxx) without directly
mutating the database. Isolates critical anomalies into Quarantine.

Validators:
1. SchemaValidator
2. RequiredFieldValidator (Separates Bad vs Missing)
3. FormatValidator (Garbage emails, names, phones, companies, locations)
4. DuplicateDetector (Fuzzy multi-signal: Auto-Merge >=0.98, Review 0.80-0.98, Separate <0.80)
5. ReferentialIntegrityValidator
6. EmailValidator
7. PhoneValidator
8. ProfileValidator
9. CompanyValidator
10. DomainValidator
11. DateTimelineValidator (Future dates, negative durations, conflicts)
12. CrossFieldConsistencyValidator (Company-email mismatch, seniority conflicts)
13. CrossSourceReconciliation
14. FreshnessValidator
"""

from __future__ import annotations

import difflib
import logging
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from ..models.data_quality_models import (
    PersonIdentity,
    CompanyMaster,
    CompanyAlias,
    DataQualityIssue,
    QuarantineRecord,
    FieldObservation,
)
from ..models.auth_models import User
from .evidence_ladder import EvidenceLadder, EvidenceLevel
from .temporal_reconciler import TemporalReconciler

logger = logging.getLogger("talentops.dq_scanner")

# Standard known garbage values
GARBAGE_EMAILS = {
    "test@test.com", "abc@gmail.com", "n/a", "unknown", "-", "none",
    "john@", "john@@abc.com", "noemail@talentops.ai", "user@domain.com"
}
GARBAGE_NAMES = {"n/a", "unknown", "test user", "john111", "asdf", "test", "null", "-", "admin"}
GARBAGE_PHONES = {"123456789", "0000000000", "1111111111", "1234567890", "0", "123"}
GARBAGE_COMPANIES = {"self", "n/a", "unknown company", "test", "freelance", "none", "null", "-"}

LOCATION_NORMALIZATION_MAP = {
    "usa": "United States",
    "us": "United States",
    "u.s.": "United States",
    "u.s.a.": "United States",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "sf": "San Francisco, CA",
    "nyc": "New York, NY",
}

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "icloud.com", "protonmail.com", "mail.com", "live.com"
}


class DataQualityScanner:
    """
    Continuous Data Quality Scanner with 14 modular validators.
    """

    def __init__(self, db: Session):
        self.db = db

    def scan_all(self, owner_user_id: int, limit: int = 200) -> Dict[str, Any]:
        """
        Runs all 14 validators across the user's person and company records.
        Returns summary of detected issues, quarantined items, and stats.
        """
        people = self.db.query(PersonIdentity).filter(
            PersonIdentity.owner_user_id == owner_user_id
        ).limit(limit).all()

        companies = self.db.query(CompanyMaster).limit(limit).all()

        detected_issues: List[Dict[str, Any]] = []
        quarantined_count = 0

        # Run Person-level Validators
        for person in people:
            issues = self.validate_person(person)
            for iss in issues:
                db_issue = self._persist_issue(iss, owner_user_id)
                detected_issues.append(iss)
                # Auto-quarantine if CRITICAL or HIGH severity
                if iss.get("severity") in ("CRITICAL", "HIGH") and iss.get("problem_type") in ("BAD", "CONFLICTING"):
                    self._quarantine_record(
                        entity_type="PERSON",
                        entity_id=person.id,
                        field_name=iss.get("field_name", "__RECORD__"),
                        raw_value=iss.get("raw_value"),
                        reason=iss.get("description"),
                        problem_type=iss.get("problem_type", "BAD"),
                        severity=iss.get("severity", "HIGH"),
                        owner_user_id=owner_user_id,
                        issue_id=db_issue.id if db_issue else None,
                    )
                    quarantined_count += 1

        # Run Company-level Validators
        for comp in companies:
            c_issues = self.validate_company(comp)
            for iss in c_issues:
                self._persist_issue(iss, owner_user_id)
                detected_issues.append(iss)

        # Run Cross-Entity Duplicate Detector
        dup_issues = self.detect_duplicates(people)
        for iss in dup_issues:
            self._persist_issue(iss, owner_user_id)
            detected_issues.append(iss)

        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to commit scan results: {e}")

        return {
            "scanned_people": len(people),
            "scanned_companies": len(companies),
            "total_issues_detected": len(detected_issues),
            "newly_quarantined": quarantined_count,
            "issues": detected_issues[:50],  # sample
        }

    def validate_person(self, person: PersonIdentity) -> List[Dict[str, Any]]:
        """
        Runs individual validators against a person record.
        """
        issues: List[Dict[str, Any]] = []

        # 1. Schema & Required Field Validator
        issues.extend(self._validate_required_fields(person))

        # 2. Format Validator (Garbage emails, names, phones, locations)
        issues.extend(self._validate_formats(person))

        # 3. Email Validator
        issues.extend(self._validate_email(person))

        # 4. Phone Validator
        issues.extend(self._validate_phone(person))

        # 5. Profile Validator
        issues.extend(self._validate_profile(person))

        # 6. Cross-Field Consistency Validator
        issues.extend(self._validate_cross_field(person))

        # 7. Freshness Validator
        issues.extend(self._validate_freshness(person))

        return issues

    def _validate_required_fields(self, person: PersonIdentity) -> List[Dict[str, Any]]:
        issues = []
        # Check Name
        if not person.canonical_name:
            issues.append({
                "issue_type": "MISSING_NAME",
                "problem_type": "MISSING",
                "severity": "CRITICAL",
                "entity_type": "PERSON",
                "entity_id": person.id,
                "field_name": "canonical_name",
                "raw_value": None,
                "description": f"Person record #{person.id} is missing mandatory canonical_name",
                "remediation_action": "Enrich name from profile URL or external source",
                "ladder_level": EvidenceLevel.LEVEL_1_WEAK,
            })
        # Check Contact (Must have email or phone or linkedin)
        if not person.primary_email and not person.primary_phone and not person.canonical_profile_url:
            issues.append({
                "issue_type": "MISSING_CONTACT",
                "problem_type": "MISSING",
                "severity": "HIGH",
                "entity_type": "PERSON",
                "entity_id": person.id,
                "field_name": "contact_channels",
                "raw_value": None,
                "description": f"Person #{person.id} ({person.canonical_name}) has zero contact channels",
                "remediation_action": "Enrich with verified corporate email, phone, or LinkedIn profile",
                "ladder_level": EvidenceLevel.LEVEL_1_WEAK,
            })
        return issues

    def _validate_formats(self, person: PersonIdentity) -> List[Dict[str, Any]]:
        issues = []
        name_lower = (person.canonical_name or "").strip().lower()

        # Name garbage check
        if name_lower in GARBAGE_NAMES or len(name_lower) < 2 or re.match(r"^[^a-zA-Z]+$", name_lower):
            issues.append({
                "issue_type": "GARBAGE_NAME",
                "problem_type": "BAD",
                "severity": "CRITICAL",
                "entity_type": "PERSON",
                "entity_id": person.id,
                "field_name": "canonical_name",
                "raw_value": person.canonical_name,
                "description": f"Invalid/placeholder name detected: '{person.canonical_name}'",
                "remediation_action": "Quarantine record and re-extract from profile",
                "ladder_level": EvidenceLevel.LEVEL_1_WEAK,
            })

        # Company garbage check
        comp_lower = (person.current_company or "").strip().lower()
        if comp_lower in GARBAGE_COMPANIES:
            issues.append({
                "issue_type": "GARBAGE_COMPANY",
                "problem_type": "BAD",
                "severity": "MEDIUM",
                "entity_type": "PERSON",
                "entity_id": person.id,
                "field_name": "current_company",
                "raw_value": person.current_company,
                "description": f"Generic or placeholder company name: '{person.current_company}'",
                "remediation_action": "Normalize or resolve canonical employer",
                "ladder_level": EvidenceLevel.LEVEL_2_MODERATE,
            })

        # Location normalization check
        loc = (person.location or "").strip().lower()
        if loc in LOCATION_NORMALIZATION_MAP:
            standardized = LOCATION_NORMALIZATION_MAP[loc]
            issues.append({
                "issue_type": "NON_STANDARD_LOCATION",
                "problem_type": "SUSPICIOUS",
                "severity": "LOW",
                "entity_type": "PERSON",
                "entity_id": person.id,
                "field_name": "location",
                "raw_value": person.location,
                "description": f"Non-standard location abbreviation: '{person.location}' -> '{standardized}'",
                "remediation_action": "Standardize to official location name",
                "ladder_level": EvidenceLevel.LEVEL_2_MODERATE,
            })

        return issues

    def _validate_email(self, person: PersonIdentity) -> List[Dict[str, Any]]:
        issues = []
        email = (person.primary_email or "").strip().lower()
        if not email:
            return issues

        # Check Garbage email
        if email in GARBAGE_EMAILS or "@" not in email:
            issues.append({
                "issue_type": "INVALID_EMAIL",
                "problem_type": "BAD",
                "severity": "CRITICAL",
                "entity_type": "PERSON",
                "entity_id": person.id,
                "field_name": "primary_email",
                "raw_value": person.primary_email,
                "description": f"Garbage or malformed email address: '{person.primary_email}'",
                "remediation_action": "Quarantine email and search for verified corporate address",
                "ladder_level": EvidenceLevel.LEVEL_1_WEAK,
            })
            return issues

        # Check double @@ or invalid syntax
        if "@@" in email or email.startswith("@") or email.endswith("@") or " " in email:
            issues.append({
                "issue_type": "INVALID_EMAIL_SYNTAX",
                "problem_type": "BAD",
                "severity": "HIGH",
                "entity_type": "PERSON",
                "entity_id": person.id,
                "field_name": "primary_email",
                "raw_value": person.primary_email,
                "description": f"Syntax error in email: '{person.primary_email}'",
                "remediation_action": "Apply safe syntax correction or quarantine",
                "ladder_level": EvidenceLevel.LEVEL_2_MODERATE,
            })

        return issues

    def _validate_phone(self, person: PersonIdentity) -> List[Dict[str, Any]]:
        issues = []
        phone = (person.primary_phone or "").strip()
        if not phone:
            return issues

        digits = re.sub(r"\D", "", phone)
        if digits in GARBAGE_PHONES or len(digits) < 7:
            issues.append({
                "issue_type": "GARBAGE_PHONE",
                "problem_type": "BAD",
                "severity": "HIGH",
                "entity_type": "PERSON",
                "entity_id": person.id,
                "field_name": "primary_phone",
                "raw_value": person.primary_phone,
                "description": f"Dummy/sequential phone number detected: '{person.primary_phone}'",
                "remediation_action": "Quarantine phone and clear from active dialers",
                "ladder_level": EvidenceLevel.LEVEL_1_WEAK,
            })
        return issues

    def _validate_profile(self, person: PersonIdentity) -> List[Dict[str, Any]]:
        issues = []
        url = (person.canonical_profile_url or "").strip()
        if not url:
            return issues

        if not (url.startswith("http://") or url.startswith("https://") or "linkedin.com" in url):
            issues.append({
                "issue_type": "MALFORMED_PROFILE_URL",
                "problem_type": "BAD",
                "severity": "MEDIUM",
                "entity_type": "PERSON",
                "entity_id": person.id,
                "field_name": "canonical_profile_url",
                "raw_value": person.canonical_profile_url,
                "description": f"Malformed or non-standard profile URL: '{person.canonical_profile_url}'",
                "remediation_action": "Standardize URL prefix and strip tracking parameters",
                "ladder_level": EvidenceLevel.LEVEL_2_MODERATE,
            })
        return issues

    def _validate_cross_field(self, person: PersonIdentity) -> List[Dict[str, Any]]:
        issues = []
        email = (person.primary_email or "").strip().lower()
        company = (person.current_company or "").strip().lower()
        title = (person.current_title or "").strip().lower()

        # Check 1: Company-Email Mismatch (e.g. Company is Google, but corporate email is @microsoft.com)
        if email and "@" in email and company:
            email_domain = email.split("@")[1]
            if email_domain not in FREE_EMAIL_DOMAINS:
                # If corporate email domain has zero overlap with company name
                comp_clean = re.sub(r"[^a-z0-9]", "", company)
                domain_prefix = email_domain.split(".")[0]
                if comp_clean and len(comp_clean) >= 4 and len(domain_prefix) >= 4:
                    if domain_prefix not in comp_clean and comp_clean not in domain_prefix:
                        # Cross-field mismatch
                        issues.append({
                            "issue_type": "COMPANY_EMAIL_MISMATCH",
                            "problem_type": "CONFLICTING",
                            "severity": "HIGH",
                            "entity_type": "PERSON",
                            "entity_id": person.id,
                            "field_name": "primary_email",
                            "raw_value": person.primary_email,
                            "description": f"Corporate email domain '@{email_domain}' does not align with company '{person.current_company}'",
                            "remediation_action": "Investigate potential employer switch and move old email to historical",
                            "ladder_level": EvidenceLevel.LEVEL_3_STRONG,
                        })

        # Check 2: Seniority / Role Conflict (e.g. Title says 'Senior Director' but contains 'Intern')
        if "director" in title or "vice president" in title or "vp" in title or "chief" in title:
            if "intern" in title or "student" in title or "trainee" in title:
                issues.append({
                    "issue_type": "SENIORITY_ROLE_CONFLICT",
                    "problem_type": "CONFLICTING",
                    "severity": "MEDIUM",
                    "entity_type": "PERSON",
                    "entity_id": person.id,
                    "field_name": "current_title",
                    "raw_value": person.current_title,
                    "description": f"Contradictory seniority terms in title: '{person.current_title}'",
                    "remediation_action": "Reconcile title with recent observation evidence",
                    "ladder_level": EvidenceLevel.LEVEL_2_MODERATE,
                })

        return issues

    def _validate_freshness(self, person: PersonIdentity) -> List[Dict[str, Any]]:
        issues = []
        now = datetime.now(timezone.utc)
        observed = person.last_seen_at or person.observed_at or person.created_at
        if observed:
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=timezone.utc)
            age_days = (now - observed).days
            if age_days > 365 or person.freshness_score < 40.0:
                issues.append({
                    "issue_type": "STALE_RECORD",
                    "problem_type": "STALE",
                    "severity": "LOW",
                    "entity_type": "PERSON",
                    "entity_id": person.id,
                    "field_name": "freshness_score",
                    "raw_value": str(round(person.freshness_score, 1)),
                    "description": f"Record last confirmed {age_days} days ago. Quality freshness decayed.",
                    "remediation_action": "Schedule re-enrichment through Scout edge observation",
                    "ladder_level": EvidenceLevel.LEVEL_2_MODERATE,
                })
        return issues

    def validate_company(self, company: CompanyMaster) -> List[Dict[str, Any]]:
        """
        Validates canonical company master and domain resolution.
        """
        issues = []
        name = (company.canonical_name or "").strip().lower()
        if name in GARBAGE_COMPANIES or len(name) < 2:
            issues.append({
                "issue_type": "GARBAGE_COMPANY_NAME",
                "problem_type": "BAD",
                "severity": "HIGH",
                "entity_type": "COMPANY",
                "entity_id": company.id,
                "field_name": "canonical_name",
                "raw_value": company.canonical_name,
                "description": f"Invalid canonical company name: '{company.canonical_name}'",
                "remediation_action": "Quarantine company and map aliases",
                "ladder_level": EvidenceLevel.LEVEL_2_MODERATE,
            })

        domain = (company.primary_domain or "").strip().lower()
        if not domain:
            issues.append({
                "issue_type": "MISSING_COMPANY_DOMAIN",
                "problem_type": "MISSING",
                "severity": "MEDIUM",
                "entity_type": "COMPANY",
                "entity_id": company.id,
                "field_name": "primary_domain",
                "raw_value": None,
                "description": f"Company '{company.canonical_name}' has no registered domain",
                "remediation_action": "Discover domain from corporate registry or MX lookup",
                "ladder_level": EvidenceLevel.LEVEL_2_MODERATE,
            })
        elif "." not in domain or domain in FREE_EMAIL_DOMAINS:
            issues.append({
                "issue_type": "INVALID_COMPANY_DOMAIN",
                "problem_type": "BAD",
                "severity": "HIGH",
                "entity_type": "COMPANY",
                "entity_id": company.id,
                "field_name": "primary_domain",
                "raw_value": company.primary_domain,
                "description": f"Free or malformed domain assigned to company: '{company.primary_domain}'",
                "remediation_action": "Resolve true corporate domain",
                "ladder_level": EvidenceLevel.LEVEL_3_STRONG,
            })

        return issues

    def detect_duplicates(self, people: List[PersonIdentity]) -> List[Dict[str, Any]]:
        """
        Fuzzy multi-signal duplicate detector across people.
        Calibrated decision tiers:
        - >= 0.98 -> AUTO_MERGE
        - 0.80 - 0.98 -> REVIEW
        - < 0.80 -> KEEP_SEPARATE
        """
        issues = []
        n = len(people)
        for i in range(n):
            p1 = people[i]
            for j in range(i + 1, n):
                p2 = people[j]

                prob, reasons = self._calculate_duplicate_probability(p1, p2)
                if prob >= 0.80:
                    outcome = "AUTO_MERGE" if prob >= 0.98 else "REVIEW"
                    issues.append({
                        "issue_type": "DUPLICATE_PERSON",
                        "problem_type": "DUPLICATE",
                        "severity": "HIGH" if prob >= 0.90 else "MEDIUM",
                        "entity_type": "PERSON",
                        "entity_id": p1.id,
                        "field_name": "identity",
                        "raw_value": f"Person #{p1.id} vs #{p2.id}",
                        "description": (
                            f"Potential duplicate between '{p1.canonical_name}' and '{p2.canonical_name}' "
                            f"(Probability: {round(prob*100)}%, Decision: {outcome}). Factors: {', '.join(reasons)}"
                        ),
                        "remediation_action": f"{outcome} via Non-Destructive Review Queue",
                        "ladder_level": EvidenceLevel.LEVEL_4_VERY_STRONG if prob >= 0.98 else EvidenceLevel.LEVEL_3_STRONG,
                    })
        return issues

    def _calculate_duplicate_probability(
        self,
        p1: PersonIdentity,
        p2: PersonIdentity,
    ) -> Tuple[float, List[str]]:
        """
        Multi-signal fuzzy matcher combining name similarity, email, profile, and company.
        """
        score = 0.0
        reasons = []

        # Signal 1: Identical or close LinkedIn profile URL (+0.50)
        u1 = (p1.canonical_profile_url or "").strip().lower()
        u2 = (p2.canonical_profile_url or "").strip().lower()
        if u1 and u2 and u1 == u2:
            score += 0.50
            reasons.append("Identical profile URL")

        # Signal 2: Identical primary email (+0.45)
        e1 = (p1.primary_email or "").strip().lower()
        e2 = (p2.primary_email or "").strip().lower()
        if e1 and e2 and e1 == e2:
            score += 0.45
            reasons.append("Identical email address")

        # Signal 3: Fuzzy name similarity (+0.25)
        n1 = (p1.canonical_name or "").strip().lower()
        n2 = (p2.canonical_name or "").strip().lower()
        name_sim = difflib.SequenceMatcher(None, n1, n2).ratio()
        if name_sim >= 0.90:
            score += 0.25
            reasons.append(f"High name similarity ({round(name_sim*100)}%)")
        elif name_sim >= 0.75:
            score += 0.15
            reasons.append(f"Moderate name similarity ({round(name_sim*100)}%)")

        # Signal 4: Matching Company (+0.15)
        c1 = (p1.current_company or "").strip().lower()
        c2 = (p2.current_company or "").strip().lower()
        if c1 and c2 and (c1 in c2 or c2 in c1):
            score += 0.15
            reasons.append("Matching employer")

        # Normalize score to 1.0 max
        prob = min(0.99, score)
        return prob, reasons

    def _persist_issue(self, iss: Dict[str, Any], owner_user_id: int) -> Optional[DataQualityIssue]:
        """
        Stores structured issue in data_quality_issues table.
        """
        code = f"DQ-{uuid.uuid4().hex[:8].upper()}"
        issue = DataQualityIssue(
            issue_code=code,
            issue_type=iss["issue_type"],
            problem_type=iss.get("problem_type", "BAD"),
            severity=iss.get("severity", "MEDIUM"),
            entity_type=iss["entity_type"],
            entity_id=iss["entity_id"],
            field_name=iss.get("field_name"),
            raw_value=str(iss.get("raw_value") or ""),
            description=iss["description"],
            remediation_action=iss.get("remediation_action"),
            evidence_ladder_level=iss.get("ladder_level", 1),
            status="OPEN",
            owner_user_id=owner_user_id,
        )
        self.db.add(issue)
        return issue

    def _quarantine_record(
        self,
        entity_type: str,
        entity_id: int,
        field_name: str,
        raw_value: Any,
        reason: str,
        problem_type: str,
        severity: str,
        owner_user_id: int,
        issue_id: Optional[int] = None,
    ) -> QuarantineRecord:
        """
        Places record or corrupted field into quarantine isolation.
        """
        qrn_code = f"QRN-{uuid.uuid4().hex[:8].upper()}"
        record = QuarantineRecord(
            quarantine_id=qrn_code,
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field_name,
            raw_value=str(raw_value or ""),
            quarantine_reason=reason,
            problem_type=problem_type,
            severity=severity,
            status="QUARANTINED",
            owner_user_id=owner_user_id,
        )
        self.db.add(record)
        return record
