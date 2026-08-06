import subprocess
import os
import time
import shutil
import tempfile
import logging
import pandas as pd
from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, Depends, Form
from pydantic import BaseModel
from app.utils.enricher_state import get_enricher_state, set_enricher_state
from app.services.auth_service import get_current_user_from_request
from app.models.auth_models import User
# from app.services.parquet_writer import write_to_parquet

router = APIRouter()
logger = logging.getLogger("system")

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

@router.post("/inject-data")
def inject_data(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    deduplicate: bool = Form(True),
    current_user: User = Depends(get_current_user_from_request)
):
    """
    Hidden admin endpoint to inject data directly into Parquet, zero Postgres egress.
    """
    if not current_user.role or current_user.role.name.lower() not in ('admin', 'superadmin'):
        raise HTTPException(status_code=403, detail="Forbidden")
        
    try:
        # Save temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
            
        def _process_injection(path: str, dedup: bool):
            try:
                # Call the CLI script via subprocess
                script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scripts", "parquet_injector.py")
                cmd = ["python", script_path, "--source", path, "--upload"]
                if dedup:
                    cmd.append("--deduplicate")
                
                logger.info(f"Running injection: {' '.join(cmd)}")
                subprocess.run(cmd, check=True)
            except Exception as e:
                logger.error(f"Injection failed: {e}")
            finally:
                if os.path.exists(path):
                    os.remove(path)
                    
        background_tasks.add_task(_process_injection, tmp_path, deduplicate)
        return {"status": "accepted", "message": "Injection task queued successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
