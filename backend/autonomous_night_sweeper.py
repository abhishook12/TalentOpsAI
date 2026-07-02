#!/usr/bin/env python
"""Autonomous Background Constitutional Quality & Enrichment Sweeper - TalentOpsAI"""
import sys, os, time, re
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

STATE_MAP = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC',
    'AB', 'BC', 'MB', 'NB', 'NL', 'NS', 'ON', 'PE', 'QC', 'SK', 'UK', 'DE', 'FR', 'IN', 'AU', 'SG', 'IE'
}

TITLE_TAXONOMY = {
    'vp': 'VP of Talent Acquisition', 'vice president': 'VP of Talent Acquisition',
    'director': 'Director of Talent Acquisition', 'head of talent': 'Head of Talent Acquisition',
    'head of recruiting': 'Head of Recruiting', 'principal': 'Principal Recruiter',
    'lead': 'Lead Technical Recruiter', 'senior': 'Senior Technical Recruiter',
    'sr': 'Senior Technical Recruiter', 'talent acquisition': 'Talent Acquisition Specialist',
    'technical recruiter': 'Technical Recruiter', 'sourcer': 'Talent Sourcer',
    'recruiter': 'Recruiter'
}

def run_sweeper_loop():
    print(f"[{time.strftime('%X')}] =========================================================")
    print(f"[{time.strftime('%X')}] AUTONOMOUS BACKGROUND CONSTITUTIONAL SWEEPER ACTIVE")
    print(f"[{time.strftime('%X')}] Mode: Continuous Offline Local Optimization ($0.00 Cost)")
    print(f"[{time.strftime('%X')}] =========================================================")
    
    db = SessionLocal()
    pass_num = 1
    try:
        while True:
            t0 = time.time()
            print(f"\n[{time.strftime('%X')}] --- STARTING SWEEP PASS #{pass_num} ---")
            
            # -----------------------------------------------------
            # LOOP 1: Deeper Text Mining for Unknown State Recruiters
            # -----------------------------------------------------
            print(f"[{time.strftime('%X')}] Mining text fields for remaining unknown states...")
            unk_rows = db.execute(text("""
                SELECT recruiter_id, notes, raw_data, review_reason
                FROM recruiters
                WHERE is_active = true AND (state IS NULL OR TRIM(state) = '' OR LOWER(state) = 'nan')
                LIMIT 5000
            """)).mappings().all()
            
            geo_updates = []
            for r in unk_rows:
                combined = f"{r['notes'] or ''} {r['raw_data'] or ''} {r['review_reason'] or ''}".upper()
                st = None
                for tok in re.findall(r'\b[A-Z]{2}\b', combined):
                    if tok in STATE_MAP: st = tok; break
                if st:
                    geo_updates.append({"rid": r['recruiter_id'], "st": st})
                    
            if geo_updates:
                for i in range(0, len(geo_updates), 500):
                    db.execute(text("UPDATE recruiters SET state = :st, state_source = 'deep_text_mining' WHERE recruiter_id = :rid"), geo_updates[i:i+500])
                db.commit()
                print(f"[{time.strftime('%X')}] Pass #{pass_num} Geo-Victory: Resolved +{len(geo_updates):,} hidden state locations!")

            # -----------------------------------------------------
            # LOOP 2: Job Title Taxonomy Normalization
            # -----------------------------------------------------
            print(f"[{time.strftime('%X')}] Standardizing job title taxonomy...")
            title_rows = db.execute(text("""
                SELECT recruiter_id, title
                FROM recruiters
                WHERE is_active = true AND title IS NOT NULL AND title NOT LIKE '%Talent%' AND title NOT LIKE '%Recruiter%'
                LIMIT 5000
            """)).mappings().all()
            
            title_ups = []
            for r in title_rows:
                t_raw = r['title'].strip().lower()
                clean_t = None
                for k, v in TITLE_TAXONOMY.items():
                    if re.search(rf'\b{k}\b', t_raw): clean_t = v; break
                if clean_t and clean_t != r['title']:
                    title_ups.append({"rid": r['recruiter_id'], "tl": clean_t})
                    
            if title_ups:
                for i in range(0, len(title_ups), 500):
                    db.execute(text("UPDATE recruiters SET title = :tl WHERE recruiter_id = :rid"), title_ups[i:i+500])
                db.commit()
                print(f"[{time.strftime('%X')}] Pass #{pass_num} Title-Victory: Aligned +{len(title_ups):,} recruiter titles to enterprise taxonomy.")

            # -----------------------------------------------------
            # LOOP 3: Completeness Score Dynamic Recalculation
            # -----------------------------------------------------
            print(f"[{time.strftime('%X')}] Recalculating dynamic completeness scores...")
            recalc_rows = db.execute(text("""
                SELECT recruiter_id, email, phone, company_id, state, title
                FROM recruiters
                WHERE is_active = true
                ORDER BY RANDOM() LIMIT 10000
            """)).mappings().all()
            
            score_ups = []
            for r in recalc_rows:
                sc = 10
                if r['email'] and '@' in r['email'] and 'missing' not in r['email']: sc += 35
                if r['phone'] and len(str(r['phone'])) >= 10: sc += 25
                if r['company_id']: sc += 15
                if r['state'] and r['state'] in STATE_MAP: sc += 10
                if r['title'] and len(r['title']) > 2: sc += 5
                score_ups.append({"rid": r['recruiter_id'], "sc": min(sc, 100)})
                
            for i in range(0, len(score_ups), 1000):
                db.execute(text("UPDATE recruiters SET completeness_score = :sc WHERE recruiter_id = :rid"), score_ups[i:i+1000])
            db.commit()
            print(f"[{time.strftime('%X')}] Pass #{pass_num} Score-Victory: Rebalanced 10,000 quality scores.")

            elapsed = round(time.time() - t0, 2)
            print(f"[{time.strftime('%X')}] Sweep Pass #{pass_num} finished in {elapsed}s. Resting 15s before next cycle...")
            pass_num += 1
            time.sleep(15)
            
            # Clear uvicorn cache periodically
            try:
                from app.routes.analytics import analytics_cache
                analytics_cache.clear()
            except Exception:
                pass

    except KeyboardInterrupt:
        print("\n[STOP] Background Sweeper shut down gracefully.")
    except Exception as e:
        print("ERROR IN SWEEPER:", e)
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_sweeper_loop()
