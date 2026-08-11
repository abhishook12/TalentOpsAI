import psycopg
conn = psycopg.connect('postgresql://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres')
print('Companies in PG:', conn.execute('SELECT COUNT(*) FROM companies').fetchone()[0])
print('Recruiters in PG:', conn.execute('SELECT COUNT(*) FROM recruiters').fetchone()[0])

import duckdb
duck = duckdb.connect()
print('Recruiters in Parquet:', duck.execute("SELECT COUNT(*) FROM read_parquet('C:/TalentOpsAI/backend/data/recruiters_full.parquet')").fetchone()[0])
