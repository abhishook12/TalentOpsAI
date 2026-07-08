"""
Bulk assign company_id to recruiters by email domain.
Uses pure SQL set operations instead of per-domain Python loops.
Designed for Render free-tier Postgres (low memory, connection timeouts).
"""
from __future__ import annotations

import os
import re
import sys
import time
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from sqlalchemy import text
from app.database import SessionLocal
from app.utils.normalizer import normalize_text

EXCLUDED_DOMAINS_STR = "', '".join([
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "aol.com", "live.com", "msn.com", "missing.local", "talentops.ai",
    "comcast.net", "att.net", "sbcglobal.net", "verizon.net", "ymail.com",
    "mail.com", "protonmail.com", "zoho.com", "me.com", "mac.com",
])


def step1_link_existing_companies():
    """Link recruiters to companies that already exist (by website or email_pattern match)."""
    total_linked = 0
    batch_num = 0
    while True:
        batch_num += 1
        db = SessionLocal()
        try:
            db.execute(text("SET statement_timeout TO '60s'"))
            # Process a limited chunk: find up to 5000 recruiters to update
            result = db.execute(text("""
                UPDATE recruiters AS r
                SET company_id = sub.company_id,
                    last_scan_at = NOW()
                FROM (
                    SELECT r2.recruiter_id, c.company_id
                    FROM recruiters r2
                    JOIN companies c ON (
                        LOWER(SPLIT_PART(r2.email, '@', 2)) = LOWER(c.website)
                        OR LOWER(SPLIT_PART(r2.email, '@', 2)) = LOWER(c.email_pattern)
                    )
                    WHERE (r2.company_id IS NULL OR r2.company_id = 0)
                      AND r2.email IS NOT NULL
                      AND r2.email LIKE '%%@%%'
                    LIMIT 5000
                ) AS sub
                WHERE r.recruiter_id = sub.recruiter_id
            """))
            linked = result.rowcount or 0
            db.commit()
            if linked == 0:
                break
            total_linked += linked
            print(f"  [Step 1 - Batch {batch_num}] Linked {linked:,} recruiters (total: {total_linked:,})")
            sys.stdout.flush()
            time.sleep(2)
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            print(f"  [Step 1 - Batch {batch_num}] Error: {str(e)[:120]}, retrying in 5s...")
            sys.stdout.flush()
            time.sleep(5)
        finally:
            db.close()

    print(f"[Step 1] Total linked: {total_linked:,} recruiters to existing companies")
    sys.stdout.flush()
    return total_linked


def step2_link_by_majority_vote():
    """For domains where most recruiters already point to a company, assign the rest too."""
    total_linked = 0
    batch_num = 0
    while True:
        batch_num += 1
        db = SessionLocal()
        try:
            db.execute(text("SET statement_timeout TO '60s'"))
            result = db.execute(text("""
                WITH domain_majority AS (
                    SELECT
                        LOWER(SPLIT_PART(email, '@', 2)) AS domain,
                        company_id,
                        COUNT(*) AS cnt,
                        SUM(COUNT(*)) OVER (PARTITION BY LOWER(SPLIT_PART(email, '@', 2))) AS total
                    FROM recruiters
                    WHERE email IS NOT NULL AND email LIKE '%%@%%'
                      AND company_id IS NOT NULL AND company_id > 0
                    GROUP BY LOWER(SPLIT_PART(email, '@', 2)), company_id
                ),
                top_company AS (
                    SELECT DISTINCT ON (domain) domain, company_id
                    FROM domain_majority
                    WHERE cnt::float / NULLIF(total, 0) >= 0.6
                      AND cnt >= 2
                    ORDER BY domain, cnt DESC
                    LIMIT 200
                )
                UPDATE recruiters AS r
                SET company_id = tc.company_id,
                    last_scan_at = NOW()
                FROM top_company AS tc
                WHERE (r.company_id IS NULL OR r.company_id = 0)
                  AND r.email IS NOT NULL
                  AND LOWER(SPLIT_PART(r.email, '@', 2)) = tc.domain
            """))
            linked = result.rowcount or 0
            db.commit()
            if linked == 0:
                break
            total_linked += linked
            print(f"  [Step 2 - Batch {batch_num}] Linked {linked:,} recruiters (total: {total_linked:,})")
            sys.stdout.flush()
            time.sleep(2)
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            print(f"  [Step 2 - Batch {batch_num}] Error: {str(e)[:120]}, retrying in 5s...")
            sys.stdout.flush()
            time.sleep(5)
        finally:
            db.close()

    print(f"[Step 2] Total linked: {total_linked:,} recruiters via majority-vote")
    sys.stdout.flush()
    return total_linked


def step3_create_companies_for_orphan_domains(batch_size: int = 200):
    """Create new company records for domains that have no match, then link recruiters."""
    db = SessionLocal()
    try:
        db.execute(text("SET statement_timeout TO '60s'"))
        rows = db.execute(text(f"""
            SELECT LOWER(SPLIT_PART(email, '@', 2)) AS domain, COUNT(*) AS cnt
            FROM recruiters
            WHERE email IS NOT NULL AND email LIKE '%%@%%'
              AND (company_id IS NULL OR company_id = 0)
              AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ('{EXCLUDED_DOMAINS_STR}')
              AND SPLIT_PART(email, '@', 2) LIKE '%%.%%'
              AND LENGTH(SPLIT_PART(email, '@', 2)) > 3
            GROUP BY LOWER(SPLIT_PART(email, '@', 2))
            ORDER BY cnt DESC
        """)).mappings().all()
        orphan_domains = [(r["domain"], r["cnt"]) for r in rows]
        db.commit()
    finally:
        db.close()

    print(f"[Step 3] Found {len(orphan_domains):,} orphan domains to create companies for")
    sys.stdout.flush()

    total_created = 0
    total_linked = 0

    for i in range(0, len(orphan_domains), batch_size):
        batch = orphan_domains[i : i + batch_size]
        batch_num = i // batch_size + 1
        batch_created = 0
        batch_linked = 0
        db = SessionLocal()
        try:
            db.execute(text("SET statement_timeout TO '120s'"))

            for domain, cnt in batch:
                # Check if company already exists
                exists = db.execute(text(
                    "SELECT company_id FROM companies WHERE LOWER(website) = :d OR LOWER(email_pattern) = :d LIMIT 1"
                ), {"d": domain}).scalar()

                if not exists:
                    # Create company name from domain
                    root = domain.split(".")[0]
                    tokens = [t for t in re.split(r"[-_]+", root) if t]
                    name = " ".join(t.upper() if len(t) <= 3 else t.capitalize() for t in tokens) if tokens else domain

                    result = db.execute(text("""
                        INSERT INTO companies (company_name, normalized_company_name, website, data_source, trust_score, is_active, is_tracked)
                        VALUES (:name, :norm_name, :website, 'exact_domain_grouping', 40, true, false)
                        RETURNING company_id
                    """), {"name": name, "norm_name": normalize_text(name), "website": domain})
                    company_id = result.scalar()
                    batch_created += 1
                else:
                    company_id = exists

                # Link recruiters
                link_result = db.execute(text("""
                    UPDATE recruiters
                    SET company_id = :cid, last_scan_at = NOW()
                    WHERE (company_id IS NULL OR company_id = 0)
                      AND LOWER(SPLIT_PART(email, '@', 2)) = :domain
                """), {"cid": company_id, "domain": domain})
                batch_linked += link_result.rowcount or 0

            db.commit()
            total_created += batch_created
            total_linked += batch_linked
            processed = min(i + batch_size, len(orphan_domains))
            print(
                f"  [Batch {batch_num}] {processed:,}/{len(orphan_domains):,} domains | "
                f"+{batch_created} companies | {batch_linked:,} recruiters linked | "
                f"Totals: {total_created:,} created, {total_linked:,} linked"
            )
            sys.stdout.flush()
            time.sleep(2)

        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            print(f"  [Batch {batch_num}] Error: {str(e)[:120]}, skipping...")
            sys.stdout.flush()
            time.sleep(5)
        finally:
            db.close()

    return total_created, total_linked


def get_current_stats():
    db = SessionLocal()
    try:
        total = db.execute(text("SELECT COUNT(*) FROM recruiters")).scalar()
        with_company = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE company_id IS NOT NULL AND company_id > 0")).scalar()
        without_company = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE company_id IS NULL OR company_id = 0")).scalar()
        total_companies = db.execute(text("SELECT COUNT(*) FROM companies")).scalar()
        return total, with_company, without_company, total_companies
    finally:
        db.close()


def main():
    print("=" * 60)
    print("BULK DOMAIN-TO-COMPANY ASSIGNMENT")
    print("=" * 60)

    total, with_co, without_co, companies = get_current_stats()
    print(f"\nBEFORE:")
    print(f"  Total recruiters:    {total:,}")
    print(f"  With company:        {with_co:,}")
    print(f"  Without company:     {without_co:,}")
    print(f"  Total companies:     {companies:,}")
    print()
    sys.stdout.flush()

    linked1 = step1_link_existing_companies()
    time.sleep(3)

    linked2 = step2_link_by_majority_vote()
    time.sleep(3)

    created3, linked3 = step3_create_companies_for_orphan_domains()

    total, with_co2, without_co2, companies2 = get_current_stats()
    print(f"\n{'=' * 60}")
    print(f"AFTER:")
    print(f"  Total recruiters:    {total:,}")
    print(f"  With company:        {with_co2:,} (+{with_co2 - with_co:,})")
    print(f"  Without company:     {without_co2:,} ({without_co2 - without_co:,})")
    print(f"  Total companies:     {companies2:,} (+{companies2 - companies:,})")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
