"""
sync/local_queue.py — Offline-Resilient Local Observation Queue

SQLite storage buffer for structured observations and candidate clusters.
Guarantees zero data loss during network interruptions.
"""

import os
import json
import sqlite3
import time
import logging
import hashlib
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

logger = logging.getLogger("scout.local_queue")

MAX_RETRIES = 5
BASE_BACKOFF_SEC = 10
MAX_BACKOFF_SEC = 300

class LocalQueue:
    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "local_queue.db")
        self.db_path = db_path if db_path == ":memory:" else os.path.abspath(db_path)
        self._mem_conn = sqlite3.connect(":memory:") if self.db_path == ":memory:" else None
        self._init_db()

    @contextmanager
    def _get_conn(self):
        if self._mem_conn:
            yield self._mem_conn
        else:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()

    def close(self):
        """Closes any persistent memory connection."""
        if self._mem_conn:
            try:
                self._mem_conn.close()
            except Exception:
                pass
            self._mem_conn = None

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS queued_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cluster_json TEXT NOT NULL,
                    status TEXT DEFAULT 'PENDING',  -- PENDING | SYNCED | FAILED | DLQ
                    created_at REAL NOT NULL,
                    synced_at REAL,
                    retry_count INTEGER DEFAULT 0,
                    error_msg TEXT
                )
            """)
            
            # Migration
            try:
                conn.execute("ALTER TABLE queued_observations ADD COLUMN content_hash TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE queued_observations ADD COLUMN next_retry_at REAL")
            except sqlite3.OperationalError:
                pass

            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON queued_observations(status)")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_content_hash ON queued_observations(content_hash)")
            conn.commit()

    def enqueue_cluster(self, cluster_dict: Dict[str, Any]) -> int:
        """Enqueues structured entity cluster for upload."""
        canonical_name = cluster_dict.get("canonical_name") or cluster_dict.get("recruiter_name", "")
        company_name = cluster_dict.get("company_name", "")
        source_url = cluster_dict.get("source_url") or cluster_dict.get("linkedin_url", "")
        hash_str = f"{canonical_name}|{company_name}|{source_url}"
        content_hash = hashlib.sha256(hash_str.encode("utf-8")).hexdigest()
        
        payload_str = json.dumps(cluster_dict)
        now = time.time()
        
        with self._get_conn() as conn:
            # Deduplication
            cur = conn.execute("""
                SELECT 1 FROM queued_observations 
                WHERE content_hash = ? AND (status = 'PENDING' OR (status = 'SYNCED' AND synced_at >= ?))
            """, (content_hash, now - 86400))
            if cur.fetchone():
                logger.info(f"Duplicate observation detected, skipping insertion: {content_hash}")
                return -1

            cur = conn.execute(
                "INSERT INTO queued_observations (cluster_json, status, created_at, content_hash) VALUES (?, 'PENDING', ?, ?)",
                (payload_str, now, content_hash),
            )
            conn.commit()
            return cur.lastrowid

    def get_pending_batch(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Fetches up to `limit` pending clusters for synchronization."""
        results = []
        now = time.time()
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT id, cluster_json, retry_count FROM queued_observations WHERE status = 'PENDING' AND (next_retry_at IS NULL OR next_retry_at <= ?) ORDER BY id ASC LIMIT ?",
                (now, limit),
            )
            for row in cur.fetchall():
                try:
                    data = json.loads(row[1])
                    data["_local_queue_id"] = row[0]
                    data["_retry_count"] = row[2]
                    results.append(data)
                except Exception:
                    pass
        return results

    def mark_batch_synced(self, queue_ids: List[int]):
        """Marks queue items as successfully committed."""
        if not queue_ids:
            return
        now = time.time()
        with self._get_conn() as conn:
            conn.executemany(
                "UPDATE queued_observations SET status = 'SYNCED', synced_at = ? WHERE id = ?",
                [(now, qid) for qid in queue_ids],
            )
            conn.commit()

    def mark_batch_failed(self, queue_ids: List[int], error_msg: str):
        """Increments retry count on failure and applies exponential backoff."""
        if not queue_ids:
            return
        now = time.time()
        with self._get_conn() as conn:
            for qid in queue_ids:
                cur = conn.execute("SELECT retry_count FROM queued_observations WHERE id = ?", (qid,))
                row = cur.fetchone()
                if not row:
                    continue
                retry_count = row[0]
                
                if retry_count >= MAX_RETRIES:
                    conn.execute(
                        "UPDATE queued_observations SET status = 'DLQ', error_msg = ? WHERE id = ?",
                        (str(error_msg)[:200], qid)
                    )
                else:
                    backoff = min(MAX_BACKOFF_SEC, BASE_BACKOFF_SEC * (2 ** retry_count))
                    next_retry_at = now + backoff
                    conn.execute(
                        "UPDATE queued_observations SET retry_count = retry_count + 1, error_msg = ?, next_retry_at = ? WHERE id = ?",
                        (str(error_msg)[:200], next_retry_at, qid)
                    )
            conn.commit()

    def get_dlq_items(self) -> List[Dict[str, Any]]:
        """Returns items in DLQ status for manual review."""
        results = []
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT id, cluster_json, retry_count, error_msg FROM queued_observations WHERE status = 'DLQ' ORDER BY id ASC"
            )
            for row in cur.fetchall():
                try:
                    data = json.loads(row[1])
                    data["_local_queue_id"] = row[0]
                    data["_retry_count"] = row[2]
                    data["_error_msg"] = row[3]
                    results.append(data)
                except Exception:
                    pass
        return results

    def retry_dlq_item(self, queue_id: int):
        """Resets a DLQ item back to PENDING with retry_count=0."""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE queued_observations SET status = 'PENDING', retry_count = 0, next_retry_at = NULL WHERE id = ?",
                (queue_id,)
            )
            conn.commit()

    def get_queue_stats(self) -> Dict[str, int]:
        """Returns pending, synced today, and failed counts."""
        now = time.time()
        today_start = now - (now % 86400)
        with self._get_conn() as conn:
            cur = conn.execute("SELECT status, count(*) FROM queued_observations GROUP BY status")
            counts = dict(cur.fetchall())

            cur_today = conn.execute(
                "SELECT count(*) FROM queued_observations WHERE status = 'SYNCED' AND synced_at >= ?",
                (today_start,),
            )
            synced_today = cur_today.fetchone()[0] or 0

            return {
                "pending": counts.get("PENDING", 0),
                "synced_today": synced_today,
                "failed": counts.get("FAILED", 0),
                "dlq": counts.get("DLQ", 0),
                "total": sum(counts.values()),
            }
