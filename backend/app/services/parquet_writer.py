import os
import time
import logging
import threading
import shutil
import urllib.request
import urllib.error
import duckdb
import pandas as pd
from typing import List, Dict, Any

from app.services.recruiter_store import PARQUET_FILE, recruiter_store

logger = logging.getLogger("parquet_writer")

SUPABASE_URL = "https://dcqvsvgrdsrgnbwwssup.supabase.co"
# Supabase storage API for uploads usually requires authentication.
# The previous script `upload_real_parquet.py` used the supabase-py client with a key.
# We will use the same approach or simple HTTP with headers.
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

class ParquetWriter:
    """
    Handles all direct writes to the Parquet file, bypassing PostgreSQL.
    Merges new or updated records into the DuckDB Parquet and syncs to Supabase.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._upload_thread = None

    def _get_max_id(self, con) -> int:
        """Get the current maximum recruiter_id."""
        if not os.path.exists(PARQUET_FILE):
            return 0
        try:
            res = con.execute(f"SELECT MAX(recruiter_id) FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}')").fetchone()
            return int(res[0]) if res and res[0] is not None else 0
        except Exception as e:
            logger.error(f"Error getting max id: {e}")
            return 0

    def _get_parquet_schema(self, con) -> Dict[str, str]:
        """Get the schema of the existing Parquet file as dict {col: type}."""
        if not os.path.exists(PARQUET_FILE):
            return {}
        res = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}') LIMIT 1").fetchall()
        return {row[0]: row[1] for row in res}

    def _align_schema(self, df: pd.DataFrame, schema: Dict[str, str]) -> pd.DataFrame:
        """Ensure the DataFrame has exactly the columns required by the Parquet schema."""
        if not schema:
            return df
        schema_cols = list(schema.keys())
        for col in schema_cols:
            if col not in df.columns:
                df[col] = None
        # Drop extra columns not in schema
        for col in df.columns:
            if col not in schema_cols:
                df = df.drop(columns=[col])
        return df[schema_cols] # Reorder to match

    def append_records(self, records: List[Dict[str, Any]]) -> int:
        """
        Append new records directly to the Parquet file.
        Returns the number of records appended.
        """
        if not records:
            return 0

        with self._lock:
            start_time = time.time()
            con = duckdb.connect()
            
            schema_cols = self._get_parquet_schema(con)
            
            # Assign auto-incrementing recruiter_ids
            max_id = self._get_max_id(con)
            for i, record in enumerate(records):
                if 'recruiter_id' not in record or not record['recruiter_id']:
                    max_id += 1
                    record['recruiter_id'] = max_id
                    
            df_new = pd.DataFrame(records)
            
            # If the file exists, align schema. Otherwise, the first write establishes the schema.
            if os.path.exists(PARQUET_FILE) and schema_cols:
                df_new = self._align_schema(df_new, schema_cols)
                
            tmp_file = f"{PARQUET_FILE}.{os.getpid()}.append.tmp"
            con.register('df_new', df_new)
            
            try:
                if not os.path.exists(PARQUET_FILE):
                    con.execute(f"COPY df_new TO '{tmp_file.replace(os.sep, '/')}' (FORMAT PARQUET, COMPRESSION 'ZSTD')")
                else:
                    con.execute(f"""
                        COPY (
                            SELECT * FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}')
                            UNION ALL
                            SELECT * FROM df_new
                        ) TO '{tmp_file.replace(os.sep, '/')}' (FORMAT PARQUET, COMPRESSION 'ZSTD')
                    """)
                    
                # Atomic swap
                shutil.move(tmp_file, PARQUET_FILE)
                logger.info(f"Appended {len(records)} records to Parquet in {time.time() - start_time:.2f}s")
                
                # Reload the read replica
                recruiter_store.reload()
                
                # Trigger background upload
                self._trigger_upload()
                
                return len(records)
            except Exception as e:
                logger.error(f"Failed to append to Parquet: {e}")
                if os.path.exists(tmp_file):
                    os.remove(tmp_file)
                raise
            finally:
                con.close()

    def update_records(self, updates: List[Dict[str, Any]]) -> int:
        """
        Update existing records in the Parquet file.
        Updates must contain 'recruiter_id'.
        """
        if not updates:
            return 0

        valid_updates = [u for u in updates if u.get('recruiter_id') is not None]
        if not valid_updates:
            return 0

        with self._lock:
            if not os.path.exists(PARQUET_FILE):
                return 0

            start_time = time.time()
            con = duckdb.connect()
            
            schema = self._get_parquet_schema(con)
            schema_cols = list(schema.keys())
            
            df_updates = pd.DataFrame(valid_updates)
            # Ensure df_updates only contains columns that exist in the schema, but don't force all columns
            update_cols = [c for c in df_updates.columns if c in schema_cols]
            df_updates = df_updates[update_cols]
            
            con.register('df_updates', df_updates)
            tmp_file = f"{PARQUET_FILE}.{os.getpid()}.update.tmp"
            
            try:
                # We do a LEFT JOIN to update the rows.
                # In DuckDB, we can use an exclude and replace strategy or COALESCE.
                # Since updates might only have a few columns, COALESCE is safest.
                select_exprs = []
                for col in schema_cols:
                    if col == 'recruiter_id':
                        select_exprs.append("base.recruiter_id")
                    elif col in update_cols:
                        # We should use CASE WHEN upd.recruiter_id IS NOT NULL THEN CAST(upd.col AS type) ELSE base.col
                        col_type = schema[col]
                        select_exprs.append(f"CASE WHEN upd.recruiter_id IS NOT NULL THEN CAST(upd.{col} AS {col_type}) ELSE base.{col} END AS {col}")
                    else:
                        select_exprs.append(f"base.{col}")
                        
                select_clause = ",\n".join(select_exprs)
                
                query = f"""
                    COPY (
                        SELECT {select_clause}
                        FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}') base
                        LEFT JOIN df_updates upd ON base.recruiter_id = upd.recruiter_id
                    ) TO '{tmp_file.replace(os.sep, '/')}' (FORMAT PARQUET, COMPRESSION 'ZSTD')
                """
                
                logger.info(f"Update query: {query}")
                con.execute(query)
                
                # Atomic swap
                shutil.move(tmp_file, PARQUET_FILE)
                logger.info(f"Updated {len(valid_updates)} records in Parquet in {time.time() - start_time:.2f}s")
                
                # Reload the read replica
                recruiter_store.reload()
                
                # Trigger background upload
                self._trigger_upload()
                
                return len(valid_updates)
            except Exception as e:
                logger.error(f"Failed to update Parquet: {e}")
                if os.path.exists(tmp_file):
                    os.remove(tmp_file)
                raise
            finally:
                con.close()

    def _trigger_upload(self):
        if self._upload_thread is None or not self._upload_thread.is_alive():
            self._upload_thread = threading.Thread(target=self._upload_to_supabase, daemon=True)
            self._upload_thread.start()

    def _upload_to_supabase(self):
        """Uploads the local Parquet file to Supabase in the background."""
        if not SUPABASE_KEY:
            logger.warning("SUPABASE_KEY not set. Cannot upload to Supabase.")
            return

        bucket_name = "data-assets"
        file_path = "recruiters_full.parquet"
        url = f"{SUPABASE_URL}/storage/v1/object/{bucket_name}/{file_path}"

        logger.info(f"Uploading {PARQUET_FILE} to Supabase bucket '{bucket_name}'...")
        try:
            with open(PARQUET_FILE, 'rb') as f:
                data = f.read()

            req = urllib.request.Request(url, data=data, method='PUT')
            req.add_header('Authorization', f'Bearer {SUPABASE_KEY}')
            req.add_header('Content-Type', 'application/vnd.apache.parquet')

            with urllib.request.urlopen(req, timeout=120) as response:
                if response.status in (200, 201):
                    logger.info("Successfully uploaded Parquet to Supabase.")
                else:
                    logger.error(f"Failed to upload Parquet to Supabase: {response.status} {response.read()}")
        except Exception as e:
            logger.error(f"Error uploading Parquet to Supabase: {e}")

parquet_writer = ParquetWriter()
