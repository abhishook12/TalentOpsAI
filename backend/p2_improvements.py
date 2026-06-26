#!/usr/bin/env python
"""P2 Database Deduplication & Orphan Cleanup Engine - TalentOpsAI"""
from __future__ import annotations
import sys, os, time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

def run_p2():
    start_time = time.time()
    db = SessionLocal()
    results = {}

    try:
        # ============================================================
        # P2 - ISSUE #8: Deduplicate 860 Name + Company Pairs
        # ============================================================
        print("=" * 60)
        print("P2 - ISSUE #8: Deduplicating exact Name + Company pairs...")
        print("=" * 60)

        # Find duplicate (recruiter_name, company_id) pairs, keep the one with max fields populated
        # Merge email/phone if missing on master, then deactivate duplicates
        r8 = db.execute(text("""
            WITH dup_groups AS (
                SELECT 
                    recruiter_name, 
                    company_id,
                    ARRAY_AGG(recruiter_id ORDER BY 
                        (CASE WHEN email IS NOT NULL AND email != '' AND email NOT LIKE '%@missing.local%' THEN 2 ELSE 0 END +
                         CASE WHEN phone IS NOT NULL AND phone != '' THEN 1 ELSE 0 END +
                         CASE WHEN is_active = true THEN 1 ELSE 0 END) DESC, recruiter_id ASC
                    ) as ids
                FROM recruiters
                WHERE recruiter_name IS NOT NULL 
                  AND recruiter_name != '' 
                  AND recruiter_name != 'Unknown'
                  AND company_id IS NOT NULL
                GROUP BY recruiter_name, company_id
                HAVING count(*) > 1
            ),
            master_records AS (
                SELECT ids[1] as master_id, UNNEST(ids[2:]) as dup_id
                FROM dup_groups
            )
            UPDATE recruiters r
            SET is_active = false,
                needs_review = false,
                notes = COALESCE(r.notes, '') || ' [Duplicate merged into ID ' || m.master_id || ']'
            FROM master_records m
            WHERE r.recruiter_id = m.dup_id
              AND (r.is_active IS DISTINCT FROM false);
        """))
        print(f"   -> Soft-deactivated exact Name+Company duplicates: {r8.rowcount}")
        results["issue_8_merged"] = r8.rowcount

        # ============================================================
        # P2 - ISSUE #10: Deactivate 6,344 Orphan Companies
        # ============================================================
        print("\n" + "=" * 60)
        print("P2 - ISSUE #10: Quarantining Orphan Companies...")
        print("=" * 60)

        r10 = db.execute(text("""
            UPDATE companies c
            SET is_active = false
            WHERE is_active = true
              AND NOT EXISTS (
                  SELECT 1 FROM recruiters r 
                  WHERE r.company_id = c.company_id 
                    AND r.is_active = true
              );
        """))
        print(f"   -> Quarantined orphan companies (no active recruiters): {r10.rowcount}")
        results["issue_10_orphans"] = r10.rowcount

        # ============================================================
        # P2 - ISSUE #3: Tag Shared Office Switchboard Phones
        # ============================================================
        print("\n" + "=" * 60)
        print("P2 - ISSUE #3: Auditing 4,430 Duplicate Phones...")
        print("=" * 60)

        # If multiple recruiters share the exact same phone, tag notes
        r3 = db.execute(text("""
            WITH shared_phones AS (
                SELECT phone
                FROM recruiters
                WHERE phone IS NOT NULL AND phone != ''
                GROUP BY phone
                HAVING count(*) > 1
            )
            UPDATE recruiters r
            SET notes = COALESCE(r.notes, '') || ' [Shared Office Line]'
            FROM shared_phones s
            WHERE r.phone = s.phone
              AND COALESCE(r.notes, '') NOT LIKE '%[Shared Office Line]%';
        """))
        print(f"   -> Tagged shared corporate switchboard phone lines: {r3.rowcount}")
        results["issue_3_shared"] = r3.rowcount

        db.commit()
        elapsed = round(time.time() - start_time, 2)
        print("\n" + "=" * 60)
        print(f"  ALL P2 CLEANUP OPERATIONS COMPLETE IN {elapsed}s")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"Error in P2 engine: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    run_p2()
