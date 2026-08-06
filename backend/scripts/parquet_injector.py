import argparse
import sys
import os
import json
import logging
import pandas as pd
from datetime import datetime, timezone

# Add the parent directory to sys.path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.parquet_writer import parquet_writer
from app.services.recruiter_store import _get_duckdb, PARQUET_FILE

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("injector")

def get_existing_emails():
    if not os.path.exists(PARQUET_FILE):
        return set()
    con = _get_duckdb().connect()
    try:
        res = con.execute(f"SELECT email FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}') WHERE email IS NOT NULL AND email != ''").fetchall()
        return set([row[0].lower().strip() for row in res])
    finally:
        con.close()

def parse_file(filepath: str) -> pd.DataFrame:
    ext = filepath.split('.')[-1].lower()
    if ext == 'csv':
        return pd.read_csv(filepath)
    elif ext in ['xls', 'xlsx']:
        return pd.read_excel(filepath)
    elif ext == 'json':
        return pd.read_json(filepath)
    elif ext == 'parquet':
        return pd.read_parquet(filepath)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")

def main():
    parser = argparse.ArgumentParser(description="Zero-Egress Data Injector directly into Parquet/Bucket")
    parser.add_argument("--source", required=True, help="Path to source data file (CSV, XLSX, JSON, Parquet)")
    parser.add_argument("--deduplicate", action="store_true", help="Deduplicate against existing emails in Parquet")
    parser.add_argument("--upload", action="store_true", help="Background upload to Supabase bucket after injection")
    
    args = parser.parse_args()
    
    logger.info(f"Loading data from {args.source}...")
    df = parse_file(args.source)
    logger.info(f"Loaded {len(df)} rows.")

    # Clean column names (lowercase, replace spaces)
    df.columns = [str(c).lower().strip().replace(' ', '_') for c in df.columns]
    
    # Map common column aliases to canonical schema
    column_mapping = {
        'name': 'recruiter_name',
        'first_name': 'recruiter_name', # naive, should be concat but keeping it simple
        'job_title': 'title',
        'state_code': 'state',
        'city': 'normalized_city',
        'company': 'company_id', # if company is a name, we might just drop it or put in notes
        'contact_email': 'email',
        'contact_phone': 'phone',
        'linkedin_url': 'linkedin',
    }
    df = df.rename(columns=column_mapping)
    
    if args.deduplicate and 'email' in df.columns:
        logger.info("Deduplicating against existing Parquet records...")
        existing_emails = get_existing_emails()
        
        # Clean emails
        df['email_clean'] = df['email'].astype(str).str.lower().str.strip()
        
        # Keep rows where email is not in existing
        df_new = df[~df['email_clean'].isin(existing_emails)]
        
        duplicates = len(df) - len(df_new)
        df = df_new.drop(columns=['email_clean'])
        logger.info(f"Skipped {duplicates} existing records based on email.")
    
    if len(df) == 0:
        logger.info("No new records to inject.")
        return
        
    # Prepare standard fields
    now = datetime.now(timezone.utc).isoformat()
    if 'created_at' not in df.columns:
        df['created_at'] = now
    if 'updated_at' not in df.columns:
        df['updated_at'] = now
    if 'is_active' not in df.columns:
        df['is_active'] = True
    if 'data_source' not in df.columns:
        df['data_source'] = 'cli_injector'
        
    records = df.to_dict(orient='records')
    
    logger.info(f"Injecting {len(records)} records into Parquet...")
    parquet_writer.append_records(records)
    
    logger.info("Injection complete! (Zero Postgres egress used)")

if __name__ == "__main__":
    main()
