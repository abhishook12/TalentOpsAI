import sqlite3
import pandas as pd
import psycopg
import time
import io
import os
from dotenv import load_dotenv

load_dotenv()
remote_url = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

print("Connecting to local SQLite dev.db...")
sqlite_conn = sqlite3.connect('C:/TalentOpsAI/dev.db')
local_df = pd.read_sql("SELECT recruiter_name, email FROM recruiters WHERE email NOT LIKE 'fake_%'", sqlite_conn)
print(f"Loaded {len(local_df)} valid recruiters from local DB.")

print("Connecting to Supabase to fetch existing...")
with psycopg.connect(remote_url) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT email FROM recruiters")
        existing_emails = set(row[0].lower() for row in cur.fetchall() if row[0])

print(f"Found {len(existing_emails)} existing recruiters in Supabase.")

local_df['email_lower'] = local_df['email'].str.lower()
new_recruiters = local_df[~local_df['email_lower'].isin(existing_emails)].copy()
new_recruiters = new_recruiters.drop_duplicates(subset=['email_lower'])
new_recruiters = new_recruiters.drop(columns=['email_lower'])
new_recruiters['recruiter_name'] = new_recruiters['recruiter_name'].fillna('Unknown Recruiter').str[:150]
new_recruiters['email'] = new_recruiters['email'].fillna('no-email@missing.local').str[:150]
# Drop duplicates again after truncation just in case
new_recruiters = new_recruiters.drop_duplicates(subset=['email'])
print(f"Identified {len(new_recruiters)} new recruiters to sync.")

if not new_recruiters.empty:
    print("Beginning ultra-fast bulk COPY...")
    start = time.time()
    
    # Save to in-memory CSV
    csv_buffer = io.StringIO()
    new_recruiters.to_csv(csv_buffer, index=False, header=False, sep='\t')
    csv_buffer.seek(0)
    
    try:
        with psycopg.connect(remote_url) as conn:
            with conn.cursor() as cur:
                with cur.copy("COPY recruiters (recruiter_name, email) FROM STDIN WITH (FORMAT CSV, DELIMITER '\t')") as copy:
                    while data := csv_buffer.read(8192):
                        copy.write(data)
            conn.commit()
        print(f"Sync complete in {time.time() - start:.2f} seconds!")
    except Exception as e:
        print(f"Error during COPY sync: {e}")
else:
    print("No new recruiters to sync.")

with psycopg.connect(remote_url) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM recruiters")
        final_count = cur.fetchone()[0]
        print(f"Final Supabase Count: {final_count}")
