import jwt
import hashlib
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from fastapi import HTTPException, status, Request, Depends
from sqlalchemy.orm import Session
from ..models.auth_models import User, Session as DBSession
from ..database import get_db
from ..config import JWT_SECRET

# Configuration — unified: uses JWT_SECRET from config.py
SECRET_KEY = JWT_SECRET
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30

import bcrypt

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(user_id: int):
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user_from_request(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        # Check authorization header as fallback
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        
        # Verify Session validity in DB if necessary
        session_id = payload.get("session_id")
        if session_id:
            db_session = db.query(DBSession).filter(DBSession.id == session_id, DBSession.is_active == True).first()
            if not db_session:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or revoked")
            
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        if user.status != "Active":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active")
        
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

def require_role(allowed_roles: list[str]):
    def role_checker(request: Request, db: Session = Depends(get_db)):
        from ..config import FREE_ADMIN_MODE
        if FREE_ADMIN_MODE and any(r.lower() in ["admin", "superadmin"] for r in allowed_roles):
            # Bypass authentication for admin routes in FREE_ADMIN_MODE
            return User(id=0, email="dev@system", first_name="Dev", last_name="Admin")
            
        user = get_current_user_from_request(request, db)
        if not user.role or user.role.name.lower() not in [r.lower() for r in allowed_roles]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return role_checker

def require_permission(permission_name: str):
    def permission_checker(request: Request, db: Session = Depends(get_db)):
        user = get_current_user_from_request(request, db)
        if not user.role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No role assigned")
            
        from ..models.auth_models import RolePermission, Permission
        has_perm = db.query(RolePermission).join(Permission).filter(
            RolePermission.role_id == user.role_id,
            Permission.name == permission_name
        ).first()
        
        if not has_perm:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
            
        return user
    return permission_checker

def log_audit(db: Session, user_id: int, action: str, previous_value: str = None, new_value: str = None, ip_address: str = None, device: str = None):
    from ..models.auth_models import AuditLog
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        previous_value=previous_value,
        new_value=new_value,
        ip_address=ip_address,
        device=device
    )
    db.add(audit_log)
    db.commit()

