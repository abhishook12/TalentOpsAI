import psycopg
conn = psycopg.connect('postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres')
cur = conn.cursor()
cur.execute("UPDATE companies SET website = 'insightglobal.com', email_pattern = 'insightglobal.com' WHERE company_name ILIKE '%Insight Global%';")
conn.commit()
print("Updated Insight Global.")
