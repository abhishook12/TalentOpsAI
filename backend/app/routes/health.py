import os
import psutil
import requests
import logging
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from ..database import get_db
from ..config import ENV as APP_ENV
from ..services.auth_service import get_current_user_from_request

router = APIRouter()
logger = logging.getLogger("talentops.health")

def get_disk_usage():
    try:
        usage = psutil.disk_usage('/')
        return {"total_gb": round(usage.total / (1024**3), 2), "used_gb": round(usage.used / (1024**3), 2), "free_gb": round(usage.free / (1024**3), 2), "percent": usage.percent}
    except Exception as e:
        return {"error": str(e)}

def get_memory_usage():
    try:
        mem = psutil.virtual_memory()
        return {"total_gb": round(mem.total / (1024**3), 2), "available_gb": round(mem.available / (1024**3), 2), "percent": mem.percent}
    except Exception as e:
        return {"error": str(e)}

import time

def check_outlook_bridge(db: Session, current_user_id: int):
    try:
        from ..models.auth_models import UserBridgeStatus
        import datetime
        status_record = db.query(UserBridgeStatus).filter(UserBridgeStatus.user_id == current_user_id).first()
        if not status_record:
            return {"status": "unhealthy", "error": "No bridge status recorded."}
        
        if not status_record.last_heartbeat:
            return {"status": "unhealthy", "error": "No heartbeat received yet."}
            
        time_diff = (datetime.datetime.utcnow() - status_record.last_heartbeat).total_seconds()
        if time_diff < 30:
            return {"status": "ok", "message": "Outlook Bridge Connected"}
        else:
            return {"status": "unhealthy", "error": f"Last heartbeat was {int(time_diff)}s ago (expected <30s)"}
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}

@router.get("/outlook")
def health_outlook(db: Session = Depends(get_db), current_user = Depends(get_current_user_from_request)):
    from ..models.auth_models import User
    return check_outlook_bridge(db, current_user.id)

@router.get("/")
@router.get("")
def basic_health(db: Session = Depends(get_db)):
    """Primary load balancer health check."""
    return system_health(db)

@router.get("/system")
def system_health(db: Session = Depends(get_db)):
    """Comprehensive system health check for infrastructure monitoring."""
    health_data = {
        "status": "healthy",
        "environment": APP_ENV,
        "components": {}
    }
    
    # Check Database
    try:
        db.execute(text("SELECT 1"))
        health_data["components"]["database"] = {"status": "healthy", "message": "Connected"}
    except Exception as e:
        health_data["components"]["database"] = {"status": "unhealthy", "error": str(e)}
        health_data["status"] = "degraded"
        logger.error(f"Database health check failed: {e}")

    # Check System Resources
    disk = get_disk_usage()
    health_data["components"]["disk"] = disk
    if disk.get("percent", 0) > 90:
        health_data["status"] = "warning"
        logger.warning(f"Disk usage critically high: {disk.get('percent')}%")

    memory = get_memory_usage()
    health_data["components"]["memory"] = memory
    if memory.get("percent", 0) > 90:
        health_data["status"] = "warning"
        logger.warning(f"Memory usage critically high: {memory.get('percent')}%")
        
    return health_data
