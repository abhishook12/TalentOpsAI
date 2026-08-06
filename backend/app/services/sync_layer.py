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
        logger.info("Sync requested: Reloading RecruiterStore and uploading to Supabase...")
        start = time.time()
        
        # 1. Reload read-replica directly from Parquet
        recruiter_store.reload()
        
        # 2. Trigger background upload to Supabase bucket
        try:
            from app.services.parquet_writer import parquet_writer
            parquet_writer._trigger_upload()
        except ImportError:
            pass
            
        elapsed = time.time() - start
        logger.info(f"Sync complete in {elapsed:.2f}s.")

sync_manager = SyncManager()
