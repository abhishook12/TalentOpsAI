from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.database import SessionLocal
from app.models.models import Company, Recruiter
from app.utils.normalizer import extract_domain
from app.utils.state_recovery import is_generic_domain
from app.utils.state_mapper import extract_state_detailed


BATCH_KEY = f"email_domain_company_assign_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

MANUAL_DOMAIN_COMPANY_MAP = {
    "vaco.com": 41827,
    "actalentservices.com": 49144,
    "addisongroup.com": 23844,
    "theintersectgroup.com": 48974,
    "pdstech.com": 41913,
    "judge.com": 21489,
    "tandymgroup.com": 49075,
    "idr-inc.com": 39079,
}


def merge_metadata(existing_value: str | None, evidence: dict) -> str:
    metadata = {}
    if existing_value:
        try:
            parsed = json.loads(existing_value) if isinstance(existing_value, str) else existing_value
            if isinstance(parsed, dict):
                metadata = dict(parsed)
        except Exception:
            metadata = {"raw_metadata": str(existing_value)}
    metadata["email_domain_company_assign"] = evidence
    return json.dumps(metadata, default=str)


def build_company_domain_map(companies: list[Company]) -> dict[str, list[Company]]:
    domain_map: dict[str, list[Company]] = defaultdict(list)
    for company in companies:
        for source in (company.website, company.email_pattern):
            domain = extract_domain(source)
            if not domain or is_generic_domain(domain):
                continue
            domain_map[domain].append(company)
    return domain_map


def choose_company(candidates: list[Company]) -> Company | None:
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    ranked = sorted(
        candidates,
        key=lambda company: (
            0 if company.state else 1,
            0 if company.location else 1,
            -(company.trust_score or 0),
            company.company_id or 0,
        ),
    )
    return ranked[0]


def company_by_id_map(companies: list[Company]) -> dict[int, Company]:
    return {company.company_id: company for company in companies if company.company_id is not None}


def build_recruiter_domain_company_map(db) -> dict[str, int]:
    rows = db.execute(text(
        """
        SELECT
            LOWER(SPLIT_PART(email, '@', 2)) AS domain,
            company_id,
            COUNT(*) AS cnt
        FROM recruiters
        WHERE email IS NOT NULL
          AND email LIKE '%@%'
          AND company_id IS NOT NULL
          AND company_id > 0
        GROUP BY LOWER(SPLIT_PART(email, '@', 2)), company_id
        """
    )).mappings().all()

    buckets: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for row in rows:
        domain = extract_domain(row["domain"])
        if not domain or is_generic_domain(domain):
            continue
        buckets[domain].append((int(row["company_id"]), int(row["cnt"])))

    resolved: dict[str, int] = {}
    for domain, items in buckets.items():
        items = sorted(items, key=lambda pair: (-pair[1], pair[0]))
        top_company_id, top_count = items[0]
        total = sum(count for _, count in items)
        second_count = items[1][1] if len(items) > 1 else 0
        if top_count >= 3 and top_count / total >= 0.6 and top_count > second_count:
            resolved[domain] = top_company_id
    return resolved


def main() -> None:
    db = SessionLocal()
    try:
        companies = db.query(Company).all()
        companies_by_id = company_by_id_map(companies)
        domain_map = build_company_domain_map(companies)
        recruiter_domain_company_map = build_recruiter_domain_company_map(db)

        recruiter_rows = (
            db.query(Recruiter)
            .filter((Recruiter.company_id.is_(None)) | (Recruiter.company_id == 0))
            .filter(Recruiter.email.isnot(None))
            .all()
        )

        company_domain_counts = Counter()
        updated = 0
        company_assigned = 0
        state_filled = 0
        location_filled = 0
        skipped_conflicts = 0
        skipped_no_match = 0
        scan_time = datetime.now(timezone.utc)

        for recruiter in recruiter_rows:
            domain = extract_domain(recruiter.email)
            if not domain:
                skipped_no_match += 1
                continue

            manual_company_id = MANUAL_DOMAIN_COMPANY_MAP.get(domain)
            majority_company_id = recruiter_domain_company_map.get(domain)
            company = companies_by_id.get(manual_company_id) if manual_company_id else None
            if not company:
                company = companies_by_id.get(majority_company_id) if majority_company_id else None
            if not company:
                company = choose_company(domain_map.get(domain, []))

            if not company:
                skipped_no_match += 1
                continue

            if len(domain_map.get(domain, [])) > 1 and manual_company_id is None and majority_company_id is None:
                skipped_conflicts += 1
                continue

            changed = False
            if recruiter.company_id != company.company_id:
                recruiter.company_id = company.company_id
                company_assigned += 1
                company_domain_counts[domain] += 1
                changed = True

            if not recruiter.location and company.location:
                recruiter.location = company.location
                location_filled += 1
                changed = True

            if not recruiter.state:
                inferred_state, reason = extract_state_detailed(company.location or company.state or "")
                if company.state:
                    recruiter.state = company.state
                    recruiter.state_source = "email_domain_company"
                    recruiter.state_confidence = "high"
                    recruiter.state_reason = "company_state"
                    state_filled += 1
                    changed = True
                elif inferred_state:
                    recruiter.state = inferred_state
                    recruiter.state_source = "email_domain_company"
                    recruiter.state_confidence = "high" if company.location else "medium"
                    recruiter.state_reason = reason
                    state_filled += 1
                    changed = True

            if changed:
                recruiter.last_scan_at = scan_time
                recruiter.metadata_json = merge_metadata(
                    recruiter.metadata_json,
                    {
                        "batch_key": BATCH_KEY,
                        "domain": domain,
                        "company_id": company.company_id,
                        "company_name": company.company_name,
                        "company_domain": extract_domain(company.website or company.email_pattern or ""),
                    },
                )
                updated += 1

        db.commit()

        print(f"updated_recruiters={updated}")
        print(f"company_assigned={company_assigned}")
        print(f"state_filled={state_filled}")
        print(f"location_filled={location_filled}")
        print(f"skipped_conflicts={skipped_conflicts}")
        print(f"skipped_no_match={skipped_no_match}")
        for domain, count in company_domain_counts.most_common(25):
            print(f"{domain} -> {count}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
