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
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
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
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)
    return state
