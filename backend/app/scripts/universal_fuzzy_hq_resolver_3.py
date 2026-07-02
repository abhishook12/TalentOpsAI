import sys, os, time, re
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.database import SessionLocal
from sqlalchemy import text

EXPANDED_HQ_MAP_3 = {
    'brownandroot': 'LA', 'dmndpkrec': 'CO', 'element84': 'VA', 'ontic.co': 'TX', 'staffinq': 'GA',
    'keyo.co': 'CA', 'ironeaglex': 'FL', 'odiin': 'TX', 'virtelligence': 'MN', 'bluematter': 'CA',
    'wincorpsolutions': 'CA', 'alexanderash': 'NY', 'hcmunlocked': 'NC', 'chopdawg': 'PA',
    'provalus': 'AL', 'experientgroup': 'GA', 'five9': 'CA', 'pssi.com': 'WI', 'superlanet': 'CA',
    'hobsonassoc': 'CT', 'accordus': 'TN', 'vectorusa': 'CA', 'kake.co': 'KS', 'verisign': 'VA',
    'hiresapphire': 'TX', 'jugde.com': 'PA', 'judge.com': 'PA', 'cohnreznick': 'NY',
    'chariotsolutions': 'PA', 'briteskies': 'OH', 'themarketingstore': 'IL', 'sparkadvisory': 'TX',
    'idmworks': 'FL', 'jooble': 'NY', 'accordion': 'NY', 'perforce': 'MN', 'drtstrategies': 'VA',
    'cybersn': 'MA', 'labormax': 'NV', 'mythics': 'VA', 'agvend': 'TX', 'integritystaffing': 'DE',
    'nscorp': 'GA', 'ankura': 'NY', 'daxtra': 'VA', 'navisite': 'MA', 'coregroupresources': 'TX',
    'alphafmc': 'NY', 'netbuilder': 'NY', 'zenergy': 'NC', 'careergroupinc': 'CA'
}

def resolve_pass_3():
    db = SessionLocal()
    t0 = time.time()
    print("=== STARTING EXPANDED FUZZY SUBSTRING HQ RESOLVER PASS 3 ===", flush=True)
    
    last_id = 0
    total_updated = 0
    
    while True:
        chunk = db.execute(text("""
            SELECT recruiter_id, email, notes
            FROM recruiters
            WHERE recruiter_id > :lid AND (state IS NULL OR state = '')
            ORDER BY recruiter_id LIMIT 10000
        """), {"lid": last_id}).mappings().all()
        if not chunk: break
        
        batch_updates = []
        for r in chunk:
            rid = r['recruiter_id']
            em = (r['email'] or '').lower()
            nts = (r['notes'] or '').lower()
            search_str = em + ' ' + nts
            
            chosen_state = None
            for kw, st in EXPANDED_HQ_MAP_3.items():
                if kw in search_str:
                    chosen_state = st
                    break
                
            if chosen_state:
                batch_updates.append({"rid": rid, "st": chosen_state})
                
        if batch_updates:
            for i in range(0, len(batch_updates), 1000):
                sub = batch_updates[i:i+1000]
                db.execute(text("UPDATE recruiters SET state = :st WHERE recruiter_id = :rid"), sub)
            db.commit()
            total_updated += len(batch_updates)
            print(f"Progress: Updated {total_updated:,} states... (Last ID: {last_id:,})", flush=True)
            
        last_id = chunk[-1]['recruiter_id']
        
    elapsed = round(time.time() - t0, 2)
    print("\n=======================================================")
    print(f"PASS 3 RESOLUTION COMPLETE!")
    print(f"Time Taken: {elapsed}s")
    print(f"Total States Backfilled: {total_updated:,}")
    print("=======================================================", flush=True)
    db.close()

if __name__ == '__main__':
    resolve_pass_3()
