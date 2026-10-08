"""
Memory Sentinel — Autonomous Proactive Memory Guard for TalentOps AI
====================================================================
Monitors Linux cgroup / container memory in real-time, especially on Render
512MB instances. Proactively prevents Out-Of-Memory (OOM) SIGKILL termination
by enforcing memory reclamation before the kernel threshold is breached:

1. Real Cgroup Tracking: Reads /sys/fs/cgroup (v1 and v2) memory limits.
2. Kernel Arena Trimming: Invokes libc malloc_trim(0) to release unmapped heap to OS.
3. Cache Shedding: Flushes route and aggregate caches if container approaches 75% limit.
4. DuckDB Memory Throttling: Keeps DuckDB internal working set capped.
"""

import os
import sys
import time
import ctypes
import logging
import threading
import gc
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger("talentops.memory_sentinel")

_LIBC = None
if sys.platform.startswith("linux"):
    try:
        _LIBC = ctypes.CDLL("libc.so.6")
    except Exception as e:
        logger.debug("libc.so.6 load notice: %s", e)


def trim_os_memory():
    """Forces glibc to release freed heap memory arenas back to the Linux kernel."""
    gc.collect()
    if _LIBC and hasattr(_LIBC, "malloc_trim"):
        try:
            _LIBC.malloc_trim(0)
        except Exception:
            pass


def read_cgroup_memory() -> Tuple[Optional[int], Optional[int]]:
    """
    Returns (used_bytes, limit_bytes) from Linux cgroups.
    Supports cgroup v2 (/sys/fs/cgroup/memory.*) and cgroup v1 (/sys/fs/cgroup/memory/*).
    """
    # 1. cgroup v2 (Modern Render / Docker environments)
    current_v2 = "/sys/fs/cgroup/memory.current"
    max_v2 = "/sys/fs/cgroup/memory.max"
    if os.path.exists(current_v2):
        try:
            with open(current_v2, "r") as f:
                used = int(f.read().strip())
            limit = None
            if os.path.exists(max_v2):
                with open(max_v2, "r") as f:
                    val = f.read().strip()
                    if val != "max":
                        limit = int(val)
            return used, limit
        except Exception:
            pass

    # 2. cgroup v1 (Legacy container environments)
    usage_v1 = "/sys/fs/cgroup/memory/memory.usage_in_bytes"
    limit_v1 = "/sys/fs/cgroup/memory/memory.limit_in_bytes"
    if os.path.exists(usage_v1):
        try:
            with open(usage_v1, "r") as f:
                used = int(f.read().strip())
            limit = None
            if os.path.exists(limit_v1):
                with open(limit_v1, "r") as f:
                    limit_raw = int(f.read().strip())
                    # cgroup v1 reports huge numbers (like 2^63-1) when no limit is configured
                    if limit_raw < 1099511627776:  # < 1 TB
                        limit = limit_raw
            return used, limit
        except Exception:
            pass

    return None, None


class MemorySentinel:
    _instance = None

    def __init__(self):
        self.is_render = bool(
            os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID") or os.getenv("IS_PRODUCTION", "false").lower() == "true"
        )
        # Default container memory ceiling (Render free/starter is 512MB)
        self.default_limit_bytes = int(os.getenv("CONTAINER_MEMORY_LIMIT_MB", "512")) * 1024 * 1024
        # Warning threshold (75% of limit, e.g. 384 MB on 512MB container)
        self.warning_threshold_ratio = float(os.getenv("MEMORY_WARNING_RATIO", "0.75"))
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._interval = 25.0  # Check every 25 seconds
        self._last_stats: Dict[str, Any] = {}
        self._trims_performed = 0

    @classmethod
    def get_instance(cls) -> "MemorySentinel":
        if cls._instance is None:
            cls._instance = MemorySentinel()
        return cls._instance

    def get_status(self) -> Dict[str, Any]:
        """Returns real-time container memory diagnostics."""
        used_bytes, limit_bytes = read_cgroup_memory()
        cgroup_detected = used_bytes is not None
        
        if used_bytes is None:
            # Fallback to psutil process RSS
            try:
                import psutil
                process = psutil.Process()
                used_bytes = process.memory_info().rss
                limit_bytes = self.default_limit_bytes if self.is_render else psutil.virtual_memory().total
            except Exception:
                used_bytes = 150 * 1024 * 1024
                limit_bytes = self.default_limit_bytes

        if not limit_bytes:
            limit_bytes = self.default_limit_bytes

        used_mb = round(used_bytes / (1024 * 1024), 1)
        limit_mb = round(limit_bytes / (1024 * 1024), 1)
        percent = round((used_bytes / limit_bytes) * 100, 1)

        status = {
            "used_mb": used_mb,
            "limit_mb": limit_mb,
            "percent": percent,
            "cgroup_detected": cgroup_detected,
            "trims_performed": self._trims_performed,
            "is_render": self.is_render,
            "is_warning": percent >= (self.warning_threshold_ratio * 100),
            "timestamp": time.time(),
        }
        self._last_stats = status
        return status

    def perform_reclamation(self, force: bool = False) -> Dict[str, Any]:
        """Reclaims memory from internal caches and OS heap."""
        status = self.get_status()
        used_mb_before = status["used_mb"]

        if force or status["is_warning"]:
            logger.warning(
                "[MEMORY SENTINEL] Container memory at %s MB (%s%% of %s MB). Initiating proactive reclamation...",
                used_mb_before, status["percent"], status["limit_mb"]
            )

            # 1. Clear in-memory analytics cache
            try:
                from ..core.cache import analytics_cache
                analytics_cache.clear()
            except Exception:
                pass

            # 2. Clear OLAP sidecar cache
            try:
                from ..olap_sidecar import olap_sidecar
                olap_sidecar.invalidate()
            except Exception:
                pass

            # 3. Throttle DuckDB working set if loaded
            try:
                from ..services.recruiter_store import recruiter_store
                if recruiter_store._conn:
                    recruiter_store._conn.execute("PRAGMA max_memory='48MB';")
            except Exception:
                pass

        # 4. Run GC and kernel arena trimming
        trim_os_memory()
        self._trims_performed += 1

        new_status = self.get_status()
        used_mb_after = new_status["used_mb"]
        freed_mb = round(max(0.0, used_mb_before - used_mb_after), 1)
        if freed_mb > 0:
            logger.info(
                "[MEMORY SENTINEL] Memory successfully reclaimed: %s MB -> %s MB (Freed %s MB)",
                used_mb_before, used_mb_after, freed_mb
            )

        return {
            "used_mb_before": used_mb_before,
            "used_mb_after": used_mb_after,
            "freed_mb": freed_mb,
            "current_status": new_status,
        }

    def run_trim_cycle(self, force: bool = False) -> Dict[str, Any]:
        """Alias for perform_reclamation."""
        return self.perform_reclamation(force=force)

    def _monitor_loop(self):
        logger.info("[MEMORY SENTINEL] Background watchdog loop started (Interval: %ss)", self._interval)
        while self._running:
            try:
                self.perform_reclamation(force=False)
            except Exception as e:
                logger.warning("[MEMORY SENTINEL] Error during memory check: %s", e)

            # Sleep in short increments for responsive shutdown
            for _ in range(int(self._interval)):
                if not self._running:
                    break
                time.sleep(1.0)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="MemorySentinelThread")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)


memory_sentinel = MemorySentinel.get_instance()
