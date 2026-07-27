from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from pydantic import BaseModel
from datetime import datetime, timezone
import os

from ..database import get_db
from ..models.auth_models import TrustedDevice, User, Session as DBSession, LoginHistory, AuditLog
from ..services.auth_service import require_admin, require_role, get_current_user_from_request

router = APIRouter()

@router.get("/stats")
def get_device_stats(request: Request, db: Session = Depends(get_db)):
    admin_user = require_admin(request, db)
    
    trusted = db.query(TrustedDevice).filter(TrustedDevice.status == 'Trusted').count()
    pending = db.query(TrustedDevice).filter(TrustedDevice.status == 'Pending').count()
    blocked = db.query(TrustedDevice).filter(TrustedDevice.status == 'Blocked').count()
    revoked = db.query(TrustedDevice).filter(TrustedDevice.status == 'Revoked').count()
    active_sessions = db.query(DBSession).filter(DBSession.is_active == True).count()
    
    last_login_obj = db.query(TrustedDevice.last_login).order_by(TrustedDevice.last_login.desc()).first()
    last_login = last_login_obj[0] if last_login_obj and last_login_obj[0] else None
    
    return {
        "trusted": trusted,
        "pending": pending,
        "blocked": blocked,
        "revoked": revoked,
        "active_sessions": active_sessions,
        "last_login": last_login
    }

@router.get("/pending/count")
def get_pending_count(request: Request, db: Session = Depends(get_db)):
    admin_user = require_admin(request, db)
    count = db.query(TrustedDevice).filter(TrustedDevice.status == 'Pending').count()
    return {"count": count}

@router.get("/sessions/active")
def get_active_sessions(request: Request, db: Session = Depends(get_db)):
    admin_user = require_admin(request, db)
    sessions = db.query(DBSession).options(joinedload(DBSession.user)).filter(DBSession.is_active == True).order_by(DBSession.created_at.desc()).limit(1000).all()
    result = []
    for s in sessions:
        result.append({
            "id": s.id,
            "user_email": s.user.email if s.user else "Unknown",
            "user_name": f"{s.user.first_name} {s.user.last_name}" if s.user else "Unknown",
            "device": s.device,
            "browser": s.browser,
            "ip_address": s.ip_address,
            "created_at": s.created_at,
            "expires_at": s.expires_at,
            "trusted_device_id": s.trusted_device_id
        })
    return result

@router.get("/")
def list_devices(request: Request, db: Session = Depends(get_db)):
    admin_user = require_admin(request, db)
    
    devices = db.query(TrustedDevice).options(
        joinedload(TrustedDevice.user)
    ).all()
    
    session_counts_raw = db.query(
        DBSession.trusted_device_id,
        func.count(DBSession.id)
    ).filter(
        DBSession.is_active == True,
        DBSession.trusted_device_id != None
    ).group_by(DBSession.trusted_device_id).all()
    
    session_counts = {device_id: count for device_id, count in session_counts_raw}
    
    result = []
    for d in devices:
        result.append({
            "id": d.id,
            "user_id": d.user.id if d.user else None,
            "user_email": d.user.email if d.user else "Unknown",
            "user_name": f"{d.user.first_name} {d.user.last_name}" if d.user else "Unknown",
            "avatar_url": d.user.avatar_url if d.user else None,
            "auth_provider": d.user.auth_provider if d.user else None,
            "browser": d.browser,
            "os": d.os,
            "device_name": d.device_name,
            "device_type": getattr(d, 'device_type', 'Desktop'),
            "browser_version": getattr(d, 'browser_version', 'Unknown'),
            "location": getattr(d, 'location', 'Unknown'),
            "ip_address": getattr(d, 'ip_address', 'Unknown'),
            "risk_level": getattr(d, 'risk_level', 'low'),
            "last_login": d.last_login,
            "status": d.status,
            "created_at": d.created_at,
            "active_sessions": session_counts.get(d.id, 0)
        })
    return result

@router.get("/{device_id}")
def get_device_detail(device_id: int, request: Request, db: Session = Depends(get_db)):
    admin_user = require_admin(request, db)
    device = db.query(TrustedDevice).options(joinedload(TrustedDevice.user)).filter(TrustedDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    return {
        "id": device.id,
        "user_email": device.user.email if device.user else "Unknown",
        "user_name": f"{device.user.first_name} {device.user.last_name}" if device.user else "Unknown",
        "browser": device.browser,
        "os": device.os,
        "device_name": device.device_name,
        "device_type": getattr(device, 'device_type', 'Desktop'),
        "browser_version": getattr(device, 'browser_version', 'Unknown'),
        "location": getattr(device, 'location', 'Unknown'),
        "ip_address": getattr(device, 'ip_address', 'Unknown'),
        "language": getattr(device, 'language', 'Unknown'),
        "timezone": getattr(device, 'timezone', 'UTC'),
        "first_seen": getattr(device, 'first_seen', device.created_at),
        "login_attempts": getattr(device, 'login_attempts', 1),
        "risk_level": getattr(device, 'risk_level', 'low'),
        "last_login": device.last_login,
        "status": device.status,
        "created_at": device.created_at,
        "updated_at": device.updated_at
    }

class StatusUpdate(BaseModel):
    status: str # Trusted, Revoked, Disabled, Pending, Blocked

@router.put("/{device_id}/status")
def update_device_status(device_id: int, payload: StatusUpdate, request: Request, db: Session = Depends(get_db)):
    admin_user = require_admin(request, db)
    
    device = db.query(TrustedDevice).filter(TrustedDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    old_status = device.status
    new_status = payload.status
    
    if new_status not in ['Trusted', 'Revoked', 'Disabled', 'Pending', 'Blocked']:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    device.status = new_status
    if new_status == 'Trusted':
        device.approved_by = admin_user.id
        
        # Identity-First: If the user is Pending Verification, approving their device also approves their account
        if device.user and device.user.status == 'Pending Verification':
            device.user.status = 'Active'
            db.add(device.user)
        
        # Check MAX_DEVICES_PER_USER
        max_devices = int(os.getenv("MAX_DEVICES_PER_USER", "0"))
        if max_devices == 1:
            # Revoke all other devices for this user
            other_devices = db.query(TrustedDevice).filter(
                TrustedDevice.user_id == device.user_id,
                TrustedDevice.id != device.id,
                TrustedDevice.status == 'Trusted'
            ).all()
            for od in other_devices:
                od.status = 'Revoked'
                # Terminate their sessions
                db.query(DBSession).filter(DBSession.trusted_device_id == od.id).update({"is_active": False})
                
    elif new_status in ['Revoked', 'Disabled', 'Blocked']:
        # Terminate all active sessions for this device immediately
        db.query(DBSession).filter(DBSession.trusted_device_id == device.id).update({"is_active": False})
        
    audit = AuditLog(
        user_id=admin_user.id,
        target_user_id=device.user_id,
        target_device_id=device.id,
        action="update_device_status",
        previous_value=old_status,
        new_value=new_status,
        device=str(device_id),
        reason=f"Status manually changed to {new_status} by admin",
        status="success"
    )
    db.add(audit)
    db.commit()
    
    return {"message": f"Device status updated to {new_status}"}

@router.delete("/{device_id}/sessions")
def force_logout_device(device_id: int, request: Request, db: Session = Depends(get_db)):
    admin_user = require_admin(request, db)
    
    device = db.query(TrustedDevice).filter(TrustedDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    updated = db.query(DBSession).filter(DBSession.trusted_device_id == device_id, DBSession.is_active == True).update({"is_active": False})
    
    audit = AuditLog(
        user_id=admin_user.id,
        target_device_id=device_id,
        action="force_logout_device",
        previous_value="active",
        new_value="inactive",
        device=str(device_id),
        reason="Admin forced logout",
        status="success"
    )
    db.add(audit)
    db.commit()
    
    return {"message": f"Terminated {updated} active sessions for this device"}

class RenameUpdate(BaseModel):
    name: str

@router.put("/{device_id}/rename")
def rename_device(device_id: int, payload: RenameUpdate, request: Request, db: Session = Depends(get_db)):
    admin_user = require_admin(request, db)
    device = db.query(TrustedDevice).filter(TrustedDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    old_name = device.device_name
    device.device_name = payload.name
    
    audit = AuditLog(
        user_id=admin_user.id,
        target_device_id=device_id,
        action="rename_device",
        previous_value=old_name,
        new_value=payload.name,
        device=str(device_id),
        status="success"
    )
    db.add(audit)
    db.commit()
    return {"message": "Device renamed successfully"}

@router.get("/{device_id}/audit")
def get_device_audit(device_id: int, request: Request, db: Session = Depends(get_db)):
    admin_user = require_admin(request, db)
    logs = db.query(AuditLog).filter(
        (AuditLog.target_device_id == device_id) | (AuditLog.device == str(device_id))
    ).order_by(AuditLog.timestamp.desc()).limit(100).all()
    
    return [{
        "id": l.id,
        "action": l.action,
        "reason": getattr(l, 'reason', None),
        "status": getattr(l, 'status', None),
        "previous_value": l.previous_value,
        "new_value": l.new_value,
        "ip_address": l.ip_address,
        "timestamp": l.timestamp
    } for l in logs]

@router.get("/{device_id}/sessions")
def get_device_sessions(device_id: int, request: Request, db: Session = Depends(get_db)):
    admin_user = require_admin(request, db)
    sessions = db.query(DBSession).filter(DBSession.trusted_device_id == device_id).order_by(DBSession.created_at.desc()).limit(50).all()
    
    return [{
        "id": s.id,
        "ip_address": s.ip_address,
        "browser": s.browser,
        "is_active": s.is_active,
        "created_at": s.created_at,
        "expires_at": s.expires_at
    } for s in sessions]

class BulkTerminate(BaseModel):
    session_ids: list[int]

@router.delete("/all")
def clear_all_devices(request: Request, db: Session = Depends(get_db)):
    admin_user = require_admin(request, db)
    # Don't delete the device associated with the current session
    current_device_id = request.cookies.get("device_id")
    
    if current_device_id:
        from ..routes.auth import _hash_token
        current_hash = _hash_token(current_device_id)
        db.query(TrustedDevice).filter(TrustedDevice.device_id_hash != current_hash).delete(synchronize_session=False)
    else:
        db.query(TrustedDevice).delete(synchronize_session=False)
    db.commit()
    return {"message": "All other trusted devices cleared"}

@router.delete("/pending")
def clear_pending_devices(request: Request, db: Session = Depends(get_db)):
    admin_user = require_admin(request, db)
    db.query(TrustedDevice).filter(TrustedDevice.status == 'Pending').delete(synchronize_session=False)
    db.commit()
    return {"message": "All pending devices cleared"}

@router.post("/sessions/bulk-terminate")
def bulk_terminate_sessions(payload: BulkTerminate, request: Request, db: Session = Depends(get_db)):
    admin_user = require_admin(request, db)
    
    current_session_token = request.cookies.get("session")
    if current_session_token:
        from ..routes.auth import _hash_token
        current_session_hash = _hash_token(current_session_token)
        current_session = db.query(DBSession).filter(DBSession.token_hash == current_session_hash).first()
        if current_session and current_session.id in payload.session_ids:
            raise HTTPException(status_code=400, detail="Cannot bulk-terminate your own active session. Use the logout button.")

    updated = db.query(DBSession).filter(DBSession.id.in_(payload.session_ids)).update({"is_active": False, "device": "Terminated by admin"}, synchronize_session=False)
    
    for sid in payload.session_ids:
        audit = AuditLog(
            user_id=admin_user.id,
            action="force_logout_session",
            previous_value="active",
            new_value="inactive",
            reason="Admin bulk termination",
            status="success"
        )
        db.add(audit)
    db.commit()
    
    return {"message": f"Terminated {updated} sessions"}

@router.delete("/sessions/all")
def terminate_all_sessions(request: Request, db: Session = Depends(get_db)):
    admin_user = require_admin(request, db)
    
    current_session_token = request.cookies.get("session")
    if current_session_token:
        from ..routes.auth import _hash_token
        current_session_hash = _hash_token(current_session_token)
        updated = db.query(DBSession).filter(DBSession.token_hash != current_session_hash, DBSession.is_active == True).update({"is_active": False, "device": "Terminated by admin"}, synchronize_session=False)
    else:
        updated = db.query(DBSession).filter(DBSession.is_active == True).update({"is_active": False, "device": "Terminated by admin"}, synchronize_session=False)
        
    audit = AuditLog(
        user_id=admin_user.id,
        action="force_logout_all",
        reason="Admin terminated all sessions",
        status="success"
    )
    db.add(audit)
    db.commit()
    return {"message": f"Terminated {updated} sessions"}

@router.delete("/sessions/expired")
def clear_expired_sessions(request: Request, db: Session = Depends(get_db)):
    admin_user = require_admin(request, db)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    deleted = db.query(DBSession).filter((DBSession.expires_at < now) | (DBSession.is_active == False)).delete(synchronize_session=False)
    db.commit()
    return {"message": f"Cleared {deleted} expired/inactive sessions"}
