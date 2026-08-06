#!/usr/bin/env python
"""Autonomous Background Constitutional Quality & Enrichment Sweeper - TalentOpsAI"""
import sys, os, time, re
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.recruiter_store import _get_duckdb, PARQUET_FILE
from app.services.parquet_writer import parquet_writer

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
    print(f"[{time.strftime('%X')}] Storage: Zero-Egress Parquet Direct Access")
    print(f"[{time.strftime('%X')}] =========================================================")
    
    duckdb = _get_duckdb()
    pass_num = 1
    try:
        while True:
            t0 = time.time()
            print(f"\n[{time.strftime('%X')}] --- STARTING SWEEP PASS #{pass_num} ---")
            
            if not os.path.exists(PARQUET_FILE):
                print(f"[{time.strftime('%X')}] Parquet file not found. Waiting...")
                time.sleep(15)
                continue

            con = duckdb.connect()
            
            # -----------------------------------------------------
            # LOOP 1: Deeper Text Mining for Unknown State Recruiters
            # -----------------------------------------------------
            print(f"[{time.strftime('%X')}] Mining text fields for remaining unknown states...")
            unk_rows = con.execute(f"""
                SELECT recruiter_id, notes, raw_data, review_reason
                FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}')
                WHERE is_active = true AND (state IS NULL OR TRIM(state) = '' OR LOWER(state) = 'nan')
                LIMIT 5000
            """).fetchall()
            
            geo_updates = []
            for r in unk_rows:
                rid, notes, raw_data, review_reason = r
                combined = f"{notes or ''} {raw_data or ''} {review_reason or ''}".upper()
                st = None
                for tok in re.findall(r'\b[A-Z]{2}\b', combined):
                    if tok in STATE_MAP: st = tok; break
                if st:
                    geo_updates.append({"recruiter_id": rid, "state": st, "state_source": "deep_text_mining"})
                    
            if geo_updates:
                parquet_writer.update_records(geo_updates)
                print(f"[{time.strftime('%X')}] Pass #{pass_num} Geo-Victory: Resolved +{len(geo_updates):,} hidden state locations!")

            # -----------------------------------------------------
            # LOOP 2: Job Title Taxonomy Normalization
            # -----------------------------------------------------
            print(f"[{time.strftime('%X')}] Standardizing job title taxonomy...")
            title_rows = con.execute(f"""
                SELECT recruiter_id, title
                FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}')
                WHERE is_active = true AND title IS NOT NULL AND title NOT LIKE '%Talent%' AND title NOT LIKE '%Recruiter%'
                LIMIT 5000
            """).fetchall()
            
            title_ups = []
            for r in title_rows:
                rid, title = r
                t_raw = title.strip().lower()
                clean_t = None
                for k, v in TITLE_TAXONOMY.items():
                    if re.search(rf'\b{k}\b', t_raw): clean_t = v; break
                if clean_t and clean_t != title:
                    title_ups.append({"recruiter_id": rid, "title": clean_t})
                    
            if title_ups:
                parquet_writer.update_records(title_ups)
                print(f"[{time.strftime('%X')}] Pass #{pass_num} Title-Victory: Aligned +{len(title_ups):,} recruiter titles to enterprise taxonomy.")

            # -----------------------------------------------------
            # LOOP 3: Completeness Score Dynamic Recalculation
            # -----------------------------------------------------
            print(f"[{time.strftime('%X')}] Recalculating dynamic completeness scores...")
            recalc_rows = con.execute(f"""
                SELECT recruiter_id, email, phone, company_id, state, title
                FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}')
                WHERE is_active = true
                USING SAMPLE 10000 ROWS
            """).fetchall()
            
            score_ups = []
            for r in recalc_rows:
                rid, email, phone, comp_id, state, title = r
                sc = 10
                if email and '@' in email and 'missing' not in email: sc += 35
                if phone and len(str(phone)) >= 10: sc += 25
                if comp_id: sc += 15
                if state and state in STATE_MAP: sc += 10
                if title and len(title) > 2: sc += 5
                score_ups.append({"recruiter_id": rid, "completeness_score": min(sc, 100)})
                
            if score_ups:
                parquet_writer.update_records(score_ups)
                print(f"[{time.strftime('%X')}] Pass #{pass_num} Score-Victory: Rebalanced {len(score_ups)} quality scores.")

            con.close()
            
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

if __name__ == "__main__":
    run_sweeper_loop()
