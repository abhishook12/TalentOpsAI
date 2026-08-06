import psycopg
conn = psycopg.connect('postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres')
cur = conn.cursor()
cur.execute("SELECT recruiter_name, title, specialization FROM recruiters WHERE recruiter_name ILIKE '%Braxton Miller%';")
print(cur.fetchall())
