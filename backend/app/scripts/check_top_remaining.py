import psycopg

conn = psycopg.connect('postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres')
cur = conn.cursor()
cur.execute("""
    SELECT split_part(email, '@', 2) as dom, count(*) 
    FROM recruiters 
    WHERE (state IS NULL OR state = '') AND email IS NOT NULL AND email != '' 
    GROUP BY dom ORDER BY count(*) DESC OFFSET 50 LIMIT 80
""")
for dom, cnt in cur.fetchall():
    try:
        print(f"{dom}: {cnt}")
    except Exception:
        pass
conn.close()
