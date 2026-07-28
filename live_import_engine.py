import pandas as pd
import sqlalchemy
import os
import json
import gc
from datetime import datetime
import sys

# Connection string to LIVE SUPABASE DB
DATABASE_URL = "postgresql+psycopg://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"

print("Starting production data import engine...")

# 1. Connect to Live DB
engine = sqlalchemy.create_engine(DATABASE_URL)

# 2. Fetch all existing live emails to deduplicate (prevents breaking unique constraints)
print("Fetching existing live emails...")
with engine.connect() as conn:
    result = conn.execute(sqlalchemy.text("SELECT email FROM recruiters"))
    existing_emails = set(row[0].strip().lower() for row in result if row[0])

print(f"Found {len(existing_emails)} existing emails on the live site.")

# 3. Read the massive winning dataset
arjun_file = r'C:\Users\User\Downloads\arjun 2nd sheet .xlsx'
print(f"Reading {arjun_file}...")
df = pd.read_excel(arjun_file, engine='openpyxl')

print("Normalizing column names...")
df.columns = [str(c).strip() for c in df.columns]

# 4. Clean & Deduplicate the new dataset itself
initial_rows = len(df)
df = df.dropna(subset=['EMAIL'])
df['EMAIL'] = df['EMAIL'].astype(str).str.strip().str.lower()
df = df.drop_duplicates(subset=['EMAIL'])
print(f"Reduced from {initial_rows} raw rows to {len(df)} internally unique emails.")

# 5. Filter out emails that already exist on the live site
df_new = df[~df['EMAIL'].isin(existing_emails)].copy()
print(f"After checking against the live site, there are {len(df_new)} completely NEW unique records to insert.")

if len(df_new) == 0:
    print("No new records to insert. Exiting.")
    sys.exit(0)

# 6. Map to the Recruiter model columns
print("Mapping columns for bulk insertion...")
# We know the columns: 'Company name', 'PV Name', 'EMAIL', 'location'
df_insert = pd.DataFrame()
df_insert['recruiter_name'] = df_new.get('PV Name', df_new.get('pv name', 'Unknown'))
df_insert['recruiter_name'] = df_insert['recruiter_name'].fillna('Unknown')
df_insert['email'] = df_new['EMAIL']
df_insert['location'] = df_new.get('location', df_new.get('Location', None))
df_insert['data_source'] = 'arjun_massive_import'
df_insert['created_at'] = datetime.utcnow()
df_insert['updated_at'] = datetime.utcnow()
df_insert['is_active'] = True
df_insert['trust_score'] = 100
df_insert['needs_review'] = False

# We'll put Company Name in notes or raw_data for now to avoid complex relational inserts for 200k rows
def row_to_json(row):
    return json.dumps({'original_company': str(row.get('Company name', '')), 'import_source': 'arjun'})

df_insert['raw_data'] = df_new.apply(row_to_json, axis=1)

del df
del df_new
gc.collect()

# 7. Bulk Insert into PostgreSQL using fast chunking
print("Starting bulk insert into live PostgreSQL database...")
df_insert.to_sql(
    'recruiters', 
    con=engine, 
    if_exists='append', 
    index=False, 
    method='multi', 
    chunksize=5000
)

print(f"SUCCESS: {len(df_insert)} records successfully pushed to the live production database!")
