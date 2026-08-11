import psycopg
from psycopg.rows import dict_row

DB_URL = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

print("Connecting to DB to create bucket...")
try:
    with psycopg.connect(DB_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
                VALUES ('data-assets', 'data-assets', true, null, null)
                ON CONFLICT (id) DO NOTHING;
            """)
            conn.commit()
    print("Bucket 'data-assets' created successfully in database.")
except Exception as e:
    print("Failed:", e)
