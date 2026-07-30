import subprocess
import os
import time
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from app.utils.enricher_state import get_enricher_state, set_enricher_state

router = APIRouter()

class ControlRequest(BaseModel):
    action: str  # "start", "stop", "pause"

# Store the subprocess globally if we spawn it from here
enricher_process = None

@router.get("/enricher/status")
def get_status():
    state = get_enricher_state()
    # Check if process is actually running if state says 'running' or 'paused'
    # For simplicity, we just rely on state.last_active or state itself.
    if state["status"] in ["running", "paused"]:
        if time.time() - state["last_active"] > 120:
            # Hasn't updated state in 2 minutes, probably dead
            state = set_enricher_state({"status": "stopped"})
    return state

@router.post("/enricher/control")
def control_enricher(req: ControlRequest):
    global enricher_process
    
    action = req.action.lower()
    if action not in ["start", "stop", "pause"]:
        raise HTTPException(status_code=400, detail="Invalid action")
        
    state = get_enricher_state()
    
    if action == "start":
        if state["status"] == "running":
            return {"message": "Already running", "state": state}
            
        set_enricher_state({"status": "running"})
        
        # If it's completely stopped, we might need to spawn it
        if state["status"] == "stopped":
            script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scripts", "background_enricher.py")
            enricher_process = subprocess.Popen(["python", script_path])
            
    elif action == "pause":
        set_enricher_state({"status": "paused"})
        
    elif action == "stop":
        set_enricher_state({"status": "stopped"})
        # In a real scenario we might kill the process, but the loop checks state and exits
        
    return {"message": f"Action {action} applied successfully", "state": get_enricher_state()}
