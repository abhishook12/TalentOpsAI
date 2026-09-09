"""
extractor/sourcing_signals_engine.py — Advanced Sourcing Signals & Deep Attribute Factorization Engine

Algorithms for extracting high-value recruiter signals:
1. Work Authorization & Visa Classifications (USC, GC, H1B, OPT/CPT, TN, C2C, W2, 1099)
2. Compensation & Rate Expectations (Hourly C2C/W2, Annual base/bonus)
3. Availability & Notice Period (Immediate, 2 weeks, 30 days)
4. Security Clearance Status (Secret, TS/SCI, Public Trust)
5. Seniority & Leveling Inference (Intern through C-Level)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


# ── Work Authorization & Visa Regexes ─────────────────────────────────────────
VISA_PATTERNS = [
    ("US_CITIZEN", re.compile(r"\b(?:u\.?s\.?\s*citizen(?:ship)?|usc|citizen)\b", re.IGNORECASE)),
    ("GREEN_CARD", re.compile(r"\b(?:green\s*card|gc\b|permanent\s*resident|pr\b)", re.IGNORECASE)),
    ("GC_EAD", re.compile(r"\b(?:gc[-\s]*ead|green\s*card[-\s]*ead)\b", re.IGNORECASE)),
    ("H1B", re.compile(r"\b(?:h[-]?1b|h1[-]?b\s*transfer|h1b\s*cap)\b", re.IGNORECASE)),
    ("H4_EAD", re.compile(r"\b(?:h[-]?4\s*ead|h4[-]?ead)\b", re.IGNORECASE)),
    ("OPT_CPT", re.compile(r"\b(?:opt\b|cpt\b|stem\s*opt|f[-]?1\s*opt)\b", re.IGNORECASE)),
    ("TN_VISA", re.compile(r"\b(?:tn\s*visa|tn[-]?1|tn[-]?2|nafta\s*visa)\b", re.IGNORECASE)),
    ("L1_L2", re.compile(r"\b(?:l[-]?1[ab]?|l[-]?2\s*ead)\b", re.IGNORECASE)),
    ("EAD_GENERAL", re.compile(r"\b(?:ead\b|employment\s*authorization\s*card)\b", re.IGNORECASE)),
]

TAX_TERM_PATTERNS = [
    ("C2C", re.compile(r"\b(?:c2c|corp[- ]to[- ]corp|corp2corp)\b", re.IGNORECASE)),
    ("W2", re.compile(r"\b(?:w[-]?2|w2\s*only)\b", re.IGNORECASE)),
    ("1099", re.compile(r"\b(?:1099|independent\s*contractor)\b", re.IGNORECASE)),
]


# ── Compensation & Rate Patterns ──────────────────────────────────────────────
HOURLY_RATE_REGEX = re.compile(
    r"(?:\$|usd\s*)?(\d{2,3}(?:\.\d{1,2})?)\s*(?:-|to|\/)\s*(?:\$|usd\s*)?(\d{2,3}(?:\.\d{1,2})?)?\s*(?:\/|\s*per\s*)?(?:hr|hour|hourly)\b",
    re.IGNORECASE,
)
HOURLY_SIMPLE_REGEX = re.compile(
    r"\$(\d{2,3})\s*(?:c2c|w2|hr|hour|\/hr)\b",
    re.IGNORECASE,
)
ANNUAL_SALARY_REGEX = re.compile(
    r"(?:\$|usd\s*)?(\d{2,3})\s*k?\s*(?:-|to)\s*(?:\$|usd\s*)?(\d{2,3})\s*k\b|(?:\$|usd\s*)(\d{2,3})\s*k\b",
    re.IGNORECASE,
)


# ── Availability Patterns ─────────────────────────────────────────────────────
AVAILABILITY_PATTERNS = [
    ("IMMEDIATE", re.compile(r"\b(?:immediate(?:ly)?|ready\s*(?:to\s*join|now)|available\s*(?:now|immediately))\b", re.IGNORECASE)),
    ("TWO_WEEKS", re.compile(r"\b(?:2\s*weeks?(?:\s*notice)?|two\s*weeks?(?:\s*notice)?)\b", re.IGNORECASE)),
    ("ONE_WEEK", re.compile(r"\b(?:1\s*week(?:\s*notice)?|one\s*week(?:\s*notice)?)\b", re.IGNORECASE)),
    ("ONE_MONTH", re.compile(r"\b(?:1\s*month(?:\s*notice)?|30\s*days?(?:\s*notice)?|one\s*month)\b", re.IGNORECASE)),
]


# ── Security Clearance Patterns ───────────────────────────────────────────────
CLEARANCE_PATTERNS = [
    ("TS_SCI", re.compile(r"\b(?:top\s*secret(?:\/sci)?|ts[\/-]sci|ts\s*clearance)\b", re.IGNORECASE)),
    ("SECRET", re.compile(r"\b(?:secret\s*clearance|dod\s*secret|active\s*secret)\b", re.IGNORECASE)),
    ("PUBLIC_TRUST", re.compile(r"\b(?:public\s*trust|mbi\b)\b", re.IGNORECASE)),
    ("CONFIDENTIAL", re.compile(r"\b(?:confidential\s*clearance)\b", re.IGNORECASE)),
]


# ── Seniority & Leveling Patterns ─────────────────────────────────────────────
SENIORITY_PATTERNS = [
    ("C_LEVEL", re.compile(r"\b(?:chief|ceo|cto|cfo|cio|ciso|coo|cro|cmo|founder|co-founder)\b", re.IGNORECASE)),
    ("VP", re.compile(r"\b(?:vp|vice\s*president|evp|svp)\b", re.IGNORECASE)),
    ("DIRECTOR", re.compile(r"\b(?:director|head\s*of)\b", re.IGNORECASE)),
    ("MANAGER", re.compile(r"\b(?:engineering\s*manager|em\b|tech\s*lead\s*manager|tlm\b|manager|lead)\b", re.IGNORECASE)),
    ("PRINCIPAL", re.compile(r"\b(?:principal|distinguished|fellow)\b", re.IGNORECASE)),
    ("STAFF", re.compile(r"\b(?:staff)\b", re.IGNORECASE)),
    ("SENIOR", re.compile(r"\b(?:senior|sr\.?)\b", re.IGNORECASE)),
    ("MID", re.compile(r"\b(?:mid[- ]level|intermediate|software\s*engineer\s*(?:ii|2|iii|3))\b", re.IGNORECASE)),
    ("JUNIOR", re.compile(r"\b(?:junior|jr\.?|associate|entry[- ]level|engineer\s*1|engineer\s*i\b)\b", re.IGNORECASE)),
    ("INTERN", re.compile(r"\b(?:intern(?:ship)?|co-op|apprentice)\b", re.IGNORECASE)),
]


@dataclass
class SourcingSignals:
    """Structured container for deep recruiter and candidate sourcing attributes."""
    work_authorization: Optional[str] = None
    work_authorization_confidence: float = 0.0
    tax_terms: List[str] = field(default_factory=list)
    compensation: Optional[Dict[str, Any]] = None
    availability: Optional[str] = None
    security_clearance: Optional[str] = None
    seniority_level: Optional[str] = None
    work_preference: Optional[str] = None  # REMOTE | HYBRID | ONSITE
    raw_matches: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "work_authorization": self.work_authorization,
            "work_authorization_confidence": self.work_authorization_confidence,
            "tax_terms": self.tax_terms,
            "compensation": self.compensation,
            "availability": self.availability,
            "security_clearance": self.security_clearance,
            "seniority_level": self.seniority_level,
            "work_preference": self.work_preference,
            "raw_matches": self.raw_matches,
        }


class SourcingSignalsEngine:
    """
    Deterministic extraction and scoring engine for rich talent intelligence signals.
    """

    @classmethod
    def extract_signals(cls, text: str) -> SourcingSignals:
        """Parses raw text (chat notes, email body, resume snippet) and returns structured signals."""
        if not text or not text.strip():
            return SourcingSignals()

        clean_text = text.strip()
        signals = SourcingSignals()

        # 1. Extract Work Authorization
        for auth_label, pat in VISA_PATTERNS:
            m = pat.search(clean_text)
            if m:
                signals.work_authorization = auth_label
                signals.work_authorization_confidence = 0.95
                signals.raw_matches.append(m.group(0))
                break

        # Tax terms (C2C, W2, 1099)
        for term_label, pat in TAX_TERM_PATTERNS:
            m = pat.search(clean_text)
            if m:
                if term_label not in signals.tax_terms:
                    signals.tax_terms.append(term_label)
                    signals.raw_matches.append(m.group(0))

        # 2. Extract Compensation / Rate
        comp = cls._extract_compensation(clean_text)
        if comp:
            signals.compensation = comp
            signals.raw_matches.append(comp.get("raw_text", ""))

        # 3. Extract Availability
        for avail_label, pat in AVAILABILITY_PATTERNS:
            m = pat.search(clean_text)
            if m:
                signals.availability = avail_label
                signals.raw_matches.append(m.group(0))
                break

        # 4. Extract Security Clearance
        for clear_label, pat in CLEARANCE_PATTERNS:
            m = pat.search(clean_text)
            if m:
                signals.security_clearance = clear_label
                signals.raw_matches.append(m.group(0))
                break

        # 5. Extract Seniority Level
        for sen_label, pat in SENIORITY_PATTERNS:
            m = pat.search(clean_text)
            if m:
                signals.seniority_level = sen_label
                break

        # 6. Extract Work Preference (Remote / Hybrid / Onsite)
        if re.search(r"\b(?:remote|wfh|work\s*from\s*home|100%\s*remote)\b", clean_text, re.IGNORECASE):
            signals.work_preference = "REMOTE"
        elif re.search(r"\b(?:hybrid|flexible\s*schedule)\b", clean_text, re.IGNORECASE):
            signals.work_preference = "HYBRID"
        elif re.search(r"\b(?:onsite|on-site|in-office)\b", clean_text, re.IGNORECASE):
            signals.work_preference = "ONSITE"

        return signals

    @classmethod
    def _extract_compensation(cls, text: str) -> Optional[Dict[str, Any]]:
        """Extracts hourly rate or annual salary structure."""
        # Check hourly rate range e.g. $70 - $85/hr or $75/hr
        m_hourly = HOURLY_RATE_REGEX.search(text)
        if m_hourly:
            min_v = float(m_hourly.group(1))
            max_v = float(m_hourly.group(2)) if m_hourly.group(2) else min_v
            return {
                "type": "HOURLY",
                "min_rate": min_v,
                "max_rate": max_v,
                "currency": "USD",
                "display": f"${min_v:.0f}-${max_v:.0f}/hr" if min_v != max_v else f"${min_v:.0f}/hr",
                "raw_text": m_hourly.group(0),
            }

        # Check simple hourly e.g. $80 C2C or $75/hr
        m_simple = HOURLY_SIMPLE_REGEX.search(text)
        if m_simple:
            rate_val = float(m_simple.group(1))
            return {
                "type": "HOURLY",
                "min_rate": rate_val,
                "max_rate": rate_val,
                "currency": "USD",
                "display": f"${rate_val:.0f}/hr",
                "raw_text": m_simple.group(0),
            }

        # Check annual salary range e.g. $150k - $180k or $160k
        m_annual = ANNUAL_SALARY_REGEX.search(text)
        if m_annual:
            if m_annual.group(3):
                sal = float(m_annual.group(3)) * 1000
                return {
                    "type": "ANNUAL",
                    "min_salary": sal,
                    "max_salary": sal,
                    "currency": "USD",
                    "display": f"${sal/1000:.0f}k/yr",
                    "raw_text": m_annual.group(0),
                }
            else:
                min_sal = float(m_annual.group(1)) * 1000
                max_sal = float(m_annual.group(2)) * 1000
                return {
                    "type": "ANNUAL",
                    "min_salary": min_sal,
                    "max_salary": max_sal,
                    "currency": "USD",
                    "display": f"${min_sal/1000:.0f}k-${max_sal/1000:.0f}k/yr",
                    "raw_text": m_annual.group(0),
                }

        return None
