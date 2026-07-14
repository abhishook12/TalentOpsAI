from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import List, Optional, Dict, Any
import math
from datetime import datetime, timedelta

from ..database import get_db
from ..models.auth_models import User, Role, Session as DBSession, LoginHistory
from ..services.auth_service import require_role, get_password_hash, log_audit

router = APIRouter()

@router.get("/analytics")
def get_user_analytics(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(["superadmin", "admin"]))
):
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.status == "Active").count()
    inactive_users = db.query(User).filter(User.status == "Inactive").count()
    
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    new_users = db.query(User).filter(User.created_at >= seven_days_ago).count()
    
    return {
        "total": total_users,
        "active": active_users,
        "inactive": inactive_users,
        "new_last_7_days": new_users
    }

@router.get("/")
def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(["superadmin", "admin"]))
):
    query = db.query(User)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (User.email.ilike(search_filter)) | 
            (User.first_name.ilike(search_filter)) | 
            (User.last_name.ilike(search_filter)) |
            (User.company.ilike(search_filter))
        )
        
    if role:
        role_record = db.query(Role).filter(Role.name == role).first()
        if role_record:
            query = query.filter(User.role_id == role_record.id)
            
    if status:
        query = query.filter(User.status == status)
        
    total_count = query.count()
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "company": u.company,
                "role_name": u.role.name if u.role else "user",
                "status": u.status,
                "created_at": u.created_at,
            }
            for u in users
        ],
        "total": total_count,
        "page": math.floor(skip / limit) + 1,
        "pages": math.ceil(total_count / limit) if limit > 0 else 1
    }

@router.get("/{user_id}")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(["superadmin", "admin"]))
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {
        "id": u.id,
        "email": u.email,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "company": u.company,
        "country": u.country,
        "role_name": u.role.name if u.role else "user",
        "status": u.status,
        "created_at": u.created_at,
    }

@router.post("/")
def create_user(
    user_data: dict = Body(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(["superadmin"]))
):
    email = user_data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
        
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    password = user_data.get("password") or "TempPass123!"
    
    role_name = user_data.get("role_name", "user")
    role_record = db.query(Role).filter(Role.name == role_name).first()
    if not role_record:
        # fallback
        role_record = db.query(Role).filter(Role.name == "user").first()
        
    new_user = User(
        email=email,
        password_hash=get_password_hash(password),
        first_name=user_data.get("first_name", ""),
        last_name=user_data.get("last_name", ""),
        company=user_data.get("company", ""),
        country=user_data.get("country", ""),
        status=user_data.get("status", "Active"),
        role_id=role_record.id if role_record else None
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    log_audit(db, admin.id, f"Created user {new_user.email}", new_value=str(user_data))
    
    return {"status": "success", "user_id": new_user.id}

@router.put("/{user_id}")
def update_user(
    user_id: int,
    user_data: dict = Body(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(["superadmin", "admin"]))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if "first_name" in user_data:
        user.first_name = user_data["first_name"]
    if "last_name" in user_data:
        user.last_name = user_data["last_name"]
    if "company" in user_data:
        user.company = user_data["company"]
    if "country" in user_data:
        user.country = user_data["country"]
        
    db.commit()
    log_audit(db, admin.id, f"Updated user {user.email}", new_value=str(user_data))
    return {"status": "success"}

@router.put("/{user_id}/status")
def update_user_status(
    user_id: int,
    status_data: dict = Body(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(["superadmin"]))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if "status" in status_data:
        user.status = status_data["status"]
        
    if "role_name" in status_data:
        role = db.query(Role).filter(Role.name == status_data["role_name"]).first()
        if not role:
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role_id = role.id
        
    db.commit()
    log_audit(db, admin.id, f"Updated status/role for {user.email}", new_value=str(status_data))
    return {"status": "success", "user_id": user_id}

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(["superadmin"]))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Soft delete
    user.status = "Deleted"
    # Or hard delete: db.delete(user)
    db.commit()
    log_audit(db, admin.id, f"Deleted user {user.email}")
    return {"status": "success"}

@router.post("/{user_id}/force-logout")
def force_logout_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(["superadmin", "admin"]))
):
    sessions = db.query(DBSession).filter(DBSession.user_id == user_id).all()
    for s in sessions:
        s.is_active = False
    db.commit()
    log_audit(db, admin.id, f"Force logged out user {user_id}")
    return {"status": "success", "message": f"Logged out user {user_id}"}

@router.get("/{user_id}/sessions")
def get_user_sessions(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(["superadmin", "admin"]))
):
    sessions = db.query(DBSession).filter(DBSession.user_id == user_id).order_by(DBSession.created_at.desc()).limit(20).all()
    return [
        {
            "id": s.id,
            "device": s.device,
            "browser": s.browser,
            "ip_address": s.ip_address,
            "created_at": s.created_at,
            "expires_at": s.expires_at,
            "is_active": s.is_active
        }
        for s in sessions
    ]

@router.get("/{user_id}/login-history")
def get_user_login_history(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(["superadmin", "admin"]))
):
    history = db.query(LoginHistory).filter(LoginHistory.user_id == user_id).order_by(LoginHistory.timestamp.desc()).limit(50).all()
    return [
        {
            "id": h.id,
            "status": h.status,
            "reason": h.reason,
            "ip_address": h.ip_address,
            "browser": h.browser,
            "os": h.os,
            "timestamp": h.timestamp
        }
        for h in history
    ]

@router.post("/bulk-action")
def bulk_user_action(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(["superadmin"]))
):
    user_ids = payload.get("user_ids", [])
    action = payload.get("action")
    value = payload.get("value")
    
    if not user_ids or not action:
        raise HTTPException(status_code=400, detail="user_ids and action are required")
        
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    
    count = 0
    for user in users:
        if action == "status":
            user.status = value
            count += 1
        elif action == "role":
            role = db.query(Role).filter(Role.name == value).first()
            if role:
                user.role_id = role.id
                count += 1
        elif action == "delete":
            user.status = "Deleted"
            count += 1
            
    db.commit()
    log_audit(db, admin.id, f"Bulk action {action} on {len(users)} users", new_value=str(value))
    return {"status": "success", "updated": count}
