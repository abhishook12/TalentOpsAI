"""
Extension API Routes — /recruiters/extension/*

Endpoints:
  POST /recruiters/extension/activate   — validate activation code, return JWT
  POST /recruiters/extension/batch      — receive scraped contact batch
  POST /recruiters/extension/heartbeat  — hourly device status ping
  GET  /recruiters/extension/report     — ADMIN: daily report for all devices
  GET  /recruiters/extension/codes      — ADMIN: list/create activation codes
  POST /recruiters/extension/codes      — ADMIN: create new activation code
"""

import json
import logging
import re
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text, func as sqlfunc

from ..database import get_db
from ..models.models import Recruiter, Company
from ..models.extension_models import (
    ExtensionActivationCode,
    ExtensionDevice,
    ExtensionHeartbeat,
    ExtensionSubmissionLog,
)
from ..models.auth_models import User
from ..services.auth_service import (
    get_current_user_from_request,
    require_role,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
)
from ..utils.normalizer import normalize_text, extract_domain

logger = logging.getLogger("talentops.extension")
router = APIRouter(prefix="/recruiters/extension", tags=["Extension"])

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "icloud.com", "live.com", "msn.com", "me.com", "mail.com",
    "protonmail.com", "ymail.com", "comcast.net", "att.net",
}

# ── Pydantic Models ─────────────────────────────────────────────────────────

class ActivationRequest(BaseModel):
    activation_code: str
    device_id: str
    user_agent: Optional[str] = None


class ExtensionContact(BaseModel):
    recruiter_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    company_name: Optional[str] = None
    linkedin_url: Optional[str] = None
    location: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    source_page_title: Optional[str] = None
    device_id: Optional[str] = None
    captured_at: Optional[str] = None
    _relevance_score: Optional[int] = None


class BatchRequest(BaseModel):
    contacts: List[ExtensionContact]
    device_id: Optional[str] = None
    session_stats: Optional[dict] = None


class HeartbeatRequest(BaseModel):
    device_id: str
    session_captured: int = 0
    session_sent: int = 0
    session_duplicates: int = 0
    queue_pending: int = 0
    total_ever_sent: int = 0
    extension_version: Optional[str] = None
    timestamp: Optional[str] = None


class CreateCodeRequest(BaseModel):
    label: Optional[str] = None
    max_uses: int = -1  # -1 = unlimited
    expires_days: Optional[int] = None  # None = never expires


def is_admin_user(user: User) -> bool:
    if not user:
        return False
    if user.email and user.email.lower() == "abhishekjadon824@gmail.com":
        return True
    if hasattr(user, "role") and user.role and getattr(user.role, "name", "").lower() in ("admin", "superadmin"):
        return True
    return False


import jwt as _jwt

async def get_extension_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Extension token required")
    token = authorization.split(" ", 1)[1]
    try:
        payload = _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


# ── POST /recruiters/extension/activate ─────────────────────────────────────

@router.post("/activate")
def activate_extension(req: ActivationRequest, db: Session = Depends(get_db)):
    """
    Validate activation code, register device, return scoped JWT.
    Silent endpoint — anyone with a valid code can activate.
    """
    code_record = (
        db.query(ExtensionActivationCode)
        .filter(
            ExtensionActivationCode.code == req.activation_code.strip().upper(),
            ExtensionActivationCode.is_active == True,
        )
        .first()
    )

    if not code_record:
        raise HTTPException(status_code=403, detail="Invalid or expired activation code")

    # Check max uses
    if code_record.max_uses != -1 and code_record.use_count >= code_record.max_uses:
        raise HTTPException(status_code=403, detail="Activation code has reached its usage limit")

    # Check expiry
    if code_record.expires_at and code_record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=403, detail="Activation code has expired")

    # Register or update device
    device = (
        db.query(ExtensionDevice)
        .filter(ExtensionDevice.device_id == req.device_id)
        .first()
    )

    if not device:
        device = ExtensionDevice(
            device_id=req.device_id,
            activation_code_id=code_record.id,
            owner_user_id=code_record.owner_user_id,
            user_agent=req.user_agent,
        )
        db.add(device)
        code_record.use_count += 1

    device.last_seen_at = datetime.now(timezone.utc)
    db.commit()

    # Issue JWT scoped to the code's owner
    token = create_access_token(
        data={"sub": str(code_record.owner_user_id), "scope": "extension"},
        expires_delta=timedelta(days=365),  # Long-lived token
    )

    logger.info("Extension activated: device=%s code=%s", req.device_id, req.activation_code)
    return {"access_token": token, "token_type": "bearer"}


# ── POST /recruiters/extension/batch ─────────────────────────────────────────

@router.post("/batch")
def ingest_extension_batch(
    req: BatchRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_extension_user),
    x_device_id: Optional[str] = Header(None),
    x_extension_version: Optional[str] = Header(None),
):
    """
    Receive batch of scraped contacts from extension.
    Deduplicates by email, creates/updates Recruiter records silently.
    """
    device_id = req.device_id or x_device_id or "unknown"
    accepted = 0
    duplicates = 0
    errors = []
    source_sites = set()

    for contact in req.contacts:
        try:
            # Must have at least name or email
            if not contact.email and not contact.recruiter_name:
                continue

            # Normalize email
            email = (contact.email or "").strip().lower() or None

            # Skip if email is free provider
            if email:
                domain = email.split("@")[-1].lower()
                if domain in FREE_EMAIL_DOMAINS:
                    email = None

            # If no email and no LinkedIn — skip (can't dedup reliably)
            if not email and not contact.linkedin_url:
                continue

            # Track source sites
            if contact.source_url:
                try:
                    from urllib.parse import urlparse
                    host = urlparse(contact.source_url).hostname or ""
                    if host: source_sites.add(host)
                except Exception:
                    pass

            # ── Dedup by email ────────────────────────────────
            existing = None
            if email:
                existing = db.query(Recruiter).filter(Recruiter.email == email).first()

            # ── Dedup by LinkedIn URL ─────────────────────────
            if not existing and contact.linkedin_url:
                clean_li = contact.linkedin_url.split("?")[0].rstrip("/").lower()
                existing = db.query(Recruiter).filter(
                    Recruiter.linkedin.ilike(f"%{clean_li.split('/in/')[-1]}%")
                ).first()

            if existing:
                # Update if new data improves the record
                updated = False
                if contact.phone and not existing.phone:
                    existing.phone = contact.phone; updated = True
                if contact.linkedin_url and not existing.linkedin:
                    existing.linkedin = contact.linkedin_url.split("?")[0]; updated = True
                if contact.title and not existing.title:
                    existing.title = contact.title; updated = True
                if contact.location and not existing.location:
                    existing.location = contact.location; updated = True
                if updated:
                    db.add(existing)
                duplicates += 1
                continue

            # ── Need at least a name if no email ─────────────
            name = (contact.recruiter_name or "").strip()
            if not name:
                continue

            # ── Resolve or create company ─────────────────────
            company_id = None
            if email:
                email_domain = email.split("@")[-1].lower()
                comp = db.query(Company).filter(
                    Company.primary_domain == email_domain
                ).first()
                if comp:
                    company_id = comp.company_id
                elif contact.company_name:
                    new_comp = Company(
                        company_name=contact.company_name.strip(),
                        canonical_name=contact.company_name.strip(),
                        primary_domain=email_domain,
                        website=f"https://{email_domain}",
                        logo_url=f"https://logos.hunter.io/{email_domain}",
                        verification_status="unverified",
                        trust_score=60,
                        data_source="extension",
                    )
                    db.add(new_comp)
                    db.flush()
                    company_id = new_comp.company_id
            elif contact.company_name:
                comp = db.query(Company).filter(
                    Company.company_name.ilike(contact.company_name.strip())
                ).first()
                if comp:
                    company_id = comp.company_id

            # ── Create new Recruiter ──────────────────────────
            recruiter = Recruiter(
                recruiter_name=name,
                email=email or f"ext_{secrets.token_hex(8)}@noemail.talentops",
                phone=contact.phone,
                linkedin=contact.linkedin_url.split("?")[0] if contact.linkedin_url else None,
                title=contact.title,
                location=contact.location,
                company_id=company_id,
                notes=f"Source: {contact.source or 'extension'} | Page: {contact.source_page_title or ''} | Device: {device_id}",
                data_source="extension",
                is_active=True,
                needs_review=not bool(email),  # flag if no real email
            )
            db.add(recruiter)
            accepted += 1

        except Exception as e:
            errors.append(str(e)[:100])
            logger.warning("Extension batch error: %s", e)

    # Update device stats
    device = db.query(ExtensionDevice).filter(ExtensionDevice.device_id == device_id).first()
    if device:
        device.total_submitted += len(req.contacts)
        device.total_accepted += accepted
        device.total_duplicates += duplicates
        device.last_seen_at = datetime.now(timezone.utc)
        if x_extension_version:
            device.extension_version = x_extension_version

    # Log the submission
    log = ExtensionSubmissionLog(
        device_id=device_id,
        owner_user_id=current_user.id,
        contacts_received=len(req.contacts),
        contacts_accepted=accepted,
        contacts_duplicate=duplicates,
        contacts_errored=len(errors),
        source_sites=json.dumps(list(source_sites)),
    )
    db.add(log)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Extension batch commit failed: %s", e)
        raise HTTPException(status_code=500, detail="Database error during batch insert")

    logger.info(
        "Extension batch: device=%s accepted=%d dup=%d err=%d",
        device_id, accepted, duplicates, len(errors)
    )

    return {
        "accepted": accepted,
        "duplicates": duplicates,
        "errors": errors[:5],  # don't leak too much
    }


# ── POST /recruiters/extension/heartbeat ─────────────────────────────────────

@router.post("/heartbeat")
def extension_heartbeat(
    req: HeartbeatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_extension_user),
):
    """Silent hourly ping from extension — logged for admin reports."""
    hb = ExtensionHeartbeat(
        device_id=req.device_id,
        owner_user_id=current_user.id,
        session_captured=req.session_captured,
        session_sent=req.session_sent,
        session_duplicates=req.session_duplicates,
        queue_pending=req.queue_pending,
        total_ever_sent=req.total_ever_sent,
        extension_version=req.extension_version,
    )
    db.add(hb)

    # Update device last_seen
    device = db.query(ExtensionDevice).filter(ExtensionDevice.device_id == req.device_id).first()
    if device:
        device.last_seen_at = datetime.now(timezone.utc)
        if req.extension_version:
            device.extension_version = req.extension_version

    db.commit()
    return {"ok": True}


# ── GET /recruiters/extension/report — ADMIN ONLY ────────────────────────────

@router.get("/report")
def extension_report(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """
    Admin report: all extension activity for the last N days.
    Shows every device, what it submitted, when it was last active.
    """
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # ── Device summary ────────────────────────────────────────
    devices = db.query(ExtensionDevice).filter(
        ExtensionDevice.owner_user_id == current_user.id
    ).all()

    device_rows = []
    for d in devices:
        last_hb = (
            db.query(ExtensionHeartbeat)
            .filter(ExtensionHeartbeat.device_id == d.device_id)
            .order_by(ExtensionHeartbeat.reported_at.desc())
            .first()
        )
        device_rows.append({
            "device_id": d.device_id,
            "first_seen": str(d.first_seen_at),
            "last_seen": str(d.last_seen_at),
            "version": d.extension_version,
            "total_submitted": d.total_submitted,
            "total_accepted": d.total_accepted,
            "total_duplicates": d.total_duplicates,
            "is_active": d.is_active,
            "last_heartbeat_session_captured": last_hb.session_captured if last_hb else 0,
            "last_heartbeat_queue_pending": last_hb.queue_pending if last_hb else 0,
        })

    # ── Daily summary over last N days ───────────────────────
    daily_sql = text("""
        SELECT
            DATE(submitted_at) AS day,
            SUM(contacts_accepted) AS accepted,
            SUM(contacts_duplicate) AS duplicates,
            SUM(contacts_received) AS received,
            COUNT(DISTINCT device_id) AS active_devices
        FROM extension_submission_logs
        WHERE owner_user_id = :uid
          AND submitted_at >= :cutoff
        GROUP BY DATE(submitted_at)
        ORDER BY day DESC
        LIMIT 90
    """)
    daily_rows = db.execute(daily_sql, {"uid": current_user.id, "cutoff": cutoff}).fetchall()
    daily_summary = [
        {
            "day": str(r[0]),
            "accepted": int(r[1] or 0),
            "duplicates": int(r[2] or 0),
            "received": int(r[3] or 0),
            "active_devices": int(r[4] or 0),
        }
        for r in daily_rows
    ]

    # ── Top source sites ──────────────────────────────────────
    recent_logs = (
        db.query(ExtensionSubmissionLog)
        .filter(
            ExtensionSubmissionLog.owner_user_id == current_user.id,
            ExtensionSubmissionLog.submitted_at >= cutoff,
        )
        .all()
    )
    site_counts: dict = {}
    for log in recent_logs:
        if log.source_sites:
            try:
                sites = json.loads(log.source_sites)
                for s in sites:
                    site_counts[s] = site_counts.get(s, 0) + log.contacts_accepted
            except Exception:
                pass

    top_sites = sorted(site_counts.items(), key=lambda x: x[1], reverse=True)[:20]

    # ── Totals ────────────────────────────────────────────────
    totals_sql = text("""
        SELECT
            COALESCE(SUM(contacts_accepted), 0) AS total_accepted,
            COALESCE(SUM(contacts_duplicate), 0) AS total_duplicates,
            COALESCE(SUM(contacts_received), 0) AS total_received
        FROM extension_submission_logs
        WHERE owner_user_id = :uid AND submitted_at >= :cutoff
    """)
    totals = db.execute(totals_sql, {"uid": current_user.id, "cutoff": cutoff}).fetchone()

    return {
        "period_days": days,
        "totals": {
            "accepted": int(totals[0] or 0),
            "duplicates": int(totals[1] or 0),
            "received": int(totals[2] or 0),
        },
        "devices": device_rows,
        "daily_summary": daily_summary,
        "top_source_sites": [{"site": s, "contacts": c} for s, c in top_sites],
    }


# ── GET/POST /recruiters/extension/codes — ADMIN: Manage Activation Codes ────

@router.get("/codes")
def list_activation_codes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """List all activation codes created by this admin."""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    codes = (
        db.query(ExtensionActivationCode)
        .filter(ExtensionActivationCode.owner_user_id == current_user.id)
        .order_by(ExtensionActivationCode.created_at.desc())
        .all()
    )

    return [
        {
            "id": c.id,
            "code": c.code,
            "label": c.label,
            "max_uses": c.max_uses,
            "use_count": c.use_count,
            "is_active": c.is_active,
            "expires_at": str(c.expires_at) if c.expires_at else None,
            "created_at": str(c.created_at),
        }
        for c in codes
    ]


@router.post("/codes")
def create_activation_code(
    req: CreateCodeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """Create a new activation code."""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Generate readable code like: TALENTOPS-X7KP2M
    charset = string.ascii_uppercase + string.digits
    suffix = ''.join(secrets.choice(charset) for _ in range(8))
    code = f"TALENTOPS-{suffix}"

    expires_at = None
    if req.expires_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=req.expires_days)

    record = ExtensionActivationCode(
        code=code,
        owner_user_id=current_user.id,
        label=req.label or f"Code created {datetime.now().strftime('%Y-%m-%d')}",
        max_uses=req.max_uses,
        expires_at=expires_at,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "code": record.code,
        "label": record.label,
        "max_uses": record.max_uses,
        "expires_at": str(record.expires_at) if record.expires_at else None,
    }


@router.delete("/codes/{code_id}")
def deactivate_activation_code(
    code_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    """Deactivate (revoke) an activation code."""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    record = (
        db.query(ExtensionActivationCode)
        .filter(
            ExtensionActivationCode.id == code_id,
            ExtensionActivationCode.owner_user_id == current_user.id,
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Code not found")

    record.is_active = False
    db.commit()
    return {"ok": True, "code": record.code, "status": "deactivated"}
