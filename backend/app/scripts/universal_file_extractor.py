import sys, os, time, re, json, csv
from collections import defaultdict, Counter
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.database import SessionLocal
from app.utils.state_mapper import extract_state_detailed
from sqlalchemy import text

# Try importing pandas or openpyxl if available for xlsx
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

DOMAIN_KEYWORD_TO_STATE = {
    'texas': 'TX', 'dallas': 'TX', 'austin': 'TX', 'houston': 'TX', 'dfw': 'TX', 'plano': 'TX', 'sanantonio': 'TX',
    'calif': 'CA', 'california': 'CA', 'socal': 'CA', 'norcal': 'CA', 'bayarea': 'CA', 'siliconvalley': 'CA', 'sandiego': 'CA', 'losangeles': 'CA', 'sf': 'CA',
    'newyork': 'NY', 'nyc': 'NY', 'manhattan': 'NY', 'brooklyn': 'NY',
    'florida': 'FL', 'miami': 'FL', 'tampa': 'FL', 'orlando': 'FL', 'jacksonville': 'FL',
    'chicago': 'IL', 'illinois': 'IL',
    'atlanta': 'GA', 'georgia': 'GA',
    'boston': 'MA', 'massachusetts': 'MA',
    'seattle': 'WA', 'washington': 'WA',
    'denver': 'CO', 'colorado': 'CO',
    'phoenix': 'AZ', 'arizona': 'AZ',
    'minnesota': 'MN', 'minneapolis': 'MN',
    'michigan': 'MI', 'detroit': 'MI',
    'pennsylvania': 'PA', 'philly': 'PA', 'philadelphia': 'PA', 'pittsburgh': 'PA',
    'ohio': 'OH', 'cleveland': 'OH', 'columbus': 'OH', 'cincinnati': 'OH',
    'carolina': 'NC', 'raleigh': 'NC', 'charlotte': 'NC',
    'virginia': 'VA', 'richmond': 'VA', 'dc': 'DC', 'maryland': 'MD', 'baltimore': 'MD',
    'newjersey': 'NJ', 'jersey': 'NJ',
    'wisconsin': 'WI', 'milwaukee': 'WI',
    'missouri': 'MO', 'stlouis': 'MO', 'kansascity': 'MO',
    'indiana': 'IN', 'indianapolis': 'IN',
    'tennessee': 'TN', 'nashville': 'TN', 'memphis': 'TN',
    'utah': 'UT', 'saltlake': 'UT',
    'oregon': 'OR', 'portland': 'OR',
    'nevada': 'NV', 'vegas': 'NV',
    'alabama': 'AL', 'birmingham': 'AL',
    'louisiana': 'LA', 'neworleans': 'LA',
    'kentucky': 'KY', 'louisville': 'KY',
    'oklahoma': 'OK',
    'connecticut': 'CT',
    'iowa': 'IA',
    'arkansas': 'AR',
    'kansas': 'KS',
    'nebraska': 'NE', 'omaha': 'NE', 'nelnet': 'NE', # Added Nelnet -> NE explicitly!
}

def harvest_from_files(base_dir):
    email_to_state = {}
    domain_to_state = {}
    
    for root, dirs, files in os.walk(base_dir):
        if 'node_modules' in root or '.git' in root or '.gemini' in root:
            continue
        for f in files:
            ext = f.lower().split('.')[-1]
            filepath = os.path.join(root, f)
            try:
                if ext == 'csv':
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as fp:
                        reader = csv.DictReader(fp)
                        for row in reader:
                            em = row.get('email') or row.get('Email') or row.get('EMAIL') or ''
                            st = row.get('state') or row.get('State') or row.get('STATE') or row.get('location') or row.get('Location') or ''
                            if em and st:
                                extracted, _ = extract_state_detailed(st)
                                if extracted and '@' in em:
                                    email_to_state[em.lower().strip()] = extracted
                                    dom = em.split('@')[-1].lower().strip()
                                    if dom not in {'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com'}:
                                        domain_to_state[dom] = extracted
                elif ext == 'json' and 'package' not in f and 'tsconfig' not in f:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as fp:
                        data = json.load(fp)
                        items = data if isinstance(data, list) else data.get('recruiters') or data.get('data') or []
                        if isinstance(items, list):
                            for row in items:
                                if isinstance(row, dict):
                                    em = row.get('email') or row.get('Email') or ''
                                    st = row.get('state') or row.get('State') or row.get('location') or ''
                                    if em and st:
                                        extracted, _ = extract_state_detailed(st)
                                        if extracted and '@' in em:
                                            email_to_state[em.lower().strip()] = extracted
                                            dom = em.split('@')[-1].lower().strip()
                                            if dom not in {'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com'}:
                                                domain_to_state[dom] = extracted
                elif ext == 'xlsx' and HAS_PANDAS:
                    df = pd.read_excel(filepath)
                    cols = {c.lower(): c for c in df.columns}
                    em_col = cols.get('email')
                    st_col = cols.get('state') or cols.get('location')
                    if em_col and st_col:
                        for _, row in df.iterrows():
                            em = str(row[em_col])
                            st = str(row[st_col])
                            if em and st and em != 'nan' and st != 'nan':
                                extracted, _ = extract_state_detailed(st)
                                if extracted and '@' in em:
                                    email_to_state[em.lower().strip()] = extracted
                                    dom = em.split('@')[-1].lower().strip()
                                    if dom not in {'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com'}:
                                        domain_to_state[dom] = extracted
            except Exception:
                pass
    return email_to_state, domain_to_state

def run_universal_engine():
    db = SessionLocal()
    t0 = time.time()
    print("=== STARTING UNIVERSAL FILE HARVESTING & HEURISTIC ENGINE ===", flush=True)
    
    print("Harvesting local spreadsheet & backup knowledge across C:\\TalentOpsAI...", flush=True)
    file_em_map, file_dom_map = harvest_from_files('C:\\TalentOpsAI')
    print(f"Harvested {len(file_em_map):,} email mappings and {len(file_dom_map):,} domain mappings from disk files.", flush=True)
    
    last_id = 0
    total_updated = 0
    from_file = 0
    from_heuristic = 0
    
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
            em = (r['email'] or '').lower().strip()
            nts = (r['notes'] or '').lower()
            
            chosen_state = None
            
            # 1. Exact email match from files
            if em in file_em_map:
                chosen_state = file_em_map[em]
                from_file += 1
            # 2. Domain match from files
            elif '@' in em and em.split('@')[-1] in file_dom_map:
                chosen_state = file_dom_map[em.split('@')[-1]]
                from_file += 1
            # 3. Keyword heuristic on domain or username
            else:
                for kw, st in DOMAIN_KEYWORD_TO_STATE.items():
                    if kw in em or kw in nts:
                        chosen_state = st
                        from_heuristic += 1
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
    print(f"UNIVERSAL HARVESTING & HEURISTICS COMPLETE!")
    print(f"Time Taken: {elapsed}s")
    print(f"Total States Backfilled: {total_updated:,}")
    print(f"  - From Local Spreadsheets/Backups: {from_file:,}")
    print(f"  - From Domain/Keyword Heuristics: {from_heuristic:,}")
    print("=======================================================", flush=True)
    db.close()

if __name__ == '__main__':
    run_universal_engine()
