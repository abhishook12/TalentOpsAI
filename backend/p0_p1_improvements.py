#!/usr/bin/env python
"""P0 + P1 Database Improvement Engine - TalentOpsAI"""
from __future__ import annotations
import sys, os, time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

def run_improvements():
    start_time = time.time()
    db = SessionLocal()
    results = {}

    try:
        # ============================================================
        # P0 - ISSUE #1: Classify 67,341 NULL is_active records
        # ============================================================
        print("=" * 60)
        print("P0 - ISSUE #1: Classifying NULL is_active records...")
        print("=" * 60)

        # Records with valid email + company = ACTIVE
        r1a = db.execute(text("""
            UPDATE recruiters
            SET is_active = true
            WHERE is_active IS NULL
              AND email IS NOT NULL AND email != ''
              AND email NOT LIKE '%@missing.local%'
              AND email_status IS DISTINCT FROM 'invalid'
              AND company_id IS NOT NULL;
        """))
        print(f"   -> Set ACTIVE (valid email + company): {r1a.rowcount}")

        # Records with valid email but no company = ACTIVE
        r1b = db.execute(text("""
            UPDATE recruiters
            SET is_active = true
            WHERE is_active IS NULL
              AND email IS NOT NULL AND email != ''
              AND email NOT LIKE '%@missing.local%'
              AND email_status IS DISTINCT FROM 'invalid';
        """))
        print(f"   -> Set ACTIVE (valid email, no company): {r1b.rowcount}")

        # Records with only dummy email and no phone = INACTIVE
        r1c = db.execute(text("""
            UPDATE recruiters
            SET is_active = false
            WHERE is_active IS NULL
              AND (email IS NULL OR email = '' OR email LIKE '%@missing.local%' OR email_status = 'invalid')
              AND (phone IS NULL OR phone = '');
        """))
        print(f"   -> Set INACTIVE (no valid email, no phone): {r1c.rowcount}")

        # Remaining NULLs with phone but bad email = ACTIVE (phone is valuable)
        r1d = db.execute(text("""
            UPDATE recruiters
            SET is_active = true
            WHERE is_active IS NULL
              AND phone IS NOT NULL AND phone != '';
        """))
        print(f"   -> Set ACTIVE (has phone): {r1d.rowcount}")

        # Any remaining NULLs = INACTIVE
        r1e = db.execute(text("""
            UPDATE recruiters
            SET is_active = false
            WHERE is_active IS NULL;
        """))
        print(f"   -> Set INACTIVE (remaining): {r1e.rowcount}")

        results["issue_1_activated"] = r1a.rowcount + r1b.rowcount + r1d.rowcount
        results["issue_1_deactivated"] = r1c.rowcount + r1e.rowcount

        # ============================================================
        # P0 - ISSUE #4: Reset needs_review flags intelligently
        # ============================================================
        print("\n" + "=" * 60)
        print("P0 - ISSUE #4: Resetting needs_review flags...")
        print("=" * 60)

        # Clear needs_review for records that have: valid email + state + company
        r4a = db.execute(text("""
            UPDATE recruiters
            SET needs_review = false
            WHERE needs_review = true
              AND email IS NOT NULL AND email != ''
              AND email NOT LIKE '%@missing.local%'
              AND email_status IS DISTINCT FROM 'invalid'
              AND state IS NOT NULL AND state != ''
              AND company_id IS NOT NULL
              AND recruiter_name IS NOT NULL AND recruiter_name != ''
              AND recruiter_name != 'Unknown'
              AND recruiter_name NOT LIKE '%@%';
        """))
        print(f"   -> Cleared (valid email+state+company+name): {r4a.rowcount}")

        # Clear needs_review for records with valid email + phone (high value contacts)
        r4b = db.execute(text("""
            UPDATE recruiters
            SET needs_review = false
            WHERE needs_review = true
              AND email IS NOT NULL AND email != ''
              AND email NOT LIKE '%@missing.local%'
              AND email_status IS DISTINCT FROM 'invalid'
              AND phone IS NOT NULL AND phone != ''
              AND recruiter_name IS NOT NULL AND recruiter_name != ''
              AND recruiter_name != 'Unknown';
        """))
        print(f"   -> Cleared (valid email+phone+name): {r4b.rowcount}")

        remaining_review = db.execute(text(
            "SELECT count(*) FROM recruiters WHERE needs_review = true"
        )).scalar()
        print(f"   -> Remaining needs_review: {remaining_review}")
        results["issue_4_cleared"] = r4a.rowcount + r4b.rowcount
        results["issue_4_remaining"] = remaining_review

        # ============================================================
        # P1 - ISSUE #12: Clean 284 fake phone numbers
        # ============================================================
        print("\n" + "=" * 60)
        print("P1 - ISSUE #12: Cleaning fake phone numbers...")
        print("=" * 60)

        r12 = db.execute(text("""
            UPDATE recruiters
            SET phone = NULL
            WHERE phone IN (
                '000-000-0000', '0000000000', '000-0000000', '0000000',
                '8888888888', '888-888-8888',
                '9999999999', '999-999-9999',
                '1111111111', '111-111-1111',
                '1234567890', '123-456-7890'
            );
        """))
        print(f"   -> Cleaned fake phones: {r12.rowcount}")
        results["issue_12_cleaned"] = r12.rowcount

        # ============================================================
        # P1 - ISSUE #11: Fix malformed emails
        # ============================================================
        print("\n" + "=" * 60)
        print("P1 - ISSUE #11: Fixing malformed emails...")
        print("=" * 60)

        # Emails missing TLD (e.g., john@companycom -> mark invalid)
        r11a = db.execute(text("""
            UPDATE recruiters
            SET email_status = 'invalid'
            WHERE email IS NOT NULL
              AND email != ''
              AND email NOT LIKE '%@missing.local%'
              AND email NOT LIKE '%@%.%'
              AND (email_status IS NULL OR email_status != 'invalid');
        """))
        print(f"   -> Marked malformed emails as invalid: {r11a.rowcount}")
        results["issue_11_fixed"] = r11a.rowcount

        # ============================================================
        # P1 - ISSUE #5: Fix email-as-name recruiter names
        # ============================================================
        print("\n" + "=" * 60)
        print("P1 - ISSUE #5: Fixing email-as-name records...")
        print("=" * 60)

        # Extract name from email-like names:
        # "Patticusack@Theoakleafgroupcom" -> extract local part, split by caps, title case
        r5 = db.execute(text("""
            UPDATE recruiters
            SET recruiter_name = INITCAP(
                REGEXP_REPLACE(
                    SPLIT_PART(recruiter_name, '@', 1),
                    '([a-z])([A-Z])', '\\1 \\2', 'g'
                )
            )
            WHERE recruiter_name LIKE '%@%'
              AND recruiter_name NOT LIKE '%@missing.local%'
              AND recruiter_name != '';
        """))
        print(f"   -> Fixed email-as-name records: {r5.rowcount}")
        results["issue_5_fixed"] = r5.rowcount

        # Also fix "Unknown" names where email exists - extract from email
        r5b = db.execute(text("""
            UPDATE recruiters
            SET recruiter_name = INITCAP(
                REGEXP_REPLACE(
                    REPLACE(REPLACE(SPLIT_PART(email, '@', 1), '.', ' '), '_', ' '),
                    '([a-z])([A-Z])', '\\1 \\2', 'g'
                )
            )
            WHERE recruiter_name = 'Unknown'
              AND email IS NOT NULL
              AND email != ''
              AND email NOT LIKE '%@missing.local%';
        """))
        print(f"   -> Fixed 'Unknown' names from email: {r5b.rowcount}")
        results["issue_5b_fixed"] = r5b.rowcount

        # ============================================================
        # COMMIT & SUMMARY
        # ============================================================
        db.commit()
        elapsed = round(time.time() - start_time, 2)

        print("\n" + "=" * 60)
        print(f"  ALL P0 + P1 IMPROVEMENTS COMPLETE IN {elapsed}s")
        print("=" * 60)
        print(f"\nP0 Issue #1 - Active/Inactive Classification:")
        print(f"   Activated:   {results['issue_1_activated']}")
        print(f"   Deactivated: {results['issue_1_deactivated']}")
        print(f"\nP0 Issue #4 - Needs Review Reset:")
        print(f"   Flags Cleared: {results['issue_4_cleared']}")
        print(f"   Still Flagged: {results['issue_4_remaining']}")
        print(f"\nP1 Issue #12 - Fake Phones Cleaned: {results['issue_12_cleaned']}")
        print(f"P1 Issue #11 - Malformed Emails Fixed: {results['issue_11_fixed']}")
        print(f"P1 Issue #5  - Names Fixed: {results['issue_5_fixed'] + results['issue_5b_fixed']}")

    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    run_improvements()
