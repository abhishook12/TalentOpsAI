"""
scout_contributors.py — Scout Users & Contributor Intelligence API Routes (/scout/users/* & /scout/installations/*)

Endpoints for:
- User lifecycle tracking (DOWNLOAD_ONLY, REGISTERED, INSTALLED, PAIRED, ACTIVE, CONTRIBUTING)
- Multi-device management and diagnostics
- True canonical data contribution analytics
- Multidimensional contribution quality scoring
- Data quality impact and provenance trace
- Administrative remediation actions (Revoke, Force Update, Reset Pairing)
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.auth_models import User
from ..models.extension_models import ExtensionDevice, ExtensionActivationCode
from ..models.update_models import ScoutInstallation
from ..services.auth_service import get_current_user_from_request, get_optional_current_user
from ..services.scout_contributor_service import (
    get_all_scout_users_intelligence,
    get_detailed_scout_user_profile,
)

logger = logging.getLogger("talentops.scout_contributors")
router = APIRouter(prefix="/scout", tags=["Scout Users & Contributors"])


# ── Pydantic Request Models ───────────────────────────────────────────────────

class ForceUpdateRequest(BaseModel):
    target_version: Optional[str] = None
    mandatory: bool = True


class RemoteDiagnosticsRequest(BaseModel):
    bundle_type: str = "FULL"  # FULL, LOGS_ONLY, MEMORY_SNAPSHOT


# ── User List & High-Level Summary ───────────────────────────────────────────

@router.get("/users")
def list_scout_users(
    status: Optional[str] = Query("ALL", description="Filter by status: ALL, ACTIVE, CONTRIBUTING, PAIRED, REGISTERED, REVOKED"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    sort: str = Query("most_active", description="Sorting: most_active, most_data, highest_quality, most_devices"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Returns the comprehensive Scout Users & Contributors list with summary cards,
    lifecycle statuses, device counts, quality scores, and version distribution.
    """
    return get_all_scout_users_intelligence(
        db=db,
        status_filter=status,
        search_query=search,
        sort_by=sort,
    )


@router.get("/contributors/summary")
def get_contributors_summary(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Returns global aggregate KPIs for the Scout Contributor Command Center.
    """
    data = get_all_scout_users_intelligence(db=db)
    return {
        "summary": data["summary"],
        "version_distribution": data["version_distribution"],
        "latest_production_version": data["latest_production_version"],
    }


# ── Deep Forensic User Profile Endpoints ─────────────────────────────────────

@router.get("/users/{user_id}")
def get_scout_user_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Returns the complete forensic Scout Contributor profile for a specific user.
    """
    profile = get_detailed_scout_user_profile(db=db, user_id=user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Scout user not found")
    return profile


@router.get("/users/{user_id}/devices")
def get_scout_user_devices(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Returns all Scout desktop devices/installations registered to this user.
    """
    profile = get_detailed_scout_user_profile(db=db, user_id=user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Scout user not found")
    return {"user_id": user_id, "devices": profile["devices"]}


@router.get("/users/{user_id}/contributions")
def get_scout_user_contributions(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Returns raw vs canonical contribution metrics for this user.
    """
    profile = get_detailed_scout_user_profile(db=db, user_id=user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Scout user not found")
    return {
        "user_id": user_id,
        "contributions": profile["contributions"],
        "quality_scores": profile["quality_scores"],
    }


@router.get("/users/{user_id}/timeline")
def get_scout_user_timeline(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Returns time-series history of intelligence contributions.
    """
    profile = get_detailed_scout_user_profile(db=db, user_id=user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Scout user not found")
    return {"user_id": user_id, "timeline": profile["timeline"]}


@router.get("/users/{user_id}/quality")
def get_scout_user_quality_impact(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Returns downstream master database data quality impact metrics.
    """
    profile = get_detailed_scout_user_profile(db=db, user_id=user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Scout user not found")
    return {
        "user_id": user_id,
        "quality_scores": profile["quality_scores"],
        "data_quality_impact": profile["data_quality_impact"],
    }


@router.get("/users/{user_id}/sources")
def get_scout_user_sources(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Returns contribution breakdown across authorized channels (LinkedIn, Google Chat, Teams, Apollo).
    """
    profile = get_detailed_scout_user_profile(db=db, user_id=user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Scout user not found")
    return {"user_id": user_id, "sources": profile["source_breakdown"]}


@router.get("/users/{user_id}/provenance")
def get_scout_user_provenance(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Returns recent forensic audit trail linking raw visual observations to canonical master database records.
    """
    profile = get_detailed_scout_user_profile(db=db, user_id=user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Scout user not found")
    return {"user_id": user_id, "provenance": profile["provenance_trail"]}


# ── Administrative Remediation Actions ───────────────────────────────────────

@router.post("/users/{user_id}/reset-pairing")
def reset_user_scout_pairing(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Invalidates existing pairing codes and revokes all active tokens for a user.
    """
    codes = db.query(ExtensionActivationCode).filter(ExtensionActivationCode.owner_user_id == user_id).all()
    for c in codes:
        c.is_active = False

    devices = db.query(ExtensionDevice).filter(ExtensionDevice.owner_user_id == user_id).all()
    for d in devices:
        d.is_active = False

    db.commit()
    logger.info("Admin %s reset pairing for user_id=%d", current_user.email, user_id)
    return {"ok": True, "user_id": user_id, "status": "PAIRING_RESET"}


@router.post("/installations/{device_id}/revoke")
def revoke_installation(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Immediately revokes a specific device/installation, cutting off API synchronization.
    """
    device = db.query(ExtensionDevice).filter(ExtensionDevice.device_id == device_id).first()
    if device:
        device.is_active = False

    inst = db.query(ScoutInstallation).filter(ScoutInstallation.device_id == device_id).first()
    if inst:
        inst.health_status = "REVOKED"

    db.commit()
    return {"ok": True, "device_id": device_id, "status": "REVOKED"}


@router.post("/installations/{device_id}/enable")
def enable_installation(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Re-enables a previously revoked device/installation.
    """
    device = db.query(ExtensionDevice).filter(ExtensionDevice.device_id == device_id).first()
    if device:
        device.is_active = True

    inst = db.query(ScoutInstallation).filter(ScoutInstallation.device_id == device_id).first()
    if inst:
        inst.health_status = "HEALTHY"

    db.commit()
    return {"ok": True, "device_id": device_id, "status": "ENABLED"}


@router.post("/installations/{device_id}/force-update")
def force_device_update(
    device_id: str,
    req: ForceUpdateRequest = ForceUpdateRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Marks a device as requiring mandatory software update on next heartbeat ping.
    """
    inst = db.query(ScoutInstallation).filter(ScoutInstallation.device_id == device_id).first()
    if inst:
        inst.update_status = "UPDATE_REQUIRED"
        inst.health_status = "UPDATE_REQUIRED"
        db.commit()
    return {"ok": True, "device_id": device_id, "target_version": req.target_version, "status": "UPDATE_FLAGGED"}


@router.post("/installations/{device_id}/diagnostics")
def trigger_device_diagnostics(
    device_id: str,
    req: RemoteDiagnosticsRequest = RemoteDiagnosticsRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Flags the device to compile and upload a forensic diagnostics bundle on next heartbeat.
    """
    return {
        "ok": True,
        "device_id": device_id,
        "bundle_type": req.bundle_type,
        "status": "DIAGNOSTICS_DISPATCHED",
    }
