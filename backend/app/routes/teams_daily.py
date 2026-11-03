"""
teams_daily.py — FastAPI endpoints for Daily 5-Day Teams Background Collection Engine
=====================================================================================
"""

from fastapi import APIRouter, Depends, Query, Body
from typing import Dict, Any, Optional

from ..services.teams_daily_collection_service import teams_daily_service
from ..services.auth_service import get_current_user_from_request
from ..models.auth_models import User

router = APIRouter(prefix="/teams", tags=["Teams Daily Collection"])


@router.get("/daily-status")
def get_daily_teams_status():
    """
    Returns the real-time status of the Daily 5-Day Teams Collection Engine:
    - Today's date and weekday classification (Monday-Friday)
    - Active running status and target duration (2.0 hours)
    - Elapsed and remaining seconds
    - Total messages scanned, staged, and promoted
    - Last person collected
    """
    return teams_daily_service.get_status()


@router.post("/daily-trigger")
def trigger_daily_teams_collection(
    force: bool = Query(False, description="Bypass weekday or already-run guard"),
    duration_seconds: int = Query(7200, description="Collection window duration in seconds (default 7200 = 2 hours)"),
    current_user: User = Depends(get_current_user_from_request)
):
    """
    Triggers the start of the 2-hour daily Teams background collection.
    By default adheres strictly to the 5 working days rule (Mon-Fri) and runs once per day.
    """
    return teams_daily_service.start_collection(
        duration_seconds=duration_seconds,
        force=force,
        source=f"API_USER_{current_user.email}"
    )


@router.post("/daily-stop")
def stop_daily_teams_collection(
    current_user: User = Depends(get_current_user_from_request)
):
    """
    Gracefully stops the active collection session and triggers data synchronization.
    """
    return teams_daily_service.stop_collection()
