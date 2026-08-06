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

files = [
    r'C:\TalentOpsAI\backend\exports\production_seed_recruiters.csv',
    r'C:\TalentOpsAI\exports\archives\perpetual_shred_1782549077.csv',
    r'C:\TalentOpsAI\exports\archives\perpetual_shred_1782549112.csv',
    r'C:\TalentOpsAI\exports\archives\shredded_archive_1782530576.csv',
    r'C:\TalentOpsAI\exports\archives\shredded_archive_1782530628.csv',
    r'C:\TalentOpsAI\exports\archives\shredded_archive_1782530678.csv',
    r'C:\TalentOpsAI\exports\archives\shredded_archive_1782530744.csv',
    r'C:\TalentOpsAI\exports\archives\shredded_archive_1782530793.csv',
    r'C:\TalentOpsAI\exports\archives\shredded_archive_1782530814.csv',
    r'C:\TalentOpsAI\exports\archives\shredded_archive_1782530837.csv',
    r'C:\TalentOpsAI\exports\archives\shredded_archive_1782530860.csv',
    r'C:\TalentOpsAI\exports\archives\shredded_archive_1782530885.csv'
]

print("Fetching existing emails...")
with psycopg.connect(remote_url) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT email FROM recruiters")
        existing_emails = set(row[0].lower() for row in cur.fetchall() if row[0])

print(f"Loaded {len(existing_emails)} existing emails.")

total_synced = 0

for fp in files:
    if not os.path.exists(fp):
        print(f"Not found: {fp}")
        continue
        
    print(f"Processing {fp}...")
    try:
        df = pd.read_csv(fp, low_memory=False, on_bad_lines='skip')
        
        email_col = next((c for c in df.columns if str(c).lower().strip() in ['email', 'email_address', 'contact_email', 'work_email', 'e-mail']), None)
        if not email_col:
            email_col = next((c for c in df.columns if 'email' in str(c).lower()), None)
            
        if not email_col:
            continue
            
        name_col = next((c for c in df.columns if str(c).lower().strip() in ['name', 'full_name', 'recruiter_name', 'contact_name', 'first_name']), None)
        if not name_col:
            name_col = next((c for c in df.columns if 'name' in str(c).lower()), None)
            
        if not name_col:
            df['recruiter_name'] = 'Unknown Recruiter'
            name_col = 'recruiter_name'
            
        df = df[[name_col, email_col]].dropna(subset=[email_col])
        df = df.rename(columns={name_col: 'recruiter_name', email_col: 'email'})
        
        # Format and truncate exactly as DB does before dedupe to prevent duplicate constraint violations!
        df['email'] = df['email'].astype(str).str.strip().str[:150]
        df['email_lower'] = df['email'].str.lower()
        df = df[df['email_lower'].str.contains('@', na=False)]
        
        new_rec = df[~df['email_lower'].isin(existing_emails)].copy()
        new_rec = new_rec.drop_duplicates(subset=['email_lower'])
        new_rec = new_rec.drop(columns=['email_lower'])
        
        new_rec['recruiter_name'] = new_rec['recruiter_name'].fillna('Unknown Recruiter').astype(str).str[:150]
        
        if new_rec.empty:
            print(" -> All duplicates. Skipping.")
            continue
            
        print(f" -> Found {len(new_rec)} new records! Uploading...")
        
        csv_buffer = io.StringIO()
        new_rec.to_csv(csv_buffer, index=False, header=False, sep='\t')
        csv_buffer.seek(0)
        
        with psycopg.connect(remote_url) as conn:
            with conn.cursor() as cur:
                with cur.copy("COPY recruiters (recruiter_name, email) FROM STDIN WITH (FORMAT CSV, DELIMITER '\t')") as copy:
                    while data := csv_buffer.read(8192):
                        copy.write(data)
            conn.commit()
            
        existing_emails.update(new_rec['email'].str.lower())
        total_synced += len(new_rec)
        print(f" -> Success! Total synced: {total_synced}. DB approx: {len(existing_emails)}")
        
    except Exception as e:
        print(f"Error on {fp}: {e}")

print(f"\nDONE! Added {total_synced} brand new recruiters.")
