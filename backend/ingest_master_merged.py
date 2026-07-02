#!/usr/bin/env python
"""Deterministic Master Merged Ingestion & Alignment Engine - TalentOpsAI"""
import sys, os, time, re
import pandas as pd
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

def clean_phone(phone_val):
    if pd.isna(phone_val) or not str(phone_val).strip():
        return None
    s = str(phone_val).strip()
    if s == 'nan': return None
    digits = re.sub(r'\D', '', s.split('.')[0])
    if len(digits) == 10:
        return f"+1 ({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    return s[:30] # safe VARCHAR(30) limit

def normalize_comp(c):
    if not c or pd.isna(c): return "Unknown"
    s = str(c).strip()
    return re.sub(r'\s+', ' ', s)[:255]

def run_ingestion():
    t0 = time.time()
    excel_p = r"C:/Users/User/Downloads/merged_master_final (1).xlsx"
    print(f"[{time.strftime('%X')}] Reading Excel Master file...")
    df = pd.read_excel(excel_p)
    print(f"[{time.strftime('%X')}] Loaded {len(df):,} Excel rows. Fetching DB tables using lightning keyset pagination...")

    db = SessionLocal()
    try:
        # Load companies map via keyset pagination
        comp_map = {} # norm_name -> company_id
        last_cid = 0
        while True:
            chunk = db.execute(text("SELECT company_id, company_name, normalized_company_name FROM companies WHERE company_id > :lid ORDER BY company_id LIMIT 10000"), {"lid": last_cid}).mappings().all()
            if not chunk: break
            for c in chunk:
                norm = (c['normalized_company_name'] or c['company_name'] or "").strip().lower()
                if norm: comp_map[norm] = c['company_id']
            last_cid = chunk[-1]['company_id']

        # Load recruiters map via keyset pagination
        email_map = {} # email -> dict
        name_comp_map = {} # (lower_name, company_id) -> dict
        last_rid = 0
        while True:
            chunk = db.execute(text("SELECT recruiter_id, recruiter_name, email, phone, location, company_id, email2 FROM recruiters WHERE recruiter_id > :lid ORDER BY recruiter_id LIMIT 10000"), {"lid": last_rid}).mappings().all()
            if not chunk: break
            for r in chunk:
                em = (r['email'] or "").strip().lower()
                if em: email_map[em] = dict(r)
                nm = (r['recruiter_name'] or "").strip().lower()
                if nm and r['company_id']: name_comp_map[(nm, r['company_id'])] = dict(r)
            last_rid = chunk[-1]['recruiter_id']

        print(f"[{time.strftime('%X')}] DB Keyset Loaded: {len(comp_map):,} companies, {len(email_map):,} recruiters.")

        new_companies = {} # norm -> name
        for idx, row in df.iterrows():
            cname = normalize_comp(row.get('Company name'))
            cnorm = cname.lower()
            if cnorm not in comp_map and cnorm not in new_companies:
                new_companies[cnorm] = cname

        # Insert new companies
        if new_companies:
            print(f"[{time.strftime('%X')}] Inserting {len(new_companies):,} newly discovered companies...")
            comp_ins = [{"cname": v, "norm": k, "notes": "newly added"} for k, v in new_companies.items()]
            for chunk in [comp_ins[i:i+500] for i in range(0, len(comp_ins), 500)]:
                db.execute(text("""
                    INSERT INTO companies (company_name, normalized_company_name, industry, is_active, notes)
                    VALUES (:cname, :norm, 'Corporate Group', true, :notes)
                    ON CONFLICT DO NOTHING
                """), chunk)
            db.commit()
            # Reload comp map
            last_cid = 0
            comp_map = {}
            while True:
                chunk = db.execute(text("SELECT company_id, normalized_company_name FROM companies WHERE company_id > :lid ORDER BY company_id LIMIT 10000"), {"lid": last_cid}).mappings().all()
                if not chunk: break
                for c in chunk:
                    if c['normalized_company_name']:
                        comp_map[c['normalized_company_name'].strip().lower()] = c['company_id']
                last_cid = chunk[-1]['company_id']

        # Process recruiter rows
        new_recs = []
        update_recs = []
        seen_batch_emails = set()

        for idx, row in df.iterrows():
            cname = normalize_comp(row.get('Company name'))
            cid = comp_map.get(cname.lower())
            
            pname = str(row.get('PV Name') or "").strip()
            if pname == 'nan' or not pname: pname = "Unnamed Recruiter"

            raw_em = str(row.get('EMAIL') or "").strip().lower()
            email = raw_em if raw_em != 'nan' and '@' in raw_em else None

            raw_gm = str(row.get('Gmail') or "").strip().lower()
            gmail = raw_gm if raw_gm != 'nan' and '@' in raw_gm else None

            if not email and gmail:
                email = gmail
                gmail = None

            phone = clean_phone(row.get('Phone Number'))
            raw_loc = str(row.get('Location') or "").strip()
            location = raw_loc[:145] if raw_loc != 'nan' and raw_loc else None

            # Check matching
            existing = None
            if email and email in email_map:
                existing = email_map[email]
            elif (pname.lower(), cid) in name_comp_map:
                existing = name_comp_map[(pname.lower(), cid)]

            if existing:
                # Rule #2: Improve & Align (merge missing attributes)
                updates = {"rid": existing['recruiter_id']}
                needs_up = False
                if not existing['phone'] and phone:
                    updates['phone'] = phone[:30]
                    needs_up = True
                if not existing['location'] and location:
                    updates['loc'] = location[:145]
                    needs_up = True
                if not existing['email2'] and gmail and gmail != existing['email']:
                    updates['email2'] = gmail[:145]
                    needs_up = True

                if needs_up:
                    update_recs.append(updates)
            else:
                # Rule #1: Newly added person
                dedup_key = email or f"{pname}_{cid}"
                if dedup_key not in seen_batch_emails:
                    seen_batch_emails.add(dedup_key)
                    new_recs.append({
                        "name": pname[:145],
                        "email": (email or f"unverified_{len(new_recs)}_{idx}@talentops.local")[:145],
                        "phone": phone[:30] if phone else None,
                        "loc": location,
                        "cid": cid,
                        "email2": gmail[:145] if gmail else None,
                        "notes": "newly added"
                    })

        print(f"[{time.strftime('%X')}] Matching Complete! Aligned Updates: {len(update_recs):,}, New Discoveries: {len(new_recs):,}")

        # Execute Updates
        if update_recs:
            print(f"[{time.strftime('%X')}] Executing {len(update_recs):,} aligned attribute enrichments...")
            for chunk in [update_recs[i:i+500] for i in range(0, len(update_recs), 500)]:
                for u in chunk:
                    set_clauses = []
                    params = {"rid": u['rid']}
                    if 'phone' in u: set_clauses.append("phone = :phone"); params['phone'] = u['phone']
                    if 'loc' in u: set_clauses.append("location = :loc"); params['loc'] = u['loc']
                    if 'email2' in u: set_clauses.append("email2 = :email2"); params['email2'] = u['email2']
                    if set_clauses:
                        db.execute(text(f"UPDATE recruiters SET {', '.join(set_clauses)} WHERE recruiter_id = :rid"), params)
            db.commit()

        # Execute Inserts
        if new_recs:
            print(f"[{time.strftime('%X')}] Inserting {len(new_recs):,} newly discovered recruiter profiles...")
            for chunk in [new_recs[i:i+500] for i in range(0, len(new_recs), 500)]:
                db.execute(text("""
                    INSERT INTO recruiters (recruiter_name, email, phone, location, company_id, email2, is_active, completeness_score, notes, created_at)
                    VALUES (:name, :email, :phone, :loc, :cid, :email2, true, 80, :notes, NOW())
                    ON CONFLICT (email) DO NOTHING
                """), chunk)
            db.commit()

        # Final count
        final_recs = db.execute(text("SELECT COUNT(*) FROM recruiters")).scalar()
        final_comps = db.execute(text("SELECT COUNT(*) FROM companies")).scalar()
        elapsed = round(time.time() - t0, 2)
        print(f"\n=======================================================")
        print(f"SUCCESSFUL INGESTION & CONSTITUTIONAL MERGE COMPLETE!")
        print(f"Total Time: {elapsed}s")
        print(f"New Profiles Discovered & Tagged: +{len(new_recs):,}")
        print(f"Existing Records Improved (Rule #2): {len(update_recs):,}")
        print(f"Final DB State: {final_recs:,} Recruiters across {final_comps:,} Companies")
        print(f"=======================================================")

    except Exception as e:
        db.rollback()
        print("ERROR DURING INGESTION:", e)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_ingestion()
