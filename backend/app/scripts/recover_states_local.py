from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import or_, text

from app.database import SessionLocal
from app.models.models import Company, Recruiter
from app.utils.state_mapper import extract_state_detailed
from app.utils.state_recovery import build_company_domain_state_index, flatten_text, infer_state_from_domain


def parse_metadata(value):
    if not value:
        return {}
    if isinstance(value, dict):
        return dict(value)
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except Exception:
        return {"raw_metadata": str(value)}


def compute_company_majority_map(session, min_ratio: float, min_count: int):
    rows = session.execute(text("""
        SELECT company_id, state, COUNT(*) AS cnt
        FROM recruiters
        WHERE company_id IS NOT NULL AND state IS NOT NULL AND state != ''
        GROUP BY company_id, state
    """)).mappings().all()
    buckets = {}
    for row in rows:
        company_id = int(row["company_id"])
        state = row["state"]
        cnt = int(row["cnt"])
        bucket = buckets.setdefault(company_id, {"total": 0, "state": None, "count": 0})
        bucket["total"] += cnt
        if cnt > bucket["count"] or (cnt == bucket["count"] and (bucket["state"] is None or state < bucket["state"])):
            bucket["state"] = state
            bucket["count"] = cnt
    return {
        company_id: bucket
        for company_id, bucket in buckets.items()
        if bucket["count"] >= min_count and (bucket["count"] / bucket["total"]) >= min_ratio
    }


def recover_companies_from_location(session, companies):
    updates = []
    for company in companies:
        if company.state or not company.location:
            continue
        state, reason = extract_state_detailed(company.location)
        if state:
            updates.append({"id": company.company_id, "state": state})
    if updates:
        session.execute(text("UPDATE companies SET state = :state WHERE company_id = :id"), updates)
        session.commit()
    return len(updates)


def recover_recruiters_pass(session, domain_index, majority_map, batch_size):
    update_sql = text("""
        UPDATE recruiters
        SET state = :state,
            state_source = :state_source,
            state_confidence = :state_confidence,
            state_reason = :state_reason,
            metadata_json = :metadata_json,
            last_scan_at = :last_scan_at
        WHERE recruiter_id = :id
    """)
    stats = Counter()
    recovered_samples = []
    unrecoverable_samples = []
    batch = []
    scanned = 0
    recovered = 0
    scan_time = datetime.now(timezone.utc)

    last_id = 0
    while True:
        rows = (
            session.query(Recruiter, Company)
            .join(Company, Recruiter.company_id == Company.company_id, isouter=True)
            .filter(or_(Recruiter.state.is_(None), Recruiter.state == ""))
            .filter(Recruiter.recruiter_id > last_id)
            .order_by(Recruiter.recruiter_id)
            .limit(batch_size)
            .all()
        )
        if not rows:
            break

        for recruiter, company in rows:
            last_id = recruiter.recruiter_id
            scanned += 1
            metadata = parse_metadata(recruiter.metadata_json)
            state = None
            source = None
            confidence = None
            reason = None
            evidence = None

            sources = [
                ("recruiter_location", recruiter.location),
                ("company_state", company.state if company else None),
                ("company_location", company.location if company else None),
                ("notes", recruiter.notes),
                ("review_reason", recruiter.review_reason),
                ("metadata_json", recruiter.metadata_json),
                ("raw_data", recruiter.raw_data),
            ]
            for label, value in sources:
                flat = flatten_text(value)
                if not flat:
                    continue
                is_strict = label in {"notes", "review_reason", "metadata_json", "raw_data"}
                extracted_state, extracted_reason = extract_state_detailed(flat, strict=is_strict)
                if extracted_state:
                    state = extracted_state
                    source = label
                    confidence = "high" if label in {"recruiter_location", "company_state", "company_location"} else "medium"
                    reason = extracted_reason
                    evidence = flat[:500]
                    break

            if not state and recruiter.email:
                extracted_state, extracted_reason, extracted_evidence = infer_state_from_domain(recruiter.email, domain_index)
                if extracted_state:
                    state = extracted_state
                    source = "email_domain"
                    confidence = "medium"
                    reason = extracted_reason
                    evidence = extracted_evidence

            if not state and recruiter.company_id in majority_map:
                majority = majority_map[recruiter.company_id]
                state = majority["state"]
                source = "company_majority_state"
                confidence = "high" if majority["count"] / majority["total"] >= 0.8 else "medium"
                reason = f"company_majority:{majority['count']}/{majority['total']}"
                evidence = {"ratio": majority["count"] / majority["total"], "count": majority["count"], "total": majority["total"]}

            if state:
                metadata["state_recovery"] = {
                    "source": source,
                    "confidence": confidence,
                    "reason": reason,
                    "evidence": evidence,
                }
                batch.append(
                    {
                        "id": recruiter.recruiter_id,
                        "state": state,
                        "state_source": source,
                        "state_confidence": confidence,
                        "state_reason": reason,
                        "metadata_json": json.dumps(metadata, default=str),
                        "last_scan_at": scan_time,
                    }
                )
                recovered += 1
                stats[source] += 1
                if len(recovered_samples) < 20:
                    recovered_samples.append(
                        {
                            "recruiter_id": recruiter.recruiter_id,
                            "name": recruiter.recruiter_name,
                            "company": company.company_name if company else None,
                            "email": recruiter.email,
                            "state": state,
                            "source": source,
                            "confidence": confidence,
                            "reason": reason,
                        }
                    )
            else:
                if len(unrecoverable_samples) < 20:
                    unrecoverable_samples.append(
                        {
                            "recruiter_id": recruiter.recruiter_id,
                            "name": recruiter.recruiter_name,
                            "company": company.company_name if company else None,
                            "email": recruiter.email,
                            "location": recruiter.location,
                            "notes": recruiter.notes,
                            "review_reason": recruiter.review_reason,
                        }
                    )

            if len(batch) >= batch_size:
                session.execute(update_sql, batch)
                session.commit()
                batch = []

    if batch:
        session.execute(update_sql, batch)
        session.commit()

    return {
        "scanned": scanned,
        "recovered": recovered,
        "source_counts": dict(stats),
        "recovered_samples": recovered_samples,
        "unrecoverable_samples": unrecoverable_samples,
    }


def print_state_totals(session):
    counts = {
        "recruiters_with_state": session.query(Recruiter).filter(Recruiter.state.isnot(None), Recruiter.state != "").count(),
        "recruiters_missing": session.query(Recruiter).filter(Recruiter.state.is_(None) | (Recruiter.state == "")).count(),
        "companies_with_state": session.query(Company).filter(Company.state.isnot(None), Company.state != "").count(),
        "companies_missing": session.query(Company).filter(Company.state.is_(None) | (Company.state == "")).count(),
    }
    print(counts, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--max-passes", type=int, default=3)
    parser.add_argument("--min-ratio", type=float, default=0.60)
    parser.add_argument("--min-count", type=int, default=3)
    args = parser.parse_args()

    session = SessionLocal()
    try:
        companies = session.query(Company).all()
        domain_index = build_company_domain_state_index(companies)
        print({"domain_index": len(domain_index)}, flush=True)
        print_state_totals(session)

        for pass_index in range(1, args.max_passes + 1):
            majority_map = compute_company_majority_map(session, args.min_ratio, args.min_count)
            print({"pass": pass_index, "majority_companies": len(majority_map)}, flush=True)

            company_updates = recover_companies_from_location(session, companies)
            if company_updates:
                print({"pass": pass_index, "company_location_updates": company_updates}, flush=True)

            result = recover_recruiters_pass(session, domain_index, majority_map, args.batch_size)
            print({"pass": pass_index, **result}, flush=True)

            domain_index = build_company_domain_state_index(session.query(Company).all())
            if result["recovered"] == 0 and company_updates == 0:
                break

        print_state_totals(session)
    finally:
        session.close()


if __name__ == "__main__":
    main()
