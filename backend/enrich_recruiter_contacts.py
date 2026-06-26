"""
Full-Database Enrichment Pipeline
==================================
Processes all recruiters using keyset pagination, with:
  - Batch checkpointing & resume
  - Update cap with PENDING_UPDATE continuation
  - Per-recruiter nested transactions with retry
  - Idempotency (skip already-processed recruiters)
  - Flattened CSV + JSON summary reports

Usage:
  # Full dry-run inspection:
  python enrich_recruiter_contacts.py --all-recruiters --dry-run --batch-size 500 --checkpoint --export-report --yes

  # Controlled apply (5000-update cap):
  python enrich_recruiter_contacts.py --all-recruiters --apply --max-updates 5000 --batch-size 500 --checkpoint --export-report --yes

  # Resume an interrupted run:
  python enrich_recruiter_contacts.py --resume-run-id full-enrichment-20260624-025000 --apply --max-updates 5000 --batch-size 500 --checkpoint --yes

  # Apply pending proposals from a previous capped run:
  python enrich_recruiter_contacts.py --apply-pending --resume-run-id <RUN_ID> --max-updates 5000 --yes

  # Retry failed records:
  python enrich_recruiter_contacts.py --retry-failed --resume-run-id <RUN_ID> --max-updates 5000 --yes
"""
import os
import sys
import argparse
import csv
import json
import re
import time
import datetime
import subprocess
from typing import List, Dict, Tuple, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

engine = create_engine(os.getenv("DATABASE_URL"), connect_args={"prepare_threshold": None})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from app.models.models import (
    Recruiter, Company, RecruiterEmail, RecruiterPhone, RecruiterLocation,
    CompanyEmailPattern, EnrichmentAudit,
    EnrichmentRun, EnrichmentResult, EnrichmentProposal
)

# ─── Constants ────────────────────────────────────────────────────────────────

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds

OUTCOME_APPLIED_MISSING_EMAIL = "APPLIED_MISSING_EMAIL"
OUTCOME_SKIPPED_ALREADY_CORRECT = "SKIPPED_ALREADY_CORRECT"
OUTCOME_PENDING_REVIEW_EXISTING_EMAIL_MISMATCH = "PENDING_REVIEW_EXISTING_EMAIL_MISMATCH"
OUTCOME_PENDING_REVIEW_LOW_CONFIDENCE = "PENDING_REVIEW_LOW_CONFIDENCE"
OUTCOME_PENDING_REVIEW_SUSPICIOUS_EXISTING_EMAIL = "PENDING_REVIEW_SUSPICIOUS_EXISTING_EMAIL"
OUTCOME_PENDING_REVIEW_NAME_NORMALIZATION = "PENDING_REVIEW_NAME_NORMALIZATION"
OUTCOME_REJECTED_INVALID_GENERATED_EMAIL = "REJECTED_INVALID_GENERATED_EMAIL"
OUTCOME_REJECTED_INSUFFICIENT_EVIDENCE = "REJECTED_INSUFFICIENT_EVIDENCE"
OUTCOME_SKIPPED_NO_VERIFIED_PATTERN = "SKIPPED_NO_VERIFIED_PATTERN"
OUTCOME_SKIPPED_INVALID_NON_PERSON_NAME = "SKIPPED_INVALID_NON_PERSON_NAME"
OUTCOME_FAILED_TECHNICAL_ERROR = "FAILED_TECHNICAL_ERROR"


# ─── Email Pattern Logic ─────────────────────────────────────────────────────

def get_email_pattern(first_name: str, last_name: str, email: str, domain: str) -> str:
    local_part = email.split('@')[0].lower()
    f = first_name.lower()
    l = last_name.lower()
    f1 = f[0] if f else ""
    l1 = l[0] if l else ""

    if f and l:
        if local_part == f"{f}.{l}": return "{first}.{last}"
        if local_part == f"{f}{l}": return "{first}{last}"
        if local_part == f"{f}_{l}": return "{first}_{last}"
        if local_part == f"{f}-{l}": return "{first}-{last}"
        if local_part == f"{f1}{l}": return "{f1}{last}"
        if local_part == f"{f}{l1}": return "{first}{l1}"
        if local_part == f"{l}.{f}": return "{last}.{first}"
        if local_part == f"{l}{f1}": return "{last}{f1}"
        if local_part == f: return "{first}"
        if local_part == l: return "{last}"
    return "unknown"


def generate_email(first_name: str, last_name: str, domain: str, pattern: str) -> str:
    f = first_name.lower()
    l = last_name.lower()
    f1 = f[0] if f else ""
    l1 = l[0] if l else ""
    local = pattern.replace("{first}", f).replace("{last}", l).replace("{f1}", f1).replace("{l1}", l1)
    local = re.sub(r'[^a-z0-9._-]', '', local)
    
    # Strip double dots and trailing/leading punctuation
    local = re.sub(r'\.{2,}', '.', local)
    local = local.strip('._-')
    
    return f"{local}@{domain}"


# ─── Enrichment Worker ───────────────────────────────────────────────────────

class EnrichmentWorker:
    def __init__(self, db: Session, args):
        self.db = db
        self.args = args
        self.run_id: str = ""
        self.run_record: Optional[EnrichmentRun] = None
        self.pattern_cache: Dict[int, Optional[dict]] = {}  # company_id -> pattern_data
        self.batch_start_time = None
        self.run_start_time = None

    # ─── Name parsing ─────────────────────────────────────────────────
    def extract_names(self, full_name: str, email: str = None) -> Tuple[str, str]:
        if email and ("@missing.local" in email or "@invalid.local" in email or "@example.com" in email):
            email = None
        if not full_name:
            return "", ""
        parts = str(full_name).strip().split()
        if len(parts) >= 2:
            return parts[0], parts[-1]
        
        # Recover concatenated name using email
        name_clean = parts[0]
        if email and '@' in email:
            local_part = email.split('@')[0].lower()
            if '.' in local_part:
                eparts = local_part.split('.')
                if len(eparts) == 2:
                    fn, ln = eparts[0], eparts[1]
                    if name_clean.lower() == (fn + ln).lower():
                        return fn.capitalize(), ln.capitalize()
            elif len(local_part) > 1:
                # E.g. jsmith -> j, smith
                fi = local_part[0]
                ln = local_part[1:]
                if name_clean.lower() == (fi + ln).lower():
                    # Can't recover full first name, but we can return fi
                    return fi.capitalize(), ln.capitalize()
                    
        return "", ""

    def is_human_name(self, name: str, company_name: str = "", existing_email: str = "") -> bool:
        if not name:
            return False
        lower_name = name.lower().strip()

        # Exact match rejections for placeholders
        if lower_name in ('unknown', 'no answer', 'n/a', 'na'):
            return False
            
        parts = lower_name.replace('.', ' ').split()
        
        # Strict roles: any single part matching these is an instant rejection
        strict_roles = {'admin', 'info', 'support', 'sales', 'billing', 'contact', 'hr'}
        if any(p in strict_roles for p in parts):
            return False
            
        # Corporate Buzzwords: reject ONLY if the ENTIRE name consists of these non-person words
        company_words = {'global', 'tech', 'group', 'partners', 'systems', 'solutions', 'talent', 'acquisition', 'staffing', 'resourcing', 'developers', 'interactive', 'vm'}
        if all(p in company_words for p in parts):
            return False

        # Catch acronyms + buzzword (e.g., "JCW Resourcing", "HT Group")
        # Reject if at least one word is a buzzword AND all remaining words are 3 characters or fewer
        buzzwords_in_name = [p for p in parts if p in company_words]
        non_buzzwords = [p for p in parts if p not in company_words]
        if buzzwords_in_name and all(len(p) <= 3 for p in non_buzzwords):
            return False

        # Reject initials (like "J. Smith" or single letter first names)
        # UNLESS the existing email already confirms that exact pattern
        # OR it is a middle initial (e.g. "John A. Smith")
        if any(len(p) == 1 for p in parts):
            is_valid_initial = (
                len(parts) >= 2
                and len(parts[0]) > 1
                and sum(1 for p in parts if len(p) == 1) == 1
            )
            if not is_valid_initial:
                corroborated = False
                if existing_email and "@" in existing_email and not any(p in existing_email for p in ["@missing.local", "@invalid.local", "@example.com"]):
                    local_part = existing_email.split('@')[0].lower()
                    name_concat = "".join(parts)
                    local_concat = re.sub(r'[^a-z0-9]', '', local_part)
                    if name_concat == local_concat:
                        corroborated = True
                    else:
                        segments = re.split(r'[._-]', local_part)
                        single_letters = [p for p in parts if len(p) == 1]
                        if all(sl in segments for sl in single_letters):
                            corroborated = True
                if not corroborated:
                    return False

        # Reject if the name exactly/near-exactly matches the company name
        if company_name:
            name_clean = re.sub(r'[^a-z0-9]', '', lower_name)
            comp_clean = re.sub(r'[^a-z0-9]', '', company_name.lower())
            if name_clean and name_clean == comp_clean:
                return False
                
        return True

    # ─── Pattern detection ────────────────────────────────────────────
    def detect_company_patterns(self, company: Company) -> Optional[dict]:
        if company.company_id in self.pattern_cache:
            return self.pattern_cache[company.company_id]

        if not company.website and not company.email_pattern:
            self.pattern_cache[company.company_id] = None
            return None

        recruiters = self.db.query(Recruiter).filter(
            Recruiter.company_id == company.company_id,
            Recruiter.email.isnot(None),
            Recruiter.email.like('%@%')
        ).all()

        domains = {}
        for r in recruiters:
            if r.email and ("@missing.local" in r.email or "@invalid.local" in r.email or "@example.com" in r.email or r.email_status == "invalid"):
                continue
            domain = r.email.split('@')[1].lower()
            domains.setdefault(domain, []).append(r)

        if not domains:
            self.pattern_cache[company.company_id] = None
            return None

        best_domain = max(domains.keys(), key=lambda d: len(domains[d]))
        recs = domains[best_domain]

        patterns = {}
        for r in recs:
            fn, ln = self.extract_names(r.recruiter_name, r.email)
            if not fn or not ln:
                continue
            pat = get_email_pattern(fn, ln, r.email, best_domain)
            if pat != "unknown":
                patterns[pat] = patterns.get(pat, 0) + 1

        if not patterns:
            self.pattern_cache[company.company_id] = None
            return None

        best_pat = max(patterns.keys(), key=lambda p: patterns[p])
        count = patterns[best_pat]
        total = len(recs)
        match_pct = (count / total) * 100

        conf = 0
        if count >= 3 and match_pct >= 90:
            conf = 90
        elif count >= 2 and match_pct >= 75:
            conf = 70
        else:
            conf = 30

        result = {
            "domain": best_domain,
            "pattern": best_pat,
            "count": count,
            "match_pct": match_pct,
            "confidence": conf
        }
        self.pattern_cache[company.company_id] = result
        return result

    # ─── Audit helper ─────────────────────────────────────────────────
    def write_audit(self, r_id, e_type, orig, prop, final, action, reason, conf=0):
        a = EnrichmentAudit(
            recruiter_id=r_id,
            enrichment_type=e_type,
            original_value=str(orig) if orig else None,
            proposed_value=str(prop) if prop else None,
            final_value=str(final) if final else None,
            action=action,
            reason=reason,
            confidence_score=conf,
            run_id=self.run_id
        )
        self.db.add(a)

    # ─── Single-recruiter processing ──────────────────────────────────
    def process_recruiter(self, r: Recruiter) -> str:
        """Process one recruiter. Returns the outcome string."""
        company = r.company
        if not company:
            return OUTCOME_SKIPPED_NO_VERIFIED_PATTERN

        # 1. Name parsing and recovery
        fn, ln = self.extract_names(r.recruiter_name, r.email)
        if not fn or not ln:
            return OUTCOME_SKIPPED_INVALID_NON_PERSON_NAME

        # Re-check human name after extraction
        if not self.is_human_name(f"{fn} {ln}", company.company_name if company else "", r.email):
            return OUTCOME_SKIPPED_INVALID_NON_PERSON_NAME

        is_recovered_name = (" " not in str(r.recruiter_name).strip() and fn and ln)

        # 2. Verified email protection
        if r.email_status == 'verified' and r.email:
            return OUTCOME_SKIPPED_ALREADY_CORRECT

        # 3. Pattern detection
        pattern_data = self.detect_company_patterns(company)
        if not pattern_data:
            return OUTCOME_SKIPPED_NO_VERIFIED_PATTERN

        # Prevent placeholder domains
        domain = pattern_data.get('domain', '')
        if not domain or '[' in domain or ']' in domain or '.' not in domain or domain == 'missing.local':
            return OUTCOME_SKIPPED_NO_VERIFIED_PATTERN

        # 4. Confidence threshold
        conf = pattern_data['confidence']
        if conf < self.args.minimum_confidence:
            return OUTCOME_REJECTED_INSUFFICIENT_EVIDENCE

        # 5. Generate candidate email
        candidate = generate_email(fn, ln, pattern_data['domain'], pattern_data['pattern'])
        local_part = candidate.split('@')[0] if '@' in candidate else ""

        if len(local_part) <= 2:
            return OUTCOME_REJECTED_INSUFFICIENT_EVIDENCE

        # Reject generated local parts that sound like roles
        segments = re.split(r'[._-]', local_part)
        standard_roles = {'admin', 'info', 'support', 'sales', 'billing', 'contact', 'hr', 'careers', 'jobs', 'team', 'hello'}
        if any(seg in standard_roles for seg in segments):
            return OUTCOME_REJECTED_INSUFFICIENT_EVIDENCE
            
        # Dynamic check against the recruiter's specific company name
        company_clean = re.sub(r'[^a-z0-9\s]', '', company.company_name.lower())
        company_words = {w for w in company_clean.split() if len(w) > 2}
        company_concat = company_clean.replace(' ', '')
        local_clean = re.sub(r'[^a-z0-9]', '', local_part)
        
        if local_clean == company_concat or any(seg in company_words for seg in segments):
            return OUTCOME_REJECTED_INSUFFICIENT_EVIDENCE

        # Gather evidence JSON for proposal
        evidence_data = {
            "raw_name": r.recruiter_name,
            "normalized_name_candidate": f"{fn} {ln}" if is_recovered_name else None,
            "company": company.company_name,
            "verified_domain": pattern_data['domain'],
            "pattern": pattern_data['pattern'],
            "evidence_count": pattern_data.get('count', 0),
            "source_record_ids": [],
            "reason": ""
        }

        # 6. Evaluate existing email
        is_placeholder = False
        if r.email and ("@missing.local" in r.email or "@invalid.local" in r.email):
            is_placeholder = True

        if r.email and str(r.email).strip() and not is_placeholder:
            existing = r.email.lower().strip()
            if existing == candidate:
                if is_recovered_name:
                    evidence_data["reason"] = "Recoverable name normalization"
                    self._save_proposal(r, candidate, pattern_data, OUTCOME_PENDING_REVIEW_NAME_NORMALIZATION, evidence_data)
                    return OUTCOME_PENDING_REVIEW_NAME_NORMALIZATION
                return OUTCOME_SKIPPED_ALREADY_CORRECT
            
            is_suspicious = False
            if '@' not in existing:
                is_suspicious = True
                evidence_data["reason"] = "Malformed existing email"
                status = OUTCOME_PENDING_REVIEW_SUSPICIOUS_EXISTING_EMAIL
            else:
                ex_local, ex_domain = existing.split('@', 1)
                if ex_domain != pattern_data['domain']:
                    is_suspicious = True
                    evidence_data["reason"] = "Company-domain mismatch"
                    status = OUTCOME_PENDING_REVIEW_EXISTING_EMAIL_MISMATCH
                elif any(b in ex_local for b in bad_locals):
                    is_suspicious = True
                    evidence_data["reason"] = "Suspicious local part"
                    status = OUTCOME_PENDING_REVIEW_SUSPICIOUS_EXISTING_EMAIL
                else:
                    evidence_data["reason"] = "Existing email mismatch"
                    status = OUTCOME_PENDING_REVIEW_EXISTING_EMAIL_MISMATCH
                
            if is_suspicious and conf >= 80:
                self._save_proposal(r, candidate, pattern_data, status, evidence_data)
                return status
            elif conf >= 80:
                self._save_proposal(r, candidate, pattern_data, status, evidence_data)
                return status
            
            return OUTCOME_SKIPPED_ALREADY_CORRECT

        # 7. Missing email
        if is_recovered_name:
            evidence_data["reason"] = "Recoverable name normalization with missing email"
            self._save_proposal(r, candidate, pattern_data, OUTCOME_PENDING_REVIEW_NAME_NORMALIZATION, evidence_data)
            return OUTCOME_PENDING_REVIEW_NAME_NORMALIZATION

        if conf < 80:
            evidence_data["reason"] = "Strong candidate with insufficient proof for automatic application"
            self._save_proposal(r, candidate, pattern_data, OUTCOME_PENDING_REVIEW_LOW_CONFIDENCE, evidence_data)
            return OUTCOME_PENDING_REVIEW_LOW_CONFIDENCE

        # 8. Duplicate check
        conflicting = self.db.query(Recruiter).filter(
            Recruiter.email == candidate,
            Recruiter.recruiter_id != r.recruiter_id
        ).first()
        if conflicting:
            return OUTCOME_REJECTED_INVALID_GENERATED_EMAIL

        # 9. Check update cap
        if self.args.apply and self.run_record:
            if self.run_record.max_updates and self.run_record.applied_update_count >= self.run_record.max_updates:
                evidence_data["reason"] = "Update cap reached"
                self._save_proposal(r, candidate, pattern_data, OUTCOME_PENDING_REVIEW_EXISTING_EMAIL_MISMATCH, evidence_data)
                return OUTCOME_PENDING_REVIEW_EXISTING_EMAIL_MISMATCH

        # 10. Dry-run: just propose
        if self.args.dry_run:
            evidence_data["reason"] = "Eligible for automatic fill (Dry Run)"
            self._save_proposal(r, candidate, pattern_data, OUTCOME_APPLIED_MISSING_EMAIL, evidence_data)
            return OUTCOME_APPLIED_MISSING_EMAIL

        # 11. Apply mode: actually update
        return self._apply_update(r, candidate, pattern_data, fn, ln, evidence_data)

    def _save_proposal(self, r: Recruiter, candidate: str, pattern_data: dict, status: str, evidence_data: dict = None):
        """Save an enrichment proposal without modifying primary tables."""
        try:
            prop = EnrichmentProposal(
                run_id=self.run_id,
                recruiter_id=r.recruiter_id,
                enrichment_type="email",
                current_value=r.email,
                proposed_value=candidate,
                status=status,
                confidence=pattern_data['confidence'],
                evidence=evidence_data if evidence_data else {"pattern": pattern_data['pattern'], "domain": pattern_data['domain']},
                source="pattern_generation"
            )
            self.db.add(prop)
        except IntegrityError:
            self.db.rollback()
            # Already exists (idempotency)

    def _apply_update(self, r: Recruiter, candidate: str, pattern_data: dict, fn: str = "", ln: str = "", evidence_data: dict = None) -> str:
        """Apply the email update within a nested transaction."""
        conf = pattern_data['confidence']
        status_label = "likely" if conf >= 70 else "inferred"

        try:
            with self.db.begin_nested():
                # Save to structured email table
                new_email = RecruiterEmail(
                    recruiter_id=r.recruiter_id,
                    email=candidate,
                    status=status_label,
                    confidence_score=conf,
                    source="pattern_generation",
                    is_generated=True,
                    is_primary=True
                )
                self.db.add(new_email)

                orig_email = r.email
                r.email = candidate
                r.email_status = status_label
                r.email_confidence = conf

                self.write_audit(r.recruiter_id, "email", orig_email, candidate, candidate, "applied", "Pattern generation", conf)

                # Save proposal as APPLIED
                prop = EnrichmentProposal(
                    run_id=self.run_id,
                    recruiter_id=r.recruiter_id,
                    enrichment_type="email",
                    current_value=orig_email,
                    proposed_value=candidate,
                    status="APPLIED_MISSING_EMAIL",
                    confidence=conf,
                    evidence=evidence_data if evidence_data else {"pattern": pattern_data['pattern'], "domain": pattern_data['domain']},
                    source="pattern_generation",
                    applied_at=datetime.datetime.utcnow()
                )
                self.db.add(prop)

            return OUTCOME_APPLIED

        except IntegrityError:
            self.db.rollback()
            return OUTCOME_REJECTED_DUPLICATE
        except Exception:
            self.db.rollback()
            return OUTCOME_FAILED

    # ─── Backup ───────────────────────────────────────────────────────
    def create_backup(self) -> str:
        """Create a pg_dump backup. Returns backup path or raises."""
        backup_dir = os.path.join("C:\\TalentOpsAI\\backups\\enrichment", self.run_id)
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, "dump.backup")

        db_url = os.getenv("DATABASE_URL", "")
        # Parse connection string for pg_dump
        # Expected: postgresql+psycopg://user:pass@host:port/dbname
        import urllib.parse
        parts = urllib.parse.urlparse(db_url.replace("postgresql+psycopg://", "postgresql://"))
        pg_host = parts.hostname or "localhost"
        pg_port = str(parts.port or 5432)
        pg_user = parts.username or "postgres"
        pg_pass = parts.password or ""
        pg_db = parts.path.lstrip("/") or "postgres"

        env = os.environ.copy()
        env["PGPASSWORD"] = pg_pass

        tables = [
            "recruiters", "recruiter_emails", "recruiter_phones",
            "recruiter_locations", "companies", "company_email_patterns",
            "enrichment_audit"
        ]
        cmd = [
            "pg_dump", "-Fc",
            "-h", pg_host, "-p", pg_port, "-U", pg_user, "-d", pg_db
        ]
        for t in tables:
            cmd.extend(["-t", t])
        cmd.extend(["-f", backup_path])

        print(f"Creating backup: {backup_path}")
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"pg_dump failed (exit {result.returncode}): {result.stderr[:500]}")

        size = os.path.getsize(backup_path)
        if size == 0:
            raise RuntimeError("pg_dump produced an empty file")

        print(f"Backup complete: {size:,} bytes")
        return backup_path

    # ─── Run lifecycle ────────────────────────────────────────────────
    def initialize_run(self):
        """Create or resume the enrichment run record."""
        now = datetime.datetime.utcnow()

        if self.args.resume_run_id:
            self.run_id = self.args.resume_run_id
            self.run_record = self.db.query(EnrichmentRun).filter_by(run_id=self.run_id).first()
            if not self.run_record:
                print(f"ERROR: Run ID '{self.run_id}' not found in database.")
                sys.exit(1)
            self.run_record.resumed_at = now
            self.run_record.status = "RUNNING" if self.args.apply else "DRY_RUN_RUNNING"
            self.db.commit()
            print(f"Resumed run: {self.run_id} (last_processed_id={self.run_record.last_processed_id})")
            return

        # New run
        self.run_id = f"full-enrichment-{now.strftime('%Y%m%d-%H%M%S')}"
        mode = "APPLY" if self.args.apply else "DRY_RUN"

        # Count total recruiters
        total = self.db.query(func.count(Recruiter.recruiter_id)).scalar() or 0

        # Create backup if applying
        backup_path = None
        if self.args.apply and not self.args.apply_pending and not self.args.retry_failed:
            try:
                backup_path = self.create_backup()
            except Exception as e:
                print(f"FATAL: Backup failed – {e}")
                print("Cannot proceed with apply mode without a valid backup.")
                sys.exit(1)

        config = {
            "batch_size": self.args.batch_size,
            "max_updates": self.args.max_updates,
            "minimum_confidence": self.args.minimum_confidence,
            "all_recruiters": self.args.all_recruiters,
            "company_filter": self.args.company,
        }

        self.run_record = EnrichmentRun(
            run_id=self.run_id,
            mode=mode,
            status="PLANNED",
            started_at=now,
            total_recruiters=total,
            total_eligible=total,
            batch_size=self.args.batch_size,
            max_updates=self.args.max_updates,
            backup_path=backup_path,
            configuration_json=config,
            last_processed_id=self.args.start_after_id or 0,
            current_batch=0
        )
        self.db.add(self.run_record)
        self.db.commit()

        print(f"Created run: {self.run_id}")
        print(f"Total recruiters: {total:,}")
        print(f"Mode: {mode}")
        if backup_path:
            print(f"Backup: {backup_path}")

    def verify_consistency(self):
        """Check for gaps or duplicates before checkpoint."""
        rr = self.run_record
        if not rr.last_processed_id: return
        
        dupes = self.db.execute(text("""
            SELECT recruiter_id, COUNT(*)
            FROM enrichment_results
            WHERE run_id = :run_id AND recruiter_id <= :lid
            GROUP BY recruiter_id HAVING COUNT(*) > 1
        """), {"run_id": self.run_id, "lid": rr.last_processed_id}).fetchall()
        
        if dupes:
            print(f"WARNING: Found {len(dupes)} duplicates before checkpoint. Cleaning up...")
            for dup in dupes:
                self.db.execute(text("DELETE FROM enrichment_results WHERE run_id = :run_id AND recruiter_id = :rid"), {"run_id": self.run_id, "rid": dup[0]})
            self.db.commit()

        # Missing check (optional but good)
        # Assuming sequential recruiter_ids, but actually just re-process missing if needed.
        # But keyset pagination inherently skips nothing unless the loop breaks.
        
        # Clean up partial batch after checkpoint
        partial = self.db.execute(text("SELECT COUNT(*) FROM enrichment_results WHERE run_id = :run_id AND recruiter_id > :lid"), {"run_id": self.run_id, "lid": rr.last_processed_id}).scalar()
        if partial > 0:
            print(f"INFO: Cleaning up {partial} results from interrupted partial batch after ID {rr.last_processed_id}...")
            self.db.execute(text("DELETE FROM enrichment_results WHERE run_id = :run_id AND recruiter_id > :lid"), {"run_id": self.run_id, "lid": rr.last_processed_id})
            self.db.execute(text("DELETE FROM enrichment_proposals WHERE run_id = :run_id AND recruiter_id > :lid"), {"run_id": self.run_id, "lid": rr.last_processed_id})
            self.db.commit()

    # ─── Apply-pending mode ───────────────────────────────────────────
    def run_apply_pending(self):
        """Apply proposals that were saved as PENDING_UPDATE."""
        print(f"\n=== APPLY-PENDING MODE for run {self.run_id} ===")
        pending = self.db.query(EnrichmentProposal).filter(
            EnrichmentProposal.run_id == self.run_id,
            EnrichmentProposal.status == "PENDING_UPDATE"
        ).order_by(EnrichmentProposal.recruiter_id).all()

        print(f"Found {len(pending)} pending proposals")
        applied = 0
        rejected = 0
        max_u = self.args.max_updates or len(pending)

        for prop in pending:
            if applied >= max_u:
                print(f"Update cap reached ({max_u}). Remaining proposals stay PENDING_UPDATE.")
                break

            recruiter = self.db.query(Recruiter).filter_by(recruiter_id=prop.recruiter_id).first()
            if not recruiter:
                prop.status = "REJECTED"
                prop.rejection_reason = "Recruiter not found"
                rejected += 1
                continue

            # Re-validate: duplicate check
            conflicting = self.db.query(Recruiter).filter(
                Recruiter.email == prop.proposed_value,
                Recruiter.recruiter_id != recruiter.recruiter_id
            ).first()
            if conflicting:
                prop.status = "REJECTED"
                prop.rejection_reason = f"Duplicate: already assigned to recruiter {conflicting.recruiter_id}"
                rejected += 1
                continue

            # Apply
            try:
                with self.db.begin_nested():
                    conf = prop.confidence or 0
                    status_label = "likely" if conf >= 70 else "inferred"

                    new_email = RecruiterEmail(
                        recruiter_id=recruiter.recruiter_id,
                        email=prop.proposed_value,
                        status=status_label,
                        confidence_score=conf,
                        source="pattern_generation",
                        is_generated=True,
                        is_primary=True
                    )
                    self.db.add(new_email)

                    orig_email = recruiter.email
                    recruiter.email = prop.proposed_value
                    recruiter.email_status = status_label
                    recruiter.email_confidence = conf

                    self.write_audit(recruiter.recruiter_id, "email", orig_email, prop.proposed_value, prop.proposed_value, "applied", "Pending apply", conf)

                    prop.status = "APPLIED"
                    prop.applied_at = datetime.datetime.utcnow()

                self.db.commit()
                applied += 1
                self.run_record.applied_update_count += 1
                self.run_record.pending_update_count = max(0, self.run_record.pending_update_count - 1)

            except Exception as e:
                self.db.rollback()
                prop.status = "REJECTED"
                prop.rejection_reason = str(e)[:500]
                rejected += 1

        self.db.commit()
        remaining = self.db.query(func.count(EnrichmentProposal.id)).filter(
            EnrichmentProposal.run_id == self.run_id,
            EnrichmentProposal.status == "PENDING_UPDATE"
        ).scalar() or 0

        self.run_record.pending_update_count = remaining
        if remaining == 0:
            self.run_record.status = "COMPLETED"
            self.run_record.completed_at = datetime.datetime.utcnow()
        self.db.commit()

        print(f"Applied: {applied} | Rejected: {rejected} | Remaining pending: {remaining}")

    # ─── Retry-failed mode ────────────────────────────────────────────
    def run_retry_failed(self):
        """Re-process recruiters that had failures."""
        print(f"\n=== RETRY-FAILED MODE for run {self.run_id} ===")
        failed_results = self.db.query(EnrichmentResult).filter(
            EnrichmentResult.run_id == self.run_id,
            EnrichmentResult.failure_category.isnot(None)
        ).order_by(EnrichmentResult.recruiter_id).all()

        print(f"Found {len(failed_results)} failed results to retry")
        retried = 0
        for er in failed_results:
            recruiter = self.db.query(Recruiter).filter_by(recruiter_id=er.recruiter_id).first()
            if not recruiter:
                continue
            # Delete old result to allow re-processing
            self.db.delete(er)
            self.db.commit()
            outcome = self.process_recruiter(recruiter)
            self._save_result(recruiter, outcome)
            self.db.commit()
            retried += 1

        print(f"Retried: {retried}")

    # ─── Save result row ──────────────────────────────────────────────
    def _save_result(self, r: Recruiter, outcome: str, error: str = None):
        """Write an enrichment_results row for this recruiter."""
        old_vals = {"email": r.email, "email_status": r.email_status}

        result = EnrichmentResult(
            run_id=self.run_id,
            recruiter_id=r.recruiter_id,
            company_id=r.company_id,
            email_outcome=outcome,
            phone_outcome="SKIPPED",
            location_outcome="SKIPPED",
            overall_outcome=outcome,
            old_values_json=old_vals,
            processing_started_at=datetime.datetime.utcnow(),
            processing_completed_at=datetime.datetime.utcnow(),
            failure_category="retryable" if outcome == OUTCOME_FAILED_TECHNICAL_ERROR else None,
            rejection_reason=error
        )
        try:
            self.db.add(result)
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            # Already processed (idempotency) – update existing
            existing = self.db.query(EnrichmentResult).filter_by(
                run_id=self.run_id, recruiter_id=r.recruiter_id
            ).first()
            if existing and (existing.overall_outcome == OUTCOME_FAILED_TECHNICAL_ERROR or existing.overall_outcome.startswith("PENDING_REVIEW_")):
                existing.overall_outcome = outcome
                existing.processing_completed_at = datetime.datetime.utcnow()
                existing.failure_category = None if outcome != OUTCOME_FAILED_TECHNICAL_ERROR else "retryable"

    # ─── Update run counters ──────────────────────────────────────────
    def _update_counters(self, outcome: str):
        rr = self.run_record
        rr.inspected_count += 1
        if outcome == OUTCOME_APPLIED_MISSING_EMAIL:
            rr.applied_update_count += 1
        elif outcome.startswith("PENDING_REVIEW_"):
            rr.pending_update_count += 1
        elif outcome.startswith("REJECTED_"):
            rr.rejected_count += 1
        elif outcome.startswith("SKIPPED_"):
            rr.skipped_count += 1
        elif outcome == OUTCOME_FAILED_TECHNICAL_ERROR:
            rr.failed_count += 1

    # ─── Batch progress output ────────────────────────────────────────
    def print_progress(self, batch_num: int, batch_ids: str, batch_count: int):
        rr = self.run_record
        elapsed = time.time() - self.run_start_time
        total = rr.total_recruiters or 1
        inspected = rr.inspected_count
        pct = (inspected / total) * 100 if total else 0

        if inspected > 0:
            rate = elapsed / inspected
            remaining = (total - inspected) * rate
            eta = datetime.timedelta(seconds=int(remaining))
        else:
            eta = "N/A"

        elapsed_str = datetime.timedelta(seconds=int(elapsed))
        max_u_str = f"{rr.max_updates:,}" if rr.max_updates else "unlimited"

        print(f"\nRun ID: {self.run_id}")
        print(f"Status: {rr.status}")
        print(f"Batch: {batch_num}  (Recruiter IDs {batch_ids})")
        print(f"Inspected this batch: {batch_count}  |  Inspected total: {inspected:,} / {total:,}  ({pct:.1f}%)")
        print(f"Applied updates total: {rr.applied_update_count:,} / {max_u_str}")
        print(f"Pending proposals: {rr.pending_update_count:,}")
        print(f"Rejected: {rr.rejected_count:,} | Skipped: {rr.skipped_count:,} | Failed: {rr.failed_count}")
        print(f"Last processed ID: {rr.last_processed_id}")
        print(f"Elapsed: {elapsed_str}  |  ETA: {eta}")

        if rr.max_updates and rr.applied_update_count >= rr.max_updates:
            print("*** UPDATE CAP REACHED – further valid proposals saved as PENDING_REVIEW ***")

    # ─── CSV / JSON report export ─────────────────────────────────────
    def export_reports(self):
        """Generate flattened CSV reports and JSON summary."""
        report_dir = os.path.join("C:\\TalentOpsAI\\reports\\enrichment", self.run_id)
        os.makedirs(report_dir, exist_ok=True)

        results = self.db.query(EnrichmentResult).filter_by(run_id=self.run_id).all()

        # Group by outcome
        groups = {}
        for r in results:
            groups.setdefault(r.overall_outcome, []).append(r)

        csv_fields = [
            "recruiter_id", "company_id", "email_outcome", "phone_outcome",
            "location_outcome", "overall_outcome", "rejection_reason"
        ]

        # All outcomes CSV
        all_path = os.path.join(report_dir, f"recruiter_outcomes_{self.run_id}.csv")
        with open(all_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=csv_fields)
            writer.writeheader()
            for r in results:
                writer.writerow({fld: getattr(r, fld, '') for fld in csv_fields})

        # Per-outcome CSVs
        outcome_files = {
            OUTCOME_APPLIED_MISSING_EMAIL: "applied_updates",
            OUTCOME_PENDING_REVIEW_EXISTING_EMAIL_MISMATCH: "pending_email_mismatch",
            OUTCOME_PENDING_REVIEW_LOW_CONFIDENCE: "pending_low_confidence",
            OUTCOME_PENDING_REVIEW_SUSPICIOUS_EXISTING_EMAIL: "pending_suspicious_email",
            OUTCOME_PENDING_REVIEW_NAME_NORMALIZATION: "pending_name_normalization",
            OUTCOME_REJECTED_INVALID_GENERATED_EMAIL: "rejected_invalid_generated",
            OUTCOME_REJECTED_INSUFFICIENT_EVIDENCE: "rejected_insufficient_evidence",
            OUTCOME_FAILED_TECHNICAL_ERROR: "failed"
        }
        for outcome_key, prefix in outcome_files.items():
            if outcome_key in groups:
                path = os.path.join(report_dir, f"{prefix}_{self.run_id}.csv")
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=csv_fields)
                    writer.writeheader()
                    for r in groups[outcome_key]:
                        writer.writerow({fld: getattr(r, fld, '') for fld in csv_fields})

        # JSON summary
        rr = self.run_record
        summary = {
            "run_id": self.run_id,
            "mode": rr.mode,
            "status": rr.status,
            "total_recruiters": rr.total_recruiters,
            "inspected_count": rr.inspected_count,
            "applied_update_count": rr.applied_update_count,
            "pending_update_count": rr.pending_update_count,
            "rejected_count": rr.rejected_count,
            "skipped_count": rr.skipped_count,
            "failed_count": rr.failed_count,
            "manual_review_count": rr.manual_review_count,
            "started_at": str(rr.started_at),
            "completed_at": str(rr.completed_at) if rr.completed_at else None,
            "backup_path": rr.backup_path,
            "report_path": report_dir,
            "outcome_breakdown": {k: len(v) for k, v in groups.items()}
        }
        summary_path = os.path.join(report_dir, f"summary_{self.run_id}.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

        self.run_record.report_path = report_dir
        self.db.commit()
        print(f"\nReports exported to: {report_dir}")
        return report_dir

    # ─── Batch verification ───────────────────────────────────────────
    def verify_batch(self, prev_last_id: int, batch_last_id: int) -> bool:
        """Run verification queries after each batch commit."""
        # Check for duplicate recruiter entries in this batch
        dupes = self.db.execute(text("""
            SELECT recruiter_id, COUNT(*) as cnt
            FROM enrichment_results
            WHERE run_id = :run_id AND recruiter_id > :prev AND recruiter_id <= :curr
            GROUP BY recruiter_id
            HAVING COUNT(*) <> 1
        """), {"run_id": self.run_id, "prev": prev_last_id, "curr": batch_last_id}).fetchall()

        if dupes:
            print(f"  BATCH VERIFICATION FAILED: Duplicate result rows for recruiter_ids: {[d[0] for d in dupes]}")
            return False

        print("  Batch verification: PASSED")
        return True

    # ─── Main run loop ────────────────────────────────────────────────
    def run(self):
        """Main entry point."""
        self.run_start_time = time.time()

        # Handle special modes
        if self.args.apply_pending:
            self.initialize_run()
            self.run_apply_pending()
            if self.args.export_report:
                self.export_reports()
            return

        if self.args.retry_failed:
            self.initialize_run()
            self.run_retry_failed()
            if self.args.export_report:
                self.export_reports()
            return

        # Normal inspection / apply flow
        self.initialize_run()
        self.verify_consistency()

        rr = self.run_record
        rr.status = "RUNNING" if self.args.apply else "DRY_RUN_RUNNING"
        self.db.commit()

        last_id = rr.last_processed_id or 0
        batch_size = self.args.batch_size
        batch_num = rr.current_batch or 0

        print(f"\nStarting from recruiter_id > {last_id}, batch_size={batch_size}")

        # Build base query
        from sqlalchemy import or_, not_
        base_query = self.db.query(Recruiter)
        
        if not self.args.all_recruiters:
            if self.args.company:
                # Filter by company name
                company_ids = [c.company_id for c in
                               self.db.query(Company.company_id).filter(Company.company_name.ilike(f"%{self.args.company}%")).all()]
                base_query = base_query.filter(Recruiter.company_id.in_(company_ids))
            else:
                # Target only records needing attention
                base_query = base_query.filter(
                    or_(
                        Recruiter.email == None,
                        Recruiter.email == '',
                        not_(Recruiter.email.like('%@%')),
                        not_(Recruiter.recruiter_name.like('% %')),
                        Recruiter.email.ilike('admin@%'),
                        Recruiter.email.ilike('info@%')
                    )
                )

        while True:
            try:
                batch = (base_query
                         .filter(Recruiter.recruiter_id > last_id)
                         .order_by(Recruiter.recruiter_id)
                         .limit(batch_size)
                         .all())

                if not batch:
                    break

                batch_num += 1
                prev_last_id = last_id
                batch_count = 0

                for recruiter in batch:
                    # Idempotency: skip if already processed in this run
                    existing = self.db.query(EnrichmentResult).filter_by(
                        run_id=self.run_id, recruiter_id=recruiter.recruiter_id
                    ).first()
                    if existing and existing.overall_outcome not in (OUTCOME_FAILED_TECHNICAL_ERROR,):
                        last_id = recruiter.recruiter_id
                        continue

                    # Process with retry
                    outcome = OUTCOME_FAILED_TECHNICAL_ERROR
                    error_msg = None
                    for attempt in range(MAX_RETRIES):
                        try:
                            outcome = self.process_recruiter(recruiter)
                            break
                        except Exception as e:
                            error_msg = str(e)[:500]
                            if attempt < MAX_RETRIES - 1:
                                time.sleep(RETRY_BACKOFF_BASE ** attempt)
                            else:
                                outcome = OUTCOME_FAILED_TECHNICAL_ERROR

                    # Save result
                    self._save_result(recruiter, outcome, error_msg)
                    self._update_counters(outcome)
                    batch_count += 1
                    last_id = recruiter.recruiter_id

                # Commit batch
                rr.last_processed_id = last_id
                rr.current_batch = batch_num
                self.db.commit()

                # Verify batch
                first_id = batch[0].recruiter_id if batch else prev_last_id
                batch_id_str = f"{first_id}-{last_id}"
                self.verify_batch(prev_last_id, last_id)

                # Print progress
                self.print_progress(batch_num, batch_id_str, batch_count)

                # Checkpoint
                if self.args.checkpoint:
                    rr.updated_at = datetime.datetime.utcnow()
                    self.db.commit()
            except SQLAlchemyError as e:
                print(f"FATAL BATCH ERROR: {e}")
                print("Connection lost or transaction failed. Reconnecting and backing off...")
                try:
                    self.db.rollback()
                    self.db.close()
                except Exception:
                    pass
                
                # Reconnection loop
                for reconnect_attempt in range(1, 10):
                    time.sleep(10 * reconnect_attempt) # Progressive cooldown
                    try:
                        self.db = SessionLocal() # Fresh session
                        self.run_record = self.db.query(EnrichmentRun).filter_by(run_id=self.run_id).first()
                        if self.run_record:
                            break
                    except Exception as re_err:
                        print(f"Reconnection attempt {reconnect_attempt} failed: {re_err}")
                else:
                    print("Failed to reconnect after multiple attempts. Exiting.")
                    sys.exit(1)
                
                rr = self.run_record
                # Revert last_id to the last properly committed checkpoint
                last_id = rr.last_processed_id or 0
                batch_num = rr.current_batch or 0
                print(f"Retrying batch from checkpoint ID {last_id}...")
                continue

        # Finalize
        if rr.max_updates and rr.applied_update_count >= rr.max_updates and rr.pending_update_count > 0:
            rr.status = "INSPECTION_COMPLETE_UPDATE_CAP_REACHED"
        elif self.args.dry_run:
            rr.status = "INSPECTION_COMPLETE"
        else:
            rr.status = "COMPLETED"

        rr.completed_at = datetime.datetime.utcnow()
        self.db.commit()

        # Print final summary
        print("\n" + "=" * 60)
        print("FINAL RUN SUMMARY")
        print("=" * 60)
        print(f"Run ID:          {self.run_id}")
        print(f"Status:          {rr.status}")
        print(f"Inspected:       {rr.inspected_count:,}")
        print(f"Applied:         {rr.applied_update_count:,}")
        print(f"Pending:         {rr.pending_update_count:,}")
        print(f"Rejected:        {rr.rejected_count:,}")
        print(f"Skipped:         {rr.skipped_count:,}")
        print(f"Failed:          {rr.failed_count:,}")
        print(f"Manual review:   {rr.manual_review_count}")
        total_elapsed = time.time() - self.run_start_time
        print(f"Total time:      {datetime.timedelta(seconds=int(total_elapsed))}")
        print("=" * 60)

        # Export reports
        if self.args.export_report:
            self.export_reports()


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Full-Database Enrichment Pipeline")

    # Scope
    parser.add_argument("--all-recruiters", action="store_true", help="Process every recruiter (ignores company filter)")
    parser.add_argument("--company", help="Filter by company name")

    # Batch & pagination
    parser.add_argument("--batch-size", type=int, default=500, help="Records per DB transaction batch")
    parser.add_argument("--start-after-id", type=int, default=0, help="Start keyset pagination after this recruiter_id")

    # Resume & checkpoint
    parser.add_argument("--resume-run-id", help="Resume an existing run from its checkpoint")
    parser.add_argument("--checkpoint", action="store_true", help="Persist checkpoint after each batch")

    # Update control
    parser.add_argument("--max-updates", type=int, default=None, help="Cap on applied modifications per run segment")
    parser.add_argument("--minimum-confidence", type=int, default=70, help="Minimum pattern confidence to apply")

    # Modes
    parser.add_argument("--dry-run", action="store_true", help="Inspection only – no DB changes to primary tables")
    parser.add_argument("--apply", action="store_true", help="Perform safe updates (subject to cap)")
    parser.add_argument("--apply-pending", action="store_true", help="Apply PENDING_UPDATE proposals from a previous run")
    parser.add_argument("--retry-failed", action="store_true", help="Re-process records with failure_category != NULL")

    # Output
    parser.add_argument("--export-report", action="store_true", help="Generate CSV and JSON reports at end of run")
    parser.add_argument("--verbose", action="store_true", help="Detailed stdout")
    parser.add_argument("--yes", action="store_true", help="Skip interactive prompts")

    # Legacy compatibility
    parser.add_argument("--company-limit", type=int, default=None, help="(Legacy) Limit number of companies")
    parser.add_argument("--recruiter-limit", type=int, default=None, help="(Legacy) Limit number of recruiters")

    args = parser.parse_args()

    # Validation
    mode_count = sum([args.dry_run, args.apply, args.apply_pending, args.retry_failed])
    if mode_count == 0:
        print("ERROR: Must specify one of --dry-run, --apply, --apply-pending, or --retry-failed")
        sys.exit(1)
    if mode_count > 1 and not (args.apply and args.apply_pending):
        # Allow --apply with --apply-pending as a valid combo
        if not (args.apply and args.retry_failed):
            print("ERROR: Conflicting mode flags. Use only one of --dry-run, --apply, --apply-pending, --retry-failed")
            sys.exit(1)

    if (args.apply_pending or args.retry_failed) and not args.resume_run_id:
        print("ERROR: --apply-pending and --retry-failed require --resume-run-id")
        sys.exit(1)

    if args.apply and not args.yes and not args.company and not args.resume_run_id:
        if args.all_recruiters:
            ans = input("WARNING: Full-database APPLY mode. Continue? (y/N): ")
            if ans.lower() != 'y':
                print("Aborting.")
                sys.exit(0)

    db = SessionLocal()
    try:
        worker = EnrichmentWorker(db, args)
        worker.run()
    except KeyboardInterrupt:
        print("\nInterrupted. Run can be resumed with --resume-run-id")
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
