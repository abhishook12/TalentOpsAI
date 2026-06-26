#!/usr/bin/env python
"""100% Deterministic Internal Database Quality Engineering Engine - TalentOpsAI"""
import sys, os, time, re
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

def run_internal_perfection():
    start_time = time.time()
    db = SessionLocal()
    results = {}

    try:
        # ============================================================
        # OPERATION 1: Deterministic Completeness Score Calibration
        # ============================================================
        print("=" * 65)
        print("OPERATION 1: Recalibrating 100% of Recruiter Completeness Scores...")
        print("=" * 65)
        
        r1 = db.execute(text("""
            UPDATE recruiters
            SET completeness_score = 
                (CASE WHEN recruiter_name IS NOT NULL AND recruiter_name != '' AND recruiter_name != 'Unknown' THEN 25 ELSE 0 END) +
                (CASE WHEN email IS NOT NULL AND email != '' AND email NOT LIKE '%@missing.local%' THEN 35 ELSE 0 END) +
                (CASE WHEN phone IS NOT NULL AND phone != '' THEN 25 ELSE 0 END) +
                (CASE WHEN state IS NOT NULL AND state != '' AND state != 'US' AND LENGTH(state) = 2 THEN 15 ELSE 0 END);
        """))
        print(f"   -> Recalibrated exact completeness scores for {r1.rowcount} profiles.")
        results["op1_scores"] = r1.rowcount

        # ============================================================
        # OPERATION 2: Peer Domain Cluster State Propagation
        # ============================================================
        print("\n" + "=" * 65)
        print("OPERATION 2: Peer Email Domain Cluster State Propagation...")
        print("=" * 65)

        r2 = db.execute(text("""
            WITH domain_clusters AS (
                SELECT 
                    SUBSTRING(email FROM '@(.*)$') as domain,
                    MODE() WITHIN GROUP (ORDER BY state) as canonical_state,
                    COUNT(*) as cluster_size
                FROM recruiters
                WHERE email IS NOT NULL AND email LIKE '%@%.%'
                  AND email NOT LIKE '%@missing.local%'
                  AND state IS NOT NULL AND state != '' AND state != 'US' AND LENGTH(state) = 2
                GROUP BY SUBSTRING(email FROM '@(.*)$')
                HAVING COUNT(*) >= 2
            )
            UPDATE recruiters r
            SET state = d.canonical_state,
                state_source = 'peer_domain_cluster_inference'
            FROM domain_clusters d
            WHERE SUBSTRING(r.email FROM '@(.*)$') = d.domain
              AND (r.state IS NULL OR r.state = '' OR r.state = 'US' OR r.state = 'Unknown')
              AND d.canonical_state IS NOT NULL;
        """))
        print(f"   -> Propagated peer cluster state to {r2.rowcount} unmapped profiles.")
        results["op2_states"] = r2.rowcount

        # ============================================================
        # OPERATION 3: Seniority Taxonomy Standardization
        # ============================================================
        print("\n" + "=" * 65)
        print("OPERATION 3: Deterministic Seniority & Title Standardization...")
        print("=" * 65)

        r3 = db.execute(text("""
            UPDATE recruiters
            SET taxonomy_category = CASE
                WHEN specialization ILIKE '%chief%' OR specialization ILIKE '%vp%' OR specialization ILIKE '%head%' OR title ILIKE '%vp%' OR title ILIKE '%head%' THEN 'Executive'
                WHEN specialization ILIKE '%director%' OR title ILIKE '%director%' OR specialization ILIKE '%dir %' THEN 'Director'
                WHEN specialization ILIKE '%manager%' OR title ILIKE '%manager%' OR specialization ILIKE '%mgr%' OR specialization ILIKE '%lead%' THEN 'Manager / Lead'
                WHEN specialization ILIKE '%senior%' OR specialization ILIKE '%sr.%' OR specialization ILIKE '%principal%' OR title ILIKE '%senior%' OR title ILIKE '%sr %' THEN 'Senior Recruiter'
                WHEN specialization ILIKE '%sourcer%' OR specialization ILIKE '%coordinator%' OR title ILIKE '%sourcer%' OR title ILIKE '%coordinator%' THEN 'Sourcer / Coordinator'
                ELSE 'Talent Acquisition / Recruiter'
            END
            WHERE taxonomy_category IS NULL OR taxonomy_category = '' OR taxonomy_category = 'Unknown';
        """))
        print(f"   -> Standardized canonical seniority taxonomy for {r3.rowcount} profiles.")
        results["op3_taxonomy"] = r3.rowcount

        # ============================================================
        # OPERATION 4: Clean US Phone Number Formatting (+1 (XXX) XXX-XXXX)
        # ============================================================
        print("\n" + "=" * 65)
        print("OPERATION 4: Standardizing US Phone Number Strings...")
        print("=" * 65)

        # Remove dots, dashes, spaces, prepend +1 if 10 digits
        r4 = db.execute(text("""
            UPDATE recruiters
            SET phone = regexp_replace(phone, '^1?([2-9][0-9]{2})[.-]?([0-9]{3})[.-]?([0-9]{4})$', '+1 (\\1) \\2-\\3')
            WHERE phone ~ '^1?[2-9][0-9]{2}[.-]?[0-9]{3}[.-]?[0-9]{4}$'
              AND phone NOT LIKE '+1 (%';
        """))
        print(f"   -> Standardized E.164 phone formatting for {r4.rowcount} numbers.")
        results["op4_phones"] = r4.rowcount

        db.commit()
        elapsed = round(time.time() - start_time, 2)
        print("\n" + "=" * 65)
        print(f"  ALL DETERMINISTIC INTERNAL DB OPERATIONS COMPLETE IN {elapsed}s")
        print("=" * 65)

    except Exception as e:
        db.rollback()
        print(f"Internal perfection engine error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    run_internal_perfection()
