#!/usr/bin/env python
"""Intense Whole-Database Constitutional Perfection & Alignment Engine - TalentOpsAI"""
import sys, os, time, re
from collections import defaultdict
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

def clean_title_case(name_str):
    if not name_str or name_str.strip().lower() in ('nan', 'none', 'null', 'unnamed recruiter', ''):
        return "Unnamed Recruiter"
    s = re.sub(r'\s+', ' ', name_str.strip())
    # Remove junk
    s = re.sub(r'[#?!*+]+', '', s).strip()
    if not s: return "Unnamed Recruiter"
    # Title case if all caps or all lower
    if s.isupper() or s.islower():
        return s.title()
    return s

def run_perfection():
    t0 = time.time()
    print(f"[{time.strftime('%X')}] INITIATING INTENSE WHOLE-DATABASE CONSTITUTIONAL PERFECTION...")
    db = SessionLocal()
    try:
        # Phase 1: Deep Deduplication & Attribute Merging (Rule #1 & #2)
        print(f"[{time.strftime('%X')}] Phase 1: Scanning for duplicate email profiles across entire DB...")
        dups = db.execute(text("""
            SELECT LOWER(TRIM(email)) as em
            FROM recruiters
            WHERE email IS NOT NULL AND TRIM(email) != '' AND is_active = true
            GROUP BY LOWER(TRIM(email))
            HAVING COUNT(*) > 1
        """)).scalars().all()
        dup_list = list(dups)
        print(f"[{time.strftime('%X')}] Found {len(dup_list):,} duplicate active email clusters. Fetching all clone rows...")

        merged_clones = 0
        enriched_masters = 0

        if dup_list:
            # Fetch all duplicate rows in chunks of 500 emails
            all_dup_rows = []
            for i in range(0, len(dup_list), 500):
                batch_ems = dup_list[i:i+500]
                rows = db.execute(text("""
                    SELECT recruiter_id, recruiter_name, email, phone, location, company_id, email2, linkedin, title, completeness_score, notes
                    FROM recruiters
                    WHERE LOWER(TRIM(email)) = ANY(:ems) AND is_active = true
                """), {"ems": batch_ems}).mappings().all()
                all_dup_rows.extend(rows)

            # Group in memory
            clusters = defaultdict(list)
            for r in all_dup_rows:
                em = (r['email'] or "").strip().lower()
                if em: clusters[em].append(dict(r))

            master_updates = []
            clone_updates = []

            for em, rows in clusters.items():
                if len(rows) < 2: continue
                # Sort master first: highest score, then oldest id
                rows.sort(key=lambda x: (x['completeness_score'] or 0, -x['recruiter_id']), reverse=True)
                master = rows[0]
                clones = rows[1:]

                m_up = {}
                for c in clones:
                    if not master.get('phone') and c.get('phone'): master['phone'] = c['phone']; m_up['phone'] = c['phone'][:30]
                    if not master.get('location') and c.get('location'): master['location'] = c['location']; m_up['location'] = c['location'][:150]
                    if not master.get('email2') and c.get('email2'): master['email2'] = c['email2']; m_up['email2'] = c['email2'][:150]
                    if not master.get('linkedin') and c.get('linkedin'): master['linkedin'] = c['linkedin']; m_up['linkedin'] = c['linkedin'][:255]
                    if not master.get('title') and c.get('title'): master['title'] = c['title']; m_up['title'] = c['title'][:150]

                if m_up:
                    m_up['rid'] = master['recruiter_id']
                    master_updates.append(m_up)

                for c in clones:
                    clone_updates.append({"cid": c['recruiter_id'], "mid": master['recruiter_id']})

            print(f"[{time.strftime('%X')}] In-Memory Analysis Complete! Enriched Masters: {len(master_updates):,}, Clones to Consolidate: {len(clone_updates):,}")

            # Execute Master Enrichments in chunks
            for i in range(0, len(master_updates), 500):
                chunk = master_updates[i:i+500]
                for m_up in chunk:
                    set_str = ", ".join([f"{k} = :{k}" for k in m_up.keys() if k != 'rid'])
                    db.execute(text(f"UPDATE recruiters SET {set_str} WHERE recruiter_id = :rid"), m_up)

            # Deactivate Clones in chunks of 500 (Rule #1)
            for i in range(0, len(clone_updates), 500):
                chunk = clone_updates[i:i+500]
                db.execute(text("""
                    UPDATE recruiters
                    SET is_active = false,
                        notes = COALESCE(notes, '') || '; merged into canonical master #' || :mid
                    WHERE recruiter_id = :cid
                """), chunk)

            db.commit()
            merged_clones = len(clone_updates)
            enriched_masters = len(master_updates)

        print(f"[{time.strftime('%X')}] Phase 1 Complete! Safely consolidated {merged_clones:,} duplicate rows into {enriched_masters:,} canonical masters.")

        # Phase 2: Intense Name & String Standardization across DB via Keyset Pagination
        print(f"[{time.strftime('%X')}] Phase 2: Standardizing recruiter names and string formatting across entire DB...")
        last_rid = 0
        cleaned_names = 0
        while True:
            chunk = db.execute(text("SELECT recruiter_id, recruiter_name FROM recruiters WHERE recruiter_id > :lid ORDER BY recruiter_id LIMIT 10000"), {"lid": last_rid}).mappings().all()
            if not chunk: break
            up_batch = []
            for r in chunk:
                clean = clean_title_case(r['recruiter_name'])
                if clean != r['recruiter_name'] and clean[:145]:
                    up_batch.append({"rid": r['recruiter_id'], "nm": clean[:145], "norm": clean.lower()[:145]})
            if up_batch:
                for i in range(0, len(up_batch), 500):
                    b_chunk = up_batch[i:i+500]
                    db.execute(text("UPDATE recruiters SET recruiter_name = :nm, normalized_recruiter_name = :norm WHERE recruiter_id = :rid"), b_chunk)
                db.commit()
                cleaned_names += len(up_batch)
            last_rid = chunk[-1]['recruiter_id']

        print(f"[{time.strftime('%X')}] Phase 2 Complete! Standardized & polished {cleaned_names:,} recruiter names.")

        # Phase 3: Telemetry audit
        tot_active = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE is_active = true")).scalar()
        tot_comps = db.execute(text("SELECT COUNT(*) FROM companies WHERE is_active = true")).scalar()
        elapsed = round(time.time() - t0, 2)

        print(f"\n=======================================================")
        print(f"INTENSE WHOLE-DATABASE CONSTITUTIONAL PERFECTION COMPLETE!")
        print(f"Execution Time: {elapsed}s")
        print(f"Duplicate Clones Safely Consolidated (Rule #1): {merged_clones:,}")
        print(f"Canonical Profiles Enriched (Rule #2): {enriched_masters:,}")
        print(f"Names & Strings Polished: {cleaned_names:,}")
        print(f"Final Active Golden Database: {tot_active:,} Recruiters across {tot_comps:,} Companies")
        print(f"=======================================================")

    except Exception as e:
        db.rollback()
        print("ERROR DURING PERFECTION:", e)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_perfection()
