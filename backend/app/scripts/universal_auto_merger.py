import os
import time
import psycopg
from dotenv import load_dotenv

load_dotenv("C:/TalentOpsAI/backend/.env")
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgresql+psycopg://", "postgresql://")

def run():
    print("=== STARTING RAW PSYCOPG UNIVERSAL AUTO MERGER ===", flush=True)
    t0 = time.time()

    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT website, array_agg(company_id) as ids 
        FROM companies 
        WHERE website IS NOT NULL AND website != '' 
          AND website NOT ILIKE '%gmail.com%'
          AND website NOT ILIKE '%yahoo.com%'
          AND website NOT ILIKE '%hotmail.com%'
          AND website NOT ILIKE '%outlook.com%'
          AND website NOT ILIKE '%aol.com%'
        GROUP BY website 
        HAVING COUNT(*) > 1
    """)
    groups = cur.fetchall()
    print(f"Found {len(groups)} duplicate website groups.", flush=True)

    total_merged = 0

    for website, ids in groups:
        cur.execute("SELECT company_id, company_name FROM companies WHERE company_id = ANY(%s)", (ids,))
        companies = cur.fetchall()
        
        # Format: (company_id, company_name)
        sorted_companies = sorted(companies, key=lambda c: len(c[1]), reverse=True)
        canon_id, canon_name = sorted_companies[0]
        
        print(f"\nProcessing website: {website}", flush=True)
        print(f" -> Elected Canonical: {canon_name} (ID: {canon_id})", flush=True)

        for alias_id, alias_name in sorted_companies[1:]:
            print(f"    -> Merging alias: {alias_name} (ID: {alias_id})", flush=True)
            
            cur.execute("""
                INSERT INTO company_aliases (canonical_company_id, alias_name, alias_type)
                VALUES (%s, %s, 'domain_alias')
            """, (canon_id, alias_name))
            
            cur.execute("UPDATE recruiters SET company_id = %s WHERE company_id = %s", (canon_id, alias_id))
            print(f"       Reparented {cur.rowcount} recruiters", flush=True)
            
            cur.execute("UPDATE companies SET is_active = false WHERE company_id = %s", (alias_id,))
            total_merged += 1
            
        cur.execute("UPDATE companies SET is_active = true WHERE company_id = %s", (canon_id,))
        
    conn.commit()
    conn.close()
    
    print(f"\nSuccessfully merged {total_merged} duplicate companies.", flush=True)
    print(f"Done in {round(time.time() - t0, 2)}s.", flush=True)

if __name__ == "__main__":
    run()
