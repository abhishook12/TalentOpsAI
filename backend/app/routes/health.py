import os
import psutil
import requests
import logging
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from ..database import get_db
from ..config import ENV as APP_ENV

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

def check_outlook_bridge():
    try:
        response = requests.get("http://localhost:1337/health", timeout=2)
        if response.status_code == 200:
            return response.json()
        return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}

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

    # Check Outlook Bridge
    bridge_health = check_outlook_bridge()
    health_data["components"]["outlook_bridge"] = bridge_health
    if bridge_health.get("status") not in ["healthy", "ok"]:
        health_data["status"] = "degraded"
        logger.error(f"Outlook Bridge health check failed: {bridge_health}")

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
