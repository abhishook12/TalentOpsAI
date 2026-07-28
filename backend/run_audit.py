import psycopg
import json

def run_audit():
    conn = psycopg.connect('postgresql://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres')
    c = conn.cursor()
    
    report = {"database": "PostgreSQL (Production)"}
    
    # 1. Total counts
    report['total_recruiters'] = c.execute("SELECT COUNT(*) FROM recruiters").fetchone()[0]
    report['total_companies'] = c.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    
    # 2. Orphaned Recruiters
    orphans = c.execute("SELECT COUNT(*) FROM recruiters WHERE company_id IS NOT NULL AND company_id NOT IN (SELECT company_id FROM companies)").fetchone()[0]
    report['orphaned_recruiters'] = orphans
    
    # 3. Duplicate Emails
    dup_emails = c.execute("""
        SELECT email, COUNT(*) 
        FROM recruiters 
        WHERE email IS NOT NULL AND email != '' 
        GROUP BY email 
        HAVING COUNT(*) > 1
    """).fetchall()
    report['duplicate_emails'] = len(dup_emails)
    
    # 4. Duplicate Phones
    dup_phones = c.execute("""
        SELECT phone, COUNT(*) 
        FROM recruiters 
        WHERE phone IS NOT NULL AND phone != '' 
        GROUP BY phone 
        HAVING COUNT(*) > 1
    """).fetchall()
    report['duplicate_phones'] = len(dup_phones)
    
    # 5. Missing Indexes Check
    indexes = c.execute("""
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE tablename = 'recruiters' OR tablename = 'companies'
    """).fetchall()
    report['indexes'] = [i[0] for i in indexes]
    
    # 6. Null States
    null_states = c.execute("SELECT COUNT(*) FROM recruiters WHERE state IS NULL OR state = ''").fetchone()[0]
    report['null_states'] = null_states

    # 7. Distribution of Data Source
    data_sources = c.execute("SELECT data_source, COUNT(*) FROM recruiters GROUP BY data_source").fetchall()
    report['data_sources'] = {ds[0]: ds[1] for ds in data_sources}

    conn.close()
    
    with open("data_audit.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print("Audit complete.")

if __name__ == "__main__":
    run_audit()
