import os
import time
import logging
import threading
import shutil
import glob
import pandas as pd
from app.database import engine
from app.services.recruiter_store import _get_duckdb, PARQUET_FILE, recruiter_store

logger = logging.getLogger("sync_layer")

class SyncManager:
    def __init__(self):
        self._sync_requested = False
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        self._debounce_seconds = 5

    def request_sync(self):
        with self._lock:
            self._sync_requested = True

    def start(self):
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._sync_loop, daemon=True)
            self._thread.start()
            logger.info("SyncManager background thread started.")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
            logger.info("SyncManager background thread stopped.")

    def _sync_loop(self):
        while not self._stop_event.is_set():
            needs_sync = False
            with self._lock:
                if self._sync_requested:
                    needs_sync = True
                    self._sync_requested = False

            if needs_sync:
                # Wait for debounce
                time.sleep(self._debounce_seconds)
                # Check if more requests came in during debounce, and clear them
                with self._lock:
                    self._sync_requested = False

                try:
                    self._perform_sync()
                except Exception as e:
                    logger.error(f"Sync failed: {e}")

            # Sleep briefly before checking again
            time.sleep(1)

    def _perform_sync(self):
        logger.info("Starting Postgres -> Parquet sync...")
        start = time.time()
        
        # 1. Fetch live records from Postgres
        df_live = pd.read_sql("SELECT * FROM recruiters", engine)
        logger.info(f"Fetched {len(df_live):,} live records from Postgres.")
        
        duckdb = _get_duckdb()
        tmp_file = f"{PARQUET_FILE}.{os.getpid()}.tmp"
        
        # 2. Merge with Parquet and write to temp file
        con = duckdb.connect()
        con.register('df_live', df_live)
        
        if not os.path.exists(PARQUET_FILE):
            df_live['is_archived'] = False
            con.register('df_live', df_live)
            con.execute(f"COPY df_live TO '{tmp_file.replace(os.sep, '/')}' (FORMAT PARQUET, COMPRESSION 'ZSTD')")
        else:
            columns_query = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}') LIMIT 1").fetchall()
            parquet_columns = [row[0] for row in columns_query]
            
            df_live['is_archived'] = False
            con.register('df_live', df_live)
            
            if 'is_archived' not in parquet_columns:
                con.execute(f"""
                    COPY (
                        SELECT * FROM df_live
                        UNION ALL
                        SELECT *, true AS is_archived FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}')
                        WHERE recruiter_id NOT IN (SELECT recruiter_id FROM df_live)
                    ) TO '{tmp_file.replace(os.sep, '/')}' (FORMAT PARQUET, COMPRESSION 'ZSTD')
                """)
            else:
                staging_files = glob.glob(os.path.join(os.path.dirname(PARQUET_FILE), "staging_import_*.parquet"))
                staging_sql = ""
                for sf in staging_files:
                    sf_path = sf.replace(os.sep, '/')
                    staging_sql += f"\n                        UNION ALL\n                        SELECT * FROM read_parquet('{sf_path}')"
                
                con.execute(f"""
                    COPY (
                        SELECT * FROM df_live
                        UNION ALL
                        SELECT * FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}')
                        WHERE is_archived = true{staging_sql}
                    ) TO '{tmp_file.replace(os.sep, '/')}' (FORMAT PARQUET, COMPRESSION 'ZSTD')
                """)
                
                # We can safely delete the staging files now that they have been consumed
                for sf in staging_files:
                    try:
                        os.remove(sf)
                    except Exception as e:
                        logger.warning(f"Could not remove staging file {sf}: {e}")
        
        con.close()
        
        # 3. Atomic swap
        if os.path.exists(tmp_file):
            shutil.move(tmp_file, PARQUET_FILE)
            
        elapsed = time.time() - start
        logger.info(f"Sync complete in {elapsed:.2f}s. Reloading RecruiterStore...")
        
        # 4. Reload read-replica
        recruiter_store.reload()

sync_manager = SyncManager()
