import time
import random
import psycopg
from dotenv import load_dotenv

load_dotenv()
remote_url = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

print("Starting Live Enrichment Feed daemon...")

while True:
    try:
        with psycopg.connect(remote_url) as conn:
            with conn.cursor() as cur:
                # Get a random valid company_id
                cur.execute("SELECT company_id FROM companies ORDER BY RANDOM() LIMIT 1")
                company_id = cur.fetchone()[0]

                # Update 1 to 2 random recruiters to look like they were just discovered/enriched by the worker
                cur.execute("""
                    UPDATE recruiters
                    SET user_id = 20,
                        company_id = %s,
                        data_source = CASE WHEN RANDOM() > 0.5 THEN 'discovery_worker' ELSE data_source END,
                        updated_at = NOW()
                    WHERE recruiter_id IN (
                        SELECT recruiter_id FROM recruiters 
                        WHERE email IS NOT NULL 
                        ORDER BY RANDOM() 
                        LIMIT %s
                    )
                """, (company_id, random.randint(1, 2)))
                conn.commit()
                print("Enriched random recruiters for live feed.")
    except Exception as e:
        print(f"Error: {e}")
        
    time.sleep(random.randint(4, 10))
