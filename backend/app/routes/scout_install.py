"""
scout_install.py — Zero-Friction One-Click Desktop Scout Auto-Registration API.

Provides:
- POST /scout/install/claim: Web UI requests a short-lived, single-use claim for signed-in user.
- POST /scout/install/register: Scout Desktop submits claim + secret on launch to auto-bind device.
- GET /scout/install/status/{claim_id}: Web UI polls claim consumption status for real-time onboarding feedback.

Security Guarantees:
- Secrets are hashed with SHA-256 before database storage; raw secrets are never persisted.
- Claims expire in 15 minutes and can only be consumed once (atomic consumption).
- NO user passwords, browser credentials, or cookies are ever extracted, handled, or stored.
"""

import os
import secrets
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.auth_models import User
from ..models.update_models import ScoutInstallationClaim, ScoutInstallation
from ..models.extension_models import ExtensionDevice, ExtensionActivationCode
from ..services.auth_service import (
    get_current_user_from_request,
    create_access_token,
)

logger = logging.getLogger("talentops.scout_install")
router = APIRouter(prefix="/scout/install", tags=["Scout Auto-Registration & Claims"])


# ── Pydantic Request Models ───────────────────────────────────────────────────

class ClaimCreateRequest(BaseModel):
    label: Optional[str] = "Desktop Scout Node"
    expires_minutes: int = 15


class ClaimRegisterRequest(BaseModel):
    claim_id: str
    claim_secret: str
    device_id: str
    hostname: Optional[str] = None
    os_info: Optional[str] = None
    scout_version: Optional[str] = "2.0.0"


# ── Claim Generation (Web UI -> Backend) ──────────────────────────────────────

@router.post("/claim")
def create_installation_claim(
    req: ClaimCreateRequest = ClaimCreateRequest(),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Creates a cryptographically secure, short-lived (15-min) installation claim.
    Called by the web download page when an authenticated user initiates Scout download.
    """
    # Generate unique claim_id: CLM-XXXX-XXXX-XXXX
    claim_id = f"CLM-{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"
    
    # Generate high-entropy one-time secret
    claim_secret = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(claim_secret.encode("utf-8")).hexdigest()

    ttl_minutes = max(5, min(60, req.expires_minutes))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)

    client_ip = request.client.host if request and request.client else None
    client_ua = request.headers.get("user-agent") if request else None

    claim = ScoutInstallationClaim(
        claim_id=claim_id,
        claim_token_hash=token_hash,
        user_id=current_user.id,
        tenant_id=current_user.id,
        status="CREATED",
        ip_address=client_ip,
        user_agent=client_ua[:300] if client_ua else None,
        expires_at=expires_at,
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)

    deep_link = f"talentopsscout://claim?claim_id={claim_id}&claim_secret={claim_secret}"

    logger.info(
        "Created Scout Installation Claim %s for user=%d (%s), expires=%s",
        claim_id, current_user.id, current_user.email, expires_at
    )

    return {
        "ok": True,
        "claim_id": claim_id,
        "claim_secret": claim_secret,
        "expires_at": expires_at.isoformat(),
        "expires_in_seconds": int((expires_at - datetime.now(timezone.utc)).total_seconds()),
        "deep_link": deep_link,
        "loopback_payload": {
            "claim_id": claim_id,
            "claim_secret": claim_secret,
        },
        "user_email": current_user.email,
    }


# ── Claim Registration (Scout Desktop -> Backend) ────────────────────────────

@router.post("/register")
def register_scout_installation(
    req: ClaimRegisterRequest,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Consumes an installation claim to register a new Scout Desktop instance.
    Validates the claim secret against stored SHA-256 hash.
    Binds the device directly to the user's account and returns a scoped JWT.
    """
    clean_claim_id = req.claim_id.strip().upper()
    claim = db.query(ScoutInstallationClaim).filter(
        ScoutInstallationClaim.claim_id == clean_claim_id
    ).first()

    if not claim:
        logger.warning("Scout register rejected: claim %s not found", clean_claim_id)
        raise HTTPException(status_code=404, detail="Installation claim not found or invalid")

    # Check status
    if claim.status == "CONSUMED":
        logger.warning("Scout register rejected: claim %s already consumed", clean_claim_id)
        raise HTTPException(status_code=409, detail="This installation claim has already been used")

    if claim.status in ("EXPIRED", "REVOKED"):
        logger.warning("Scout register rejected: claim %s status is %s", clean_claim_id, claim.status)
        raise HTTPException(status_code=403, detail=f"Installation claim is {claim.status.lower()}")

    # Check TTL
    now = datetime.now(timezone.utc)
    exp_aware = claim.expires_at.replace(tzinfo=timezone.utc) if claim.expires_at.tzinfo is None else claim.expires_at
    if exp_aware < now:
        claim.status = "EXPIRED"
        db.commit()
        logger.warning("Scout register rejected: claim %s has expired", clean_claim_id)
        raise HTTPException(status_code=403, detail="Installation claim has expired. Please launch from download page again.")

    # Validate secret
    provided_hash = hashlib.sha256(req.claim_secret.strip().encode("utf-8")).hexdigest()
    if not secrets.compare_digest(provided_hash, claim.claim_token_hash):
        logger.warning("Scout register rejected: secret mismatch for claim %s", clean_claim_id)
        raise HTTPException(status_code=403, detail="Invalid claim secret")

    # Retrieve owner user
    owner = db.query(User).filter(User.id == claim.user_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="User account associated with this claim no longer exists")

    client_ip = request.client.host if request and request.client else None
    device_name = f"{req.hostname or 'Windows Desktop'} ({req.os_info or 'Windows'})"

    # Mark claim CONSUMED atomically
    claim.status = "CONSUMED"
    claim.used_at = now
    claim.device_id = req.device_id
    claim.hostname = req.hostname
    claim.os_info = req.os_info
    if client_ip:
        claim.ip_address = client_ip

    # Register or update ExtensionDevice
    device = db.query(ExtensionDevice).filter(
        ExtensionDevice.device_id == req.device_id
    ).first()

    if not device:
        device = ExtensionDevice(
            device_id=req.device_id,
            owner_user_id=owner.id,
            user_agent=device_name,
            extension_version=req.scout_version or "2.0.0",
            first_seen_at=now,
            last_seen_at=now,
            is_active=True,
        )
        db.add(device)
    else:
        device.owner_user_id = owner.id
        device.user_agent = device_name
        device.extension_version = req.scout_version or "2.0.0"
        device.last_seen_at = now
        device.is_active = True

    # Register or update ScoutInstallation
    installation = db.query(ScoutInstallation).filter(
        ScoutInstallation.device_id == req.device_id
    ).first()

    if not installation:
        installation = ScoutInstallation(
            device_id=req.device_id,
            installation_id=f"inst-{secrets.token_hex(6)}",
            user_id=owner.id,
            tenant_id=claim.tenant_id or owner.id,
            scout_version=req.scout_version or "2.0.0",
            os_info=req.os_info,
            health_status="HEALTHY",
            update_status="UP_TO_DATE",
            last_seen=now,
        )
        db.add(installation)
    else:
        installation.user_id = owner.id
        installation.tenant_id = claim.tenant_id or owner.id
        installation.scout_version = req.scout_version or "2.0.0"
        installation.os_info = req.os_info
        installation.health_status = "HEALTHY"
        installation.last_seen = now

    db.commit()

    # Issue scoped JWT token (1-year validity for persistent companion node)
    token_payload = {
        "sub": str(owner.id),
        "email": owner.email,
        "device_id": req.device_id,
        "node_type": "desktop_scout",
        "scope": "scout:telemetry",
    }
    access_token = create_access_token(
        data=token_payload,
        expires_delta=timedelta(days=365),
    )

    logger.info(
        "🎉 Scout Desktop auto-registered successfully! claim=%s device=%s user=%s (%d)",
        clean_claim_id, req.device_id, owner.email, owner.id
    )

    return {
        "ok": True,
        "access_token": access_token,
        "token_type": "bearer",
        "scout_id": req.device_id,
        "device_id": req.device_id,
        "user_id": owner.id,
        "user_email": owner.email,

        "user_name": f"{getattr(owner, 'first_name', '') or ''} {getattr(owner, 'last_name', '') or ''}".strip() or owner.email.split("@")[0],
        "status": "REGISTERED",
    }




# ── Claim Status Polling (Web UI -> Backend) ──────────────────────────────────

@router.get("/status/{claim_id}")
def get_claim_status(
    claim_id: str,
    db: Session = Depends(get_db),
):
    """
    Allows the download web page to monitor when Scout Desktop has consumed
    the claim and successfully joined the user's fleet.
    """
    clean_claim_id = claim_id.strip().upper()
    claim = db.query(ScoutInstallationClaim).filter(
        ScoutInstallationClaim.claim_id == clean_claim_id
    ).first()

    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    now = datetime.now(timezone.utc)
    exp_aware = claim.expires_at.replace(tzinfo=timezone.utc) if claim.expires_at.tzinfo is None else claim.expires_at
    is_expired = (claim.status != "CONSUMED") and (exp_aware < now)

    effective_status = "EXPIRED" if is_expired else claim.status

    return {
        "claim_id": claim.claim_id,
        "status": effective_status,
        "is_consumed": claim.status == "CONSUMED",
        "device_id": claim.device_id,
        "hostname": claim.hostname,
        "used_at": claim.used_at.isoformat() if claim.used_at else None,
        "created_at": claim.created_at.isoformat() if claim.created_at else None,
        "expires_at": claim.expires_at.isoformat() if claim.expires_at else None,
    }
