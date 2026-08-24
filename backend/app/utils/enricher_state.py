import os
import json
import time

STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "enricher_state.json")

def get_enricher_state():
    if not os.path.exists(STATE_FILE):
        return {
            "status": "stopped", # running, paused, stopped
            "records_processed": 0,
            "last_active": 0,
            "success_count": 0
        }
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "status": "stopped",
            "records_processed": 0,
            "last_active": 0,
            "success_count": 0
        }

def set_enricher_state(new_state):
    state = get_enricher_state()
    state.update(new_state)
    state["last_active"] = time.time()
    tmp_file = f"{STATE_FILE}.tmp"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4)
        os.replace(tmp_file, STATE_FILE)
    except Exception:
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=4)
        except Exception:
            pass
    return state

