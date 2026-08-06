import json
import pandas as pd
import psycopg
import time
import io
import os
from dotenv import load_dotenv

load_dotenv()
remote_url = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

# Read candidates
sync_list_path = r'C:\Users\User\.gemini\antigravity\brain\e050007d-77bf-4880-ac17-0d8a6b8d4518\scratch\sync_candidates_all.json'
with open(sync_list_path, 'r') as f:
    files = json.load(f)

print(f"Loaded {len(files)} files to sync.")

print("Connecting to Supabase to fetch existing emails (this may take a moment)...")
with psycopg.connect(remote_url) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT email FROM recruiters")
        existing_emails = set(row[0].lower() for row in cur.fetchall() if row[0])

print(f"Found {len(existing_emails)} existing recruiters in Supabase.")

total_synced = 0
MAX_TARGET = 1000000

for file_info in files:
    filepath = file_info['file']
    ftype = file_info.get('type')
    
    if not os.path.exists(filepath):
        continue
        
    print(f"Processing {filepath}...")
    
    try:
        if ftype == 'csv':
            df = pd.read_csv(filepath, low_memory=False, on_bad_lines='skip')
        elif ftype == 'json':
            df = pd.read_json(filepath)
        else:
            continue
            
        # Try to find email col
        email_col = next((c for c in df.columns if c.lower() in ['email', 'email_address', 'contact_email', 'work_email']), None)
        name_col = next((c for c in df.columns if c.lower() in ['name', 'full_name', 'recruiter_name', 'contact_name']), None)
        
        if not email_col:
            continue
            
        if not name_col:
            df['recruiter_name'] = 'Unknown Recruiter'
            name_col = 'recruiter_name'
            
        df = df[[name_col, email_col]].dropna(subset=[email_col])
        df = df.rename(columns={name_col: 'recruiter_name', email_col: 'email'})
        
        # Clean and dedupe
        df['email_lower'] = df['email'].astype(str).str.lower().str.strip()
        df = df[df['email_lower'].str.contains('@', na=False)]
        
        new_recruiters = df[~df['email_lower'].isin(existing_emails)].copy()
        new_recruiters = new_recruiters.drop_duplicates(subset=['email_lower'])
        new_recruiters = new_recruiters.drop(columns=['email_lower'])
        
        new_recruiters['recruiter_name'] = new_recruiters['recruiter_name'].fillna('Unknown Recruiter').astype(str).str[:150]
        new_recruiters['email'] = new_recruiters['email'].fillna('no-email@missing.local').astype(str).str[:150]
        
        if new_recruiters.empty:
            continue
            
        print(f"  Found {len(new_recruiters)} new records. Uploading...")
        
        csv_buffer = io.StringIO()
        new_recruiters.to_csv(csv_buffer, index=False, header=False, sep='\t')
        csv_buffer.seek(0)
        
        with psycopg.connect(remote_url) as conn:
            with conn.cursor() as cur:
                with cur.copy("COPY recruiters (recruiter_name, email) FROM STDIN WITH (FORMAT CSV, DELIMITER '\t')") as copy:
                    while data := csv_buffer.read(8192):
                        copy.write(data)
            conn.commit()
            
        # Update existing emails set
        existing_emails.update(new_recruiters['email'].str.lower())
        total_synced += len(new_recruiters)
        print(f"  Success. Total synced this run: {total_synced}. DB Total approx: {len(existing_emails)}")
        
        if len(existing_emails) >= MAX_TARGET:
            print("Reached target of 1 million recruiters! Stopping.")
            break
            
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

print("Done mass sync.")
