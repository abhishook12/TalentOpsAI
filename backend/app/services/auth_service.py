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

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against its hashed version.
    
    Args:
        plain_password: The plaintext password to check.
        hashed_password: The bcrypt hashed password string from the database.
        
    Returns:
        bool: True if the password matches, False otherwise.
    """
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    
    Args:
        password: The plaintext password to hash.
        
    Returns:
        str: The bcrypt hashed password string.
    """
    salt = bcrypt.gensalt(10)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Create a JWT access token for a user session.
    
    Args:
        data: The payload dictionary to encode (e.g., {"sub": user_id, "session_id": session_id}).
        expires_delta: Optional override for the token expiration time.
        
    Returns:
        str: The encoded JWT token string.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(user_id: int) -> str:
    """
    Create a long-lived JWT refresh token.
    
    Args:
        user_id: The ID of the user this token belongs to.
        
    Returns:
        str: The encoded JWT refresh token.
    """
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user_from_request(request: Request, db: Session = Depends(get_db)):
    """
    Extracts, decodes, and validates the JWT access token from the request.
    It checks both cookies and the Authorization header.
    It also validates the session against the database to ensure it hasn't been revoked.
    
    Args:
        request: The FastAPI Request object.
        db: The SQLAlchemy database session.
        
    Returns:
        User: The authenticated User object.
        
    Raises:
        HTTPException: If the token is missing, invalid, expired, or the user/session is inactive.
    """
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
        
        from sqlalchemy.orm import joinedload
        session_id = payload.get("session_id")
        
        if session_id:
            # Single query to check session, user, and load role
            try:
                session_id_int = int(session_id)
            except (ValueError, TypeError):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session ID")
            result = db.query(User, DBSession).join(
                DBSession, DBSession.user_id == User.id
            ).options(
                joinedload(User.role)
            ).filter(
                DBSession.id == session_id_int,
                DBSession.is_active == True,
                User.id == int(user_id)
            ).first()
            
            if not result:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or user not found")
            
            user, db_session = result
        else:
            # Fallback if no session_id in payload (e.g. legacy token)
            user = db.query(User).options(joinedload(User.role)).filter(User.id == int(user_id)).first()

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
        user = get_current_user_from_request(request, db)
        if not user.role or user.role.name.lower() not in [r.lower() for r in allowed_roles]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return role_checker

def require_admin(request: Request, db: Session = Depends(get_db)):
    """
    Enforces strict Admin access.
    Checks if the user's email is the master admin OR they possess the admin role.
    """
    user = get_current_user_from_request(request, db)
    if user.email.lower() == "abhishekjadon824@gmail.com":
        return user
        
    if not user.role or user.role.name.lower() not in ["superadmin", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user

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

