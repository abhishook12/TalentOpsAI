from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from pydantic import BaseModel
import jwt
import time
import logging
from app.config import JWT_SECRET, ADMIN_PASSWORD, IS_PRODUCTION

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


def verify_admin(request: Request):
    token = request.cookies.get("admin_session")
    if not token:
        legacy = request.headers.get("X-Admin-Token")
        if legacy and legacy == ADMIN_PASSWORD:
            return True
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )
    try:
        _decode_admin_token(token)
        return True
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid session.")


@router.get("/me")
def auth_me(request: Request):
    token = request.cookies.get("admin_session")
    if not token:
        return {"authenticated": False}
    try:
        _decode_admin_token(token)
        return {"authenticated": True, "role": "admin"}
    except jwt.InvalidTokenError:
        return {"authenticated": False}


@router.post("/login")
def login(data: LoginRequest, response: Response):
    if data.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Incorrect password.")

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
        samesite="lax",
        path="/",
    )
    return {"message": "Logged in successfully", "role": "admin"}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key="admin_session",
        path="/",
        httponly=True,
        samesite="lax",
        secure=IS_PRODUCTION,
    )
    return {"message": "Logged out successfully"}
