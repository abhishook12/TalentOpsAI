import os
import pandas as pd
import psycopg
import time
import io
import json
from dotenv import load_dotenv
import warnings

# Suppress pandas warnings
warnings.filterwarnings('ignore')

load_dotenv()
remote_url = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

desktop_path = r'C:\Users\User\Desktop'
MAX_COLS = 13
MAX_TARGET = 1000000

print("Connecting to Supabase to fetch existing emails (this may take a moment)...")
with psycopg.connect(remote_url) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT email FROM recruiters")
        existing_emails = set(row[0].lower() for row in cur.fetchall() if row[0])

print(f"Found {len(existing_emails)} existing recruiters in Supabase.")

total_synced = 0
files_processed = 0
files_skipped = 0

for root, dirs, files in os.walk(desktop_path):
    if any(skip in root for skip in ['node_modules', '.git', 'venv', '__pycache__']):
        continue
    for f in files:
        if f.endswith(('.csv', '.xls', '.xlsx')):
            fp = os.path.join(root, f)
            try:
                if f.endswith('.csv'):
                    df = pd.read_csv(fp, low_memory=False, on_bad_lines='skip')
                else:
                    df = pd.read_excel(fp)
                    
                cols = len(df.columns)
                if cols > MAX_COLS:
                    print(f"Skipping {fp} - too many columns ({cols})")
                    files_skipped += 1
                    continue
                    
                # Find email and name cols
                email_col = next((c for c in df.columns if str(c).lower().strip() in ['email', 'email_address', 'contact_email', 'work_email', 'e-mail']), None)
                if not email_col:
                    # Fallback check any column that might contain 'email' in its name
                    email_col = next((c for c in df.columns if 'email' in str(c).lower()), None)
                    
                if not email_col:
                    continue
                    
                name_col = next((c for c in df.columns if str(c).lower().strip() in ['name', 'full_name', 'recruiter_name', 'contact_name', 'first_name', 'recruiter']), None)
                if not name_col:
                    name_col = next((c for c in df.columns if 'name' in str(c).lower()), None)
                    
                if not name_col:
                    df['recruiter_name'] = 'Unknown Recruiter'
                    name_col = 'recruiter_name'
                    
                df = df[[name_col, email_col]].dropna(subset=[email_col])
                df = df.rename(columns={name_col: 'recruiter_name', email_col: 'email'})
                
                # Clean and dedupe
                df['email_lower'] = df['email'].astype(str).str.lower().str.strip().str[:150]
                df = df[df['email_lower'].str.contains('@', na=False)]
                
                new_recruiters = df[~df['email_lower'].isin(existing_emails)].copy()
                new_recruiters = new_recruiters.drop_duplicates(subset=['email_lower'])
                new_recruiters = new_recruiters.drop(columns=['email_lower'])
                
                new_recruiters['recruiter_name'] = new_recruiters['recruiter_name'].fillna('Unknown Recruiter').astype(str).str[:150]
                new_recruiters['email'] = new_recruiters['email'].fillna('no-email@missing.local').astype(str).str[:150]
                
                if new_recruiters.empty:
                    files_processed += 1
                    continue
                    
                print(f"[{fp}] Found {len(new_recruiters)} new records. Uploading...")
                
                csv_buffer = io.StringIO()
                new_recruiters.to_csv(csv_buffer, index=False, header=False, sep='\t')
                csv_buffer.seek(0)
                
                with psycopg.connect(remote_url) as conn:
                    with conn.cursor() as cur:
                        with cur.copy("COPY recruiters (recruiter_name, email) FROM STDIN WITH (FORMAT CSV, DELIMITER '\t')") as copy:
                            while data := csv_buffer.read(8192):
                                copy.write(data)
                    conn.commit()
                    
                existing_emails.update(new_recruiters['email'].str.lower())
                total_synced += len(new_recruiters)
                files_processed += 1
                
                print(f"  Success. Total synced this run: {total_synced}. DB Total approx: {len(existing_emails)}")
                
                if len(existing_emails) >= MAX_TARGET:
                    print("Reached target of 1 million recruiters! Stopping.")
                    break
                    
            except Exception as e:
                print(f"Error processing {fp}: {e}")

print(f"Done mass sync from Desktop. Processed {files_processed} files, skipped {files_skipped} files. Added {total_synced} new records.")
