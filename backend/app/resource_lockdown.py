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

# 90% Limit Thresholds (Override: 450MB DB, 900MB Storage)
MAX_DB_SIZE_MB = 450.0  # 90% of 500MB limit
MAX_STORAGE_SIZE_MB = 900.0 # 90% of 1000MB limit
MAX_MEMORY_MB = 250.0   # 70% of 358 MB
MAX_GEMINI_RPM = 7      # 70% of 10 RPM

class ResourceLockdownException(Exception):
    pass

def _get_lockdown_state() -> dict:
    if not os.path.exists(LOCKDOWN_FILE):
        return {"is_locked": False, "reason": None, "timestamp": None, "unlock_until": None}
    try:
        with open(LOCKDOWN_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"is_locked": False, "reason": None, "timestamp": None, "unlock_until": None}

def _set_lockdown_state(is_locked: bool, reason: Optional[str] = None, unlock_until: Optional[float] = None):
    state = {
        "is_locked": is_locked,
        "reason": reason,
        "timestamp": time.time() if is_locked else None,
        "unlock_until": unlock_until
    }
    with open(LOCKDOWN_FILE, "w") as f:
        json.dump(state, f)
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
    state = _get_lockdown_state()
    if state.get("is_locked"):
        raise ResourceLockdownException(f"System is in Emergency Lockdown: {state.get('reason')}")

_last_limit_check_time: float = 0.0
_LIMIT_CHECK_INTERVAL: float = 30.0  # Check DB/memory at most once every 30 seconds

def check_system_limits():
    """Checks DB size and memory. If thresholds breached, triggers lockdown.
    Results are cached for 30s to avoid hammering DB on every request."""
    global _last_limit_check_time
    if is_locked_down():
        return

    now = time.time()
    if now - _last_limit_check_time < _LIMIT_CHECK_INTERVAL:
        return  # Skip — checked recently, all was fine
    _last_limit_check_time = now

    # Check Memory
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    mem_mb = mem_info.rss / 1048576.0
    if mem_mb >= MAX_MEMORY_MB:
        _set_lockdown_state(True, f"Memory exceeded 70% threshold ({mem_mb:.2f} MB / {MAX_MEMORY_MB} MB limit)")
        return

    # Check DB Size & Storage Size
    try:
        from sqlalchemy.orm import Session
        with Session(engine) as db:
            # 1. Check Database Size
            res = db.execute(text("SELECT pg_database_size(current_database()) / 1048576.0")).fetchone()
            db_size_mb = float(res[0]) if res and res[0] else 0.0
            logger.debug(f"[Shield] DB size: {db_size_mb:.1f} MB / {MAX_DB_SIZE_MB} MB limit")
            if db_size_mb >= MAX_DB_SIZE_MB:
                _set_lockdown_state(True, f"Database Size exceeded 90% threshold ({db_size_mb:.2f} MB / {MAX_DB_SIZE_MB} MB limit)")
                return
            
            # 2. Check Storage Size
            try:
                storage_res = db.execute(text("SELECT sum((metadata->>'size')::bigint) FROM storage.objects")).fetchone()
                storage_size_bytes = float(storage_res[0]) if storage_res and storage_res[0] else 0.0
                storage_size_mb = storage_size_bytes / 1048576.0
                logger.debug(f"[Shield] Storage size: {storage_size_mb:.1f} MB / {MAX_STORAGE_SIZE_MB} MB limit")
                if storage_size_mb >= MAX_STORAGE_SIZE_MB:
                    _set_lockdown_state(True, f"Storage Size exceeded 90% threshold ({storage_size_mb:.2f} MB / {MAX_STORAGE_SIZE_MB} MB limit)")
                    return
            except Exception as se:
                logger.debug(f"[Shield] Could not check storage size (likely local SQLite or no storage configured): {se}")
                
    except Exception as e:
        logger.error(f"Failed to check DB limits: {e}")

def track_gemini_call():
    """Tracks Gemini API usage. If > 7 RPM, triggers lockdown."""
    enforce_limits()
    
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
    
    if len(requests) >= MAX_GEMINI_RPM:
        _set_lockdown_state(True, f"Gemini API rate exceeded 70% threshold ({len(requests)} calls in last 60s)")
        raise ResourceLockdownException("Gemini API rate exceeded. Lockdown initiated.")
        
    requests.append(now)
    with open(GEMINI_TRACKER_FILE, "w") as f:
        json.dump(requests, f)

def request_unlock(verification_code: str):
    """Requires the correct birthday/secret code to unlock for 15 minutes."""
    secret = os.getenv("UNLOCK_CODE", "0101")
    if verification_code == secret:
        # Unlock for 15 minutes (900 seconds)
        _set_lockdown_state(False, None, unlock_until=time.time() + 900)
        logger.warning(f"Emergency override activated. System unlocked for 15 minutes.")
        return True
    return False
