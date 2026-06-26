import os
import sys
import psycopg

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__))))
from enrich_recruiter_contacts import EnrichmentWorker
from types import SimpleNamespace

DB_URL = 'postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require'

def main():
    conn = psycopg.connect(DB_URL)
    cur = conn.cursor()
    
    # Load companies
    cur.execute("SELECT company_id, company_name FROM companies")
    companies = cur.fetchall()
    company_map = {r[0]: r[1] for r in companies}
    
    # Instantiate FakeDB and worker to check is_human_name
    class FakeDB:
        def query(self, *a, **kw): return self
        def filter(self, *a, **kw): return self
        def all(self): return []
        def count(self): return 0
    
    args = SimpleNamespace(
        dry_run=True, apply=False, minimum_confidence=70,
        batch_size=500, max_updates=500, all_recruiters=True
    )
    worker = EnrichmentWorker(FakeDB(), args)

    human_co_ids = set()
    for cid, cname in company_map.items():
        if cname and ' ' in cname and worker.is_human_name(cname, ''):
            human_co_ids.add(cid)
            
    print(f"Total human companies identified: {len(human_co_ids)}")
    
    placeholders = ','.join(str(x) for x in human_co_ids)
    
    # Count total records in this cohort
    cur.execute(f"SELECT count(*) FROM recruiters WHERE company_id IN ({placeholders})")
    total_cohort = cur.fetchone()[0]
    print(f"Total recruiters in cohort: {total_cohort}")
    
    # Count processed/repaired
    cur.execute(f"""
        SELECT count(*) FROM recruiters 
        WHERE company_id IN ({placeholders}) 
        AND repair_reason IS NOT NULL AND repair_reason != ''
    """)
    processed = cur.fetchone()[0]
    print(f"Processed/Repaired in cohort: {processed}")
    
    # Count unprocessed
    cur.execute(f"""
        SELECT count(*) FROM recruiters 
        WHERE company_id IN ({placeholders}) 
        AND (repair_reason IS NULL OR repair_reason = '')
    """)
    unprocessed = cur.fetchone()[0]
    print(f"Unprocessed in cohort: {unprocessed}")
    
    # Breakdown of repair reasons in the cohort
    cur.execute(f"""
        SELECT repair_reason, count(*) FROM recruiters 
        WHERE company_id IN ({placeholders})
        GROUP BY repair_reason
    """)
    print("\n=== Cohort Breakdown of repair_reason ===")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")
        
    conn.close()

if __name__ == '__main__':
    main()
