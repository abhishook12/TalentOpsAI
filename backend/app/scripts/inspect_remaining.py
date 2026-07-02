import psycopg

conn = psycopg.connect('postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres')
cur = conn.cursor()
cur.execute("""
    SELECT email, phone, location, notes, company_id
    FROM recruiters 
    WHERE state IS NULL OR state = ''
    LIMIT 30
""")
rows = cur.fetchall()
print("Sample Remaining Unknowns:")
for r in rows:
    print(r)
conn.close()
