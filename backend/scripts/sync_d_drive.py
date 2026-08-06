import os
import pandas as pd
import psycopg
import time
import io
import warnings
from dotenv import load_dotenv

warnings.filterwarnings('ignore')
load_dotenv()
remote_url = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

MAX_COLS = 13
MAX_TARGET = 1000000

print("Fetching existing emails from Supabase to prevent duplicates...")
with psycopg.connect(remote_url) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT email FROM recruiters")
        existing_emails = set(row[0].lower() for row in cur.fetchall() if row[0])

print(f"Loaded {len(existing_emails)} existing emails from DB.")

# Read the file list from the scan log
log_path = r'C:\Users\User\.gemini\antigravity\brain\e050007d-77bf-4880-ac17-0d8a6b8d4518\scratch\d_drive_scan.log'
files = []
with open(log_path, 'r', encoding='utf-8') as f:
    for line in f:
        if '|' in line:
            parts = line.strip().split(' | ', 1)
            if len(parts) == 2:
                files.append(parts[1])

print(f"Loaded {len(files)} paths from scan log.")

total_synced = 0
files_processed = 0
files_skipped_cols = 0
files_errored = 0

start_time = time.time()

for idx, fp in enumerate(files, 1):
    if not os.path.exists(fp):
        continue
        
    # Print status every 10 files
    if idx % 10 == 0:
        print(f"Progress: Processed {idx}/{len(files)} files. Total Synced: {total_synced}. DB approx: {len(existing_emails)}")

    try:
        if fp.lower().endswith('.csv'):
            df = pd.read_csv(fp, low_memory=False, on_bad_lines='skip', nrows=5)
            cols = len(df.columns)
            if cols > MAX_COLS:
                files_skipped_cols += 1
                continue
            df = pd.read_csv(fp, low_memory=False, on_bad_lines='skip')
        else:
            # Excel files might take too much memory if huge, but we try
            df = pd.read_excel(fp, nrows=5)
            cols = len(df.columns)
            if cols > MAX_COLS:
                files_skipped_cols += 1
                continue
            df = pd.read_excel(fp)
            
        # Find email and name cols
        email_col = next((c for c in df.columns if str(c).lower().strip() in ['email', 'email_address', 'contact_email', 'work_email', 'e-mail']), None)
        if not email_col:
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
        
        # Clean and dedupe exactly against DB length limits
        df['email'] = df['email'].astype(str).str.strip().str[:150]
        df['email_lower'] = df['email'].str.lower()
        df = df[df['email_lower'].str.contains('@', na=False)]
        
        new_recruiters = df[~df['email_lower'].isin(existing_emails)].copy()
        new_recruiters = new_recruiters.drop_duplicates(subset=['email_lower'])
        new_recruiters = new_recruiters.drop(columns=['email_lower'])
        
        new_recruiters['recruiter_name'] = new_recruiters['recruiter_name'].fillna('Unknown Recruiter').astype(str).str[:150]
        
        if new_recruiters.empty:
            files_processed += 1
            continue
            
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
        
        if len(existing_emails) >= MAX_TARGET:
            print("Reached target of 1 million recruiters! Stopping.")
            break
            
    except Exception as e:
        files_errored += 1
        pass # Silently skip unreadable files to maintain speed

print("\n" + "="*50)
print(f"D:\\ DRIVE SYNC COMPLETE in {int(time.time() - start_time)}s")
print(f"Files Successfully Processed: {files_processed}")
print(f"Files Skipped (>13 cols): {files_skipped_cols}")
print(f"Files Errored/Unreadable: {files_errored}")
print(f"New Unique Records Added: {total_synced}")
print(f"Final DB Approximate Count: {len(existing_emails)}")
print("="*50)
