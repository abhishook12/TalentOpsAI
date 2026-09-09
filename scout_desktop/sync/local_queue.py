"""
sync/local_queue.py — Offline-Resilient Local Observation & Priority Queue (Scout 2.0)

SQLite storage buffer for structured observations, delta packets, and candidate clusters.
Guarantees zero data loss during network interruptions, enforces DLP redaction before disk write,
supports HIGH/MEDIUM/LOW priority scheduling, and uses exponential backoff with jitter.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from scout_desktop.core.dlp_engine import DLPEngine

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
                    error_msg TEXT,
                    priority TEXT DEFAULT 'MEDIUM', -- HIGH | MEDIUM | LOW
                    operation TEXT DEFAULT 'INSERT', -- INSERT | UPDATE | DELTA
                    content_hash TEXT,
                    next_retry_at REAL,
                    dlq_reason TEXT
                )
            """)

            # Migrations for existing databases
            columns = [
                ("content_hash", "TEXT"),
                ("next_retry_at", "REAL"),
                ("priority", "TEXT DEFAULT 'MEDIUM'"),
                ("operation", "TEXT DEFAULT 'INSERT'"),
                ("dlq_reason", "TEXT"),
            ]
            for col_name, col_type in columns:
                try:
                    conn.execute(f"ALTER TABLE queued_observations ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError:
                    pass

            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON queued_observations(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_priority ON queued_observations(priority)")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_content_hash ON queued_observations(content_hash)")
            conn.commit()

    def enqueue_cluster(
        self,
        cluster_dict: Dict[str, Any],
        priority: str = "MEDIUM",
        operation: str = "INSERT",
    ) -> int:
        """
        Enqueues structured entity cluster or delta packet for synchronization.
        Enforces DLP redaction on edge before disk persistence.
        Returns queue record ID or -1 if duplicate.
        """
        # DLP Redaction: Strip secrets before persisting to disk
        safe_dict = DLPEngine.redact_dict(cluster_dict)

        canonical_name = safe_dict.get("canonical_name") or safe_dict.get("recruiter_name", "")
        company_name = safe_dict.get("company_name") or safe_dict.get("company", "")
        source_url = safe_dict.get("source_url") or safe_dict.get("linkedin_url", "")
        packet_id = safe_dict.get("packet_id", "")

        # Compute deterministic content hash
        hash_str = f"{packet_id}|{canonical_name}|{company_name}|{source_url}|{operation}"
        content_hash = hashlib.sha256(hash_str.encode("utf-8")).hexdigest()

        payload_str = json.dumps(safe_dict)
        now = time.time()
        norm_priority = priority.upper() if priority else "MEDIUM"
        if norm_priority not in ("HIGH", "MEDIUM", "LOW"):
            norm_priority = "MEDIUM"

        with self._get_conn() as conn:
            # Deduplication: check if identical record was queued recently
            cur = conn.execute("""
                SELECT 1 FROM queued_observations 
                WHERE content_hash = ? AND (status = 'PENDING' OR (status = 'SYNCED' AND synced_at >= ?))
            """, (content_hash, now - 86400))
            if cur.fetchone():
                logger.info("Duplicate observation detected, skipping insertion: %s", content_hash)
                return -1

            cur = conn.execute(
                """
                INSERT INTO queued_observations (
                    cluster_json, status, created_at, content_hash, priority, operation
                ) VALUES (?, 'PENDING', ?, ?, ?, ?)
                """,
                (payload_str, now, content_hash, norm_priority, operation),
            )
            conn.commit()
            return cur.lastrowid

    def enqueue_packet(
        self,
        packet_dict: Dict[str, Any],
        priority: str = "MEDIUM",
        operation: str = "INSERT",
    ) -> int:
        """Alias for intelligence packet enqueueing."""
        return self.enqueue_cluster(packet_dict, priority=priority, operation=operation)

    def get_pending_batch(self, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Fetches up to `limit` pending items for synchronization.
        Strictly orders by priority (HIGH -> MEDIUM -> LOW), respecting exponential backoff.
        """
        results = []
        now = time.time()
        with self._get_conn() as conn:
            cur = conn.execute(
                """
                SELECT id, cluster_json, retry_count, priority, operation 
                FROM queued_observations 
                WHERE status = 'PENDING' AND (next_retry_at IS NULL OR next_retry_at <= ?)
                ORDER BY 
                    CASE priority 
                        WHEN 'HIGH' THEN 1 
                        WHEN 'MEDIUM' THEN 2 
                        WHEN 'LOW' THEN 3 
                        ELSE 4 
                    END ASC, 
                    id ASC 
                LIMIT ?
                """,
                (now, limit),
            )
            for row in cur.fetchall():
                try:
                    data = json.loads(row[1])
                    data["_local_queue_id"] = row[0]
                    data["_retry_count"] = row[2]
                    data["_priority"] = row[3] or "MEDIUM"
                    data["_operation"] = row[4] or "INSERT"
                    results.append(data)
                except Exception as e:
                    logger.warning("Failed to deserialize queued observation %s: %s", row[0], e)
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
        """
        Increments retry count on failure and applies exponential backoff with jitter.
        After MAX_RETRIES, transitions records into Dead-Letter Queue (DLQ).
        """
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

                new_retry = retry_count + 1
                if new_retry >= MAX_RETRIES:
                    conn.execute(
                        "UPDATE queued_observations SET status = 'DLQ', retry_count = ?, error_msg = ?, dlq_reason = ? WHERE id = ?",
                        (new_retry, str(error_msg)[:200], f"Exceeded {MAX_RETRIES} retries", qid),
                    )
                else:
                    # Exponential backoff with random jitter: base * (2^retry) + jitter(0.1, 1.5)
                    jitter = random.uniform(0.1, 1.5)
                    backoff = min(MAX_BACKOFF_SEC, (BASE_BACKOFF_SEC * (2 ** retry_count)) + jitter)
                    next_retry_at = now + backoff
                    conn.execute(
                        "UPDATE queued_observations SET retry_count = ?, error_msg = ?, next_retry_at = ? WHERE id = ?",
                        (new_retry, str(error_msg)[:200], next_retry_at, qid),
                    )
            conn.commit()

    def get_dlq_items(self) -> List[Dict[str, Any]]:
        """Returns items in DLQ status for manual review or diagnostics."""
        results = []
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT id, cluster_json, retry_count, error_msg, dlq_reason FROM queued_observations WHERE status = 'DLQ' ORDER BY id ASC"
            )
            for row in cur.fetchall():
                try:
                    data = json.loads(row[1])
                    data["_local_queue_id"] = row[0]
                    data["_retry_count"] = row[2]
                    data["_error_msg"] = row[3]
                    data["_dlq_reason"] = row[4]
                    results.append(data)
                except Exception:
                    pass
        return results

    def retry_dlq_item(self, queue_id: int) -> bool:
        """Resets a DLQ item back to PENDING with retry_count=0."""
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE queued_observations SET status = 'PENDING', retry_count = 0, next_retry_at = NULL, dlq_reason = NULL WHERE id = ?",
                (queue_id,),
            )
            conn.commit()
            return cur.rowcount > 0

    def heal_stalled_items(self, max_stalled_sec: float = 300.0) -> int:
        """
        Self-healing watchdog: Recovers items that were in flight or stalled during unexpected
        shutdown or crash, resetting them back to PENDING.
        """
        now = time.time()
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE queued_observations SET status = 'PENDING' WHERE status = 'PROCESSING' AND created_at < ?",
                (now - max_stalled_sec,),
            )
            count = cur.rowcount
            conn.commit()
            if count > 0:
                logger.info("Self-healing watchdog: Recovered %d stalled queue observations", count)
            return count

    def get_queue_stats(self) -> Dict[str, int]:
        """Returns pending, priority breakdown, synced today, failed, and dlq counts."""
        now = time.time()
        today_start = now - (now % 86400)
        with self._get_conn() as conn:
            cur = conn.execute("SELECT status, count(*) FROM queued_observations GROUP BY status")
            counts = dict(cur.fetchall())

            cur_prio = conn.execute("SELECT priority, count(*) FROM queued_observations WHERE status = 'PENDING' GROUP BY priority")
            prio_counts = dict(cur_prio.fetchall())

            cur_today = conn.execute(
                "SELECT count(*) FROM queued_observations WHERE status = 'SYNCED' AND synced_at >= ?",
                (today_start,),
            )
            synced_today = cur_today.fetchone()[0] or 0

            return {
                "pending": counts.get("PENDING", 0),
                "high_priority_pending": prio_counts.get("HIGH", 0),
                "medium_priority_pending": prio_counts.get("MEDIUM", 0),
                "low_priority_pending": prio_counts.get("LOW", 0),
                "synced_today": synced_today,
                "failed": counts.get("FAILED", 0),
                "dlq": counts.get("DLQ", 0),
                "total": sum(counts.values()),
            }
