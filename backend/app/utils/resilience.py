"""
Self-Healing Circuit Breaker & SQLite Dead-Letter Queue Shield - TalentOpsAI
Intercepts transaction crashes mid-air and routes orphaned payloads to offline DLQ.
"""
import sqlite3
import time
import json
import logging
from functools import wraps
import os
from typing import Callable, Any

logger = logging.getLogger("talentops.resilience")

DLQ_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dlq.db")

def _init_dlq():
    try:
        conn = sqlite3.connect(DLQ_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dead_letter_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                func_name TEXT,
                args_repr TEXT,
                kwargs_repr TEXT,
                error_message TEXT,
                created_at REAL,
                resolved INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"[DLQ] Error initializing DLQ table: {e}")

_init_dlq()

def log_to_dlq(func_name: str, args: tuple, kwargs: dict, error_msg: str):
    try:
        conn = sqlite3.connect(DLQ_PATH)
        conn.execute(
            "INSERT INTO dead_letter_queue (func_name, args_repr, kwargs_repr, error_message, created_at) VALUES (?, ?, ?, ?, ?)",
            (func_name, repr(args), repr(kwargs), str(error_msg), time.time())
        )
        conn.commit()
        conn.close()
        logger.warning(f"[DLQ] Payload safely quarantined in Dead-Letter Queue for {func_name}!")
    except Exception as e:
        logger.error(f"[DLQ] Failed to write to DLQ: {e}")

def circuit_breaker(max_retries: int = 3, backoff: float = 1.5, fallback_factory: Callable = None):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempt = 0
            current_delay = 0.5
            while attempt < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    logger.warning(f"[SHIELD] {func.__name__} failed (Attempt {attempt}/{max_retries}): {e}")
                    if attempt >= max_retries:
                        log_to_dlq(func.__name__, args, kwargs, str(e))
                        if fallback_factory:
                            logger.info(f"[SHIELD] Executing fallback factory for {func.__name__}...")
                            return fallback_factory(*args, **kwargs)
                        raise
                    time.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator
