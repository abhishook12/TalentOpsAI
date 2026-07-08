import json
import os
import time
from threading import Lock
import logging

logger = logging.getLogger("talentops.apikey")

# The path where we store key states
KEYS_FILE = os.path.join(os.path.dirname(__file__), '..', 'api_keys_pool.json')

class TavilyKeyManager:
    _instance = None
    _lock = Lock()

    def __init__(self):
        self.keys_data = []
        self.load_keys()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = TavilyKeyManager()
        return cls._instance

    def load_keys(self):
        if os.path.exists(KEYS_FILE):
            try:
                with open(KEYS_FILE, 'r') as f:
                    self.keys_data = json.load(f)
            except Exception as e:
                logger.error(f"Error loading API keys: {e}")
                self.keys_data = []
        else:
            self.keys_data = []

    def save_keys(self):
        with open(KEYS_FILE, 'w') as f:
            json.dump(self.keys_data, f, indent=4)

    def add_keys(self, new_keys):
        """Adds new keys if they don't already exist."""
        with self._lock:
            existing_keys = {k["api_key"] for k in self.keys_data}
            added = 0
            for key in new_keys:
                key = key.strip().strip('"').strip("'")
                if key and key not in existing_keys:
                    # Mask the key for logging/UI
                    prefix = key[:12] if len(key) > 15 else key[:4]
                    suffix = key[-4:] if len(key) > 15 else ""
                    self.keys_data.append({
                        "api_key": key,
                        "masked": f"{prefix}...{suffix}",
                        "status": "ACTIVE",
                        "usage_count": 0,
                        "last_used_at": None,
                        "cooldown_until": None,
                        "added_at": time.time()
                    })
                    existing_keys.add(key)
                    added += 1
            if added > 0:
                self.save_keys()
            return added

    def get_active_key(self):
        """Returns the next available active key."""
        with self._lock:
            now = time.time()
            # First, try to revive any keys whose cooldown has expired
            for k in self.keys_data:
                if k["status"] == "COOLDOWN" and k["cooldown_until"] and now > k["cooldown_until"]:
                    k["status"] = "ACTIVE"
                    k["cooldown_until"] = None

            # Find active keys
            active_keys = [k for k in self.keys_data if k["status"] == "ACTIVE"]
            
            if not active_keys:
                # If no active keys, find the one with the shortest cooldown
                cooldown_keys = [k for k in self.keys_data if k["status"] == "COOLDOWN" and k["cooldown_until"]]
                if cooldown_keys:
                    shortest = min(cooldown_keys, key=lambda x: x["cooldown_until"])
                    time_left = int(shortest['cooldown_until'] - now)
                    raise Exception(f"All API keys exhausted. Next key available in {time_left} seconds.")
                raise Exception("No API keys available in the pool!")

            # Pick the key with the least usage to balance load
            best_key = min(active_keys, key=lambda x: x["usage_count"])
            
            return best_key["api_key"]

    def record_usage(self, api_key):
        """Increments usage counter for a key."""
        with self._lock:
            for k in self.keys_data:
                if k["api_key"] == api_key:
                    k["usage_count"] += 1
                    k["last_used_at"] = time.time()
                    break
            self.save_keys()

    def mark_exhausted(self, api_key):
        """Marks a key as exhausted (out of credits)."""
        with self._lock:
            for k in self.keys_data:
                if k["api_key"] == api_key:
                    k["status"] = "EXHAUSTED"
                    break
            self.save_keys()

    def mark_rate_limited(self, api_key, cooldown_seconds=3600):
        """Marks a key as rate-limited, putting it on cooldown."""
        with self._lock:
            for k in self.keys_data:
                if k["api_key"] == api_key:
                    k["status"] = "COOLDOWN"
                    k["cooldown_until"] = time.time() + cooldown_seconds
                    break
            self.save_keys()

    def get_stats(self):
        """Returns stats of all keys for dashboard viewing."""
        with self._lock:
            # Return safe copy without full keys if desired, or just raw data
            return self.keys_data

key_manager = TavilyKeyManager.get_instance()
