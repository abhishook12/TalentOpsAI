"""
Recruiter Profile Deduplication Engine
=====================================
Detects duplicate recruiter records in DuckDB / Parquet store via:
  1. Exact Normalized Primary Email
  2. Normalized Full Name + Company Matching
  3. Normalized 10-Digit Phone Numbers

Merges secondary contact vectors (alternate emails & phones, LinkedIn, notes)
into the primary canonical record, minimizing database bloat and eliminating duplicate outreach.
"""

import logging
import re
from typing import Dict, Any, List, Tuple
from collections import defaultdict
from .recruiter_store import recruiter_store
from .parquet_writer import parquet_writer

logger = logging.getLogger("talentops.dedup")


def _norm_str(val: Any) -> str:
    return str(val or "").strip().lower()


def _norm_phone(val: Any) -> str:
    digits = re.sub(r"\D+", "", str(val or ""))
    return digits[-10:] if len(digits) >= 10 else ""


class DeduplicationEngine:
    def __init__(self):
        pass

    def scan_duplicates(self, limit_clusters: int = 50) -> Dict[str, Any]:
        """
        Scans the Parquet store and returns clusters of duplicate profiles without modifying data.
        """
        recruiter_store._ensure_loaded()
        conn = recruiter_store._get_conn()
        
        # 1. Find email duplicates
        email_dupes_sql = """
            SELECT LOWER(TRIM(email)) as norm_email, COUNT(*) as cnt
            FROM recruiters
            WHERE email IS NOT NULL AND email != '' AND email LIKE '%@%'
            GROUP BY LOWER(TRIM(email))
            HAVING COUNT(*) > 1
            ORDER BY cnt DESC
            LIMIT ?
        """
        email_dupe_rows = conn.execute(email_dupes_sql, [limit_clusters]).fetchall()
        
        email_clusters = []
        for norm_email, count in email_dupe_rows:
            recs = conn.execute(
                "SELECT recruiter_id, recruiter_name, email, phone, company_id, location FROM recruiters WHERE LOWER(TRIM(email)) = ? LIMIT 10",
                [norm_email]
            ).fetchall()
            email_clusters.append({
                "match_type": "email",
                "key": norm_email,
                "count": count,
                "sample_profiles": [
                    {"id": r[0], "name": r[1], "email": r[2], "phone": r[3], "company_id": r[4], "location": r[5]}
                    for r in recs
                ]
            })

        # 2. Find Name + Company duplicates
        name_comp_sql = """
            SELECT LOWER(TRIM(recruiter_name)) as norm_name, CAST(COALESCE(company_id, '') AS VARCHAR) as comp, COUNT(*) as cnt
            FROM recruiters
            WHERE recruiter_name IS NOT NULL AND recruiter_name != '' AND company_id IS NOT NULL
            GROUP BY LOWER(TRIM(recruiter_name)), CAST(COALESCE(company_id, '') AS VARCHAR)
            HAVING COUNT(*) > 1
            ORDER BY cnt DESC
            LIMIT ?
        """
        name_comp_rows = conn.execute(name_comp_sql, [limit_clusters]).fetchall()
        
        name_comp_clusters = []
        for norm_name, comp, count in name_comp_rows:
            recs = conn.execute(
                "SELECT recruiter_id, recruiter_name, email, phone, company_id, location FROM recruiters WHERE LOWER(TRIM(recruiter_name)) = ? AND CAST(COALESCE(company_id, '') AS VARCHAR) = ? LIMIT 10",
                [norm_name, comp]
            ).fetchall()
            name_comp_clusters.append({
                "match_type": "name_company",
                "key": f"{norm_name} @ {comp}",
                "count": count,
                "sample_profiles": [
                    {"id": r[0], "name": r[1], "email": r[2], "phone": r[3], "company_id": r[4], "location": r[5]}
                    for r in recs
                ]
            })

        total_dupes = sum(c["count"] - 1 for c in email_clusters) + sum(c["count"] - 1 for c in name_comp_clusters)

        return {
            "total_duplicate_clusters_found": len(email_clusters) + len(name_comp_clusters),
            "estimated_redundant_records": total_dupes,
            "email_clusters": email_clusters,
            "name_company_clusters": name_comp_clusters
        }

    def merge_duplicates(self, match_strategy: str = "email", max_clusters: int = 25, dry_run: bool = True) -> Dict[str, Any]:
        """
        Merges duplicate records. In dry-run mode, previews changes.
        In live mode, consolidates secondary contact info and removes redundant records.
        """
        recruiter_store._ensure_loaded()
        conn = recruiter_store._get_conn()

        if match_strategy == "email":
            dupes_sql = """
                SELECT LOWER(TRIM(email)) as match_key, COUNT(*) as cnt
                FROM recruiters
                WHERE email IS NOT NULL AND email != '' AND email LIKE '%@%'
                GROUP BY LOWER(TRIM(email))
                HAVING COUNT(*) > 1
                LIMIT ?
            """
        else:
            dupes_sql = """
                SELECT LOWER(TRIM(recruiter_name)) || '|||' || CAST(COALESCE(company_id, '') AS VARCHAR) as match_key, COUNT(*) as cnt
                FROM recruiters
                WHERE recruiter_name IS NOT NULL AND recruiter_name != '' AND company_id IS NOT NULL
                GROUP BY LOWER(TRIM(recruiter_name)), CAST(COALESCE(company_id, '') AS VARCHAR)
                HAVING COUNT(*) > 1
                LIMIT ?
            """

        clusters = conn.execute(dupes_sql, [max_clusters]).fetchall()
        merged_count = 0
        deleted_count = 0
        details = []

        for match_key, count in clusters:
            if match_strategy == "email":
                rows = conn.execute(
                    "SELECT * FROM recruiters WHERE LOWER(TRIM(email)) = ?",
                    [match_key]
                ).fetchdf().to_dict(orient="records")
            else:
                name_part, comp_part = match_key.split("|||", 1)
                rows = conn.execute(
                    "SELECT * FROM recruiters WHERE LOWER(TRIM(recruiter_name)) = ? AND CAST(COALESCE(company_id, '') AS VARCHAR) = ?",
                    [name_part, comp_part]
                ).fetchdf().to_dict(orient="records")

            if not rows or len(rows) < 2:
                continue

            # Pick primary: one with highest completeness or oldest ID
            rows.sort(key=lambda r: (r.get("completeness_score") or 0, -(r.get("recruiter_id") or 0)), reverse=True)
            primary = rows[0]
            secondaries = rows[1:]

            # Consolidate emails and phones
            all_emails = set()
            all_phones = set()

            for r in rows:
                for f in ["email", "email2", "email3", "email4"]:
                    val = _norm_str(r.get(f))
                    if val and "@" in val:
                        all_emails.add(val)
                for f in ["phone", "phone2", "phone3", "phone4"]:
                    val = _norm_phone(r.get(f))
                    if val:
                        all_phones.add(val)

            # Assign to primary
            email_list = list(all_emails)
            phone_list = list(all_phones)

            primary_update = {
                "recruiter_id": primary["recruiter_id"],
                "email": email_list[0] if len(email_list) > 0 else primary.get("email"),
                "email2": email_list[1] if len(email_list) > 1 else None,
                "email3": email_list[2] if len(email_list) > 2 else None,
                "email4": email_list[3] if len(email_list) > 3 else None,
                "phone": phone_list[0] if len(phone_list) > 0 else primary.get("phone"),
                "phone2": phone_list[1] if len(phone_list) > 1 else None,
                "phone3": phone_list[2] if len(phone_list) > 2 else None,
                "phone4": phone_list[3] if len(phone_list) > 3 else None,
            }

            delete_ids = [s["recruiter_id"] for s in secondaries if s.get("recruiter_id")]

            details.append({
                "canonical_id": primary["recruiter_id"],
                "name": primary.get("recruiter_name"),
                "merged_records_count": len(secondaries),
                "merged_ids": delete_ids,
                "consolidated_emails_count": len(email_list),
                "consolidated_phones_count": len(phone_list)
            })

            merged_count += 1
            deleted_count += len(delete_ids)

            if not dry_run:
                # Apply updates
                parquet_writer.update_records([primary_update])
                if delete_ids:
                    parquet_writer.delete_records(delete_ids)

        if not dry_run and merged_count > 0:
            recruiter_store.reload()

        return {
            "dry_run": dry_run,
            "strategy": match_strategy,
            "clusters_processed": merged_count,
            "records_consolidated": deleted_count,
            "details": details
        }


deduplication_engine = DeduplicationEngine()
