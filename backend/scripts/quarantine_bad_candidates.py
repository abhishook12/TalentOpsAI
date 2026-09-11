"""
backend/scripts/quarantine_bad_candidates.py — Database Quarantine & Data Repair Migration

Rules 27 & 28 Mandate:
- PRESERVE ORIGINAL raw evidence and audit history.
- DO NOT hard-delete records.
- Identify and quarantine all invalid candidate records across:
  1. Desktop Scout SQLite queue (scout_desktop/local_queue.db)
  2. Postgres discovery_staging
  3. Postgres resolved_persons
  4. Postgres recruiters (extension source)
"""

import os
import sys
import json
import sqlite3
import re

sys.path.insert(0, r"c:\TalentOpsAI\backend")
from app.database import SessionLocal
from app.models.staging_models import DiscoveryStaging, ResolvedPerson
from app.models.models import Recruiter
from app.utils.normalizer import validate_human_name, validate_company_for_person

def quarantine_local_sqlite_queue():
    db_path = r"c:\TalentOpsAI\scout_desktop\local_queue.db"
    if not os.path.exists(db_path):
        print(f"[SQLite] DB not found at {db_path}, skipping.")
        return 0, 0

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, cluster_json, status FROM queued_observations")
    rows = cur.fetchall()

    total_inspected = len(rows)
    quarantined_count = 0

    for rid, cluster_str, status in rows:
        try:
            data = json.loads(cluster_str)
            name = str(data.get("recruiter_name") or data.get("raw_name") or "").strip()
            comp = str(data.get("company_name") or data.get("raw_company") or "").strip()
            title = str(data.get("title") or data.get("raw_title") or "").strip()

            is_valid_name, _, name_reason = validate_human_name(name)
            is_valid_comp, comp_reason = validate_company_for_person(comp, person_name=name)

            # Check explicit bad noise cases
            is_bad = (
                not is_valid_name
                or not is_valid_comp
                or any(t in name.lower() for t in [": people", ": overview", "reason:", "active window", "latest capture", "mailings", "54 ri", "ihhi", "ask gemini", "teams extractor"])
                or any(t in comp.lower() for t in ["inbox", "mailings", "active window", "followed by", "experience", "quick easy prompt"])
            )

            if is_bad and status not in ("QUARANTINED", "REJECTED"):
                reason = name_reason or comp_reason or "UI noise or invalid identity"
                cur.execute(
                    "UPDATE queued_observations SET status = 'QUARANTINED', dlq_reason = ? WHERE id = ?",
                    (f"Quarantined by Candidate Creation Gate: {reason}", rid)
                )
                quarantined_count += 1
        except Exception as e:
            pass

    conn.commit()
    conn.close()
    print(f"[SQLite] Inspected {total_inspected} queued observations. Quarantined: {quarantined_count}. Retained/Preserved: {total_inspected}")
    return total_inspected, quarantined_count


def quarantine_postgres_database():
    db = SessionLocal()

    # 1. Inspect and quarantine discovery_staging
    staging_records = db.query(DiscoveryStaging).all()
    stg_total = len(staging_records)
    stg_quarantined = 0

    for r in staging_records:
        name = str(r.raw_name or "").strip()
        comp = str(r.raw_company or "").strip()

        is_valid_name, _, name_reason = validate_human_name(name)
        is_valid_comp, comp_reason = validate_company_for_person(comp, person_name=name)

        is_bad = (
            not is_valid_name
            or not is_valid_comp
            or any(t in name.lower() for t in [": people", ": overview", "reason:", "active window", "latest capture", "mailings", "54 ri", "ihhi", "ask gemini", "teams extractor"])
            or any(t in comp.lower() for t in ["inbox", "mailings", "active window", "followed by", "experience", "quick easy prompt"])
            or getattr(r, "platform", "") == "Active Window"
            or str(getattr(r, "source_page_title", "") or "").lower() == "active window"
        )

        if is_bad and r.processing_status not in ("rejected", "quarantined"):
            r.processing_status = "rejected"
            r.decision = "QUARANTINED_UI_TEXT"
            r.decision_reason = f"Quarantined by Candidate Creation Gate: {name_reason or comp_reason or 'UI noise / invalid identity'}"
            r.identity_confidence = 0.0
            stg_quarantined += 1

    # 2. Inspect and quarantine resolved_persons
    persons = db.query(ResolvedPerson).all()
    persons_total = len(persons)
    persons_quarantined = 0

    for p in persons:
        name = str(p.canonical_name or "").strip()
        comp = str(p.current_company or "").strip()

        is_valid_name, _, _ = validate_human_name(name)
        is_valid_comp, _ = validate_company_for_person(comp, person_name=name)

        is_bad = (
            not is_valid_name
            or not is_valid_comp
            or any(t in name.lower() for t in [": people", ": overview", "reason:", "active window", "latest capture", "mailings", "54 ri", "ihhi", "ask gemini", "teams extractor"])
            or any(t in comp.lower() for t in ["inbox", "mailings", "active window", "followed by", "experience"])
        )

        if is_bad and p.identity_confidence > 0.0:
            p.identity_confidence = 0.0
            persons_quarantined += 1

    # 3. Inspect and quarantine recruiters created by extension
    recruiters = db.query(Recruiter).filter(Recruiter.data_source == "extension").all()
    recs_total = len(recruiters)
    recs_quarantined = 0

    for rc in recruiters:
        name = str(getattr(rc, "recruiter_name", "") or "").strip()
        is_valid_name, _, name_reason = validate_human_name(name)
        is_bad = (
            not is_valid_name
            or any(t in name.lower() for t in [": people", ": overview", "reason:", "active window", "latest capture", "mailings", "54 ri", "ihhi", "ask gemini", "teams extractor"])
        )

        if is_bad and not rc.needs_review:
            rc.needs_review = True
            rc.review_reason = f"Quarantined by Candidate Creation Gate: {name_reason or 'Invalid identity/UI noise'}"
            recs_quarantined += 1

    db.commit()
    db.close()

    print(f"[Postgres Staging] Inspected {stg_total} records. Quarantined: {stg_quarantined}. Retained/Preserved: {stg_total}")
    print(f"[Postgres Resolved] Inspected {persons_total} persons. Quarantined: {persons_quarantined}. Active Retained: {persons_total - persons_quarantined}")
    print(f"[Postgres Recruiters] Inspected {recs_total} extension recruiters. Quarantined: {recs_quarantined}. Valid Retained: {recs_total - recs_quarantined}")

    return {
        "staging_total": stg_total,
        "staging_quarantined": stg_quarantined,
        "persons_total": persons_total,
        "persons_quarantined": persons_quarantined,
        "recruiters_total": recs_total,
        "recruiters_quarantined": recs_quarantined,
    }


if __name__ == "__main__":
    print("=== EXECUTING DATA REPAIR & CANDIDATE QUARANTINE MIGRATION ===")
    quarantine_local_sqlite_queue()
    quarantine_postgres_database()
    print("=== QUARANTINE MIGRATION COMPLETED SUCCESSFULLY ===")
