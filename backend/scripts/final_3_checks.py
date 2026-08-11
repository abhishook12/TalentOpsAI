import psycopg
import duckdb
import os
from dotenv import load_dotenv

load_dotenv('C:/TalentOpsAI/backend/.env')

print('--- CHECK 1: PostgreSQL Companies DB State ---')
db_url = os.environ['DATABASE_URL'].replace('+psycopg', '')
conn = psycopg.connect(db_url)
print('Total Companies:', conn.execute('SELECT COUNT(*) FROM companies').fetchone()[0])
print('Total Recruiters in PG:', conn.execute('SELECT COUNT(*) FROM recruiters').fetchone()[0])

print('\n--- CHECK 2: DuckDB Parquet Engine State ---')
duck = duckdb.connect()
print('Total Recruiters in Parquet:', duck.execute("SELECT COUNT(*) FROM read_parquet('C:/TalentOpsAI/backend/data/recruiters_full.parquet')").fetchone()[0])
print('Local Parquet File Size:', os.path.getsize('C:/TalentOpsAI/backend/data/recruiters_full.parquet'))

print('\n--- CHECK 3: Supabase Storage Integration ---')
from supabase import create_client, Client
supabase: Client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SECRET_KEY'])
res = supabase.storage.from_('data-assets').download('recruiters_full.parquet')
print('Remote Parquet File Size:', len(res))
