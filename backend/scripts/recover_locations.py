import os
import pandas as pd
import psycopg
import time
import io
import warnings
import json
from dotenv import load_dotenv

warnings.filterwarnings('ignore')
load_dotenv()
remote_url = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

print("Starting Source File Location Recovery...")

log_path = r'C:\Users\User\.gemini\antigravity\brain\e050007d-77bf-4880-ac17-0d8a6b8d4518\scratch\d_drive_scan.log'
files = []
if os.path.exists(log_path):
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            if '|' in line:
                parts = line.strip().split(' | ', 1)
                if len(parts) == 2:
                    files.append(parts[1])

print(f"Loaded {len(files)} paths from scan log to search for locations.")

# Mapping of email -> state
email_state_map = {}

start_time = time.time()
files_processed = 0

for idx, fp in enumerate(files, 1):
    if not os.path.exists(fp):
        continue
        
    try:
        if fp.lower().endswith('.csv'):
            df = pd.read_csv(fp, low_memory=False, on_bad_lines='skip', nrows=5)
        else:
            df = pd.read_excel(fp, nrows=5, engine='calamine')
            
        columns_lower = [str(c).lower().strip() for c in df.columns]
        
        # We need an email column and a state/location column
        email_col = next((c for i, c in enumerate(df.columns) if columns_lower[i] in ['email', 'email_address', 'contact_email', 'work_email', 'e-mail']), None)
        if not email_col:
            email_col = next((c for i, c in enumerate(df.columns) if 'email' in columns_lower[i]), None)
            
        if not email_col:
            continue
            
        state_col = next((c for i, c in enumerate(df.columns) if columns_lower[i] in ['state', 'company state', 'province', 'region']), None)
        if not state_col:
            state_col = next((c for i, c in enumerate(df.columns) if 'state' in columns_lower[i]), None)
            
        if not state_col:
            # Fallback to city or location
            state_col = next((c for i, c in enumerate(df.columns) if columns_lower[i] in ['location', 'city', 'company city']), None)
            
        if not state_col:
            continue
            
        # Read only these two columns to save memory
        if fp.lower().endswith('.csv'):
            df = pd.read_csv(fp, usecols=[email_col, state_col], low_memory=False, on_bad_lines='skip')
        else:
            df = pd.read_excel(fp, usecols=[email_col, state_col], engine='calamine')
            
        df = df.dropna(subset=[email_col, state_col])
        
        for _, row in df.iterrows():
            email = str(row[email_col]).strip().lower()
            state = str(row[state_col]).strip()[:100]
            if email and state and '@' in email and len(state) >= 2 and state.lower() != 'nan':
                if email not in email_state_map:
                    email_state_map[email] = state

        files_processed += 1
        
        if idx % 10 == 0:
            print(f"Scanned {idx}/{len(files)} files. Found {len(email_state_map)} location mappings.")
            
    except Exception as e:
        pass # Skip unreadable files

print(f"Finished scanning. Extracted {len(email_state_map)} total unique email locations.")

if len(email_state_map) == 0:
    print("No locations found.")
    exit(0)

# Create a temporary CSV to bulk load into a temp table for fast updating
csv_buffer = io.StringIO()
for email, state in email_state_map.items():
    csv_buffer.write(f"{email}\t{state}\n")
csv_buffer.seek(0)

print("Pushing location updates to database...")
with psycopg.connect(remote_url) as conn:
    with conn.cursor() as cur:
        # Create temp table
        cur.execute("CREATE TEMP TABLE temp_locations (email VARCHAR(150), state VARCHAR(100))")
        
        # Copy data
        with cur.copy("COPY temp_locations (email, state) FROM STDIN WITH (FORMAT CSV, DELIMITER '\t')") as copy:
            while data := csv_buffer.read(8192):
                copy.write(data)
                
        # Create index on temp table for fast join
        cur.execute("CREATE INDEX idx_temp_loc_email ON temp_locations(email)")
        
        # Execute bulk update
        cur.execute("""
            UPDATE recruiters r
            SET state = t.state,
                state_source = 'source_file',
                state_confidence = 'high'
            FROM temp_locations t
            WHERE lower(r.email) = t.email
              AND (r.state IS NULL OR r.state = '')
        """)
        updated_rows = cur.rowcount
        conn.commit()

print("="*50)
print(f"LOCATION RECOVERY COMPLETE in {int(time.time() - start_time)}s")
print(f"Files Processed for Locations: {files_processed}")
print(f"Successfully Updated Recruiters: {updated_rows}")
print("="*50)
