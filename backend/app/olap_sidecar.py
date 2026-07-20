"""
Sub-15ms In-Memory OLAP Analytical Caching Sidecar - TalentOpsAI
Serves heavy dashboard KPI aggregates from high-speed Python RAM memory.
"""
import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("talentops.olap")

class MemoryOLAPSidecar:
    _instance = None
    _cached_data_quality: Dict[int, Dict[str, Any]] = {}
    _last_sync_time: Dict[int, float] = {}
    _sync_ttl: float = 300  # Auto-refresh every 5 minutes

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MemoryOLAPSidecar()
        return cls._instance

    def refresh(self, user_id: int, force: bool = False) -> Dict[str, Any]:
        now = time.time()
        if not force and user_id in self._cached_data_quality and (now - self._last_sync_time.get(user_id, 0) < self._sync_ttl):
            return self._cached_data_quality[user_id]

        t0 = time.time()
        logger.info(f"[OLAP] Synchronizing high-speed OLAP aggregate sidecar for user {user_id}...")
        try:
            from .database import SessionLocal
            from sqlalchemy import text
            db = SessionLocal()
            try:
                db.execute(text("SET statement_timeout = '60s'"))
                recruiter_counts = db.execute(text("""
                    SELECT
                        COUNT(*) AS total_recruiters,
                        COUNT(*) FILTER (WHERE email IS NOT NULL AND email != '') AS real_emails,
                        COUNT(*) FILTER (WHERE phone IS NOT NULL AND phone != '') AS phones,
                        COUNT(*) FILTER (WHERE company_id IS NOT NULL) AS companies_linked,
                        COUNT(*) FILTER (WHERE state IS NOT NULL AND state != '') AS with_state,
                        COUNT(DISTINCT state) FILTER (WHERE state IS NOT NULL AND state != '') AS states_covered,
                        COUNT(*) FILTER (WHERE needs_review = true) AS needs_review,
                        COUNT(*) FILTER (WHERE state IS NULL OR state = '') AS unknown_state_count,
                        COUNT(*) FILTER (WHERE state_source IN ('state_column', 'recruiter_state_col', 'abbreviation_exact_match')) AS direct_state_count,
                        COUNT(*) FILTER (WHERE state_source = 'company_state') AS company_state_count,
                        COUNT(*) FILTER (WHERE state_source LIKE 'company_majority_state%') AS company_majority_count,
                        COUNT(*) FILTER (WHERE state_source = 'email_domain') AS domain_state_count,
                        COUNT(*) FILTER (WHERE state_source IN ('recruiter_location', 'company_location', 'notes', 'review_reason', 'metadata_json', 'raw_data')) AS text_inferred_count
                    FROM recruiters
                    WHERE user_id = :user_id
                """), {"user_id": user_id}).mappings().one()

                total_recruiters = int(recruiter_counts["total_recruiters"] or 0)
                real_emails = int(recruiter_counts["real_emails"] or 0)
                phones = int(recruiter_counts["phones"] or 0)
                companies_linked = int(recruiter_counts["companies_linked"] or 0)
                with_state = int(recruiter_counts["with_state"] or 0)
                states_covered = int(recruiter_counts["states_covered"] or 0)
                needs_review = int(recruiter_counts["needs_review"] or 0)
                unknown_state_count = int(recruiter_counts["unknown_state_count"] or 0)
                direct_state_count = int(recruiter_counts["direct_state_count"] or 0)
                company_state_count = int(recruiter_counts["company_state_count"] or 0)
                company_majority_count = int(recruiter_counts["company_majority_count"] or 0)
                domain_state_count = int(recruiter_counts["domain_state_count"] or 0)
                text_inferred_count = int(recruiter_counts["text_inferred_count"] or 0)

                total_companies = db.execute(text("SELECT COUNT(*) FROM companies WHERE user_id = :user_id"), {"user_id": user_id}).scalar() or 0

                try:
                    db_size = db.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))")).scalar()
                except Exception:
                    db_size = "Unknown"

                duplicate_risk = db.execute(
                    text("SELECT COUNT(*) FROM (SELECT phone FROM recruiters WHERE phone IS NOT NULL AND phone != '' AND user_id = :user_id GROUP BY phone HAVING COUNT(*) > 1) t"), {"user_id": user_id}
                ).scalar() or 0

                explicit_state_count = direct_state_count
                pre_existing_states = db.execute(text("""
                    SELECT COUNT(*)
                    FROM recruiters
                    WHERE (state IS NOT NULL AND state != '')
                      AND (state_source IS NULL OR state_source = '')
                      AND user_id = :user_id
                """), {"user_id": user_id}).scalar() or 0
                explicit_state_count += pre_existing_states
                inferred_state_count = max(with_state - explicit_state_count, 0)

                email_cov = round((real_emails / total_recruiters * 100), 1) if total_recruiters else 0
                phone_cov = round((phones / total_recruiters * 100), 1) if total_recruiters else 0
                comp_cov = round((companies_linked / total_recruiters * 100), 1) if total_recruiters else 0
                state_cov = round((with_state / total_recruiters * 100), 1) if total_recruiters else 0
                review_cov = round((needs_review / total_recruiters * 100), 1) if total_recruiters else 0
                quality_score = round((email_cov * 0.4) + (phone_cov * 0.2) + (comp_cov * 0.2) + (state_cov * 0.2), 1)

                result = {
                    "total_recruiters": total_recruiters,
                    "total_companies": total_companies,
                    "states_covered": states_covered,
                    "database_size": db_size,
                    "email_coverage": email_cov,
                    "phone_coverage": phone_cov,
                    "company_coverage": comp_cov,
                    "state_coverage": state_cov,
                    "needs_review_percent": review_cov,
                    "quality_score": quality_score,
                    "missing_email_count": total_recruiters - real_emails,
                    "missing_phone_count": total_recruiters - phones,
                    "missing_company_count": total_recruiters - companies_linked,
                    "missing_state_count": unknown_state_count,
                    "duplicate_risk_count": duplicate_risk,
                    "needs_review_count": needs_review,
                    "known_state_count": with_state,
                    "unknown_state_count": unknown_state_count,
                    "explicit_state_count": explicit_state_count,
                    "inferred_state_count": inferred_state_count,
                    "company_state_count": company_state_count,
                    "company_majority_state_count": company_majority_count,
                    "domain_state_count": domain_state_count,
                    "text_inferred_state_count": text_inferred_count,
                }

                self._cached_data_quality[user_id] = result
                self._last_sync_time[user_id] = time.time()
                elapsed = round((self._last_sync_time[user_id] - t0) * 1000, 2)
                logger.info(f"[OLAP] Sidecar sync complete in {elapsed}ms! Known State: {with_state:,}")
                return result

            finally:
                db.close()
        except Exception as e:
            logger.error(f"[OLAP] Error syncing sidecar: {e}")
            if user_id in self._cached_data_quality:
                return self._cached_data_quality[user_id]
            raise

    def get_data_quality(self, user_id: int) -> Dict[str, Any]:
        return self.refresh(user_id=user_id, force=False)

    def invalidate(self, user_id: int = None):
        logger.info("[OLAP] Cache invalidated. Next query will trigger C-speed DB sync.")
        if user_id and user_id in self._last_sync_time:
            self._last_sync_time[user_id] = 0
        else:
            self._last_sync_time = {}

olap_sidecar = MemoryOLAPSidecar.get_instance()
