import sys
import duckdb
import os
import time

sys.path.append('C:/TalentOpsAI/backend')
from dotenv import load_dotenv
load_dotenv('C:/TalentOpsAI/backend/.env')
from app.database import SessionLocal
from sqlalchemy import text
from app.utils.logo_domains import THIRD_PARTY_LOGO_DOMAINS

print("1. Fetching canonical companies from Postgres...")
db = SessionLocal()
# Get all active companies. If multiple have the same domain, pick the one with the highest trust_score / highest ID
companies = db.execute(text("""
    SELECT company_id, email_pattern, website, company_name
    FROM companies
    WHERE is_active = True
    ORDER BY COALESCE(trust_score, 0) DESC, company_id ASC
""")).fetchall()

# Build mapping: domain -> company_id
domain_to_company = {}

def extract_domain(val):
    if not val:
        return None
    val = val.lower().strip()
    if '://' in val:
        val = val.split('://')[-1]
    val = val.split('/')[0]
    val = val.replace('www.', '')
    if ';' in val:
        val = val.split(';')[0].strip()
    # Remove trailing dots
    val = val.rstrip('.')
    return val if '.' in val else None

for row in companies:
    cid, pattern, website, name = row
    
    d1 = extract_domain(pattern)
    if d1 and d1 not in THIRD_PARTY_LOGO_DOMAINS and d1 not in domain_to_company:
        domain_to_company[d1] = cid
        
    d2 = extract_domain(website)
    if d2 and d2 not in THIRD_PARTY_LOGO_DOMAINS and d2 not in domain_to_company:
        domain_to_company[d2] = cid

print(f"Loaded {len(domain_to_company)} valid domains mapping to canonical companies.")

print("2. Connecting to DuckDB Parquet...")
PARQUET_FILE = 'C:/TalentOpsAI/backend/data/recruiters_full.parquet'
conn = duckdb.connect()

# Read Parquet into a memory table
print("Reading parquet into memory table...")
conn.execute(f"CREATE TABLE recruiters AS SELECT * FROM read_parquet('{PARQUET_FILE}')")

# Get recruiters with missing companies
missing = conn.execute("SELECT recruiter_id, email FROM recruiters WHERE company_id IS NULL AND email IS NOT NULL").fetchall()
print(f"Found {len(missing)} recruiters with missing company_id and valid emails.")

updates = []
for rid, email in missing:
    if '@' not in email:
        continue
    domain = email.split('@')[-1].lower().strip()
    if domain in THIRD_PARTY_LOGO_DOMAINS:
        continue
        
    if domain in domain_to_company:
        updates.append((domain_to_company[domain], rid))

print(f"Found {len(updates)} recruiters that can be mapped to a canonical company!")

if not updates:
    print("No updates needed.")
else:
    print("3. Updating DuckDB table...")
    # Update in batches using a temp table
    conn.execute("CREATE TEMP TABLE update_batch(cid BIGINT, rid VARCHAR)")
    conn.executemany("INSERT INTO update_batch VALUES (?, ?)", updates)
    
    conn.execute("""
        UPDATE recruiters
        SET company_id = update_batch.cid
        FROM update_batch
        WHERE recruiters.recruiter_id = update_batch.rid
    """)
    print("Update complete.")
    
    print("4. Writing back to Parquet...")
    temp_parquet = PARQUET_FILE + '.tmp.parquet'
    conn.execute(f"COPY recruiters TO '{temp_parquet}' (FORMAT PARQUET)")
    
    # Swap
    if os.path.exists(PARQUET_FILE):
        os.remove(PARQUET_FILE)
    os.rename(temp_parquet, PARQUET_FILE)
    print("Successfully updated Parquet file!")

print("5. Uploading to Supabase via ParquetWriter...")
from app.services.parquet_writer import parquet_writer
parquet_writer._trigger_upload()
# Wait for upload to complete
time.sleep(20)
print("Upload triggered and slept for 20s to allow completion.")
