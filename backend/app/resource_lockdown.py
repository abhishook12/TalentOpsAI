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

# 70% Limit Thresholds (Override: 400MB soft limit, 450MB hard limit)
MAX_DB_SIZE_MB = 400.0  # Rule 8 explicit limit overridden by user to 400MB
MAX_MEMORY_MB = 250.0   # 70% of 358 MB
MAX_GEMINI_RPM = 7      # 70% of 10 RPM

class ResourceLockdownException(Exception):
    pass

def _get_lockdown_state() -> dict:
    if not os.path.exists(LOCKDOWN_FILE):
        return {"is_locked": False, "reason": None, "timestamp": None}
    try:
        with open(LOCKDOWN_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"is_locked": False, "reason": None, "timestamp": None}

def _set_lockdown_state(is_locked: bool, reason: Optional[str] = None):
    state = {
        "is_locked": is_locked,
        "reason": reason,
        "timestamp": time.time() if is_locked else None
    }
    with open(LOCKDOWN_FILE, "w") as f:
        json.dump(state, f)
    if is_locked:
        logger.error(f"!!! EMERGENCY RESOURCE LOCKDOWN INITIATED: {reason} !!!")
    else:
        logger.info("System unlocked successfully.")

def is_locked_down() -> bool:
    return _get_lockdown_state().get("is_locked", False)

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

    # Check DB Size
    try:
        from sqlalchemy.orm import Session
        with Session(engine) as db:
            res = db.execute(text("SELECT pg_database_size(current_database()) / 1048576.0")).fetchone()
            db_size_mb = float(res[0]) if res and res[0] else 0.0
            logger.debug(f"[Shield] DB size: {db_size_mb:.1f} MB / {MAX_DB_SIZE_MB} MB limit")
            if db_size_mb >= MAX_DB_SIZE_MB:
                _set_lockdown_state(True, f"Database Size exceeded 70% threshold ({db_size_mb:.2f} MB / {MAX_DB_SIZE_MB} MB limit)")
                return
    except Exception as e:
        logger.error(f"Failed to check DB size: {e}")

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
    """Requires 'START' or 'UNBLOCK' exactly 3 times from the unlock script."""
    # This is normally handled by the script that calls this.
    pass
