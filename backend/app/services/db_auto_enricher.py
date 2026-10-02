"""
db_auto_enricher.py — Database Auto-Enricher & Flywheel Synchronizer.
====================================================================
Bridges external discoveries from discovery_staging into the master catalog
by routing through the mandatory 7-stage Universal Ingestion Funnel:
1. Raw Sourcing & Platform Chrome Elimination
2. Hard Entity Disambiguation (Person vs Company vs Job)
3. Contextual Identity Reconstruction & Title Sanitization
4. Autonomous Corporate Email Intelligence & Pattern Mining
5. Live Port 25 SMTP Deliverability Probing & MX Verification
6. Actionable Contact Intelligence Gate (Zero Fake Emails)
7. Master Catalog Promotion & DuckDB Parquet Dual-Sync Flywheel
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.staging_models import DiscoveryStaging
from ..models.models import Recruiter, Company
from .ingestion_funnel import universal_funnel

logger = logging.getLogger("talentops.db_auto_enricher")


class DatabaseAutoEnricher:
    """
    Safely reconciles staged web intelligence into PostgreSQL master tables.
    Non-destructive: Never overwrites existing populated fields; only fills blanks.
    Governed 100% by UniversalIngestionFunnel.
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
        Processes pending staged observations through the mandatory 7-stage Universal Ingestion Funnel.
        """
        results = universal_funnel.process_staging_batch(db=db, limit=limit)
        self.stats["total_processed"] += results.get("processed_count", 0)
        self.stats["existing_enriched"] += results.get("enriched_existing", 0)
        self.stats["new_promoted"] += results.get("promoted_new", 0)
        logger.info("[DB_AUTO_ENRICHER] Universal Funnel batch complete: %d processed, %d enriched, %d promoted",
                    results.get("processed_count", 0), results.get("enriched_existing", 0), results.get("promoted_new", 0))
        return results

    def autonomous_sync_parquet(self, db: Session) -> int:
        """
        Autonomous self-healing Parquet synchronizer.
        Automatically identifies any PostgreSQL recruiters with data_source LIKE 'web_intelligence:%'
        or 'universal_funnel:%' that are missing from DuckDB Parquet and appends them with schema alignment.
        Zero manual user clicks required.
        """
        try:
            from .parquet_writer import parquet_writer
            from .recruiter_store import PARQUET_FILE, recruiter_store, safe_duckdb_connect

            promoted_recs = db.query(Recruiter).filter(
                (Recruiter.data_source.like("web_intelligence:%")) |
                (Recruiter.data_source.like("universal_funnel:%"))
            ).all()

            if not promoted_recs:
                return 0

            con = safe_duckdb_connect(threads=1)
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
