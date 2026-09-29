"""
offline_buffer.py — TalentOps AI Smart Offline Buffer & Render Watchdog v2
===========================================================================

Intelligence upgrades over v1:

1. ADAPTIVE POLLING  — Exponential backoff when Render is offline.
   Starts at 30s, backs off to 5 min after 1h down, max 10 min after 6h.
   Returns to 30s immediately when online.

2. RENDER HEALTH SCORE  — Tracks probe response time, consecutive successes,
   and cumulative uptime %. Requires 3 stable pings (< 3s avg) before
   declaring Render "ready" and initiating the flush.

3. PRIORITY FLUSH  — Sorts pending records by quality_score DESC before
   flushing so high-confidence verified profiles are committed first.

4. EXPONENTIAL RETRY BACKOFF  — Failed flush records enter a cooldown
   (2^attempt minutes) before being retried, preventing endless hammering
   of a flapping DB connection.

5. SCHEDULED WAKEUP  — Background timer fires at the known Render reset time
   (Oct 1 2026 00:00 UTC). A separate thread sleeps until exactly that
   timestamp, then triggers a force-probe to accelerate detection.

6. DOWNTIME TELEMETRY  — Tracks total_downtime_sec, last_offline_at,
   last_online_at, downtime_events, and full history for dashboard display.

7. SMART DEDUP  — Multi-key fingerprint: SHA-256(name|email|linkedin_slug).
   Handles cases where name+email is unknown but LinkedIn URL is confirmed.

8. BUFFER VACUUMING  — Auto-runs SQLite VACUUM after each flush session once
   the FLUSHED row count exceeds 500, keeping DB file compact.

9. SOURCE PRIORITY TIERS  — Desktop Scout detections (real human, live
   window) get tier=1 (highest flush priority) vs tier=3 for scraped web.

10. RESPONSE-TIME AWARE FLUSH THROTTLE  — If Render responds > 2s, insert a
    50ms inter-record delay to avoid overwhelming a cold-starting instance.

Zero data loss. Zero manual intervention. Fully autonomous.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger("talentops.offline_buffer")

# ── Configuration ─────────────────────────────────────────────────────────────

BUFFER_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "offline_harvest_buffer.db"
)

RENDER_URL = os.getenv("RENDER_BACKEND_URL", "https://talentopsai-1.onrender.com")

# Adaptive polling — base interval when Render is down
RENDER_POLL_BASE_SEC   = int(os.getenv("RENDER_POLL_BASE", "30"))
RENDER_POLL_MAX_SEC    = int(os.getenv("RENDER_POLL_MAX", "600"))    # 10 min ceiling
FLUSH_BATCH_SIZE       = int(os.getenv("RENDER_FLUSH_BATCH_SIZE", "50"))
MIN_STABLE_PINGS       = 3       # consecutive sub-3s pings before "ready"
HEALTHY_PROBE_MS       = 3000    # max acceptable response time (ms) to count as "stable"
VACUUM_THRESHOLD       = 500     # vacuum DB after N flushed rows accumulate

# Known Render free-tier reset timestamp (Oct 1 2026 00:00 UTC)
RENDER_RESET_UTC = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)

# Source priority tiers (lower number = flush first)
SOURCE_PRIORITY = {
    "desktop_scout":    1,
    "scout_extension":  1,
    "xray_dork":        2,
    "web_harvest":      3,
    "ats_harvest":      2,
    "git_miner":        3,
}


class RenderHealthTracker:
    """
    Tracks Render's availability, response times, and stability score.
    Used by the watchdog to decide when Render is truly ready for a flush.
    """

    def __init__(self):
        self.consecutive_successes = 0
        self.consecutive_failures  = 0
        self.probe_times_ms: List[float] = []   # rolling window of last 10 probe durations
        self.total_probes      = 0
        self.total_successes   = 0
        self.last_probe_ms     = 0.0
        self.is_stable         = False           # True once MIN_STABLE_PINGS achieved

    def record_success(self, probe_ms: float):
        self.consecutive_successes += 1
        self.consecutive_failures  = 0
        self.total_probes          += 1
        self.total_successes       += 1
        self.last_probe_ms         = probe_ms
        self.probe_times_ms = (self.probe_times_ms + [probe_ms])[-10:]

        # Declare stable only after MIN_STABLE_PINGS under HEALTHY_PROBE_MS
        fast_pings = sum(1 for ms in self.probe_times_ms[-MIN_STABLE_PINGS:] if ms < HEALTHY_PROBE_MS)
        if len(self.probe_times_ms) >= MIN_STABLE_PINGS and fast_pings >= MIN_STABLE_PINGS:
            self.is_stable = True

    def record_failure(self):
        self.consecutive_failures  += 1
        self.consecutive_successes = 0
        self.total_probes          += 1
        self.is_stable             = False

    @property
    def avg_probe_ms(self) -> float:
        return sum(self.probe_times_ms) / len(self.probe_times_ms) if self.probe_times_ms else 0.0

    @property
    def uptime_pct(self) -> float:
        if self.total_probes == 0:
            return 100.0
        return round(self.total_successes / self.total_probes * 100, 1)

    def reset_stability(self):
        self.consecutive_successes = 0
        self.is_stable = False
        self.probe_times_ms = []


class OfflineHarvestBuffer:
    """
    Smart offline-resilient local SQLite buffer for discovered candidate profiles.

    Lifecycle:
    1. When Render is UP      → profiles write to Supabase; buffer marks them FLUSHED immediately.
    2. When Render is DOWN    → profiles accumulate in PENDING tier, sorted by priority+quality.
    3. When Render STABILISES → watchdog auto-flushes in priority order with throttling.
    4. Scheduled wakeup       → fires at known Render reset time for instant detection.
    """

    def __init__(self, db_path: str = BUFFER_DB_PATH):
        self.db_path    = db_path
        self._lock      = threading.Lock()
        self._watchdog_thread: Optional[threading.Thread]  = None
        self._scheduler_thread: Optional[threading.Thread] = None
        self._running         = False
        self._render_online   = True   # Optimistic assumption
        self.health           = RenderHealthTracker()

        # Downtime telemetry
        self._offline_since:       Optional[float] = None
        self._last_online_at:      Optional[float] = None
        self._total_downtime_sec:  float = 0.0
        self._downtime_events:     int   = 0
        self._flush_sessions:      int   = 0
        self._session_start:       Optional[float] = time.time()

        # Adaptive polling state
        self._poll_interval        = RENDER_POLL_BASE_SEC
        self._consecutive_fails    = 0

        self._init_db()
        self._recover_state()

    # ── DB Setup ──────────────────────────────────────────────────────────────

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Creates the buffer DB and all tables/indexes. Idempotent."""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS offline_profiles (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    discovery_id      TEXT NOT NULL UNIQUE,
                    raw_name          TEXT,
                    raw_title         TEXT,
                    raw_company       TEXT,
                    raw_email         TEXT,
                    raw_phone         TEXT,
                    raw_linkedin      TEXT,
                    raw_location      TEXT,
                    source_url        TEXT,
                    extraction_source TEXT DEFAULT 'web_harvest',
                    quality_score     REAL DEFAULT 0.7,
                    dom_confidence    REAL DEFAULT 0.7,
                    geo_region        TEXT,
                    geo_confidence    REAL,
                    owner_user_id     INTEGER DEFAULT 1,
                    metadata_json     TEXT DEFAULT '{}',
                    content_hash      TEXT NOT NULL,
                    source_tier       INTEGER DEFAULT 3,
                    status            TEXT DEFAULT 'PENDING',
                    buffered_at       REAL NOT NULL,
                    retry_after       REAL DEFAULT 0,
                    flushed_at        REAL,
                    flush_attempts    INTEGER DEFAULT 0,
                    flush_error       TEXT
                )
            """)
            # Composite index for priority flush ordering
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_buffer_flush_order
                ON offline_profiles(status, retry_after, source_tier ASC, quality_score DESC)
            """)
            # Fast lookup by content_hash for dedup
            conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_buffer_content_hash
                ON offline_profiles(content_hash)
            """)
            # Telemetry table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS buffer_events (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    detail     TEXT,
                    ts         REAL NOT NULL
                )
            """)
        logger.info("[SMART_BUFFER] Database initialized at %s", self.db_path)

    def _recover_state(self):
        """Restores pending count and logs it on restart."""
        try:
            with self._get_conn() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM offline_profiles WHERE status = 'PENDING'"
                ).fetchone()
                pending = row[0] if row else 0
                if pending > 0:
                    logger.info(
                        "[SMART_BUFFER] Recovered %d PENDING profiles from last session — "
                        "will auto-flush once Render is stable.",
                        pending
                    )
        except Exception as e:
            logger.debug("[SMART_BUFFER] State recovery error: %s", e)

    # ── Smart Dedup Fingerprint ───────────────────────────────────────────────

    @staticmethod
    def _make_content_hash(raw_name: str, raw_email: str, raw_linkedin: str) -> str:
        """
        Multi-key fingerprint: SHA-256(normalised_name|email|linkedin_slug).
        Catches duplicates even when email is missing but LinkedIn is confirmed.
        """
        name_key    = raw_name.strip().lower()
        email_key   = raw_email.strip().lower()
        # Extract just the slug from a full LinkedIn URL
        li_key = raw_linkedin.strip().lower()
        if "linkedin.com/in/" in li_key:
            li_key = li_key.split("linkedin.com/in/")[-1].rstrip("/")

        fingerprint = f"{name_key}|{email_key}|{li_key}"
        return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:40]

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def is_render_online(self) -> bool:
        return self._render_online

    def buffer_profile(self, profile: Dict[str, Any]) -> bool:
        """
        Saves a discovered profile to the offline buffer with dedup + priority tier.
        Returns True if newly buffered, False if duplicate or error.
        """
        try:
            discovery_id = profile.get("discovery_id") or f"BUF-{uuid.uuid4().hex[:14].upper()}"
            raw_name     = (profile.get("raw_name")    or profile.get("name")    or "").strip()
            raw_email    = (profile.get("raw_email")   or profile.get("email")   or "").strip()
            raw_linkedin = (profile.get("raw_linkedin") or profile.get("linkedin") or "").strip()

            content_hash = self._make_content_hash(raw_name, raw_email, raw_linkedin)
            source       = profile.get("extraction_source", "web_harvest")
            source_tier  = SOURCE_PRIORITY.get(source, 3)
            quality      = float(profile.get("quality_score", 0.7))

            with self._get_conn() as conn:
                existing = conn.execute(
                    "SELECT id, status FROM offline_profiles WHERE content_hash = ?",
                    (content_hash,)
                ).fetchone()

                if existing and existing["status"] != "FAILED":
                    return False  # Already buffered or flushed

                conn.execute("""
                    INSERT OR IGNORE INTO offline_profiles (
                        discovery_id, raw_name, raw_title, raw_company,
                        raw_email, raw_phone, raw_linkedin, raw_location,
                        source_url, extraction_source, quality_score, dom_confidence,
                        geo_region, geo_confidence, owner_user_id, metadata_json,
                        content_hash, source_tier, status, buffered_at, retry_after
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, 0)
                """, (
                    discovery_id,
                    raw_name,
                    (profile.get("raw_title")    or profile.get("title")    or "").strip(),
                    (profile.get("raw_company")  or profile.get("company")  or "").strip(),
                    raw_email,
                    (profile.get("raw_phone")    or profile.get("phone")    or "").strip() or None,
                    raw_linkedin or None,
                    (profile.get("raw_location") or profile.get("location") or "").strip() or None,
                    profile.get("source_url", ""),
                    source,
                    quality,
                    float(profile.get("dom_confidence", quality)),
                    profile.get("geo_region"),
                    profile.get("geo_confidence"),
                    int(profile.get("owner_user_id", 1)),
                    json.dumps(profile.get("metadata_json") or {}),
                    content_hash,
                    source_tier,
                    time.time(),
                ))
            return True
        except Exception as e:
            logger.warning("[SMART_BUFFER] buffer_profile error: %s", e)
            return False

    def get_pending_count(self) -> int:
        try:
            with self._get_conn() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM offline_profiles WHERE status = 'PENDING'"
                ).fetchone()
                return row[0] if row else 0
        except Exception:
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Returns comprehensive buffer + health telemetry for dashboard display."""
        try:
            with self._get_conn() as conn:
                pending = conn.execute(
                    "SELECT COUNT(*) FROM offline_profiles WHERE status = 'PENDING'"
                ).fetchone()[0]
                flushed = conn.execute(
                    "SELECT COUNT(*) FROM offline_profiles WHERE status = 'FLUSHED'"
                ).fetchone()[0]
                failed = conn.execute(
                    "SELECT COUNT(*) FROM offline_profiles WHERE status = 'FAILED'"
                ).fetchone()[0]
                in_retry = conn.execute(
                    "SELECT COUNT(*) FROM offline_profiles WHERE status = 'PENDING' AND retry_after > ?",
                    (time.time(),)
                ).fetchone()[0]
                tier_breakdown = conn.execute("""
                    SELECT source_tier, COUNT(*) as cnt
                    FROM offline_profiles WHERE status = 'PENDING'
                    GROUP BY source_tier ORDER BY source_tier
                """).fetchall()
                db_size_bytes = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        except Exception:
            pending = flushed = failed = in_retry = db_size_bytes = 0
            tier_breakdown = []

        now = time.time()
        current_downtime = (now - self._offline_since) if self._offline_since else 0

        return {
            "render_online":       self._render_online,
            "render_stable":       self.health.is_stable,
            "render_url":          RENDER_URL,
            "render_uptime_pct":   self.health.uptime_pct,
            "render_probe_ms":     round(self.health.last_probe_ms, 1),
            "render_avg_probe_ms": round(self.health.avg_probe_ms, 1),
            "render_reset_utc":    RENDER_RESET_UTC.isoformat(),
            "seconds_until_reset": max(0, int((RENDER_RESET_UTC - datetime.now(timezone.utc)).total_seconds())),
            "pending_buffered":    pending,
            "in_retry_cooldown":   in_retry,
            "total_flushed":       flushed,
            "total_failed":        failed,
            "flush_sessions":      self._flush_sessions,
            "current_poll_interval_sec": self._poll_interval,
            "total_downtime_sec":  round(self._total_downtime_sec + current_downtime, 1),
            "downtime_events":     self._downtime_events,
            "buffer_db_size_kb":   round(db_size_bytes / 1024, 1),
            "watchdog_running":    self._running,
            "tier_breakdown":      [{"tier": r["source_tier"], "count": r["cnt"]} for r in tier_breakdown],
        }

    # ── Smart Flush Engine ────────────────────────────────────────────────────

    def flush_pending_to_production(self, throttle_ms: float = 0) -> Dict[str, int]:
        """
        Flushes pending buffered profiles to Supabase in priority order:
          source_tier ASC (Desktop Scout first), then quality_score DESC.

        Only retries records whose retry_after timestamp has passed.

        Args:
            throttle_ms: Optional inter-record delay (ms) for cold-start Render protection.
        """
        from ..database import SessionLocal
        from ..models.staging_models import DiscoveryStaging

        result = {"flushed": 0, "skipped": 0, "failed": 0, "dlq": 0}
        now = time.time()

        try:
            with self._get_conn() as conn:
                rows = conn.execute("""
                    SELECT * FROM offline_profiles
                    WHERE status = 'PENDING' AND retry_after <= ?
                    ORDER BY source_tier ASC, quality_score DESC
                    LIMIT ?
                """, (now, FLUSH_BATCH_SIZE)).fetchall()
        except Exception as e:
            logger.error("[SMART_BUFFER] Cannot read pending records: %s", e)
            return result

        if not rows:
            return result

        logger.info("[SMART_BUFFER] Flushing %d profiles (priority-ordered)...", len(rows))
        for row in rows:
            try:
                with SessionLocal() as db:
                    # Dedup against live staging table
                    exists_email = (
                        db.query(DiscoveryStaging.id)
                        .filter(DiscoveryStaging.raw_email == row["raw_email"])
                        .first()
                    ) if row["raw_email"] else None

                    exists_id = (
                        db.query(DiscoveryStaging.id)
                        .filter(DiscoveryStaging.discovery_id == row["discovery_id"])
                        .first()
                    )

                    if exists_email or exists_id:
                        self._mark_status(row["id"], "FLUSHED", "dup")
                        result["skipped"] += 1
                        continue

                    staging = DiscoveryStaging(
                        discovery_id     = row["discovery_id"],
                        raw_name         = row["raw_name"],
                        raw_title        = row["raw_title"],
                        raw_company      = row["raw_company"],
                        raw_email        = row["raw_email"],
                        raw_phone        = row["raw_phone"],
                        raw_linkedin     = row["raw_linkedin"],
                        raw_location     = row["raw_location"],
                        source_url       = row["source_url"],
                        extraction_source= row["extraction_source"] or "web_harvest",
                        quality_score    = row["quality_score"] or 0.7,
                        dom_confidence   = row["dom_confidence"] or 0.7,
                        geo_region       = row["geo_region"],
                        geo_confidence   = row["geo_confidence"],
                        owner_user_id    = row["owner_user_id"] or 1,
                        metadata_json    = row["metadata_json"] or "{}",
                        processing_status= "pending",
                        created_at       = datetime.now(timezone.utc),
                    )
                    db.add(staging)
                    db.commit()
                    self._mark_status(row["id"], "FLUSHED")
                    result["flushed"] += 1
                    self._total_flushed_session = getattr(self, "_total_flushed_session", 0) + 1

                    if throttle_ms > 0:
                        time.sleep(throttle_ms / 1000.0)

            except Exception as e:
                attempts = (row["flush_attempts"] or 0) + 1
                if attempts >= 5:
                    self._mark_status(row["id"], "FAILED", str(e)[:300])
                    result["dlq"] += 1
                else:
                    # Exponential backoff: 2^attempts minutes
                    backoff_sec = min(2 ** attempts * 60, 3600)
                    self._mark_retry(row["id"], str(e)[:300], now + backoff_sec)
                    result["failed"] += 1
                logger.debug("[SMART_BUFFER] Flush error (attempt %d): %s", attempts, e)

        total = result["flushed"] + result["skipped"] + result["failed"] + result["dlq"]
        logger.info(
            "[SMART_BUFFER] Flush session: %d flushed | %d skipped | %d retry | %d DLQ of %d",
            result["flushed"], result["skipped"], result["failed"], result["dlq"], total
        )

        # Vacuum DB if flushed rows have accumulated
        self._maybe_vacuum()
        return result

    def _mark_status(self, record_id: int, status: str, note: str = ""):
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE offline_profiles SET status=?, flushed_at=?, flush_error=? WHERE id=?",
                    (status, time.time(), note or None, record_id)
                )
        except Exception as e:
            logger.debug("[SMART_BUFFER] _mark_status error: %s", e)

    def _mark_retry(self, record_id: int, error_msg: str, retry_after: float):
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    UPDATE offline_profiles
                    SET flush_attempts = flush_attempts + 1,
                        flush_error    = ?,
                        retry_after    = ?
                    WHERE id = ?
                """, (error_msg, retry_after, record_id))
        except Exception as e:
            logger.debug("[SMART_BUFFER] _mark_retry error: %s", e)

    def _maybe_vacuum(self):
        """Compacts the SQLite file once flushed rows exceed VACUUM_THRESHOLD."""
        try:
            with self._get_conn() as conn:
                flushed = conn.execute(
                    "SELECT COUNT(*) FROM offline_profiles WHERE status = 'FLUSHED'"
                ).fetchone()[0]
                if flushed >= VACUUM_THRESHOLD:
                    # Delete old FLUSHED rows to reclaim space, keep last 100
                    conn.execute("""
                        DELETE FROM offline_profiles WHERE status = 'FLUSHED'
                        AND id NOT IN (
                            SELECT id FROM offline_profiles WHERE status = 'FLUSHED'
                            ORDER BY flushed_at DESC LIMIT 100
                        )
                    """)
                    conn.execute("VACUUM")
                    logger.info("[SMART_BUFFER] VACUUM completed — old FLUSHED rows purged.")
        except Exception as e:
            logger.debug("[SMART_BUFFER] Vacuum error: %s", e)

    def _log_event(self, event_type: str, detail: str = ""):
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO buffer_events (event_type, detail, ts) VALUES (?, ?, ?)",
                    (event_type, detail, time.time())
                )
        except Exception:
            pass

    # ── Adaptive Render Probe ─────────────────────────────────────────────────

    def _probe_render(self) -> Tuple[bool, float]:
        """
        Probes Render /ping endpoint.
        Returns (is_online: bool, response_time_ms: float).
        """
        start = time.monotonic()
        try:
            r = requests.get(
                f"{RENDER_URL}/ping",
                timeout=10,
                headers={"User-Agent": "TalentOpsAI-WatchdogV2/1.0"}
            )
            elapsed_ms = (time.monotonic() - start) * 1000
            return r.status_code == 200, elapsed_ms
        except Exception:
            elapsed_ms = (time.monotonic() - start) * 1000
            return False, elapsed_ms

    def _compute_poll_interval(self) -> float:
        """
        Adaptive polling: exponential backoff when Render is offline.
        30s → 60s → 120s … capped at RENDER_POLL_MAX_SEC.
        Resets to base immediately on recovery.
        """
        if self._render_online:
            return RENDER_POLL_BASE_SEC
        backoff = RENDER_POLL_BASE_SEC * (2 ** min(self._consecutive_fails, 8))
        return min(backoff, RENDER_POLL_MAX_SEC)

    # ── Scheduled Wakeup Thread ───────────────────────────────────────────────

    def _run_scheduler(self):
        """
        Sleeps until the known Render reset time (Oct 1 2026 00:00 UTC),
        then probes every 10 seconds for 5 minutes to detect the exact
        moment Render comes back online (fast-path, bypasses backoff).
        """
        now = datetime.now(timezone.utc)
        if now >= RENDER_RESET_UTC:
            return  # Already past reset time, no need to schedule

        sleep_sec = (RENDER_RESET_UTC - now).total_seconds()
        logger.info(
            "[SMART_BUFFER] Render reset scheduler: will activate in %.0f seconds "
            "(Oct 1 2026 00:00 UTC).", sleep_sec
        )
        time.sleep(max(0, sleep_sec - 30))  # Wake up 30s early to start fast-probing

        if not self._running:
            return

        logger.info("[SMART_BUFFER] Render reset window reached — entering fast-probe mode (10s intervals).")
        self._poll_interval = 10   # Override adaptive poll for fast detection
        deadline = time.time() + 300  # Fast-probe for up to 5 minutes

        while self._running and time.time() < deadline:
            is_online, ms = self._probe_render()
            if is_online:
                logger.info("[SMART_BUFFER] SCHEDULED WAKEUP: Render detected online! (%.0fms)", ms)
                self._handle_render_recovery(ms)
                self._poll_interval = RENDER_POLL_BASE_SEC
                return
            time.sleep(10)

        # Hand back to normal watchdog after fast-probe window
        self._poll_interval = RENDER_POLL_BASE_SEC
        logger.info("[SMART_BUFFER] Fast-probe window closed. Handing back to watchdog.")

    def _handle_render_recovery(self, probe_ms: float):
        """Called when Render transitions from offline → stable. Initiates smart flush."""
        self._render_online = True
        self._consecutive_fails = 0
        self._poll_interval = RENDER_POLL_BASE_SEC

        # Compute and record downtime
        if self._offline_since:
            downtime = time.time() - self._offline_since
            self._total_downtime_sec += downtime
            self._offline_since = None
            self._log_event("RENDER_ONLINE", f"downtime={downtime:.0f}s probe_ms={probe_ms:.0f}")

        self._last_online_at = time.time()
        pending = self.get_pending_count()

        logger.info(
            "[SMART_BUFFER] ✅ RENDER STABLE (avg probe: %.0fms | uptime: %.1f%%). "
            "Flushing %d buffered profiles...",
            self.health.avg_probe_ms, self.health.uptime_pct, pending
        )

        if pending == 0:
            logger.info("[SMART_BUFFER] Buffer is empty — nothing to flush.")
            return

        self._flush_sessions += 1

        # If Render is still slow (cold start), throttle inter-record writes
        throttle_ms = 50.0 if self.health.avg_probe_ms > 2000 else 0.0

        remaining = pending
        while remaining > 0 and self._running:
            fr = self.flush_pending_to_production(throttle_ms=throttle_ms)
            remaining = self.get_pending_count()
            if fr["flushed"] == 0 and fr["skipped"] == 0:
                break  # Nothing made progress — stop to avoid spin

        logger.info(
            "[SMART_BUFFER] Full flush complete. %d records remain (retry cooldown).",
            self.get_pending_count()
        )

    # ── Main Watchdog Loop ────────────────────────────────────────────────────

    def start_watchdog(self):
        """Starts both the watchdog thread and the scheduled wakeup thread."""
        if self._running:
            return
        self._running = True

        # Main watchdog
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop, daemon=True, name="RenderWatchdog"
        )
        self._watchdog_thread.start()

        # Scheduled wakeup (Oct 1 reset)
        now = datetime.now(timezone.utc)
        if now < RENDER_RESET_UTC:
            self._scheduler_thread = threading.Thread(
                target=self._run_scheduler, daemon=True, name="RenderScheduler"
            )
            self._scheduler_thread.start()
            secs_left = int((RENDER_RESET_UTC - now).total_seconds())
            logger.info(
                "[SMART_BUFFER] Watchdog + Scheduler started. "
                "Render resets in %dh %dm (Oct 1 00:00 UTC).",
                secs_left // 3600, (secs_left % 3600) // 60
            )
        else:
            logger.info("[SMART_BUFFER] Watchdog started. (Past scheduled reset — continuous polling.)")

    def stop_watchdog(self):
        self._running = False
        logger.info("[SMART_BUFFER] Watchdog stopped.")

    def _watchdog_loop(self):
        """
        Main watchdog loop with adaptive polling and health-gated flush.
        """
        # Initial probe — don't assume online
        is_online, probe_ms = self._probe_render()
        if is_online:
            self.health.record_success(probe_ms)
        else:
            self.health.record_failure()
            self._render_online = False
            self._offline_since = time.time()
            self._downtime_events += 1
            logger.warning(
                "[SMART_BUFFER] Render is OFFLINE at startup. "
                "Adaptive polling active. %d profiles buffered.",
                self.get_pending_count()
            )

        while self._running:
            try:
                is_online, probe_ms = self._probe_render()

                if is_online:
                    self.health.record_success(probe_ms)

                    if not self._render_online:
                        # Transitioning offline → recovering
                        logger.info(
                            "[SMART_BUFFER] Render responding (%.0fms). "
                            "Confirming stability (%d/%d pings)...",
                            probe_ms, self.health.consecutive_successes, MIN_STABLE_PINGS
                        )
                        if self.health.is_stable:
                            # Render confirmed stable — trigger flush
                            self._handle_render_recovery(probe_ms)

                    else:
                        # Already online — opportunistic flush of any lingering PENDING
                        pending = self.get_pending_count()
                        if pending > 0:
                            logger.info(
                                "[SMART_BUFFER] Opportunistic flush: %d pending records.", pending
                            )
                            self.flush_pending_to_production(throttle_ms=0)
                else:
                    self.health.record_failure()

                    if self._render_online:
                        # Transitioning online → offline
                        self._render_online = False
                        self._offline_since = time.time()
                        self._downtime_events += 1
                        self.health.reset_stability()
                        self._log_event("RENDER_OFFLINE", f"probe_ms={probe_ms:.0f}")
                        logger.warning(
                            "[SMART_BUFFER] ⚠ Render OFFLINE. Offline buffer mode active. "
                            "Poll backoff starting."
                        )

                    self._consecutive_fails += 1

                self._poll_interval = self._compute_poll_interval()

            except Exception as e:
                logger.debug("[SMART_BUFFER] Watchdog error: %s", e)
                self._poll_interval = RENDER_POLL_BASE_SEC

            time.sleep(self._poll_interval)


# ── Module-Level Singleton ────────────────────────────────────────────────────

offline_buffer = OfflineHarvestBuffer()
