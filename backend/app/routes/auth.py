from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import secrets
import jwt
import time
import hashlib
from collections import defaultdict, deque

from ..database import get_db
from ..models.auth_models import User, Session as DBSession, Role, LoginHistory, PasswordResetToken, EmailVerificationToken
from ..services.auth_service import get_password_hash, verify_password, create_access_token, create_refresh_token, get_current_user_from_request, require_role
from ..services.email_service import send_verification_email, send_password_reset_email
from pydantic import BaseModel, EmailStr
from ..config import JWT_SECRET, ADMIN_PASSWORD, APP_PASSWORD, IS_PRODUCTION, DEV_AUTO_VERIFY
from ..models.models import ActionLog
from ..core.limiter import limiter

router = APIRouter()
ALGORITHM = "HS256"

# -------- Role Seeding Helper --------
def _ensure_default_roles(db: Session):
    """Create default roles if none exist. Idempotent."""
    if db.query(Role).count() > 0:
        return
    defaults = [
        ("superadmin", "Full platform access"),
        ("admin", "Administrative access"),
        ("manager", "Team management access"),
        ("recruiter", "Recruiter access"),
        ("user", "Standard user access"),
        ("readonly", "Read-only access"),
    ]
    for name, desc in defaults:
        db.add(Role(name=name, description=desc))
    db.commit()

_MAX_FAILS = 5
_LOCK_MINUTES = 10

def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def _check_rate_limit(db: Session, ip: str):
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=_LOCK_MINUTES)
    recent_fails = db.query(LoginHistory).filter(
        LoginHistory.ip_address == ip,
        LoginHistory.status == "Failed",
        LoginHistory.timestamp >= cutoff
    ).count()
    if recent_fails >= _MAX_FAILS:
        pass # raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later.")


def _log_admin_event(db: Session, request: Request, action_type: str, status_value: str, details: str | None = None):
    try:
        ip = _client_ip(request)
        db.add(ActionLog(
            user_email=None,
            session_id=None,
            action_type=action_type,
            details=details,
            status=status_value,
            ip_address=ip,
        ))
        db.commit()
    except Exception:
        db.rollback()

def _hash_token(token: str) -> str:
    """SHA-256 hash a token before storing in DB."""
    return hashlib.sha256(token.encode()).hexdigest()


# -------- New API Routes --------

class UserRegister(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    company: str = None
    country: str = None
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False

def _validate_password(password: str):
    """Validate password strength. Raises HTTPException(400) with details on failure."""
    issues = []
    if len(password) < 8:
        issues.append("at least 8 characters")
    if not any(c.isupper() for c in password):
        issues.append("at least 1 uppercase letter")
    if not any(c.islower() for c in password):
        issues.append("at least 1 lowercase letter")
    if not any(c.isdigit() for c in password):
        issues.append("at least 1 digit")
    special_chars = set("!@#$%^&*()_+-=[]{}|;:',.<>?/`~")
    if not any(c in special_chars for c in password):
        issues.append("at least 1 special character (!@#$%^&*()_+-=[]{}|;:',.<>?/`~)")
    if issues:
        raise HTTPException(
            status_code=400,
            detail=f"Password too weak. Missing: {'; '.join(issues)}"
        )

from fastapi import BackgroundTasks
@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, user: UserRegister, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    _validate_password(user.password)
    existing_user = db.query(User).filter(User.email == user.email.lower().strip()).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Seed default roles if table is empty
    _ensure_default_roles(db)
    
    hashed_password = get_password_hash(user.password)
    
    # Assign default role
    default_role = db.query(Role).filter(Role.name == "user").first()
    
    # Determine user status
    initial_status = "Active" if DEV_AUTO_VERIFY else "Pending Verification"
    
    # First user ever → make superadmin and active
    is_first_user = db.query(User).count() == 0
    if is_first_user:
        default_role = db.query(Role).filter(Role.name == "superadmin").first() or default_role
        initial_status = "Active"
    
    from ..utils.sanitize import sanitize_html
    new_user = User(
        first_name=sanitize_html(user.first_name.strip()),
        last_name=sanitize_html(user.last_name.strip()),
        email=user.email.lower().strip(),
        company=sanitize_html(user.company) if user.company else None,
        country=sanitize_html(user.country) if user.country else None,
        password_hash=hashed_password,
        status=initial_status,
        role_id=default_role.id if default_role else None
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    if initial_status == "Pending Verification":
        token = secrets.token_hex(32)
        verification = EmailVerificationToken(
            user_id=new_user.id,
            token_hash=_hash_token(token),
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
        )
        db.add(verification)
        db.commit()
        background_tasks.add_task(send_verification_email, new_user.email, token)
    
    result = {
        "message": "User registered successfully",
        "user_id": new_user.id,
        "status": initial_status,
    }
    if is_first_user:
        result["note"] = "First user created as superadmin with Active status."
    elif initial_status == "Pending Verification":
        result["note"] = "Please verify your email address to activate your account."
        
    return result

def _handle_trusted_device(request: Request, response: Response, db: Session, user: User, user_agent: str, ip: str):
    from ..models.auth_models import TrustedDevice, AuditLog
    device_id = request.cookies.get("device_id")
    
    if not device_id:
        device_id = secrets.token_hex(32)
        
    device_hash = _hash_token(device_id)
    trusted_device = db.query(TrustedDevice).filter(TrustedDevice.device_id_hash == device_hash).first()
    
    device_name = "Unknown Device"
    device_type = "Desktop"
    browser_version = "Unknown"
    
    if user_agent:
        browser = "Unknown Browser"
        if "Chrome/" in user_agent: 
            browser = "Chrome"
            browser_version = user_agent.split("Chrome/")[1].split(" ")[0]
        elif "Firefox/" in user_agent: 
            browser = "Firefox"
            browser_version = user_agent.split("Firefox/")[1].split(" ")[0]
        elif "Safari/" in user_agent and "Chrome" not in user_agent: 
            browser = "Safari"
            browser_version = user_agent.split("Version/")[1].split(" ")[0] if "Version/" in user_agent else "Unknown"
        elif "Edge/" in user_agent: 
            browser = "Edge"
            browser_version = user_agent.split("Edge/")[1].split(" ")[0]
        elif "Edg/" in user_agent:
            browser = "Edge"
            browser_version = user_agent.split("Edg/")[1].split(" ")[0]
            
        os_name = "Unknown OS"
        if "Windows" in user_agent: os_name = "Windows"
        elif "Mac" in user_agent: os_name = "macOS"
        elif "Linux" in user_agent: os_name = "Linux"
        elif "Android" in user_agent: 
            os_name = "Android"
            device_type = "Mobile"
        elif "iOS" in user_agent or "iPhone" in user_agent: 
            os_name = "iOS"
            device_type = "Mobile"
        elif "iPad" in user_agent:
            os_name = "iOS"
            device_type = "Tablet"
            
        device_name = f"{browser} on {os_name}"
        
    language = request.headers.get("accept-language", "").split(",")[0] if request.headers.get("accept-language") else "Unknown"
    req_timezone = request.headers.get("x-timezone", "UTC")
    location = "Unknown Location" # Could be enhanced with GeoIP later
    
    if not trusted_device:
        trusted_device = TrustedDevice(
            device_id_hash=device_hash,
            user_id=user.id,
            device_name=device_name,
            device_type=device_type,
            browser_version=browser_version,
            timezone=req_timezone,
            language=language,
            location=location,
            ip_address=ip,
            browser=user_agent,
            os=user_agent,
            status='Pending'
        )
        db.add(trusted_device)
        db.commit()
        db.refresh(trusted_device)
        
        # Log device request
        audit = AuditLog(
            action="device_request",
            target_user_id=user.id,
            target_device_id=trusted_device.id,
            ip_address=ip,
            device=device_name,
            reason="New device detected",
            status="success"
        )
        db.add(audit)
        db.commit()
    else:
        # Update volatile fields
        trusted_device.ip_address = ip
        trusted_device.login_attempts += 1
        db.commit()
        
    # Auto-approve devices for superadmin to prevent lockout
    if trusted_device.status == 'Pending' and user.role and user.role.name in ['superadmin', 'admin']:
        trusted_device.status = 'Trusted'
        trusted_device.approved_by = user.id
        db.commit()
            
    # Always ensure the cookie is set, especially if we just generated it
    response.set_cookie(
        key="device_id",
        value=device_id,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
        max_age=365*24*60*60 # 1 year
    )
    
    if trusted_device.status == 'Blocked':
        audit = AuditLog(action="login_blocked", target_user_id=user.id, target_device_id=trusted_device.id, ip_address=ip, device=device_name, reason="Device is permanently blocked", status="failed")
        db.add(audit)
        db.commit()
        raise HTTPException(status_code=403, detail="Access Restricted: This device has been permanently blocked by an administrator.")
        
    if trusted_device.status != 'Trusted':
        # Log failure
        history = LoginHistory(
            user_id=user.id,
            email=user.email,
            status="Failed",
            reason="Device not trusted",
            ip_address=ip,
            browser=user_agent
        )
        db.add(history)
        
        audit = AuditLog(action="login_denied", target_user_id=user.id, target_device_id=trusted_device.id, ip_address=ip, device=device_name, reason="Device pending approval", status="failed")
        db.add(audit)
        db.commit()
        
        cookie_val = f"device_id={device_id}; HttpOnly; SameSite=Lax; Max-Age=31536000; Path=/"
        if IS_PRODUCTION:
            cookie_val += "; Secure"
            
        raise HTTPException(
            status_code=403, 
            detail="Access Restricted: This device has not yet been approved for access.",
            headers={"Set-Cookie": cookie_val}
        )
        
    trusted_device.last_login = datetime.now(timezone.utc).replace(tzinfo=None)
    trusted_device.login_attempts = 0 # reset on successful login
    db.commit()
    
    audit = AuditLog(action="login_success", target_user_id=user.id, target_device_id=trusted_device.id, ip_address=ip, device=device_name, reason="Successful login from trusted device", status="success")
    db.add(audit)
    db.commit()
    
    return trusted_device

@router.get("/device-status")
def get_device_status(request: Request, db: Session = Depends(get_db)):
    from ..models.auth_models import TrustedDevice
    device_id = request.cookies.get("device_id")
    if not device_id:
        return {"status": "Unknown"}
        
    device_hash = _hash_token(device_id)
    trusted_device = db.query(TrustedDevice).filter(TrustedDevice.device_id_hash == device_hash).first()
    
    if not trusted_device:
        return {"status": "Unknown"}
        
    return {"status": trusted_device.status}

@router.post("/login")
# @limiter.limit("10/minute")
def login(request: Request, login_data: UserLogin, response: Response, db: Session = Depends(get_db)):
    ip = _client_ip(request)
    
    # Rate Limiting Check
    _check_rate_limit(db, ip)

    user = db.query(User).filter(User.email == login_data.email).first()
    user_agent = request.headers.get("user-agent")
    
    if not user or user.auth_provider not in ['local', 'both'] or not user.password_hash or not verify_password(login_data.password, user.password_hash):
        history = LoginHistory(
            user_id=user.id if user else None,
            email=login_data.email,
            status="Failed",
            reason="Invalid credentials",
            ip_address=ip,
            browser=user_agent
        )
        db.add(history)
        db.commit()
        # Generic error — never reveal whether email or password is wrong
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    if user.status == "Pending Verification":
        history = LoginHistory(
            user_id=user.id,
            email=login_data.email,
            status="Failed",
            reason="Pending Verification",
            ip_address=ip,
            browser=user_agent
        )
        db.add(history)
        db.commit()
        raise HTTPException(status_code=403, detail="Please verify your email address before logging in.")
        
    elif user.status != "Active":
        history = LoginHistory(
            user_id=user.id,
            email=login_data.email,
            status="Failed",
            reason=f"Account status: {user.status}",
            ip_address=ip,
            browser=user_agent
        )
        db.add(history)
        db.commit()
        raise HTTPException(status_code=403, detail=f"Account is {user.status}. Please contact support.")

    # Trusted Device Check
    trusted_device = _handle_trusted_device(request, response, db, user, user_agent, ip)

    # Create Session
    session_token = secrets.token_hex(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30 if login_data.remember_me else 1)
    
    db_session = DBSession(
        user_id=user.id,
        token_hash=_hash_token(session_token),
        trusted_device_id=trusted_device.id,
        device=user_agent,
        browser=user_agent,
        ip_address=ip,
        expires_at=expires_at
    )
    db.add(db_session)
    
    history = LoginHistory(
        user_id=user.id,
        email=login_data.email,
        status="Success",
        ip_address=ip,
        browser=user_agent
    )
    db.add(history)
    db.commit()
    db.refresh(db_session)
    
    access_token = create_access_token(
        data={"sub": str(user.id), "session_id": db_session.id},
        expires_delta=timedelta(days=30) if login_data.remember_me else timedelta(hours=12)
    )
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
        max_age=30*24*60*60 if login_data.remember_me else None
    )
    
    refresh_token = create_refresh_token(user.id)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
        max_age=30*24*60*60
    )
    
    return {
        "message": "Login successful",
        "token": access_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role.name if user.role else "None",
            "avatar_url": user.avatar_url,
            "company": user.company
        }
    }

class GoogleAuthRequest(BaseModel):
    credential: str

@router.post("/google")
@limiter.limit("10/minute")
def google_auth(request: Request, data: GoogleAuthRequest, response: Response, db: Session = Depends(get_db)):
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    import os
    
    ip = _client_ip(request)
    _check_rate_limit(db, ip)
    
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    if not client_id:
        # If client ID is missing, we must fail gracefully. But for local dev mock, we can accept a mock token.
        if data.credential == "mock_google_token" and not IS_PRODUCTION:
            idinfo = {
                "email": "googleuser@example.com",
                "given_name": "Google",
                "family_name": "User",
                "sub": "mock_google_sub_123",
                "picture": ""
            }
        else:
            raise HTTPException(status_code=500, detail="Google Auth is not configured on this server.")
    else:
        try:
            idinfo = id_token.verify_oauth2_token(data.credential, google_requests.Request(), client_id)
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid Google token")

    email = idinfo.get("email", "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Google token missing email")

    user = db.query(User).filter(User.email == email).first()
    user_agent = request.headers.get("user-agent")

    if user:
        if user.auth_provider != "google" and user.auth_provider != "both":
            # Account linking: Google guarantees the email, so we upgrade to "both" seamlessly
            user.auth_provider = "both"
            if not user.provider_id:
                user.provider_id = idinfo.get("sub")
            if not user.avatar_url:
                user.avatar_url = idinfo.get("picture", "")
            if user.status == "Pending Verification":
                user.status = "Active"
            db.commit()
            
        if user.status != "Active":
            raise HTTPException(status_code=403, detail=f"Account is {user.status}.")
    else:
        # Create new user
        _ensure_default_roles(db)
        default_role = db.query(Role).filter(Role.name == "user").first()
        is_first_user = db.query(User).count() == 0
        if is_first_user:
            default_role = db.query(Role).filter(Role.name == "superadmin").first() or default_role

        user = User(
            first_name=idinfo.get("given_name", ""),
            last_name=idinfo.get("family_name", ""),
            email=email,
            auth_provider="google",
            provider_id=idinfo.get("sub"),
            avatar_url=idinfo.get("picture", ""),
            status="Active", # Google emails are already verified
            role_id=default_role.id if default_role else None
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Trusted Device Check
    trusted_device = _handle_trusted_device(request, response, db, user, user_agent, ip)

    # Create Session
    session_token = secrets.token_hex(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    
    db_session = DBSession(
        user_id=user.id,
        token_hash=_hash_token(session_token),
        trusted_device_id=trusted_device.id,
        device=user_agent, browser=user_agent, ip_address=ip, expires_at=expires_at
    )
    db.add(db_session)
    
    history = LoginHistory(
        user_id=user.id, email=email, status="Success", ip_address=ip, browser=user_agent
    )
    db.add(history)
    db.commit()
    db.refresh(db_session)
    
    access_token = create_access_token(
        data={"sub": str(user.id), "session_id": db_session.id},
        expires_delta=timedelta(days=30)
    )
    
    response.set_cookie(
        key="access_token", value=access_token, httponly=True, secure=IS_PRODUCTION, samesite="lax", max_age=30*24*60*60
    )
    
    refresh_token = create_refresh_token(user.id)
    response.set_cookie(
        key="refresh_token", value=refresh_token, httponly=True, secure=IS_PRODUCTION, samesite="lax", max_age=30*24*60*60
    )
    
    return {
        "message": "Google Login successful",
        "token": access_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role.name if user.role else "None",
            "avatar_url": user.avatar_url,
            "company": user.company
        }
    }

@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if token:
        try:
            from ..services.auth_service import SECRET_KEY, ALGORITHM
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            session_id = payload.get("session_id")
            if session_id:
                db_session = db.query(DBSession).filter(DBSession.id == session_id).first()
                if db_session:
                    db_session.is_active = False
                    db.commit()
        except Exception:
            pass
            
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    # Also delete legacy cookies
    response.delete_cookie("admin_session")
    response.delete_cookie("app_session")
    return {"message": "Logged out successfully"}

@router.get("/me")
def get_me(request: Request, db: Session = Depends(get_db)):
    try:
        user = get_current_user_from_request(request, db)
        return {
            "authenticated": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role.name if user.role else "None",
                "avatar_url": user.avatar_url,
                "company": user.company
            }
        }
    except HTTPException:
        # Fallback to legacy auth_me behavior
        cookie_token = request.cookies.get("admin_session")
        if cookie_token:
            try:
                payload = jwt.decode(cookie_token, JWT_SECRET, algorithms=[ALGORITHM])
                if payload.get("role") == "admin":
                    return {"authenticated": True, "role": "admin"}
            except Exception:
                pass
        return {"authenticated": False}

# Add old admin login endpoint to preserve frontend UI until we swap it out
class LegacyLoginRequest(BaseModel):
    password: str
    remember_device: bool = False

@router.post("/admin-login")
def admin_login(req: LegacyLoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = _client_ip(request)
    _check_rate_limit(db, ip)

    if req.password != ADMIN_PASSWORD:
        history = LoginHistory(
            email="admin",
            status="Failed",
            reason="Invalid admin password",
            ip_address=ip,
            browser=request.headers.get("user-agent")
        )
        db.add(history)
        db.commit()
        _log_admin_event(db, request, "ADMIN_LOGIN_FAILED", "failed", details="invalid_password")
        raise HTTPException(status_code=401, detail="Invalid admin password.")

    _log_admin_event(db, request, "ADMIN_LOGIN_SUCCESS", "success")

    expires_seconds = 30 * 24 * 3600 if req.remember_device else 12 * 3600
    token = jwt.encode({"role": "admin", "exp": time.time() + expires_seconds}, JWT_SECRET, algorithm=ALGORITHM)

    response.set_cookie(
        key="admin_session",
        value=token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
        max_age=expires_seconds
    )
    return {"message": "Admin login successful", "token": token}

# -------- Phase 2 Auth Flows --------

class VerifyEmailRequest(BaseModel):
    token: str

@router.post("/verify-email")
def verify_email(req: VerifyEmailRequest, db: Session = Depends(get_db)):
    token_record = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token_hash == _hash_token(req.token),
        EmailVerificationToken.is_used == False
    ).first()
    
    if not token_record or token_record.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(status_code=400, detail="Invalid or expired token")
        
    user = db.query(User).filter(User.id == token_record.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.status = "Active"
    token_record.is_used = True
    db.commit()
    
    return {"message": "Email verified successfully"}

class ResendVerificationRequest(BaseModel):
    email: EmailStr

@router.post("/resend-verification")
def resend_verification(req: ResendVerificationRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if not user or user.status == "Active":
        return {"message": "If the email is registered and unverified, a new link has been sent."}
        
    token = secrets.token_hex(32)
    verification = EmailVerificationToken(
        user_id=user.id,
        token_hash=_hash_token(token),
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
    )
    db.add(verification)
    db.commit()
    
    send_verification_email(user.email, token)
    return {"message": "If the email is registered and unverified, a new link has been sent."}

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

@router.post("/forgot-password")
@limiter.limit("3/minute")
def forgot_password(request: Request, req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if not user:
        return {"message": "If the email is registered, a password reset link has been sent."}
        
    token = secrets.token_hex(32)
    reset_record = PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_token(token),
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
    )
    db.add(reset_record)
    db.commit()
    
    send_password_reset_email(user.email, token)
    return {"message": "If the email is registered, a password reset link has been sent."}

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@router.post("/reset-password")
@limiter.limit("3/minute")
def reset_password(request: Request, req: ResetPasswordRequest, db: Session = Depends(get_db)):
    _validate_password(req.new_password)
    token_record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == _hash_token(req.token),
        PasswordResetToken.is_used == False
    ).first()
    
    if not token_record or token_record.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(status_code=400, detail="Invalid or expired token")
        
    user = db.query(User).filter(User.id == token_record.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.password_hash = get_password_hash(req.new_password)
    token_record.is_used = True
    
    # Invalidate all existing sessions
    db.query(DBSession).filter(DBSession.user_id == user.id).update({"is_active": False})
    
    db.commit()
    return {"message": "Password has been reset successfully"}

@router.post("/refresh")
def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token_cookie = request.cookies.get("refresh_token")
    if not refresh_token_cookie:
        raise HTTPException(status_code=401, detail="Refresh token missing")
        
    from ..services.auth_service import SECRET_KEY, ALGORITHM
    try:
        payload = jwt.decode(refresh_token_cookie, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
            
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or user.status != "Active":
            raise HTTPException(status_code=403, detail="Invalid user")
            
        # Issue new session and tokens
        session_token = secrets.token_hex(32)
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
        
        db_session = DBSession(
            user_id=user.id,
            token_hash=_hash_token(session_token),
            device=request.headers.get("user-agent"),
            browser=request.headers.get("user-agent"),
            ip_address=_client_ip(request),
            expires_at=expires_at
        )
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        
        access_token = create_access_token(
            data={"sub": str(user.id), "session_id": db_session.id},
            expires_delta=timedelta(hours=12)
        )
        
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=IS_PRODUCTION,
            samesite="lax",
            max_age=12*60*60
        )
        
        return {"message": "Token refreshed"}
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@router.get("/sessions")
def get_my_sessions(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_request(request, db)
    sessions = db.query(DBSession).filter(DBSession.user_id == user.id, DBSession.is_active == True).order_by(DBSession.created_at.desc()).all()
    
    # We need the current session ID to highlight it
    current_session_id = None
    token = request.cookies.get("access_token")
    if token:
        try:
            from ..services.auth_service import SECRET_KEY, ALGORITHM
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            current_session_id = payload.get("session_id")
        except:
            pass

    return {
        "sessions": [
            {
                "id": s.id,
                "device": s.device,
                "browser": s.browser,
                "ip_address": s.ip_address,
                "created_at": s.created_at,
                "expires_at": s.expires_at,
                "is_current": s.id == current_session_id
            } for s in sessions
        ]
    }

@router.delete("/sessions/{session_id}")
def logout_session(session_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_request(request, db)
    db_session = db.query(DBSession).filter(DBSession.id == session_id, DBSession.user_id == user.id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    db_session.is_active = False
    db.commit()
    return {"message": "Session logged out"}

