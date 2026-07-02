import csv
import glob
import os
import psycopg
import time

DB_URL = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

VALID_STATES = {
    'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA',
    'HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
    'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
    'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
    'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY'
}

def restore():
    print("=== STARTING MASS RESTORATION OF ORIGINAL CSV LOCATION & STATES ===")
    t0 = time.time()
    conn = psycopg.connect(DB_URL)
    cur = conn.cursor()
    
    print("Loading database email map...")
    cur.execute("SELECT LOWER(TRIM(email)), recruiter_id, state, location FROM recruiters WHERE email IS NOT NULL AND TRIM(email) != ''")
    db_map = {}
    for em, rid, st, loc in cur.fetchall():
        db_map[em] = (rid, st, loc)
    print(f"Loaded {len(db_map):,} emails from database.")
    
    # We will scan all large CSV files
    csv_files = glob.glob("c:/TalentOpsAI/**/*.csv", recursive=True)
    
    updates = {} # rid -> (new_state, new_loc)
    
    for filepath in csv_files:
        if os.path.getsize(filepath) < 50000:
            continue
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames or 'email' not in [c.lower() for c in reader.fieldnames]:
                    continue
                
                # map lowercase column names
                col_map = {c.lower(): c for c in reader.fieldnames if c}
                em_col = col_map.get('email')
                st_col = col_map.get('state')
                loc_col = col_map.get('location')
                
                if not em_col or (not st_col and not loc_col):
                    continue
                
                for row in reader:
                    em = row.get(em_col, '').strip().lower()
                    if not em or em not in db_map:
                        continue
                    
                    rid, curr_st, curr_loc = db_map[em]
                    
                    st_val = row.get(st_col, '').strip().upper() if st_col else ''
                    loc_val = row.get(loc_col, '').strip() if loc_col else ''
                    
                    new_st = curr_st
                    new_loc = curr_loc
                    
                    if st_val in VALID_STATES:
                        new_st = st_val
                    elif loc_val and len(loc_val) >= 2 and loc_val[-2:].upper() in VALID_STATES:
                        new_st = loc_val[-2:].upper()
                        
                    if loc_val and (not curr_loc or len(loc_val) > len(str(curr_loc))):
                        new_loc = loc_val
                        
                    if new_st != curr_st or (new_loc and new_loc != curr_loc):
                        updates[rid] = (new_st, new_loc, rid)
                        # update local db_map tracking so subsequent files can improve further
                        db_map[em] = (rid, new_st, new_loc)
        except Exception as e:
            pass

    print(f"Found {len(updates):,} candidate profiles to restore to their original state/location!")
    
    # Count how many are moving to TX
    tx_count = sum(1 for st, loc, rid in updates.values() if st == 'TX')
    print(f"Specifically restoring {tx_count:,} recruiters to TEXAS (TX)!")
    
    if updates:
        print("Executing bulk database updates...")
        update_list = list(updates.values())
        batch_size = 5000
        for i in range(0, len(update_list), batch_size):
            cur.executemany("UPDATE recruiters SET state = %s, location = %s WHERE recruiter_id = %s", update_list[i:i+batch_size])
            conn.commit()
            print(f"Updated {min(i+batch_size, len(update_list)):,} / {len(update_list):,} records...")
            
    cur.close()
    conn.close()
    print(f"=== RESTORATION COMPLETE IN {time.time() - t0:.2f}s ===")

if __name__ == "__main__":
    restore()
