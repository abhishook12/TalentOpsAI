"""
db_auto_enricher.py — Non-Destructive Database Auto-Enricher & Healer.
Safely bridges external web intelligence from discovery_staging into the master catalog:
- Heals & enriches existing recruiters without overwriting valid data
- Runs Port 25 SMTP handshakes to verify or flag deliverability
- Promotes verified fresh talent with complete provenance attribution
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import SessionLocal
from ..models.staging_models import DiscoveryStaging
from ..models.models import Recruiter, Company
from ..services.smtp_prober import smtp_prober

logger = logging.getLogger("talentops.db_auto_enricher")


class DatabaseAutoEnricher:
    """
    Safely reconciles staged web intelligence into PostgreSQL master tables.
    Non-destructive: Never overwrites existing populated fields; only fills blanks.
    """

    def __init__(self):
        self.stats = {
            "total_processed": 0,
            "existing_enriched": 0,
            "new_promoted": 0,
            "emails_smtp_verified": 0,
            "bounced_emails_flagged": 0,
            "duplicates_skipped": 0,
        }

    def reconcile_staging_batch(self, db: Session, limit: int = 50) -> Dict[str, Any]:
        """
        Processes pending staged observations and applies non-destructive enrichment.
        """
        pending_records = db.query(DiscoveryStaging).filter(
            DiscoveryStaging.processing_status == "pending"
        ).order_by(DiscoveryStaging.id.asc()).limit(limit).all()

        results = {
            "processed_count": len(pending_records),
            "enriched_existing": 0,
            "promoted_new": 0,
            "skipped": 0,
        }
        promoted_records_for_parquet = []

        for staged in pending_records:
            self.stats["total_processed"] += 1
            raw_name = (staged.raw_name or "").strip()
            raw_email = (staged.raw_email or "").strip().lower()
            raw_company = (staged.raw_company or "").strip()

            if not raw_name or len(raw_name.split()) < 2:
                staged.processing_status = "rejected"
                staged.decision = "REJECTED_INVALID_NAME"
                staged.decision_reason = "Name missing or insufficient tokens"
                results["skipped"] += 1
                continue

            # Resolve or lookup company
            company = None
            if raw_company:
                company = db.query(Company).filter(
                    func.lower(Company.company_name) == raw_company.lower()
                ).first()

            # Check if this recruiter already exists in the master catalog
            existing_recruiter = None
            if raw_email:
                existing_recruiter = db.query(Recruiter).filter(
                    func.lower(Recruiter.email) == raw_email
                ).first()

            if not existing_recruiter and company:
                existing_recruiter = db.query(Recruiter).filter(
                    func.lower(Recruiter.recruiter_name) == raw_name.lower(),
                    Recruiter.company_id == company.company_id
                ).first()

            if existing_recruiter:
                # ── ENRICHMENT MODE (NON-DESTRUCTIVE) ──────────────────────────
                fields_enriched = []

                if not existing_recruiter.title and staged.raw_title:
                    existing_recruiter.title = staged.raw_title
                    fields_enriched.append("title")

                if not existing_recruiter.phone and staged.raw_phone:
                    existing_recruiter.phone = staged.raw_phone
                    fields_enriched.append("phone")

                if not existing_recruiter.linkedin and staged.raw_linkedin:
                    existing_recruiter.linkedin = staged.raw_linkedin
                    fields_enriched.append("linkedin")

                if staged.raw_location and not existing_recruiter.state:
                    # Check for 2-letter state code
                    st_m = re.search(r"\b([A-Z]{2})\b", staged.raw_location)
                    if st_m:
                        existing_recruiter.state = st_m.group(1)
                        fields_enriched.append("state")

                # Verify email deliverability if unverified
                if existing_recruiter.email and getattr(existing_recruiter, "email_status", None) != "SMTP_VERIFIED":
                    try:
                        probe = smtp_prober.probe_mailbox(existing_recruiter.email)
                        if probe.smtp_code == 250:
                            existing_recruiter.email_status = "SMTP_VERIFIED"
                            existing_recruiter.email_confidence = 100
                            self.stats["emails_smtp_verified"] += 1
                            fields_enriched.append("email_smtp_verified")
                        elif probe.smtp_code == 550:
                            existing_recruiter.email_status = "BOUNCED"
                            self.stats["bounced_emails_flagged"] += 1
                            fields_enriched.append("email_bounced")
                    except Exception as e:
                        logger.debug("SMTP probe skipped during enrichment: %s", e)

                staged.processing_status = "enriched"
                staged.decision = "ENRICHED_EXISTING"
                staged.decision_reason = f"Enriched existing recruiter #{existing_recruiter.recruiter_id}: {', '.join(fields_enriched) if fields_enriched else 'Confirmed existing'}"
                staged.processed_at = datetime.utcnow()

                self.stats["existing_enriched"] += 1
                results["enriched_existing"] += 1

            else:
                # ── PROMOTION MODE (NEW CONTACT) ──────────────────────────────
                # Ensure company exists or create lightweight company shell
                if not company and raw_company:
                    clean_dom = ""
                    if raw_email and "@" in raw_email:
                        clean_dom = raw_email.split("@")[1]
                    company = Company(
                        company_name=raw_company,
                        normalized_name=raw_company.lower().strip(),
                        primary_domain=clean_dom,
                    )
                    db.add(company)
                    db.flush()

                # Live Port 25 SMTP deliverability check before promotion
                email_status = "PATTERN_PREDICTED"
                confidence = staged.quality_score or 75

                if raw_email:
                    try:
                        probe = smtp_prober.probe_mailbox(raw_email)
                        if probe.smtp_code == 250:
                            email_status = "SMTP_VERIFIED"
                            confidence = 100
                            self.stats["emails_smtp_verified"] += 1
                        elif probe.smtp_code == 550:
                            email_status = "BOUNCED"
                    except Exception:
                        pass

                raw_loc = (staged.raw_location or "").strip()
                state_abbr = None
                if raw_loc:
                    try:
                        from ..utils.state_mapper import extract_state_detailed
                        state_abbr, _ = extract_state_detailed(raw_loc)
                    except Exception:
                        pass

                new_recruiter = Recruiter(
                    recruiter_name=raw_name,
                    title=staged.raw_title or "Talent Acquisition Specialist",
                    company_id=company.company_id if company else None,
                    email=raw_email if raw_email else f"{raw_name.lower().replace(' ', '.')}@{company.primary_domain or 'unknown.com'}",
                    phone=staged.raw_phone,
                    linkedin=staged.raw_linkedin,
                    location=raw_loc or None,
                    state=state_abbr,
                    email_status=email_status,
                    email_confidence=confidence,
                    data_source=f"web_intelligence:{staged.extraction_source}",
                    notes=f"Auto-harvested via {staged.extraction_source} on {datetime.utcnow().strftime('%Y-%m-%d')}",
                    email_generated=True if staged.extraction_source in ("search_xray", "web_harvest") else False,
                )
                db.add(new_recruiter)
                db.flush()

                staged.processing_status = "promoted"
                staged.decision = "PROMOTED_NEW"
                staged.decision_reason = f"Promoted to master catalog as Recruiter #{new_recruiter.recruiter_id} (Status: {email_status})"
                staged.processed_at = datetime.utcnow()

                self.stats["new_promoted"] += 1
                results["promoted_new"] += 1

                promoted_dict = {
                    "recruiter_id": new_recruiter.recruiter_id,
                    "recruiter_name": new_recruiter.recruiter_name,
                    "title": new_recruiter.title,
                    "company_id": new_recruiter.company_id,
                    "email": new_recruiter.email,
                    "phone": new_recruiter.phone,
                    "linkedin": new_recruiter.linkedin,
                    "location": raw_loc or None,
                    "state": state_abbr,
                    "email_status": new_recruiter.email_status,
                    "email_confidence": new_recruiter.email_confidence,
                    "data_source": new_recruiter.data_source,
                    "notes": new_recruiter.notes,
                    "quality_score": confidence,
                    "completeness_score": 85,
                    "is_active": True,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }
                promoted_records_for_parquet.append(promoted_dict)

        db.commit()

        if promoted_records_for_parquet:
            try:
                from .parquet_writer import parquet_writer
                parquet_writer.append_records(promoted_records_for_parquet)
                logger.info("[DB_AUTO_ENRICHER] Parquet Dual-Sync: Appended %d promoted recruiters to DuckDB Parquet", len(promoted_records_for_parquet))
            except Exception as pq_err:
                logger.warning("[DB_AUTO_ENRICHER] Parquet dual-sync warning: %s", pq_err)

        logger.info("[DB_AUTO_ENRICHER] Reconciled batch: %d processed, %d enriched, %d promoted",
                    results["processed_count"], results["enriched_existing"], results["promoted_new"])
        return results

    def autonomous_sync_parquet(self, db: Session) -> int:
        """
        Autonomous self-healing Parquet synchronizer.
        Automatically identifies any PostgreSQL recruiters with data_source LIKE 'web_intelligence:%'
        that are missing from DuckDB Parquet and appends them with schema alignment.
        Zero manual user clicks required.
        """
        try:
            from .parquet_writer import parquet_writer
            from .recruiter_store import PARQUET_FILE, recruiter_store
            import duckdb

            promoted_recs = db.query(Recruiter).filter(
                Recruiter.data_source.like("web_intelligence:%")
            ).all()

            if not promoted_recs:
                return 0

            con = duckdb.connect()
            p_path = PARQUET_FILE.replace("\\", "/")
            existing_emails = set()
            existing_ids = set()
            try:
                promoted_emails = [r.email.lower() for r in promoted_recs if r.email]
                if promoted_emails:
                    escaped = [e.replace("'", "''") for e in promoted_emails]
                    in_clause = ", ".join(f"'{e}'" for e in escaped)
                    rows = con.execute(f"SELECT recruiter_id, lower(email) FROM read_parquet('{p_path}') WHERE lower(email) IN ({in_clause})").fetchall()
                    for r in rows:
                        if r[0] is not None:
                            existing_ids.add(r[0])
                        if r[1]:
                            existing_emails.add(r[1])
            except Exception as e:
                logger.debug("[DB_AUTO_ENRICHER] Parquet read error during auto-sync: %s", e)
            finally:
                con.close()

            to_append = []
            seen = set()
            for r in promoted_recs:
                r_email = (r.email or "").strip().lower()
                if r.recruiter_id in existing_ids or (r_email and r_email in existing_emails) or (r_email and r_email in seen):
                    continue
                if r_email:
                    seen.add(r_email)
                to_append.append({
                    "recruiter_id": r.recruiter_id,
                    "recruiter_name": r.recruiter_name,
                    "title": r.title,
                    "company_id": r.company_id,
                    "email": r.email,
                    "phone": r.phone,
                    "linkedin": r.linkedin,
                    "location": r.location,
                    "state": getattr(r, "state", None),
                    "email_status": r.email_status,
                    "email_confidence": r.email_confidence,
                    "data_source": r.data_source,
                    "notes": r.notes,
                    "quality_score": r.email_confidence or 85,
                    "completeness_score": 85,
                    "is_active": True,
                    "created_at": r.created_at.isoformat() if r.created_at else datetime.utcnow().isoformat(),
                    "updated_at": r.updated_at.isoformat() if r.updated_at else datetime.utcnow().isoformat(),
                })

            if to_append:
                count = parquet_writer.append_records(to_append)
                logger.info("[DB_AUTO_ENRICHER] Autonomous Parquet Sync: Appended %d promoted records to Parquet", count)
                return count
            return 0
        except Exception as err:
            logger.warning("[DB_AUTO_ENRICHER] Autonomous Parquet Sync warning: %s", err)
            return 0


db_auto_enricher = DatabaseAutoEnricher()
