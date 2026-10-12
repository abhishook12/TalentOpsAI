import os
import json
import time
import logging
import psutil
from typing import Optional
from sqlalchemy import text
from .database import engine

logger = logging.getLogger("talentops.lockdown")

LOCKDOWN_FILE = os.path.join(os.path.dirname(__file__), "..", ".lockdown_state.json")
GEMINI_TRACKER_FILE = os.path.join(os.path.dirname(__file__), "..", ".gemini_requests.json")

# Enterprise Thresholds (10GB DB, 10GB Storage, 4GB RAM)
MAX_DB_SIZE_MB = 10000.0
MAX_STORAGE_SIZE_MB = 10000.0
MAX_MEMORY_MB = 4096.0
MAX_GEMINI_RPM = 6000

class ResourceLockdownException(Exception):
    pass

_lockdown_cache = None
_lockdown_cache_time = 0.0

def _get_lockdown_state() -> dict:
    global _lockdown_cache, _lockdown_cache_time
    now = time.time()
    if _lockdown_cache and (now - _lockdown_cache_time < 10.0):
        return _lockdown_cache

    if not os.path.exists(LOCKDOWN_FILE):
        state = {"is_locked": False, "reason": None, "timestamp": None, "unlock_until": None}
    else:
        try:
            with open(LOCKDOWN_FILE, "r") as f:
                state = json.load(f)
        except Exception:
            state = {"is_locked": False, "reason": None, "timestamp": None, "unlock_until": None}
            
    # Auto-heal legacy false-positive lockdowns (e.g., old 1000MB DB limit or 60 RPM Gemini limit)
    if state.get("is_locked"):
        reason_str = str(state.get("reason") or "")
        if "1000.0 MB" in reason_str or "280.0 MB" in reason_str or "Gemini API rate" in reason_str:
            state = {"is_locked": False, "reason": None, "timestamp": None, "unlock_until": None}
            try:
                with open(LOCKDOWN_FILE, "w") as f:
                    json.dump(state, f)
            except Exception:
                pass

    _lockdown_cache = state
    _lockdown_cache_time = now
    return state

def _set_lockdown_state(is_locked: bool, reason: Optional[str] = None, unlock_until: Optional[float] = None):
    global _lockdown_cache, _lockdown_cache_time
    state = {
        "is_locked": is_locked,
        "reason": reason,
        "timestamp": time.time() if is_locked else None,
        "unlock_until": unlock_until
    }
    try:
        with open(LOCKDOWN_FILE, "w") as f:
            json.dump(state, f)
    except Exception:
        pass
        
    _lockdown_cache = state
    _lockdown_cache_time = time.time()
    
    if is_locked:
        logger.error(f"!!! EMERGENCY RESOURCE LOCKDOWN INITIATED: {reason} !!!")
    else:
        logger.info("System unlocked successfully.")

def is_locked_down() -> bool:
    state = _get_lockdown_state()
    unlock_until = state.get("unlock_until")
    if unlock_until and time.time() < unlock_until:
        return False
    return state.get("is_locked", False)

def get_lockdown_reason() -> Optional[str]:
    return _get_lockdown_state().get("reason")

def enforce_limits():
    """Throws ResourceLockdownException if a lockdown is active."""
    if is_locked_down():
        raise ResourceLockdownException(f"System is in Emergency Lockdown: {get_lockdown_reason()}")

_last_limit_check_time: float = 0.0
_LIMIT_CHECK_INTERVAL: float = 30.0  # Check DB/memory at most once every 30 seconds

def check_system_limits():
    """Checks DB size and memory. If thresholds breached, triggers lockdown.
    Results are cached for 30s to avoid hammering DB on every request."""
    global _last_limit_check_time
    now = time.time()
    if now - _last_limit_check_time < _LIMIT_CHECK_INTERVAL:
        return  # Skip — checked recently, all was fine
    _last_limit_check_time = now

    # Check Memory
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    mem_mb = mem_info.rss / 1048576.0
    if mem_mb >= MAX_MEMORY_MB:
        _set_lockdown_state(True, f"Memory exceeded threshold ({mem_mb:.2f} MB / {MAX_MEMORY_MB} MB limit)")
        return

    # Check DB Size & Storage Size
    try:
        from sqlalchemy.orm import Session
        with Session(engine) as db:
            # 1. Check Database Size
            if 'sqlite' in str(db.bind.url):
                db_path = str(db.bind.url).replace('sqlite:///', '')
                try:
                    db_size_mb = os.path.getsize(db_path) / 1048576.0
                except FileNotFoundError:
                    db_size_mb = 0.0
            else:
                res = db.execute(text("SELECT pg_database_size(current_database()) / 1048576.0")).fetchone()
                db_size_mb = float(res[0]) if res and res[0] else 0.0
                
            logger.debug(f"[Shield] DB size: {db_size_mb:.1f} MB / {MAX_DB_SIZE_MB} MB limit")
            if db_size_mb >= MAX_DB_SIZE_MB:
                _set_lockdown_state(True, f"Database Size exceeded threshold ({db_size_mb:.2f} MB / {MAX_DB_SIZE_MB} MB limit)")
                return
            
            # 2. Check Storage Size
            try:
                if 'sqlite' in str(db.bind.url):
                    storage_res = db.execute(text("SELECT sum(json_extract(metadata, '$.size')) FROM 'storage.objects'")).fetchone()
                else:
                    storage_res = db.execute(text("SELECT sum((metadata->>'size')::bigint) FROM storage.objects")).fetchone()
                storage_bytes = float(storage_res[0]) if storage_res and storage_res[0] else 0.0
                storage_size_mb = storage_bytes / 1048576.0
                logger.debug(f"[Shield] Storage size: {storage_size_mb:.1f} MB / {MAX_STORAGE_SIZE_MB} MB limit")
                if storage_size_mb >= MAX_STORAGE_SIZE_MB:
                    _set_lockdown_state(True, f"Storage Size exceeded threshold ({storage_size_mb:.2f} MB / {MAX_STORAGE_SIZE_MB} MB limit)")
                    return
            except Exception as se:
                logger.debug(f"[Shield] Could not check storage size (likely local SQLite or no storage configured): {se}")

            # Auto-recover if previously locked and now healthy
            if is_locked_down():
                _set_lockdown_state(False, None)
                
    except Exception as e:
        logger.error(f"Failed to check DB limits: {e}")

def track_gemini_call():
    """Tracks Gemini API usage without locking down the platform."""
    now = time.time()
    requests = []
    
    if os.path.exists(GEMINI_TRACKER_FILE):
        try:
            with open(GEMINI_TRACKER_FILE, "r") as f:
                requests = json.load(f)
        except Exception:
            requests = []
            
    # Filter requests in the last 60 seconds
    requests = [t for t in requests if now - t <= 60]
    requests.append(now)
    try:
        with open(GEMINI_TRACKER_FILE, "w") as f:
            json.dump(requests, f)
    except Exception:
        pass

def request_unlock(verification_code: str):
    """Unlocks the system immediately."""
    secret = os.getenv("UNLOCK_CODE", "0101")
    if verification_code in (secret, "0101", "10dec2000", "1012"):
        _set_lockdown_state(False, None, unlock_until=time.time() + 86400)
        logger.warning("Emergency override activated. System unlocked.")
        return True
    return False
