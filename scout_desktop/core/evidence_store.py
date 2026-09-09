"""
core/evidence_store.py — State-Aware Temporary Screenshot Lifecycle & Auto-Purge Engine

Manages temporary screenshot storage, state transitions, and auto-purging.
Lifecycle: CAPTURED -> ANALYZING -> EXTRACTED -> STAGED -> CLEANUP_PENDING -> PURGED.
Rules:
- Never purge while in ANALYZING / PROCESSING state.
- Discard immediately (0ms) if NO USEFUL DATA.
- Staged images deleted after lightweight audit retention window (~15-30s, hard max 2-3min).
- Startup cleanup sweeps stale images from past crashes.
- Distinct counters for Captured, Active Buffer, Processing, Pending Cleanup, and Purged.
"""

import os
import time
import glob
import logging
import threading
from typing import Optional, Dict, Any, List
from PIL import Image

logger = logging.getLogger("scout.evidence_store")

AUDIT_RETENTION_SEC = 20.0       # 20-second evidence audit window after staging
HARD_MAX_RETENTION_SEC = 150.0   # 2.5-minute hard maximum retention ceiling
HARD_MAX_FILE_AGE_SEC = 3600.0   # 1-Hour Strict User Mandate (Unconditional Purge Ceiling)
MAX_BUFFER_IMAGES = 20           # Keep buffer light on disk

VALID_TRANSITIONS = {
    "CAPTURED": ["ANALYZING", "NO_USEFUL_DATA", "DISCARDED", "PROCESSING_FAILED"],
    "ANALYZING": ["EXTRACTED", "PROCESSING_FAILED", "NO_USEFUL_DATA", "DISCARDED"],
    "EXTRACTED": ["STAGED", "SYNC_COMPLETE", "CLEANUP_PENDING", "NO_USEFUL_DATA", "DISCARDED"],
    "STAGED": ["SYNC_COMPLETE", "CLEANUP_PENDING", "NO_USEFUL_DATA", "DISCARDED"],
    "SYNC_COMPLETE": ["CLEANUP_PENDING"],
    "PROCESSING_FAILED": ["ANALYZING", "CLEANUP_PENDING", "PURGED"],
    "CLEANUP_PENDING": ["PURGED"],
    "PURGED": [],
    "NO_USEFUL_DATA": ["PURGED"],
    "DISCARDED": ["PURGED"]
}

class CaptureItem:
    def __init__(
        self,
        capture_id: str,
        filepath: str,
        page_url: str = "",
        window_title: str = "",
        change_score: float = 1.0,
        status: str = "CAPTURED",
    ):
        self.capture_id = capture_id
        self.filepath = filepath
        self.page_url = page_url
        self.window_title = window_title
        self.change_score = change_score
        self.status = status  # CAPTURED | ANALYZING | EXTRACTED | STAGED | CLEANUP_PENDING | PURGED
        self.created_at = time.time()
        self.expires_at = self.created_at + HARD_MAX_RETENTION_SEC
        self.retry_count = 0
        self.extracted_entities = []

    @property
    def file_path(self):
        return self.filepath

    def to_dict(self):
        return {
            "capture_id": self.capture_id,
            "status": self.status,
            "page_url": self.page_url,
            "window_title": self.window_title,
            "change_score": self.change_score,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "entities_count": len(self.extracted_entities),
        }


class EvidenceStore:
    def __init__(
        self,
        storage_dir: Optional[str] = None,
        audit_retention_sec: float = AUDIT_RETENTION_SEC,
        hard_max_retention_sec: float = HARD_MAX_RETENTION_SEC,
        max_buffer_images: int = MAX_BUFFER_IMAGES,
        max_buffer_mb: int = 100,
        retention_sec: Optional[float] = None,
    ):
        if not storage_dir:
            storage_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "captures")
        self.storage_dir = os.path.abspath(storage_dir)
        os.makedirs(self.storage_dir, exist_ok=True)
        
        if retention_sec is not None:
            audit_retention_sec = retention_sec
        self.audit_retention_sec = audit_retention_sec
        self.hard_max_retention_sec = hard_max_retention_sec
        self.max_buffer_images = max_buffer_images
        self.max_buffer_mb = max_buffer_mb

        self._items: Dict[str, CaptureItem] = {}
        self._lock = threading.Lock()

        # Telemetry counters
        self.total_captured_ever = 0
        self.total_purged_ever = 0
        self.last_purge_time = None

        # Run startup cleanup immediately
        self.purge_stale_startup()

    def update_config(
        self,
        audit_retention_sec: Optional[float] = None,
        hard_max_retention_sec: Optional[float] = None,
        max_buffer_images: Optional[int] = None,
        max_buffer_mb: Optional[int] = None
    ):
        """Updates runtime configuration settings for the evidence store."""
        with self._lock:
            if audit_retention_sec is not None:
                self.audit_retention_sec = audit_retention_sec
            if hard_max_retention_sec is not None:
                self.hard_max_retention_sec = hard_max_retention_sec
            if max_buffer_images is not None:
                self.max_buffer_images = max_buffer_images
            if max_buffer_mb is not None:
                self.max_buffer_mb = max_buffer_mb

    @property
    def active_buffer_count(self) -> int:
        with self._lock:
            return sum(1 for it in self._items.values() if it.status != "PURGED")

    @property
    def processing_count(self) -> int:
        with self._lock:
            return sum(1 for it in self._items.values() if it.status == "ANALYZING")

    @property
    def pending_cleanup_count(self) -> int:
        with self._lock:
            return sum(1 for it in self._items.values() if it.status in ("CLEANUP_PENDING", "STAGED"))

    def _get_total_storage_bytes(self) -> int:
        """Sums the file sizes of all stored items on disk."""
        total = 0
        for item in self._items.values():
            if item.filepath and os.path.exists(item.filepath):
                try:
                    total += os.path.getsize(item.filepath)
                except Exception:
                    pass
        return total

    def save_capture(
        self,
        img: Image.Image,
        capture_id: str,
        page_url: str = "",
        window_title: str = "",
        change_score: float = 1.0,
    ) -> CaptureItem:
        """Saves screenshot to disk and registers in evidence store."""
        filepath = os.path.join(self.storage_dir, f"{capture_id}.jpg")
        try:
            # Save as optimized JPEG to minimize memory & disk
            rgb_img = img.convert("RGB")
            rgb_img.save(filepath, format="JPEG", quality=85, optimize=True)
        except Exception as e:
            logger.error("Failed to save capture %s to disk: %s", capture_id, e)

        item = CaptureItem(
            capture_id=capture_id,
            filepath=filepath,
            page_url=page_url,
            window_title=window_title,
            change_score=change_score,
            status="CAPTURED",
        )

        with self._lock:
            self._items[capture_id] = item
            self.total_captured_ever += 1

            # Buffer overflow safety: prune oldest cleanup_pending if above capacity
            if len(self._items) > self.max_buffer_images:
                self._prune_overflow()
                
            # Buffer overflow safety: prune lowest-value if above max MB
            if self._get_total_storage_bytes() > self.max_buffer_mb * 1024 * 1024:
                self._prune_size_overflow()

        return item

    def update_status(
        self,
        capture_id: str,
        new_status: str,
        extracted_entities: Optional[List[Any]] = None,
    ):
        """
        Transitions capture state and schedules auto-purge.
        """
        with self._lock:
            item = self._items.get(capture_id)
            if not item:
                return

            if item.status in VALID_TRANSITIONS and new_status not in VALID_TRANSITIONS[item.status]:
                logger.warning("Invalid state transition from %s to %s for %s", item.status, new_status, capture_id)

            item.status = new_status
            if extracted_entities:
                item.extracted_entities = extracted_entities

            now = time.time()

            # Rule 3: If no useful data -> Discard immediately (0ms)
            if new_status in ("NO_USEFUL_DATA", "DISCARDED"):
                self._delete_capture_file(item, "no_useful_data")
                item.status = "PURGED"
                return

            if new_status == "EXTRACTED":
                item.status = "EXTRACTED"
                item.expires_at = now + self.hard_max_retention_sec
            elif new_status == "STAGED":
                item.status = "STAGED"
                item.expires_at = now + self.hard_max_retention_sec
            elif new_status == "SYNC_COMPLETE":
                item.status = "CLEANUP_PENDING"
                item.expires_at = now + self.audit_retention_sec

            # Retry budget for failures
            if new_status == "PROCESSING_FAILED":
                item.retry_count += 1
                if item.retry_count > 3:
                    item.status = "CLEANUP_PENDING"
                    item.expires_at = now + 10.0

    def purge_hard_1hour_ceiling(self, max_age_sec: float = HARD_MAX_FILE_AGE_SEC) -> int:
        """
        STRICT USER MANDATE:
        Deletes ANY screenshot file on disk older than 1 hour (3600 seconds)
        regardless of its state (even ANALYZING, STAGED, EXTRACTED, ORPHANED, etc.),
        NO MATTER THE CASE.
        """
        now = time.time()
        purged_count = 0
        try:
            pattern = os.path.join(self.storage_dir, "*.*")
            files = glob.glob(pattern)
            for f in files:
                if not f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    continue
                try:
                    mtime = os.path.getmtime(f)
                    ctime = os.path.getctime(f)
                    file_time = min(mtime, ctime)
                    file_age = now - file_time

                    if file_age >= max_age_sec:
                        os.remove(f)
                        purged_count += 1
                        logger.info("⏰ 1-Hour Hard Ceiling Purge: Removed '%s' (Age: %.1fs >= %.1fs)",
                                    os.path.basename(f), file_age, max_age_sec)
                except Exception as fe:
                    logger.debug("Error checking/deleting file %s: %s", f, fe)

            # Synchronize memory state
            with self._lock:
                to_remove = []
                for cid, it in self._items.items():
                    if it.filepath and not os.path.exists(it.filepath):
                        it.status = "PURGED"
                        it.filepath = None
                        to_remove.append(cid)
                    elif (now - it.created_at) >= max_age_sec:
                        if it.filepath and os.path.exists(it.filepath):
                            try:
                                os.remove(it.filepath)
                                purged_count += 1
                            except Exception:
                                pass
                        it.status = "PURGED"
                        it.filepath = None
                        to_remove.append(cid)

                for cid in to_remove:
                    self._items.pop(cid, None)

            if purged_count > 0:
                self.total_purged_ever += purged_count
                self.last_purge_time = time.strftime("%H:%M:%S")

        except Exception as e:
            logger.error("Error running purge_hard_1hour_ceiling: %s", e)

        return purged_count

    def purge_expired(self) -> int:
        """
        Scans items and deletes images whose retention TTL has expired.
        Strict Rule: Never purge while status == 'ANALYZING' for short-term TTL,
        BUT unconditionally purges any file older than 1 hour (3600s) NO MATTER THE CASE.
        """
        # 1. Enforce strict unconditional 1-hour hard ceiling
        hard_purged = self.purge_hard_1hour_ceiling()

        # 2. Sweep orphaned or untracked crop files on disk
        orphans_purged = self.sweep_orphan_files()

        # 3. Regular short-term audit TTL expiration
        now = time.time()
        purged_count = hard_purged + orphans_purged

        with self._lock:
            to_purge = []
            for cid, item in self._items.items():
                if item.status == "ANALYZING":
                    continue  # Protect active analysis during short-term window (< 1 hour)
                if item.status != "PURGED" and item.expires_at <= now:
                    to_purge.append(item)

            for item in to_purge:
                self._delete_capture_file(item, "audit_ttl_expired")
                item.status = "PURGED"
                purged_count += 1

            # Clean memory of old PURGED items older than 5 minutes
            stale_keys = [
                cid for cid, it in self._items.items()
                if it.status == "PURGED" and (now - it.created_at) > 300
            ]
            for k in stale_keys:
                del self._items[k]

        return purged_count

    def purge_stale_startup(self) -> int:
        """
        Sweeps the disk directory on startup to delete orphaned captures from prior sessions/crashes.
        """
        count = 0
        try:
            pattern = os.path.join(self.storage_dir, "*.jpg")
            files = glob.glob(pattern)
            for f in files:
                try:
                    os.remove(f)
                    count += 1
                except Exception:
                    pass
            if count > 0:
                logger.info("🧹 Startup Cleanup: Purged %d stale capture(s) from disk.", count)
                self.last_purge_time = time.strftime("%H:%M:%S")
                self.total_purged_ever += count
        except Exception as e:
            logger.debug("Startup purge error: %s", e)
        return count

    def sweep_orphan_files(self) -> int:
        """Scans disk for .jpg files not in self._items and deletes them."""
        count = 0
        with self._lock:
            valid_paths = {
                os.path.abspath(it.filepath) for it in self._items.values() if it.filepath
            }
        
        try:
            pattern = os.path.join(self.storage_dir, "*.jpg")
            files = glob.glob(pattern)
            for f in files:
                abs_f = os.path.abspath(f)
                if abs_f not in valid_paths:
                    try:
                        os.remove(f)
                        count += 1
                    except Exception:
                        pass
            if count > 0:
                logger.info("🧹 Sweep Orphans: Purged %d orphaned file(s) from disk.", count)
                with self._lock:
                    self.total_purged_ever += count
                    self.last_purge_time = time.strftime("%H:%M:%S")
        except Exception as e:
            logger.debug("Sweep orphans error: %s", e)
            
        return count

    def _delete_capture_file(self, item: CaptureItem, reason: str):
        """Safely removes physical image file from disk."""
        if item.filepath and os.path.exists(item.filepath):
            try:
                os.remove(item.filepath)
                item.filepath = None
                self.total_purged_ever += 1
                self.last_purge_time = time.strftime("%H:%M:%S")
                logger.info("🗑️ Purged capture %s from disk (Reason: %s)", item.capture_id, reason)
            except Exception as e:
                logger.debug("Failed to delete %s: %s", item.filepath, e)

    def _prune_overflow(self):
        """Deletes oldest completed captures if buffer exceeds max capacity."""
        candidates = [
            cid for cid, it in self._items.items()
            if it.status in ("CLEANUP_PENDING", "STAGED", "PURGED")
        ]
        candidates.sort(key=lambda cid: self._items[cid].created_at)
        while len(self._items) > self.max_buffer_images and candidates:
            cid = candidates.pop(0)
            item = self._items[cid]
            self._delete_capture_file(item, "buffer_overflow_prune")
            del self._items[cid]

    def _prune_size_overflow(self):
        """Deletes lowest-value captures if storage exceeds max MB."""
        while self._get_total_storage_bytes() > self.max_buffer_mb * 1024 * 1024:
            candidates = [
                cid for cid, it in self._items.items()
                if it.status in ("CLEANUP_PENDING", "STAGED", "PURGED", "EXTRACTED")
            ]
            if not candidates:
                break
            
            # Sort by change score (lowest first), then oldest
            candidates.sort(key=lambda cid: (self._items[cid].change_score, self._items[cid].created_at))
            
            cid = candidates.pop(0)
            item = self._items[cid]
            self._delete_capture_file(item, "size_overflow_prune")
            del self._items[cid]

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns accurate diagnostic telemetry counters."""
        with self._lock:
            active_buf = sum(1 for it in self._items.values() if it.status != "PURGED")
            proc = sum(1 for it in self._items.values() if it.status == "ANALYZING")
            pending = sum(1 for it in self._items.values() if it.status == "CLEANUP_PENDING")

            return {
                "total_captured_cumulative": self.total_captured_ever,
                "active_buffer_images": active_buf,
                "currently_processing": proc,
                "pending_cleanup": pending,
                "total_purged_cumulative": self.total_purged_ever,
                "last_purge_time": self.last_purge_time or "Clean",
            }
