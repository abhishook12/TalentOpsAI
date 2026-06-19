from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.database import SessionLocal
from app.models.models import Company, Recruiter
from app.utils.state_mapper import extract_state_detailed


BATCH_KEY = f"company_fill_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def merge_metadata(existing_value: str | None, evidence: dict) -> str:
    metadata = {}
    if existing_value:
        try:
            parsed = json.loads(existing_value) if isinstance(existing_value, str) else existing_value
            if isinstance(parsed, dict):
                metadata = dict(parsed)
        except Exception:
            metadata = {"raw_metadata": str(existing_value)}
    metadata["company_fill"] = evidence
    return json.dumps(metadata, default=str)


def main() -> None:
    db = SessionLocal()
    try:
        recruiters = (
            db.query(Recruiter, Company)
            .join(Company, Recruiter.company_id == Company.company_id, isouter=True)
            .filter(Recruiter.company_id.isnot(None))
            .filter(
                (Recruiter.location.is_(None)) | (Recruiter.location == "") |
                (Recruiter.state.is_(None)) | (Recruiter.state == "")
            )
            .all()
        )

        updated = 0
        location_filled = 0
        state_filled = 0
        scan_time = datetime.now(timezone.utc)

        for recruiter, company in recruiters:
            changed = False
            evidence = {
                "batch_key": BATCH_KEY,
                "company_id": company.company_id if company else None,
                "company_name": company.company_name if company else None,
            }

            if company and not recruiter.location and company.location:
                recruiter.location = company.location
                location_filled += 1
                changed = True
                evidence["location"] = company.location

            if not recruiter.state and company:
                inferred_state = company.state
                reason = "company_state"
                if not inferred_state and company.location:
                    inferred_state, reason = extract_state_detailed(company.location)
                if inferred_state:
                    recruiter.state = inferred_state
                    recruiter.state_source = "company_fill"
                    recruiter.state_confidence = "high" if company.state or company.location else "medium"
                    recruiter.state_reason = reason
                    state_filled += 1
                    changed = True
                    evidence["state"] = inferred_state
                    evidence["state_reason"] = reason

            if changed:
                recruiter.last_scan_at = scan_time
                recruiter.metadata_json = merge_metadata(recruiter.metadata_json, evidence)
                updated += 1

        db.commit()
        print(f"updated_recruiters={updated}")
        print(f"location_filled={location_filled}")
        print(f"state_filled={state_filled}")
        print(f"scanned={len(recruiters)}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
