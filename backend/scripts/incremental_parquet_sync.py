import duckdb
import psycopg
import pandas as pd
import os
import time
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env')))
DB_URL = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DATABASE_URL")
if DB_URL and "+psycopg" in DB_URL:
    DB_URL = DB_URL.replace("postgresql+psycopg://", "postgresql://")
PARQUET_PATH = "C:/TalentOpsAI/backend/data/recruiters_full.parquet"
TEMP_PARQUET_PATH = "C:/TalentOpsAI/backend/data/recruiters_full_temp.parquet"

def sync():
    logging.info("Starting incremental Parquet sync...")
    
    con = duckdb.connect()
    
    try:
        # 1. Get max updated_at from Parquet
        logging.info("Fetching max updated_at from Parquet...")
        res = con.execute(f"SELECT MAX(updated_at) FROM read_parquet('{PARQUET_PATH}')").fetchone()
        max_updated_at = res[0] if res and res[0] else None
        
        if not max_updated_at:
            logging.warning("Could not determine max updated_at from Parquet. Will not perform full sync to save egress.")
            return
            
        logging.info(f"Latest Parquet update timestamp: {max_updated_at}")
        
        # 2. Fetch updated records from PostgreSQL
        logging.info("Connecting to PostgreSQL...")
        pg_conn = psycopg.connect(DB_URL)
        
        parquet_columns = [
            'recruiter_id', 'recruiter_name', 'normalized_recruiter_name', 'email', 'phone', 'email2', 
            'phone2', 'email3', 'phone3', 'email4', 'phone4', 'alternate_emails', 'alternate_phones', 
            'linkedin', 'specialization', 'title', 'notes', 'review_reason', 'location', 'state', 
            'normalized_city', 'location_confidence', 'state_source', 'state_confidence', 'state_reason', 
            'last_scan_at', 'completeness_score', 'needs_review', 'is_active', 'data_source', 'trust_score', 
            'source_job_id', 'raw_data', 'metadata_json', 'tags', 'created_at', 'updated_at', 
            'taxonomy_category', 'report_count', 'email_status', 'email_confidence', 'email_source', 
            'email_pattern_id', 'email_generated', 'email_verified_at', 'email_last_checked_at', 
            'canonical_company_id', 'historical_company_id', 'company_domain_id', 'raw_email_value', 
            'repair_reason', 'user_id', 'quality_score', 'missing_fields', 'sentinel_status', 
            'last_verified_at', 'company_confidence', 'company_reasoning', 'is_archived', 'company_id'
        ]
        
        pg_columns = parquet_columns.copy()
        # Replace 'is_archived' with 'false AS is_archived' since it doesn't exist in Postgres
        pg_columns[pg_columns.index('is_archived')] = 'false AS is_archived'
        
        query = f"""
            SELECT {', '.join(pg_columns)} 
            FROM recruiters 
            WHERE updated_at > %s
        """
        
        logging.info("Executing fetch query...")
        cur = pg_conn.cursor()
        cur.execute(query, (max_updated_at,))
        rows = cur.fetchall()
        
        if not rows:
            logging.info("No new updates found in PostgreSQL. Sync complete.")
            pg_conn.close()
            return
            
        logging.info(f"Found {len(rows)} recently updated recruiters. Applying delta...")
        
        import json
        df_updates = pd.DataFrame(rows, columns=parquet_columns)
        for str_col in ['alternate_emails', 'alternate_phones', 'raw_data', 'repair_reason', 'metadata_json', 'notes', 'tags', 'missing_fields']:
            if str_col in df_updates.columns:
                df_updates[str_col] = df_updates[str_col].apply(
                    lambda x: json.dumps(x) if isinstance(x, (list, dict)) else (str(x) if x is not None and not pd.isna(x) and str(x).lower() != 'nan' else None)
                )
        for num_col in ['quality_score', 'trust_score', 'completeness_score', 'report_count']:
            if num_col in df_updates.columns:
                df_updates[num_col] = pd.to_numeric(df_updates[num_col], errors='coerce')
        pg_conn.close()
        
        # 3. Apply updates to Parquet file
        logging.info("Loading Parquet into local memory...")
        con.execute(f"""
            CREATE TABLE master AS SELECT * REPLACE (
                CAST(alternate_emails AS VARCHAR) AS alternate_emails, 
                CAST(alternate_phones AS VARCHAR) AS alternate_phones,
                CAST(raw_data AS VARCHAR) AS raw_data,
                CAST(repair_reason AS VARCHAR) AS repair_reason,
                CAST(quality_score AS DOUBLE) AS quality_score,
                CAST(trust_score AS DOUBLE) AS trust_score
            ) FROM read_parquet('{PARQUET_PATH}')
        """)
        
        logging.info("Deleting old rows...")
        con.execute("DELETE FROM master WHERE recruiter_id IN (SELECT recruiter_id FROM df_updates)")
        
        logging.info("Inserting updated rows...")
        cols_sql = ', '.join(parquet_columns)
        con.execute(f"INSERT INTO master ({cols_sql}) SELECT * FROM df_updates")
        
        logging.info("Writing updated dataset to new Parquet file...")
        con.execute(f"COPY master TO '{TEMP_PARQUET_PATH}' (FORMAT PARQUET)")
        
        logging.info("Replacing old Parquet file...")
        con.close()
        replaced = False
        for attempt in range(6):
            try:
                os.replace(TEMP_PARQUET_PATH, PARQUET_PATH)
                replaced = True
                break
            except (PermissionError, OSError) as pe:
                if attempt < 5:
                    time.sleep(0.6)
                else:
                    raise pe
        
        logging.info("Incremental Sync successfully completed!")
        
    except Exception as e:
        logging.error(f"Error during incremental sync: {e}")
    finally:
        try:
            con.close()
        except:
            pass

def run_sync_daemon():
    logging.info("Starting Incremental Parquet Sync Daemon...")
    while True:
        try:
            sync()
        except Exception as e:
            logging.error(f"Daemon crashed: {e}")
        logging.info("Sleeping for 1 hour...")
        time.sleep(3600)

if __name__ == '__main__':
    run_sync_daemon()
