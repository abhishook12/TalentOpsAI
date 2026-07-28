import os

file_path = r'C:\TalentOpsAI\backend\app\routes\admin_devices.py'
with open(file_path, 'a', encoding='utf-8') as f:
    f.write("""
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
""")
print("admin_devices.py endpoints appended successfully.")
