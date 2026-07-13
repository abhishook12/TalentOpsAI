import time
import psycopg
import re

DB_URL = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

def execute_cleanse():
    print("=== STARTING ULTIMATE DATA CLEANSE ===", flush=True)
    t0 = time.time()
    conn = psycopg.connect(DB_URL)
    cur = conn.cursor()

    # Step 1: Fix squished recruiter names based on email patterns
    print("\n[Step 1] Repairing squished recruiter names...", flush=True)
    
    cur.execute("""
        SELECT recruiter_id, email, recruiter_name 
        FROM recruiters 
        WHERE recruiter_name !~ ' ' 
          AND email ~ '^[a-zA-Z0-9]+[.-][a-zA-Z0-9]+@'
    """)
    rows = cur.fetchall()
    
    updates = []
    for r_id, email, old_name in rows:
        local_part = email.split('@')[0]
        parts = re.split(r'[.\-_]', local_part)
        
        if len(parts) >= 2:
            first_name = parts[0].capitalize()
            last_name = parts[-1].capitalize()
            new_name = f"{first_name} {last_name}"
            
            squished_new = (first_name + last_name).lower()
            if old_name.lower() == squished_new or old_name.lower() == first_name.lower():
                updates.append((new_name, r_id))
            elif old_name.lower() == local_part.replace('.', '').replace('-', '').replace('_', '').lower():
                 updates.append((new_name, r_id))
            elif len(first_name) > 1 and len(last_name) > 1:
                updates.append((new_name, r_id))

    print(f" -> Found {len(updates)} profiles to repair.", flush=True)
    
    if updates:
        cur.executemany("UPDATE recruiters SET recruiter_name = %s WHERE recruiter_id = %s", updates)
        conn.commit()
    print(f" -> Successfully repaired {len(updates)} recruiter names!", flush=True)


    # Step 2: Fix phantom companies (Deduplication)
    print("\n[Step 2] Resolving phantom companies (Deduplication)...", flush=True)
    
    mapping = {
        'Insightglobal': 'Insight Global',
        'Roberthalf': 'Robert Half',
        'Randstadusa': 'Randstad',
        'Vaco': 'Vaco',
        'Roberthalflegal': 'Robert Half',
        'Roberthalftechnology': 'Robert Half',
        'Kforce': 'Kforce',
        'Actalent': 'Actalent',
    }

    canonical_ids = {}
    for bad_name, good_name in mapping.items():
        cur.execute("""
            SELECT c.company_id 
            FROM companies c
            WHERE c.company_name = %s 
            ORDER BY (SELECT count(*) FROM recruiters r WHERE r.company_id = c.company_id) DESC 
            LIMIT 1
        """, (good_name,))
        res = cur.fetchone()
        if res:
            canonical_ids[good_name] = res[0]
            
            cur.execute("SELECT company_id FROM companies WHERE company_name ILIKE %s AND company_id != %s", (bad_name, res[0]))
            phantoms = cur.fetchall()
            
            for (p_id,) in phantoms:
                cur.execute("UPDATE recruiters SET company_id = %s WHERE company_id = %s", (res[0], p_id))
                cur.execute("UPDATE companies SET is_active = false WHERE company_id = %s", (p_id,))
                print(f" -> Migrated recruiters from phantom '{bad_name}' (ID: {p_id}) to '{good_name}' (ID: {res[0]})", flush=True)
    
    conn.commit()
    
    # Step 3: Exact-name duplicates
    print("\n[Step 3] Merging exact-name duplicate companies...", flush=True)
    cur.execute("""
        SELECT company_name, array_agg(company_id ORDER BY (SELECT count(*) FROM recruiters r WHERE r.company_id = c.company_id) DESC) 
        FROM companies c 
        WHERE is_active = true OR is_active IS NULL
        GROUP BY company_name 
        HAVING count(*) > 1
    """)
    duplicates = cur.fetchall()
    
    merged_count = 0
    for comp_name, ids in duplicates:
        canonical_id = ids[0]
        phantom_ids = ids[1:]
        
        for p_id in phantom_ids:
            cur.execute("UPDATE recruiters SET company_id = %s WHERE company_id = %s", (canonical_id, p_id), prepare=False)
            cur.execute("UPDATE companies SET is_active = false, company_name = %s WHERE company_id = %s", (f"[DUPLICATE] {comp_name}", p_id), prepare=False)
            merged_count += 1
            
    conn.commit()
    print(f" -> Merged {merged_count} exact-name phantom companies into their canonical parents!", flush=True)

    print(f"\n=== CLEANSE COMPLETE IN {time.time() - t0:.2f}s ===", flush=True)
    cur.close()
    conn.close()

if __name__ == "__main__":
    execute_cleanse()
