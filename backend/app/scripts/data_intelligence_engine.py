import os
import sys
import argparse
import re
import json
from datetime import datetime, timezone
from sqlalchemy import text, or_

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from app.database import SessionLocal
from app.models.models import Recruiter, Company
from app.utils.state_mapper import extract_state_detailed, STATE_MAP as US_STATE_MAP, CITY_TO_STATE, LOCATION_PHRASE_TO_STATE
from app.utils.state_recovery import build_company_domain_state_index, infer_state_from_sources

STATE_ABBR_SET = set(US_STATE_MAP.values())
STATE_ABBR_RE = re.compile(r'(?<![A-Z])(?:' + "|".join(sorted(STATE_ABBR_SET, key=len, reverse=True)) + r')(?![A-Z])')
STATE_SIGNAL_TERMS = sorted(
    {term.upper() for term in list(US_STATE_MAP.keys()) + list(CITY_TO_STATE.keys()) + list(LOCATION_PHRASE_TO_STATE.keys())},
    key=len,
    reverse=True,
)

def infer_state(text_value, source_label: str):
    if not text_value:
        return None, None, None
    state, reason = extract_state_detailed(text_value)
    if not state:
        return None, None, None
    confidence = "high" if source_label in {"recruiter_location", "company_location"} else "medium"
    if reason in {"abbreviation_exact_match", "abbreviation_word_boundary", "abbreviation_comma_split", "full_state_name_match", "location_phrase_match", "city_match"}:
        confidence = "high" if source_label in {"recruiter_location", "company_location"} else "medium"
    return state, confidence, f"{source_label}: {reason}"


def _flatten_json_text(value):
    if value is None:
        return None
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except Exception:
        return str(value)

    parts = []

    def walk(item):
        if item is None:
            return
        if isinstance(item, dict):
            for nested in item.values():
                walk(nested)
            return
        if isinstance(item, (list, tuple, set)):
            for nested in item:
                walk(nested)
            return
        text = str(item).strip()
        if text:
            parts.append(text)

    walk(parsed)
    return " ".join(parts) if parts else None


def _candidate_state_sources(recruiter, company):
    candidates = [
        ("recruiter_location", recruiter.location),
        ("company_state", company.state if company else None),
        ("company_location", company.location if company else None),
        ("metadata_json", recruiter.metadata_json),
        ("raw_data", recruiter.raw_data),
        ("notes", recruiter.notes),
        ("review_reason", recruiter.review_reason),
        ("email_domain", recruiter.email),
    ]
    for source_label, value in candidates:
        if not value:
            continue
        if source_label in {"metadata_json", "raw_data"}:
            flattened = _flatten_json_text(value)
            if flattened:
                yield source_label, flattened
                continue
        yield source_label, value


def _has_state_signal(value) -> bool:
    if not value:
        return False
    text = str(value).upper()
    if STATE_ABBR_RE.search(text):
        return True
    return any(term in text for term in STATE_SIGNAL_TERMS)

def run_engine(dry_run=True, batch_size=1000):
    db = SessionLocal()
    print(f"--- STARTING DATA INTELLIGENCE ENGINE V2 ---", flush=True)
    if dry_run:
        print(f"!!! DRY RUN MODE ACTIVE - NO CHANGES WILL BE SAVED !!!\n", flush=True)
    else:
        print(f"!!! LIVE EXECUTION MODE ACTIVE (Batch Size: {batch_size}) !!!\n", flush=True)

    # 1. Flag Duplicate Phones
    print("Finding shared phone numbers...", flush=True)
    dup_phones = db.execute(text("SELECT phone FROM recruiters WHERE phone IS NOT NULL AND phone != '' GROUP BY phone HAVING COUNT(*) > 1")).fetchall()
    dup_phone_set = {p[0] for p in dup_phones}
    print(f"Found {len(dup_phone_set)} phone numbers shared across multiple recruiters.", flush=True)

    # 2. Flag Duplicate Name/Company
    print("Finding shared Name + Company combinations...", flush=True)
    dup_nc = db.execute(text("SELECT recruiter_name, company_id FROM recruiters WHERE recruiter_name != 'Unknown' AND company_id IS NOT NULL GROUP BY recruiter_name, company_id HAVING COUNT(*) > 1")).fetchall()
    dup_nc_set = {(r[0], r[1]) for r in dup_nc}
    print(f"Found {len(dup_nc_set)} shared Name+Company combinations.", flush=True)

    total_recruiters = db.query(Recruiter).count()
    companies = {c.company_id: c for c in db.query(Company).all()}
    company_domain_index = build_company_domain_state_index(companies.values())

    company_state_counts = db.execute(text("""
        SELECT company_id, state, COUNT(*) AS cnt
        FROM recruiters
        WHERE company_id IS NOT NULL AND state IS NOT NULL AND state != ''
        GROUP BY company_id, state
    """)).mappings().all()
    company_state_totals = {}
    company_state_map = {}
    for row in company_state_counts:
        company_id = int(row["company_id"])
        state = row["state"]
        cnt = int(row["cnt"])
        bucket = company_state_totals.setdefault(company_id, {"total": 0, "state": None, "count": 0})
        bucket["total"] += cnt
        if cnt > bucket["count"] or (cnt == bucket["count"] and (bucket["state"] is None or state < bucket["state"])):
            bucket["state"] = state
            bucket["count"] = cnt
    for company_id, bucket in company_state_totals.items():
        if bucket["count"] >= 2 and bucket["count"] / bucket["total"] >= 0.5:
            company_state_map[company_id] = {
                "state": bucket["state"],
                "count": bucket["count"],
                "total": bucket["total"],
            }
    print(f"Company states recoverable from recruiter majority: {len(company_state_map)}", flush=True)
    print(f"Recruiters currently missing state: {db.query(Recruiter).filter((Recruiter.state.is_(None)) | (Recruiter.state == '')).count()}", flush=True)
    updates = 0
    inferred_states = 0
    flagged_reviews = 0
    normalized_names = 0
    processed = 0

    for company_id, payload in company_state_map.items():
        company = companies.get(company_id)
        if not company or company.state:
            continue
        company.state = payload["state"]
        inferred_states += 1
        updates += 1
    if company_state_map:
        db.commit()

    scan_query = (
        db.query(Recruiter)
        .filter(or_(Recruiter.state.is_(None), Recruiter.state == ""))
        .filter(
            or_(
                Recruiter.metadata_json.isnot(None),
                Recruiter.raw_data.isnot(None),
                Recruiter.notes.isnot(None),
                Recruiter.review_reason.isnot(None),
                Recruiter.company_id.in_(list(company_state_map.keys())) if company_state_map else False,
            )
        )
        .order_by(Recruiter.recruiter_id)
    )
    print(f"Total recruiters in DB: {total_recruiters}", flush=True)
    candidate_count = scan_query.count()
    print(f"Candidate rows for state backfill: {candidate_count}", flush=True)
    company_candidates = [c for c in companies.values() if not c.state and c.location]

    scan_time = datetime.now(timezone.utc)

    # Process in batches to avoid locking
    recruiters = []
    processed = 0

    def process_batch(batch):
        nonlocal updates, inferred_states, flagged_reviews, normalized_names
        for r in batch:
            needs_update = False
            review_reasons = []

            # Name Normalization
            if r.recruiter_name and r.recruiter_name != 'Unknown' and r.recruiter_name != r.recruiter_name.title():
                r.recruiter_name = r.recruiter_name.title()
                normalized_names += 1
                needs_update = True

            # Review Flags
            if r.phone in dup_phone_set:
                review_reasons.append("Shared Phone Number (Possible Duplicate)")
            if r.company_id and (r.recruiter_name, r.company_id) in dup_nc_set:
                review_reasons.append("Shared Name & Company (Possible Duplicate)")
            if "@missing.local" in (r.email or ""):
                review_reasons.append("Dummy Email / Phone-Only Contact")

            if review_reasons:
                r.needs_review = True
                r.review_reason = " | ".join(review_reasons)
                flagged_reviews += 1
                needs_update = True
            else:
                if r.needs_review:
                    r.needs_review = False
                    r.review_reason = None
                    needs_update = True

            # State Inference
            if not r.state:
                company = companies.get(r.company_id)
                state_result = infer_state_from_sources(
                    _candidate_state_sources(r, company),
                    domain_index=company_domain_index,
                )
                if state_result and state_result.get("state"):
                    r.state = state_result["state"]
                    r.state_source = state_result["state_source"]
                    r.state_confidence = state_result["state_confidence"]
                    r.state_reason = state_result["state_reason"]
                    inferred_states += 1
                    needs_update = True
                    meta = {}
                    if r.metadata_json:
                        try:
                            meta = json.loads(r.metadata_json) if isinstance(r.metadata_json, str) else dict(r.metadata_json)
                        except Exception:
                            meta = {"raw_metadata": str(r.metadata_json)}
                    meta.setdefault("state_recovery", {})
                    meta["state_recovery"] = {
                        "source": r.state_source,
                        "confidence": r.state_confidence,
                        "reason": r.state_reason,
                        "evidence": state_result.get("evidence"),
                    }
                    r.metadata_json = json.dumps(meta, default=str)

            # Tracking timestamp
            r.last_scan_at = scan_time
            needs_update = True

            # Completeness Score (0-100)
            score = 0
            if r.recruiter_name and r.recruiter_name != 'Unknown': score += 20
            if r.email and "@missing.local" not in r.email: score += 20
            if r.phone: score += 20
            if r.company_id: score += 20
            if r.state: score += 20
            
            if r.completeness_score != score:
                r.completeness_score = score
                needs_update = True

            if needs_update:
                updates += 1

    for recruiter in scan_query.yield_per(batch_size):
        recruiters.append(recruiter)
        if len(recruiters) < batch_size:
            continue
        process_batch(recruiters)
        processed += len(recruiters)
        print(f"Processed {min(processed, candidate_count)} / {candidate_count} candidate records...", flush=True)
        if not dry_run:
            db.commit()
        recruiters = []

    if recruiters:
        process_batch(recruiters)
        processed += len(recruiters)
        print(f"Processed {processed} / {candidate_count} candidate records...", flush=True)
        if not dry_run:
            db.commit()

    for company in company_candidates:
        inferred, conf, reason = infer_state(company.location, "company_location")
        if inferred and company.state != inferred:
            company.state = inferred
            inferred_states += 1
            updates += 1
    if company_candidates and not dry_run:
        db.commit()

    print("\n--- RESULTS ---", flush=True)
    print(f"Records touched/updated: {updates}", flush=True)
    print(f"States safely inferred: {inferred_states}", flush=True)
    print(f"Records flagged for manual review: {flagged_reviews}", flush=True)
    print(f"Names normalized (casing): {normalized_names}", flush=True)

    if not dry_run:
        print("\nAll batches committed to database.", flush=True)
    else:
        print("\nRolling back dry-run session...", flush=True)
        db.rollback()

    db.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Actually run the updates against the database")
    parser.add_argument("--batch-size", type=int, default=1000, help="Number of records to process per commit")
    args = parser.parse_args()
    
    run_engine(dry_run=not args.execute, batch_size=args.batch_size)
