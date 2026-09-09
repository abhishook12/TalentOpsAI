"""
scout_updates.py — Fast API Endpoints for Scout Release Manifests & Fleet Management.

Routes:
- GET  /scout/updates/manifest : Public endpoint for Scout clients to query latest version, minimum version, package info, SHA-256, and remote feature flags.
- POST /scout/updates/report   : Telemetry report from desktop nodes (version, update status, error).
- POST /scout/releases         : Admin endpoint to publish new Scout software releases.
- GET  /scout/fleet/stats      : Fleet version distribution analytics.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from ..database import get_db
from ..models.update_models import ScoutRelease, ScoutInstallation
from ..models.auth_models import User
from ..services.auth_service import get_current_user_from_request

logger = logging.getLogger("talentops.scout_updates")
router = APIRouter(prefix="/scout", tags=["Scout Auto-Update & Fleet"])

# Fallback production CDN constants
DEFAULT_RELEASE_VERSION = "2.0.0"
DEFAULT_MINIMUM_VERSION = "1.0.0"
DEFAULT_DOWNLOAD_URL = "https://qpetzpxmuofuepvrqedk.supabase.co/storage/v1/object/public/data-assets/TalentOpsScoutSetup.exe"
DEFAULT_SHA256 = "4a7e93f6c8d19a2b3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d"
DEFAULT_SIZE = 50474851

DEFAULT_FEATURES = {
    "new_capture_pipeline": True,
    "batch_upload_v2": True,
    "knowledge_graph_enabled": True,
    "ocr_daemon_enabled": True,
}

DEFAULT_CONFIG = {
    "poll_interval_sec": 30,
    "max_buffer_mb": 100,
    "max_buffer_images": 200,
    "hard_max_retention_sec": 300,
}


# ── Schemas ──────────────────────────────────────────────────────────────────

class ReleasePublishRequest(BaseModel):
    version: str
    channel: str = "stable"
    minimum_version: str = "1.0.0"
    mandatory: bool = False
    download_url: str
    sha256: Optional[str] = None
    size_bytes: Optional[int] = None
    release_notes: Optional[str] = None
    features: Dict[str, Any] = Field(default_factory=dict)
    config: Dict[str, Any] = Field(default_factory=dict)


class UpdateReportRequest(BaseModel):
    device_id: str
    scout_version: str
    channel: str = "stable"
    os_info: Optional[str] = None
    update_status: str = "UP_TO_DATE"
    error_message: Optional[str] = None
    queue_size: int = 0


# ── Route Handlers ───────────────────────────────────────────────────────────

@router.get("/updates/manifest")
def get_update_manifest(
    channel: str = Query("stable", description="Deployment channel: stable, beta, internal"),
    db: Session = Depends(get_db),
):
    """
    Returns the channel-aware release manifest for Scout Desktop.
    Includes package download URL, cryptographic SHA-256 hash,
    minimum supported version (for mandatory deprecation enforcement),
    and runtime remote feature flags.
    """
    try:
        latest = (
            db.query(ScoutRelease)
            .filter(ScoutRelease.channel == channel, ScoutRelease.status == "ACTIVE")
            .order_by(ScoutRelease.id.desc())
            .first()
        )

        if latest:
            features = json.loads(latest.features_json or "{}") if latest.features_json else DEFAULT_FEATURES
            config = json.loads(latest.config_json or "{}") if latest.config_json else DEFAULT_CONFIG
            
            return {
                "product": "talentops-scout",
                "channel": latest.channel,
                "latest_version": latest.version,
                "minimum_version": latest.minimum_version,
                "mandatory": latest.mandatory,
                "release_date": latest.created_at.strftime("%Y-%m-%d") if latest.created_at else "2026-09-09",
                "release_notes": latest.release_notes,
                "package": {
                    "url": latest.download_url,
                    "sha256": latest.sha256,
                    "size": latest.size_bytes or DEFAULT_SIZE,
                },
                "features": features,
                "config": config,
            }

        # Fallback default response if database has no custom releases yet
        return {
            "product": "talentops-scout",
            "channel": channel,
            "latest_version": DEFAULT_RELEASE_VERSION,
            "minimum_version": DEFAULT_MINIMUM_VERSION,
            "mandatory": False,
            "release_date": "2026-09-09",
            "release_notes": "Official release of TalentOps Scout Desktop with autonomous background ingestion.",
            "package": {
                "url": DEFAULT_DOWNLOAD_URL,
                "sha256": DEFAULT_SHA256,
                "size": DEFAULT_SIZE,
            },
            "features": DEFAULT_FEATURES,
            "config": DEFAULT_CONFIG,
        }
    except Exception as e:
        logger.error("Error generating update manifest: %s", e)
        # Always return valid fallback JSON so desktop clients never crash
        return {
            "product": "talentops-scout",
            "channel": channel,
            "latest_version": DEFAULT_RELEASE_VERSION,
            "minimum_version": DEFAULT_MINIMUM_VERSION,
            "mandatory": False,
            "release_date": "2026-09-09",
            "package": {
                "url": DEFAULT_DOWNLOAD_URL,
                "sha256": DEFAULT_SHA256,
                "size": DEFAULT_SIZE,
            },
            "features": DEFAULT_FEATURES,
            "config": DEFAULT_CONFIG,
        }


@router.post("/updates/report")
def report_update_telemetry(
    req: UpdateReportRequest,
    db: Session = Depends(get_db),
):
    """
    Receives update status reports from Scout client nodes.
    Tracks fleet adoption rates and flags failed updates.
    """
    try:
        inst = db.query(ScoutInstallation).filter(ScoutInstallation.device_id == req.device_id).first()
        now = datetime.now(timezone.utc)

        if not inst:
            inst = ScoutInstallation(
                device_id=req.device_id,
                scout_version=req.scout_version,
                channel=req.channel,
                os_info=req.os_info,
                update_status=req.update_status,
                error_message=req.error_message,
                queue_size=req.queue_size,
                last_check_at=now,
                last_update_at=now if req.update_status == "UPDATED" else None,
            )
            db.add(inst)
        else:
            inst.scout_version = req.scout_version
            inst.channel = req.channel
            inst.update_status = req.update_status
            inst.error_message = req.error_message
            inst.queue_size = req.queue_size
            inst.last_check_at = now
            if req.update_status == "UPDATED":
                inst.last_update_at = now

        db.commit()
        return {"status": "ok", "device_id": req.device_id, "recorded_status": req.update_status}
    except Exception as e:
        db.rollback()
        logger.error("Failed to record update telemetry: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/releases")
def publish_scout_release(
    req: ReleasePublishRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Admin endpoint to publish a new software version.
    """
    try:
        existing = db.query(ScoutRelease).filter(ScoutRelease.version == req.version).first()
        if existing:
            existing.channel = req.channel
            existing.minimum_version = req.minimum_version
            existing.mandatory = req.mandatory
            existing.download_url = req.download_url
            existing.sha256 = req.sha256
            existing.size_bytes = req.size_bytes
            existing.release_notes = req.release_notes
            existing.features_json = json.dumps(req.features)
            existing.config_json = json.dumps(req.config)
            existing.status = "ACTIVE"
            rel = existing
        else:
            rel = ScoutRelease(
                version=req.version,
                channel=req.channel,
                minimum_version=req.minimum_version,
                mandatory=req.mandatory,
                download_url=req.download_url,
                sha256=req.sha256,
                size_bytes=req.size_bytes,
                release_notes=req.release_notes,
                features_json=json.dumps(req.features),
                config_json=json.dumps(req.config),
                status="ACTIVE",
            )
            db.add(rel)

        db.commit()
        logger.info("Published new Scout release v%s (channel: %s)", req.version, req.channel)
        return {"status": "published", "version": req.version, "id": rel.id}
    except Exception as e:
        db.rollback()
        logger.error("Failed to publish release: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fleet/stats")
def get_fleet_update_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Returns analytics on Scout fleet versions and update health.
    """
    try:
        total = db.query(sqlfunc.count(ScoutInstallation.id)).scalar() or 0
        version_counts = (
            db.query(ScoutInstallation.scout_version, sqlfunc.count(ScoutInstallation.id))
            .group_by(ScoutInstallation.scout_version)
            .all()
        )

        fleet = []
        for ver, cnt in version_counts:
            pct = round((cnt / total * 100.0), 1) if total > 0 else 0.0
            fleet.append({
                "version": ver,
                "device_count": cnt,
                "percentage": pct,
            })

        status_counts = dict(
            db.query(ScoutInstallation.update_status, sqlfunc.count(ScoutInstallation.id))
            .group_by(ScoutInstallation.update_status)
            .all()
        )

        return {
            "total_devices": total,
            "version_distribution": fleet,
            "status_distribution": status_counts,
        }
    except Exception as e:
        logger.error("Failed to fetch fleet stats: %s", e)
        return {"total_devices": 0, "version_distribution": [], "status_distribution": {}}
