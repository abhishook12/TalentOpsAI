from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from pydantic import BaseModel
import jwt
import time
import logging
from app.config import JWT_SECRET, ADMIN_PASSWORD, APP_PASSWORD, IS_PRODUCTION, FREE_ADMIN_MODE
from app.database import get_db
from sqlalchemy.orm import Session
from app.models.models import ActionLog
from datetime import datetime
from collections import defaultdict, deque

logger = logging.getLogger("talentops")
router = APIRouter()
ALGORITHM = "HS256"


class LoginRequest(BaseModel):
    password: str
    remember_device: bool = False


def create_access_token(data: dict, expires_delta_seconds: int):
    to_encode = data.copy()
    expire = time.time() + expires_delta_seconds
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)


def _decode_admin_token(token: str):
    payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    if payload.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Invalid role.")
    return payload


def _decode_app_token(token: str):
    payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    if payload.get("role") != "user":
        raise HTTPException(status_code=401, detail="Invalid role.")
    return payload


def _extract_token(request: Request, cookie_name: str):
    cookie_token = request.cookies.get(cookie_name)
    if cookie_token:
        return cookie_token
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None


# -------- Rate limiting (in-memory) --------
# NOTE: This is per-process. For multi-instance deployments, prefer a shared store (Redis/Postgres).
_FAILED_BY_IP: dict[str, deque] = defaultdict(deque)  # ip -> timestamps (seconds)
_LOCKED_UNTIL: dict[str, float] = {}                  # ip -> epoch seconds
_MAX_FAILS = 5
_WINDOW_SECONDS = 10 * 60   # 10 minutes
_LOCK_SECONDS = 10 * 60     # 10 minutes


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if fwd:
        # first IP in the chain
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _is_locked(ip: str) -> float | None:
    until = _LOCKED_UNTIL.get(ip)
    now = time.time()
    if until and until > now:
        return until
    if until:
        _LOCKED_UNTIL.pop(ip, None)
    return None


def _register_failure(ip: str):
    now = time.time()
    q = _FAILED_BY_IP[ip]
    q.append(now)
    # drop old
    while q and (now - q[0]) > _WINDOW_SECONDS:
        q.popleft()
    if len(q) >= _MAX_FAILS:
        _LOCKED_UNTIL[ip] = now + _LOCK_SECONDS
        q.clear()


def _clear_failures(ip: str):
    _FAILED_BY_IP.pop(ip, None)
    _LOCKED_UNTIL.pop(ip, None)


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


def verify_admin(request: Request, db: Session = Depends(get_db)):
    if FREE_ADMIN_MODE:
        return True
    token = _extract_token(request, "admin_session")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )
    try:
        _decode_admin_token(token)
        return True
    except jwt.ExpiredSignatureError:
        _log_admin_event(db, request, "ADMIN_SESSION_EXPIRED", "failed", details="expired")
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    except jwt.InvalidTokenError:
        _log_admin_event(db, request, "ADMIN_SESSION_INVALID", "failed", details="invalid")
        raise HTTPException(status_code=401, detail="Invalid session.")


@router.get("/me")
def auth_me(request: Request):
    if FREE_ADMIN_MODE:
        return {"authenticated": True, "role": "admin", "free_mode": True}
    token = _extract_token(request, "admin_session")
    if not token:
        return {"authenticated": False}
    try:
        _decode_admin_token(token)
        return {"authenticated": True, "role": "admin"}
    except jwt.InvalidTokenError:
        return {"authenticated": False}


@router.get("/app-me")
def app_me(request: Request):
    token = _extract_token(request, "app_session")
    if not token:
        return {"authenticated": False}
    try:
        _decode_app_token(token)
        return {"authenticated": True, "role": "user"}
    except jwt.InvalidTokenError:
        return {"authenticated": False}


@router.post("/login")
def login(data: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    """
    Admin login using a PIN/password stored server-side (ADMIN_PASSWORD env var).
    Sets an HttpOnly session cookie. Includes rate limiting + audit logs.
    """
    ip = _client_ip(request)
    locked_until = _is_locked(ip)
    if locked_until:
        _log_admin_event(db, request, "ADMIN_LOGIN_LOCKED", "failed", details=f"locked_until={int(locked_until)}")
        raise HTTPException(status_code=429, detail="Too many failed attempts. Please wait before retrying.")

    if data.password != ADMIN_PASSWORD:
        _register_failure(ip)
        _log_admin_event(db, request, "ADMIN_LOGIN_FAILURE", "failed", details="invalid_pin")
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    expires_in = 30 * 24 * 60 * 60 if data.remember_device else 24 * 60 * 60
    token = create_access_token(
        data={"sub": "admin", "role": "admin"},
        expires_delta_seconds=expires_in,
    )

    response.set_cookie(
        key="admin_session",
        value=token,
        max_age=expires_in,
        httponly=True,
        secure=IS_PRODUCTION,
        # Frontend (Vercel) and API (Render) are different sites.
        # To persist sessions across refreshes, the cookie must be sent on cross-site XHR requests.
        # That requires SameSite=None + Secure in production.
        samesite="none" if IS_PRODUCTION else "lax",
        path="/",
    )
    _clear_failures(ip)
    _log_admin_event(db, request, "ADMIN_LOGIN_SUCCESS", "success", details=f"expires_in={expires_in}")
    return {"message": "Logged in successfully", "role": "admin", "access_token": token, "expires_in": expires_in}


@router.post("/app-login")
def app_login(data: LoginRequest, response: Response, request: Request):
    """
    Platform gateway login (non-admin). Uses APP_PASSWORD env var.
    Sets app_session HttpOnly cookie.
    """
    if data.password != APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    expires_in = 30 * 24 * 60 * 60 if data.remember_device else 24 * 60 * 60
    token = create_access_token(
        data={"sub": "user", "role": "user"},
        expires_delta_seconds=expires_in,
    )

    response.set_cookie(
        key="app_session",
        value=token,
        max_age=expires_in,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="none" if IS_PRODUCTION else "lax",
        path="/",
    )
    return {"message": "Logged in successfully", "role": "user", "access_token": token, "expires_in": expires_in}


@router.post("/logout")
def logout(response: Response, request: Request, db: Session = Depends(get_db)):
    response.delete_cookie(
        key="admin_session",
        path="/",
        httponly=True,
        samesite="none" if IS_PRODUCTION else "lax",
        secure=IS_PRODUCTION,
    )
    _log_admin_event(db, request, "ADMIN_LOGOUT", "success")
    return {"message": "Logged out successfully"}


@router.post("/app-logout")
def app_logout(response: Response):
    response.delete_cookie(
        key="app_session",
        path="/",
        httponly=True,
        samesite="none" if IS_PRODUCTION else "lax",
        secure=IS_PRODUCTION,
    )
    return {"message": "Logged out successfully"}
