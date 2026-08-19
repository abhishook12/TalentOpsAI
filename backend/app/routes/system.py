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
from app.services.auth_service import get_current_user_from_request, require_admin
from app.models.auth_models import User
# from app.services.parquet_writer import write_to_parquet

router = APIRouter()
logger = logging.getLogger("system")

class ControlRequest(BaseModel):
    action: str  # "start", "stop", "pause"

# Store the subprocess globally if we spawn it from here
enricher_process = None

@router.get("/enricher/status")
def get_status(admin: User = Depends(require_admin)):
    from app.services.enrichment_service import enrichment_engine
    return enrichment_engine.get_status()

@router.post("/enricher/control")
def control_enricher(req: ControlRequest, admin: User = Depends(require_admin)):
    from app.services.enrichment_service import enrichment_engine
    
    action = req.action.lower()
    if action == "start":
        return enrichment_engine.start()
    elif action == "pause":
        return enrichment_engine.pause()
    elif action == "resume":
        return enrichment_engine.resume()
    elif action == "stop":
        return enrichment_engine.stop()
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action}")

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

@router.get("/mx-stats")
def get_mx_stats(current_user: User = Depends(get_current_user_from_request)):
    """Return live metrics from the DNS MX domain registry cache."""
    registry_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mx_domain_registry.json")
    if not os.path.exists(registry_path):
        return {"status": "uninitialized", "total_domains": 0, "deliverable_domains": 0}
    try:
        import json
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
        total = len(registry)
        deliverable = sum(1 for v in registry.values() if v.get("valid", False) or v.get("is_deliverable", False))
        return {
            "status": "ready",
            "total_domains": total,
            "deliverable_domains": deliverable,
            "deliverability_rate": f"{(deliverable/total*100):.1f}%" if total > 0 else "0%"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read MX registry: {e}")

@router.post("/refresh-mx-deliverability")
def trigger_mx_refresh(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_from_request)
):
    """Trigger background DNS MX validation worker."""
    if not current_user.role or current_user.role.name.lower() not in ('admin', 'superadmin'):
        raise HTTPException(status_code=403, detail="Forbidden")

    def _run_mx_worker():
        try:
            worker_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "mx_validation_worker.py")
            logger.info("Starting background MX validation worker...")
            subprocess.run(["python", worker_path], check=True)
            logger.info("Background MX validation worker finished successfully.")
        except Exception as e:
            logger.error(f"MX validation worker failed: {e}")

    background_tasks.add_task(_run_mx_worker)
    return {"status": "queued", "message": "DNS MX Pre-Validation background task dispatched."}
