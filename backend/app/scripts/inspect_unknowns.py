import psycopg

conn = psycopg.connect('postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres')
cur = conn.cursor()
cur.execute("""
    SELECT location, notes, email, company_id 
    FROM recruiters 
    WHERE state IS NULL OR state = ''
    LIMIT 20
""")
rows = cur.fetchall()
print("Sample Unknown Records:")
for r in rows:
    print(r)
conn.close()
