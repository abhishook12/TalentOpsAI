import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.append(os.path.abspath('C:/TalentOpsAI/backend'))
from dotenv import load_dotenv
load_dotenv(os.path.join('C:/TalentOpsAI/backend', '.env'))

import psycopg
from app.database import SessionLocal
from sqlalchemy import text

# 1. Check size BEFORE using SQLAlchemy
db = SessionLocal()
before = float(db.execute(text('SELECT pg_database_size(current_database()) / 1048576.0')).scalar())
print(f'Database Size BEFORE Cleanup: {before:.2f} MB')

tables = db.execute(text(
    "SELECT relname, pg_total_relation_size(relid) / 1048576.0 AS total_mb, "
    "n_dead_tup, n_live_tup "
    "FROM pg_stat_user_tables "
    "ORDER BY pg_total_relation_size(relid) DESC LIMIT 10"
)).fetchall()
print('\nTop Tables by Size (Before VACUUM):')
for t in tables:
    print(f'  {t[0]}: {float(t[1]):.2f} MB | Live: {t[3]:,} | Dead Tuples: {t[2]:,}')

# Get raw connection string from environment, stripping SQLAlchemy driver prefix
raw_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DATABASE_URL") or ""
db_url = raw_url.replace("postgresql+psycopg://", "postgresql://")
if db_url.startswith("postgresql://"):
    pass  # good
elif not db_url:
    print("ERROR: No DATABASE_URL found in environment")
    sys.exit(1)
db.close()

# 2. Open a fresh psycopg connection with autocommit=True for VACUUM
print('\n--- Opening direct autocommit connection for VACUUM ---')
conn = psycopg.connect(db_url, autocommit=True, prepare_threshold=None)
cursor = conn.cursor()

print('[Step 1] Running VACUUM on recruiters table...')
cursor.execute('VACUUM recruiters')
print('  -> VACUUM recruiters complete.')

print('[Step 2] Running VACUUM on companies table...')
cursor.execute('VACUUM companies')
print('  -> VACUUM companies complete.')

print('[Step 3] Running VACUUM on enrichment_results table...')
cursor.execute('VACUUM enrichment_results')
print('  -> VACUUM enrichment_results complete.')

print('[Step 4] Running ANALYZE for query planner optimization...')
cursor.execute('ANALYZE recruiters')
cursor.execute('ANALYZE companies')
print('  -> ANALYZE complete.')

cursor.close()
conn.close()

# 3. Check size AFTER
db2 = SessionLocal()
after = float(db2.execute(text('SELECT pg_database_size(current_database()) / 1048576.0')).scalar())
saved = before - after
print(f'\nDatabase Size AFTER Cleanup: {after:.2f} MB')
print(f'Space Reclaimed: {saved:.2f} MB')
print(f'Storage Utilization: {(after / 500.0) * 100:.1f}% of 500 MB Supabase cap')

tables2 = db2.execute(text(
    "SELECT relname, pg_total_relation_size(relid) / 1048576.0 AS total_mb, "
    "n_dead_tup, n_live_tup "
    "FROM pg_stat_user_tables "
    "ORDER BY pg_total_relation_size(relid) DESC LIMIT 10"
)).fetchall()
print('\nTop Tables by Size (After VACUUM):')
for t in tables2:
    print(f'  {t[0]}: {float(t[1]):.2f} MB | Live: {t[3]:,} | Dead Tuples: {t[2]:,}')

db2.close()
print('\n✅ Database optimization complete!')
