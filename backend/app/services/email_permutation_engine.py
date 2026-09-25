"""
Email Permutation Matrix & Live Matcher Engine — TalentOps AI
=============================================================
Combines corporate name tokenization, email syntax permutation formulas,
database pattern memory, and live SMTP mailbox probes to discover verified
corporate emails from recruiter names and employer domains.

Mechanics:
1. Tokenizes candidate name into (First, Last, Initials).
2. Checks PostgreSQL `CompanyEmailPattern` for known employer pattern.
3. Generates the top corporate email permutations sorted by likelihood.
4. Executes live non-intrusive SMTP RCPT TO handshake probes to find the winning mailbox.
5. Persists newly discovered winning patterns into `CompanyEmailPattern` for future acceleration.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.models import CompanyEmailPattern, Company
from .email_intelligence_service import email_intelligence
from .smtp_prober import smtp_prober

logger = logging.getLogger("talentops.permutation_engine")


class EmailPermutationEngine:
    """
    Enterprise Email Permutation Matrix & Live Matcher Engine.
    Discovers verified corporate emails from Name + Domain using live socket probing.
    """

    def __init__(self):
        self._pattern_cache: Dict[str, str] = {}

    def discover_verified_email(
        self,
        full_name: str,
        domain: str,
        company_name: Optional[str] = None,
        db: Optional[Session] = None,
        max_probes: int = 5,
    ) -> Optional[Dict[str, Any]]:
        """
        Discovers and mathematically verifies a candidate's email address by
        permuting name syntax and executing live SMTP RCPT TO probes.
        
        Returns dict with winning email, pattern, deliverability status, and confidence.
        """
        if not full_name or not domain:
            return None

        clean_domain = domain.lower().strip().replace("www.", "")
        name_tokens = email_intelligence.clean_name_tokens(full_name)
        if not name_tokens:
            return None

        first = name_tokens.get("first")
        last = name_tokens.get("last")
        if not first or not last or len(first) < 2 or len(last) < 2:
            return None

        # Step 1: Check if company has a known winning email pattern in DB or cache
        known_pattern = self._get_known_company_pattern(clean_domain, db)

        # Step 2: Generate candidate permutations
        candidates = email_intelligence.generate_permutations(
            first=first,
            last=last,
            domain=clean_domain,
            known_pattern=known_pattern,
        )

        if not candidates:
            return None

        # Step 3: Check domain MX and catch-all status
        mx_host = smtp_prober._get_mx_host(clean_domain)
        if not mx_host:
            logger.debug("[PERMUTATION] No MX host for domain %s", clean_domain)
            return None

        is_catchall = smtp_prober.detect_catchall(clean_domain)

        # If domain is catch-all, live probing cannot differentiate addresses.
        # Fall back to top weighted candidate or known company pattern.
        if is_catchall:
            top_candidate = candidates[0]
            winning_email = top_candidate["email"]
            winning_pattern = top_candidate.get("pattern", "first.last")

            logger.debug(
                "[PERMUTATION] Catch-all domain %s: selected weighted pattern %s (%s)",
                clean_domain, winning_pattern, winning_email
            )
            return {
                "email": winning_email,
                "pattern": winning_pattern,
                "smtp_status": "CATCH_ALL",
                "is_deliverable": True,
                "is_catchall": True,
                "smtp_code": 250,
                "mx_host": mx_host,
                "confidence_score": 75 if known_pattern else 65,
                "discovery_method": "permutation_catchall_inferred",
            }

        # Step 4: Live Probe Loop (Probe top candidates until a 250 OK mailbox is discovered)
        probed_count = 0
        for cand in candidates[:max_probes]:
            target_email = cand["email"]
            pattern_name = cand["pattern"]
            probed_count += 1

            probe_result = smtp_prober.probe_mailbox(target_email, mx_host=mx_host)

            if probe_result.smtp_code == 250 and probe_result.mailbox_exists and not probe_result.is_catchall:
                logger.info(
                    "[PERMUTATION] SUCCESS: Verified %s at %s (Pattern: %s) in %d probes",
                    target_email, clean_domain, pattern_name, probed_count
                )

                # Persist discovered pattern in DB for future instant hits
                self._record_winning_pattern(clean_domain, pattern_name, company_name, db)

                return {
                    "email": target_email,
                    "pattern": pattern_name,
                    "smtp_status": "DELIVERABLE",
                    "is_deliverable": True,
                    "is_catchall": False,
                    "smtp_code": 250,
                    "mx_host": mx_host,
                    "confidence_score": 95,
                    "discovery_method": "permutation_smtp_handshake_verified",
                    "probes_executed": probed_count,
                    "probe_ms": probe_result.probe_time_ms,
                }
            elif probe_result.smtp_code in (550, 551, 552, 553):
                logger.debug("[PERMUTATION] Mailbox %s does not exist (SMTP %d)", target_email, probe_result.smtp_code)
                continue
            elif probe_result.is_greylisted:
                logger.debug("[PERMUTATION] Host %s greylisted probe for %s", mx_host, target_email)
                break

        return None

    def _get_known_company_pattern(self, domain: str, db: Optional[Session] = None) -> Optional[str]:
        """Retrieves known corporate email pattern from memory cache or DB."""
        if domain in self._pattern_cache:
            return self._pattern_cache[domain]

        close_session = False
        if not db:
            db = SessionLocal()
            close_session = True

        try:
            record = (
                db.query(CompanyEmailPattern)
                .filter(CompanyEmailPattern.domain == domain, CompanyEmailPattern.active == True)
                .order_by(CompanyEmailPattern.verified_example_count.desc(), CompanyEmailPattern.confidence_score.desc())
                .first()
            )
            if record and record.pattern:
                self._pattern_cache[domain] = record.pattern
                return record.pattern
        except Exception as e:
            logger.debug("[PERMUTATION] Error reading pattern cache: %s", e)
        finally:
            if close_session and db:
                db.close()

        return None

    def _record_winning_pattern(
        self, domain: str, pattern: str, company_name: Optional[str] = None, db: Optional[Session] = None
    ):
        """Records or updates a confirmed email pattern in PostgreSQL."""
        self._pattern_cache[domain] = pattern

        close_session = False
        if not db:
            db = SessionLocal()
            close_session = True

        try:
            existing = (
                db.query(CompanyEmailPattern)
                .filter(CompanyEmailPattern.domain == domain, CompanyEmailPattern.pattern == pattern)
                .first()
            )
            if existing:
                existing.verified_example_count = (existing.verified_example_count or 0) + 1
                existing.confidence_score = min(99, (existing.confidence_score or 80) + 5)
                existing.last_verified_at = sqlfunc.now()
            else:
                new_record = CompanyEmailPattern(
                    domain=domain,
                    company_name=company_name,
                    pattern=pattern,
                    confidence_score=90,
                    verified_example_count=1,
                    active=True,
                )
                db.add(new_record)
            db.commit()
        except Exception as e:
            if db:
                db.rollback()
            logger.debug("[PERMUTATION] Error persisting winning pattern: %s", e)
        finally:
            if close_session and db:
                db.close()


# Module-level singleton
email_permutation_engine = EmailPermutationEngine()
