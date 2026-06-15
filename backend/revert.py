import psycopg2

conn = psycopg2.connect('postgresql://postgres.dcqvsvgrdsrgnbwwssup:rd%2Fnew%2Fjvminw@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres')
conn.autocommit = True
cur = conn.cursor()

query = """
UPDATE recruiters 
SET state = NULL, 
    state_source = NULL, 
    state_confidence = NULL, 
    state_reason = NULL, 
    last_scan_at = NULL 
WHERE state_source IN ('notes', 'review_reason', 'raw_data', 'metadata_json');
"""
cur.execute(query)
print(f"Reverted {cur.rowcount} rows.")
conn.close()
