import sys, os, time
from collections import defaultdict, Counter
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.database import SessionLocal
from app.models.models import Recruiter, Company
from app.utils.state_mapper import extract_state_detailed
from sqlalchemy import text

def run_propagation():
    db = SessionLocal()
    t0 = time.time()
    print("=== STARTING EMAIL DOMAIN & COMPANY STATE PROPAGATION ===", flush=True)
    
    # 1. Gather known domains from Companies
    domain_to_state = {}
    companies = db.query(Company).filter(Company.state.isnot(None), Company.state != '').all()
    for c in companies:
        st = c.state
        if c.website:
            clean_dom = c.website.replace('http://', '').replace('https://', '').replace('www.', '').split('/')[0].lower().strip()
            if clean_dom and '.' in clean_dom:
                domain_to_state[clean_dom] = st
                
    print(f"Loaded {len(domain_to_state):,} domain mappings from Company table.", flush=True)
    
    # 2. Gather known domain frequencies from Recruiters
    domain_state_counts = defaultdict(Counter)
    last_id = 0
    while True:
        chunk = db.execute(text("""
            SELECT recruiter_id, email, state
            FROM recruiters
            WHERE recruiter_id > :lid AND state IS NOT NULL AND state != '' AND email IS NOT NULL
            ORDER BY recruiter_id LIMIT 10000
        """), {"lid": last_id}).mappings().all()
        if not chunk: break
        for r in chunk:
            em = r['email']
            st = r['state']
            if '@' in em:
                dom = em.split('@')[-1].lower().strip()
                if dom not in {'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com'}:
                    domain_state_counts[dom][st] += 1
        last_id = chunk[-1]['recruiter_id']
        
    for dom, counts in domain_state_counts.items():
        if dom not in domain_to_state:
            best_st, cnt = counts.most_common(1)[0]
            # If we have at least 2 records supporting this state or it's overwhelming majority
            if cnt >= 2 or (cnt == 1 and len(counts) == 1):
                domain_to_state[dom] = best_st

    print(f"Total Combined Domain -> State Knowledge Base: {len(domain_to_state):,} domains.", flush=True)
    
    # 3. Propagate to unknown recruiters
    last_id = 0
    total_updated = 0
    
    while True:
        chunk = db.execute(text("""
            SELECT recruiter_id, email
            FROM recruiters
            WHERE recruiter_id > :lid AND (state IS NULL OR state = '') AND email IS NOT NULL
            ORDER BY recruiter_id LIMIT 10000
        """), {"lid": last_id}).mappings().all()
        if not chunk: break
        
        batch_updates = []
        for r in chunk:
            rid = r['recruiter_id']
            em = r['email']
            if '@' in em:
                dom = em.split('@')[-1].lower().strip()
                if dom in domain_to_state:
                    batch_updates.append({"rid": rid, "st": domain_to_state[dom]})
                    
        if batch_updates:
            for i in range(0, len(batch_updates), 1000):
                sub = batch_updates[i:i+1000]
                db.execute(text("UPDATE recruiters SET state = :st WHERE recruiter_id = :rid"), sub)
            db.commit()
            total_updated += len(batch_updates)
            print(f"Propagated {total_updated:,} states so far... (Last ID: {last_id:,})", flush=True)
            
        last_id = chunk[-1]['recruiter_id']
        
    elapsed = round(time.time() - t0, 2)
    print("\n=======================================================")
    print(f"DOMAIN PROPAGATION COMPLETE!")
    print(f"Time Taken: {elapsed}s")
    print(f"Total States Backfilled via Email Domain Knowledge: {total_updated:,}")
    print("=======================================================", flush=True)
    db.close()

if __name__ == '__main__':
    run_propagation()
