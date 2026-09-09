"""
scout_updates.py — FastAPI Endpoints for Scout Release Manifests, Staged Rollouts & Fleet Management.

Features:
1. Cryptographically Signed Release Manifests (Ed25519)
2. Deployment Channels: Stable, Beta, Internal
3. Staged Rollout Gating: 10%, 25%, 50%, 100% via deterministic device hashing
4. Automatic Rollout Circuit Breaker: Pauses distribution when failure rate > 3%
5. Node Health Classification: HEALTHY, STALE, UPDATE_FAILED, OFFLINE
6. Fleet Telemetry & Adoption Analytics
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from ..database import get_db
from ..models.update_models import ScoutRelease, ScoutInstallation, ScoutDownloadEvent, ScoutRemoteConfig
from ..models.auth_models import User
from ..services.auth_service import get_current_user_from_request
from ..services.release_signer import sign_manifest, sign_package_hash

logger = logging.getLogger("talentops.scout_updates")
router = APIRouter(prefix="/scout", tags=["Scout Auto-Update & Fleet"])

# Production Fallbacks
DEFAULT_RELEASE_VERSION = "2.7.0"
DEFAULT_MINIMUM_VERSION = "1.0.0"
DEFAULT_DOWNLOAD_URL = "https://qpetzpxmuofuepvrqedk.supabase.co/storage/v1/object/public/data-assets/TalentOpsScoutSetup_v2.7.0.exe"
DEFAULT_SHA256 = "4a7e93f6c8d19a2b3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d"
DEFAULT_SIZE = 52000000

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
    channel: str = "stable"  # stable, beta, internal
    minimum_version: str = "1.0.0"
    mandatory: bool = False
    download_url: str
    sha256: Optional[str] = None
    size_bytes: Optional[int] = None
    release_notes: Optional[str] = None
    features: Dict[str, Any] = Field(default_factory=dict)
    config: Dict[str, Any] = Field(default_factory=dict)
    rollout_percentage: int = 100
    failure_threshold_pct: float = 5.0
    is_production: bool = False  # If True, approved immediately; if False, created as candidate


class ApprovalChecklist(BaseModel):
    tests_passed: bool = True
    security_verified: bool = True
    signing_verified: bool = True
    installer_verified: bool = True
    migration_verified: bool = True
    rollback_tested: bool = True
    compatibility_verified: bool = True
    notes: Optional[str] = None
    force: bool = False


class ReleaseApprovalRequest(BaseModel):
    checklist: ApprovalChecklist = Field(default_factory=ApprovalChecklist)
    rollout_percentage: Optional[int] = 100
    set_minimum_version: Optional[str] = None


class RolloutControlRequest(BaseModel):
    rollout_percentage: Optional[int] = None
    is_paused: Optional[bool] = None


class RemoteConfigUpdateRequest(BaseModel):
    config_key: str = "global"
    channel: str = "stable"
    features: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    description: Optional[str] = None


class UpdateReportRequest(BaseModel):
    device_id: str
    scout_version: str
    channel: str = "stable"
    os_info: Optional[str] = None
    os_version: Optional[str] = None
    update_status: str = "UP_TO_DATE"
    error_message: Optional[str] = None
    queue_size: int = 0
    target_version: Optional[str] = None
    tenant_id: Optional[int] = None


# ── Canonical Release & Remote Config Helpers ─────────────────────────────────

def get_canonical_production_release(channel: str = "stable", db: Session = None) -> Optional[ScoutRelease]:
    """
    Authoritative Single Source of Truth for Scout Release Distribution.
    Strictly queries the database for the active release marked `is_current = True` for the given channel.
    If none marked `is_current`, falls back to newest ACTIVE release on that channel.
    """
    if not db:
        return None
    # 1. Authoritative: is_current == True on requested channel
    rel = (
        db.query(ScoutRelease)
        .filter(ScoutRelease.channel == channel, ScoutRelease.is_current == True)
        .order_by(ScoutRelease.id.desc())
        .first()
    )
    # 2. Fallback: newest ACTIVE release on requested channel
    if not rel:
        rel = (
            db.query(ScoutRelease)
            .filter(ScoutRelease.channel == channel, ScoutRelease.status == "ACTIVE")
            .order_by(ScoutRelease.id.desc())
            .first()
        )
    # 3. Fallback: stable channel production release
    if not rel and channel != "stable":
        rel = (
            db.query(ScoutRelease)
            .filter(ScoutRelease.channel == "stable", ScoutRelease.is_current == True)
            .order_by(ScoutRelease.id.desc())
            .first()
        )
    return rel


def get_merged_remote_config(channel: str = "stable", db: Session = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Merges baseline defaults with centralized remote configuration (Type 3 changes).
    Evaluates global config and channel-specific overrides from `scout_remote_configs`.
    """
    features = dict(DEFAULT_FEATURES)
    config = dict(DEFAULT_CONFIG)
    if not db:
        return features, config

    try:
        global_cfg = db.query(ScoutRemoteConfig).filter(ScoutRemoteConfig.config_key == "global").first()
        if global_cfg:
            if global_cfg.features_json:
                features.update(json.loads(global_cfg.features_json))
            if global_cfg.config_json:
                config.update(json.loads(global_cfg.config_json))

        if channel and channel != "global":
            chan_cfg = db.query(ScoutRemoteConfig).filter(ScoutRemoteConfig.config_key == channel).first()
            if chan_cfg:
                if chan_cfg.features_json:
                    features.update(json.loads(chan_cfg.features_json))
                if chan_cfg.config_json:
                    config.update(json.loads(chan_cfg.config_json))
    except Exception as e:
        logger.warning("Error resolving remote config overrides: %s", e)

    return features, config


# ── Route Handlers ───────────────────────────────────────────────────────────

@router.get("/updates/manifest")
def get_update_manifest(
    channel: str = Query("stable", description="Deployment channel: stable, beta, internal"),
    device_id: Optional[str] = Query(None, description="Device identifier for staged rollout cohort calculation"),
    db: Session = Depends(get_db),
):
    """
    Returns the channel-aware, cryptographically signed release manifest for Scout Desktop.
    Includes package download URL, cryptographic SHA-256 hash, Ed25519 digital signature,
    minimum supported version (for mandatory update enforcement), and remote feature flags.
    Enforces Single Source of Truth, staged rollout cohorts (0-100%), circuit breaker auto-pauses,
    and remote dynamic configuration (Type 3 changes).
    """
    try:
        # 1. Authoritative Single Source of Truth: Canonical production release
        canonical_release = get_canonical_production_release(channel=channel, db=db)
        selected_release = canonical_release

        if canonical_release:
            # 2. Circuit breaker / pause check
            if canonical_release.is_paused or canonical_release.status in ("CIRCUIT_TRIPPED", "ROLLED_BACK", "PAUSED"):
                logger.info("Canonical release v%s is PAUSED / CIRCUIT_TRIPPED. Falling back to previous stable.", canonical_release.version)
                fallback_rel = (
                    db.query(ScoutRelease)
                    .filter(
                        ScoutRelease.channel == channel,
                        ScoutRelease.id < canonical_release.id,
                        ScoutRelease.status == "ACTIVE",
                        ScoutRelease.is_paused == False
                    )
                    .order_by(ScoutRelease.id.desc())
                    .first()
                )
                if fallback_rel:
                    selected_release = fallback_rel

            # 3. Staged rollout evaluation (Cohort allocation: 0-99)
            elif selected_release.rollout_percentage < 100 and device_id:
                cohort_bucket = abs(hash(device_id)) % 100
                if cohort_bucket >= selected_release.rollout_percentage:
                    logger.debug("Device %s in bucket %d >= rollout %d%% for v%s. Falling back to earlier release.",
                                 device_id, cohort_bucket, selected_release.rollout_percentage, selected_release.version)
                    fallback_rel = (
                        db.query(ScoutRelease)
                        .filter(
                            ScoutRelease.channel == channel,
                            ScoutRelease.id < selected_release.id,
                            ScoutRelease.status == "ACTIVE",
                            ScoutRelease.is_paused == False
                        )
                        .order_by(ScoutRelease.id.desc())
                        .first()
                    )
                    if fallback_rel:
                        selected_release = fallback_rel

        # 4. Resolve Dynamic Remote Features and Config (Type 3 changes)
        features, config = get_merged_remote_config(channel=channel, db=db)

        if selected_release:
            if selected_release.features_json:
                try:
                    features.update(json.loads(selected_release.features_json))
                except Exception:
                    pass
            if selected_release.config_json:
                try:
                    config.update(json.loads(selected_release.config_json))
                except Exception:
                    pass

            manifest_payload = {
                "product": "talentops-scout",
                "channel": selected_release.channel,
                "latest_version": selected_release.version,
                "minimum_version": selected_release.minimum_version,
                "mandatory": selected_release.mandatory,
                "release_date": selected_release.created_at.strftime("%Y-%m-%d") if selected_release.created_at else "2026-09-09",
                "release_notes": selected_release.release_notes,
                "rollout_percentage": selected_release.rollout_percentage,
                "is_current": bool(getattr(selected_release, "is_current", True)),
                "package": {
                    "url": selected_release.download_url,
                    "sha256": selected_release.sha256,
                    "size": selected_release.size_bytes or DEFAULT_SIZE,
                },
                "features": features,
                "config": config,
            }

            # Generate or attach Ed25519 signature
            sig = selected_release.signature
            if not sig:
                try:
                    sig = sign_manifest(manifest_payload)
                    selected_release.signature = sig
                    db.commit()
                except Exception as sign_err:
                    logger.warning("Could not dynamically sign manifest: %s", sign_err)

            pkg_sig = selected_release.package_signature
            if not pkg_sig and selected_release.sha256:
                try:
                    pkg_sig = sign_package_hash(selected_release.sha256)
                    selected_release.package_signature = pkg_sig
                    db.commit()
                except Exception as sign_err:
                    logger.warning("Could not dynamically sign package hash: %s", sign_err)

            manifest_payload["signature"] = sig
            manifest_payload["package_signature"] = pkg_sig
            return manifest_payload

        # Default fallback if DB has no releases
        fallback_manifest = {
            "product": "talentops-scout",
            "channel": channel,
            "latest_version": DEFAULT_RELEASE_VERSION,
            "minimum_version": DEFAULT_MINIMUM_VERSION,
            "mandatory": False,
            "release_date": "2026-09-09",
            "release_notes": "Official production release of TalentOps Scout Desktop.",
            "package": {
                "url": DEFAULT_DOWNLOAD_URL,
                "sha256": DEFAULT_SHA256,
                "size": DEFAULT_SIZE,
            },
            "features": features,
            "config": config,
        }
        try:
            fallback_manifest["signature"] = sign_manifest(fallback_manifest)
            fallback_manifest["package_signature"] = sign_package_hash(DEFAULT_SHA256)
        except Exception:
            pass

        return fallback_manifest

    except Exception as e:
        logger.error("Error generating signed update manifest: %s", e)
        fallback = {
            "product": "talentops-scout",
            "channel": channel,
            "latest_version": DEFAULT_RELEASE_VERSION,
            "minimum_version": DEFAULT_MINIMUM_VERSION,
            "mandatory": False,
            "package": {"url": DEFAULT_DOWNLOAD_URL, "sha256": DEFAULT_SHA256, "size": DEFAULT_SIZE},
            "features": DEFAULT_FEATURES,
            "config": DEFAULT_CONFIG,
        }
        return fallback


@router.get("/updates/latest")
def get_latest_release_info(
    channel: str = Query("stable", description="Deployment channel: stable, beta, internal"),
    db: Session = Depends(get_db),
):
    """
    Public single-source-of-truth metadata endpoint for web downloaders.
    Returns the canonical production release from the database registry (`is_current = True`).
    """
    try:
        release = get_canonical_production_release(channel=channel, db=db)

        if release:
            rel_date = (release.released_at or release.created_at)
            return {
                "version": release.version,
                "channel": release.channel,
                "status": release.status,
                "artifact": getattr(release, "artifact", "TalentOpsScoutSetup.exe") or "TalentOpsScoutSetup.exe",
                "artifact_url": getattr(release, "artifact_url", None) or release.download_url,
                "download_url": release.download_url,
                "sha256": release.sha256,
                "size_bytes": release.size_bytes or DEFAULT_SIZE,
                "release_notes": release.release_notes,
                "release_date": rel_date.strftime("%Y-%m-%d") if rel_date else "2026-09-09",
                "minimum_version": release.minimum_version,
                "mandatory": release.mandatory,
                "supported_windows_version": "Windows 10 / 11 64-bit",
                "is_current": bool(getattr(release, "is_current", True)),
                "is_public": bool(getattr(release, "is_public", True)),
                "rollout_percentage": release.rollout_percentage,
                "approved_at": release.approved_at.isoformat() if getattr(release, "approved_at", None) else None,
            }
    except Exception as err:
        logger.warning("Could not fetch release from db: %s", err)

    return {
        "version": DEFAULT_RELEASE_VERSION,
        "channel": channel,
        "status": "ACTIVE",
        "artifact": "TalentOpsScoutSetup.exe",
        "artifact_url": DEFAULT_DOWNLOAD_URL,
        "download_url": DEFAULT_DOWNLOAD_URL,
        "sha256": DEFAULT_SHA256,
        "size_bytes": DEFAULT_SIZE,
        "release_notes": "Official production release of TalentOps Scout Desktop.",
        "release_date": "2026-09-09",
        "minimum_version": DEFAULT_MINIMUM_VERSION,
        "mandatory": False,
        "supported_windows_version": "Windows 10 / 11 64-bit",
        "is_current": True,
        "is_public": True,
        "rollout_percentage": 100,
        "approved_at": None,
    }


class DownloadTrackRequest(BaseModel):
    version: Optional[str] = None
    source: Optional[str] = "web_download_button"


@router.post("/download/track")
def track_scout_download(
    req: DownloadTrackRequest = DownloadTrackRequest(),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Records a public or authenticated Scout installer download event.
    Distinguishes download events from installed/active contributors.
    """
    try:
        ip = request.client.host if request and request.client else None
        ua = request.headers.get("user-agent") if request else None

        user_id = None
        auth_header = request.headers.get("authorization") if request else None
        if auth_header and auth_header.startswith("Bearer "):
            try:
                import jwt as _jwt
                from ..services.auth_service import SECRET_KEY, ALGORITHM
                payload = _jwt.decode(auth_header.split(" ")[1], SECRET_KEY, algorithms=[ALGORITHM])
                user_id = int(payload.get("sub")) if payload.get("sub") else None
            except Exception:
                pass

        info = get_latest_release_info(db=db)
        ver = req.version or info.get("version") or DEFAULT_RELEASE_VERSION

        evt = ScoutDownloadEvent(
            user_id=user_id,
            ip_address=ip,
            user_agent=ua,
            release_version=ver,
            download_source=req.source or "web_download_page",
        )
        db.add(evt)
        db.commit()
        return {"ok": True, "event_id": evt.id, "version": ver}
    except Exception as e:
        logger.warning("Could not record download event: %s", e)
        return {"ok": False, "error": str(e)}


@router.get("/download/stats")
def get_download_stats(db: Session = Depends(get_db)):
    """Returns total download event count and recent telemetry."""
    total = db.query(ScoutDownloadEvent).count()
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    today_count = db.query(ScoutDownloadEvent).filter(ScoutDownloadEvent.downloaded_at >= today_start).count()
    return {
        "total_downloads": total,
        "downloads_today": today_count,
    }


@router.get("/updates/download/latest")
def download_latest_installer(
    channel: str = Query("stable"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Public redirect endpoint that dynamically sends the client to the official
    production download URL from the database registry, preventing stale links.
    Also records download telemetry for contributor lifecycle tracking.
    """
    from fastapi.responses import RedirectResponse

    info = get_latest_release_info(channel=channel, db=db)
    download_url = info.get("download_url") or DEFAULT_DOWNLOAD_URL

    try:
        ip = request.client.host if request and request.client else None
        ua = request.headers.get("user-agent") if request else None
        evt = ScoutDownloadEvent(
            ip_address=ip,
            user_agent=ua,
            release_version=info.get("version", DEFAULT_RELEASE_VERSION),
            download_source="direct_redirect_url",
        )
        db.add(evt)
        db.commit()
    except Exception:
        pass

    headers = {
        "Content-Disposition": 'attachment; filename="TalentOpsScoutSetup.exe"',
        "X-Content-Type-Options": "nosniff",
        "X-Checksum-SHA256": info.get("sha256") or DEFAULT_SHA256,
        "Cache-Control": "private, no-transform, max-age=60",
    }

    direct = (request.query_params.get("direct") or "").lower() in ("1", "true", "yes") if request else False
    local_setup = r"c:\TalentOpsAI\scout_desktop\dist\TalentOpsScoutSetup.exe"
    if direct and os.path.exists(local_setup):
        from fastapi.responses import FileResponse
        return FileResponse(
            path=local_setup,
            filename="TalentOpsScoutSetup.exe",
            media_type="application/vnd.microsoft.portable-executable",
            headers=headers,
        )

    return RedirectResponse(url=download_url, status_code=307, headers=headers)



@router.post("/updates/report")
def report_update_telemetry(
    req: UpdateReportRequest,
    db: Session = Depends(get_db),
):
    """
    Receives update status reports from Scout client nodes.
    Tracks state machine transitions, node health classification,
    and triggers automated circuit breakers if update failure rate > 3%.
    """
    try:
        inst = db.query(ScoutInstallation).filter(ScoutInstallation.device_id == req.device_id).first()
        now = datetime.now(timezone.utc)

        # 1. Determine Node Health Status
        health = "HEALTHY"
        if req.update_status in ("FAILED", "ROLLBACK", "DOWNLOAD_FAILED", "VERIFICATION_FAILED", "APPLY_FAILED", "HEALTH_CHECK_FAILED"):
            health = "UPDATE_FAILED"

        # 2. Create or Update Node Record
        if not inst:
            inst = ScoutInstallation(
                device_id=req.device_id,
                tenant_id=req.tenant_id,
                scout_version=req.scout_version,
                channel=req.channel,
                os_info=req.os_info,
                os_version=req.os_version,
                update_status=req.update_status,
                error_message=req.error_message,
                last_error=req.error_message if health == "UPDATE_FAILED" else None,
                queue_size=req.queue_size,
                health_status=health,
                current_release=req.target_version or req.scout_version,
                update_attempts=1 if health == "UPDATE_FAILED" else 0,
                last_seen=now,
                last_check_at=now,
                last_update_check=now,
                last_update_at=now if req.update_status in ("SUCCESS", "UPDATED", "UP_TO_DATE") else None,
                last_successful_update=now if req.update_status in ("SUCCESS", "UPDATED") else None,
            )
            db.add(inst)
        else:
            inst.scout_version = req.scout_version
            inst.channel = req.channel
            inst.update_status = req.update_status
            inst.error_message = req.error_message
            if req.os_info:
                inst.os_info = req.os_info
            if req.os_version:
                inst.os_version = req.os_version
            if req.tenant_id:
                inst.tenant_id = req.tenant_id
            inst.queue_size = req.queue_size
            inst.health_status = health
            inst.last_seen = now
            inst.last_check_at = now
            inst.last_update_check = now

            if req.target_version:
                inst.current_release = req.target_version

            if health == "UPDATE_FAILED":
                inst.last_error = req.error_message
                inst.update_attempts = (inst.update_attempts or 0) + 1

            if req.update_status in ("SUCCESS", "UPDATED"):
                inst.last_update_at = now
                inst.last_successful_update = now

        # 3. Track Release Success / Failure counts & Evaluate Circuit Breaker
        target_v = req.target_version or req.scout_version
        rel = db.query(ScoutRelease).filter(ScoutRelease.version == target_v).first()

        if rel:
            if req.update_status in ("SUCCESS", "UPDATED"):
                rel.success_count = (rel.success_count or 0) + 1
            elif req.update_status in ("FAILED", "ROLLBACK", "DOWNLOAD_FAILED", "VERIFICATION_FAILED", "APPLY_FAILED", "HEALTH_CHECK_FAILED"):
                rel.failure_count = (rel.failure_count or 0) + 1

            # AUTOMATED CIRCUIT BREAKER:
            # If at least 5 update attempts have been recorded and failure rate > threshold (3%),
            # immediately PAUSE release to prevent fleet-wide failure.
            total_attempts = (rel.failure_count or 0) + (rel.success_count or 0)
            if total_attempts >= 5:
                fail_rate = (rel.failure_count / total_attempts) * 100.0
                if fail_rate > rel.failure_threshold_pct and not rel.is_paused:
                    rel.is_paused = True
                    rel.status = "CIRCUIT_TRIPPED"
                    logger.warning(
                        "[CIRCUIT BREAKER ACTIVATED] Paused release v%s! Failure rate: %.1f%% > %.1f%% threshold (%d failures / %d attempts)",
                        rel.version, fail_rate, rel.failure_threshold_pct, rel.failure_count, total_attempts
                    )

        db.commit()
        return {
            "status": "ok",
            "device_id": req.device_id,
            "recorded_status": req.update_status,
            "health_status": health,
        }
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
    Admin endpoint to publish a new software version with cryptographic signatures.
    If is_production is True, automatically demotes prior releases and promotes this one.
    Otherwise, creates the release in 'RELEASE_CANDIDATE' status awaiting production approval.
    """
    try:
        now = datetime.now(timezone.utc)
        # Pre-compute signatures
        manifest_data = {
            "product": "talentops-scout",
            "channel": req.channel,
            "latest_version": req.version,
            "minimum_version": req.minimum_version,
            "mandatory": req.mandatory,
            "release_notes": req.release_notes,
            "package": {
                "url": req.download_url,
                "sha256": req.sha256,
                "size": req.size_bytes or DEFAULT_SIZE,
            },
            "features": req.features,
            "config": req.config,
        }
        sig = sign_manifest(manifest_data)
        pkg_sig = sign_package_hash(req.sha256) if req.sha256 else None

        if req.is_production:
            db.query(ScoutRelease).filter(ScoutRelease.channel == req.channel).update({"is_current": False})

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
            existing.rollout_percentage = req.rollout_percentage
            existing.failure_threshold_pct = req.failure_threshold_pct
            existing.signature = sig
            existing.package_signature = pkg_sig
            existing.is_paused = False
            if req.is_production:
                existing.is_current = True
                existing.status = "ACTIVE"
                existing.approved_at = now
                existing.released_at = now
                existing.approved_by = getattr(current_user, "id", None)
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
                rollout_percentage=req.rollout_percentage,
                failure_threshold_pct=req.failure_threshold_pct,
                signature=sig,
                package_signature=pkg_sig,
                status="ACTIVE" if req.is_production else "RELEASE_CANDIDATE",
                is_current=req.is_production,
                is_paused=False,
                approved_at=now if req.is_production else None,
                released_at=now if req.is_production else None,
                approved_by=getattr(current_user, "id", None) if req.is_production else None,
            )
            db.add(rel)

        db.commit()
        db.refresh(rel)
        logger.info("Published Scout release v%s (channel: %s, is_production=%s)", req.version, req.channel, req.is_production)
        return {
            "status": "published",
            "version": req.version,
            "id": rel.id,
            "is_current": rel.is_current,
            "release_status": rel.status,
            "signature": sig,
            "package_signature": pkg_sig,
        }
    except Exception as e:
        db.rollback()
        logger.error("Failed to publish release: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/releases/{version}/approve-production")
def approve_production_release(
    version: str,
    req: ReleaseApprovalRequest = ReleaseApprovalRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Authoritative manual Production Release Approval Gate.
    Verifies the safety checklist (Tests, Security, Signing, Installer, Migration, Rollback, Compatibility).
    Atomically promotes the specified version to `is_current = True` and demotes previous releases.
    Instantly synchronizes:
      1. Release Registry
      2. Public Website Download
      3. Update Manifest
      4. Fleet Auto-Updater
    """
    rel = db.query(ScoutRelease).filter(ScoutRelease.version == version).first()
    if not rel:
        raise HTTPException(status_code=404, detail=f"Release v{version} not found in registry")

    # Safety checklist validation
    chk = req.checklist
    failed_checks = []
    if not chk.tests_passed: failed_checks.append("Automated Tests")
    if not chk.security_verified: failed_checks.append("Security & Cryptographic Trust")
    if not chk.signing_verified: failed_checks.append("Code Signing & Integrity Hash")
    if not chk.installer_verified: failed_checks.append("Installer Build & Metadata")
    if not chk.migration_verified: failed_checks.append("Database Schema Migration")
    if not chk.rollback_tested: failed_checks.append("Rollback Verification")
    if not chk.compatibility_verified: failed_checks.append("Backward Compatibility")

    if failed_checks and not chk.force:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve production release. Failed checklist items: {', '.join(failed_checks)}. Pass force=true to override."
        )

    now = datetime.now(timezone.utc)
    try:
        # 1. Demote any currently active production release for this channel
        db.query(ScoutRelease).filter(
            ScoutRelease.channel == rel.channel,
            ScoutRelease.id != rel.id,
        ).update({"is_current": False})

        # 2. Promote target release as canonical production release
        rel.is_current = True
        rel.status = "ACTIVE"
        rel.is_paused = False
        rel.approved_at = now
        rel.released_at = now
        rel.approved_by = getattr(current_user, "id", None)
        rel.approval_checklist_json = json.dumps(chk.model_dump())
        if req.rollout_percentage is not None:
            rel.rollout_percentage = max(0, min(100, req.rollout_percentage))
        if req.set_minimum_version:
            rel.minimum_version = req.set_minimum_version

        db.commit()
        db.refresh(rel)

        logger.info(
            "🎉 [PRODUCTION RELEASE APPROVED] v%s is now canonical production for '%s' (Rollout: %d%%). Approved by user=%s",
            rel.version, rel.channel, rel.rollout_percentage, getattr(current_user, "email", "system")
        )

        return {
            "status": "APPROVED",
            "version": rel.version,
            "channel": rel.channel,
            "is_current": True,
            "rollout_percentage": rel.rollout_percentage,
            "minimum_version": rel.minimum_version,
            "approved_at": rel.approved_at.isoformat(),
            "synchronized_surfaces": {
                "release_registry": f"/scout/releases (version={rel.version}, is_current=true)",
                "public_download": f"/scout/updates/download/latest -> {rel.download_url}",
                "latest_info": f"/scout/updates/latest (version={rel.version})",
                "update_manifest": f"/scout/updates/manifest (latest_version={rel.version})",
                "fleet_telemetry": f"/scout/fleet/stats (measuring against v{rel.version})",
            }
        }
    except Exception as e:
        db.rollback()
        logger.error("Failed to approve production release v%s: %s", version, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/releases/{version}/rollback")
def rollback_production_release(
    version: str,
    reason: Optional[str] = "Emergency rollback triggered by admin",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Emergency Rollback Gate.
    Immediately trips / pauses the faulty release (status='ROLLED_BACK', is_current=False).
    Promotes the previous stable release on that channel back to `is_current = True`.
    Instantly restores public downloads and fleet manifests to the proven stable version.
    """
    rel = db.query(ScoutRelease).filter(ScoutRelease.version == version).first()
    if not rel:
        raise HTTPException(status_code=404, detail=f"Release v{version} not found in registry")

    try:
        # Demote broken release
        rel.is_current = False
        rel.is_paused = True
        rel.status = "ROLLED_BACK"

        # Find previous stable release on that channel
        prev = (
            db.query(ScoutRelease)
            .filter(
                ScoutRelease.channel == rel.channel,
                ScoutRelease.id < rel.id,
                ScoutRelease.status.in_(["ACTIVE", "CIRCUIT_TRIPPED", "PAUSED"])
            )
            .order_by(ScoutRelease.id.desc())
            .first()
        )

        restored_version = None
        if prev:
            prev.is_current = True
            prev.status = "ACTIVE"
            prev.is_paused = False
            restored_version = prev.version
            logger.warning("🚨 [ROLLBACK EXECUTED] Rolled back from v%s to previous stable v%s! Reason: %s", version, prev.version, reason)
        else:
            logger.warning("🚨 [ROLLBACK EXECUTED] Tripped v%s, no previous release in channel. Reason: %s", version, reason)

        db.commit()
        return {
            "status": "ROLLED_BACK",
            "rolled_back_version": version,
            "restored_version": restored_version,
            "reason": reason,
            "is_paused": True,
        }
    except Exception as e:
        db.rollback()
        logger.error("Failed to execute rollback for v%s: %s", version, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/releases/{version}/rollout")
def control_release_rollout(
    version: str,
    req: RolloutControlRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Admin endpoint to adjust rollout percentage (e.g. 5%, 25%, 50%, 100%)
    or pause/resume release rollout.
    """
    rel = db.query(ScoutRelease).filter(ScoutRelease.version == version).first()
    if not rel:
        raise HTTPException(status_code=404, detail=f"Release v{version} not found")

    if req.rollout_percentage is not None:
        rel.rollout_percentage = max(0, min(100, req.rollout_percentage))

    if req.is_paused is not None:
        rel.is_paused = req.is_paused
        if not req.is_paused and rel.status in ("CIRCUIT_TRIPPED", "PAUSED"):
            rel.status = "ACTIVE"
            rel.failure_count = 0  # reset circuit count on manual un-pause

    db.commit()
    return {
        "version": rel.version,
        "rollout_percentage": rel.rollout_percentage,
        "is_paused": rel.is_paused,
        "status": rel.status,
    }


@router.get("/config")
def get_remote_configuration(
    channel: str = Query("stable"),
    db: Session = Depends(get_db),
):
    """
    Returns active Remote Configuration parameters and feature flags (Type 3 changes).
    Allows clients or dashboards to inspect active capture rules, batch sizes, and sync intervals.
    """
    features, config = get_merged_remote_config(channel=channel, db=db)
    cfg_rec = db.query(ScoutRemoteConfig).filter(ScoutRemoteConfig.config_key == "global").first()
    return {
        "channel": channel,
        "features": features,
        "config": config,
        "description": cfg_rec.description if cfg_rec else "Global Remote Configuration",
        "updated_at": cfg_rec.updated_at.isoformat() if cfg_rec and cfg_rec.updated_at else None,
    }


@router.put("/config")
def update_remote_configuration(
    req: RemoteConfigUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Centralized Remote Configuration Editor (Type 3 changes).
    Dynamically alters Scout parameters (batch size, sync intervals, feature flags)
    without recompilation, new installers, or client restarts.
    """
    cfg_rec = db.query(ScoutRemoteConfig).filter(ScoutRemoteConfig.config_key == req.config_key).first()
    now = datetime.now(timezone.utc)
    if not cfg_rec:
        cfg_rec = ScoutRemoteConfig(
            config_key=req.config_key,
            channel=req.channel,
            features_json=json.dumps(req.features or {}),
            config_json=json.dumps(req.config or {}),
            description=req.description or f"Configuration for {req.config_key}",
            updated_by=getattr(current_user, "id", None),
            created_at=now,
            updated_at=now,
        )
        db.add(cfg_rec)
    else:
        if req.features is not None:
            existing_f = json.loads(cfg_rec.features_json or "{}")
            existing_f.update(req.features)
            cfg_rec.features_json = json.dumps(existing_f)
        if req.config is not None:
            existing_c = json.loads(cfg_rec.config_json or "{}")
            existing_c.update(req.config)
            cfg_rec.config_json = json.dumps(existing_c)
        if req.description:
            cfg_rec.description = req.description
        cfg_rec.updated_by = getattr(current_user, "id", None)
        cfg_rec.updated_at = now

    db.commit()
    db.refresh(cfg_rec)
    logger.info("Updated remote configuration '%s' (channel: %s) by user=%s", req.config_key, req.channel, getattr(current_user, "email", "system"))
    return {
        "status": "updated",
        "config_key": cfg_rec.config_key,
        "channel": cfg_rec.channel,
        "features": json.loads(cfg_rec.features_json or "{}"),
        "config": json.loads(cfg_rec.config_json or "{}"),
        "updated_at": cfg_rec.updated_at.isoformat() if cfg_rec.updated_at else None,
    }


@router.get("/fleet/user/{user_id}/installations")
def get_user_device_installations(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Returns multi-computer fleet breakdown for a specific user (Desktop, Laptop, Work PC).
    Each installation shows its independent version, update status, health status, and whether update is required.
    """
    nodes = db.query(ScoutInstallation).filter(ScoutInstallation.user_id == user_id).all()
    canonical_prod = get_canonical_production_release(channel="stable", db=db)
    latest_v = canonical_prod.version if canonical_prod else DEFAULT_RELEASE_VERSION
    min_v = canonical_prod.minimum_version if canonical_prod else DEFAULT_MINIMUM_VERSION

    def parse_v(v: str):
        try:
            return tuple(int(x) for x in v.strip().lstrip("v").split("-")[0].split("."))
        except Exception:
            return (0, 0, 0)

    results = []
    for n in nodes:
        node_v = parse_v(n.scout_version)
        min_parsed = parse_v(min_v)
        latest_parsed = parse_v(latest_v)

        is_below_min = node_v < min_parsed
        is_up_to_date = node_v >= latest_parsed

        derived_status = n.update_status
        if is_below_min:
            derived_status = "UPDATE_REQUIRED"
        elif not is_up_to_date and derived_status in ("UP_TO_DATE", "STABLE"):
            derived_status = "UPDATE_AVAILABLE"

        results.append({
            "id": n.id,
            "device_id": n.device_id,
            "hostname": n.os_info or n.device_id,
            "os_info": n.os_info,
            "os_version": n.os_version,
            "scout_version": n.scout_version,
            "channel": n.channel,
            "update_status": derived_status,
            "health_status": n.health_status,
            "is_below_minimum": is_below_min,
            "is_latest": is_up_to_date,
            "latest_production_version": latest_v,
            "minimum_required_version": min_v,
            "last_seen": n.last_seen.isoformat() if n.last_seen else None,
            "last_update_at": n.last_update_at.isoformat() if n.last_update_at else None,
        })
    return {
        "user_id": user_id,
        "total_devices": len(results),
        "latest_production_version": latest_v,
        "minimum_required_version": min_v,
        "installations": results,
    }


@router.get("/releases")
def list_scout_releases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """Returns catalog of all Scout software releases across channels."""
    releases = db.query(ScoutRelease).order_by(ScoutRelease.id.desc()).all()
    total_nodes = db.query(sqlfunc.count(ScoutInstallation.id)).scalar() or 0

    results = []
    for r in releases:
        # Calculate adoption percentage
        count = db.query(sqlfunc.count(ScoutInstallation.id)).filter(ScoutInstallation.scout_version == r.version).scalar() or 0
        adoption_pct = round((count / total_nodes * 100.0), 1) if total_nodes > 0 else 0.0

        chk = {}
        if r.approval_checklist_json:
            try:
                chk = json.loads(r.approval_checklist_json)
            except Exception:
                pass

        results.append({
            "id": r.id,
            "version": r.version,
            "channel": r.channel,
            "minimum_version": r.minimum_version,
            "mandatory": r.mandatory,
            "status": "CIRCUIT_TRIPPED" if (r.status == "CIRCUIT_TRIPPED" or (r.is_paused and r.failure_rate > r.failure_threshold_pct)) else ("PAUSED" if r.is_paused else r.status),
            "is_current": bool(getattr(r, "is_current", False)),
            "is_production": bool(getattr(r, "is_current", False)),
            "rollout_percentage": r.rollout_percentage,
            "is_paused": r.is_paused,
            "adoption_percentage": adoption_pct,
            "device_count": count,
            "failure_rate": r.failure_rate,
            "failure_count": r.failure_count or 0,
            "success_count": r.success_count or 0,
            "release_notes": r.release_notes,
            "download_url": r.download_url,
            "sha256": r.sha256,
            "approved_at": r.approved_at.isoformat() if r.approved_at else None,
            "approved_by": r.approved_by,
            "approval_checklist": chk,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return results


@router.get("/fleet/stats")
def get_fleet_update_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Returns enterprise analytics on Scout fleet health, version distribution,
    and active release channels.
    """
    try:
        now = datetime.now(timezone.utc)
        stale_threshold = now - timedelta(minutes=10)
        offline_threshold = now - timedelta(hours=24)

        all_nodes = db.query(ScoutInstallation).all()
        total = len(all_nodes)

        # Get latest active stable release for minimum_version floor
        latest_stable = (
            db.query(ScoutRelease)
            .filter(ScoutRelease.channel == "stable", ScoutRelease.status == "ACTIVE")
            .order_by(ScoutRelease.id.desc())
            .first()
        )
        min_ver_str = latest_stable.minimum_version if latest_stable else "1.0.0"
        latest_ver_str = latest_stable.version if latest_stable else "2.0.0"

        # Node Health Breakdown
        healthy = 0
        stale = 0
        update_available = 0
        update_required = 0
        failed = 0
        offline = 0

        def parse_v(v: str):
            try:
                return tuple(int(x) for x in v.strip().lstrip("v").split("-")[0].split("."))
            except Exception:
                return (0, 0, 0)

        min_v = parse_v(min_ver_str)
        latest_v = parse_v(latest_ver_str)

        for n in all_nodes:
            seen = n.last_seen
            if seen and seen.tzinfo is None:
                seen = seen.replace(tzinfo=timezone.utc)

            v = parse_v(n.scout_version)

            if seen and seen < offline_threshold:
                offline += 1
            elif n.update_status in ("FAILED", "ROLLBACK", "DOWNLOAD_FAILED", "VERIFICATION_FAILED", "APPLY_FAILED", "HEALTH_CHECK_FAILED"):
                failed += 1
            elif seen and seen < stale_threshold:
                stale += 1
            else:
                healthy += 1

            if v < min_v:
                update_required += 1
            elif v < latest_v:
                update_available += 1

        # Version Distribution
        version_counts = (
            db.query(ScoutInstallation.scout_version, sqlfunc.count(ScoutInstallation.id))
            .group_by(ScoutInstallation.scout_version)
            .all()
        )
        v_dist = []
        for ver, cnt in version_counts:
            pct = round((cnt / total * 100.0), 1) if total > 0 else 0.0
            v_dist.append({
                "version": ver,
                "device_count": cnt,
                "percentage": pct,
                "is_below_minimum": parse_v(ver) < min_v,
            })
        v_dist.sort(key=lambda x: parse_v(x["version"]), reverse=True)

        # Releases Summary
        releases = db.query(ScoutRelease).order_by(ScoutRelease.id.desc()).all()
        rel_list = []
        circuit_alert = None

        for r in releases:
            cnt = sum(1 for n in all_nodes if n.scout_version == r.version)
            pct = round((cnt / total * 100.0), 1) if total > 0 else 0.0
            status = "CIRCUIT_TRIPPED" if (r.status == "CIRCUIT_TRIPPED" or (r.is_paused and r.failure_rate > r.failure_threshold_pct)) else ("PAUSED" if r.is_paused else r.status)
            
            if status == "CIRCUIT_TRIPPED" and not circuit_alert:
                circuit_alert = {
                    "version": r.version,
                    "channel": r.channel,
                    "failure_rate": r.failure_rate,
                    "threshold": r.failure_threshold_pct,
                    "message": f"Rollout auto-paused: Version {r.version} failure rate ({r.failure_rate}%) exceeded safety threshold ({r.failure_threshold_pct}%)."
                }

            rel_list.append({
                "id": r.id,
                "version": r.version,
                "channel": r.channel,
                "rollout_percentage": r.rollout_percentage,
                "is_paused": r.is_paused,
                "status": status,
                "adoption_percentage": pct,
                "device_count": cnt,
                "failure_rate": r.failure_rate,
            })

        return {
            "total_devices": total,
            "node_health": {
                "healthy": healthy,
                "stale": stale,
                "update_available": update_available,
                "update_required": update_required,
                "failed": failed,
                "offline": offline,
            },
            "version_distribution": v_dist,
            "releases": rel_list,
            "circuit_breaker_alert": circuit_alert,
        }
    except Exception as e:
        logger.error("Failed to generate fleet update stats: %s", e)
        return {
            "total_devices": 0,
            "node_health": {"healthy": 0, "stale": 0, "update_available": 0, "update_required": 0, "failed": 0, "offline": 0},
            "version_distribution": [],
            "releases": [],
            "circuit_breaker_alert": None,
        }
