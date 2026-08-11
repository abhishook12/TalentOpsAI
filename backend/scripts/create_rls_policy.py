import psycopg
from psycopg.rows import dict_row

DB_URL = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

print("Connecting to DB to add permissive RLS policy...")
try:
    with psycopg.connect(DB_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            # Drop policy if exists
            cur.execute("DROP POLICY IF EXISTS allow_all_data_assets ON storage.objects;")
            
            # Create policy to allow all actions on data-assets bucket
            cur.execute("""
                CREATE POLICY allow_all_data_assets ON storage.objects
                FOR ALL USING (bucket_id = 'data-assets') WITH CHECK (bucket_id = 'data-assets');
            """)
            conn.commit()
    print("RLS policy 'allow_all_data_assets' created successfully.")
except Exception as e:
    print("Failed:", e)
