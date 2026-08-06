import psycopg
conn = psycopg.connect('postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres')
cur = conn.cursor()
cur.execute("SELECT company_name, website, email_pattern FROM companies WHERE company_name ILIKE '%Insight Global%';")
print(cur.fetchall())
