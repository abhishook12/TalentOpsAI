import sys, os, time, re, json, csv
from collections import defaultdict, Counter
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.database import SessionLocal
from app.utils.state_mapper import extract_state_detailed
from sqlalchemy import text

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

FILENAME_STATE_HINTS = {
    '_tx_': 'TX', '_new_york': 'NY', '_georgia': 'GA', '_north_carolina': 'NC',
    '_detroit': 'MI', '_california': 'CA', '_florida': 'FL', '_illinois': 'IL'
}

def harvest_from_pc(folders):
    email_to_state = {}
    domain_to_state = {}
    
    for folder in folders:
        if not os.path.exists(folder): continue
        for root, dirs, files in os.walk(folder):
            for f in files:
                ext = f.lower().split('.')[-1]
                if ext not in {'csv', 'xlsx', 'json'}: continue
                filepath = os.path.join(root, f)
                
                # Check filename hint
                file_hint_state = None
                fltr = f.lower()
                for kw, st in FILENAME_STATE_HINTS.items():
                    if kw in fltr:
                        file_hint_state = st
                        break
                        
                try:
                    if ext == 'csv':
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as fp:
                            reader = csv.DictReader(fp)
                            for row in reader:
                                em = (row.get('email') or row.get('Email') or row.get('EMAIL') or '').lower().strip()
                                st = row.get('state') or row.get('State') or row.get('STATE') or row.get('location') or row.get('Location') or file_hint_state or ''
                                if em and st and '@' in em:
                                    extracted, _ = extract_state_detailed(st) if not file_hint_state else (file_hint_state, 'filename')
                                    if extracted:
                                        email_to_state[em] = extracted
                                        dom = em.split('@')[-1]
                                        if dom not in {'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com'}:
                                            domain_to_state[dom] = extracted
                    elif ext == 'xlsx' and HAS_PANDAS:
                        df = pd.read_excel(filepath)
                        cols = {c.lower(): c for c in df.columns}
                        em_col = cols.get('email')
                        st_col = cols.get('state') or cols.get('location')
                        if em_col:
                            for _, row in df.iterrows():
                                em = str(row[em_col]).lower().strip()
                                st = str(row[st_col]) if st_col else (file_hint_state or '')
                                if em and em != 'nan' and '@' in em:
                                    extracted, _ = extract_state_detailed(st) if not file_hint_state else (file_hint_state, 'filename')
                                    if extracted:
                                        email_to_state[em] = extracted
                                        dom = em.split('@')[-1]
                                        if dom not in {'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com'}:
                                            domain_to_state[dom] = extracted
                except Exception:
                    pass
    return email_to_state, domain_to_state

def run_pc_harvester():
    db = SessionLocal()
    t0 = time.time()
    print("=== STARTING PC-WIDE STATE HARVESTER ===", flush=True)
    
    folders_to_scan = [
        'C:\\Users\\User\\Downloads',
        'C:\\Users\\User\\Documents',
        'C:\\Users\\User\\Desktop'
    ]
    print(f"Scanning {len(folders_to_scan)} PC directories for spreadsheet state mappings...", flush=True)
    file_em_map, file_dom_map = harvest_from_pc(folders_to_scan)
    print(f"Harvested {len(file_em_map):,} email mappings and {len(file_dom_map):,} domain mappings from PC files.", flush=True)
    
    last_id = 0
    total_updated = 0
    from_em = 0
    from_dom = 0
    
    while True:
        chunk = db.execute(text("""
            SELECT recruiter_id, email
            FROM recruiters
            WHERE recruiter_id > :lid AND (state IS NULL OR state = '')
            ORDER BY recruiter_id LIMIT 10000
        """), {"lid": last_id}).mappings().all()
        if not chunk: break
        
        batch_updates = []
        for r in chunk:
            rid = r['recruiter_id']
            em = (r['email'] or '').lower().strip()
            
            chosen_state = None
            if em in file_em_map:
                chosen_state = file_em_map[em]
                from_em += 1
            elif '@' in em and em.split('@')[-1] in file_dom_map:
                chosen_state = file_dom_map[em.split('@')[-1]]
                from_dom += 1
                        
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
    print(f"PC-WIDE HARVESTING COMPLETE!")
    print(f"Time Taken: {elapsed}s")
    print(f"Total States Backfilled: {total_updated:,}")
    print(f"  - From Exact Email Match: {from_em:,}")
    print(f"  - From Domain Match: {from_dom:,}")
    print("=======================================================", flush=True)
    db.close()

if __name__ == '__main__':
    run_pc_harvester()
