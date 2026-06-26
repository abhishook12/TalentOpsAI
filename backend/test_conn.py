import psycopg

conn = psycopg.connect(
    'postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require'
)
cur = conn.cursor()
cur.execute('SELECT count(*) FROM recruiters')
print(f'Total recruiters: {cur.fetchone()[0]}')
cur.execute('SELECT count(*) FROM companies')
print(f'Total companies: {cur.fetchone()[0]}')
cur.execute("SELECT count(*) FROM recruiters WHERE repair_reason IS NOT NULL AND repair_reason != ''")
print(f'Already tagged with repair_reason: {cur.fetchone()[0]}')
conn.close()
print('Connection OK!')
