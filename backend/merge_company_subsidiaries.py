#!/usr/bin/env python
"""Deterministic Corporate Subsidiary Normalization Engine - TalentOpsAI"""
import sys, os, time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

def merge_subsidiaries():
    start_time = time.time()
    print("STARTING DETERMINISTIC CORPORATE SUBSIDIARY MERGING...")
    db = SessionLocal()
    try:
        # Find groups of companies sharing normalized_company_name
        # Keep ID with max active recruiters
        res = db.execute(text("""
            WITH comp_groups AS (
                SELECT 
                    normalized_company_name,
                    ARRAY_AGG(company_id ORDER BY 
                        (SELECT count(*) FROM recruiters r WHERE r.company_id = companies.company_id AND r.is_active = true) DESC,
                        company_id ASC
                    ) as ids
                FROM companies
                WHERE normalized_company_name IS NOT NULL 
                  AND normalized_company_name != ''
                  AND is_active = true
                GROUP BY normalized_company_name
                HAVING count(*) > 1
            ),
            master_map AS (
                SELECT ids[1] as master_id, UNNEST(ids[2:]) as sub_id
                FROM comp_groups
            )
            UPDATE recruiters r
            SET company_id = m.master_id,
                notes = COALESCE(r.notes, '') || ' [Company HQ Aligned]'
            FROM master_map m
            WHERE r.company_id = m.sub_id;
        """))
        print(f"   -> Realigned {res.rowcount} recruiter profiles to canonical parent corporate HQ.")

        # Deactivate subsidiary company records
        res2 = db.execute(text("""
            WITH comp_groups AS (
                SELECT 
                    normalized_company_name,
                    ARRAY_AGG(company_id ORDER BY 
                        (SELECT count(*) FROM recruiters r WHERE r.company_id = companies.company_id AND r.is_active = true) DESC,
                        company_id ASC
                    ) as ids
                FROM companies
                WHERE normalized_company_name IS NOT NULL 
                  AND normalized_company_name != ''
                  AND is_active = true
                GROUP BY normalized_company_name
                HAVING count(*) > 1
            ),
            sub_records AS (
                SELECT ids[1] as master_id, UNNEST(ids[2:]) as sub_id
                FROM comp_groups
            )
            UPDATE companies c
            SET is_active = false,
                notes = COALESCE(c.notes, '') || ' [Merged into parent HQ ID ' || s.master_id || ']'
            FROM sub_records s
            WHERE c.company_id = s.sub_id;
        """))
        print(f"   -> Soft-merged {res2.rowcount} corporate subsidiary entities into master HQ groups.")

        db.commit()
        elapsed = round(time.time() - start_time, 2)
        print(f"\nAll Corporate Subsidiary Merges Complete in {elapsed}s!")
    except Exception as e:
        db.rollback()
        print(f"Subsidiary merge error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    merge_subsidiaries()
