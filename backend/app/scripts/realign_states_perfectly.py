import psycopg
import re
import time

DB_URL = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

VALID_STATES = {
    'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA',
    'HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
    'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
    'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
    'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY'
}

def run_realignment():
    print("=== STARTING PERFECT STATE REALIGNMENT FROM LOCATION & NOTES ===")
    t0 = time.time()
    conn = psycopg.connect(DB_URL)
    cur = conn.cursor()
    
    cur.execute("SELECT recruiter_id, location, notes, state FROM recruiters WHERE location IS NOT NULL OR notes IS NOT NULL")
    rows = cur.fetchall()
    print(f"Loaded {len(rows):,} candidates for inspection...")
    
    geo_re = re.compile(r'\[GEO:\s*[^,]+,\s*([A-Z]{2})\b')
    loc_re = re.compile(r',\s*([A-Z]{2})\b')
    
    updates = []
    tx_count = 0
    
    for rid, loc, notes, st in rows:
        new_st = None
        if loc:
            m = loc_re.search(loc)
            if m and m.group(1) in VALID_STATES:
                new_st = m.group(1)
        if not new_st and notes:
            m = geo_re.search(notes)
            if m and m.group(1) in VALID_STATES:
                new_st = m.group(1)
        
        if new_st and new_st != st:
            updates.append((new_st, rid))
            if new_st == 'TX':
                tx_count += 1

    print(f"Found {len(updates):,} state mismatches across the database!")
    print(f"Specifically moving {tx_count:,} recruiters directly into TEXAS (TX)!")
    
    if updates:
        print("Executing bulk database update...")
        cur.executemany("UPDATE recruiters SET state = %s WHERE recruiter_id = %s", updates)
        conn.commit()
    
    cur.close()
    conn.close()
    print(f"=== REALIGNMENT COMPLETE IN {time.time() - t0:.2f}s ===")

if __name__ == "__main__":
    run_realignment()
