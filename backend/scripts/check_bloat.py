import psycopg, os
from dotenv import load_dotenv
load_dotenv('C:/TalentOpsAI/backend/.env')

conn = psycopg.connect(os.getenv('DATABASE_URL').replace('postgresql+psycopg://','postgresql://'), autocommit=True)
cur = conn.cursor()

# Table sizes
cur.execute("""
    SELECT relname, pg_size_pretty(pg_total_relation_size(C.oid)) as size, 
           pg_total_relation_size(C.oid)/1048576 as mb
    FROM pg_class C 
    LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace) 
    WHERE nspname = 'public' 
    ORDER BY pg_total_relation_size(C.oid) DESC LIMIT 15
""")
rows = cur.fetchall()
print("TABLE SIZE BREAKDOWN:")
for r in rows:
    print(f"  {r[0]}: {r[1]} ({r[2]} MB)")

# Row counts for bloat tables
for tbl in ['enrichment_results', 'enrichment_audit', 'recruiter_emails', 'mailintel_tracking', 'mailintel_evidence', 'raw_uploads', 'recruiter_phones', 'sentinel_state']:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        print(f"\n{tbl} rows: {cur.fetchone()[0]:,}")
    except Exception as e:
        print(f"\n{tbl}: {e}")
        conn.rollback()

# Check how much space unknown recruiters still occupy
cur.execute("SELECT COUNT(*) FROM recruiters WHERE email_status = 'unknown'")
print(f"\nRemaining unknown recruiters: {cur.fetchone()[0]:,}")

cur.execute("SELECT pg_database_size(current_database()) / 1048576.0")
print(f"\nTotal DB Size: {cur.fetchone()[0]:.2f} MB")

conn.close()
