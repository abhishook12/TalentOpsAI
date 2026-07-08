from __future__ import annotations

import csv
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.database import SessionLocal
from app.models.models import Company
from app.utils.normalizer import normalize_text


BATCH_KEY = f"exact_domain_company_assign_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
REVIEW_PATH = Path(__file__).resolve().parent / "outputs" / "company_domain_manual_review.csv"
EXCLUDED_DOMAINS = {
    "missing.local",
    "talentops.ai",
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "icloud.com",
    "aol.com",
    "live.com",
    "msn.com",
    ".com",
}
MANUAL_DOMAIN_NAMES = {
    "delayaa.com": "Daley and Associates",
    "orspartners.com": "ORS Partners",
    "on24.com": "ON24",
    "ssctech.com": "SS&C Technologies",
    "allstaffsolutions.net": "All Staff Solutions",
    "populusgroup.com": "Populus Group",
    "opensystemstech.com": "Open Systems Technologies",
    "theplanetforward.com": "Planet Forward",
    "libertyjobs.com": "Liberty Jobs",
    "isostech.com": "ISOtech",
    "workrise.com": "Workrise",
}


def domain_based_company_name(domain: str) -> str:
    if domain in MANUAL_DOMAIN_NAMES:
        return MANUAL_DOMAIN_NAMES[domain]
    root = domain.split(".")[0]
    tokens = [token for token in re.split(r"[-_]+", root) if token]
    if not tokens:
        return domain
    return " ".join(token.upper() if len(token) <= 3 else token.capitalize() for token in tokens)


def is_valid_company_domain(domain: str) -> bool:
    return bool(domain and "." in domain and domain not in EXCLUDED_DOMAINS and not domain.startswith("."))


def load_review_domains() -> dict[str, dict[str, str]]:
    if not REVIEW_PATH.exists():
        return {}
    with REVIEW_PATH.open(encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    return {
        row["domain"].strip().lower(): row
        for row in rows
        if is_valid_company_domain((row.get("domain") or "").strip().lower())
    }


def load_candidate_domains(db) -> list[str]:
    domain_limit_raw = os.getenv("EXACT_DOMAIN_LIMIT", "").strip()
    domain_limit = int(domain_limit_raw) if domain_limit_raw else None
    rows = db.execute(
        text(
            f"""
            WITH domain_stats AS (
                SELECT LOWER(SPLIT_PART(email, '@', 2)) AS domain,
                       COUNT(*) AS recruiters,
                       COUNT(*) FILTER (WHERE company_id IS NULL OR company_id = 0) AS missing_recruiters,
                       COUNT(DISTINCT company_id) FILTER (WHERE company_id IS NOT NULL AND company_id > 0) AS distinct_companies
                FROM recruiters
                WHERE email IS NOT NULL
                  AND email LIKE '%%@%%'
                GROUP BY LOWER(SPLIT_PART(email, '@', 2))
            )
            SELECT domain
            FROM domain_stats
            WHERE missing_recruiters > 0
               OR distinct_companies > 1
            ORDER BY recruiters DESC, domain
            {f"LIMIT {domain_limit}" if domain_limit else ""}
            """
        )
    ).scalars().all()
    return [domain for domain in rows if is_valid_company_domain((domain or "").strip().lower())]


def find_company_by_domain(db, domain: str) -> Company | None:
    return (
        db.query(Company)
        .filter((Company.website == domain) | (Company.email_pattern == domain))
        .order_by(Company.company_id.asc())
        .first()
    )


def clean_top_linked_company_id(row: dict[str, str]) -> int | None:
    company_id_raw = (row.get("top_linked_company_id") or "").strip()
    company_name = (row.get("top_linked_company_name") or "").strip()
    if not company_id_raw:
        return None
    if company_name in {"", "--", "MI", "FL", "PA", "CA", "NY", "TX"}:
        return None
    if company_name.isdigit():
        return None
    if "@" in company_name:
        return None
    if len(company_name) <= 2:
        return None
    try:
        return int(company_id_raw)
    except ValueError:
        return None


def sync_company_name(company: Company, domain: str) -> None:
    desired_name = domain_based_company_name(domain)
    if company.company_name != desired_name:
        company.company_name = desired_name
        company.normalized_company_name = normalize_text(desired_name)


def ensure_company_for_domain(db, domain: str, row: dict[str, str] | None) -> Company:
    company = find_company_by_domain(db, domain)
    if company:
        sync_company_name(company, domain)
        if not company.website:
            company.website = domain
        elif not company.email_pattern:
            company.email_pattern = domain
        return company

    top_linked_company_id = clean_top_linked_company_id(row or {})
    if top_linked_company_id is not None:
        company = db.query(Company).filter(Company.company_id == top_linked_company_id).first()
        if company:
            sync_company_name(company, domain)
            if not company.website:
                company.website = domain
            elif not company.email_pattern:
                company.email_pattern = domain
            return company

    name = domain_based_company_name(domain)
    company = Company(
        company_name=name,
        normalized_company_name=normalize_text(name),
        website=domain,
        data_source="exact_domain_grouping",
        trust_score=40,
    )
    db.add(company)
    db.flush()
    return company


def main() -> None:
    BATCH_SIZE = 100  # smaller batches to stay within Render free-tier limits
    SLEEP_BETWEEN = 2  # seconds between batches to let DB breathe

    # Load domains list with a throwaway session
    db = SessionLocal()
    try:
        db.execute(text("SET statement_timeout TO 0"))
        review_rows = load_review_domains()
        domains = load_candidate_domains(db)
        db.commit()
    finally:
        db.close()

    total_domains = len(domains)
    total_created_companies = 0
    total_reused_companies = 0
    total_updated_recruiters = 0
    now = datetime.now(timezone.utc)

    print(f"Total domains to process: {total_domains}")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Estimated batches: {(total_domains + BATCH_SIZE - 1) // BATCH_SIZE}")
    sys.stdout.flush()

    for batch_start in range(0, total_domains, BATCH_SIZE):
        batch_domains = domains[batch_start : batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        max_retries = 3
        batch_updated = 0
        created_companies = 0
        reused_companies = 0

        for attempt in range(1, max_retries + 1):
            db = SessionLocal()
            try:
                db.execute(text("SET statement_timeout TO 0"))
                domain_mappings: list[dict[str, int | str]] = []
                created_companies = 0
                reused_companies = 0

                for domain in batch_domains:
                    row = review_rows.get(domain)
                    existing = find_company_by_domain(db, domain)
                    company = ensure_company_for_domain(db, domain, row)
                    domain_mappings.append({"domain": domain, "company_id": company.company_id})

                    if existing:
                        reused_companies += 1
                    elif company.company_id:
                        top_linked_company_id = clean_top_linked_company_id(row or {})
                        if top_linked_company_id is not None and company.company_id == top_linked_company_id:
                            reused_companies += 1
                        else:
                            created_companies += 1

                db.flush()

                if domain_mappings:
                    db.execute(text("DROP TABLE IF EXISTS temp_domain_company_map"))
                    db.execute(
                        text(
                            """
                            CREATE TEMP TABLE temp_domain_company_map (
                                domain TEXT PRIMARY KEY,
                                company_id BIGINT NOT NULL
                            )
                            """
                        )
                    )
                    db.execute(
                        text(
                            """
                            INSERT INTO temp_domain_company_map (domain, company_id)
                            VALUES (:domain, :company_id)
                            """
                        ),
                        domain_mappings,
                    )
                    result = db.execute(
                        text(
                            """
                            UPDATE recruiters AS r
                            SET company_id = m.company_id,
                                last_scan_at = :last_scan_at
                            FROM temp_domain_company_map AS m
                            WHERE r.email IS NOT NULL
                              AND LOWER(SPLIT_PART(r.email, '@', 2)) = m.domain
                              AND COALESCE(r.company_id, 0) <> m.company_id
                            """
                        ),
                        {"last_scan_at": now},
                    )
                    batch_updated = int(result.rowcount or 0)
                    db.execute(text("DROP TABLE IF EXISTS temp_domain_company_map"))
                else:
                    batch_updated = 0

                db.commit()
                break  # success

            except Exception as exc:
                try:
                    db.rollback()
                except Exception:
                    pass
                if attempt < max_retries:
                    wait = attempt * 10
                    print(f"  [Batch {batch_num}] Error on attempt {attempt}: {str(exc)[:80]}... retrying in {wait}s")
                    sys.stdout.flush()
                    time.sleep(wait)
                    continue
                print(f"  [Batch {batch_num}] FAILED after {max_retries} attempts, skipping: {str(exc)[:120]}")
                sys.stdout.flush()
                batch_updated = 0
                created_companies = 0
                reused_companies = 0
                break  # skip this batch instead of crashing
            finally:
                db.close()

        total_created_companies += created_companies
        total_reused_companies += reused_companies
        total_updated_recruiters += batch_updated
        processed = min(batch_start + BATCH_SIZE, total_domains)
        print(
            f"[Batch {batch_num}] {processed}/{total_domains} domains | "
            f"+{created_companies} companies | {batch_updated} recruiters linked | "
            f"Running totals: {total_created_companies} created, {total_updated_recruiters} linked"
        )
        sys.stdout.flush()
        time.sleep(SLEEP_BETWEEN)

    print(f"\n=== COMPLETE ===")
    print(f"batch_key={BATCH_KEY}")
    print(f"updated_recruiters={total_updated_recruiters}")
    print(f"created_companies={total_created_companies}")
    print(f"reused_companies={total_reused_companies}")


if __name__ == "__main__":
    main()
