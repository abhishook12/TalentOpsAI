import psycopg

conn = psycopg.connect('postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres')
cur = conn.cursor()
cur.execute("""
    SELECT count(*), 
           count(CASE WHEN phone IS NOT NULL AND phone != '' THEN 1 END) as has_phone,
           count(CASE WHEN email IS NOT NULL AND email != '' THEN 1 END) as has_email,
           count(CASE WHEN notes IS NOT NULL AND notes != '' THEN 1 END) as has_notes,
           count(CASE WHEN company_id IS NOT NULL THEN 1 END) as has_company
    FROM recruiters 
    WHERE state IS NULL OR state = ''
""")
print("Remaining Unknown Stats:", cur.fetchone())
conn.close()
