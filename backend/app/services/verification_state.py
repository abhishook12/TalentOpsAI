import os
import json
import logging
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
STATE_FILE = os.path.join(DATA_DIR, 'verification_state.json')

class VerificationState:
    def __init__(self):
        self._lock = threading.RLock()
        
        # Default state
        self.state = {
            "last_completed_domain": None,
            "last_completed_recruiter_id": 0,
            "total_processed": 0,
            "total_verified": 0,
            "total_likely_valid": 0,
            "total_needs_monitoring": 0,
            "total_suspicious": 0,
            "total_invalid": 0,
            "total_pending": 0,
            "batch_number": 0,
            "started_at": None,
            "last_batch_at": None,
            "current_domain": None,
            "current_batch_size": 0,
            "speed_emails_per_hour": 0.0,
            "is_running": False,
            "is_paused": False,
            "completed_domains": [],
            "retry_queue": [],
            "errors": [],
            "batch_log": []
        }
        self.load()

    def load(self):
        with self._lock:
            if os.path.exists(STATE_FILE):
                try:
                    with open(STATE_FILE, 'r') as f:
                        saved_state = json.load(f)
                        self.state.update(saved_state)
                        
                        # Reset transient runtime flags
                        self.state["is_running"] = False
                        self.state["is_paused"] = False
                except Exception as e:
                    logger.error(f"Failed to load verification state: {e}")

    def save(self):
        with self._lock:
            try:
                os.makedirs(DATA_DIR, exist_ok=True)
                tmp_file = f"{STATE_FILE}.tmp"
                with open(tmp_file, 'w') as f:
                    json.dump(self.state, f, indent=2)
                os.replace(tmp_file, STATE_FILE)
            except Exception as e:
                logger.error(f"Failed to save verification state: {e}")

    def mark_email_processed(self, status: str, confidence: int):
        with self._lock:
            self.state["total_processed"] += 1
            if confidence >= 90:
                self.state["total_verified"] += 1
            elif confidence >= 70:
                self.state["total_likely_valid"] += 1
            elif confidence >= 50:
                self.state["total_needs_monitoring"] += 1
            elif confidence >= 30:
                self.state["total_suspicious"] += 1
            else:
                self.state["total_invalid"] += 1

    def mark_batch_complete(self, domain: str, count: int, duration: float):
        with self._lock:
            now_iso = datetime.now(timezone.utc).isoformat()
            self.state["last_completed_domain"] = domain
            self.state["batch_number"] += 1
            self.state["last_batch_at"] = now_iso
            
            if domain not in self.state["completed_domains"]:
                self.state["completed_domains"].append(domain)
                
            # Update rolling speed (exponential moving average)
            current_speed = (count / duration) * 3600 if duration > 0 else 0
            if self.state["speed_emails_per_hour"] == 0:
                self.state["speed_emails_per_hour"] = current_speed
            else:
                self.state["speed_emails_per_hour"] = (self.state["speed_emails_per_hour"] * 0.8) + (current_speed * 0.2)
                
            log_entry = {
                "batch_number": self.state["batch_number"],
                "domain": domain,
                "count": count,
                "duration_seconds": round(duration, 2),
                "timestamp": now_iso
            }
            
            self.state["batch_log"].insert(0, log_entry)
            if len(self.state["batch_log"]) > 100:
                self.state["batch_log"].pop()
                
        self.save()
        
    def add_error(self, message: str):
        with self._lock:
            now_iso = datetime.now(timezone.utc).isoformat()
            self.state["errors"].insert(0, {"timestamp": now_iso, "message": message})
            if len(self.state["errors"]) > 50:
                self.state["errors"].pop()

    def get_progress(self) -> dict:
        with self._lock:
            return dict(self.state)

    def reset(self):
        with self._lock:
            self.state = {
                "last_completed_domain": None,
                "last_completed_recruiter_id": 0,
                "total_processed": 0,
                "total_verified": 0,
                "total_likely_valid": 0,
                "total_needs_monitoring": 0,
                "total_suspicious": 0,
                "total_invalid": 0,
                "total_pending": 0,
                "batch_number": 0,
                "started_at": None,
                "last_batch_at": None,
                "current_domain": None,
                "current_batch_size": 0,
                "speed_emails_per_hour": 0.0,
                "is_running": False,
                "is_paused": False,
                "completed_domains": [],
                "retry_queue": [],
                "errors": [],
                "batch_log": []
            }
            if os.path.exists(STATE_FILE):
                try:
                    os.remove(STATE_FILE)
                except:
                    pass

verification_state = VerificationState()
