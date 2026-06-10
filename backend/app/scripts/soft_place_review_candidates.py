from __future__ import annotations

import argparse
import csv
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import sys

from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.database import SessionLocal
from app.models.models import Company, Recruiter
from app.utils.state_mapper import ABBR_TO_NAME, extract_state_detailed, normalize_state
from app.utils.state_recovery import build_company_domain_state_index, infer_state_from_sources

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def extract_city(location: str | None) -> str | None:
    if not location:
        return None
    loc_upper = str(location).upper()

    known_cities = [
        "ATLANTA", "AUSTIN", "BALTIMORE", "BOSTON", "CHARLOTTE", "CHICAGO", "DALLAS",
        "DENVER", "DETROIT", "HOUSTON", "INDIANAPOLIS", "JACKSONVILLE", "LOS ANGELES",
        "MIAMI", "MINNEAPOLIS", "NASHVILLE", "NEW YORK", "NYC", "ORLANDO", "PHOENIX",
        "PITTSBURGH", "PORTLAND", "RALEIGH", "RICHMOND", "SACRAMENTO", "SAN ANTONIO",
        "SAN DIEGO", "SAN FRANCISCO", "SAN JOSE", "SEATTLE", "ST. LOUIS", "TAMPA",
        "BAY AREA", "SILICON VALLEY", "DFW", "RTP", "RESEARCH TRIANGLE", "DALLAS METRO",
        "ATLANTA METRO", "NYC METRO", "NEW YORK METRO", "CHARLOTTE METRO", "SOUTH FLORIDA",
        "CENTRAL FLORIDA",
    ]
    for city in known_cities:
        if re.search(r"\b" + re.escape(city) + r"\b", loc_upper):
            return city.title()

    parts = [p.strip() for p in re.split(r"[,/|-]+", str(location)) if p.strip()]
    if not parts:
        return None

    first = parts[0]
    if first.upper() not in ABBR_TO_NAME and first.upper() not in ABBR_TO_NAME.values():
        return first.title()
    return None


def merge_reason(existing: str | None, new_reason: str) -> str:
    reasons = [part.strip() for part in str(existing or "").split(";") if part.strip()]
    if new_reason not in reasons:
        reasons.append(new_reason)
    return "; ".join(reasons)


def safe_json(value):
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except Exception:
        return {"raw": str(value)}


def classify_soft_candidate(recruiter: Recruiter, company_by_id: dict[int, Company], domain_index):
    company = company_by_id.get(recruiter.company_id) if recruiter.company_id else None
    sources = [
        ("recruiter_location", recruiter.location),
        ("company_location", company.location if company else None),
    ]
    state_result = infer_state_from_sources(sources, domain_index=domain_index)
    city_value = extract_city(recruiter.location or (company.location if company else None))
    city_state = None
    city_reason = None
    if not state_result and (recruiter.location or (company.location if company else None)):
        location_text = recruiter.location or (company.location if company else None)
        city_state, city_reason = extract_state_detailed(location_text)
        if city_state:
            state_result = {
                "state": city_state,
                "state_source": "soft_location",
                "state_confidence": "low",
                "state_reason": city_reason or "location_parse",
                "evidence": location_text[:500],
            }

    if not state_result:
        return {
            "applies": bool(recruiter.location or (company.location if company else None)),
            "state": None,
            "state_source": None,
            "state_confidence": None,
            "state_reason": "suspicious_location_only" if (recruiter.location or (company.location if company else None)) else "no_location_evidence",
            "city": city_value,
            "confidence": "manual_review",
            "review_reason": "Suspicious placement candidate: has location text but no clear state match",
            "evidence": recruiter.location or (company.location if company else None),
        }

    source = state_result.get("state_source")
    source_is_soft = source in {"recruiter_location", "company_location", "soft_location"}
    location_text = recruiter.location or (company.location if company else None)
    review_reason = "Suspicious soft placement from location/company evidence"

    return {
        "applies": bool(source_is_soft),
        "state": state_result["state"],
        "state_source": f"{source}_soft" if source and not str(source).endswith("_soft") else source,
        "state_confidence": "low" if source_is_soft else state_result.get("state_confidence"),
        "state_reason": state_result.get("state_reason") or city_reason or "soft_location_review",
        "city": city_value,
        "confidence": "manual_review",
        "review_reason": review_reason,
        "evidence": state_result.get("evidence") or location_text,
    }


def main():
    parser = argparse.ArgumentParser(description="Soft-place suspicious/unmapped recruiters into location-derived states and keep them flagged for review.")
    parser.add_argument("--apply", action="store_true", help="Persist the soft placement updates.")
    parser.add_argument("--limit", type=int, default=0, help="Optional max records to update (0 = all).")
    parser.add_argument("--after-id", type=int, default=0, help="Only scan recruiters after this ID.")
    parser.add_argument("--sample-size", type=int, default=20, help="How many example records to include.")
    args = parser.parse_args()

    session = SessionLocal()
    try:
        companies = session.query(Company).all()
        company_by_id = {company.company_id: company for company in companies}
        domain_index = build_company_domain_state_index(companies)

        recruiters = (
            session.query(Recruiter)
            .filter(
                Recruiter.recruiter_id > args.after_id,
                (Recruiter.needs_review == True) |
                (Recruiter.state.is_(None)) | (Recruiter.state == "") |
                (Recruiter.location.isnot(None)) | (Recruiter.location != "")
            )
            .order_by(Recruiter.recruiter_id.asc())
            .all()
        )

        updated_rows = []
        flagged_samples = []
        source_counts = Counter()
        state_counts = Counter()
        total_candidates = 0
        already_flagged = 0
        pending_updates = []
        last_processed_id = None
        update_sql = """
            UPDATE recruiters
            SET needs_review = :needs_review,
                review_reason = :review_reason,
                location_confidence = :location_confidence,
                normalized_city = :normalized_city,
                metadata_json = :metadata_json,
                state = COALESCE(:state, state),
                state_source = COALESCE(:state_source, state_source),
                state_confidence = COALESCE(:state_confidence, state_confidence),
                state_reason = COALESCE(:state_reason, state_reason)
            WHERE recruiter_id = :recruiter_id
        """

        for recruiter in recruiters:
            company = company_by_id.get(recruiter.company_id) if recruiter.company_id else None
            has_location = bool((recruiter.location or "").strip() or (company.location if company and company.location else "").strip())
            if not has_location:
                continue

            is_missing_state = not bool((recruiter.state or "").strip())
            is_review_candidate = bool(recruiter.needs_review) or is_missing_state or (recruiter.location_confidence in {"low", "manual_review"}) or bool((recruiter.review_reason or "").strip())
            if not is_review_candidate:
                continue

            classification = classify_soft_candidate(recruiter, company_by_id, domain_index)
            if not classification["applies"]:
                continue

            total_candidates += 1
            current_state = (recruiter.state or "").strip()
            current_review = bool(recruiter.needs_review)
            if current_review:
                already_flagged += 1

            # Always keep the person in the correct place if we can derive a state.
            new_state = classification["state"] or (normalize_state(recruiter.location) if recruiter.location else None)
            if not new_state and company and company.location:
                new_state = normalize_state(company.location)

            metadata = safe_json(recruiter.metadata_json)
            metadata.setdefault("state_recovery", {})
            metadata["state_recovery"]["soft_placement"] = {
                "applied_at": datetime.now(timezone.utc).isoformat(),
                "state": new_state,
                "source": classification["state_source"],
                "confidence": classification["state_confidence"] or "low",
                "reason": classification["state_reason"],
                "evidence": classification["evidence"],
                "review_reason": classification["review_reason"],
            }

            updates = {
                "needs_review": True,
                "review_reason": merge_reason(recruiter.review_reason, classification["review_reason"]),
                "location_confidence": "manual_review",
                "normalized_city": recruiter.normalized_city or classification["city"],
                "metadata_json": json.dumps(metadata, default=str),
            }

            if new_state:
                updates["state"] = new_state
                updates["state_source"] = classification["state_source"] or "soft_location"
                updates["state_confidence"] = classification["state_confidence"] or "low"
                updates["state_reason"] = classification["state_reason"]

            db_update = {
                "recruiter_id": recruiter.recruiter_id,
                "needs_review": updates["needs_review"],
                "review_reason": updates["review_reason"],
                "location_confidence": updates["location_confidence"],
                "normalized_city": updates["normalized_city"],
                "metadata_json": updates["metadata_json"],
                "state": updates.get("state"),
                "state_source": updates.get("state_source"),
                "state_confidence": updates.get("state_confidence"),
                "state_reason": updates.get("state_reason"),
            }
            if args.apply:
                pending_updates.append(db_update)
                if len(pending_updates) >= 500:
                    session.execute(text(update_sql), pending_updates)
                    session.commit()
                    pending_updates.clear()

            source_counts[updates.get("state_source") or "no_state"] += 1
            if new_state:
                state_counts[new_state] += 1

            record = {
                "recruiter_id": recruiter.recruiter_id,
                "recruiter_name": recruiter.recruiter_name,
                "email": recruiter.email,
                "company": company.company_name if company else None,
                "location": recruiter.location or (company.location if company else None),
                "old_state": current_state or None,
                "new_state": new_state,
                "state_source": updates.get("state_source"),
                "review_reason": updates["review_reason"],
                "city": classification["city"],
                "already_flagged": current_review,
            }
            updated_rows.append(record)
            if len(flagged_samples) < args.sample_size:
                flagged_samples.append(record)
            last_processed_id = recruiter.recruiter_id

            if args.limit and len(updated_rows) >= args.limit:
                break

        if args.apply:
            if pending_updates:
                session.execute(text(update_sql), pending_updates)
            session.commit()
        else:
            session.rollback()

        report = {
            "mode": "apply" if args.apply else "dry_run",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_candidates": total_candidates,
            "updated_rows": len(updated_rows),
            "already_flagged": already_flagged,
            "state_counts": dict(state_counts.most_common()),
            "source_counts": dict(source_counts.most_common()),
            "last_processed_id": last_processed_id,
            "next_after_id": last_processed_id or args.after_id,
            "samples": flagged_samples,
            "notes": [
                "Soft-placed people with location evidence into the most likely state when possible.",
                "Every updated record stays flagged for manual review.",
                "No record was unflagged by this pass.",
            ],
        }

        report_path = OUTPUT_DIR / "soft_place_review_candidates_report.json"
        csv_path = OUTPUT_DIR / "soft_place_review_candidates.csv"
        report["report_path"] = str(report_path)
        report["csv_path"] = str(csv_path)

        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                "recruiter_id", "recruiter_name", "email", "company", "location", "old_state", "new_state",
                "state_source", "review_reason", "city", "already_flagged",
            ])
            writer.writeheader()
            writer.writerows(updated_rows)

        print(json.dumps(report, indent=2))
    except Exception as exc:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
